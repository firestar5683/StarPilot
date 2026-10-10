import SwiftUI
import Network

@main
struct GalaxyBluetoothApp: App {
    @StateObject private var model = AppModel.shared
    var body: some Scene { WindowGroup { GalaxyRootView(model: model) } }
}

enum CompanionTab: String, CaseIterable, Identifiable {
    case galaxy = "Galaxy", live = "Live View", diagnostics = "Diagnostics", connections = "Settings"
    var id: String { rawValue }
    var icon: String {
        switch self {
        case .galaxy: "sparkles"
        case .live: "play.rectangle"
        case .diagnostics: "chart.xyaxis.line"
        case .connections: "gearshape.fill"
        }
    }
}

@MainActor
final class AppModel: ObservableObject {
    static let shared = AppModel()
    let diagnostics = CompanionDiagnostics()
    @Published var showDiagnostics = false
    @Published var tab: CompanionTab = .connections
    private var phoneActive = false
    private var carPlayActive = false
    private var monitorTask: Task<Void, Never>?
    func setPhoneActive(_ active: Bool) { phoneActive = active; diagnostics.phoneActive = active; updateMonitoring() }
    func setCarPlayActive(_ active: Bool) { carPlayActive = active; diagnostics.carPlayActive = active; updateMonitoring() }
    private func updateMonitoring() {
        if phoneActive || carPlayActive {
            if monitorTask == nil { monitorTask = Task { await monitor() } }
        } else { monitorTask?.cancel(); monitorTask = nil }
    }
    @Published var pairingKey = PairingKeyStore.load()
    @Published var address = UserDefaults.standard.string(forKey: "galaxy.lan.address") ?? ""
    @Published var findAddressAutomatically = UserDefaults.standard.object(forKey: "galaxy.lan.auto") as? Bool ?? true {
        didSet { UserDefaults.standard.set(findAddressAutomatically, forKey: "galaxy.lan.auto") }
    }
    @Published var networkDetails = "Comma can use a hotspot, Wi-Fi or its SIM for internet. Your connection here controls how this iPhone reaches comma."
    @Published var mode = ConnectionMode(rawValue: UserDefaults.standard.string(forKey: "galaxy.connection.mode") ?? "") ?? .automatic {
        didSet {
            transport.mode = mode
            UserDefaults.standard.set(mode.rawValue, forKey: "galaxy.connection.mode")
            if mode == .lan { bluetooth.disconnect() }
            if mode == .bluetooth { lan.invalidate() }
        }
    }
    @Published var showConnections = false
    @Published var showPairingScanner = false
    @Published var opened = false
    @Published var connectionMessage = "Choose a connection, or use Automatic for Wi-Fi with Bluetooth fallback."
    @Published var wantsConnection = true
    let bluetooth: BluetoothTransport
    let lan: LANTransport
    let transport: PreferredTransport
    let assets: GalaxyAssetStore
    let server: LoopbackServer
    private let pathMonitor = NWPathMonitor()
    private var lastReconnect = Date.distantPast
    private var lastAddressCheck = Date.distantPast
    private var identitySession = ""
    private var addressCheckSession = ""
    func importPairingKey(_ key: String) {
        // Save imported keys only after the encrypted handshake.
        opened = false
        wantsConnection = false
        bluetooth.forgetSavedDevice()
        PairingKeyStore.remove()
        lan.clearEndpoint()
        lan.bind(to: nil)
        address = ""
        identitySession = ""
        addressCheckSession = ""
        UserDefaults.standard.removeObject(forKey: "galaxy.comma.identity")
        UserDefaults.standard.removeObject(forKey: "galaxy.lan.address")
        pairingKey = key
        if mode == .lan { mode = .automatic }
        connectionMessage = "Code scanned. Select your comma below to finish pairing."
        bluetooth.scan()
    }
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
        if let saved = UserDefaults.standard.string(forKey: "galaxy.comma.identity"), LANTransport.deviceID(Data(saved.utf8)) != nil {
            lan.bind(to: saved)
        }
        diagnostics.transport = transport; diagnostics.lan = lan
        server.start()
        pathMonitor.pathUpdateHandler = { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                self.lan.invalidate()
                self.lastAddressCheck = .distantPast
            }
        }
        pathMonitor.start(queue: .main)
    }
    deinit { pathMonitor.cancel() }
    func connect() {
        do {
            if mode != .bluetooth, !address.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                try lan.configure(address: address)
            } else if mode == .lan {
                throw BridgeError.message("Enter comma’s current local IP address, or use Automatic and pair Bluetooth to find it.")
            }
            UserDefaults.standard.set(address.trimmingCharacters(in: .whitespacesAndNewlines), forKey: "galaxy.lan.address")
            wantsConnection = true
            lastReconnect = .distantPast
            lastAddressCheck = .distantPast
            connectionMessage = "Checking your comma…"
        } catch { connectionMessage = error.localizedDescription }
    }
    func openIfReady() {
        guard wantsConnection, transport.connected, !opened else { return }
        let root = assets.readyRoot ?? assets.bundledRoot
        assets.inUseRoot = root
        server.useWebRoot(root)
        opened = true
        if tab == .connections { tab = .galaxy }
    }
    func disconnect() {
        wantsConnection = false; opened = false
        bluetooth.disconnect(); lan.invalidate()
        connectionMessage = "Disconnected."
    }
    private func learnAddress() async {
        guard bluetooth.connected, Date().timeIntervalSince(lastAddressCheck) >= 20 || addressCheckSession != bluetooth.sessionIdentifier else { return }
        lastAddressCheck = Date()
        let session = bluetooth.sessionIdentifier
        addressCheckSession = session
        do {
            if identitySession != session {
                let identity = try await bluetooth.request(path: "/api/params?key=DongleId", method: "GET", headers: [:], body: Data())
                guard wantsConnection, mode != .bluetooth, bluetooth.sessionIdentifier == session else { return }
                // Only the authenticated BLE peer may establish the automatic LAN identity.
                guard identity.status == 200, let value = LANTransport.deviceID(identity.bodyData) else {
                    networkDetails = "Automatic local discovery needs a registered device identifier. Bluetooth still works; enter comma’s IP manually for Wi-Fi."
                    return
                }
                lan.bind(to: value)
                UserDefaults.standard.set(value, forKey: "galaxy.comma.identity")
                identitySession = session
            }
            guard findAddressAutomatically, !lan.connected else { return }
            let response = try await bluetooth.request(path: "/api/device/status", method: "GET", headers: [:], body: Data())
            guard wantsConnection, mode != .bluetooth, bluetooth.sessionIdentifier == session, response.status == 200,
                  !response.bodyData.isEmpty else { return }
            if let ip = LANTransport.reportedAddress(response.bodyData) {
                try lan.configure(address: ip)
                address = ip
                UserDefaults.standard.set(ip, forKey: "galaxy.lan.address")
                networkDetails = "Trying comma’s current local address. If this hotspot or Wi-Fi network blocks direct access, Bluetooth stays available."
            } else {
                networkDetails = "Comma has no usable local Wi-Fi address. Bluetooth still controls local settings; comma can use its SIM for online downloads."
            }
            // Galaxy's online:true means the server responds, not that comma can reach the internet.
        } catch { /* Discovery is optional; it must not disrupt working BLE. */ }
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
                    await learnAddress()
                    if lan.endpoint == nil, !address.isEmpty {
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
            VStack(spacing: 14) {
                HStack {
                    Text("StarPilot").font(.title3.bold())
                    Spacer()
                    HStack(spacing: 5) {
                        Circle().fill(model.transport.connected ? Color.green : Color.orange).frame(width: 6, height: 6)
                        Text(model.transport.label).font(.caption.weight(.medium))
                    }.padding(.horizontal, 10).padding(.vertical, 6)
                        .background(.white.opacity(0.07), in: Capsule())
                }
                HStack(spacing: 4) {
                    ForEach(CompanionTab.allCases.filter { $0 != .connections }) { tab in
                        Button { select(tab) } label: {
                            VStack(spacing: 5) {
                                Image(systemName: tab.icon).font(.system(size: 17, weight: .semibold))
                                Text(tab.rawValue).font(.system(size: 10, weight: .semibold)).lineLimit(1).minimumScaleFactor(0.8)
                            }.frame(maxWidth: .infinity).padding(.vertical, 10)
                                .foregroundStyle(model.tab == tab ? Color.white : Color.secondary)
                                .background(model.tab == tab ? brandPurple.opacity(0.3) : Color.clear, in: RoundedRectangle(cornerRadius: 12))
                        }.buttonStyle(.plain).accessibilityAddTraits(model.tab == tab ? .isSelected : [])
                    }
                    Button { select(.connections) } label: {
                        VStack(spacing: 4) {
                            Image(systemName: "gearshape.fill").font(.system(size: 17, weight: .semibold))
                                .frame(width: 36, height: 36)
                                .background(model.tab == .connections ? brandPurple.opacity(0.4) : Color.white.opacity(0.08), in: Circle())
                            Text("Settings").font(.system(size: 10, weight: .semibold))
                        }.frame(width: 60).padding(.vertical, 4)
                            .foregroundStyle(model.tab == .connections ? Color.white : Color.secondary)
                    }.buttonStyle(.plain).accessibilityAddTraits(model.tab == .connections ? .isSelected : [])
                }.padding(4).background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 16))
            }.padding(.horizontal, 16).padding(.top, 10).padding(.bottom, 12)
            ZStack {
                if model.opened, let url = server.url {
                    GalaxyWebView(url: url, requestKey: server.localSecret)
                        .opacity(model.tab == .galaxy ? 1 : 0)
                        .allowsHitTesting(model.tab == .galaxy)
                        .accessibilityHidden(model.tab != .galaxy)
                }
                if model.tab == .live || model.tab == .diagnostics {
                    CompanionView(diagnostics: model.diagnostics)
                } else if model.tab == .connections || !model.opened {
                    connectionView
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .background(Color.black)
        .preferredColorScheme(.dark)
        .onChange(of: model.showConnections) { _, show in
            if show { select(.connections); model.showConnections = false }
        }
        .onChange(of: model.showDiagnostics) { _, show in
            if show { select(.live); model.showDiagnostics = false }
        }
        .onChange(of: bluetooth.connected) { _, connected in if connected { model.openIfReady() } }
        .task(id: scenePhase) {
            model.setPhoneActive(scenePhase == .active)
            if scenePhase == .active { await model.assets.check() }
        }
    }
    private func select(_ tab: CompanionTab) {
        model.tab = tab
        model.diagnostics.live = tab == .live
    }
    private let brandPurple = Color(red: 0.55, green: 0.36, blue: 0.96)

    private var connectionView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(spacing: 8) {
                    Image("StarPilotHero")
                        .resizable().scaledToFit()
                        .frame(maxWidth: 480)
                        .accessibilityLabel("StarPilot")
                    Text("Galaxy companion")
                        .font(.subheadline.weight(.medium)).foregroundStyle(.secondary)
                }.frame(maxWidth: .infinity).padding(.top, 8)
                Text("Connect your comma").font(.title2.bold())
                Picker("Connection", selection: $model.mode) {
                    ForEach(ConnectionMode.allCases) { Text($0.title).tag($0) }
                }.pickerStyle(.segmented)
                Text("Automatic prefers local Wi-Fi and falls back to your paired comma over Bluetooth. Internet isn’t needed for local settings.")
                    .font(.subheadline).foregroundStyle(.secondary)
                Text(model.networkDetails).font(.caption).foregroundStyle(.secondary)
                if model.mode != .bluetooth {
                    Toggle("Find comma’s address over Bluetooth", isOn: $model.findAddressAutomatically)
                    Text("Comma IP address").font(.headline)
                    TextField("192.168.10.85", text: $model.address)
                        .keyboardType(.numbersAndPunctuation).textInputAutocapitalization(.never).autocorrectionDisabled()
                        .padding(14).background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
                    Text(lan.status).font(.caption).foregroundStyle(.secondary)
                }
                Button { model.connect(); if model.opened { select(.galaxy) } } label: {
                    Text("Connect").font(.headline).frame(maxWidth: .infinity).padding(.vertical, 8)
                }.buttonStyle(.borderedProminent).tint(brandPurple)
                Text(model.connectionMessage).font(.subheadline).foregroundStyle(.secondary)
                if model.mode != .lan {
                    Divider()
                    Text("Bluetooth pairing").font(.headline)
                    Text("On comma, open Settings → Pair phone. Scan its code here, then select your comma below. After pairing once, the app reconnects automatically.")
                        .font(.subheadline).foregroundStyle(.secondary)
                    Button("Scan pairing code") { model.showPairingScanner = true }
                        .buttonStyle(.borderedProminent).tint(brandPurple)
                        .sheet(isPresented: $model.showPairingScanner) {
                            PairingScannerSheet { model.importPairingKey($0) }
                        }
                    SecureField("64-character pairing key", text: $model.pairingKey)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                        .font(.system(.body, design: .monospaced))
                        .padding(14).background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
                    Button(bluetooth.isScanning ? "Scanning…" : "Scan for comma") { model.wantsConnection = true; bluetooth.scan() }
                        .buttonStyle(.bordered).disabled(bluetooth.isScanning || bluetooth.connecting)
                    Text(bluetooth.status).font(.subheadline).foregroundStyle(.secondary)
                    ForEach(bluetooth.devices) { device in
                        Button {
                            model.opened = false
                            model.wantsConnection = true
                            model.lan.clearEndpoint()
                            model.lan.bind(to: nil)
                            model.address = ""
                            UserDefaults.standard.removeObject(forKey: "galaxy.comma.identity")
                            UserDefaults.standard.removeObject(forKey: "galaxy.lan.address")
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
                        model.lan.bind(to: nil); UserDefaults.standard.removeObject(forKey: "galaxy.comma.identity")
                    }.font(.caption).foregroundStyle(.secondary)
                }
                Divider()
                Text(assets.status).font(.caption).foregroundStyle(.secondary)
                Button("Check Galaxy updates") { Task { await assets.check() } }.disabled(assets.checking)
                Text("Screens are saved on your iPhone. GitHub updates apply next time you open Galaxy, without interrupting your current screen.")
                    .font(.caption).foregroundStyle(.secondary)
                if model.opened {
                    Button("Back to Galaxy") { select(.galaxy) }
                    Button("Disconnect") { model.disconnect(); select(.connections) }
                }
                if !server.error.isEmpty { Text(server.error).foregroundStyle(.red) }
            }.padding(24).frame(maxWidth: 560).frame(maxWidth: .infinity)
        }.background(Color.black).tint(brandPurple)
    }
}
