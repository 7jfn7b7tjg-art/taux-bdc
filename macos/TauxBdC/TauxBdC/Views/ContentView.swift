import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var appState: AppState
    @State private var selection: AppSection? = .convert

    enum AppSection: Hashable {
        case convert, batch
    }

    var body: some View {
        NavigationSplitView {
            sidebar
        } detail: {
            detail
        }
        .navigationTitle(L10n.t("brand", lang: appState.lang))
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Picker(L10n.t("lang", lang: appState.lang), selection: $appState.lang) {
                    ForEach(AppLang.allCases) { lang in
                        Text(lang.label).tag(lang)
                    }
                }
                .pickerStyle(.menu)
                .onChange(of: appState.lang) { newValue in
                    appState.status = L10n.t("ready", lang: newValue)
                }
            }
        }
    }

    private var sidebar: some View {
        List(selection: $selection) {
            Section {
                Label(L10n.t("tab_convert", lang: appState.lang),
                      systemImage: "arrow.left.arrow.right.circle")
                    .tag(AppSection.convert)
                Label(L10n.t("tab_batch", lang: appState.lang),
                      systemImage: "tablecells")
                    .tag(AppSection.batch)
            } header: {
                sidebarHeader
            }
        }
        .listStyle(.sidebar)
        .navigationSplitViewColumnWidth(min: 200, ideal: 220, max: 280)
    }

    private var sidebarHeader: some View {
        HStack(spacing: 10) {
            Image("Logo")
                .resizable()
                .interpolation(.high)
                .frame(width: 34, height: 34)
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            VStack(alignment: .leading, spacing: 1) {
                Text(L10n.t("brand", lang: appState.lang))
                    .font(.headline)
                    .foregroundStyle(Theme.text)
                Text(L10n.t("tagline", lang: appState.lang))
                    .font(.caption2)
                    .foregroundStyle(Theme.gold)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 6)
    }

    private var detail: some View {
        VStack(spacing: 0) {
            Group {
                switch selection ?? .convert {
                case .convert:
                    ConvertView()
                case .batch:
                    BatchView()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            Divider()
            HStack {
                Text(appState.status)
                    .font(.caption)
                    .foregroundStyle(Theme.muted)
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 6)
        }
        .background(Theme.windowBg)
    }
}
