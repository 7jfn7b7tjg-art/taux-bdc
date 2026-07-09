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
        Self.multiply(amount, by: rate)
    }

    // MARK: - Helpers Decimal purs (testables hors réseau)

    /// devise → CAD, arrondi 2 décimales HALF_UP.
    static func multiply(_ amount: Decimal, by rate: Decimal) -> Decimal {
        var product = amount * rate
        var rounded = Decimal()
        NSDecimalRound(&rounded, &product, 2, .plain)
        return rounded
    }

    /// CAD → devise (division), arrondi 2 décimales HALF_UP.
    static func divide(_ amount: Decimal, by rate: Decimal) -> Decimal {
        var quotient = amount / rate
        var rounded = Decimal()
        NSDecimalRound(&rounded, &quotient, 2, .plain)
        return rounded
    }

    /// Moyenne Decimal pure, arrondie à `scale` décimales HALF_UP.
    static func average(_ values: [Decimal], scale: Int = 6) -> Decimal {
        guard !values.isEmpty else { return 0 }
        let sum = values.reduce(Decimal(0), +)
        var quotient = sum / Decimal(values.count)
        var rounded = Decimal()
        NSDecimalRound(&rounded, &quotient, scale, .plain)
        return rounded
    }

    // MARK: - Taux moyen mensuel / annuel

    func fetchAverageRate(currency: String, year: Int, month: Int?) async throws -> AverageRate {
        let series = try CurrencyCatalog.seriesId(for: currency)
        let ccy = currency.uppercased()
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(secondsFromGMT: 0)!

        var startComps = DateComponents()
        startComps.year = year
        startComps.month = month ?? 1
        startComps.day = 1
        guard let start = cal.date(from: startComps) else {
            throw BoCError.network("Période invalide.")
        }
        let end: Date
        if let month {
            var next = DateComponents()
            next.year = month == 12 ? year + 1 : year
            next.month = month == 12 ? 1 : month + 1
            next.day = 1
            end = cal.date(byAdding: .day, value: -1, to: cal.date(from: next)!)!
        } else {
            var dec = DateComponents()
            dec.year = year
            dec.month = 12
            dec.day = 31
            end = cal.date(from: dec)!
        }

        let today = Date()
        guard start <= today else {
            throw BoCError.noRate("Période future — aucun taux publié. / Future period — no rates published.")
        }
        let cappedEnd = min(end, today)

        let startISO = MoneyParsing.isoDate(start)
        let endISO = MoneyParsing.isoDate(cappedEnd)
        let urlString = "https://www.bankofcanada.ca/valet/observations/\(series)/json?start_date=\(startISO)&end_date=\(endISO)"
        guard let url = URL(string: urlString) else { throw BoCError.network("URL invalide") }

        var request = URLRequest(url: url, timeoutInterval: 30)
        request.setValue("taux-bdc-swift/1.0", forHTTPHeaderField: "User-Agent")
        let (data, response) = try await session.data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode == 404 {
            throw BoCError.network("Série Valet introuvable (404) pour \(series)")
        }
        let map = try parseObservations(data: data, series: series)
        guard !map.isEmpty else {
            throw BoCError.noRate("Aucune observation \(series) entre \(startISO) et \(endISO).")
        }
        let stringKeyed = Dictionary(uniqueKeysWithValues: map.map { (MoneyParsing.isoDate($0.key), $0.value) })
        RateCache.merge(series: series, observations: stringKeyed)

        let periodLabel = month.map { String(format: "%04d-%02d", year, $0) } ?? String(year)
        return AverageRate(
            periodLabel: periodLabel,
            rate: Self.average(Array(map.values)),
            observationCount: map.count,
            series: series,
            currency: ccy
        )
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
