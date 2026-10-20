import SwiftUI

struct ConnectionSettingsView: View {
    @ObservedObject var model: AppModel
    @ObservedObject var bluetooth: BluetoothTransport
    @ObservedObject var lan: LANTransport
    @ObservedObject var assets: GalaxyAssetStore
    @ObservedObject var server: LoopbackServer
    @ObservedObject var discovery: LANDiscovery
    @ObservedObject var location: PhoneLocation
    @ObservedObject var audio: AudioPairing
    let returningFromGalaxy: Bool
    let select: (CompanionTab) -> Void
    @Environment(\.openURL) private var openURL
    @State private var advanced = false
    @State private var confirmForget = false
    @State private var checked = false
    @State private var openAfterReconnect = false

    private let accent = Color(red: 0.68, green: 0.48, blue: 0.96)
    private let background = Color(red: 0.035, green: 0.035, blue: 0.078)
    private let panel = Color(red: 0.09, green: 0.065, blue: 0.145)
    private let muted = Color(red: 0.70, green: 0.65, blue: 0.77)
    private var connected: Bool { model.transport.connected }
    private var pairing: Bool { model.pairingInProgress }
    private var needsPairing: Bool { model.mode != .lan && model.pairingKey.isEmpty }
    private var connecting: Bool { !connected && (bluetooth.connecting || bluetooth.isScanning) }
    private var primaryTitle: String {
        if pairing { return "Pairing…" }
        if connected { return model.opened ? "Open Galaxy" : "Preparing Galaxy…" }
        if connecting { return "Connecting…" }
        return needsPairing ? "Pair with comma" : "Reconnect"
    }
    private var checking: Bool { model.matchingGalaxy || assets.checking }
    private var status: String { pairing ? "Pairing with comma…" : connected ? "Connected via \(model.transport.label)" : connecting ? "Connecting to comma…" : "Not connected" }

    init(model: AppModel, returningFromGalaxy: Bool, select: @escaping (CompanionTab) -> Void) {
        self.model = model; self.returningFromGalaxy = returningFromGalaxy; self.select = select
        bluetooth = model.bluetooth; lan = model.lan; assets = model.assets; server = model.server
        discovery = model.discovery; location = model.phoneLocation; audio = model.audioPairing
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 8) {
                HStack {
                    if returningFromGalaxy && model.opened {
                        Button { select(.galaxy) } label: {
                            Image(systemName: "chevron.left").frame(width: 44, height: 44)
                        }.accessibilityLabel("Back to Galaxy")
                    } else { Color.clear.frame(width: 44, height: 44) }
                    Spacer(minLength: 0)
                    Text(returningFromGalaxy ? "Settings" : "StarPilot BT")
                        .font(.custom("Sora-Regular", size: 22).weight(.medium)).lineLimit(1)
                    Spacer(minLength: 0)
                    Color.clear.frame(width: 44, height: 44)
                }
                ConnectionOrbit(route: connected ? model.transport.label : "", pairing: pairing)
                    .padding(.bottom, 10)
                connectionPanel
                Text("PREFERENCES").font(.system(size: 11, weight: .medium)).tracking(1.2)
                    .foregroundStyle(muted).frame(maxWidth: .infinity, alignment: .leading)
                preferences
                DisclosureGroup(isExpanded: $advanced) { advancedControls.padding(.top, 8) } label: {
                    Text("Advanced connection options").font(.system(size: 13)).frame(minHeight: 30)
                }.padding(.horizontal, 14).padding(.vertical, 7).background(panel, in: RoundedRectangle(cornerRadius: 16))
                    .overlay(RoundedRectangle(cornerRadius: 16).stroke(accent.opacity(0.16)))
                HStack(spacing: 18) {
                    Button(model.loadingLegacyURL ? "Getting link…" : "Legacy Galaxy") {
                        Task { if let url = await model.fetchLegacyURL() {
                            openURL(url) { accepted in if !accepted { model.legacyMessage = "Couldn’t open your browser. Try again." } }
                        } }
                    }.disabled(model.loadingLegacyURL || pairing)
                    Link("Support", destination: URL(string: "https://wiki.firestar.link/ticketsystem/")!)
                    Link("Privacy", destination: URL(string: "https://github.com/natehuby76/ios-clone/blob/codex/secretgood-galaxy/docs/privacy.md")!)
                }.font(.system(size: 12)).frame(minHeight: 44)
                if !model.legacyMessage.isEmpty { message(model.legacyMessage) }
                if !server.error.isEmpty { message(server.error) }
                Text("StarPilot BT · \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "")")
                    .font(.system(size: 11)).foregroundStyle(muted)
            }.padding(.horizontal, 18).padding(.top, 0).padding(.bottom, 12)
                .frame(maxWidth: 460).frame(maxWidth: .infinity)
        }.scrollBounceBehavior(.basedOnSize).background(background).foregroundStyle(Color.white)
            .onChange(of: connected) { _, _ in openReconnectedGalaxy() }
            .onChange(of: model.opened) { _, _ in openReconnectedGalaxy() }
            .onChange(of: model.wantsConnection) { _, value in if !value { openAfterReconnect = false } }
            .tint(accent).preferredColorScheme(.dark)
            .confirmationDialog("Forget Bluetooth pairing?", isPresented: $confirmForget, titleVisibility: .visible) {
                Button("Forget pairing", role: .destructive) {
                    model.disconnect(); bluetooth.forgetSavedDevice(); PairingKeyStore.remove(); model.pairingKey = ""
                    lan.bind(to: nil); UserDefaults.standard.removeObject(forKey: "galaxy.comma.identity")
                }
            } message: { Text("This removes the saved app pairing. Pair your phone again to reconnect.") }
    }

    private func openReconnectedGalaxy() {
        guard openAfterReconnect, connected, model.opened else { return }
        openAfterReconnect = false
        select(.galaxy)
    }

    private var connectionPanel: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Image(model.transport.label == "Wi-Fi" ? "ConnectionWiFi" : "ConnectionBluetooth").renderingMode(.template).resizable().scaledToFit().frame(width: 20, height: 20).foregroundStyle(accent)
                    .frame(width: 38, height: 38).background(accent.opacity(0.15), in: RoundedRectangle(cornerRadius: 12))
                VStack(alignment: .leading, spacing: 2) {
                    Text("Your comma").font(.system(size: 17, weight: .medium))
                    Text(status).font(.system(size: 11)).foregroundStyle(muted).accessibilityAddTraits(.updatesFrequently)
                }
                Spacer(minLength: 4)
                Text(pairing ? "Pairing…" : connected ? "Connected" : connecting ? "Connecting…" : "Offline")
                    .font(.system(size: 10, weight: .medium)).foregroundStyle(pairing ? accent : connected ? .mint : muted)
                    .padding(.horizontal, 9).padding(.vertical, 6)
                    .background((pairing ? accent : connected ? Color.mint : muted).opacity(0.13), in: Capsule())
            }
            Picker("Connection mode", selection: $model.mode) {
                Text("Automatic").tag(ConnectionMode.automatic)
                Text("Bluetooth").tag(ConnectionMode.bluetooth)
                Text("Wi-Fi").tag(ConnectionMode.lan)
            }.pickerStyle(.segmented).disabled(pairing)
            Text(pairing ? "Keep Pair phone open on comma." : model.mode == .automatic ? "Wi-Fi first, Bluetooth as backup." : model.mode == .bluetooth ? "Local controls over Bluetooth." : "Uses your local Wi-Fi network.")
                .font(.system(size: 11)).foregroundStyle(muted)
            Button {
                if connected && model.opened { select(.galaxy) }
                else if needsPairing { model.pairWithComma() }
                else { openAfterReconnect = true; model.connect(); openReconnectedGalaxy() }
            } label: {
                HStack(spacing: 7) {
                    if pairing { PairingSignal() }
                    else if connecting || (connected && !model.opened) { ProgressView().controlSize(.small) }
                    Text(primaryTitle)
                }.font(.system(size: 12, weight: .medium)).frame(maxWidth: .infinity, minHeight: 44)
                    .background(LinearGradient(colors: [Color(red: 0.73, green: 0.55, blue: 1), accent], startPoint: .leading, endPoint: .trailing), in: Capsule())
                    .foregroundStyle(Color(red: 0.12, green: 0.06, blue: 0.19))
            }.buttonStyle(.plain).disabled(pairing || connecting || (connected && !model.opened))
            if pairing {
                Button("Cancel pairing") { model.cancelPairing() }.font(.system(size: 12)).frame(maxWidth: .infinity, minHeight: 30)
            } else if model.connectionMessage != "Connected over \(model.transport.label)." && !connected {
                message(model.connectionMessage)
            }
        }.padding(14).background(LinearGradient(colors: [panel, background], startPoint: .topLeading, endPoint: .bottomTrailing), in: RoundedRectangle(cornerRadius: 22))
            .overlay(RoundedRectangle(cornerRadius: 22).stroke(accent.opacity(0.25)))
    }

    private var preferences: some View {
        VStack(spacing: 0) {
            row("music.note", title: "Phone music", subtitle: audio.phase == .connected ? "Comma is the audio output" : pairing ? "Waiting for app pairing" : "Audio not verified") {
                Button("Set up") { model.startAudioPairing() }.disabled(!connected || pairing).font(.system(size: 12)).frame(minHeight: 44)
            }
            separator
            row("location", title: "Share phone location", subtitle: location.status.isEmpty ? "Optional" : location.status) {
                Toggle("Share phone location", isOn: Binding(get: { location.sharing }, set: { location.setSharing($0) })).labelsHidden()
            }
            separator
            row("rectangle.on.rectangle", title: "Galaxy screens", subtitle: pairing ? "Waiting for pairing" : checking ? "Checking version…" : checked && assets.readyRoot != nil ? "Up to date · just checked" : assets.readyRoot != nil && connected ? "Matched to your comma" : "Bundled screens") {
                Button {
                    Task { await model.checkGalaxyUpdates(); checked = true }
                } label: {
                    if checking { ProgressView().controlSize(.small).accessibilityLabel("Checking Galaxy") }
                    else { Text(checked ? assets.readyRoot != nil ? "✓ Checked" : "Retry" : "Check") }
                }.font(.system(size: 12)).frame(minHeight: 44).disabled(checking || !connected || pairing)
            }
            if checked && !checking && assets.readyRoot == nil { message(assets.status).padding(.horizontal, 14).padding(.bottom, 10) }
            separator
            row("chevron.left.forwardslash.chevron.right", title: "Developer mode", subtitle: "Diagnostics and logs") {
                Toggle("Developer mode", isOn: $model.developerMode).labelsHidden()
            }
        }.background(panel, in: RoundedRectangle(cornerRadius: 20))
            .overlay(RoundedRectangle(cornerRadius: 20).stroke(accent.opacity(0.23)))
    }

    private var advancedControls: some View {
        VStack(alignment: .leading, spacing: 12) {
            if model.developerMode {
                Toggle("Fast Bluetooth reads", isOn: $bluetooth.fastReads)
                message(bluetooth.fastReadFallback ? "Fast reads paused after an error. Reliable reads are active." : "Experimental. Turn off to use reliable reads.")
                Button("Open Dev / Logs") { select(.logs) }
                Divider()
            }
            if model.mode != .bluetooth {
                HStack {
                    Button(discovery.searching ? "Stop discovery" : "Find comma on Wi-Fi") {
                        if discovery.searching { discovery.stop() } else { discovery.start() }
                    }.disabled(model.selectingDiscoveredComma || pairing)
                }
                message(discovery.status)
                ForEach(discovery.devices) { device in
                    Button { Task { await model.selectDiscoveredComma(device) } } label: {
                        VStack(alignment: .leading) { Text(device.name); Text(device.address).font(.caption) }
                    }.disabled(model.selectingDiscoveredComma || pairing)
                }
                Toggle("Find address over Bluetooth", isOn: $model.findAddressAutomatically)
                TextField("Comma IP address", text: $model.address).keyboardType(.numbersAndPunctuation)
                    .textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder)
                message(lan.status)
            }
            if model.mode != .lan {
                Button("Pair again") { model.pairWithComma() }.disabled(pairing)
                SecureField("64-character pairing key", text: $model.pairingKey)
                    .textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder)
                Button(bluetooth.isScanning ? "Scanning…" : "Scan for comma") { model.wantsConnection = true; bluetooth.scan() }
                    .disabled(bluetooth.isScanning || bluetooth.connecting || pairing)
                message(bluetooth.status)
                ForEach(bluetooth.devices) { device in
                    Button(device.name) {
                        model.opened = false; model.wantsConnection = true; lan.clearEndpoint(); lan.bind(to: nil); model.address = ""
                        UserDefaults.standard.removeObject(forKey: "galaxy.comma.identity")
                        UserDefaults.standard.removeObject(forKey: "galaxy.lan.address")
                        bluetooth.connect(device, pairingKey: model.pairingKey)
                    }.disabled(bluetooth.connecting || pairing)
                }
                if bluetooth.connecting { Button("Cancel Bluetooth connection") { bluetooth.disconnect() } }
                Button("Forget Bluetooth pairing", role: .destructive) { confirmForget = true }.disabled(pairing)
            }
            message(assets.status)
            if let url = model.legacyURL { Text(url.absoluteString).font(.caption).textSelection(.enabled) }
            Button("Disconnect") { model.disconnect() }.disabled(pairing)
        }.font(.system(size: 13)).buttonStyle(.bordered).frame(maxWidth: .infinity, alignment: .leading)
    }

    private var separator: some View { Rectangle().fill(accent.opacity(0.12)).frame(height: 1).padding(.leading, 42) }
    private func message(_ text: String) -> some View {
        Text(text).font(.system(size: 11)).foregroundStyle(muted).fixedSize(horizontal: false, vertical: true)
    }
    private func row<Control: View>(_ symbol: String, title: String, subtitle: String, @ViewBuilder control: () -> Control) -> some View {
        HStack(spacing: 10) {
            Image(systemName: symbol).foregroundStyle(accent).frame(width: 20)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.system(size: 13, weight: .medium))
                Text(subtitle).font(.system(size: 11)).foregroundStyle(muted).fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 4)
            control().fixedSize(horizontal: true, vertical: false)
        }.padding(.horizontal, 13).padding(.vertical, 6).frame(minHeight: 56)
    }
}

private struct PairingSignal: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pulse = false
    var body: some View {
        HStack(alignment: .bottom, spacing: 2) {
            ForEach(0..<3) { index in
                Capsule().frame(width: 3, height: CGFloat(5 + index * 4))
                    .opacity(reduceMotion || pulse ? 1 : 0.25)
                    .animation(reduceMotion ? nil : .easeInOut(duration: 0.7).repeatForever(autoreverses: true).delay(Double(index) * 0.15), value: pulse)
            }
        }.frame(height: 15).onAppear { pulse = true }.accessibilityHidden(true)
    }
}

private struct ConnectionOrbit: View {
    let route: String
    let pairing: Bool
    private let purple = Color(red: 0.68, green: 0.48, blue: 0.96)
    var body: some View {
        ZStack {
            Ellipse().stroke(purple.opacity(0.5), lineWidth: 1).frame(width: 232, height: 64).rotationEffect(.degrees(12)).position(x: 132, y: 48)
            Ellipse().stroke(purple.opacity(0.35), style: StrokeStyle(lineWidth: 1, dash: [2, 4]))
                .frame(width: 258, height: 76).rotationEffect(.degrees(-9)).position(x: 132, y: 48)
            Circle().fill(LinearGradient(colors: [Color(red: 0.74, green: 0.53, blue: 1), purple], startPoint: .topLeading, endPoint: .bottomTrailing))
                .overlay(Circle().stroke(Color.white.opacity(0.6)))
                .overlay(Image("StarPilotMark").resizable().scaledToFit().padding(5))
                .shadow(color: purple.opacity(0.5), radius: 16).frame(width: 60, height: 60).position(x: 132, y: 43)
            node("ConnectionWiFi", angle: 155, active: route == "Wi-Fi")
            node("ConnectionBluetooth", angle: 110, active: route == "Bluetooth" || pairing)
            node("ConnectionNetwork", angle: -25, active: false)
        }.frame(width: 264, height: 88).accessibilityHidden(true)
    }
    private func node(_ symbol: String, angle: Double, active: Bool) -> some View {
        let theta = angle * .pi / 180, rotation = 12.0 * .pi / 180
        let x = 132 + 116 * cos(theta) * cos(rotation) - 32 * sin(theta) * sin(rotation)
        let y = 48 + 116 * cos(theta) * sin(rotation) + 32 * sin(theta) * cos(rotation)
        return Image(symbol).renderingMode(.template).resizable().scaledToFit().frame(width: 15, height: 15).foregroundStyle(active ? Color.white : Color.white.opacity(0.65))
            .frame(width: 30, height: 30).background(Color(red: 0.09, green: 0.075, blue: 0.15), in: Circle())
            .overlay(Circle().stroke(Color.white.opacity(active ? 0.75 : 0.4)))
            .shadow(color: purple.opacity(active ? 0.35 : 0), radius: 7).position(x: x, y: y)
    }
}
