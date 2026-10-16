import SwiftUI
import Network

@main
struct GalaxyBluetoothApp: App {
    @StateObject private var model = AppModel.shared
    var body: some Scene { WindowGroup { GalaxyRootView(model: model) } }
}

enum CompanionTab: String, CaseIterable, Identifiable {
    case galaxy = "Galaxy", live = "Live View", diagnostics = "Diagnostics", logs = "Dev / Logs", connections = "Settings"
    var id: String { rawValue }
    var isDeveloperPage: Bool { self == .live || self == .diagnostics || self == .logs }
    var icon: String {
        switch self {
        case .galaxy: "sparkles"
        case .live: "play.rectangle"
        case .diagnostics: "chart.xyaxis.line"
        case .logs: "ladybug"
        case .connections: "gearshape.fill"
        }
    }
}

struct LegacyGalaxyStatus: Decodable {
    let paired: Bool
    let url: String
    var browserURL: URL? {
        guard let parsed = URL(string: url), parsed.scheme == "https",
              parsed.host == "galaxy.firestar.link", parsed.port == nil,
              parsed.user == nil, parsed.password == nil, parsed.query == nil, parsed.fragment == nil,
              parsed.path.range(of: "^/[A-Za-z0-9]{16}$", options: .regularExpression) != nil else { return nil }
        return parsed
    }
}

@MainActor
final class AppModel: ObservableObject {
    static let shared = AppModel()
    let diagnostics = CompanionDiagnostics()
    let galaxyPage = GalaxyPageDiagnostics()
    let connectionLog = ConnectionEventLog()
    let discovery = LANDiscovery()
    @Published var selectingDiscoveredComma = false
    private var lastRoute = "Reconnecting…"
    @Published var showDiagnostics = false
    @Published var tab: CompanionTab = .galaxy
    @Published var developerMode = UserDefaults.standard.bool(forKey: "galaxy.app.developerMode") {
        didSet {
            UserDefaults.standard.set(developerMode, forKey: "galaxy.app.developerMode")
            if !developerMode {
                if tab.isDeveloperPage { tab = opened ? .galaxy : .connections }
                diagnostics.live = false
                diagnostics.phoneVisible = false
                showDiagnostics = false
            }
        }
    }
    private var galaxyRecoveryTask: Task<Void, Never>?
    private var lastAutomaticGalaxyRecovery: TimeInterval = -.infinity
    func recoverGalaxy(automatic: Bool = true, reload: Bool = true) {
        guard phoneActive, galaxyRecoveryTask == nil else { return }
        let now = ProcessInfo.processInfo.systemUptime
        if automatic && reload {
            guard now - lastAutomaticGalaxyRecovery >= 30 else {
                galaxyPage.record("Automatic page recovery paused; use Retry Galaxy")
                return
            }
            lastAutomaticGalaxyRecovery = now
        }
        galaxyRecoveryTask = Task { @MainActor in
            defer { self.galaxyRecoveryTask = nil }
            let previousURL = self.server.url
            let healthy = await self.server.ensureAvailable()
            guard self.phoneActive else { return }
            if healthy {
                if self.opened && (reload || self.galaxyPage.stalled || previousURL != self.server.url) {
                    self.galaxyPage.record("Local server checked; recreating Galaxy web page")
                    self.galaxyPage.retry()
                }
            } else { self.galaxyPage.fail("Local server unavailable after recovery attempt") }
        }
    }
    private var phoneActive = false
    private var carPlayActive = false
    private var monitorTask: Task<Void, Never>?
    func setPhoneActive(_ active: Bool) { phoneActive = active; diagnostics.phoneActive = active; if !active { discovery.stop() }; updateMonitoring() }
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
            if mode == .bluetooth { discovery.stop(); lan.invalidate(reason: "Bluetooth-only mode selected") }
            logConnection("Connection mode selected: \(mode.title)")
        }
    }
    @Published var showConnections = false
    @Published var showPairingScanner = false
    @Published var opened = false
    @Published var connectionMessage = "Choose a connection, or use Automatic for Wi-Fi with Bluetooth fallback."
    @Published var wantsConnection = true
    @Published var loadingLegacyURL = false
    @Published var legacyMessage = ""
    @Published var legacyURL: URL?
    let bluetooth: BluetoothTransport
    let lan: LANTransport
    let transport: PreferredTransport
    let assets: GalaxyAssetStore
    let server: LoopbackServer
    private let pathMonitor = NWPathMonitor()
    private var lastNetworkPath = ""
    private var lastReconnect = Date.distantPast
    private var lastAddressCheck = Date.distantPast
    private var identitySession = ""
    private var addressCheckSession = ""
    func importPairingKey(_ code: PairingCode) {
        // Save imported keys only after the encrypted handshake.
        opened = false
        wantsConnection = false
        bluetooth.forgetSavedDevice()
        PairingKeyStore.stage(code)
        lan.clearEndpoint()
        lan.bind(to: nil)
        address = ""
        identitySession = ""
        addressCheckSession = ""
        UserDefaults.standard.removeObject(forKey: "galaxy.comma.identity")
        UserDefaults.standard.removeObject(forKey: "galaxy.lan.address")
        pairingKey = code.key
        if mode == .lan { mode = .automatic }
        connectionMessage = "Code scanned. Select your comma below to finish pairing."
        bluetooth.scan()
    }
    init() {
        let bluetooth = BluetoothTransport()
        let lan = LANTransport()
        let transport = PreferredTransport(lan: lan, bluetooth: bluetooth, invalidateLAN: { lan.invalidate(reason: $0) })
        let assets = GalaxyAssetStore()
        self.bluetooth = bluetooth; self.lan = lan; self.transport = transport; self.assets = assets
        let cache = GalaxyReadCache(transport: transport, sessionID: {
            transport.usesLAN ? "lan-" + lan.generation : "ble-" + bluetooth.sessionIdentifier
        })
        server = LoopbackServer(transport: cache, webRoot: assets.readyRoot ?? assets.bundledRoot)
        transport.mode = mode
        diagnostics.transport = transport; diagnostics.lan = lan
        galaxyPage.recover = { [weak self] automatic in self?.recoverGalaxy(automatic: automatic) }
        server.start()
        discovery.onEvent = { [weak self] reason in self?.connectionLog.record(reason) }
        lan.onEvent = { [weak self] reason in self?.logConnection(reason) }
        bluetooth.onEvent = { [weak self] reason in self?.logConnection(reason) }
        pathMonitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in
                guard let self else { return }
                let route = path.usesInterfaceType(.wifi) ? "Wi-Fi" : path.usesInterfaceType(.cellular) ? "cellular" : "other"
                let reason = "iOS network path updated: \(path.status == .satisfied ? "available" : "unavailable"), \(route), expensive=\(path.isExpensive), constrained=\(path.isConstrained)"
                let interfaces = path.availableInterfaces
                    .filter { path.usesInterfaceType($0.type) }
                    .map { "\($0.name):\($0.index)" }.sorted().joined(separator: ",")
                let fingerprint = "\(path.status)|\(route)|\(interfaces)|ipv4=\(path.supportsIPv4)"
                guard fingerprint != self.lastNetworkPath else { return }
                self.lastNetworkPath = fingerprint
                self.connectionLog.record(reason)
                self.lan.invalidate(reason: reason)
                self.lastAddressCheck = .distantPast
            }
        }
        pathMonitor.start(queue: .main)
    }
    deinit { pathMonitor.cancel() }
    private func logConnection(_ reason: String) {
        let route = transport.label
        if route != lastRoute {
            connectionLog.record("\(lastRoute) → \(route): \(reason)")
            lastRoute = route
        } else { connectionLog.record("\(route): \(reason)") }
    }
    func connect() {
        legacyURL = nil
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
        legacyURL = nil
        discovery.stop()
        wantsConnection = false; opened = false
        bluetooth.disconnect(reason: "User selected Disconnect"); lan.invalidate(reason: "User selected Disconnect")
        connectionMessage = "Disconnected."
    }
    func selectDiscoveredComma(_ device: DiscoveredComma) async {
        guard !selectingDiscoveredComma, mode != .bluetooth else { return }
        discovery.stop()
        selectingDiscoveredComma = true
        defer { selectingDiscoveredComma = false }
        // Advertised names and addresses are discovery hints, not pairing credentials.
        let candidate = LANTransport()
        candidate.bind(to: lan.expectedDeviceID)
        let originalGeneration = lan.generation
        let originalMode = mode
        do {
            try candidate.configure(address: device.address)
            guard await candidate.probe() else {
                connectionMessage = "Found a device, but Galaxy is unavailable or it doesn’t match your paired comma."
                connectionLog.record("Discovered comma rejected by LAN verification")
                return
            }
            guard lan.generation == originalGeneration, mode == originalMode, phoneActive else {
                connectionMessage = "Connection changed. Select the comma again."
                return
            }
            address = device.address
            connect()
            connectionLog.record("User selected a discovered comma; LAN verification passed")
        } catch {
            connectionMessage = "Couldn’t connect to the discovered comma. Try again or enter its IP."
        }
    }
    func fetchLegacyURL() async -> URL? {
        guard !loadingLegacyURL else { return nil }
        legacyMessage = ""
        legacyURL = nil
        guard wantsConnection, transport.connected else {
            legacyMessage = "Connect to your comma first to get its Galaxy link."
            return nil
        }
        loadingLegacyURL = true
        defer { loadingLegacyURL = false }
        let lanSession = lan.generation
        let bluetoothSession = bluetooth.sessionIdentifier
        do {
            let response = try await transport.request(path: "/api/galaxy/status", method: "GET", headers: [:], body: Data())
            guard wantsConnection, transport.connected, lan.generation == lanSession,
                  bluetooth.sessionIdentifier == bluetoothSession else {
                throw BridgeError.message("Connection changed. Try opening legacy Galaxy again.")
            }
            guard response.status == 200 else {
                throw BridgeError.message("Couldn’t get your comma’s Galaxy link (HTTP \(response.status)).")
            }
            let status = try JSONDecoder().decode(LegacyGalaxyStatus.self, from: response.bodyData)
            guard status.paired else {
                throw BridgeError.message("Set up legacy Galaxy pairing on your comma first. Bluetooth pairing is separate.")
            }
            guard let url = status.browserURL else {
                throw BridgeError.message("Your comma hasn’t provided a valid Galaxy link. Check its legacy Galaxy pairing.")
            }
            legacyURL = url
            connectionLog.record("Comma-specific legacy Galaxy link validated")
            return url
        } catch {
            connectionLog.record("Comma-specific legacy Galaxy link unavailable")
            legacyMessage = (error as? BridgeError)?.localizedDescription ?? "Couldn’t get your comma’s Galaxy link. Check the connection and try again."
            return nil
        }
    }
    private func learnAddress() async {
        guard bluetooth.connected, Date().timeIntervalSince(lastAddressCheck) >= 20 || addressCheckSession != bluetooth.sessionIdentifier else { return }
        lastAddressCheck = Date()
        let session = bluetooth.sessionIdentifier
        addressCheckSession = session
        do {
            do {
                let identity = try await bluetooth.request(path: "/data/runtime.json", method: "GET", headers: [:], body: Data())
                guard wantsConnection, mode != .bluetooth, bluetooth.sessionIdentifier == session else { return }
                // Only the authenticated BLE peer may establish the automatic LAN identity.
                guard identity.status == 200, let value = LANTransport.deviceID(identity.bodyData) else {
                    networkDetails = "Automatic local discovery needs a registered device identifier. Bluetooth still works; enter comma’s IP manually for Wi-Fi."
                    return
                }
                lan.bind(to: value)

                identitySession = session
            }
            guard findAddressAutomatically, !lan.connected else { return }
            let response = try await bluetooth.request(path: "/api/local-access", method: "GET", headers: [:], body: Data())
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
                if transport.label != lastRoute { logConnection("Connection availability changed") }
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
    @ObservedObject var discovery: LANDiscovery
    @ObservedObject var galaxyPage: GalaxyPageDiagnostics
    private var editorFocused: Bool { model.tab == .galaxy && galaxyPage.landscapeEditor }
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase
    init(model: AppModel) {
        self.model = model; bluetooth = model.bluetooth; lan = model.lan; assets = model.assets; server = model.server; discovery = model.discovery; galaxyPage = model.galaxyPage
    }
    var body: some View {
        VStack(spacing: 0) {
            if !editorFocused {
            VStack(spacing: 14) {
                HStack {
                    if !model.developerMode && model.tab == .connections {
                        if model.opened {
                            Button { select(.galaxy) } label: {
                                Image(systemName: "chevron.left").font(.body.weight(.semibold))
                                    .frame(width: 36, height: 36)
                            }.buttonStyle(.plain).accessibilityLabel("Back to Galaxy")
                        }
                        Text("Settings").font(.title3.bold())
                    } else {
                        Text("StarPilot").font(.title3.bold())
                    }
                    Spacer()
                    HStack(spacing: 5) {
                        Circle().fill(model.transport.connected ? Color.green : Color.orange).frame(width: 6, height: 6)
                        Text(model.transport.label).font(.caption.weight(.medium))
                    }.padding(.horizontal, 10).padding(.vertical, 6)
                        .background(Color(uiColor: .secondarySystemBackground), in: Capsule())
                    if !model.developerMode && model.tab != .connections {
                        Button { select(.connections) } label: {
                            Image(systemName: "gearshape.fill").font(.body.weight(.semibold))
                                .frame(width: 36, height: 36)
                                .background(Color(uiColor: .secondarySystemBackground), in: Circle())
                        }.buttonStyle(.plain).accessibilityLabel("Settings")
                    }
                }
                if model.developerMode {
                    HStack(spacing: 4) {
                        ForEach(CompanionTab.allCases.filter { $0 != .connections }) { tab in
                            Button { select(tab) } label: {
                                VStack(spacing: 5) {
                                    Image(systemName: tab.icon).font(.system(size: 17, weight: .semibold))
                                    Text(tab.rawValue).font(.system(size: 10, weight: .semibold)).lineLimit(1).minimumScaleFactor(0.8)
                                }.frame(maxWidth: .infinity).padding(.vertical, 10)
                                    .foregroundStyle(model.tab == tab ? Color.white : Color.secondary)
                                    .background(model.tab == tab ? brandPurple : Color.clear, in: RoundedRectangle(cornerRadius: 12))
                            }.buttonStyle(.plain).accessibilityAddTraits(model.tab == tab ? .isSelected : [])
                        }
                        Button { select(.connections) } label: {
                            VStack(spacing: 4) {
                                Image(systemName: "gearshape.fill").font(.system(size: 17, weight: .semibold))
                                    .frame(width: 36, height: 36)
                                    .background(model.tab == .connections ? brandPurple : Color(uiColor: .tertiarySystemBackground), in: Circle())
                                    .foregroundStyle(model.tab == .connections ? Color.white : Color.secondary)
                                Text("Settings").font(.system(size: 10, weight: .semibold))
                            }.frame(width: 60).padding(.vertical, 4)
                                .foregroundStyle(model.tab == .connections ? Color.primary : Color.secondary)
                        }.buttonStyle(.plain).accessibilityAddTraits(model.tab == .connections ? .isSelected : [])
                    }.padding(4).background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16))
                }
            }.padding(.horizontal, 16).padding(.top, 10).padding(.bottom, 12)
            }
            ZStack {
                if model.opened, let url = server.url {
                    GalaxyWebView(url: url, requestKey: server.localSecret, diagnostics: model.galaxyPage,
                                  isActive: model.tab == .galaxy && scenePhase == .active) {
                        model.galaxyPage.report(server: server, connection: model.transport.label)
                    }
                        .opacity(model.tab == .galaxy ? 1 : 0)
                        .allowsHitTesting(model.tab == .galaxy)
                        .accessibilityHidden(model.tab != .galaxy)
                } else if model.opened && model.tab == .galaxy {
                    VStack(spacing: 16) {
                        if server.error.isEmpty { ProgressView("Reconnecting Galaxy…") }
                        else { Text(server.error).multilineTextAlignment(.center) }
                        Button("Retry Galaxy") { model.recoverGalaxy(automatic: false) }.buttonStyle(.bordered)
                    }.padding(24)
                }
                if model.developerMode && model.tab == .logs {
                    DeveloperLogsView(model: model, log: model.connectionLog)
                } else if model.developerMode && (model.tab == .live || model.tab == .diagnostics) {
                    CompanionView(diagnostics: model.diagnostics)
                } else if model.tab == .connections || !model.opened {
                    connectionView
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .background(Color(uiColor: .systemBackground))
        .ignoresSafeArea(.container, edges: editorFocused ? .all : [])
        .statusBarHidden(editorFocused)
        .onChange(of: model.showConnections) { _, show in
            if show { select(.connections); model.showConnections = false }
        }
        .onChange(of: model.showDiagnostics) { _, show in
            if show { if model.developerMode { select(.live) }; model.showDiagnostics = false }
        }
        .onChange(of: bluetooth.connected) { _, connected in if connected { model.openIfReady() } }
        .task(id: scenePhase) {
            model.setPhoneActive(scenePhase == .active)
            if scenePhase == .active { model.recoverGalaxy(reload: false); await model.assets.check() }
        }
    }
    private func select(_ requestedTab: CompanionTab) {
        let tab = requestedTab.isDeveloperPage && !model.developerMode ? (model.opened ? CompanionTab.galaxy : .connections) : requestedTab
        if tab != .connections { discovery.stop() }
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
                    HStack {
                        Button(discovery.searching ? "Searching Wi-Fi…" : "Find comma on Wi-Fi") { discovery.start() }
                            .buttonStyle(.bordered).disabled(discovery.searching || model.selectingDiscoveredComma)
                        if discovery.searching { Button("Stop") { discovery.stop() }.font(.caption) }
                    }
                    Text(discovery.status).font(.caption).foregroundStyle(.secondary)
                    ForEach(discovery.devices) { device in
                        Button { Task { await model.selectDiscoveredComma(device) } } label: {
                            HStack {
                                Image(systemName: "wifi")
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(device.name).font(.headline)
                                    Text(device.address).font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer(); Image(systemName: "chevron.right")
                            }.padding(14).background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 12))
                        }.buttonStyle(.plain).disabled(model.selectingDiscoveredComma)
                    }
                    Toggle("Find comma’s address over Bluetooth", isOn: $model.findAddressAutomatically)
                    Text("Comma IP address").font(.headline)
                    TextField("192.168.10.85", text: $model.address)
                        .keyboardType(.numbersAndPunctuation).textInputAutocapitalization(.never).autocorrectionDisabled()
                        .padding(14).background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 12))
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
                        .padding(14).background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 12))
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
                            }.padding(16).background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 12))
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
                Toggle("Developer Mode", isOn: $model.developerMode)
                Text("Show Live View, Diagnostics, and Dev / Logs on this iPhone.")
                    .font(.caption).foregroundStyle(.secondary)
                if model.developerMode {
                    Toggle("Fast Bluetooth reads", isOn: $bluetooth.fastReads)
                    if bluetooth.fastReadFallback {
                        Label("Fast reads paused after an error. Reliable reads are active after reconnecting. Switch fast reads off and on to try again.", systemImage: "arrow.triangle.2.circlepath")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Text("Experimental notification streaming for maximum transfer speed. Turn off to return to reliable reads. Changes apply to the next request.")
                        .font(.caption).foregroundStyle(.secondary)
                    Button("Open Dev / Logs") { select(.logs) }
                }
                Button("Check Galaxy updates") { Task { await assets.check() } }.disabled(assets.checking)
                Text("Screens are saved on your iPhone. GitHub updates apply next time you open Galaxy, without interrupting your current screen.")
                    .font(.caption).foregroundStyle(.secondary)
                if model.opened {
                    Button("Back to Galaxy") { select(.galaxy) }
                    Button("Disconnect") { model.disconnect(); select(.connections) }
                }
                Divider()
                Text("Legacy connection").font(.headline)
                Button {
                    Task {
                        if let url = await model.fetchLegacyURL() {
                            openURL(url) { accepted in
                                if !accepted { model.legacyMessage = "Couldn’t open your browser. Try again." }
                            }
                        }
                    }
                } label: {
                    Label(model.loadingLegacyURL ? "Getting Galaxy link…" : "Open legacy Galaxy", systemImage: "safari")
                }.buttonStyle(.bordered).disabled(model.loadingLegacyURL)
                if let url = model.legacyURL {
                    Text(url.absoluteString).font(.caption).textSelection(.enabled)
                }
                Text("Gets this comma’s unique Galaxy link and opens it in your default browser.")
                    .font(.caption).foregroundStyle(.secondary)
                if !model.legacyMessage.isEmpty {
                    Text(model.legacyMessage).font(.caption).foregroundStyle(.secondary)
                }
                if !server.error.isEmpty { Text(server.error).foregroundStyle(.red) }
            }.padding(24).frame(maxWidth: 560).frame(maxWidth: .infinity)
        }.background(Color(uiColor: .systemBackground)).tint(brandPurple)
    }
}

@MainActor
final class ConnectionEventLog: ObservableObject {
    @Published private(set) var events: [String] = []
    @Published var section = "Connections"
    @Published var detail = ""
    @Published var copied = false
    private var lastEvent = ""
    func record(_ event: String) {
        guard event != lastEvent else { return }
        lastEvent = event
        events.append("\(ISO8601DateFormatter().string(from: Date())) \(event.prefix(300))")
        if events.count > 100 { events.removeFirst(events.count - 100) }
    }
    func clear() { events.removeAll(); lastEvent = ""; detail = ""; copied = false }
    func report(model: AppModel) -> String {
        let info = Bundle.main.infoDictionary ?? [:]
        return """
        StarPilot connection diagnostics
        \(ISO8601DateFormatter().string(from: Date()))
        App: \(info["CFBundleShortVersionString"] ?? "?") (\(info["CFBundleVersion"] ?? "?"))
        iOS: \(UIDevice.current.systemVersion)
        Mode: \(model.mode.title)
        Selected route: \(model.transport.label)
        LAN verified: \(model.lan.connected)
        Bluetooth verified: \(model.bluetooth.connected)
        Recent connection events:
        \(events.joined(separator: "\n"))
        """
    }
}

private struct DeveloperLogsView: View {
    @ObservedObject var model: AppModel
    @ObservedObject var log: ConnectionEventLog
    private func selectedReport() -> String {
        switch log.section {
        case "Galaxy": return model.galaxyPage.report(server: model.server, connection: model.transport.label)
        case "Live View": return model.diagnostics.diagnosticLog()
        default: return log.report(model: model)
        }
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("Dev / Logs").font(.title2.bold())
                Text("Recent events stay in memory. Reports are shared only when you copy them.")
                    .font(.subheadline).foregroundStyle(.secondary)
                Picker("Report", selection: $log.section) {
                    ForEach(["Connections", "Galaxy", "Live View"], id: \.self) { Text($0).tag($0) }
                }.pickerStyle(.segmented)
                HStack {
                    Button(log.copied ? "Copied" : "Copy report", systemImage: "doc.on.doc") {
                        UIPasteboard.general.string = selectedReport(); log.copied = true
                    }.buttonStyle(.borderedProminent).tint(.purple)
                    Button("Refresh") { log.detail = selectedReport(); log.copied = false }.buttonStyle(.bordered)
                }
                Button("Copy all reports") {
                    UIPasteboard.general.string = [log.report(model: model), model.galaxyPage.report(server: model.server, connection: model.transport.label), model.diagnostics.diagnosticLog(), "Galaxy screen updates\n" + model.assets.status].joined(separator: "\n\n")
                    log.copied = true
                }
                Text(log.section == "Connections" ? log.report(model: model) : log.detail)
                    .font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(14).background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 12))
                Button("Clear connection history") { log.clear(); log.detail = selectedReport() }
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(20)
        }.background(Color(uiColor: .systemBackground))
            .onAppear { log.detail = selectedReport() }
            .onChange(of: log.section) { _, _ in log.detail = selectedReport(); log.copied = false }
    }
}
