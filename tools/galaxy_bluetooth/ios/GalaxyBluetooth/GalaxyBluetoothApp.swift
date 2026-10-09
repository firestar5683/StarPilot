import SwiftUI

@main
struct GalaxyBluetoothApp: App {
    @StateObject private var model = AppModel()
    var body: some Scene { WindowGroup { GalaxyRootView(model: model) } }
}

@MainActor
final class AppModel: ObservableObject {
    @Published var pairingKey = PairingKeyStore.load()
    let bluetooth: BluetoothTransport
    let server: LoopbackServer
    init() {
        let bluetooth = BluetoothTransport()
        self.bluetooth = bluetooth
        server = LoopbackServer(transport: bluetooth)
        server.start()
    }
}

struct GalaxyRootView: View {
    @ObservedObject var model: AppModel
    @ObservedObject var bluetooth: BluetoothTransport
    @ObservedObject var server: LoopbackServer

    init(model: AppModel) {
        self.model = model
        self.model = model
        bluetooth = model.bluetooth
        server = model.server
    }

    var body: some View {
        VStack(spacing: 0) {
            if bluetooth.connected, let url = server.url {
                HStack {
                    Image(systemName: "antenna.radiowaves.left.and.right").foregroundStyle(.green)
                    Text("Galaxy · Bluetooth").font(.subheadline.weight(.semibold))
                    Spacer()
                    Button("Disconnect") { bluetooth.disconnect() }.font(.subheadline)
                }
                .padding(.horizontal, 16).padding(.vertical, 10)
                GalaxyWebView(url: url, requestKey: server.localSecret)
            } else {
                connectionView
            }
        }
        .background(Color(red: 0.06, green: 0.05, blue: 0.09))
        .preferredColorScheme(.dark)
    }

    private var connectionView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                Image(systemName: "sparkles").font(.system(size: 54)).foregroundStyle(.purple)
                    .padding(.top, 56)
                Text("Galaxy").font(.largeTitle.bold())
                Text("Your comma, connected directly.").font(.title3).foregroundStyle(.secondary)
                Text("Start the Galaxy Bluetooth bridge on your comma and turn on Bluetooth in StarPilot. Paste its pairing key below, then scan.")
                    .font(.body).foregroundStyle(.secondary)
                VStack(alignment: .leading, spacing: 10) {
                    Text("Pairing key").font(.headline)
                    SecureField("64-character key from your comma", text: $model.pairingKey)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                        .font(.system(.body, design: .monospaced))
                        .padding(14).background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
                    Text("Saved securely on this iPhone after a successful connection.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Button(action: bluetooth.scan) {
                    HStack {
                        if bluetooth.isScanning { ProgressView().tint(.white) }
                        Text(bluetooth.isScanning ? "Scanning…" : "Scan for comma").fontWeight(.semibold)
                    }.frame(maxWidth: .infinity).padding(15)
                }
                .buttonStyle(.borderedProminent).tint(.purple)
                .disabled(bluetooth.isScanning || bluetooth.connecting)
                Text(bluetooth.status).font(.subheadline).foregroundStyle(.secondary)
                if !server.error.isEmpty { Text(server.error).foregroundStyle(.red) }
                ForEach(bluetooth.devices) { device in
                    Button {
                        bluetooth.connect(device, pairingKey: model.pairingKey)
                    } label: {
                        HStack {
                            Image(systemName: "car.side.fill").font(.title2)
                            VStack(alignment: .leading) {
                                Text(device.name).font(.headline)
                                Text("Bluetooth · \(device.signal) dBm").font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Image(systemName: "chevron.right")
                        }.padding(18).background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 16))
                    }.buttonStyle(.plain).disabled(bluetooth.connecting)
                }
                if bluetooth.connecting {
                    Button("Cancel connection") { bluetooth.disconnect() }
                }
                Button("Forget saved pairing key") {
                    PairingKeyStore.remove()
                    model.pairingKey = ""
                }.font(.caption).foregroundStyle(.secondary)
            }.padding(28)
        }
    }
}
