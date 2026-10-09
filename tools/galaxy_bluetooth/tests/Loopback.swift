import Foundation
import CryptoKit

@MainActor
final class FixtureTransport: GalaxyRequestTransport {
    var connected = true
    var catalogSHA256: String?
    var received: [(String, String, Data)] = []
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        received.append((path, method, body))
        return BridgeResponse(id: "test", session: "test", counter: 1, status: 200,
                              headers: ["content-type": "application/json"], body: Data("{\"transport\":\"fixture\"}".utf8).base64EncodedString())
    }
}

@main
struct LoopbackCheck {
    @MainActor
    static func main() async throws {
        let transport = FixtureTransport()
        let server = LoopbackServer(transport: transport, webRoot: URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true))
        server.start()
        for _ in 0..<100 {
            if server.url != nil { break }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        guard let url = server.url else { fatalError("Loopback listener did not start: \(server.error)") }
        let session = URLSession(configuration: .ephemeral)
        let (html, rootResponse) = try await session.data(from: url)
        precondition((rootResponse as! HTTPURLResponse).statusCode == 200)
        precondition(String(decoding: html, as: UTF8.self).contains("galaxy-app"))
        let (_, moduleResponse) = try await session.data(from: url.appendingPathComponent("assets/mobile/js/app.js"))
        precondition((moduleResponse as! HTTPURLResponse).mimeType == "text/javascript")

        let catalogURL = URL(fileURLWithPath: CommandLine.arguments[1]).appendingPathComponent("assets/components/tools/device_settings_layout.json")
        let catalog = try Data(contentsOf: catalogURL)
        transport.catalogSHA256 = SHA256.hash(data: catalog).map { String(format: "%02x", $0) }.joined()
        var layoutRequest = URLRequest(url: URL(string: "assets/components/tools/device_settings_layout.json?v=settings-tier-1", relativeTo: url)!)
        let (_, protectedLayout) = try await session.data(for: layoutRequest)
        precondition((protectedLayout as! HTTPURLResponse).statusCode == 403 && transport.received.isEmpty)
        layoutRequest.setValue(server.localSecret, forHTTPHeaderField: "X-Galaxy-Local")
        let (localLayout, layoutResponse) = try await session.data(for: layoutRequest)
        precondition((layoutResponse as! HTTPURLResponse).statusCode == 200 && localLayout == catalog && transport.received.isEmpty)
        transport.catalogSHA256 = "changed"
        _ = try await session.data(for: layoutRequest)
        precondition(transport.received.count == 1)
        transport.received.removeAll()
        transport.connected = false
        let (_, offlineLayout) = try await session.data(for: layoutRequest)
        precondition((offlineLayout as! HTTPURLResponse).statusCode == 503 && transport.received.isEmpty)
        transport.connected = true

        var request = URLRequest(url: url.appendingPathComponent("api/params"))
        request.httpMethod = "PUT"
        request.httpBody = Data("{\"key\":\"Metric\",\"value\":true}".utf8)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let (_, rejected) = try await session.data(for: request)
        precondition((rejected as! HTTPURLResponse).statusCode == 403)
        precondition(transport.received.isEmpty)

        request.setValue(server.localSecret, forHTTPHeaderField: "X-Galaxy-Local")
        let (reply, accepted) = try await session.data(for: request)
        precondition((accepted as! HTTPURLResponse).statusCode == 200)
        precondition(String(decoding: reply, as: UTF8.self).contains("fixture"))
        precondition(transport.received.count == 1 && transport.received[0].0 == "/api/params"
                     && transport.received[0].1 == "PUT" && transport.received[0].2 == request.httpBody)

        request.setValue("https://evil.example", forHTTPHeaderField: "Origin")
        let (_, crossOrigin) = try await session.data(for: request)
        precondition((crossOrigin as! HTTPURLResponse).statusCode == 403 && transport.received.count == 1)
        request.setValue(nil, forHTTPHeaderField: "Origin")
        transport.connected = false
        let (_, disconnected) = try await session.data(for: request)
        precondition((disconnected as! HTTPURLResponse).statusCode == 503 && transport.received.count == 1)
        server.stop()
        session.invalidateAndCancel()
        print("Production loopback server: bundled UI/modules, API forwarding, app header, origin and disconnect checks passed")
    }
}
