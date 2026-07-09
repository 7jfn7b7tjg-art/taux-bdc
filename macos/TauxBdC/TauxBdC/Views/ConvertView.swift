import SwiftUI
import AppKit
import UniformTypeIdentifiers

struct ConvertView: View {
    @EnvironmentObject private var appState: AppState

    @State private var currency = "USD"
    @State private var date = Date()
    @State private var amountText = ""
    @State private var reference = ""
    @State private var result: ConversionResult?
    @State private var isBusy = false
    @State private var errorMessage: String?
    @State private var showError = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                form
                if let result {
                    resultCard(result)
                        .transition(.opacity.combined(with: .move(edge: .top)))
                }
            }
            .padding(20)
            .frame(maxWidth: 640, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .animation(.easeOut(duration: 0.2), value: result)
        .alert(L10n.t("error", lang: appState.lang), isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
    }

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
                    label(L10n.t("date", lang: appState.lang))
                    DatePicker("", selection: $date, displayedComponents: .date)
                        .labelsHidden()
                        .datePickerStyle(.field)
                        .frame(width: 130, alignment: .leading)
                }
                GridRow {
                    label(L10n.t("amount", lang: appState.lang))
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

    private func label(_ text: String) -> some View {
        Text(text)
            .foregroundStyle(Theme.muted)
            .frame(width: 150, alignment: .leading)
    }

    private func resultCard(_ result: ConversionResult) -> some View {
        let lang = appState.lang
        let r = result.rate
        return VStack(alignment: .leading, spacing: 0) {
            // Montant CAD en vedette
            VStack(alignment: .leading, spacing: 4) {
                Text(L10n.t("cad_amount", lang: lang))
                    .font(.caption)
                    .foregroundStyle(Theme.muted)
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text("\(MoneyParsing.format(result.cad, decimals: 2, lang: lang)) CAD")
                        .font(.system(size: 30, weight: .bold, design: .rounded))
                        .foregroundStyle(Theme.accent)
                        .textSelection(.enabled)
                    if r.isAdjusted {
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
                detailRow(L10n.t("currency", lang: lang), r.currency)
                detailRow(L10n.t("date", lang: lang), MoneyParsing.isoDate(r.requestedDate))
                detailRow(L10n.t("rate_date", lang: lang), MoneyParsing.isoDate(r.rateDate))
                detailRow("1 \(r.currency) = CAD", MoneyParsing.format(r.rate, lang: lang))
                detailRow(L10n.t("amount", lang: lang),
                          "\(MoneyParsing.format(result.amount, decimals: 2, lang: lang)) \(r.currency)")
                if !result.reference.isEmpty {
                    detailRow(L10n.t("reference", lang: lang), result.reference)
                }
            }
            .padding(18)

            Divider()

            HStack(spacing: 10) {
                Button {
                    copyResult()
                } label: {
                    Label(L10n.t("copy", lang: lang), systemImage: "doc.on.doc")
                }
                Button {
                    exportCSV()
                } label: {
                    Label(L10n.t("export_csv", lang: lang), systemImage: "square.and.arrow.up")
                }
                Spacer()
                Text(r.sourceLabel(lang: lang))
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

    private var resultText: String {
        guard let result else { return "—" }
        let lang = appState.lang
        let r = result.rate
        let note = r.isAdjusted ? "  ← \(L10n.t("adjusted", lang: lang))" : ""
        return """
        \(L10n.t("fiche_title", lang: lang))
        ────────────────────────────────
        \(L10n.t("currency", lang: lang)) : \(r.currency)
        \(L10n.t("date", lang: lang)) : \(MoneyParsing.isoDate(r.requestedDate))
        \(L10n.t("rate_date", lang: lang)) : \(MoneyParsing.isoDate(r.rateDate))\(note)
        1 \(r.currency) = CAD : \(MoneyParsing.format(r.rate, lang: lang))
        \(L10n.t("amount", lang: lang)) : \(MoneyParsing.format(result.amount, decimals: 2, lang: lang)) \(r.currency)
        \(L10n.t("cad_amount", lang: lang)) : \(MoneyParsing.format(result.cad, decimals: 2, lang: lang)) CAD
        Source : \(r.sourceLabel(lang: lang))
        """
    }

    /// ISO local : le DatePicker rend une Date en fuseau local ; formater en GMT
    /// pourrait décaler d'un jour en soirée.
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
            result = try await BoCRateService.shared.convertAndLog(
                currency: currency,
                dateText: localISO(date),
                amountText: amountText,
                reference: reference,
                lang: appState.lang
            )
            appState.status = L10n.t("done", lang: appState.lang)
        } catch {
            errorMessage = error.localizedDescription
            showError = true
            appState.status = L10n.t("ready", lang: appState.lang)
        }
    }

    private func copyResult() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(resultText, forType: .string)
        appState.status = appState.lang == .fr ? "Fiche copiée." : "Copied."
    }

    private func exportCSV() {
        guard let result else { return }
        let row = BatchRow(
            rawDate: MoneyParsing.isoDate(result.rate.requestedDate),
            currency: result.rate.currency,
            rawAmount: NSDecimalNumber(decimal: result.amount).stringValue,
            reference: result.reference,
            requestedDate: result.rate.requestedDate,
            amount: result.amount,
            rateDate: result.rate.rateDate,
            rate: result.rate.rate,
            cad: result.cad,
            series: result.rate.series,
            adjusted: result.rate.isAdjusted,
            error: ""
        )
        let csv = CSVBatch.export([row], lang: appState.lang)
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.commaSeparatedText]
        panel.nameFieldStringValue = "conversion_bdc.csv"
        if panel.runModal() == .OK, let url = panel.url {
            try? csv.write(to: url, atomically: true, encoding: .utf8)
            appState.status = appState.lang == .fr ? "CSV enregistré." : "CSV saved."
        }
    }
}
