import Foundation

enum CurrencyCatalog {
    /// ISO -> Valet series
    static let series: [String: String] = [
        "USD": "FXUSDCAD", "EUR": "FXEURCAD", "GBP": "FXGBPCAD", "CHF": "FXCHFCAD",
        "JPY": "FXJPYCAD", "AUD": "FXAUDCAD", "NZD": "FXNZDCAD", "CNY": "FXCNYCAD",
        "HKD": "FXHKDCAD", "MXN": "FXMXNCAD", "INR": "FXINRCAD", "KRW": "FXKRWCAD",
        "SGD": "FXSGDCAD", "SEK": "FXSEKCAD", "NOK": "FXNOKCAD", "BRL": "FXBRLCAD",
        "ZAR": "FXZARCAD", "TRY": "FXTRYCAD", "THB": "FXTHBCAD", "TWD": "FXTWDCAD",
        "MYR": "FXMYRCAD", "IDR": "FXIDRCAD", "VND": "FXVNDCAD", "PEN": "FXPENCAD",
        "SAR": "FXSARCAD", "RUB": "FXRUBCAD",
    ]

    static var codes: [String] { series.keys.sorted() }

    static func seriesId(for code: String) throws -> String {
        let c = code.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        if c == "CAD" { throw BoCError.invalidCurrency("CAD") }
        if let s = series[c] { return s }
        if c.count == 3, c.unicodeScalars.allSatisfy({ CharacterSet.letters.contains($0) }) {
            return "FX\(c)CAD"
        }
        throw BoCError.invalidCurrency(code)
    }
}

actor BoCRateService {
    static let shared = BoCRateService()
    private let lookbackDays = 14
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func fetchRate(currency: String, on requested: Date) async throws -> ExchangeRate {
        let series = try CurrencyCatalog.seriesId(for: currency)
        let ccy = currency.uppercased()
        let end = requested
        let start = Calendar(identifier: .gregorian).date(byAdding: .day, value: -lookbackDays, to: end)!
        let startISO = MoneyParsing.isoDate(start)
        let endISO = MoneyParsing.isoDate(end)
        let urlString = "https://www.bankofcanada.ca/valet/observations/\(series)/json?start_date=\(startISO)&end_date=\(endISO)"
        guard let url = URL(string: urlString) else { throw BoCError.network("URL invalide") }

        do {
            var request = URLRequest(url: url, timeoutInterval: 30)
            request.setValue("taux-bdc-swift/1.0", forHTTPHeaderField: "User-Agent")
            let (data, response) = try await session.data(for: request)
            if let http = response as? HTTPURLResponse, http.statusCode == 404 {
                throw BoCError.network("Série Valet introuvable (404) pour \(series)")
            }
            let map = try parseObservations(data: data, series: series)
            if !map.isEmpty {
                let stringKeyed = Dictionary(uniqueKeysWithValues: map.map { (MoneyParsing.isoDate($0.key), $0.value) })
                RateCache.merge(series: series, observations: stringKeyed)
                if let resolved = resolve(map: map, requested: end, start: start) {
                    return ExchangeRate(
                        requestedDate: end,
                        rateDate: resolved.0,
                        rate: resolved.1,
                        series: series,
                        currency: ccy,
                        source: .api
                    )
                }
            }
        } catch let error as BoCError {
            // fall through to cache
            _ = error
        } catch {
            // fall through to cache
        }

        let cached = RateCache.observations(series: series)
        let dateMap = cached.reduce(into: [Date: Decimal]()) { acc, pair in
            if let d = try? MoneyParsing.parseDate(pair.key) {
                acc[d] = pair.value
            }
        }
        if let resolved = resolve(map: dateMap, requested: end, start: start) {
            return ExchangeRate(
                requestedDate: end,
                rateDate: resolved.0,
                rate: resolved.1,
                series: series,
                currency: ccy,
                source: .cache
            )
        }

        throw BoCError.noRate("Aucun taux \(series) entre \(startISO) et \(endISO)")
    }

    func convert(amount: Decimal, rate: Decimal) -> Decimal {
        var product = amount * rate
        var rounded = Decimal()
        NSDecimalRound(&rounded, &product, 2, .plain)
        return rounded
    }

    func convertAndLog(
        currency: String,
        dateText: String,
        amountText: String,
        reference: String,
        lang: AppLang
    ) async throws -> ConversionResult {
        let date = try MoneyParsing.parseDate(dateText)
        let amount = try MoneyParsing.parseAmount(amountText)
        let rate = try await fetchRate(currency: currency, on: date)
        let cad = convert(amount: amount, rate: rate.rate)
        AuditLog.append(
            lang: lang,
            reference: reference,
            requestedDate: MoneyParsing.isoDate(rate.requestedDate),
            rateDate: MoneyParsing.isoDate(rate.rateDate),
            rate: rate.rate,
            currency: rate.currency,
            amount: amount,
            cad: cad,
            sourceLabel: rate.sourceLabel(lang: lang)
        )
        return ConversionResult(rate: rate, amount: amount, cad: cad, reference: reference)
    }

    private func parseObservations(data: Data, series: String) throws -> [Date: Decimal] {
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let observations = json["observations"] as? [[String: Any]]
        else { return [:] }

        var map: [Date: Decimal] = [:]
        for obs in observations {
            guard let day = obs["d"] as? String,
                  let cell = obs[series] as? [String: Any],
                  let raw = cell["v"] as? String,
                  let value = Decimal(string: raw),
                  let date = try? MoneyParsing.parseDate(day)
            else { continue }
            map[date] = value
        }
        return map
    }

    private func resolve(map: [Date: Decimal], requested: Date, start: Date) -> (Date, Decimal)? {
        var cursor = requested
        let cal = Calendar(identifier: .gregorian)
        while cursor >= start {
            if let v = map[cursor] { return (cursor, v) }
            guard let prev = cal.date(byAdding: .day, value: -1, to: cursor) else { break }
            cursor = prev
        }
        return nil
    }
}
