import Foundation

enum AppDataPaths {
    /// Prefer <app_parent>/data ; fallback Application Support.
    static var directory: URL {
        if let preferred = preferredWritableDataDir() {
            return preferred
        }
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
            .appendingPathComponent("TauxBdC", isDirectory: true)
        try? FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
        return support
    }

    static var cacheFile: URL { directory.appendingPathComponent("cache_taux.json") }
    static var auditLog: URL { directory.appendingPathComponent("historique_conversions.log") }

    private static func preferredWritableDataDir() -> URL? {
        let candidates: [URL] = [
            Bundle.main.bundleURL.deletingLastPathComponent().appendingPathComponent("data", isDirectory: true),
            URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent("data", isDirectory: true),
        ]
        for url in candidates {
            do {
                try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
                let probe = url.appendingPathComponent(".write_test")
                try "ok".write(to: probe, atomically: true, encoding: .utf8)
                try FileManager.default.removeItem(at: probe)
                return url
            } catch {
                continue
            }
        }
        return nil
    }
}
