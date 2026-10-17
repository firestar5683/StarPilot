import Foundation

struct BridgeResponse { let status: Int; let bodyData: Data }
enum Wire { static let maxBody = 1_048_576 }
enum BridgeError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let text) = self { return text }; return nil }
}

@MainActor final class ScriptedComma: GalaxyRequestTransport {
    var connected = true
    var statuses: [[String: Any]]
    var actionStatus = 200
    var posts: [[String: Any]] = []
    init(_ statuses: [[String: Any]]) { self.statuses = statuses }
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        if method == "POST" {
            precondition(path == "/api/bluetooth/action" && headers["Content-Type"] == "application/json")
            let payload = try JSONSerialization.jsonObject(with: body) as! [String: Any]
            posts.append(payload)
            return BridgeResponse(status: payload["operation"] as? String == "accept_pair" ? actionStatus : 200, bodyData: Data("{}".utf8))
        }
        precondition(path == "/api/bluetooth/status")
        let next = statuses.count > 1 ? statuses.removeFirst() : statuses[0]
        return BridgeResponse(status: 200, bodyData: try JSONSerialization.data(withJSONObject: next))
    }
}

func snapshot(address: String = "AA:BB:CC:DD:EE:FF", pairing: [String: Any]? = nil) -> [String: Any] {
    var value: [String: Any] = ["adapterAddress": address, "adapterName": "comma", "pairing": NSNull()]
    if let pairing { value["pairing"] = pairing }
    return value
}

func prompt(kind: String = "confirmation", displayOnly: Bool = false) -> [String: Any] {
    ["id": String(repeating: "a", count: 32), "kind": kind, "value": "123456", "displayOnly": displayOnly]
}

@main struct AudioPairingRegression {
    @MainActor static func settle(_ model: AudioPairing, until done: (AudioPairing.Phase) -> Bool) async {
        for _ in 0..<2000 {
            if done(model.phase) { return }
            await Task.yield()
        }
        preconditionFailure("Audio pairing never reached the expected phase: \(model.phase)")
    }

    @MainActor static func main() async {
        // Parsing ignores any pairing that is not the phone window, and rejects bad addresses.
        precondition(AudioPairing.parse(Data("{\"adapterAddress\":\"AA:BB:CC:DD:EE:FF\",\"pairing\":{\"state\":\"pairing\",\"prompt\":null}}".utf8))?.state == nil)
        precondition(AudioPairing.validAddress("AA:BB:CC:DD:EE:FF") && !AudioPairing.validAddress("AA:BB") && !AudioPairing.validAddress(""))

        // Happy path: window opens, code appears, approval is sent, comma reports paired.
        let waiting: [String: Any] = ["incoming": true, "state": "pairing", "address": "", "name": "", "prompt": NSNull()]
        let asking: [String: Any] = ["incoming": true, "state": "pairing", "address": "11:22:33:44:55:66", "name": "iPhone", "prompt": prompt()]
        let paired: [String: Any] = ["incoming": true, "state": "paired", "address": "11:22:33:44:55:66", "name": "iPhone", "prompt": NSNull()]
        let comma = ScriptedComma([snapshot(), snapshot(pairing: waiting), snapshot(pairing: asking), snapshot(pairing: asking), snapshot(pairing: paired)])
        let model = AudioPairing(transport: { comma }, pause: { await Task.yield() })
        model.start()
        await settle(model) { if case .confirm = $0 { return true }; return false }
        guard case .confirm(let code, _, let name) = model.phase else { preconditionFailure() }
        precondition(code == "123456" && name == "comma")
        model.respond(accepted: true)
        await settle(model) { $0 == .done }
        precondition(comma.posts.first?["operation"] as? String == "accept_pair")
        precondition(comma.posts.contains { $0["operation"] as? String == "pairing_response" && $0["accepted"] as? Bool == true })

        // Older comma: no adapter address means no window and no message.
        let old = ScriptedComma([["pairing": NSNull()]])
        let oldModel = AudioPairing(transport: { old }, pause: { await Task.yield() })
        oldModel.start()
        await settle(oldModel) { $0 == .idle }
        precondition(old.posts.isEmpty)
        let unsupported = ScriptedComma([snapshot()]); unsupported.actionStatus = 400
        let unsupportedModel = AudioPairing(transport: { unsupported }, pause: { await Task.yield() })
        unsupportedModel.start()
        await settle(unsupportedModel) { $0 == .idle && !unsupported.posts.isEmpty }

        // Busy comma explains itself; display-only and non-confirmation prompts are never approved.
        let busy = ScriptedComma([snapshot()]); busy.actionStatus = 409
        let busyModel = AudioPairing(transport: { busy }, pause: { await Task.yield() })
        busyModel.start()
        await settle(busyModel) { if case .message(let text) = $0 { return text.contains("busy") }; return false }
        let quiet: [String: Any] = ["incoming": true, "state": "pairing", "address": "", "name": "", "prompt": prompt(kind: "authorization")]
        let failed: [String: Any] = ["incoming": true, "state": "failed", "address": "", "name": "", "prompt": NSNull()]
        let careful = ScriptedComma([snapshot(), snapshot(pairing: quiet), snapshot(pairing: failed)])
        let carefulModel = AudioPairing(transport: { careful }, pause: { await Task.yield() })
        carefulModel.start()
        await settle(carefulModel) { if case .message = $0 { return true }; return false }
        precondition(!careful.posts.contains { $0["operation"] as? String == "pairing_response" })

        // Closing the sheet mid-window cancels it on comma.
        let hanging = ScriptedComma([snapshot(), snapshot(pairing: waiting)])
        let hangingModel = AudioPairing(transport: { hanging }, attempts: 100000, pause: { await Task.yield() })
        hangingModel.start()
        await settle(hangingModel) { if case .waiting = $0 { return true }; return false }
        hangingModel.dismiss()
        await settle(hangingModel) { $0 == .idle && hanging.posts.contains { $0["operation"] as? String == "cancel_pair" } }
        print("audio pairing ok")
    }
}
