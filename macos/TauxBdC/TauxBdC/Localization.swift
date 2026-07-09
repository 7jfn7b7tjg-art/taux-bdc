import Foundation
import SwiftUI

enum AppLang: String, CaseIterable, Identifiable {
    case fr, en
    var id: String { rawValue }
    var label: String {
        switch self {
        case .fr: return "Français"
        case .en: return "English"
        }
    }
}

enum L10n {
    static func t(_ key: String, lang: AppLang, _ args: CVarArg...) -> String {
        let table: [String: [AppLang: String]] = [
            "brand": [.fr: "Taux BdC", .en: "BoC Rates"],
            "tagline": [.fr: "Taux officiels · Écritures comptables", .en: "Official rates · Journal entries"],
            "tab_convert": [.fr: "Conversion", .en: "Convert"],
            "tab_batch": [.fr: "Lots", .en: "Batches"],
            "currency": [.fr: "Devise", .en: "Currency"],
            "date": [.fr: "Date transaction", .en: "Transaction date"],
            "amount": [.fr: "Montant", .en: "Amount"],
            "reference": [.fr: "Référence (opt.)", .en: "Reference (opt.)"],
            "convert": [.fr: "Convertir", .en: "Convert"],
            "copy": [.fr: "Copier", .en: "Copy"],
            "export_csv": [.fr: "Exporter CSV", .en: "Export CSV"],
            "result": [.fr: "Résultat", .en: "Result"],
            "import_csv": [.fr: "Importer un fichier…", .en: "Import file…"],
            "process": [.fr: "Traiter le lot", .en: "Process batch"],
            "export_result": [.fr: "Exporter le résultat…", .en: "Export results…"],
            "save_template": [.fr: "Enregistrer un modèle…", .en: "Save template…"],
            "ready": [.fr: "Prêt.", .en: "Ready."],
            "fetching": [.fr: "Récupération du taux…", .en: "Fetching rate…"],
            "done": [.fr: "Terminé.", .en: "Done."],
            "adjusted": [.fr: "ajustée (week-end/férié)", .en: "adjusted (weekend/holiday)"],
            "source_api": [.fr: "Banque du Canada (Valet)", .en: "Bank of Canada (Valet)"],
            "source_cache": [.fr: "Cache local (Valet)", .en: "Local cache (Valet)"],
            "rate_date": [.fr: "Date taux BdC", .en: "BoC rate date"],
            "cad_amount": [.fr: "Montant CAD", .en: "CAD amount"],
            "error": [.fr: "Erreur", .en: "Error"],
            "lang": [.fr: "Langue", .en: "Language"],
            "date_hint": [.fr: "AAAA-MM-JJ ou JJ/MM/AAAA", .en: "YYYY-MM-DD or DD/MM/YYYY"],
            "batch_hint": [
                .fr: "Formats : CSV, Excel (.xlsx), JSON, XML — colonnes : date, devise, montant, reference",
                .en: "Formats: CSV, Excel (.xlsx), JSON, XML — columns: date, devise, montant, reference"
            ],
            "no_rows": [
                .fr: "Importez ou glissez-déposez un fichier ici.",
                .en: "Import or drop a file here."
            ],
            "confirm_batch": [
                .fr: "Traiter %d ligne(s) via l'API Banque du Canada ?",
                .en: "Process %d row(s) via the Bank of Canada API?"
            ],
            "batch_done": [.fr: "Lot terminé : %d OK, %d erreur(s).", .en: "Batch done: %d OK, %d error(s)."],
            "fiche_title": [.fr: "ÉCRITURE — CONVERSION DEVISE", .en: "JOURNAL ENTRY — FX CONVERSION"],
            "tab_history": [.fr: "Historique", .en: "History"],
            "rate_mode": [.fr: "Type de taux", .en: "Rate type"],
            "mode_daily": [.fr: "Taux du jour", .en: "Daily rate"],
            "mode_monthly": [.fr: "Moyenne mensuelle", .en: "Monthly average"],
            "mode_annual": [.fr: "Moyenne annuelle", .en: "Annual average"],
            "month": [.fr: "Mois", .en: "Month"],
            "year": [.fr: "Année", .en: "Year"],
            "period": [.fr: "Période", .en: "Period"],
            "avg_detail": [.fr: "Taux moyen %@ (%d obs.)", .en: "Average rate %@ (%d obs.)"],
            "direction": [.fr: "Sens", .en: "Direction"],
            "converted_amount": [.fr: "Montant converti", .en: "Converted amount"],
            "copy_full": [.fr: "Fiche complète", .en: "Full summary"],
            "copy_amount_only": [.fr: "Montant converti seul", .en: "Converted amount only"],
            "copy_tsv": [.fr: "Ligne tabulée (Excel / journal)", .en: "Tab-separated row (Excel / journal)"],
            "search_placeholder": [.fr: "Rechercher (référence, devise, date)…", .en: "Search (reference, currency, date)…"],
            "export_txt": [.fr: "Exporter…", .en: "Export…"],
            "show_finder": [.fr: "Afficher dans le Finder", .en: "Show in Finder"],
            "no_history": [
                .fr: "Aucune conversion journalisée pour l'instant.",
                .en: "No logged conversions yet."
            ],
            "history_count": [.fr: "%d entrée(s)", .en: "%d entry(ies)"],
        ]
        let format = table[key]?[lang] ?? key
        if args.isEmpty { return format }
        return String(format: format, arguments: args)
    }
}
