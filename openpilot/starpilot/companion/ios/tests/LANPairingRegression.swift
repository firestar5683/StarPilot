import Foundation

@MainActor final class FakeLAN: GalaxyRequestTransport {
    var connected = true
    var status = 200
    var requests: [(path: String, method: String, body: Data)] = []
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        requests.append((path, method, body))
        if status == -1 { throw URLError(.notConnectedToInternet) }
        return BridgeResponse(id: "", session: "", counter: 0, status: status, headers: [:], body: "")
    }
}

@main struct LANPairingRegression {
    @MainActor static func main() async throws {
        let lan = FakeLAN()
        let opened = await LANPairing.openWindow(over: lan)
        precondition(opened && lan.requests.count == 1)
        precondition(lan.requests[0].path == "/api/bluetooth/action" && lan.requests[0].method == "POST")
        precondition(lan.requests[0].body == Data("{\"operation\":\"accept_pair\"}".utf8))
        precondition(SecretGoodGalaxy.validTarget(LANPairing.windowPath), "The LAN transport must accept the window request")
        lan.status = 409
        let busy = await LANPairing.openWindow(over: lan)
        precondition(!busy, "A refused window falls back to the manual steps")
        lan.status = -1
        let offline = await LANPairing.openWindow(over: lan)
        precondition(!offline)
        lan.connected = false; lan.requests = []
        let disconnected = await LANPairing.openWindow(over: lan)
        precondition(!disconnected && lan.requests.isEmpty, "No Wi-Fi session means no request")
        print("LAN pairing: window opens over an existing Wi-Fi session and falls back to manual pairing otherwise")
    }
}
