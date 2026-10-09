import SwiftUI

@main
struct GalaxyBluetoothApp: App {
    @StateObject private var model = AppModel()
    var body: some Scene { WindowGroup { GalaxyRootView(model: model) } }
}

@MainActor
final class AppModel: ObservableObject {
    @Published var pairingKey = PairingKeyStore.load()
    @Published var address = UserDefaults.standard.string(forKey: "galaxy.lan.address") ?? "192.168.10.85"
    @Published var mode = ConnectionMode(rawValue: UserDefaults.standard.string(forKey: "galaxy.connection.mode") ?? "") ?? .automatic {
        didSet {
            transport.mode = mode
            UserDefaults.standard.set(mode.rawValue, forKey: "galaxy.connection.mode")
            if mode == .lan { bluetooth.disconnect() }
            if mode == .bluetooth { lan.invalidate() }
        }
    }
    @Published var showConnections = false
    @Published var opened = false
    @Published var connectionMessage = "Choose a connection, or use Automatic for Wi-Fi with Bluetooth fallback."
    @Published var wantsConnection = true
    let bluetooth: BluetoothTransport
    let lan: LANTransport
    let transport: PreferredTransport
    let assets: GalaxyAssetStore
    let server: LoopbackServer
    private var lastReconnect = Date.distantPast
    init() {
        let bluetooth = BluetoothTransport()
        let lan = LANTransport()
        let transport = PreferredTransport(lan: lan, bluetooth: bluetooth, invalidateLAN: { lan.invalidate() })
        let assets = GalaxyAssetStore()
        self.bluetooth = bluetooth; self.lan = lan; self.transport = transport; self.assets = assets
        let cache = GalaxyReadCache(transport: transport, sessionID: {
            transport.usesLAN ? "lan-" + lan.generation : "ble-" + bluetooth.sessionIdentifier
        })
        server = LoopbackServer(transport: cache, webRoot: assets.readyRoot ?? assets.bundledRoot)
        transport.mode = mode
        server.start()
    }
    func connect() {
        do {
            if mode != .bluetooth { try lan.configure(address: address) }
            UserDefaults.standard.set(address.trimmingCharacters(in: .whitespacesAndNewlines), forKey: "galaxy.lan.address")
            wantsConnection = true
            lastReconnect = .distantPast
            connectionMessage = "Checking your comma…"
        } catch { connectionMessage = error.localizedDescription }
    }
    func openIfReady() {
        guard wantsConnection, transport.connected, !opened else { return }
        let root = assets.readyRoot ?? assets.bundledRoot
        assets.inUseRoot = root
        server.useWebRoot(root)
        opened = true
    }
    func disconnect() {
        wantsConnection = false; opened = false
        bluetooth.disconnect(); lan.invalidate()
        connectionMessage = "Disconnected."
    }
    func monitor() async {
        while !Task.isCancelled {
            if wantsConnection {
                if mode != .lan, !bluetooth.connected, !bluetooth.connecting, !bluetooth.isScanning,
                   !pairingKey.isEmpty, Date().timeIntervalSince(lastReconnect) >= 25 {
                    lastReconnect = Date()
                    bluetooth.reconnectSaved(pairingKey: pairingKey)
                }
                if mode != .bluetooth {
                    if lan.endpoint == nil {
                        do { try lan.configure(address: address) }
                        catch { connectionMessage = error.localizedDescription }
                    }
                    _ = await lan.probe()
                }
                if transport.connected { openIfReady(); connectionMessage = "Connected over \(transport.label)." }
                else { connectionMessage = "Wi-Fi unavailable. Pair over Bluetooth below, or check your comma’s IP address." }
            }
            do { try await Task.sleep(nanoseconds: 3_000_000_000) } catch { return }
        }
    }
}

struct GalaxyRootView: View {
    @ObservedObject var model: AppModel
    @ObservedObject var bluetooth: BluetoothTransport
    @ObservedObject var lan: LANTransport
    @ObservedObject var assets: GalaxyAssetStore
    @ObservedObject var server: LoopbackServer
    @Environment(\.scenePhase) private var scenePhase
    init(model: AppModel) {
        self.model = model; bluetooth = model.bluetooth; lan = model.lan; assets = model.assets; server = model.server
    }
    var body: some View {
        VStack(spacing: 0) {
            if model.opened, let url = server.url {
                HStack {
                    Image(systemName: model.transport.usesLAN ? "wifi" : "antenna.radiowaves.left.and.right")
                        .foregroundStyle(model.transport.connected ? .green : .orange)
                    Text("Galaxy · \(model.transport.label)").font(.subheadline.weight(.semibold))
                    Spacer()
                    Button("Connections") { model.showConnections = true }.font(.subheadline)
                }.padding(.horizontal, 16).padding(.vertical, 10)
                // Keep the screen mounted across connection switches.
                GalaxyWebView(url: url, requestKey: server.localSecret)
            } else { connectionView }
        }
        .background(Color(red: 0.06, green: 0.05, blue: 0.09))
        .preferredColorScheme(.dark)
        .sheet(isPresented: $model.showConnections) { connectionView.preferredColorScheme(.dark) }
        .onChange(of: bluetooth.connected) { _, connected in if connected { model.openIfReady() } }
        .task(id: scenePhase) {
            guard scenePhase == .active else { return }
            await withTaskGroup(of: Void.self) { group in
                group.addTask { await model.assets.check() }
                group.addTask { await model.monitor() }
                await group.waitForAll()
            }
        }
    }
    private var connectionView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Image(systemName: "sparkles").font(.system(size: 48)).foregroundStyle(.purple).padding(.top, 28)
                Text("Galaxy").font(.largeTitle.bold())
                Text("Your comma, wherever you connect.").font(.title3).foregroundStyle(.secondary)
                Picker("Connection", selection: $model.mode) {
                    ForEach(ConnectionMode.allCases) { Text($0.title).tag($0) }
                }.pickerStyle(.segmented)
                Text("Automatic prefers local Wi-Fi and falls back to your paired comma over Bluetooth. Internet isn’t needed for local settings.")
                    .font(.subheadline).foregroundStyle(.secondary)
                if model.mode != .bluetooth {
                    Text("Comma IP address").font(.headline)
                    TextField("192.168.10.85", text: $model.address)
                        .keyboardType(.numbersAndPunctuation).textInputAutocapitalization(.never).autocorrectionDisabled()
                        .padding(14).background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
                }
                Button("Connect") { model.connect(); if model.opened { model.showConnections = false } }
                    .buttonStyle(.borderedProminent).tint(.purple)
                Text(model.connectionMessage).font(.subheadline).foregroundStyle(.secondary)
                if model.mode != .lan {
                    Divider()
                    Text("Bluetooth pairing").font(.headline)
                    Text("Start the bridge on comma, then enter its pairing key. After pairing once, the app can reconnect automatically.")
                        .font(.subheadline).foregroundStyle(.secondary)
                    SecureField("64-character pairing key", text: $model.pairingKey)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                        .font(.system(.body, design: .monospaced))
                        .padding(14).background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
                    Button(bluetooth.isScanning ? "Scanning…" : "Scan for comma") { model.wantsConnection = true; bluetooth.scan() }
                        .buttonStyle(.bordered).disabled(bluetooth.isScanning || bluetooth.connecting)
                    Text(bluetooth.status).font(.subheadline).foregroundStyle(.secondary)
                    ForEach(bluetooth.devices) { device in
                        Button {
                            model.wantsConnection = true
                            bluetooth.connect(device, pairingKey: model.pairingKey)
                        } label: {
                            HStack {
                                Image(systemName: "car.side.fill"); Text(device.name).font(.headline)
                                Spacer(); Image(systemName: "chevron.right")
                            }.padding(16).background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
                        }.buttonStyle(.plain).disabled(bluetooth.connecting)
                    }
                    if bluetooth.connecting { Button("Cancel Bluetooth connection") { bluetooth.disconnect() } }
                    Button("Forget Bluetooth pairing") {
                        bluetooth.forgetSavedDevice(); PairingKeyStore.remove(); model.pairingKey = ""
                    }.font(.caption).foregroundStyle(.secondary)
                }
                Divider()
                Text(assets.status).font(.caption).foregroundStyle(.secondary)
                Button("Check Galaxy updates") { Task { await assets.check() } }.disabled(assets.checking)
                Text("Screens are saved on your iPhone. GitHub updates apply next time you open Galaxy, without interrupting your current screen.")
                    .font(.caption).foregroundStyle(.secondary)
                if model.opened {
                    Button("Back to Galaxy") { model.showConnections = false }
                    Button("Disconnect") { model.disconnect(); model.showConnections = false }
                }
                if !server.error.isEmpty { Text(server.error).foregroundStyle(.red) }
            }.padding(28)
        }
    }
}
