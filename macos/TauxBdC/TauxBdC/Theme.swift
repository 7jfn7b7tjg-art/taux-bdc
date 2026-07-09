import SwiftUI
import AppKit

enum Theme {
    /// Teal de marque — éclairci en mode sombre pour rester lisible.
    static let accent = dynamic(
        light: NSColor(red: 0.043, green: 0.431, blue: 0.431, alpha: 1),   // #0B6E6E
        dark: NSColor(red: 0.29, green: 0.67, blue: 0.65, alpha: 1)
    )

    /// Or — badges et touches discrètes.
    static let gold = dynamic(
        light: NSColor(red: 0.769, green: 0.639, blue: 0.353, alpha: 1),   // #C4A35A
        dark: NSColor(red: 0.85, green: 0.73, blue: 0.46, alpha: 1)
    )

    // Fonds et textes : couleurs sémantiques système (clair/sombre automatiques)
    static let windowBg = Color(nsColor: .windowBackgroundColor)
    static let cardBg = Color(nsColor: .controlBackgroundColor)
    static let text = Color(nsColor: .labelColor)
    static let muted = Color(nsColor: .secondaryLabelColor)

    private static func dynamic(light: NSColor, dark: NSColor) -> Color {
        Color(nsColor: NSColor(name: nil) { appearance in
            appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua ? dark : light
        })
    }
}
