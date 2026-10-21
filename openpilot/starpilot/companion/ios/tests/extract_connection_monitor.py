from pathlib import Path
import sys

source = Path('GalaxyBluetooth/GalaxyBluetoothApp.swift').read_text()

def method(signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

stubs = r'''
import Foundation

enum ConnectionMode { case automatic, bluetooth, lan }
@MainActor final class Bluetooth {
    var connected = false, connecting = false, isScanning = false
    var attempts = 0
    func reconnectSaved(pairingKey: String) { attempts += 1 }
}
@MainActor final class LAN {
    var endpoint: URL?
    var connected = false
    var probes = 0
    func configure(address: String) throws {}
    func probe() async -> Bool {
        probes += 1
        try? await Task.sleep(nanoseconds: 60_000_000_000)
        return false
    }
}
@MainActor final class Transport {
    let label = "Reconnecting…"
    let connected = false
}
@MainActor final class Discovery { func stop() {} }
@MainActor final class Assets { var readyRoot: URL?; var status = "" }
@MainActor final class MonitorProbe {
    let bluetooth = Bluetooth(), lan = LAN(), transport = Transport(), discovery = Discovery()
    let assets = Assets()
    var opened = false
    var wantsConnection = true, pairingInProgress = false, openingGalaxy = false, offerAudioPairing = false
    var mode = ConnectionMode.automatic
    var pairingKey = "saved", address = "", connectionMessage = "", lastRoute = ""
    var lastReconnect = Date.distantPast, lastGalaxyMatch = Date.distantPast
    var lanProbeTask: Task<Void, Never>?
    func learnAddress() async {}
    func discoverAutomaticLAN() {}
    func logConnection(_ reason: String) {}
    func openIfReady() {}
    func checkGalaxyUpdates() async {}
    func startAudioPairing() {}
'''
tests = r'''
}
@main struct MonitorRegression {
    @MainActor static func main() async throws {
        let model = MonitorProbe()
        let monitor = Task { await model.monitor() }
        for _ in 0..<100 where model.lan.probes == 0 {
            try await Task.sleep(nanoseconds: 20_000_000)
        }
        precondition(model.lan.probes == 1 && model.bluetooth.attempts == 1)
        model.lastReconnect = .distantPast
        try await Task.sleep(nanoseconds: 3_200_000_000)
        precondition(model.bluetooth.attempts >= 2, "A stalled Wi-Fi request must not block Bluetooth reconnects")
        precondition(model.lan.probes == 1, "Do not pile up Wi-Fi probes while one is still running")
        monitor.cancel()
        model.lanProbeTask?.cancel()
        await monitor.value
        print("Slow Wi-Fi leaves Bluetooth reconnects running; only one LAN probe in flight")
    }
}
'''
Path(sys.argv[1]).write_text(stubs + '\n' + method('    private func probeLocalConnection()') + '\n' + method('    func monitor() async') + tests)
