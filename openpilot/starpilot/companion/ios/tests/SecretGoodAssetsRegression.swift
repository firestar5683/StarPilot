import Foundation
import CryptoKit

@main struct AssetRegression {
    @MainActor static func main() async throws {
        let manager = FileManager.default
        let root = manager.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try manager.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? manager.removeItem(at: root) }
        let suite = "secretgood-assets-" + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        final class Comma: @unchecked Sendable {
            var files = ["index.html": Data("<html>Galaxy</html>".utf8), "js/boot.js": Data("import './app.js'".utf8), "js/app.js": Data("const galaxy = true".utf8), "data/catalog.json": Data("{}".utf8), "sentry-push-worker.js": Data("self.addEventListener('push', () => {})".utf8)]
            var commit: String? = String(repeating: "a", count: 40)
            var fileCalls = 0
            var corrupt = false
            var manifestStatus = 200
            var networkFailure = false
            func listing() throws -> Data {
                let entries = files.map { ["path": $0.key, "size": $0.value.count, "sha256": GalaxyAssetManifest.digest($0.value)] as [String: Any] }
                return try JSONSerialization.data(withJSONObject: ["schema": 1, "commit": commit as Any, "files": entries])
            }
            func fetch(_ path: String, _ limit: Int) async throws -> (status: Int, data: Data) {
                if networkFailure { throw URLError(.notConnectedToInternet) }
                if path == "/api/companion/web-manifest" { return (manifestStatus, manifestStatus == 200 ? try listing() : Data()) }
                fileCalls += 1
                return (200, corrupt ? Data("wrong".utf8) : files[String(path.dropFirst())]!)
            }
        }
        let comma = Comma()
        let fetch: GalaxyPageFetch = { try await comma.fetch($0, $1) }
        let cache = root.appendingPathComponent("cache")
        let store = GalaxyAssetStore(cacheRoot: cache, defaults: defaults)
        precondition(store.readyRoot == nil && store.status == GalaxyAssetStore.notDownloaded, "No pages are bundled; nothing to open before the first Wi-Fi download")
        await store.check(fetch: fetch)
        precondition(store.readyRoot != nil && comma.fileCalls == 5)
        let savedApp = try Data(contentsOf: store.readyRoot!.appendingPathComponent("js/app.js"))
        precondition(savedApp == Data("const galaxy = true".utf8))
        let first = store.readyRoot
        await store.check(fetch: fetch)
        precondition(comma.fileCalls == 5 && store.status == "Galaxy matches comma.", "Unchanged files must not download twice")
        comma.files["js/app.js"] = Data("hand patched, same commit".utf8)
        await store.check(fetch: fetch)
        precondition(comma.fileCalls == 6 && store.readyRoot != first, "A changed file refreshes even when the commit is the same")
        let current = store.readyRoot
        let restored = GalaxyAssetStore(cacheRoot: cache, defaults: defaults)
        precondition(restored.readyRoot == current, "Saved pages must validate after restart so Bluetooth opens offline")
        precondition(!restored.olderThan(commit: comma.commit) && restored.olderThan(commit: String(repeating: "b", count: 40)), "Notice when comma moved on")
        precondition(!restored.olderThan(commit: nil))
        restored.noteCommaBuild(commit: String(repeating: "b", count: 40))
        precondition(restored.status.contains("older comma build"))

        comma.files["js/app.js"] = Data("changed app".utf8); comma.corrupt = true
        await store.check(fetch: fetch)
        precondition(store.readyRoot == current, "A failed update keeps the saved pages")
        precondition(store.status.contains("verification failed"), "Do not hide verification failures as network failures")
        comma.commit = String(repeating: "c", count: 40)
        await store.check(fetch: fetch)
        precondition(store.olderThan(commit: String(repeating: "c", count: 40)), "A failed download must not hide that comma moved on")
        comma.corrupt = false; comma.networkFailure = true
        await store.check(fetch: fetch)
        precondition(store.status.contains("network error -1009") && store.readyRoot == current)
        comma.networkFailure = false; comma.manifestStatus = 404
        await store.check(fetch: fetch)
        precondition(store.status.contains("too old") && store.readyRoot == current, "Older comma without the inventory route")
        comma.manifestStatus = 401
        let fresh = GalaxyAssetStore(cacheRoot: root.appendingPathComponent("empty"), defaults: UserDefaults(suiteName: UUID().uuidString)!)
        await fresh.check(fetch: fetch)
        precondition(fresh.readyRoot == nil && fresh.status.contains("too old") && fresh.status.contains("No Galaxy screens are saved yet."))
        comma.manifestStatus = 200; comma.corrupt = true
        await fresh.check(fetch: fetch)
        precondition(fresh.readyRoot == nil, "Pages that fail their hash are never activated")

        try Data("tampered".utf8).write(to: current!.appendingPathComponent("js/app.js"))
        let tampered = GalaxyAssetStore(cacheRoot: cache, defaults: defaults)
        precondition(tampered.readyRoot == nil, "Reject altered saved UI")

        comma.corrupt = false; comma.commit = nil
        let custom = GalaxyAssetStore(cacheRoot: root.appendingPathComponent("custom"), defaults: UserDefaults(suiteName: UUID().uuidString)!)
        comma.files["js/custom-branch-only.js"] = Data("export default 1".utf8)
        await custom.check(fetch: fetch)
        precondition(custom.readyRoot != nil, "Custom and unpushed builds work because nothing comes from GitHub")
        let switched = GalaxyAssetStore(cacheRoot: root.appendingPathComponent("switched"), defaults: UserDefaults(suiteName: UUID().uuidString)!)
        await switched.check(fetch: fetch, stillCurrent: { false })
        precondition(switched.readyRoot == nil, "A switched comma must not activate its download")
        print("SecretGood assets: comma LAN download, hash verification, atomic update and saved UI validation passed")
    }
}
