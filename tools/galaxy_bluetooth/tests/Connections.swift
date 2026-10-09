import Foundation

@MainActor
final class FakeRoute: GalaxyRequestTransport {
    var connected = true
    var calls: [String] = []
    var failure: Error?
    var status = 200
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        calls.append(method)
        if let failure { throw failure }
        return BridgeResponse(id: "test", session: "session", counter: 0, status: status, headers: [:], body: "")
    }
}
actor GitFixture {
    var map: [String: Data] = [:]
    var calls = 0
    func set(_ map: [String: Data]) { self.map = map }
    func fetch(_ request: URLRequest, _ limit: Int) throws -> (Data, HTTPURLResponse) {
        calls += 1
        guard let url = request.url, let data = map[url.lastPathComponent], data.count <= limit else { throw URLError(.notConnectedToInternet) }
        return (data, HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil, headerFields: [:])!)
    }
}
@main
struct Connections {
    @MainActor static func main() async throws {
        let lan = FakeRoute(), ble = FakeRoute()
        let router = PreferredTransport(lan: lan, bluetooth: ble, invalidateLAN: { lan.connected = false })
        func read() async throws -> BridgeResponse { try await router.request(path: "/api/params", method: "GET", headers: [:], body: Data()) }
        _ = try await read(); precondition(lan.calls.count == 1 && ble.calls.isEmpty)
        lan.failure = URLError(.networkConnectionLost)
        _ = try await read(); precondition(!lan.connected && ble.calls.count == 1)
        lan.connected = true
        do { _ = try await router.request(path: "/api/params", method: "PUT", headers: [:], body: Data([1])); fatalError("Write replayed") }
        catch { precondition(error.localizedDescription.contains("may have saved")) }
        precondition(ble.calls.count == 1 && lan.calls.last == "PUT")
        router.mode = .lan
        do { _ = try await read(); fatalError("Wi-Fi-only used BLE") } catch {}
        precondition(ble.calls.count == 1)
        router.mode = .bluetooth; lan.connected = true; lan.failure = nil
        _ = try await read(); precondition(ble.calls.count == 2)
        router.mode = .automatic; lan.status = 500
        let response = try await read(); precondition(response.status == 500 && ble.calls.count == 2)
        for address in ["127.0.0.1", "8.8.8.8", "192.168.10.85:8082", "https://example.com", "192.168.010.85", "192.168.1.256"] {
            do { _ = try LANTransport.endpoint(address); fatalError("Invalid LAN host accepted") } catch {}
        }
        _ = try LANTransport.endpoint("192.168.10.85")
        print("Routing: LAN priority, read fallback, no mutation replay, explicit modes, HTTP errors and private-address validation passed")

        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let bundle = root.appendingPathComponent("bundle"), cache = root.appendingPathComponent("cache")
        try FileManager.default.createDirectory(at: bundle, withIntermediateDirectories: true)
        let suite = "GalaxyTests." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let fixture = GitFixture()
        func release(_ text: String, corrupt: Bool = false) throws -> [String: Data] {
            let page = Data("<html>\(text)</html>".utf8), api = Data("export const version = '\(text)'".utf8)
            let manifest = GalaxyAssetManifest(schema: 1, nativeBridge: 1, files: [
                .init(path: "assets/mobile/index.html", sha256: GalaxyAssetManifest.digest(page), size: page.count),
                .init(path: "assets/mobile/js/api.js", sha256: GalaxyAssetManifest.digest(api), size: api.count)])
            let manifestData = try JSONEncoder().encode(manifest)
            return ["galaxy-bluetooth": Data("{\"sha\":\"\(String(repeating: "a", count: 40))\"}".utf8),
                    "galaxy-native-manifest.json": manifestData, "index.html": page, "api.js": corrupt ? Data("bad".utf8) : api]
        }
        let store = GalaxyAssetStore(bundledRoot: bundle, cacheRoot: cache, defaults: defaults, fetch: { try await fixture.fetch($0, $1) })
        await fixture.set(try release("one")); await store.check()
        guard let saved = store.readyRoot else { fatalError("Valid update not installed: \(store.status)") }
        let cached = GalaxyAssetStore(bundledRoot: bundle, cacheRoot: cache, defaults: defaults, fetch: { try await fixture.fetch($0, $1) })
        precondition(cached.readyRoot == saved)
        let initialCalls = await fixture.calls
        await store.check(); let unchangedCalls = await fixture.calls; precondition(unchangedCalls == initialCalls + 2)
        await fixture.set(try release("two", corrupt: true)); await store.check()
        precondition(store.readyRoot == saved && store.status.contains("saved"))
        store.inUseRoot = saved
        await fixture.set(try release("two")); await store.check()
        await fixture.set(try release("three")); await store.check()
        precondition(FileManager.default.fileExists(atPath: saved.appendingPathComponent("manifest.json").path))
        let newest = store.readyRoot
        await fixture.set([:]); await store.check(); precondition(store.readyRoot == newest)
        let cachedFiles = try FileManager.default.contentsOfDirectory(atPath: cache.path)
        precondition(cachedFiles.allSatisfy { !$0.hasPrefix("staging-") })
        let bad = GalaxyAssetManifest(schema: 1, nativeBridge: 1, files: [.init(path: "assets/../../outside", sha256: String(repeating: "a", count: 64), size: 1)])
        do { try bad.validate(); fatalError("Traversal manifest accepted") } catch {}
        try Data("corrupted".utf8).write(to: store.readyRoot!.appendingPathComponent("assets/mobile/js/api.js"))
        let broken = GalaxyAssetStore(bundledRoot: bundle, cacheRoot: cache, defaults: defaults, fetch: { try await fixture.fetch($0, $1) })
        precondition(broken.readyRoot == nil)
        print("GitHub assets: complete verified update, offline restart, unchanged fast check, failed update rollback, traversal and corruption rejection passed")
        if let base = ProcessInfo.processInfo.environment["GALAXY_HTTP_FIXTURE"], let url = URL(string: base) {
            var request = URLRequest(url: url.appendingPathComponent("redirect")); request.timeoutInterval = 3
            let (_, redirect) = try await BoundedHTTP.load(request, limit: 1024)
            precondition(redirect.statusCode == 302)
            for path in ["oversize", "unknown-size"] {
                request.url = url.appendingPathComponent(path)
                do { _ = try await BoundedHTTP.load(request, limit: 1024); fatalError("Oversized HTTP response accepted") } catch {}
            }
            request.url = url.appendingPathComponent("slow")
            let slowRequest = request
            let pending = Task { try await BoundedHTTP.load(slowRequest, limit: 1024) }
            try await Task.sleep(nanoseconds: 50_000_000); pending.cancel()
            do { _ = try await pending.value; fatalError("Cancelled HTTP request completed") }
            catch { precondition(error is CancellationError) }
            print("HTTP client: redirect rejection, declared/streamed size bounds and cancellation passed")
        }
        if CommandLine.arguments.count > 1 {
            let live = LANTransport(); try live.configure(address: CommandLine.arguments[1])
            let found = await live.probe(); precondition(found)
            let status = try await live.request(path: "/api/device/status", method: "GET", headers: [:], body: Data())
            precondition(status.status == 200)
            print("Actual comma: LAN health probe and read-only status request passed")
        }
    }
}
