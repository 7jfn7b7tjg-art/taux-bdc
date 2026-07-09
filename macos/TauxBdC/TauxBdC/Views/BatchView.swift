import SwiftUI
import UniformTypeIdentifiers
import AppKit

struct BatchView: View {
    @EnvironmentObject private var appState: AppState

    @State private var rows: [BatchRow] = []
    @State private var isBusy = false
    @State private var progress: Double = 0
    @State private var processedCount = 0
    @State private var showImporter = false
    @State private var errorMessage: String?
    @State private var showError = false
    @State private var showConfirm = false
    @State private var isDropTargeted = false

    private static let importTypes: [UTType] = {
        var types: [UTType] = [.commaSeparatedText, .json, .xml, .plainText]
        if let xlsx = UTType(filenameExtension: "xlsx") {
            types.insert(xlsx, at: 1)
        }
        return types
    }()

    private static let importExtensions: Set<String> = ["csv", "xlsx", "xlsm", "json", "xml", "txt"]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            actionBar

            if isBusy {
                HStack(spacing: 10) {
                    ProgressView(value: progress)
                    Text("\(processedCount) / \(rows.count)")
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(Theme.muted)
                }
            }

            if rows.isEmpty {
                emptyState
            } else {
                table
            }
        }
        .padding(20)
        .onDrop(of: [.fileURL], isTargeted: $isDropTargeted) { providers in
            handleDrop(providers)
        }
        .fileImporter(
            isPresented: $showImporter,
            allowedContentTypes: Self.importTypes,
            allowsMultipleSelection: false
        ) { result in
            switch result {
            case .success(let urls):
                if let url = urls.first { importFile(url) }
            case .failure(let error):
                errorMessage = error.localizedDescription
                showError = true
            }
        }
        .alert(L10n.t("error", lang: appState.lang), isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
        .confirmationDialog(
            String(format: L10n.t("confirm_batch", lang: appState.lang), rows.count),
            isPresented: $showConfirm
        ) {
            Button(L10n.t("process", lang: appState.lang)) {
                Task { await processBatch() }
            }
            Button(appState.lang == .fr ? "Annuler" : "Cancel", role: .cancel) {}
        }
    }

    private var actionBar: some View {
        HStack(spacing: 10) {
            Button {
                showImporter = true
            } label: {
                Label(L10n.t("import_csv", lang: appState.lang), systemImage: "square.and.arrow.down")
            }
            .buttonStyle(.borderedProminent)

            Button {
                saveTemplate()
            } label: {
                Label(L10n.t("save_template", lang: appState.lang), systemImage: "doc.badge.plus")
            }

            Button {
                showConfirm = true
            } label: {
                Label(L10n.t("process", lang: appState.lang), systemImage: "play.fill")
            }
            .disabled(rows.isEmpty || isBusy)

            Menu {
                Button("CSV") { exportResult(ext: "csv", type: .commaSeparatedText) }
                Button("JSON") { exportResult(ext: "json", type: .json) }
                Button("XML") { exportResult(ext: "xml", type: .xml) }
            } label: {
                Label(L10n.t("export_result", lang: appState.lang), systemImage: "square.and.arrow.up")
            }
            .fixedSize()
            .disabled(rows.isEmpty)

            Spacer()
        }
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "tray.and.arrow.down")
                .font(.system(size: 42, weight: .light))
                .foregroundStyle(Theme.muted)
            Text(L10n.t("no_rows", lang: appState.lang))
                .foregroundStyle(Theme.muted)
            Text(L10n.t("batch_hint", lang: appState.lang))
                .font(.caption)
                .foregroundStyle(Theme.muted.opacity(0.8))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(isDropTargeted ? Theme.accent.opacity(0.08) : Theme.cardBg.opacity(0.5))
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .strokeBorder(
                    isDropTargeted ? Theme.accent : Color(nsColor: .separatorColor),
                    style: StrokeStyle(lineWidth: isDropTargeted ? 2 : 1, dash: [6])
                )
        )
        .animation(.easeOut(duration: 0.15), value: isDropTargeted)
    }

    private var table: some View {
        Table(rows) {
            TableColumn("date") { row in
                Text(row.requestedDate.map(MoneyParsing.isoDate) ?? row.rawDate)
            }
            TableColumn("devise") { row in
                Text(row.currency)
            }
            TableColumn("montant") { row in
                Text(row.rawAmount)
            }
            TableColumn("réf.") { row in
                Text(row.reference)
            }
            TableColumn("date_taux") { row in
                Text(row.rateDate.map(MoneyParsing.isoDate) ?? "")
            }
            TableColumn("taux") { row in
                Text(row.rate.map { MoneyParsing.format($0, lang: appState.lang) } ?? "")
            }
            TableColumn("CAD") { row in
                Text(row.cad.map { MoneyParsing.format($0, decimals: 2, lang: appState.lang) } ?? "")
                    .fontWeight(row.cad == nil ? .regular : .medium)
                    .foregroundStyle(row.cad == nil ? Theme.text : Theme.accent)
            }
            TableColumn("erreur") { row in
                if row.error.isEmpty {
                    Text("")
                } else {
                    Text(row.error)
                        .foregroundStyle(.red)
                        .help(row.error)
                }
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .strokeBorder(Color(nsColor: .separatorColor), lineWidth: 1)
        )
    }

    private func importFile(_ url: URL) {
        let accessed = url.startAccessingSecurityScopedResource()
        defer { if accessed { url.stopAccessingSecurityScopedResource() } }
        do {
            rows = try FileFormats.importRows(from: url)
            progress = 0
            processedCount = 0
            appState.status = "\(rows.count) — \(L10n.t("ready", lang: appState.lang))"
        } catch {
            errorMessage = error.localizedDescription
            showError = true
        }
    }

    private func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        guard let provider = providers.first(where: { $0.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) }) else {
            return false
        }
        provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
            let url: URL?
            if let data = item as? Data {
                url = URL(dataRepresentation: data, relativeTo: nil)
            } else if let u = item as? URL {
                url = u
            } else {
                url = nil
            }
            guard let url, Self.importExtensions.contains(url.pathExtension.lowercased()) else { return }
            DispatchQueue.main.async {
                importFile(url)
            }
        }
        return true
    }

    private func saveTemplate() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.commaSeparatedText]
        panel.nameFieldStringValue = "modele_lot.csv"
        if panel.runModal() == .OK, let url = panel.url {
            try? CSVBatch.templateCSV().write(to: url, atomically: true, encoding: .utf8)
        }
    }

    private func exportResult(ext: String, type: UTType) {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [type]
        panel.nameFieldStringValue = "conversions_bdc.\(ext)"
        if panel.runModal() == .OK, var url = panel.url {
            if url.pathExtension.lowercased() != ext {
                url = url.appendingPathExtension(ext)
            }
            do {
                try FileFormats.export(rows, to: url, lang: appState.lang)
                appState.status = appState.lang == .fr ? "Fichier enregistré." : "File saved."
            } catch {
                errorMessage = error.localizedDescription
                showError = true
            }
        }
    }

    @MainActor
    private func processBatch() async {
        guard !rows.isEmpty else {
            errorMessage = L10n.t("no_rows", lang: appState.lang)
            showError = true
            return
        }
        isBusy = true
        progress = 0
        processedCount = 0
        defer { isBusy = false }

        var ok = 0
        var err = 0
        let total = Double(rows.count)

        for i in rows.indices {
            if !rows[i].error.isEmpty {
                err += 1
            } else if let date = rows[i].requestedDate, let amount = rows[i].amount {
                do {
                    let rate = try await BoCRateService.shared.fetchRate(currency: rows[i].currency, on: date)
                    let cad = await BoCRateService.shared.convert(amount: amount, rate: rate.rate)
                    AuditLog.append(
                        lang: appState.lang,
                        reference: rows[i].reference,
                        requestedDate: MoneyParsing.isoDate(rate.requestedDate),
                        rateDate: MoneyParsing.isoDate(rate.rateDate),
                        rate: rate.rate,
                        currency: rate.currency,
                        amount: amount,
                        cad: cad,
                        sourceLabel: rate.sourceLabel(lang: appState.lang)
                    )
                    rows[i].rateDate = rate.rateDate
                    rows[i].rate = rate.rate
                    rows[i].cad = cad
                    rows[i].series = rate.series
                    rows[i].adjusted = rate.isAdjusted
                    rows[i].error = ""
                    ok += 1
                } catch {
                    rows[i].error = error.localizedDescription
                    err += 1
                }
            } else {
                rows[i].error = "Ligne incomplète"
                err += 1
            }
            processedCount = i + 1
            progress = Double(i + 1) / total
            appState.status = "\(i + 1) / \(rows.count)"
        }

        appState.status = String(format: L10n.t("batch_done", lang: appState.lang), ok, err)
    }
}
