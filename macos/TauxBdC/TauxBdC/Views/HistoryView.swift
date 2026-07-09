import SwiftUI
import AppKit
import UniformTypeIdentifiers

struct HistoryView: View {
    @EnvironmentObject private var appState: AppState

    @State private var entries: [String] = []
    @State private var query = ""
    @State private var showClearConfirm = false
    @State private var errorMessage: String?
    @State private var showError = false

    private var filtered: [String] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return entries }
        return entries.filter { $0.localizedCaseInsensitiveContains(q) }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                HStack(spacing: 6) {
                    Image(systemName: "magnifyingglass")
                        .foregroundStyle(Theme.muted)
                    TextField(L10n.t("search_placeholder", lang: appState.lang), text: $query)
                        .textFieldStyle(.plain)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Theme.cardBg)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .strokeBorder(Color(nsColor: .separatorColor), lineWidth: 1)
                )
                .frame(maxWidth: 380)

                Button {
                    exportFiltered()
                } label: {
                    Label(L10n.t("export_txt", lang: appState.lang), systemImage: "square.and.arrow.up")
                }
                .disabled(filtered.isEmpty)

                Button {
                    NSWorkspace.shared.activateFileViewerSelecting([AppDataPaths.auditLog])
                } label: {
                    Label(L10n.t("show_finder", lang: appState.lang), systemImage: "folder")
                }

                Button(role: .destructive) {
                    showClearConfirm = true
                } label: {
                    Label(L10n.t("clear_history", lang: appState.lang), systemImage: "trash")
                }
                .disabled(entries.isEmpty)

                Spacer()

                Text(L10n.t("history_count", lang: appState.lang, filtered.count))
                    .font(.caption)
                    .foregroundStyle(Theme.muted)
            }

            if filtered.isEmpty {
                emptyState
            } else {
                list
            }
        }
        .padding(20)
        .onAppear(perform: reload)
        .alert(L10n.t("error", lang: appState.lang), isPresented: $showError) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(errorMessage ?? "")
        }
        .confirmationDialog(
            L10n.t("clear_confirm_title", lang: appState.lang),
            isPresented: $showClearConfirm,
            titleVisibility: .visible
        ) {
            Button(L10n.t("clear_confirm_button", lang: appState.lang), role: .destructive) {
                clearHistory()
            }
            Button(L10n.t("cancel", lang: appState.lang), role: .cancel) {}
        } message: {
            Text(L10n.t("clear_confirm_message", lang: appState.lang))
        }
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "clock.arrow.circlepath")
                .font(.system(size: 42, weight: .light))
                .foregroundStyle(Theme.muted)
            Text(L10n.t("no_history", lang: appState.lang))
                .foregroundStyle(Theme.muted)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.cardBg.opacity(0.5))
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .strokeBorder(Color(nsColor: .separatorColor), style: StrokeStyle(lineWidth: 1, dash: [6]))
        )
    }

    private var list: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                ForEach(Array(filtered.enumerated()), id: \.offset) { index, line in
                    Text(line)
                        .font(.system(size: 11.5, design: .monospaced))
                        .foregroundStyle(Theme.text)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 7)
                        .background(index.isMultiple(of: 2) ? Color.clear : Theme.windowBg.opacity(0.6))
                    Divider()
                }
            }
        }
        .background(Theme.cardBg)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .strokeBorder(Color(nsColor: .separatorColor), lineWidth: 1)
        )
    }

    private func reload() {
        entries = AuditLog.readEntries()
    }

    private func exportFiltered() {
        let panel = ExportPanel.make(name: "historique_conversions.txt", type: .plainText)
        if panel.runModal() == .OK, let url = panel.url {
            let text = filtered.joined(separator: "\n") + "\n"
            try? text.write(to: url, atomically: true, encoding: .utf8)
            ExportPanel.remember(url)
            appState.status = appState.lang == .fr ? "Historique exporté." : "History exported."
        }
    }

    private func clearHistory() {
        do {
            let backup = try AuditLog.clearWithBackup()
            query = ""
            reload()
            if let backup {
                appState.status = L10n.t("cleared_status", lang: appState.lang, backup.lastPathComponent)
            } else {
                appState.status = L10n.t("ready", lang: appState.lang)
            }
        } catch {
            errorMessage = error.localizedDescription
            showError = true
            appState.status = L10n.t("ready", lang: appState.lang)
        }
    }
}
