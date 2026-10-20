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
    @Published var showAudioPairing = false
    private var offerAudioPairing = false
    private var audioWindowOpen = false
    private let claimer = ClaimTransport()
    lazy var audioPairing = AudioPairing(transport: { [weak self] in self?.transport })
    lazy var phoneLocation: PhoneLocation = {
        let value = PhoneLocation(transport: { [weak self] in self?.transport })
        value.onSharingChanged = { [weak self] _ in self?.updateMonitoring() }
        return value
    }()
    @Published var tab: CompanionTab = .connections
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
    func setPhoneActive(_ active: Bool) { phoneActive = active; if !active { automaticLAN?.cancel() }; diagnostics.phoneActive = active; if !active { discovery.stop() }; updateMonitoring() }
    func setCarPlayActive(_ active: Bool) { carPlayActive = active; diagnostics.carPlayActive = active; updateMonitoring() }
    private func updateMonitoring() {
        // Sharing phone GPS keeps the app running in the background, so keep reconnecting too.
        if phoneActive || carPlayActive || phoneLocation.sharing {
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
            automaticLAN?.cancel(); lanProbeTask?.cancel()
            transport.mode = mode
            UserDefaults.standard.set(mode.rawValue, forKey: "galaxy.connection.mode")
            if mode == .lan { bluetooth.disconnect() }
            if mode == .bluetooth { discovery.stop(); lan.invalidate(reason: "Bluetooth-only mode selected") }
            logConnection("Connection mode selected: \(mode.title)")
        }
    }
    @Published var showConnections = false
    @Published var pairingInProgress = false
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
    private var localAddressNetwork = ""
    private var automaticLAN: Task<Void, Never>?
    private var lanProbeTask: Task<Void, Never>?
    private var lastLANDiscovery = Date.distantPast
    private var triedLANAddresses = Set<String>()
    /// One step for the app and music: comma's open pairing window gives this iPhone its key, then music is set up in the same window.
    func pairWithComma() {
        guard !pairingInProgress else { return }
        pairingInProgress = true
        offerAudioPairing = false
        showAudioPairing = false
        bluetooth.disconnect(reason: "Starting new phone pairing")
        connectionMessage = "Open Settings → Bluetooth → Pair phone on comma (or Pair phone in Galaxy). Looking for comma…"
        Task { @MainActor in
            defer { pairingInProgress = false }
            do { importClaim(try await claimer.claim(name: UIDevice.current.name)) }
            catch is CancellationError { connectionMessage = "Pairing cancelled." }
            catch { connectionMessage = error.localizedDescription }
        }
    }
    func cancelPairing() { claimer.cancel() }
    private func importClaim(_ outcome: ClaimTransport.Outcome) {
        // The key is saved only after the encrypted handshake, like any imported key.
        opened = false
        wantsConnection = true
        bluetooth.forgetSavedDevice()
        PairingKeyStore.stage(PairingCode(key: outcome.result.key, id: outcome.result.id))
        lan.clearEndpoint()
        lan.bind(to: nil)
        address = ""
        identitySession = ""
        addressCheckSession = ""
        UserDefaults.standard.removeObject(forKey: "galaxy.comma.identity")
        UserDefaults.standard.removeObject(forKey: "galaxy.lan.address")
        UserDefaults.standard.set(outcome.deviceID.uuidString, forKey: "galaxy.bluetooth.device")
        pairingKey = outcome.result.key
        if mode == .lan { mode = .automatic }
        connectionMessage = "Paired. Connecting to comma…"
        offerAudioPairing = true
        audioWindowOpen = true
        lastReconnect = Date()
        bluetooth.reconnectSaved(pairingKey: pairingKey)
        if !bluetooth.connecting { bluetooth.scan() }
    }
    init() {
        let bluetooth = BluetoothTransport()
        let lan = LANTransport()
        let transport = PreferredTransport(lan: lan, bluetooth: bluetooth, invalidateLAN: { lan.invalidate(reason: $0) })
        let assets = GalaxyAssetStore()
        self.bluetooth = bluetooth; self.lan = lan; self.transport = transport; self.assets = assets
        lan.bind(to: UserDefaults.standard.string(forKey: "galaxy.comma.identity"))
        let cache = GalaxyReadCache(transport: transport, sessionID: {
            transport.usesLAN ? "lan-" + lan.generation : "ble-" + bluetooth.sessionIdentifier
        })
        server = LoopbackServer(transport: cache, webRoot: assets.readyRoot ?? assets.bundledRoot)
        transport.mode = mode
        diagnostics.transport = transport; diagnostics.lan = lan
        galaxyPage.recover = { [weak self] automatic in self?.recoverGalaxy(automatic: automatic) }
        server.start()
        discovery.onEvent = { [weak self] reason in self?.connectionLog.record(reason) }
        discovery.onDevicesChanged = { [weak self] in self?.discoverAutomaticLAN() }
        lan.onEvent = { [weak self] reason in self?.logConnection(reason) }
        bluetooth.onEvent = { [weak self] reason in self?.logConnection(reason) }
        claimer.onEvent = { [weak self] reason in self?.connectionLog.record(reason) }
        pathMonitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in
                guard let self else { return }
                let route = path.usesInterfaceType(.wifi) ? "Wi-Fi" : path.usesInterfaceType(.cellular) ? "cellular" : "other"
                let reason = "iOS network path updated: \(path.status == .satisfied ? "available" : "unavailable"), \(route), expensive=\(path.isExpensive), constrained=\(path.isConstrained)"
                let interfaces = path.availableInterfaces
                    .filter { path.usesInterfaceType($0.type) }
                    .map { "\($0.name):\($0.index)" }.sorted().joined(separator: ",")
                let fingerprint = "\(path.status)|\(route)|\(interfaces)|ipv4=\(path.supportsIPv4)|\(LANDiscovery.networkSignature())"
                guard fingerprint != self.lastNetworkPath else { return }
                self.lastNetworkPath = fingerprint
                self.connectionLog.record(reason)
                self.automaticLAN?.cancel(); self.lanProbeTask?.cancel()
                self.discovery.networkChanged()
                self.triedLANAddresses.removeAll()
                self.lastLANDiscovery = .distantPast
                self.lan.invalidate(reason: reason)
                self.lastAddressCheck = .distantPast
                self.discoverAutomaticLAN()
            }
        }
        pathMonitor.start(queue: .main)
        updateMonitoring()
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
            localAddressNetwork = ""
            connectionMessage = "Checking your comma…"
        } catch { connectionMessage = error.localizedDescription }
    }
    func startAudioPairing() {
        guard transport.connected else { return }
        showAudioPairing = true
        let windowOpen = audioWindowOpen
        audioWindowOpen = false
        audioPairing.start(windowOpen: windowOpen)
    }
    private var openingGalaxy = false
    @Published private(set) var matchingGalaxy = false
    private var lastGalaxyMatch = Date.distantPast

    func applyMatchedGalaxy() {
        guard opened, let root = assets.readyRoot, root != assets.inUseRoot else { return }
        assets.inUseRoot = root
        server.useWebRoot(root)
        recoverGalaxy(automatic: false)
    }

    func checkGalaxyUpdates() async {
        guard wantsConnection, transport.connected, !matchingGalaxy else { return }
        matchingGalaxy = true
        lastGalaxyMatch = Date()
        defer { matchingGalaxy = false }
        let bleSession = bluetooth.sessionIdentifier
        let lanSession = lan.generation
        do {
            let response = try await transport.request(path: "/api/software/status?history=0", method: "GET", headers: [:], body: Data())
            guard wantsConnection, transport.connected, bluetooth.sessionIdentifier == bleSession, lan.generation == lanSession else { return }
            guard response.status == 200 else { throw BridgeError.message("Comma’s Galaxy version could not be read.") }
            let source = try GalaxySource.parse(response.bodyData)
            await assets.check(source: source, stillCurrent: { self.wantsConnection && self.transport.connected && self.bluetooth.sessionIdentifier == bleSession && self.lan.generation == lanSession })
        } catch {
            if bluetooth.sessionIdentifier == bleSession && lan.generation == lanSession {
                assets.unavailable("Couldn’t match Galaxy to comma.")
            }
        }
    }
    func openIfReady() {
        guard wantsConnection, transport.connected, !opened, !openingGalaxy else { return }
        openingGalaxy = true
        Task { @MainActor in
            defer { openingGalaxy = false }
            await checkGalaxyUpdates()
            guard wantsConnection, transport.connected, !opened else { return }
            let root = assets.readyRoot ?? assets.bundledRoot
            assets.inUseRoot = root
            server.useWebRoot(root)
            opened = true
        }
    }
    func disconnect() {
        legacyURL = nil
        automaticLAN?.cancel(); lanProbeTask?.cancel()
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
            lan.bind(to: candidate.verifiedDeviceID)
            UserDefaults.standard.set(candidate.verifiedDeviceID, forKey: "galaxy.comma.identity")
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
        let networkPath = lastNetworkPath
        addressCheckSession = session
        do {
            if identitySession != session {
                let identity = try await bluetooth.request(path: "/data/runtime.json", method: "GET", headers: [:], body: Data())
                guard !Task.isCancelled, wantsConnection, mode != .bluetooth, bluetooth.sessionIdentifier == session else { return }
                // Only the authenticated BLE peer may establish the automatic LAN identity.
                guard identity.status == 200, let value = LANTransport.deviceID(identity.bodyData) else {
                    networkDetails = "Automatic local discovery needs a registered device identifier. Bluetooth still works; enter comma’s IP manually for Wi-Fi."
                    return
                }
                lan.bind(to: value)
                UserDefaults.standard.set(value, forKey: "galaxy.comma.identity")

                identitySession = session
            }
            let network = session + "|" + networkPath
            guard findAddressAutomatically, !lan.connected, localAddressNetwork != network else { return }
            let generation = lan.generation
            let response = try await bluetooth.request(path: "/api/local-access", method: "GET", headers: [:], body: Data())
            guard !Task.isCancelled, wantsConnection, mode != .bluetooth, bluetooth.sessionIdentifier == session, response.status == 200,
                  lastNetworkPath == networkPath, lan.generation == generation, !lan.connected,
                  !response.bodyData.isEmpty else { return }
            if let ip = LANTransport.reportedAddress(response.bodyData) {
                localAddressNetwork = network
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
    private func discoverAutomaticLAN() {
        guard phoneActive, wantsConnection, mode == .automatic,
              !pairingInProgress, !selectingDiscoveredComma, !lan.connected,
              let identity = lan.expectedDeviceID else { return }
        if !discovery.searching, Date().timeIntervalSince(lastLANDiscovery) >= 20 {
            lastLANDiscovery = Date()
            triedLANAddresses.removeAll()
            discovery.start()
        }
        guard automaticLAN == nil else { return }
        let addresses = discovery.devices.map(\.address).filter { !triedLANAddresses.contains($0) }
        guard !addresses.isEmpty else { return }
        triedLANAddresses.formUnion(addresses)
        let generation = lan.generation
        automaticLAN = Task { @MainActor in
            defer { self.automaticLAN = nil }
            let stillCurrent = {
                self.phoneActive && self.wantsConnection && self.mode == .automatic
                    && !self.pairingInProgress && !self.selectingDiscoveredComma && !self.lan.connected
                    && self.lan.generation == generation && self.lan.expectedDeviceID == identity
            }
            let address = await LANDiscoveryMatch.first(addresses: addresses, expectedDeviceID: identity, stillCurrent: stillCurrent) { address, identity in
                let candidate = LANTransport()
                candidate.bind(to: identity)
                guard (try? candidate.configure(address: address)) != nil else { return false }
                return await candidate.probe()
            }
            guard let address, !Task.isCancelled, stillCurrent() else { return }
            do { try self.lan.configure(address: address) } catch { return }
            self.address = address
            UserDefaults.standard.set(address, forKey: "galaxy.lan.address")
            if await self.lan.probe() {
                self.discovery.stop()
                self.connectionLog.record("Automatic Wi-Fi discovery verified the paired comma")
            }
        }
    }

    private func probeLocalConnection() {
        guard lanProbeTask == nil else { return }
        lanProbeTask = Task { @MainActor in
            defer { self.lanProbeTask = nil }
            await self.learnAddress()
            guard !Task.isCancelled, self.wantsConnection, self.mode != .bluetooth else { return }
            if self.lan.endpoint == nil, !self.address.isEmpty {
                do { try self.lan.configure(address: self.address) }
                catch { self.connectionMessage = error.localizedDescription }
            }
            _ = await self.lan.probe()
            if !Task.isCancelled, self.lan.connected { self.discovery.stop() }
        }
    }

    func monitor() async {
        while !Task.isCancelled {
            if wantsConnection && !pairingInProgress {
                if mode != .lan, !bluetooth.connected, !bluetooth.connecting, !bluetooth.isScanning,
                   !pairingKey.isEmpty, Date().timeIntervalSince(lastReconnect) >= 25 {
                    lastReconnect = Date()
                    bluetooth.reconnectSaved(pairingKey: pairingKey)
                }
                if mode != .bluetooth {
                    discoverAutomaticLAN()
                    probeLocalConnection()
                }
                guard !pairingInProgress else { continue }
                if transport.label != lastRoute { logConnection("Connection availability changed") }
                if transport.connected {
                    openIfReady()
                    if Date().timeIntervalSince(lastGalaxyMatch) > 60 && !openingGalaxy {
                        Task { await self.checkGalaxyUpdates() }
                    }
                    connectionMessage = "Connected over \(transport.label)."
                    if offerAudioPairing { offerAudioPairing = false; startAudioPairing() }
                } else if mode == .bluetooth {
                    connectionMessage = "Reconnecting over Bluetooth. If you forgot this phone on comma, open Pair phone on comma and Pair with comma here."
                } else {
                    connectionMessage = "Wi-Fi unavailable. Pair over Bluetooth below, or check your comma’s IP address."
                }
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
    @State private var hasVisitedGalaxy = false
    private var galaxyColorScheme: ColorScheme? {
        guard model.tab == .galaxy, let dark = galaxyPage.darkAppearance else { return nil }
        return dark ? .dark : .light
    }
    private var editorFocused: Bool { model.tab == .galaxy && galaxyPage.landscapeEditor }
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase
    init(model: AppModel) {
        self.model = model; bluetooth = model.bluetooth; lan = model.lan; assets = model.assets; server = model.server; discovery = model.discovery; galaxyPage = model.galaxyPage
    }
    var body: some View {
        VStack(spacing: 0) {
            if !editorFocused && model.tab != .connections {
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
                        Text("StarPilot BT").font(.title3.bold())
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
                    ConnectionSettingsView(model: model, returningFromGalaxy: hasVisitedGalaxy, select: select)
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .background(model.tab == .galaxy && galaxyPage.darkAppearance == true
            ? Color(red: 0.06, green: 0.05, blue: 0.09) : Color(uiColor: .systemBackground))
        .preferredColorScheme(galaxyColorScheme)
        .ignoresSafeArea(.container, edges: editorFocused ? .all : [])
        .statusBarHidden(editorFocused)
        .onChange(of: model.showConnections) { _, show in
            if show { select(.connections); model.showConnections = false }
        }
        .onChange(of: model.showDiagnostics) { _, show in
            if show { if model.developerMode { select(.live) }; model.showDiagnostics = false }
        }
        .onChange(of: bluetooth.connected) { _, connected in if connected { model.openIfReady() } }
        .sheet(isPresented: $model.showAudioPairing, onDismiss: { model.audioPairing.dismiss() }) {
            AudioPairingSheet(pairing: model.audioPairing) { model.showAudioPairing = false }
        }
        .task(id: scenePhase) {
            model.setPhoneActive(scenePhase == .active)
            if scenePhase == .active { model.recoverGalaxy(reload: false); await model.checkGalaxyUpdates() }
        }
    }
    private func select(_ requestedTab: CompanionTab) {
        let tab = requestedTab.isDeveloperPage && !model.developerMode ? (model.opened ? CompanionTab.galaxy : .connections) : requestedTab
        if tab != .connections { discovery.stop() }
        model.tab = tab
        if tab == .galaxy { hasVisitedGalaxy = true; model.applyMatchedGalaxy() }
        model.diagnostics.live = tab == .live
    }
    private let brandPurple = Color(red: 139.0 / 255, green: 92.0 / 255, blue: 246.0 / 255)


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
        StarPilot BT connection diagnostics
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
