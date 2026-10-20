import SwiftUI

struct AudioPairingSheet: View {
    @ObservedObject var pairing: AudioPairing
    let close: () -> Void

    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: "music.note").font(.system(size: 40))
            Text("Bluetooth music").font(.title3.weight(.semibold))
            switch pairing.phase {
            case .idle, .opening:
                ProgressView("Asking comma to open pairing…")
            case .waiting(let name):
                Text("On your iPhone, open **Settings → Bluetooth** and select **\(name)** to pair music.")
                    .multilineTextAlignment(.center)
                ProgressView()
                Text("Already says Connected? In Control Center, check whether comma is available as an audio output.")
                    .font(.callout).multilineTextAlignment(.center)
            case .confirm(let code, _, _):
                Text("Check that comma and this iPhone both show").multilineTextAlignment(.center)
                Text(code).font(.system(size: 34, weight: .semibold, design: .monospaced))
                HStack {
                    Button("Cancel") { pairing.respond(accepted: false) }.buttonStyle(.bordered)
                    Button("Pair") { pairing.respond(accepted: true) }.buttonStyle(.borderedProminent)
                }
            case .done:
                Text("Bluetooth music paired. In Control Center, choose comma as the audio output.").multilineTextAlignment(.center)
            case .connected:
                Text("Music connected. This iPhone is already using comma as its Bluetooth audio output.").multilineTextAlignment(.center)
            case .message(let text):
                Text(text).multilineTextAlignment(.center)
            }
            Button((pairing.phase == .done || pairing.phase == .connected) ? "Done" : "Close") { close() }.padding(.top, 6)
        }.padding(24).presentationDetents([.medium, .large])
    }
}
