import Foundation
import CryptoKit

@main struct AssetRegression {
    @MainActor static func main() async throws {
        let manager = FileManager.default
        let root = manager.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try manager.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? manager.removeItem(at: root) }
        let bundled = root.appendingPathComponent("bundle")
        try manager.createDirectory(at: bundled, withIntermediateDirectories: true)
        let defaults = UserDefaults(suiteName: "secretgood-assets-" + UUID().uuidString)!
        defer { defaults.removeObject(forKey: "galaxy.secretgood.assets.manifest"); defaults.removeObject(forKey: "galaxy.secretgood.commit") }
        let commit = String(repeating: "a", count: 40)
        var files = ["index.html": Data("<html>Galaxy</html>".utf8), "js/boot.js": Data("import './app.js'".utf8), "js/app.js": Data("const galaxy = true".utf8), "data/catalog.json": Data("{}".utf8), "sentry-push-worker.js": Data("self.addEventListener('push', () => {})".utf8)]
        var rawCalls = 0
        var corrupt = false
        var httpStatus = 200
        var networkFailure = false
        func inventory() -> [[String: Any]] {
            files.map { path, data in
                let sha = Insecure.SHA1.hash(data: Data("blob \(data.count)\0".utf8) + data).map { String(format: "%02x", $0) }.joined()
                return ["path": GalaxyAssetStore.resourcePath + "/" + path, "sha": sha, "type": "blob", "size": data.count]
            }
        }
        let fetch: (URLRequest, Int) async throws -> (Data, HTTPURLResponse) = { request, _ in
            if networkFailure { throw URLError(.notConnectedToInternet) }
            let url = request.url!
            let data: Data
            if url.path.contains("/commits/") { data = try JSONSerialization.data(withJSONObject: ["sha": corrupt ? String(repeating: "b", count: 40) : commit]) }
            else if url.path.contains("/git/trees/") { data = try JSONSerialization.data(withJSONObject: ["truncated": false, "tree": inventory()]) }
            else {
                rawCalls += 1
                let path = url.path.components(separatedBy: GalaxyAssetStore.resourcePath + "/").last!
                data = corrupt ? Data("wrong".utf8) : files[path]!
            }
            return (data, HTTPURLResponse(url: url, statusCode: httpStatus, httpVersion: nil, headerFields: nil)!)
        }
        let cache = root.appendingPathComponent("cache")
        let store = GalaxyAssetStore(bundledRoot: bundled, cacheRoot: cache, defaults: defaults, fetch: fetch)
        await store.check()
        precondition(store.readyRoot != nil && rawCalls == 5)
        let first = store.readyRoot
        await store.check()
        precondition(rawCalls == 5, "Same revision must not download assets twice")
        let restored = GalaxyAssetStore(bundledRoot: bundled, cacheRoot: cache, defaults: defaults, fetch: fetch)
        precondition(restored.readyRoot == first, "Saved assets must validate after restart")
        files["js/app.js"] = Data("changed app".utf8); corrupt = true
        await store.check()
        precondition(store.readyRoot == first, "Corrupt update must preserve the last verified UI")
        precondition(store.status.contains("verification failed"), "Do not hide verification failures as network failures")
        httpStatus = 403
        await store.check()
        precondition(store.status.contains("HTTP 403") && store.readyRoot == first)
        httpStatus = 200; networkFailure = true
        await store.check()
        precondition(store.status.contains("network error -1009") && store.readyRoot == first)
        let offline = GalaxyAssetStore(bundledRoot: bundled, cacheRoot: root.appendingPathComponent("empty"), defaults: UserDefaults(suiteName: UUID().uuidString)!, fetch: fetch)
        await offline.check()
        precondition(offline.status.contains("included with this app"), "Bundled fallback must not be described as a saved update")
        try Data("tampered".utf8).write(to: first!.appendingPathComponent("js/app.js"))
        let tampered = GalaxyAssetStore(bundledRoot: bundled, cacheRoot: cache, defaults: defaults, fetch: fetch)
        precondition(tampered.readyRoot == nil, "Reject altered saved UI")
        print("SecretGood assets: Git object verification, atomic update fallback and saved UI validation passed")
    }
}
