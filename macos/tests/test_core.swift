import Foundation

// Harnais de tests du moteur (compilé par scripts/test_macos.sh, exécuté en CI).

var failures = 0

func check(_ condition: Bool, _ label: String) {
    if condition {
        print("  ok  \(label)")
    } else {
        failures += 1
        print("FAIL  \(label)")
    }
}

func decStr(_ d: Decimal) -> String {
    NSDecimalNumber(decimal: d).stringValue
}

@main
struct TestMain {
    static func main() throws {
        try testParseAmount()
        try testParseDate()
        testFormat()
        testMath()
        try testCSV()
        try testFileFormats()

        if failures > 0 {
            print("\n\(failures) test(s) FAILED")
            exit(1)
        }
        print("\nAll tests passed")
    }

    static func testParseAmount() throws {
        check(decStr(try MoneyParsing.parseAmount("1 500,00")) == "1500", "parseAmount FR espace+virgule")
        check(decStr(try MoneyParsing.parseAmount("1500.50")) == "1500.5", "parseAmount point")
        check(decStr(try MoneyParsing.parseAmount("1,234.56")) == "1234.56", "parseAmount EN milliers")
        check(decStr(try MoneyParsing.parseAmount("1.234,56")) == "1234.56", "parseAmount FR milliers")
        check((try? MoneyParsing.parseAmount("-5")) == nil, "parseAmount négatif rejeté")
        check((try? MoneyParsing.parseAmount("0")) == nil, "parseAmount zéro rejeté")
        check((try? MoneyParsing.parseAmount("abc")) == nil, "parseAmount texte rejeté")
        check((try? MoneyParsing.parseAmount("")) == nil, "parseAmount vide rejeté")
    }

    static func testParseDate() throws {
        let iso = try MoneyParsing.parseDate("2026-07-05")
        check(MoneyParsing.isoDate(iso) == "2026-07-05", "parseDate ISO")
        check(MoneyParsing.isoDate(try MoneyParsing.parseDate("05/07/2026")) == "2026-07-05", "parseDate JJ/MM/AAAA")
        check(MoneyParsing.isoDate(try MoneyParsing.parseDate("05-07-2026")) == "2026-07-05", "parseDate JJ-MM-AAAA")
        check(MoneyParsing.isoDate(try MoneyParsing.parseDate("2026/07/05")) == "2026-07-05", "parseDate AAAA/MM/JJ")
        check((try? MoneyParsing.parseDate("pas-une-date")) == nil, "parseDate invalide rejetée")
    }

    static func testFormat() {
        check(MoneyParsing.format(Decimal(string: "1500")!, decimals: 2, lang: .fr) == "1 500,00", "format FR")
        check(MoneyParsing.format(Decimal(string: "1500")!, decimals: 2, lang: .en) == "1,500.00", "format EN")
        check(MoneyParsing.format(Decimal(string: "1.4201")!, lang: .fr) == "1,4201", "format taux FR")
    }

    static func testMath() {
        check(decStr(BoCRateService.multiply(Decimal(1500), by: Decimal(string: "1.4201")!)) == "2130.15", "multiply 1500 × 1.4201")
        check(decStr(BoCRateService.divide(Decimal(string: "2130.15")!, by: Decimal(string: "1.4201")!)) == "1500", "divide 2130.15 ÷ 1.4201")
        check(decStr(BoCRateService.divide(Decimal(100), by: Decimal(3))) == "33.33", "divide arrondi 100 ÷ 3")
        check(decStr(BoCRateService.average([Decimal(string: "1.40")!, Decimal(string: "1.41")!, Decimal(string: "1.42")!])) == "1.41", "average exacte")
        check(decStr(BoCRateService.average([Decimal(string: "1.4201")!, Decimal(string: "1.4174")!])) == "1.41875", "average 2 obs")
    }

    static func testCSV() throws {
        let csv = """
        date,devise,montant,reference
        2026-07-05,USD,1500.00,FAC-123
        08/07/2026,EUR,"1000,50",FAC-124
        """
        let rows = try CSVBatch.parse(csv)
        check(rows.count == 2, "CSV parse 2 lignes")
        check(rows[0].currency == "USD" && decStr(rows[0].amount ?? 0) == "1500", "CSV ligne USD")
        check(decStr(rows[1].amount ?? 0) == "1000.5", "CSV virgule décimale")
        check(rows[1].requestedDate.map(MoneyParsing.isoDate) == "2026-07-08", "CSV date JJ/MM")

        let out = CSVBatch.export(rows, lang: .fr)
        check(out.contains("date_taux"), "CSV export en-têtes résultat")
        check(out.contains("FAC-123"), "CSV export contenu")
    }

    static func testFileFormats() throws {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("tauxbdc-tests-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }

        // JSON import (alias EN + montant numérique)
        let jsonURL = dir.appendingPathComponent("lot.json")
        try #"[{"date":"2026-07-05","devise":"USD","montant":"1500.00","reference":"A"},{"date":"08/07/2026","currency":"EUR","amount":1000.5,"ref":"B"}]"#
            .write(to: jsonURL, atomically: true, encoding: .utf8)
        let jsonRows = try FileFormats.importRows(from: jsonURL)
        check(jsonRows.count == 2 && jsonRows[1].currency == "EUR" && decStr(jsonRows[1].amount ?? 0) == "1000.5", "JSON import")

        // XML import (attributs + éléments enfants)
        let xmlURL = dir.appendingPathComponent("lot.xml")
        try """
        <?xml version="1.0"?>
        <lot>
          <ecriture date="2026-07-05" devise="USD" montant="1500.00" reference="A"/>
          <ecriture><date>08/07/2026</date><devise>EUR</devise><montant>1000,50</montant></ecriture>
        </lot>
        """.write(to: xmlURL, atomically: true, encoding: .utf8)
        let xmlRows = try FileFormats.importRows(from: xmlURL)
        check(xmlRows.count == 2 && decStr(xmlRows[1].amount ?? 0) == "1000.5", "XML import")

        // Export JSON / XML — précision du taux conservée en chaîne
        var row = BatchRow(rawDate: "2026-07-05", currency: "USD", rawAmount: "1500.00", reference: "A")
        row.requestedDate = try MoneyParsing.parseDate("2026-07-05")
        row.amount = Decimal(string: "1500.00")
        row.rateDate = try MoneyParsing.parseDate("2026-07-03")
        row.rate = Decimal(string: "1.4201")
        row.cad = Decimal(string: "2130.15")
        row.series = "FXUSDCAD"
        row.adjusted = true

        let outJSON = dir.appendingPathComponent("out.json")
        try FileFormats.export([row], to: outJSON, lang: .fr)
        let jsonText = try String(contentsOf: outJSON, encoding: .utf8)
        check(jsonText.contains("\"taux\" : \"1.4201\"") || jsonText.contains("\"taux\":\"1.4201\""), "JSON export taux en chaîne")

        let outXML = dir.appendingPathComponent("out.xml")
        try FileFormats.export([row], to: outXML, lang: .fr)
        let xmlText = try String(contentsOf: outXML, encoding: .utf8)
        check(xmlText.contains("taux=\"1.4201\"") && xmlText.contains("ajuste=\"oui\""), "XML export attributs")
    }
}
