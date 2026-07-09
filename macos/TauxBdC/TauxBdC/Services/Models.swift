import Foundation

enum MoneyParsing {
    static func parseDate(_ text: String) throws -> Date {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let formats = ["yyyy-MM-dd", "dd/MM/yyyy", "dd-MM-yyyy", "yyyy/MM/dd"]
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        for fmt in formats {
            formatter.dateFormat = fmt
            if let d = formatter.date(from: trimmed) { return d }
        }
        throw BoCError.invalidDate(trimmed)
    }

    static func parseAmount(_ text: String) throws -> Decimal {
        var cleaned = text.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "\u{00a0}", with: "")
            .replacingOccurrences(of: " ", with: "")
        // French "1.234,56" or "1234,56" vs English "1,234.56" / "1234.56"
        if cleaned.contains(",") && cleaned.contains(".") {
            if let lastComma = cleaned.lastIndex(of: ","),
               let lastDot = cleaned.lastIndex(of: "."),
               lastComma > lastDot {
                // 1.234,56 → remove dots, comma to dot
                cleaned = cleaned.replacingOccurrences(of: ".", with: "")
                    .replacingOccurrences(of: ",", with: ".")
            } else {
                // 1,234.56 → remove commas
                cleaned = cleaned.replacingOccurrences(of: ",", with: "")
            }
        } else if cleaned.contains(",") {
            cleaned = cleaned.replacingOccurrences(of: ",", with: ".")
        }
        guard !cleaned.isEmpty else { throw BoCError.invalidAmount(text) }
        guard let value = Decimal(string: cleaned), value > 0 else {
            throw BoCError.invalidAmount(text)
        }
        return value
    }

    static func isoDate(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0)
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }

    static func format(_ value: Decimal, decimals: Int? = nil, lang: AppLang) -> String {
        var v = value
        if let decimals {
            var rounded = Decimal()
            var copy = v
            NSDecimalRound(&rounded, &copy, decimals, .plain)
            v = rounded
        }
        let raw = NSDecimalNumber(decimal: v).stringValue
        let parts = raw.split(separator: ".", omittingEmptySubsequences: false)
        var intPart = String(parts[0])
        var frac = parts.count > 1 ? String(parts[1]) : ""
        // Decimal ne conserve pas les zéros finaux : compléter à `decimals` (1 500 → 1 500,00)
        if let decimals, decimals > 0, frac.count < decimals {
            frac += String(repeating: "0", count: decimals - frac.count)
        }
        var sign = ""
        if intPart.hasPrefix("-") {
            sign = "-"
            intPart.removeFirst()
        }
        var groups: [String] = []
        var rest = intPart
        while !rest.isEmpty {
            let start = rest.index(rest.endIndex, offsetBy: -min(3, rest.count))
            groups.insert(String(rest[start...]), at: 0)
            rest = String(rest[..<start])
        }
        let sepThousands = lang == .en ? "," : " "
        let sepDecimal = lang == .en ? "." : ","
        let joined = groups.joined(separator: sepThousands)
        if frac.isEmpty { return sign + joined }
        return sign + joined + sepDecimal + frac
    }
}

enum BoCError: LocalizedError {
    case invalidDate(String)
    case invalidAmount(String)
    case invalidCurrency(String)
    case network(String)
    case noRate(String)

    var errorDescription: String? {
        switch self {
        case .invalidDate(let s): return "Date invalide / Invalid date: \(s)"
        case .invalidAmount(let s): return "Montant invalide / Invalid amount: \(s)"
        case .invalidCurrency(let s): return "Devise invalide / Invalid currency: \(s)"
        case .network(let s): return s
        case .noRate(let s): return s
        }
    }
}

struct ExchangeRate: Equatable {
    let requestedDate: Date
    let rateDate: Date
    let rate: Decimal
    let series: String
    let currency: String
    let source: RateSource

    var isAdjusted: Bool { MoneyParsing.isoDate(requestedDate) != MoneyParsing.isoDate(rateDate) }

    func sourceLabel(lang: AppLang) -> String {
        let base = source == .cache
            ? L10n.t("source_cache", lang: lang)
            : L10n.t("source_api", lang: lang)
        return "\(base) / \(series)"
    }
}

enum RateSource: String {
    case api, cache
}

struct ConversionResult: Equatable {
    let rate: ExchangeRate
    let amount: Decimal
    let cad: Decimal
    let reference: String
}

/// Taux moyen d'une période (mensuel ou annuel) — moyenne des observations Valet.
struct AverageRate: Equatable {
    let periodLabel: String      // "2026-06" ou "2026"
    let rate: Decimal
    let observationCount: Int
    let series: String
    let currency: String
}

struct BatchRow: Identifiable, Equatable {
    let id: UUID
    var rawDate: String
    var currency: String
    var rawAmount: String
    var reference: String
    var requestedDate: Date?
    var amount: Decimal?
    var rateDate: Date?
    var rate: Decimal?
    var cad: Decimal?
    var series: String
    var adjusted: Bool
    var error: String

    init(
        id: UUID = UUID(),
        rawDate: String,
        currency: String,
        rawAmount: String,
        reference: String,
        requestedDate: Date? = nil,
        amount: Decimal? = nil,
        rateDate: Date? = nil,
        rate: Decimal? = nil,
        cad: Decimal? = nil,
        series: String = "",
        adjusted: Bool = false,
        error: String = ""
    ) {
        self.id = id
        self.rawDate = rawDate
        self.currency = currency
        self.rawAmount = rawAmount
        self.reference = reference
        self.requestedDate = requestedDate
        self.amount = amount
        self.rateDate = rateDate
        self.rate = rate
        self.cad = cad
        self.series = series
        self.adjusted = adjusted
        self.error = error
    }
}
