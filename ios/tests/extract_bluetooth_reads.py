from pathlib import Path
import sys

def method(path, name):
    source = Path(path).read_text()
    start = source.index("    static func " + name + "(")
    end = source.index("{", start) + 1
    depth = 1
    while depth:
        if source[end] == "{": depth += 1
        if source[end] == "}": depth -= 1
        end += 1
    return source[start:end]

methods = method("GalaxyBluetooth/BluetoothTransport.swift", "useNotifications")
methods += "\n" + method("GalaxyBluetooth/BluetoothTransport.swift", "backgroundRead") + "\n" + method("GalaxyBluetooth/BluetoothTransport.swift", "nextRequestIndex")
methods += "\n" + method("GalaxyBluetooth/BluetoothTransport.swift", "shouldPauseFastReads")
methods += "\n" + method("GalaxyBluetooth/BluetoothTransport.swift", "canDrainCancellation")
tests = r'''
@main struct BluetoothReadRegression {
    static func main() {
        for path in ["/api/settings/pages/hub", "/api/device/state", "/api/settings/pages/appearance"] {
            precondition(!Probe.useNotifications(method: "GET", path: path, supported: true), "Read used stalled notification window")
        }
        precondition(Probe.useNotifications(method: "PUT", path: "/api/settings/confirm", supported: true))
        precondition(!Probe.useNotifications(method: "PUT", path: "/api/settings/confirm", supported: false))
        precondition(!Probe.useNotifications(method: "GET", path: "/_bridge/health", supported: true))
        precondition(Probe.nextRequestIndex(methods: ["GET", "GET"], paths: ["/api/system/monitor", "/api/settings/pages/hub"], priorityStreak: 0) == 1)
        precondition(Probe.nextRequestIndex(methods: ["GET", "PUT", "GET"], paths: ["/api/system/monitor", "/api/settings/confirm", "/api/settings/pages/hub"], priorityStreak: 0) == 0)
        precondition(Probe.nextRequestIndex(methods: ["GET", "GET"], paths: ["/api/system/monitor", "/api/settings/pages/hub"], priorityStreak: 3) == 0)
        precondition(Probe.nextRequestIndex(methods: ["PUT", "GET"], paths: ["/api/settings/confirm", "/api/settings/pages/hub"], priorityStreak: 0) == 0)
        precondition(Probe.backgroundRead("/api/device/state?refresh=1"))
        precondition(Probe.nextRequestIndex(methods: ["GET", "GET", "GET"], paths: ["/api/models/status", "/api/drives/stats?timezone=UTC", "/api/settings/pages/hub"], priorityStreak: 0) == 2)
        precondition(Probe.backgroundRead("/api/software/status?history=0"))
        precondition(Probe.useNotifications(method: "GET", path: "/api/settings/pages/hub", supported: true, fastReads: true))
        precondition(!Probe.useNotifications(method: "GET", path: "/api/settings/pages/hub", supported: false, fastReads: true))
        precondition(!Probe.useNotifications(method: "GET", path: "/_bridge/health", supported: true, fastReads: true))
        precondition(!Probe.useNotifications(method: "GET", path: "/api/settings/pages/hub", supported: true, fastReads: false))
        precondition(Probe.shouldPauseFastReads(method: "GET", notifications: true, cancelled: false))
        precondition(!Probe.shouldPauseFastReads(method: "GET", notifications: false, cancelled: false))
        precondition(!Probe.shouldPauseFastReads(method: "GET", notifications: true, cancelled: true))
        precondition(!Probe.shouldPauseFastReads(method: "PUT", notifications: true, cancelled: false))
        precondition(!Probe.shouldPauseFastReads(method: nil, notifications: true, cancelled: false))
        precondition(Probe.canDrainCancellation(method: "GET", requestSent: false))
        precondition(Probe.canDrainCancellation(method: "GET", requestSent: true))
        precondition(!Probe.canDrainCancellation(method: "PUT", requestSent: false))
        precondition(!Probe.canDrainCancellation(method: "POST", requestSent: false))
        precondition(Probe.canDrainCancellation(method: "PUT", requestSent: true))
        print("Bluetooth read policy, cancellation and priority passed")
    }
}
'''
Path(sys.argv[1]).write_text("import Foundation\nstruct Probe {\n" + methods + "\n}\n" + tests)
