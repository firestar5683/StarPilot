import Foundation

@MainActor final class OfflineTransport: GalaxyRequestTransport {
    var connected = false
    var calls = 0
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        calls += 1
        throw URLError(.notConnectedToInternet)
    }
}

@main struct LoopbackRecoveryRegression {
    @MainActor static func main() async throws {
        let transport = OfflineTransport()
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try Data("Galaxy test page".utf8).write(to: root.appendingPathComponent("index.html"))
        let source = try Data(contentsOf: URL(fileURLWithPath: "GalaxyBluetooth/Resources/Web/js/toggle-search.js"))
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
        print("Loopback recovery: real HTTP health, origin preservation, restart, stale callbacks, bounded retries and transport isolation passed")
    }
}
