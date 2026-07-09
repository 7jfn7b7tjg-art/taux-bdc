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
    @Published var lang: AppLang {
        didSet { UserDefaults.standard.set(lang.rawValue, forKey: "pref_lang") }
    }
    @Published var status: String = ""
    /// Incrémenté à chaque écriture ou effacement du journal d'audit.
    @Published var auditLogRevision: Int = 0

    func bumpAuditLog() {
        auditLogRevision += 1
    }

    init() {
        let saved = UserDefaults.standard.string(forKey: "pref_lang")
        lang = saved.flatMap(AppLang.init(rawValue:)) ?? .fr
        status = L10n.t("ready", lang: lang)
    }
}
