import Foundation

enum CSVBatch {
    static let inputHeaders = ["date", "devise", "montant", "reference"]
    static let outputHeaders = [
        "date", "devise", "montant", "reference",
        "date_taux", "taux", "montant_cad", "serie", "ajuste", "erreur"
    ]

    static func parse(_ text: String) throws -> [BatchRow] {
        let lines = text
            .replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
            .split(separator: "\n", omittingEmptySubsequences: false)
            .map(String.init)
            .filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }
        guard let headerLine = lines.first else { return [] }
        let headers = splitCSVLine(headerLine).map { normalizeHeader($0) }
        guard let iDate = headers.firstIndex(of: "date"),
              let iCcy = headers.firstIndex(where: { $0 == "devise" || $0 == "currency" }),
              let iAmt = headers.firstIndex(where: { $0 == "montant" || $0 == "amount" })
        else {
            throw BoCError.network("Colonnes manquantes : date, devise, montant")
        }
        let iRef = headers.firstIndex(where: { $0 == "reference" || $0 == "ref" })

        var rows: [BatchRow] = []
        for line in lines.dropFirst() {
            let cols = splitCSVLine(line)
            func cell(_ idx: Int?) -> String {
                guard let idx, idx < cols.count else { return "" }
                return cols[idx].trimmingCharacters(in: .whitespacesAndNewlines)
            }
            let rawDate = cell(iDate)
            let rawCcy = cell(iCcy)
            let rawAmt = cell(iAmt)
            let ref = cell(iRef)
            var row = BatchRow(rawDate: rawDate, currency: rawCcy.uppercased(), rawAmount: rawAmt, reference: ref)
            do {
                row.requestedDate = try MoneyParsing.parseDate(rawDate)
                row.amount = try MoneyParsing.parseAmount(rawAmt)
                row.currency = rawCcy.uppercased()
            } catch {
                row.error = error.localizedDescription
            }
            rows.append(row)
        }
        return rows
    }

    static func export(_ rows: [BatchRow], lang: AppLang) -> String {
        var lines = [outputHeaders.joined(separator: ",")]
        let yes = lang == .fr ? "oui" : "yes"
        let no = lang == .fr ? "non" : "no"
        for r in rows {
            let date = r.requestedDate.map(MoneyParsing.isoDate) ?? r.rawDate
            let amt = r.amount.map { MoneyParsing.format($0, decimals: 2, lang: lang) } ?? r.rawAmount
            let rateDate = r.rateDate.map(MoneyParsing.isoDate) ?? ""
            let rate = r.rate.map { MoneyParsing.format($0, lang: lang) } ?? ""
            let cad = r.cad.map { MoneyParsing.format($0, decimals: 2, lang: lang) } ?? ""
            let adj = r.rate == nil ? "" : (r.adjusted ? yes : no)
            let fields = [
                date, r.currency, amt, r.reference,
                rateDate, rate, cad, r.series, adj, r.error
            ].map(escapeCSV)
            lines.append(fields.joined(separator: ","))
        }
        return lines.joined(separator: "\n") + "\n"
    }

    static func templateCSV() -> String {
        """
        date,devise,montant,reference
        2026-07-05,USD,1500.00,FAC-123
        08/07/2026,EUR,"1000,50",FAC-124
        """
    }

    private static func normalizeHeader(_ h: String) -> String {
        h.trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .replacingOccurrences(of: " ", with: "_")
            .replacingOccurrences(of: "-", with: "_")
    }

    private static func splitCSVLine(_ line: String) -> [String] {
        var result: [String] = []
        var current = ""
        var inQuotes = false
        for ch in line {
            if ch == "\"" {
                inQuotes.toggle()
                continue
            }
            if ch == "," && !inQuotes {
                result.append(current)
                current = ""
                continue
            }
            current.append(ch)
        }
        result.append(current)
        return result
    }

    private static func escapeCSV(_ value: String) -> String {
        if value.contains(",") || value.contains("\"") || value.contains("\n") {
            return "\"" + value.replacingOccurrences(of: "\"", with: "\"\"") + "\""
        }
        return value
    }
}
