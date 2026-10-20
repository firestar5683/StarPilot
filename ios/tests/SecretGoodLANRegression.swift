import Foundation

@MainActor final class Server {
    var calls: [URLRequest] = []
    var sessions = 0
    var expired = false
    var failWrite = false
    var corruptIdentity = false
    func load(_ request: URLRequest, _ limit: Int) async throws -> (Data, HTTPURLResponse) {
        calls.append(request)
        let path = request.url!.path
        var headers: [String: String] = [:]
        var status = 200
        var json: [String: Any] = [:]
        if path == "/api/auth/session" {
            sessions += 1
            let current = sessions
            try await Task.sleep(nanoseconds: 5_000_000)
            json = ["authenticated": true, "localAccess": true]
            headers["Set-Cookie"] = "galaxy_session=token\(current); HttpOnly; SameSite=Strict; Path=/; Max-Age=1800"
        } else {
            precondition(request.value(forHTTPHeaderField: "Cookie")?.hasPrefix("galaxy_session=token") == true)
            if path == "/data/runtime.json" {
                json = ["schemaVersion": 1, "monitor": "local", "instance": corruptIdentity ? "fedcba9876543210" : "0123456789abcdef"]
            } else if expired {
                expired = false; status = 401; json = ["error": "Refresh the local Galaxy session"]
            } else if failWrite { throw URLError(.networkConnectionLost) }
            else { json = ["saved": true] }
        }
        return (try JSONSerialization.data(withJSONObject: json), HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: "HTTP/1.1", headerFields: headers)!)
    }
}

@main struct LANRegression {
    @MainActor static func main() async throws {
        let server = Server()
        let lan = LANTransport(load: server.load)
        try lan.configure(address: "192.168.1.86")
        lan.bind(to: "0123456789abcdef")
        let verified = await lan.probe()
        precondition(verified && server.sessions == 1)
        server.expired = true
        let result = try await lan.request(path: "/api/settings/confirm", method: "POST", headers: ["Cookie": "forged", "Origin": "http://evil.invalid"], body: Data("{}".utf8))
        precondition(result.status == 200 && server.sessions == 2)
        let writes = server.calls.filter { $0.httpMethod == "POST" }
        precondition(writes.count == 2, "Explicit session rejection must retry exactly once")
        precondition(writes.allSatisfy { $0.value(forHTTPHeaderField: "Origin") == "http://192.168.1.86:8082" && $0.value(forHTTPHeaderField: "Content-Type") == "application/json" })
        precondition(writes[0].value(forHTTPHeaderField: "Cookie") != writes[1].value(forHTTPHeaderField: "Cookie"))
        server.failWrite = true
        let before = server.calls.count
        do { _ = try await lan.request(path: "/api/settings/confirm", method: "POST", headers: [:], body: Data("{}".utf8)); preconditionFailure("Expected network error") } catch is URLError {}
        precondition(server.calls.count == before + 1, "Never retry an uncertain mutation")
        server.failWrite = false
        try lan.configure(address: "192.168.1.87")
        precondition(!lan.connected)
        _ = await lan.probe()
        precondition(server.sessions == 3, "A different comma must get a separate session")
        server.corruptIdentity = true
        let mismatched = await lan.probe()
        precondition(!mismatched, "Reject LAN endpoint that differs from authenticated BLE identity")
        for invalid in ["http://evil.invalid/api/x", "//evil.invalid/api/x", "/api/../x", "/api/%2e%2e/x", "/api/%252e/x", "/api/x#fragment", "/data/system-monitor.sample.json"] {
            precondition(!SecretGoodGalaxy.validTarget(invalid), invalid)
        }
        precondition(SecretGoodGalaxy.validTarget("/api/settings/pages/hub"))
        precondition(SecretGoodGalaxy.validTarget("/data/runtime.json"))
        precondition(SecretGoodGalaxy.needsWiFi("/api/cameras/snapshot"))
        precondition(!SecretGoodGalaxy.needsWiFi("/api/settings/pages/hub"))
        let concurrent = Server()
        let shared = LANTransport(load: concurrent.load)
        try shared.configure(address: "192.168.1.88")
        async let first = shared.probe()
        async let second = shared.probe()
        _ = await (first, second)
        precondition(concurrent.sessions == 1, "Share concurrent session handshakes")
        print("SecretGood LAN: cookies, refresh, mutation safety, identity and isolation passed")
    }
}
