import SwiftUI
import AppKit
import UniformTypeIdentifiers

enum ConvertDirection: String {
    case toCAD, fromCAD
}

enum RateMode: String, CaseIterable {
    case daily, monthly, annual
}

/// Résultat affichable, indépendant du sens et du type de taux.
struct ConvertOutcome: Equatable {
    var currency: String
    var series: String
    var rate: Decimal
    var requestedLabel: String   // date ISO ou période "2026-06"
    var rateDetail: String       // date BdC ou "Taux moyen … (n obs.)"
    var adjusted: Bool
    var sourceLabel: String
    var inputAmount: Decimal
    var inputCurrency: String
    var outputAmount: Decimal
    var outputCurrency: String
    var reference: String
}

/// NSSavePanel avec mémoire du dernier dossier d'export.
enum ExportPanel {
    private static let key = "pref_export_dir"

    static func make(name: String, type: UTType) -> NSSavePanel {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [type]
        panel.nameFieldStringValue = name
        if let dir = UserDefaults.standard.string(forKey: key) {
            panel.directoryURL = URL(fileURLWithPath: dir, isDirectory: true)
        }
        return panel
    }

    static func remember(_ url: URL) {
        UserDefaults.standard.set(url.deletingLastPathComponent().path, forKey: key)
    }
}

struct ConvertView: View {
    @EnvironmentObject private var appState: AppState

    @AppStorage("pref_currency") private var currency = "USD"
    @AppStorage("pref_direction") private var directionRaw = ConvertDirection.toCAD.rawValue
    @AppStorage("pref_rate_mode") private var rateModeRaw = RateMode.daily.rawValue

    @State private var date = Date()
    @State private var selectedYear = Calendar.current.component(.year, from: Date())
    @State private var selectedMonth = Calendar.current.component(.month, from: Date())
    @State private var amountText = ""
    @State private var reference = ""
    @State private var outcome: ConvertOutcome?
    @State private var isBusy = false
    @State private var errorMessage: String?
    @State private var showError = false

    private var direction: ConvertDirection {
        ConvertDirection(rawValue: directionRaw) ?? .toCAD
    }
    private var rateMode: RateMode {
        RateMode(rawValue: rateModeRaw) ?? .daily
    }
    private var inputCurrency: String {
        direction == .toCAD ? currency : "CAD"
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                form
                if let outcome {
                    resultCard(outcome)
                        .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
            .padding(20)
            .frame(maxWidth: 660, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .animation(.easeOut(duration: 0.2), value: outcome)
        .alert(L10n.t("error", lang: appState.lang), isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

    // MARK: - Formulaire

    private var form: some View {
        VStack(alignment: .leading, spacing: 0) {
            Grid(alignment: .leading, horizontalSpacing: 14, verticalSpacing: 12) {
                GridRow {
                    label(L10n.t("currency", lang: appState.lang))
                    Picker("", selection: $currency) {
                        ForEach(CurrencyCatalog.codes, id: \.self) { code in
                            Text(code).tag(code)
                        }
                    }
                    .labelsHidden()
                    .frame(width: 110, alignment: .leading)
                }

                GridRow {
                    label(L10n.t("direction", lang: appState.lang))
                    Picker("", selection: $directionRaw) {
                        Text("\(currency) → CAD").tag(ConvertDirection.toCAD.rawValue)
                        Text("CAD → \(currency)").tag(ConvertDirection.fromCAD.rawValue)
                    }
                    .pickerStyle(.segmented)
                    .labelsHidden()
                    .frame(width: 260)
                }

                GridRow {
                    label(L10n.t("rate_mode", lang: appState.lang))
                    Picker("", selection: $rateModeRaw) {
                        Text(L10n.t("mode_daily", lang: appState.lang)).tag(RateMode.daily.rawValue)
                        Text(L10n.t("mode_monthly", lang: appState.lang)).tag(RateMode.monthly.rawValue)
                        Text(L10n.t("mode_annual", lang: appState.lang)).tag(RateMode.annual.rawValue)
                    }
                    .labelsHidden()
                    .frame(width: 200, alignment: .leading)
                }

                switch rateMode {
                case .daily:
                    GridRow {
                        label(L10n.t("date", lang: appState.lang))
                        DatePicker("", selection: $date, displayedComponents: .date)
                            .labelsHidden()
                            .datePickerStyle(.field)
                            .frame(width: 130, alignment: .leading)
                    }
                case .monthly:
                    GridRow {
                        label(L10n.t("period", lang: appState.lang))
                        HStack(spacing: 8) {
                            Picker("", selection: $selectedMonth) {
                                ForEach(1...12, id: \.self) { m in
                                    Text(monthName(m)).tag(m)
                                }
                            }
                            .labelsHidden()
                            .frame(width: 130)
                            yearPicker
                        }
                    }
                case .annual:
                    GridRow {
                        label(L10n.t("year", lang: appState.lang))
                        yearPicker
                    }
                }

                GridRow {
                    label("\(L10n.t("amount", lang: appState.lang)) (\(inputCurrency))")
                    TextField("1500.00", text: $amountText)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 180)
                        .onSubmit { Task { await convert() } }
                }

                GridRow {
                    label(L10n.t("reference", lang: appState.lang))
                    TextField("FAC-123", text: $reference)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 220)
                }
            }
            .padding(18)

            Divider()

            HStack(spacing: 10) {
                Button {
                    Task { await convert() }
                } label: {
                    HStack(spacing: 6) {
                        if isBusy {
                            ProgressView().controlSize(.small)
                        } else {
                            Image(systemName: "arrow.left.arrow.right")
                        }
                        Text(L10n.t("convert", lang: appState.lang))
                    }
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .disabled(isBusy || amountText.trimmingCharacters(in: .whitespaces).isEmpty)
                Spacer()
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 12)
        }
        .background(Theme.cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .strokeBorder(Color(nsColor: .separatorColor), lineWidth: 1)
        )
    }

    private var yearPicker: some View {
        let current = Calendar.current.component(.year, from: Date())
        return Picker("", selection: $selectedYear) {
            ForEach((2017...current).reversed(), id: \.self) { y in
                Text(String(y)).tag(y)
            }
        }
        .labelsHidden()
        .frame(width: 90)
    }

    private func monthName(_ m: Int) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: appState.lang == .fr ? "fr_CA" : "en_CA")
        return f.monthSymbols[m - 1].capitalized
    }

    private func label(_ text: String) -> some View {
        Text(text)
            .foregroundStyle(Theme.muted)
            .frame(width: 150, alignment: .leading)
    }

    // MARK: - Fiche résultat

    private func resultCard(_ o: ConvertOutcome) -> some View {
        let lang = appState.lang
        return VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 4) {
                Text(L10n.t("converted_amount", lang: lang))
                    .font(.caption)
                    .foregroundStyle(Theme.muted)
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text("\(MoneyParsing.format(o.outputAmount, decimals: 2, lang: lang)) \(o.outputCurrency)")
                        .font(.system(size: 30, weight: .bold, design: .rounded))
                        .foregroundStyle(Theme.accent)
                        .textSelection(.enabled)
                    if o.adjusted {
                        Text(L10n.t("adjusted", lang: lang))
                            .font(.caption2.weight(.semibold))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(Theme.gold.opacity(0.18))
                            .foregroundStyle(Theme.gold)
                            .clipShape(Capsule())
                    }
                }
            }
            .padding(18)

            Divider()

            VStack(spacing: 10) {
                detailRow(L10n.t("currency", lang: lang), o.currency)
                detailRow(
                    rateMode == .daily ? L10n.t("date", lang: lang) : L10n.t("period", lang: lang),
                    o.requestedLabel
                )
                detailRow(L10n.t("rate_date", lang: lang), o.rateDetail)
                detailRow("1 \(o.currency) = CAD", MoneyParsing.format(o.rate, lang: lang))
                detailRow(
                    "\(L10n.t("amount", lang: lang)) (\(o.inputCurrency))",
                    "\(MoneyParsing.format(o.inputAmount, decimals: 2, lang: lang)) \(o.inputCurrency)"
                )
                if !o.reference.isEmpty {
                    detailRow(L10n.t("reference", lang: lang), o.reference)
                }
            }
            .padding(18)

            Divider()

            HStack(spacing: 10) {
                Menu {
                    Button(L10n.t("copy_full", lang: lang)) { copyToPasteboard(ficheText(o)) }
                    Button(L10n.t("copy_amount_only", lang: lang)) {
                        copyToPasteboard(NSDecimalNumber(decimal: o.outputAmount).stringValue)
                    }
                    Button(L10n.t("copy_tsv", lang: lang)) { copyToPasteboard(tsvLine(o)) }
                } label: {
                    Label(L10n.t("copy", lang: lang), systemImage: "doc.on.doc")
                }
                .fixedSize()

                Button {
                    exportCSV(o)
                } label: {
                    Label(L10n.t("export_csv", lang: lang), systemImage: "square.and.arrow.up")
                }

                Spacer()
                Text(o.sourceLabel)
                    .font(.caption2)
                    .foregroundStyle(Theme.muted)
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 12)
        }
        .background(Theme.cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .strokeBorder(Color(nsColor: .separatorColor), lineWidth: 1)
        )
    }

    private func detailRow(_ title: String, _ value: String) -> some View {
        LabeledContent {
            Text(value)
                .foregroundStyle(Theme.text)
                .textSelection(.enabled)
        } label: {
            Text(title)
                .foregroundStyle(Theme.muted)
        }
    }

    // MARK: - Textes de copie

    private func ficheText(_ o: ConvertOutcome) -> String {
        let lang = appState.lang
        let note = o.adjusted ? "  ← \(L10n.t("adjusted", lang: lang))" : ""
        return """
        \(L10n.t("fiche_title", lang: lang))
        ────────────────────────────────
        \(L10n.t("currency", lang: lang)) : \(o.currency)
        \(rateMode == .daily ? L10n.t("date", lang: lang) : L10n.t("period", lang: lang)) : \(o.requestedLabel)
        \(L10n.t("rate_date", lang: lang)) : \(o.rateDetail)\(note)
        1 \(o.currency) = CAD : \(MoneyParsing.format(o.rate, lang: lang))
        \(L10n.t("amount", lang: lang)) : \(MoneyParsing.format(o.inputAmount, decimals: 2, lang: lang)) \(o.inputCurrency)
        \(L10n.t("converted_amount", lang: lang)) : \(MoneyParsing.format(o.outputAmount, decimals: 2, lang: lang)) \(o.outputCurrency)
        Source : \(o.sourceLabel)
        """
    }

    /// date ⇥ référence ⇥ devise ⇥ montant devise ⇥ taux ⇥ montant CAD (points décimaux bruts)
    private func tsvLine(_ o: ConvertOutcome) -> String {
        let foreign = o.inputCurrency == "CAD" ? o.outputAmount : o.inputAmount
        let cad = o.inputCurrency == "CAD" ? o.inputAmount : o.outputAmount
        return [
            o.requestedLabel,
            o.reference,
            o.currency,
            NSDecimalNumber(decimal: foreign).stringValue,
            NSDecimalNumber(decimal: o.rate).stringValue,
            NSDecimalNumber(decimal: cad).stringValue,
        ].joined(separator: "\t")
    }

    private func copyToPasteboard(_ text: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
        appState.status = appState.lang == .fr ? "Copié." : "Copied."
    }

    // MARK: - Conversion

    private func localISO(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }

    @MainActor
    private func convert() async {
        isBusy = true
        appState.status = L10n.t("fetching", lang: appState.lang)
        defer { isBusy = false }
        do {
            let amount = try MoneyParsing.parseAmount(amountText)
            let lang = appState.lang

            let rate: Decimal
            let series: String
            let requestedLabel: String
            let rateDetail: String
            let adjusted: Bool
            let sourceLabel: String

            switch rateMode {
            case .daily:
                let parsed = try MoneyParsing.parseDate(localISO(date))
                let ex = try await BoCRateService.shared.fetchRate(currency: currency, on: parsed)
                rate = ex.rate
                series = ex.series
                requestedLabel = MoneyParsing.isoDate(ex.requestedDate)
                rateDetail = MoneyParsing.isoDate(ex.rateDate)
                adjusted = ex.isAdjusted
                sourceLabel = ex.sourceLabel(lang: lang)
            case .monthly, .annual:
                let avg = try await BoCRateService.shared.fetchAverageRate(
                    currency: currency,
                    year: selectedYear,
                    month: rateMode == .monthly ? selectedMonth : nil
                )
                rate = avg.rate
                series = avg.series
                requestedLabel = avg.periodLabel
                rateDetail = L10n.t("avg_detail", lang: lang, avg.periodLabel, avg.observationCount)
                adjusted = false
                sourceLabel = (lang == .fr ? "Banque du Canada (Valet) / " : "Bank of Canada (Valet) / ") + avg.series
            }

            let input = amount
            let output: Decimal
            let inputCcy: String
            let outputCcy: String
            if direction == .toCAD {
                output = BoCRateService.multiply(input, by: rate)
                inputCcy = currency
                outputCcy = "CAD"
            } else {
                output = BoCRateService.divide(input, by: rate)
                inputCcy = "CAD"
                outputCcy = currency
            }

            AuditLog.append(
                lang: lang,
                reference: reference,
                requestedDate: requestedLabel,
                rateDate: rateDetail,
                rate: rate,
                fromAmount: input,
                fromCurrency: inputCcy,
                toAmount: output,
                toCurrency: outputCcy,
                sourceLabel: sourceLabel
            )

            outcome = ConvertOutcome(
                currency: currency,
                series: series,
                rate: rate,
                requestedLabel: requestedLabel,
                rateDetail: rateDetail,
                adjusted: adjusted,
                sourceLabel: sourceLabel,
                inputAmount: input,
                inputCurrency: inputCcy,
                outputAmount: output,
                outputCurrency: outputCcy,
                reference: reference.trimmingCharacters(in: .whitespacesAndNewlines)
            )
            appState.status = L10n.t("done", lang: appState.lang)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
            appState.status = L10n.t("ready", lang: appState.lang)
        }
    }

    private func exportCSV(_ o: ConvertOutcome) {
        let foreign = o.inputCurrency == "CAD" ? o.outputAmount : o.inputAmount
        let cad = o.inputCurrency == "CAD" ? o.inputAmount : o.outputAmount
        var row = BatchRow(
            rawDate: o.requestedLabel,
            currency: o.currency,
            rawAmount: NSDecimalNumber(decimal: foreign).stringValue,
            reference: o.reference
        )
        row.requestedDate = try? MoneyParsing.parseDate(o.requestedLabel)
        row.amount = foreign
        row.rate = o.rate
        row.cad = cad
        row.series = o.series
        row.adjusted = o.adjusted
        let csv = CSVBatch.export([row], lang: appState.lang)
        let panel = ExportPanel.make(name: "conversion_bdc.csv", type: .commaSeparatedText)
        if panel.runModal() == .OK, let url = panel.url {
            try? csv.write(to: url, atomically: true, encoding: .utf8)
            ExportPanel.remember(url)
            appState.status = appState.lang == .fr ? "CSV enregistré." : "CSV saved."
        }
    }
}
