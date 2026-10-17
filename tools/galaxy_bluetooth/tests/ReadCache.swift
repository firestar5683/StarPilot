import Foundation

@MainActor
final class ReadFixture: GalaxyRequestTransport {
    var connected = true
    var calls: [(String, String)] = []
    var revision = 0
    var status = 200

    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        calls.append((path, method))
        if method != "GET" { revision += 1 }
        let snapshot = revision
        if method == "GET" { try await Task.sleep(nanoseconds: 30_000_000) }
        return BridgeResponse(id: "test", session: "test", counter: 1, status: status,
                              headers: [:], body: Data(String(snapshot).utf8).base64EncodedString())
    }
}

@main
struct ReadCacheCheck {
    @MainActor
    static func main() async throws {
        let fixture = ReadFixture()
        var session = "one"
        var time: TimeInterval = 0
        let cache = GalaxyReadCache(transport: fixture, sessionID: { session }, now: { time })
        let catalog = "/assets/components/tools/device_settings_layout.json?v=settings-tier-1"
        @MainActor @Sendable func read(_ path: String = "/api/params/all", headers: [String: String] = [:]) async throws -> BridgeResponse {
            try await cache.request(path: path, method: "GET", headers: headers, body: Data())
        }
        func write() async throws {
            _ = try await cache.request(path: "/api/params", method: "PUT", headers: [:], body: Data("{}".utf8))
        }
        async let a = read(catalog)
        async let b = read(catalog)
        _ = try await (a, b)
        precondition(fixture.calls.count == 1)
        _ = try await read(catalog)
        precondition(fixture.calls.count == 1)

        _ = try await read()
        _ = try await read()
        precondition(fixture.calls.count == 3, "Current toggle values must never be cached")
        async let c = read()
        async let d = read()
        _ = try await (c, d)
        precondition(fixture.calls.count == 4)

        try await write()
        _ = try await read(catalog)
        precondition(fixture.calls.count == 6)
        time = 301
        _ = try await read(catalog)
        precondition(fixture.calls.count == 7)
        session = "two"
        _ = try await read(catalog)
        precondition(fixture.calls.count == 8)
        _ = try await read(catalog, headers: ["Range": "bytes=0-10"])
        precondition(fixture.calls.count == 9)

        session = "three"
        fixture.status = 500
        _ = try await read(catalog)
        _ = try await read(catalog)
        precondition(fixture.calls.count == 11, "Failed reads must not be cached")
        fixture.status = 200

        let beforeCancel = fixture.calls.count
        let cancelled = Task { try await read(catalog) }
        while fixture.calls.count == beforeCancel { await Task.yield() }
        let remaining = Task { try await read(catalog) }
        await Task.yield()
        cancelled.cancel()
        do { _ = try await cancelled.value; fatalError("Cancelled waiter succeeded") }
        catch is CancellationError {} catch { throw error }
        _ = try await remaining.value
        precondition(fixture.calls.count == beforeCancel + 1, "Cancelling one reader must preserve the shared read")

        session = "four"
        let beforeWrite = fixture.calls.count
        let oldRead = Task { try await read(catalog) }
        while fixture.calls.count == beforeWrite { await Task.yield() }
        try await write()
        let old = try await oldRead.value
        let fresh = try await read(catalog)
        precondition(old.body != fresh.body && fixture.calls.count == beforeWrite + 3,
                     "A read spanning a write must not populate the cache")
        try await write()
        try await write()
        precondition(fixture.calls.count == beforeWrite + 5, "Each write must be forwarded exactly once")
        print("Read cache: shared reads, fresh values, write/reconnect/TTL invalidation, errors and cancellation passed")
    }
}
