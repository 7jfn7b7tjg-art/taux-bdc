import Foundation

enum AuditLog {
    static func append(
        lang: AppLang,
        reference: String,
        requestedDate: String,
        rateDate: String,
        rate: Decimal,
        currency: String,
        amount: Decimal,
        cad: Decimal,
        sourceLabel: String
    ) {
        let stamp = Self.timestamp()
        let rateStr = NSDecimalNumber(decimal: rate).stringValue
        let amtStr = NSDecimalNumber(decimal: amount).stringValue
        let cadStr = NSDecimalNumber(decimal: cad).stringValue
        let subject: String
        if reference.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            subject = lang == .fr ? "Conversion" : "Conversion"
        } else if lang == .fr {
            subject = "Facture n° \(reference)"
        } else {
            subject = "Invoice #\(reference)"
        }

        let line: String
        if lang == .en {
            line = "[\(stamp)] \(subject) converted. Requested date: \(requestedDate). Rate applied: \(rateStr) (BoC date: \(rateDate)). Amount: \(amtStr) \(currency) → \(cadStr) CAD. Source: \(sourceLabel)."
        } else {
            line = "[\(stamp)] \(subject) convertie. Date demandée: \(requestedDate). Taux appliqué: \(rateStr) (Date BdC: \(rateDate)). Montant: \(amtStr) \(currency) → \(cadStr) CAD. Source: \(sourceLabel)."
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

    private static func timestamp() -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd HH:mm:ss"
        return f.string(from: Date())
    }
}
