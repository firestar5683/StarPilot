import SwiftUI
import CryptoKit
import UIKit
import ImageIO

struct DiagnosticMetric: Decodable, Identifiable {
    let name: String
    let value: Double?
    let unit: String
    var id: String { name }
    var display: String { value.map { String(format: "%.1f %@", $0, unit) } ?? "Not reported" }
}
struct DiagnosticSnapshot: Decodable {
    let ageSeconds: Double
    let engaged: Bool?
    let temperatures: [DiagnosticMetric]
    let rates: [DiagnosticMetric]
    let capture: CaptureStatus?
}

struct CaptureStatus: Codable {
    let hookAgeSeconds: Double?
    let frameAgeSeconds: Double?
    let queuedImages: Int?
    let captureError: String?
    let encoderError: String?
    let encoderStderr: String?
    let encoderExitCode: Int?
    let videoSize: [Int]?
    let encoderRunning: Bool?
}

@MainActor
final class CompanionDiagnostics: ObservableObject {
    @Published var snapshot: DiagnosticSnapshot?
    @Published var screen: UIImage?
    @Published var status = "Connect and pair with comma to read diagnostics." { didSet { record(status) } }
    @Published var screenStatus = "Live View uses local Wi-Fi." { didSet { record(screenStatus) } }
    @Published var live = true { didSet { if live { waitingSince = Date() } } }
    @Published var phoneVisible = false { didSet { if phoneVisible && !oldValue { waitingSince = Date(); copiedLog = false }; updateActivity() } }
    @Published var carPlayActive = false { didSet { updateActivity() } }
    @Published private(set) var receivedAt: Date?
    @Published private(set) var frameAt: Date?
    @Published var copiedLog = false
    var transport: PreferredTransport?
    var lan: LANTransport?
    var phoneActive = true { didSet { updateActivity() } }
    private var task: Task<Void, Never>?
    private var stream: LiveStream?
    private var streamHost = ""
    private var streamStarted = Date.distantPast
    private var streamGeneration = UUID()
    private var lastStreamAttempt = Date.distantPast
    private var frameCount = 0
    private var fpsStarted = Date()
    @Published private(set) var displayFPS = 0.0
    private var lastDiagnostics = Date.distantPast
    private var waitingSince = Date()
    private var events: [String] = []
    private var lastEvent = ""
    private var captureSample: CaptureStatus?
    private var captureSampleAt: Date?

    var canCopyLog: Bool {
        live && phoneVisible && !frameFresh && Date().timeIntervalSince(waitingSince) >= 10
    }
    private func record(_ message: String) {
        guard message != lastEvent else { return }
        lastEvent = message
        events.append("\(ISO8601DateFormatter().string(from: Date())) \(message.prefix(500))")
        if events.count > 30 { events.removeFirst(events.count - 30) }
    }
    func diagnosticLog() -> String {
        let info = Bundle.main.infoDictionary ?? [:]
        var lines = ["StarPilot Live diagnostics", ISO8601DateFormatter().string(from: Date()),
                     "App: \(info["CFBundleShortVersionString"] ?? "unknown") (\(info["CFBundleVersion"] ?? "unknown"))",
                     "iOS: \(UIDevice.current.systemVersion)",
                     "Connection: \(transport?.label ?? "Disconnected")",
                     "LAN connected: \(lan?.connected == true)",
                     "Telemetry: \(status)", "Stream: \(screenStatus)",
                     "No frame for: \(Int(Date().timeIntervalSince(waitingSince))) seconds"]
        if let captureSample, let captureSampleAt,
           let data = try? JSONEncoder().encode(captureSample), let text = String(data: data, encoding: .utf8) {
            lines.append("Capture sample age: \(Int(Date().timeIntervalSince(captureSampleAt))) seconds")
            lines.append("Comma capture: \(text)")
        } else { lines.append("Comma capture details unavailable; update the comma fork if telemetry is connected.") }
        lines.append("Recent events:")
        lines.append(contentsOf: events)
        return lines.joined(separator: "\n")
    }

    var fresh: Bool {
        guard let snapshot, let receivedAt, transport?.connected == true else { return false }
        return snapshot.ageSeconds + Date().timeIntervalSince(receivedAt) < 5
    }
    var frameFresh: Bool {
        guard let frameAt, lan?.connected == true else { return false }
        return Date().timeIntervalSince(frameAt) < 3
    }
    private func headers(_ path: String) throws -> [String: String] {
        let text = PairingKeyStore.load()
        guard text.count == 64 else { throw BridgeError.message("Pair this phone with comma before opening diagnostics.") }
        var bytes = Data()
        var index = text.startIndex
        while index < text.endIndex {
            let next = text.index(index, offsetBy: 2)
            guard let byte = UInt8(text[index..<next], radix: 16) else { throw BridgeError.message("Invalid pairing key.") }
            bytes.append(byte); index = next
        }
        let nonce = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        let signature = HMAC<SHA256>.authenticationCode(for: Data("\(nonce)\nGET\n\(path)".utf8), using: SymmetricKey(data: bytes))
        return ["X-Companion-Nonce": nonce, "X-Companion-MAC": signature.map { String(format: "%02x", $0) }.joined()]
    }
    private func updateActivity() {
        let active = carPlayActive || (phoneVisible && phoneActive)
        if !active { task?.cancel(); task = nil; stopStream(); return }
        guard task == nil else { return }
        task = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                await self.poll()
                do { try await Task.sleep(nanoseconds: 500_000_000) } catch { return }
            }
        }
    }
    private func poll() async {
        if Date().timeIntervalSince(lastDiagnostics) >= 2 {
            lastDiagnostics = Date()
            do {
                guard let transport else { return }
                let path = "/api/companion/diagnostics"
                let response = try await transport.request(path: path, method: "GET", headers: headers(path), body: Data())
                try Task.checkCancellation()
                guard response.status == 200 else { throw BridgeError.message(response.status == 403 ? "Enable diagnostics on comma and pair this phone." : "Waiting for comma telemetry.") }
                let sample = try JSONDecoder().decode(DiagnosticSnapshot.self, from: response.bodyData)
                guard sample.ageSeconds.isFinite, sample.ageSeconds >= 0 else { throw BridgeError.message("Invalid telemetry age.") }
                snapshot = sample; receivedAt = Date(); status = sample.ageSeconds < 5 ? "Connected · read only" : "Telemetry is outdated"
                if let capture = sample.capture { captureSample = capture; captureSampleAt = Date() }
            } catch { if !Task.isCancelled { status = error.localizedDescription; snapshot = nil; receivedAt = nil } }
        }
        guard live, phoneVisible, phoneActive else { stopStream(); return }
        guard let lan, lan.connected, let host = lan.endpoint?.host else {
            stopStream(); screenStatus = "Live View needs local Wi-Fi. Diagnostics also work over Bluetooth."; return
        }
        if stream != nil && streamHost != host { stopStream() }
        if let frameAt, Date().timeIntervalSince(frameAt) > 3 { stopStream() }
        if stream != nil, frameAt == nil, Date().timeIntervalSince(streamStarted) > 5 { stopStream() }
        guard stream == nil, Date().timeIntervalSince(lastStreamAttempt) >= 1 else { return }
        lastStreamAttempt = Date()
        do {
            let headers = try headers("/api/companion/stream")
            let generation = UUID(); streamGeneration = generation; streamHost = host
            fpsStarted = Date(); frameCount = 0
            let stream = LiveStream(host: host, headers: headers, frame: { [weak self] data in
                guard let source = CGImageSourceCreateWithData(data as CFData, nil),
                      let image = CGImageSourceCreateImageAtIndex(source, 0, [kCGImageSourceShouldCacheImmediately: true] as CFDictionary) else { return }
                let picture = UIImage(cgImage: image)
                Task { @MainActor in
                    guard let self, self.streamGeneration == generation else { return }
                    self.screen = picture; self.frameAt = Date(); self.frameCount += 1
                    self.waitingSince = Date()
                    let elapsed = Date().timeIntervalSince(self.fpsStarted)
                    if elapsed >= 1 {
                        self.displayFPS = Double(self.frameCount) / elapsed
                        self.frameCount = 0; self.fpsStarted = Date()
                    }
                    self.screenStatus = String(format: "Full comma display · %.1f FPS · Wi-Fi", self.displayFPS)
                }
            }, failure: { [weak self] message in
                Task { @MainActor in
                    guard let self, self.streamGeneration == generation else { return }
                    self.stopStream(); self.screenStatus = message
                }
            })
            streamStarted = Date(); self.stream = stream; stream.start()
            screenStatus = "Connecting live stream…"
        } catch { screenStatus = error.localizedDescription }

    }
    private func stopStream() {
        streamGeneration = UUID(); stream?.stop(); stream = nil
        screen = nil; frameAt = nil; displayFPS = 0
    }
}

struct CompanionView: View {
    @ObservedObject var diagnostics: CompanionDiagnostics
    private let purple = Color(red: 0.55, green: 0.36, blue: 0.96)
    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { _ in
            if diagnostics.live { liveView } else { diagnosticView }
        }
        .background(Color.black)
        .onAppear { diagnostics.phoneVisible = true; UIApplication.shared.isIdleTimerDisabled = diagnostics.live }
        .onChange(of: diagnostics.live) { _, live in UIApplication.shared.isIdleTimerDisabled = live }
        .onDisappear { diagnostics.phoneVisible = false; UIApplication.shared.isIdleTimerDisabled = false }
    }
    private var liveView: some View {
        VStack(spacing: 16) {
            GeometryReader { space in
                if diagnostics.frameFresh, let image = diagnostics.screen {
                    Image(uiImage: image).resizable().scaledToFit()
                        .frame(width: space.size.width, height: space.size.height)
                        .accessibilityLabel("Live comma display")
                } else {
                    ContentUnavailableView("Waiting for live video", systemImage: "play.rectangle", description: Text(diagnostics.screenStatus))
                        .frame(width: space.size.width, height: space.size.height)
                }
            }.background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 20))
            Label(diagnostics.screenStatus, systemImage: diagnostics.frameFresh ? "wifi" : "clock")
                .font(.caption).foregroundStyle(.secondary)
            if diagnostics.canCopyLog {
                Text("No frame received. Copy diagnostics to share what happened.")
                    .font(.caption).foregroundStyle(.secondary)
                copyButton
            }
        }.padding(16)
    }
    private var diagnosticView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Live diagnostics").font(.title2.bold())
                        Text(diagnostics.fresh ? "Updating every 2 seconds" : diagnostics.status)
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text("READ ONLY").font(.system(size: 9, weight: .bold)).tracking(1)
                        .padding(8).background(purple.opacity(0.18), in: Capsule()).foregroundStyle(purple)
                }
                HStack(spacing: 12) {
                    Image(systemName: "car.side.fill").font(.title2).foregroundStyle(purple)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(drivingStatus).font(.headline)
                        Text(diagnostics.fresh ? "Telemetry connected" : "Waiting for fresh telemetry")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Circle().fill(diagnostics.fresh ? Color.green : Color.orange).frame(width: 8, height: 8)
                }.padding(18).background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 18))
                metricCards("Temperatures", icon: "thermometer.medium", values: diagnostics.fresh ? diagnostics.snapshot?.temperatures ?? [] : [])
                metricCards("Frame & message rates", icon: "waveform.path", values: diagnostics.fresh ? diagnostics.snapshot?.rates ?? [] : [])
                Text("Unavailable sensors show no reading. Message rates reflect updates observed by the comma UI.")
                    .font(.caption).foregroundStyle(.secondary)
                copyButton.frame(maxWidth: .infinity)
            }.padding(20).frame(maxWidth: 700).frame(maxWidth: .infinity)
        }
    }
    private var drivingStatus: String {
        guard diagnostics.fresh, let engaged = diagnostics.snapshot?.engaged else { return "Driving status unavailable" }
        return engaged ? "StarPilot engaged" : "StarPilot not engaged"
    }
    private var copyButton: some View {
        Button(diagnostics.copiedLog ? "Copied diagnostics" : "Copy diagnostics", systemImage: diagnostics.copiedLog ? "checkmark" : "doc.on.doc") {
            UIPasteboard.general.string = diagnostics.diagnosticLog()
            diagnostics.copiedLog = true
        }.buttonStyle(.bordered).tint(purple)
    }
    private func metricCards(_ title: String, icon: String, values: [DiagnosticMetric]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(title, systemImage: icon).font(.headline)
            if values.isEmpty {
                Text("No readings available").font(.subheadline).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading).padding(18)
                    .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 16))
            } else {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 145), spacing: 12)], spacing: 12) {
                    ForEach(Array(values.enumerated()), id: \.offset) { _, metric in
                        VStack(alignment: .leading, spacing: 12) {
                            Text(metric.name).font(.caption.weight(.medium)).foregroundStyle(.secondary)
                                .lineLimit(2).frame(minHeight: 30, alignment: .topLeading)
                            HStack(alignment: .firstTextBaseline, spacing: 4) {
                                Text(metric.value.map { String(format: "%.1f", $0) } ?? "—")
                                    .font(.system(size: 29, weight: .semibold, design: .rounded)).monospacedDigit()
                                Text(metric.unit).font(.caption).foregroundStyle(purple).lineLimit(1).minimumScaleFactor(0.6)
                            }.minimumScaleFactor(0.7).lineLimit(1)
                        }.frame(maxWidth: .infinity, alignment: .leading).padding(16)
                            .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 16))
                    }
                }
            }
        }
    }
}
