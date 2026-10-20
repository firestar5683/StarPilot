import SwiftUI

struct AudioPairingSheet: View {
    @ObservedObject var pairing: AudioPairing
    let close: () -> Void

    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: "music.note").font(.system(size: 40))
            Text("Music through comma").font(.title3.weight(.semibold))
            switch pairing.phase {
            case .idle, .opening:
                ProgressView("Asking comma to open pairing…")
            case .waiting(let name):
                Text("Open Settings → Bluetooth on this iPhone and tap **\(name)**. This stays open for two minutes.")
                    .multilineTextAlignment(.center)
                ProgressView()
                Button("Open Settings") { if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) } }
                    .buttonStyle(.bordered)
            case .confirm(let code, _, _):
                Text("Check that comma and this iPhone both show").multilineTextAlignment(.center)
                Text(code).font(.system(size: 34, weight: .semibold, design: .monospaced))
                HStack {
                    Button("Cancel") { pairing.respond(accepted: false) }.buttonStyle(.bordered)
                    Button("Pair") { pairing.respond(accepted: true) }.buttonStyle(.borderedProminent)
                }
            case .done:
                Text("Music is ready. In Control Center, choose comma as the audio output.").multilineTextAlignment(.center)
            case .message(let text):
                Text(text).multilineTextAlignment(.center)
            }
            Button(pairing.phase == .done ? "Done" : "Close") { close() }.padding(.top, 6)
        }.padding(24).presentationDetents([.medium])
    }
}
