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
    @Published var system: [String: Any]?
    @Published var snapshot: DiagnosticSnapshot?
    @Published var screen: UIImage?
    @Published var status = "Connect and pair with comma to read diagnostics." { didSet { record(status) } }
    @Published var screenStatus = "Live View uses local Wi-Fi." { didSet { if !screenStatus.hasPrefix("Full comma display") { record(screenStatus) } } }
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
    private var telemetryTask: Task<Void, Never>?
    private var reconnectCount = 0
    private var retryDelay = 1.0
    private var streamHasFrame = false
    private var streamHost = ""
    private var streamStarted = Date.distantPast
    private var streamGeneration = UUID()
    private var lastStreamAttempt = Date.distantPast
    private var frameCount = 0
    private var fpsStarted = Date()
    @Published private(set) var displayFPS = 0.0
    private var lastDiagnostics = Date.distantPast
    private var lastDiagnosticsHTTP: Int?
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
        var lines = ["StarPilot BT Live diagnostics", ISO8601DateFormatter().string(from: Date()),
                     "App: \(info["CFBundleShortVersionString"] ?? "unknown") (\(info["CFBundleVersion"] ?? "unknown"))",
                     "iOS: \(UIDevice.current.systemVersion)",
                     "Connection: \(transport?.label ?? "Disconnected")",
                     "LAN connected: \(lan?.connected == true)",
                     "Live mode: \(live); phone visible: \(phoneVisible); phone active: \(phoneActive); CarPlay active: \(carPlayActive)",
                     "Stream reconnect attempts: \(reconnectCount)",
                     "Telemetry: \(status)", "Telemetry HTTP: \(lastDiagnosticsHTTP.map(String.init) ?? "No response yet")", "Stream: \(screenStatus)",
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
    private func updateActivity() {
        let active = carPlayActive || (phoneVisible && phoneActive)
        if !active {
            task?.cancel(); task = nil; telemetryTask?.cancel(); telemetryTask = nil
            stopStream(); return
        }
        guard task == nil else { return }
        task = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                self.maintainStream()
                do { try await Task.sleep(nanoseconds: 500_000_000) } catch { return }
            }
        }
        telemetryTask = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                await self.pollDiagnostics()
                do { try await Task.sleep(nanoseconds: 2_000_000_000) } catch { return }
            }
        }
    }
    private func pollDiagnostics() async {
        guard Date().timeIntervalSince(lastDiagnostics) >= 3, let transport, transport.connected else { return }
        lastDiagnostics = Date()
        do {
            let response = try await transport.request(path: "/api/system/monitor", method: "GET", headers: [:], body: Data())
            try Task.checkCancellation()
            lastDiagnosticsHTTP = response.status
            let value = try JSONSerialization.jsonObject(with: response.bodyData) as? [String: Any] ?? [:]
            guard response.status == 200, value["schemaVersion"] as? Int == 1 else {
                throw BridgeError.message(value["error"] as? String ?? "System monitor unavailable.")
            }
            let cpu = (value["cpuPercent"] as? NSNumber)?.doubleValue
            let memory = value["memory"] as? [String: Any] ?? [:]
            let cores = value["cores"] as? [[String: Any]] ?? []
            system = value
            snapshot = DiagnosticSnapshot(ageSeconds: 0, engaged: nil, temperatures: [], rates:
                [DiagnosticMetric(name: "CPU load", value: cpu, unit: "%"),
                 DiagnosticMetric(name: "Memory", value: (memory["percent"] as? NSNumber)?.doubleValue, unit: "%")] +
                cores.map { DiagnosticMetric(name: $0["name"] as? String ?? "CPU", value: ($0["percent"] as? NSNumber)?.doubleValue, unit: "%") }, capture: nil)
            receivedAt = Date(); status = "Connected · read only"
        } catch {
            if !Task.isCancelled { status = error.localizedDescription; system = nil; snapshot = nil; receivedAt = nil }
        }
    }
    private func maintainStream() {
        stopStream()
        screenStatus = "Open Cameras & Monitoring in Galaxy for SecretGood’s camera views. Cameras require local Wi-Fi."
    }
    private func stopStream(preserveFrame: Bool = false) {
        if !preserveFrame { screen = nil; frameAt = nil; displayFPS = 0 }
    }
}

struct CompanionView: View {
    @ObservedObject var diagnostics: CompanionDiagnostics
    private let purple = Color(red: 0.55, green: 0.36, blue: 0.96)
    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { _ in
            if diagnostics.live { liveView } else { diagnosticView }
        }
        .background(Color(uiColor: .systemBackground))
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
                    ContentUnavailableView("Galaxy cameras", systemImage: "play.rectangle", description: Text(diagnostics.screenStatus))
                        .frame(width: space.size.width, height: space.size.height)
                }
            }.background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20))
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
                }.padding(18).background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 18))
                metricSection("Temperatures", icon: "thermometer.medium", values: temperatures.filter { !isExternalGPU($0) }, thermal: true)
                metricSection("Frame rates", icon: "speedometer", values: rates.filter { $0.unit == "FPS" && !isExternalGPU($0) }, thermal: false)
                metricSection("Message rates", icon: "waveform.path", values: rates.filter { $0.unit != "FPS" && !isExternalGPU($0) }, thermal: false)
                externalGPUView
                Text("Unavailable sensors show no reading. Message rates reflect updates observed by the comma UI.")
                    .font(.caption).foregroundStyle(.secondary)
                copyButton.frame(maxWidth: .infinity)
            }.padding(20).frame(maxWidth: 700).frame(maxWidth: .infinity)
        }
    }
    private var temperatures: [DiagnosticMetric] {
        diagnostics.fresh ? diagnostics.snapshot?.temperatures ?? [] : []
    }
    private var rates: [DiagnosticMetric] {
        diagnostics.fresh ? diagnostics.snapshot?.rates ?? [] : []
    }
    private func isExternalGPU(_ metric: DiagnosticMetric) -> Bool {
        let name = metric.name.lowercased()
        return name.contains("external gpu") || name.contains("chestnut") || name.hasPrefix("sensor: amdgpu")
    }
    private var externalGPUView: some View {
        let sensors = temperatures.filter(isExternalGPU)
        let updates = rates.filter(isExternalGPU)
        return VStack(alignment: .leading, spacing: 16) {
            HStack {
                Label("External GPU", systemImage: "cpu").font(.title3.bold())
                Spacer()
                Text("CHESTNUT").font(.system(size: 9, weight: .bold)).tracking(1).foregroundStyle(purple)
            }
            if sensors.isEmpty && updates.isEmpty {
                Text("No Chestnut telemetry reported.").font(.subheadline).foregroundStyle(.secondary)
            } else {
                if !sensors.isEmpty { metricCards("Temperatures", icon: "thermometer.medium", values: sensors) }
                if !updates.isEmpty { metricCards("Telemetry rates", icon: "waveform.path", values: updates) }
            }
        }.padding(18).background(purple.opacity(0.08), in: RoundedRectangle(cornerRadius: 20))
            .overlay(RoundedRectangle(cornerRadius: 20).stroke(purple.opacity(0.25), lineWidth: 1))
    }
    private func metricName(_ metric: DiagnosticMetric) -> String {
        switch metric.name {
        case "External GPU": "GPU temperature"
        case "External GPU memory": "Memory temperature"
        case "chestnutState": "Telemetry updates"
        default: metric.name
        }
    }
    private func component(_ metric: DiagnosticMetric, thermal: Bool) -> String {
        let name = metric.name.lowercased()
        if thermal {
            if name.hasPrefix("sensor:") { return "Additional hardware sensors" }
            if name.contains("cpu") || name.contains("dsp") || name.contains("soc") { return "Processors" }
            if name.contains("gpu") { return "Onboard GPU" }
            if name.contains("memory") { return "Memory" }
            if name.contains("pmic") { return "Power management" }
            if name.contains("modem") || name.contains("gnss") { return "Connectivity & positioning" }
            if name.contains("intake") || name.contains("exhaust") { return "Cooling" }
            return "Other temperatures"
        }
        if name.contains("camera") { return "Cameras" }
        if name == "ui" { return "Display" }
        if name.contains("model") || name.contains("plan") { return "Models & planning" }
        if name.contains("carstate") || name.contains("carcontrol") || name.contains("selfdrive") { return "Driving" }
        if name.contains("device") || name.contains("peripheral") { return "Device" }
        return "Other services"
    }
    private func metricSection(_ title: String, icon: String, values: [DiagnosticMetric], thermal: Bool) -> some View {
        let order = thermal
            ? ["Processors", "Onboard GPU", "Memory", "Power management", "Cooling", "Connectivity & positioning", "Other temperatures", "Additional hardware sensors"]
            : ["Display", "Cameras", "Models & planning", "Driving", "Device", "Other services"]
        return VStack(alignment: .leading, spacing: 16) {
            Label(title, systemImage: icon).font(.title3.bold())
            if values.isEmpty {
                Text("No readings available").font(.subheadline).foregroundStyle(.secondary)
            }
            ForEach(order, id: \.self) { group in
                let readings = values.filter { component($0, thermal: thermal) == group }
                if !readings.isEmpty {
                    if group == "Additional hardware sensors" || group == "Other services" || group == "Other temperatures" {
                        DisclosureGroup {
                            metricCards("", icon: icon, values: readings).padding(.top, 12)
                        } label: {
                            HStack {
                                Text(group).font(.subheadline.weight(.medium))
                                Spacer()
                                Text("\(readings.count)").font(.caption).foregroundStyle(.secondary)
                            }
                        }.tint(purple).padding(16)
                            .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16))
                    } else {
                        metricCards(group, icon: icon, values: readings)
                    }
                }
            }
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
            if !title.isEmpty { Text(title).font(.subheadline.weight(.semibold)).foregroundStyle(.secondary) }
            if values.isEmpty {
                Text("No readings available").font(.subheadline).foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading).padding(18)
                    .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16))
            } else {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 145), spacing: 12)], spacing: 12) {
                    ForEach(Array(values.enumerated()), id: \.offset) { _, metric in
                        VStack(alignment: .leading, spacing: 12) {
                            Text(metricName(metric)).font(.caption.weight(.medium)).foregroundStyle(.secondary)
                                .lineLimit(2).frame(minHeight: 30, alignment: .topLeading)
                            HStack(alignment: .firstTextBaseline, spacing: 4) {
                                Text(metric.value.map { String(format: "%.1f", $0) } ?? "—")
                                    .font(.system(size: 29, weight: .semibold, design: .rounded)).monospacedDigit()
                                Text(metric.unit).font(.caption).foregroundStyle(purple).lineLimit(1).minimumScaleFactor(0.6)
                            }.minimumScaleFactor(0.7).lineLimit(1)
                        }.frame(maxWidth: .infinity, alignment: .leading).padding(16)
                            .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16))
                    }
                }
            }
        }
    }
}
