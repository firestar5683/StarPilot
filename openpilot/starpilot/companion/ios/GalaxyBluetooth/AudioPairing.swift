import Foundation
#if os(iOS)
import AVFAudio
#endif

/// After this iPhone is paired for Galaxy, also pair it with comma for Bluetooth music.
/// iOS apps cannot start a classic Bluetooth pairing, so comma opens a short window and the
/// person taps comma in Settings → Bluetooth. Comma accepts only one phone and needs the code approved.
@MainActor
final class AudioPairing: ObservableObject {
    enum Phase: Equatable {
        case idle
        case opening
        case waiting(commaName: String)
        case confirm(code: String, promptID: String, commaName: String)
        case done
        case connected
        case message(String)
    }

    struct Snapshot: Equatable {
        var adapterAddress: String
        var adapterName: String
        var state: String?
        var promptID: String?
        var promptKind: String?
        var code: String
        var displayOnly: Bool
    }

    @Published private(set) var phase: Phase = .idle
    private let transport: () -> (any GalaxyRequestTransport)?
    private let pause: () async -> Void
    private let audioOutput: (String) -> Bool
    private let attempts: Int
    private var task: Task<Void, Never>?

    init(transport: @escaping () -> (any GalaxyRequestTransport)?, attempts: Int = 125,
         audioOutput: ((String) -> Bool)? = nil,
         pause: @escaping () async -> Void = { try? await Task.sleep(nanoseconds: 1_000_000_000) }) {
        self.transport = transport; self.attempts = attempts; self.pause = pause; self.audioOutput = audioOutput ?? { AudioPairing.isAudioOutput($0) }
    }

    static func isAudioOutput(_ commaName: String) -> Bool {
        #if os(iOS)
        return AVAudioSession.sharedInstance().currentRoute.outputs.contains {
            $0.portType == .bluetoothA2DP && $0.portName == commaName
        }
        #else
        return false
        #endif
    }

    var active: Bool { phase != .idle }

    nonisolated static func validAddress(_ value: String) -> Bool {
        value.range(of: "^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", options: .regularExpression) != nil
    }

    /// Only the window this phone opened counts; any other pairing belongs to someone else.
    nonisolated static func parse(_ data: Data) -> Snapshot? {
        guard let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        let pairing = (value["pairing"] as? [String: Any]).flatMap { ($0["incoming"] as? Bool) == true ? $0 : nil }
        let prompt = pairing?["prompt"] as? [String: Any]
        return Snapshot(adapterAddress: (value["adapterAddress"] as? String) ?? "", adapterName: (value["adapterName"] as? String) ?? "",
                        state: pairing?["state"] as? String, promptID: prompt?["id"] as? String, promptKind: prompt?["kind"] as? String,
                        code: (prompt?["value"] as? String) ?? "", displayOnly: (prompt?["displayOnly"] as? Bool) ?? false)
    }

    /// `windowOpen`: comma's pairing window is already open because the person just paired the app from comma's Pair phone.
    func start(windowOpen: Bool = false) {
        guard task == nil else { return }
        phase = .opening
        task = Task { [weak self] in
            await self?.run(windowOpen: windowOpen)
            self?.task = nil
        }
    }

    func respond(accepted: Bool) {
        guard case .confirm(_, let promptID, let name) = phase else { return }
        phase = .waiting(commaName: name)
        Task { [weak self] in
            guard let self else { return }
            _ = try? await self.post(["operation": "pairing_response", "promptId": promptID, "accepted": accepted])
        }
    }

    func cancel() {
        task?.cancel()
        task = nil
        let wasOpen = phase != .idle && phase != .done && phase != .connected
        phase = .idle
        if wasOpen { Task { [weak self] in _ = try? await self?.post(["operation": "cancel_pair"]) } }
    }

    func dismiss() { if case .message = phase { phase = .idle } else if phase == .done || phase == .connected { phase = .idle } else { cancel() } }

    private func post(_ payload: [String: Any]) async throws -> BridgeResponse? {
        guard let transport = transport(), transport.connected else { return nil }
        let body = try JSONSerialization.data(withJSONObject: payload)
        return try await transport.request(path: "/api/bluetooth/action", method: "POST",
                                           headers: ["Content-Type": "application/json"], body: body)
    }

    private func status() async -> Snapshot? {
        guard let transport = transport(), transport.connected,
              let response = try? await transport.request(path: "/api/bluetooth/status", method: "GET", headers: [:], body: Data()),
              response.status == 200 else { return nil }
        return Self.parse(response.bodyData)
    }

    private func run(windowOpen: Bool) async {
        guard let first = await status() else { phase = .message("Phone music wasn't set up. Connect to your comma and try again."); return }
        // An older comma reports no adapter address and has no pairing window.
        guard Self.validAddress(first.adapterAddress) else { phase = .idle; return }
        let name = first.adapterName.isEmpty ? "comma" : first.adapterName
        if audioOutput(name) { phase = .connected; return }
        if !windowOpen {
            let opened: BridgeResponse?
            do { opened = try await post(["operation": "accept_pair"]) } catch { opened = nil }
            switch opened?.status {
            case 200?: break
            case 400?: phase = .idle; return
            case 409?: phase = .message("Phone music wasn't set up because comma's Bluetooth is busy. Park, stop Android Auto pairing, then try Set up phone music again."); return
            default: phase = .message("Phone music wasn't set up. Try Set up phone music again."); return
            }
        }
        phase = .waiting(commaName: name)
        var answered: String?
        for _ in 0..<attempts {
            await pause()
            if Task.isCancelled { return }
            if audioOutput(name) { phase = .connected; return }
            guard let current = await status() else { continue }
            if let id = current.promptID, !current.displayOnly, current.promptKind == "confirmation", id != answered {
                answered = id
                phase = .confirm(code: current.code, promptID: id, commaName: name)
            }
            switch current.state {
            case "paired"?: phase = .done; return
            case "failed"?, "canceled"?:
                phase = .message("Phone music pairing didn't finish. Try Set up phone music again."); return
            default: break
            }
        }
        phase = .message("The pairing window closed. Try Set up phone music again.")
    }
}
