import Foundation

enum AuditLog {
    /// Journalise une conversion dans le sens réel (devise → CAD ou CAD → devise).
    static func append(
        lang: AppLang,
        reference: String,
        requestedDate: String,
        rateDate: String,
        rate: Decimal,
        fromAmount: Decimal,
        fromCurrency: String,
        toAmount: Decimal,
        toCurrency: String,
        sourceLabel: String
    ) {
        let stamp = Self.timestamp()
        let rateStr = NSDecimalNumber(decimal: rate).stringValue
        let fromStr = NSDecimalNumber(decimal: fromAmount).stringValue
        let toStr = NSDecimalNumber(decimal: toAmount).stringValue
        let subject: String
        if reference.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            subject = "Conversion"
        } else if lang == .fr {
            subject = "Facture n° \(reference)"
        } else {
            subject = "Invoice #\(reference)"
        }

        let line: String
        if lang == .en {
            line = "[\(stamp)] \(subject) converted. Requested date: \(requestedDate). Rate applied: \(rateStr) (BoC date: \(rateDate)). Amount: \(fromStr) \(fromCurrency) → \(toStr) \(toCurrency). Source: \(sourceLabel)."
        } else {
            line = "[\(stamp)] \(subject) convertie. Date demandée: \(requestedDate). Taux appliqué: \(rateStr) (Date BdC: \(rateDate)). Montant: \(fromStr) \(fromCurrency) → \(toStr) \(toCurrency). Source: \(sourceLabel)."
        }

        let url = AppDataPaths.auditLog
        let data = (line + "\n").data(using: .utf8) ?? Data()
        if FileManager.default.fileExists(atPath: url.path) {
            if let handle = try? FileHandle(forWritingTo: url) {
                defer { try? handle.close() }
                _ = try? handle.seekToEnd()
                try? handle.write(contentsOf: data)
            }
        } else {
            try? data.write(to: url, options: .atomic)
        }
    }

    /// Lignes du journal, plus récentes en premier.
    static func readEntries() -> [String] {
        guard let text = try? String(contentsOf: AppDataPaths.auditLog, encoding: .utf8) else {
            return []
        }
        return text
            .split(separator: "\n", omittingEmptySubsequences: true)
            .map(String.init)
            .reversed()
    }

    private static func timestamp() -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd HH:mm:ss"
        return f.string(from: Date())
    }
}
