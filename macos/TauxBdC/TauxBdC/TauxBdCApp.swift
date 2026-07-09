import SwiftUI

@main
struct TauxBdCApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .tint(Theme.accent)
                .frame(minWidth: 840, minHeight: 560)
        }
        .defaultSize(width: 960, height: 660)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }
}

@MainActor
final class AppState: ObservableObject {
    @Published var lang: AppLang = .fr
    @Published var status: String = ""

    init() {
        status = L10n.t("ready", lang: lang)
    }
}
