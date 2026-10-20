import Foundation

struct BridgeResponse { let status: Int; let bodyData: Data }
enum Wire { static let maxBody = 1_048_576 }
enum BridgeError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let text) = self { return text }; return nil }
}
@MainActor final class FakeTransport: GalaxyRequestTransport {
    var connected = true
    var session = "first"
    var clock = 0.0
    var calls = 0
    var waiting: [Int: CheckedContinuation<BridgeResponse, Error>] = [:]
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        calls += 1
        let index = calls
        return try await withCheckedThrowingContinuation { waiting[index] = $0 }
    }
    func reply(_ index: Int) {
        waiting.removeValue(forKey: index)!.resume(returning: BridgeResponse(status: 200, bodyData: Data("reply\(index)".utf8)))
    }
    func until(_ count: Int) async {
        for _ in 0..<1000 {
            if calls >= count { return }
            await Task.yield()
        }
        preconditionFailure("Request never reached transport")
    }
}
@main struct CacheRegression {
    @MainActor static func main() async throws {
        let transport = FakeTransport()
        let cache = GalaxyReadCache(transport: transport, sessionID: { transport.session }, now: { transport.clock })
        func read(_ path: String, method: String = "GET") -> Task<BridgeResponse, Error> {
            Task { try await cache.request(path: path, method: method, headers: [:], body: Data()) }
        }
        let page = "/api/settings/pages/hub"
        let first = read(page)
        await transport.until(1)
        let joined = read(page)
        for _ in 0..<10 { await Task.yield() }
        precondition(transport.calls == 1, "Concurrent page reads were duplicated")
        transport.reply(1)
        let a = try await first.value, b = try await joined.value
        precondition(a.bodyData == b.bodyData)
        let fresh = read(page)
        await transport.until(2); transport.reply(2); _ = try await fresh.value
        let stale = read(page)
        await transport.until(3)
        let mutation = read("/api/settings/confirm", method: "POST")
        await transport.until(4)
        transport.reply(3)
        do { _ = try await stale.value; preconditionFailure("Read from before mutation accepted") } catch {}
        transport.reply(4); _ = try await mutation.value
        let oldSession = read(page)
        await transport.until(5)
        transport.session = "second"; transport.reply(5)
        do { _ = try await oldSession.value; preconditionFailure("Old session read accepted") } catch {}
        let cancelled = read(page)
        await transport.until(6)
        let survivor = read(page)
        for _ in 0..<10 { await Task.yield() }
        cancelled.cancel(); transport.reply(6)
        do { _ = try await cancelled.value; preconditionFailure("Cancelled caller received result") } catch {}
        _ = try await survivor.value
        precondition(transport.calls == 6)
        let background = read("/api/system/monitor")
        await transport.until(7)
        let duplicate = read("/api/system/monitor")
        for _ in 0..<10 { await Task.yield() }
        precondition(transport.calls == 7, "Concurrent monitor reads must share one transfer")
        transport.reply(7)
        _ = try await background.value; _ = try await duplicate.value
        let nextSample = read("/api/system/monitor")
        await transport.until(8); transport.reply(8); _ = try await nextSample.value
        print("SecretGood page reads: coalescing, fresh tokens, writes, reconnects and cancellation passed")
    }
}
