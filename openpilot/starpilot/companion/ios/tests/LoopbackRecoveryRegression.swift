import Foundation

@MainActor final class OfflineTransport: GalaxyRequestTransport {
    var connected = false
    var calls = 0
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        calls += 1
        throw URLError(.notConnectedToInternet)
    }
}

@MainActor final class LiveTransport: GalaxyRequestTransport {
    var connected = true
    var pages: [String: Data] = ["/js/app.js": Data("live app".utf8), "/index.html": Data("live index".utf8)]
    var requested: [String] = []
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        throw URLError(.notConnectedToInternet)
    }
    func page(path: String) async throws -> BridgeResponse {
        requested.append(path)
        guard let data = pages[path] else { return BridgeResponse(id: "", session: "", counter: 0, status: 404, headers: [:], body: "") }
        return BridgeResponse(id: "", session: "", counter: 0, status: 200, headers: [:], body: data.base64EncodedString())
    }
}

@main struct LoopbackRecoveryRegression {
    @MainActor static func main() async throws {
        let transport = OfflineTransport()
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try Data("Galaxy test page".utf8).write(to: root.appendingPathComponent("index.html"))
        let source = try Data(contentsOf: URL(fileURLWithPath: "../../galaxy/web/js/toggle-search.js"))
        try FileManager.default.createDirectory(at: root.appendingPathComponent("js"), withIntermediateDirectories: true)
        let searchFile = root.appendingPathComponent("js/toggle-search.js")
        try source.write(to: searchFile)
        let server = LoopbackServer(transport: transport, webRoot: root)
        defer { server.stop() }
        let started = await server.ensureAvailable()
        precondition(started && server.url != nil)
        let first = server.url
        let (adaptedSearch, searchResponse) = try await BoundedHTTP.load(URLRequest(url: first!.appendingPathComponent("js/toggle-search.js")), limit: 1_048_576)
        precondition(searchResponse.statusCode == 200)
        precondition(String(data: adaptedSearch, encoding: .utf8)!.contains("Native Bluetooth search adapter v1"))
        let unchangedSearch = try Data(contentsOf: searchFile)
        precondition(unchangedSearch == source, "Saved assets must remain verified and unchanged")
        let healthy = await server.ensureAvailable()
        precondition(healthy && server.url == first, "Healthy foreground checks must retain the page origin")
        server.stop()
        precondition(server.url == nil && server.listenerState == "stopped")
        let restored = await server.ensureAvailable()
        precondition(restored && server.url != nil, "Stopped listeners must restart before page reload")
        // Let stale cancellation callbacks run; they must not clear the replacement.
        try await Task.sleep(nanoseconds: 100_000_000)
        precondition(server.url != nil && server.listenerState == "ready")
        precondition(transport.calls == 0, "Local recovery must not reconnect, write or probe comma")

        var probes = 0
        let stale = LoopbackServer(transport: transport, webRoot: root, probe: { _ in
            probes += 1
            return probes > 1
        })
        defer { stale.stop() }
        let repaired = await stale.ensureAvailable()
        precondition(repaired && probes == 2)
        precondition(stale.lifecycleEvents.contains(where: { $0.contains("restarting listener") }))
        precondition(stale.lifecycleEvents.contains(where: { $0.contains("recovery succeeded") }))

        let broken = LoopbackServer(transport: transport, webRoot: root, probe: { _ in false })
        defer { broken.stop() }
        async let a = broken.ensureAvailable()
        async let b = broken.ensureAvailable()
        let outcomes = await [a, b]
        precondition(outcomes.allSatisfy { !$0 } && broken.url == nil && !broken.error.isEmpty)
        precondition(broken.lifecycleEvents.filter { $0.contains("restarting listener") }.count == 1,
                     "Simultaneous retries must share one bounded recovery")
        // No saved copy: over Wi-Fi/LAN pages are read live from comma; otherwise the "not downloaded" message shows.
        let live = LiveTransport()
        let liveServer = LoopbackServer(transport: live, webRoot: nil)
        defer { liveServer.stop() }
        let liveStarted = await liveServer.ensureAvailable()
        precondition(liveStarted)
        let (app, appResponse) = try await BoundedHTTP.load(URLRequest(url: liveServer.url!.appendingPathComponent("js/app.js")), limit: 1_048_576)
        precondition(appResponse.statusCode == 200 && app == Data("live app".utf8))
        let (_, rootResponse) = try await BoundedHTTP.load(URLRequest(url: liveServer.url!), limit: 1_048_576)
        precondition(rootResponse.statusCode == 200 && live.requested.contains("/index.html"))
        let (_, missing) = try await BoundedHTTP.load(URLRequest(url: liveServer.url!.appendingPathComponent("js/missing.js")), limit: 1_048_576)
        precondition(missing.statusCode == 404)
        let (_, escaped) = try await BoundedHTTP.load(URLRequest(url: liveServer.url!.appendingPathComponent("other/secret.js")), limit: 1_048_576)
        precondition(escaped.statusCode == 503 && !live.requested.contains("/other/secret.js"), "Only Galaxy page files are read live")
        live.connected = false
        let (_, offline) = try await BoundedHTTP.load(URLRequest(url: liveServer.url!.appendingPathComponent("js/app.js")), limit: 1_048_576)
        precondition(offline.statusCode == 503)
        let bluetoothOnly = LoopbackServer(transport: transport, webRoot: nil)
        defer { bluetoothOnly.stop() }
        _ = await bluetoothOnly.ensureAvailable()
        transport.connected = true
        let (_, notYet) = try await BoundedHTTP.load(URLRequest(url: bluetoothOnly.url!.appendingPathComponent("js/app.js")), limit: 1_048_576)
        precondition(notYet.statusCode == 503, "Over Bluetooth with no saved copy there is nothing to serve")
        print("Loopback recovery: real HTTP health, origin preservation, restart, stale callbacks, bounded retries and transport isolation passed")
    }
}
