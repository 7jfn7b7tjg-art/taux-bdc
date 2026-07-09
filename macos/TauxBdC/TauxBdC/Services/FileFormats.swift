import Foundation

/// Import / export multi-formats pour l'onglet Lots.
/// Import : .csv .xlsx .json .xml — Export : .csv .json .xml
enum FileFormats {

    // MARK: - Entrées publiques

    static func importRows(from url: URL) throws -> [BatchRow] {
        switch url.pathExtension.lowercased() {
        case "csv", "txt":
            let text = try String(contentsOf: url, encoding: .utf8)
            return try CSVBatch.parse(text)
        case "xlsx", "xlsm":
            return try importXLSX(url)
        case "json":
            let data = try Data(contentsOf: url)
            return try importJSON(data)
        case "xml":
            let data = try Data(contentsOf: url)
            return try importXML(data)
        default:
            throw BoCError.network(
                "Format non supporté : .\(url.pathExtension). Utilisez CSV, XLSX, JSON ou XML."
            )
        }
    }

    static func export(_ rows: [BatchRow], to url: URL, lang: AppLang) throws {
        switch url.pathExtension.lowercased() {
        case "csv":
            try CSVBatch.export(rows, lang: lang).write(to: url, atomically: true, encoding: .utf8)
        case "json":
            try exportJSON(rows, lang: lang).write(to: url, options: .atomic)
        case "xml":
            try exportXML(rows, lang: lang).write(to: url, atomically: true, encoding: .utf8)
        default:
            throw BoCError.network(
                "Format d'export non supporté : .\(url.pathExtension). Utilisez CSV, JSON ou XML."
            )
        }
    }

    // MARK: - Construction de ligne (partagée xlsx/json/xml)

    private static func makeRow(rawDate: String, rawCcy: String, rawAmt: String, ref: String) -> BatchRow {
        var row = BatchRow(
            rawDate: rawDate,
            currency: rawCcy.uppercased(),
            rawAmount: rawAmt,
            reference: ref
        )
        do {
            guard !rawDate.isEmpty, !rawCcy.isEmpty, !rawAmt.isEmpty else {
                throw BoCError.network("date, devise et montant sont requis.")
            }
            row.requestedDate = try MoneyParsing.parseDate(rawDate)
            row.amount = try MoneyParsing.parseAmount(rawAmt)
        } catch {
            row.error = error.localizedDescription
        }
        return row
    }

    private static func normalizeKey(_ key: String) -> String {
        key.trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
            .replacingOccurrences(of: " ", with: "_")
            .replacingOccurrences(of: "-", with: "_")
    }

    /// Alias d'en-têtes / clés acceptés (mêmes que CSV).
    private static func canonicalKey(_ key: String) -> String? {
        switch normalizeKey(key) {
        case "date", "date_transaction", "transaction_date": return "date"
        case "devise", "currency", "ccy": return "devise"
        case "montant", "amount": return "montant"
        case "reference", "ref", "memo": return "reference"
        default: return nil
        }
    }

    // MARK: - JSON

    private static func importJSON(_ data: Data) throws -> [BatchRow] {
        guard let parsed = try? JSONSerialization.jsonObject(with: data),
              let array = parsed as? [[String: Any]]
        else {
            throw BoCError.network(
                "JSON invalide : attendu un tableau d'objets {date, devise, montant, reference}."
            )
        }
        return array.map { obj in
            var fields: [String: String] = [:]
            for (key, value) in obj {
                guard let canon = canonicalKey(key) else { continue }
                // Nombre JSON → texte (jamais de Double intermédiaire côté Decimal)
                if let number = value as? NSNumber {
                    fields[canon] = number.stringValue
                } else if let str = value as? String {
                    fields[canon] = str.trimmingCharacters(in: .whitespacesAndNewlines)
                }
            }
            return makeRow(
                rawDate: fields["date"] ?? "",
                rawCcy: fields["devise"] ?? "",
                rawAmt: fields["montant"] ?? "",
                ref: fields["reference"] ?? ""
            )
        }
    }

    private static func exportJSON(_ rows: [BatchRow], lang: AppLang) throws -> Data {
        let yes = lang == .fr ? "oui" : "yes"
        let no = lang == .fr ? "non" : "no"
        let objects: [[String: String]] = rows.map { r in
            [
                "date": r.requestedDate.map(MoneyParsing.isoDate) ?? r.rawDate,
                "devise": r.currency,
                "montant": r.amount.map { NSDecimalNumber(decimal: $0).stringValue } ?? r.rawAmount,
                "reference": r.reference,
                "date_taux": r.rateDate.map(MoneyParsing.isoDate) ?? "",
                "taux": r.rate.map { NSDecimalNumber(decimal: $0).stringValue } ?? "",
                "montant_cad": r.cad.map { NSDecimalNumber(decimal: $0).stringValue } ?? "",
                "serie": r.series,
                "ajuste": r.rate == nil ? "" : (r.adjusted ? yes : no),
                "erreur": r.error,
            ]
        }
        return try JSONSerialization.data(
            withJSONObject: objects,
            options: [.prettyPrinted, .sortedKeys]
        )
    }

    // MARK: - XML

    private static func importXML(_ data: Data) throws -> [BatchRow] {
        let parser = LotXMLParser()
        guard parser.parse(data) else {
            throw BoCError.network("XML invalide ou illisible.")
        }
        guard !parser.records.isEmpty else {
            throw BoCError.network(
                "Aucune écriture trouvée dans le XML (élément <ecriture> attendu)."
            )
        }
        return parser.records.map { fields in
            makeRow(
                rawDate: fields["date"] ?? "",
                rawCcy: fields["devise"] ?? "",
                rawAmt: fields["montant"] ?? "",
                ref: fields["reference"] ?? ""
            )
        }
    }

    private static func exportXML(_ rows: [BatchRow], lang: AppLang) -> String {
        let yes = lang == .fr ? "oui" : "yes"
        let no = lang == .fr ? "non" : "no"
        var out = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<lot>\n"
        for r in rows {
            let attrs: [(String, String)] = [
                ("date", r.requestedDate.map(MoneyParsing.isoDate) ?? r.rawDate),
                ("devise", r.currency),
                ("montant", r.amount.map { NSDecimalNumber(decimal: $0).stringValue } ?? r.rawAmount),
                ("reference", r.reference),
                ("date_taux", r.rateDate.map(MoneyParsing.isoDate) ?? ""),
                ("taux", r.rate.map { NSDecimalNumber(decimal: $0).stringValue } ?? ""),
                ("montant_cad", r.cad.map { NSDecimalNumber(decimal: $0).stringValue } ?? ""),
                ("serie", r.series),
                ("ajuste", r.rate == nil ? "" : (r.adjusted ? yes : no)),
                ("erreur", r.error),
            ]
            let rendered = attrs
                .map { "\($0.0)=\"\(escapeXML($0.1))\"" }
                .joined(separator: " ")
            out += "  <ecriture \(rendered)/>\n"
        }
        out += "</lot>\n"
        return out
    }

    private static func escapeXML(_ value: String) -> String {
        value
            .replacingOccurrences(of: "&", with: "&amp;")
            .replacingOccurrences(of: "<", with: "&lt;")
            .replacingOccurrences(of: ">", with: "&gt;")
            .replacingOccurrences(of: "\"", with: "&quot;")
            .replacingOccurrences(of: "'", with: "&apos;")
    }

    // MARK: - XLSX

    private static func importXLSX(_ url: URL) throws -> [BatchRow] {
        let fm = FileManager.default
        let workDir = fm.temporaryDirectory
            .appendingPathComponent("tauxbdc-xlsx-\(UUID().uuidString)", isDirectory: true)
        try fm.createDirectory(at: workDir, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: workDir) }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/unzip")
        process.arguments = ["-o", "-qq", url.path, "-d", workDir.path]
        process.standardOutput = Pipe()
        process.standardError = Pipe()
        try process.run()
        process.waitUntilExit()
        guard process.terminationStatus == 0 else {
            throw BoCError.network("Impossible d'ouvrir le fichier Excel (.xlsx).")
        }

        // Chaînes partagées (peut être absent)
        var sharedStrings: [String] = []
        let sharedURL = workDir.appendingPathComponent("xl/sharedStrings.xml")
        if let data = try? Data(contentsOf: sharedURL) {
            let sp = SharedStringsParser()
            if sp.parse(data) {
                sharedStrings = sp.strings
            }
        }

        let sheetURL = workDir.appendingPathComponent("xl/worksheets/sheet1.xml")
        guard let sheetData = try? Data(contentsOf: sheetURL) else {
            throw BoCError.network("Feuille Excel introuvable (xl/worksheets/sheet1.xml).")
        }
        let sheet = SheetParser(sharedStrings: sharedStrings)
        guard sheet.parse(sheetData) else {
            throw BoCError.network("Feuille Excel illisible.")
        }

        let rows = sheet.rows
        guard let headerRow = rows.first else { return [] }

        // Colonne (lettre) → clé canonique
        var mapping: [String: String] = [:]
        for (col, raw) in headerRow {
            if let canon = canonicalKey(raw) {
                mapping[col] = canon
            }
        }
        let needed = ["date", "devise", "montant"]
        let missing = needed.filter { !mapping.values.contains($0) }
        guard missing.isEmpty else {
            throw BoCError.network("Colonnes manquantes : \(missing.joined(separator: ", "))")
        }

        return rows.dropFirst().compactMap { cells in
            var fields: [String: String] = [:]
            for (col, value) in cells {
                if let canon = mapping[col] {
                    fields[canon] = value.trimmingCharacters(in: .whitespacesAndNewlines)
                }
            }
            let rawDate = normalizeExcelDate(fields["date"] ?? "")
            let rawCcy = fields["devise"] ?? ""
            let rawAmt = fields["montant"] ?? ""
            let ref = fields["reference"] ?? ""
            if rawDate.isEmpty && rawCcy.isEmpty && rawAmt.isEmpty { return nil }
            return makeRow(rawDate: rawDate, rawCcy: rawCcy, rawAmt: rawAmt, ref: ref)
        }
    }

    /// Excel stocke souvent les dates comme numéro de série (base 1899-12-30).
    private static func normalizeExcelDate(_ raw: String) -> String {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return trimmed }
        // Déjà une date texte ?
        if trimmed.contains("-") || trimmed.contains("/") { return trimmed }
        guard let serial = Double(trimmed), serial > 59, serial < 100_000 else { return trimmed }
        var comps = DateComponents()
        comps.year = 1899
        comps.month = 12
        comps.day = 30
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!
        guard let base = cal.date(from: comps),
              let date = cal.date(byAdding: .day, value: Int(serial), to: base)
        else { return trimmed }
        return MoneyParsing.isoDate(date)
    }
}

// MARK: - Parsers XML internes

/// Parse xl/sharedStrings.xml — concatène les runs <t> de chaque <si>.
private final class SharedStringsParser: NSObject, XMLParserDelegate {
    private(set) var strings: [String] = []
    private var current = ""
    private var inT = false
    private var inSI = false

    func parse(_ data: Data) -> Bool {
        let parser = XMLParser(data: data)
        parser.delegate = self
        return parser.parse()
    }

    func parser(_ parser: XMLParser, didStartElement name: String, namespaceURI: String?,
                qualifiedName: String?, attributes: [String: String] = [:]) {
        switch name {
        case "si":
            inSI = true
            current = ""
        case "t":
            inT = true
        default:
            break
        }
    }

    func parser(_ parser: XMLParser, foundCharacters string: String) {
        if inSI && inT { current += string }
    }

    func parser(_ parser: XMLParser, didEndElement name: String, namespaceURI: String?,
                qualifiedName: String?) {
        switch name {
        case "t":
            inT = false
        case "si":
            strings.append(current)
            inSI = false
        default:
            break
        }
    }
}

/// Parse xl/worksheets/sheet1.xml — lignes de cellules colonne → valeur texte.
private final class SheetParser: NSObject, XMLParserDelegate {
    private let sharedStrings: [String]
    private(set) var rows: [[String: String]] = []

    private var currentRow: [String: String] = [:]
    private var currentColumn = ""
    private var currentType = ""
    private var currentValue = ""
    private var capturing = false

    init(sharedStrings: [String]) {
        self.sharedStrings = sharedStrings
    }

    func parse(_ data: Data) -> Bool {
        let parser = XMLParser(data: data)
        parser.delegate = self
        return parser.parse()
    }

    func parser(_ parser: XMLParser, didStartElement name: String, namespaceURI: String?,
                qualifiedName: String?, attributes: [String: String] = [:]) {
        switch name {
        case "row":
            currentRow = [:]
        case "c":
            currentColumn = Self.columnLetters(attributes["r"] ?? "")
            currentType = attributes["t"] ?? ""
            currentValue = ""
        case "v", "t":
            capturing = true
        default:
            break
        }
    }

    func parser(_ parser: XMLParser, foundCharacters string: String) {
        if capturing { currentValue += string }
    }

    func parser(_ parser: XMLParser, didEndElement name: String, namespaceURI: String?,
                qualifiedName: String?) {
        switch name {
        case "v", "t":
            capturing = false
        case "c":
            guard !currentColumn.isEmpty else { break }
            var value = currentValue
            if currentType == "s", let index = Int(value), index >= 0, index < sharedStrings.count {
                value = sharedStrings[index]
            }
            if !value.isEmpty {
                currentRow[currentColumn] = value
            }
        case "row":
            if !currentRow.isEmpty {
                rows.append(currentRow)
            }
        default:
            break
        }
    }

    /// "B12" → "B"
    private static func columnLetters(_ ref: String) -> String {
        String(ref.prefix { $0.isLetter })
    }
}

/// Parse un lot XML : éléments <ecriture> (ou row/entry/record), attributs ou éléments enfants.
private final class LotXMLParser: NSObject, XMLParserDelegate {
    private(set) var records: [[String: String]] = []

    private static let recordNames: Set<String> = ["ecriture", "row", "entry", "record"]
    private var currentRecord: [String: String]?
    private var currentChildKey: String?
    private var currentChildValue = ""

    func parse(_ data: Data) -> Bool {
        let parser = XMLParser(data: data)
        parser.delegate = self
        return parser.parse()
    }

    func parser(_ parser: XMLParser, didStartElement name: String, namespaceURI: String?,
                qualifiedName: String?, attributes: [String: String] = [:]) {
        let lower = name.lowercased()
        if Self.recordNames.contains(lower) {
            var record: [String: String] = [:]
            for (key, value) in attributes {
                if let canon = Self.canonical(key) {
                    record[canon] = value
                }
            }
            currentRecord = record
        } else if currentRecord != nil, let canon = Self.canonical(name) {
            currentChildKey = canon
            currentChildValue = ""
        }
    }

    func parser(_ parser: XMLParser, foundCharacters string: String) {
        if currentChildKey != nil { currentChildValue += string }
    }

    func parser(_ parser: XMLParser, didEndElement name: String, namespaceURI: String?,
                qualifiedName: String?) {
        let lower = name.lowercased()
        if Self.recordNames.contains(lower) {
            if let record = currentRecord, !record.isEmpty {
                records.append(record)
            }
            currentRecord = nil
        } else if let key = currentChildKey, Self.canonical(name) == key {
            currentRecord?[key] = currentChildValue.trimmingCharacters(in: .whitespacesAndNewlines)
            currentChildKey = nil
        }
    }

    private static func canonical(_ key: String) -> String? {
        switch key.lowercased().replacingOccurrences(of: "-", with: "_") {
        case "date", "date_transaction", "transaction_date": return "date"
        case "devise", "currency", "ccy": return "devise"
        case "montant", "amount": return "montant"
        case "reference", "ref", "memo": return "reference"
        default: return nil
        }
    }
}
