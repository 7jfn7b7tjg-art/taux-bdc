import Foundation

/// Local Valet rate cache — JSON { "FXUSDCAD": { "2026-07-03": "1.4201" } }
enum RateCache {
    static func load() -> [String: [String: String]] {
        let url = AppDataPaths.cacheFile
        guard let data = try? Data(contentsOf: url),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: [String: String]]
        else { return [:] }
        return obj
    }

    static func save(_ cache: [String: [String: String]]) {
        guard let data = try? JSONSerialization.data(withJSONObject: cache, options: [.prettyPrinted, .sortedKeys]) else { return }
        try? data.write(to: AppDataPaths.cacheFile, options: .atomic)
    }

    static func merge(series: String, observations: [String: Decimal]) {
        var cache = load()
        var bucket = cache[series] ?? [:]
        for (day, rate) in observations {
            bucket[day] = NSDecimalNumber(decimal: rate).stringValue
        }
        cache[series] = bucket
        save(cache)
    }

    static func observations(series: String) -> [String: Decimal] {
        let bucket = load()[series] ?? [:]
        var result: [String: Decimal] = [:]
        for (day, raw) in bucket {
            if let d = Decimal(string: raw) {
                result[day] = d
            }
        }
        return result
    }
}
