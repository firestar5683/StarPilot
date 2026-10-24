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
        for address in ["192.168.10.85", "192.168.4.12", "172.20.10.3", "10.42.0.8"] { _ = try LANTransport.endpoint(address) }
        for ip in ["192.168.4.12", "172.20.10.3", "10.42.0.8"] {
            let status = try JSONSerialization.data(withJSONObject: ["lanIp": ip, "online": true])
            precondition(LANTransport.reportedAddress(status) == ip)
        }
        for status in ["{\"lanIp\":null}", "{\"lanIp\":\"8.8.8.8\"}", "{\"lanIp\":\"https://evil.example\"}", "not json"] {
            precondition(LANTransport.reportedAddress(Data(status.utf8)) == nil)
        }
        precondition(LANTransport.deviceID(Data("0123456789abcdef\n".utf8)) != nil)
        precondition(LANTransport.deviceID(Data("Unregistered".utf8)) == nil)
        precondition(LANTransport.deviceID(Data("other comma".utf8)) == nil)
        var parser = LANHTTPParser(limit: 128, headOnly: false)
        let packet = Data("HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Type: text/plain\r\n\r\n2\r\nhe\r\n3;test=yes\r\nllo\r\n0\r\n\r\n".utf8)
        var parsed: LocalResponse?
        for byte in packet { parsed = try parser.consume(Data([byte]), ended: false) }
        precondition(parsed?.body == Data("hello".utf8))
        for invalid in [
            "HTTP/1.1 200 OK\r\nContent-Length: 999\r\n\r\n",
            "HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\nx",
            "HTTP/1.1 200 OK\r\nContent-Length: 1\r\nTransfer-Encoding: chunked\r\n\r\n",
            "HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nx",
            "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n1\r\nxZZ",
            "HTTP/1.1 200 OK\r\nContent-Length: 1\r\n\r\nxx"] {
            var bad = LANHTTPParser(limit: 128, headOnly: false)
            do { _ = try bad.consume(Data(invalid.utf8), ended: true); fatalError("Malformed local HTTP accepted") } catch {}
        }
        var closed = LANHTTPParser(limit: 128, headOnly: false)
        let closeResult = try closed.consume(Data("HTTP/1.0 200 OK\r\n\r\nhello".utf8), ended: true)
        precondition(closeResult?.body == Data("hello".utf8))
        print("Local HTTP: incremental chunked/close framing, length bounds, ambiguous/truncated response rejection and hotspot/private IPs passed")
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
            let found = await live.probe(); guard found else { throw BridgeError.message("Live probe failed: " + live.status) }
            let status = try await live.request(path: "/api/device/status", method: "GET", headers: [:], body: Data())
            precondition(status.status == 200)
            let identity = try await live.request(path: "/api/params?key=DongleId", method: "GET", headers: [:], body: Data())
            if let value = LANTransport.deviceID(identity.bodyData) {
                live.bind(to: value == "0000000000000000" ? "1111111111111111" : "0000000000000000")
                let mismatch = await live.probe(); precondition(!mismatch)
                live.bind(to: value)
                let matched = await live.probe(); precondition(matched)
                print("Actual comma: mismatched LAN identity rejected; matching device accepted")
            }
            print("Actual comma: endpoint-scoped LAN health probe and read-only status request passed")
        }
    }
}
