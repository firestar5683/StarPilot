import Foundation

struct PairingCode: Decodable {
    let type: String
    let version: Int
    let key: String

    static func parse(_ text: String) throws -> String {
        guard text.utf8.count <= 512, let data = text.data(using: .utf8),
              let value = try? JSONDecoder().decode(Self.self, from: data),
              value.type == "galaxy-bluetooth", value.version == 1,
              value.key.utf8.count == 64,
              value.key.utf8.allSatisfy({ (48...57).contains($0) || (65...70).contains($0) || (97...102).contains($0) }) else {
            throw NSError(domain: "GalaxyPairing", code: 1, userInfo: [NSLocalizedDescriptionKey:
                "This isn’t a Galaxy Bluetooth pairing code. Open Pair phone on your comma."])
        }
        return value.key.lowercased()
    }
}

#if canImport(VisionKit) && os(iOS)
import SwiftUI
import VisionKit
import AVFoundation

@MainActor
private final class ScannerState: ObservableObject {
    @Published var ready = false
    @Published var message = "Open Settings → Pair phone on comma, then point the camera at its code."
}

struct PairingScannerSheet: View {
    let onKey: (String) -> Void
    @Environment(\.dismiss) private var dismiss
    @StateObject private var state = ScannerState()

    var body: some View {
        NavigationStack {
            VStack {
                Text(state.message).padding()
                if state.ready {
                    PairingCamera { text in
                        do {
                            let key = try PairingCode.parse(text)
                            onKey(key)
                            dismiss()
                            return true
                        } catch { state.message = error.localizedDescription; return false }
                    } onError: { state.message = $0; state.ready = false }
                } else {
                    Image(systemName: "qrcode.viewfinder").font(.system(size: 80)).padding()
                    Text("You can also enter a pairing key on the connection screen.")
                        .font(.caption).foregroundStyle(.secondary).padding()
                }
                Spacer(minLength: 0)
            }
            .navigationTitle("Pair with comma")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } } }
            .task {
                guard DataScannerViewController.isSupported else {
                    state.message = "Camera scanning isn’t supported on this device."; return
                }
                let granted = await AVCaptureDevice.requestAccess(for: .video)
                guard granted, DataScannerViewController.isAvailable else {
                    state.message = "Allow camera access in iPhone Settings to scan the comma’s code."; return
                }
                state.ready = true
            }
        }
    }
}

private struct PairingCamera: UIViewControllerRepresentable {
    let onCode: (String) -> Bool
    let onError: (String) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(onCode: onCode, onError: onError) }
    func makeUIViewController(context: Context) -> CameraHost {
        let scanner = DataScannerViewController(recognizedDataTypes: [.barcode(symbologies: [.qr])],
            qualityLevel: .accurate, recognizesMultipleItems: false,
            isHighFrameRateTrackingEnabled: false, isPinchToZoomEnabled: true,
            isGuidanceEnabled: true, isHighlightingEnabled: true)
        scanner.delegate = context.coordinator
        return CameraHost(scanner: scanner, coordinator: context.coordinator)
    }
    func updateUIViewController(_ host: CameraHost, context: Context) {}
    static func dismantleUIViewController(_ host: CameraHost, coordinator: Coordinator) {
        coordinator.finished = true
        host.scanner.stopScanning()
        host.scanner.delegate = nil
    }
    final class CameraHost: UIViewController {
        let scanner: DataScannerViewController
        let coordinator: Coordinator
        init(scanner: DataScannerViewController, coordinator: Coordinator) {
            self.scanner = scanner; self.coordinator = coordinator
            super.init(nibName: nil, bundle: nil)
        }
        required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
        override func viewDidLoad() {
            super.viewDidLoad()
            addChild(scanner); view.addSubview(scanner.view)
            scanner.view.frame = view.bounds
            scanner.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
            scanner.didMove(toParent: self)
        }
        override func viewDidAppear(_ animated: Bool) {
            super.viewDidAppear(animated)
            guard !coordinator.finished, !scanner.isScanning else { return }
            do { try scanner.startScanning() }
            catch { coordinator.onError("Could not start the camera. Check camera permission and try again.") }
        }
        override func viewWillDisappear(_ animated: Bool) {
            scanner.stopScanning()
            super.viewWillDisappear(animated)
        }
    }
    final class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let onCode: (String) -> Bool
        let onError: (String) -> Void
        var finished = false
        init(onCode: @escaping (String) -> Bool, onError: @escaping (String) -> Void) {
            self.onCode = onCode; self.onError = onError
        }
        func accept(_ items: [RecognizedItem], scanner: DataScannerViewController) {
            guard !finished else { return }
            for item in items {
                if case .barcode(let code) = item, let text = code.payloadStringValue, onCode(text) {
                    finished = true; scanner.stopScanning(); return
                }
            }
        }
        func dataScanner(_ scanner: DataScannerViewController, didAdd items: [RecognizedItem], allItems: [RecognizedItem]) {
            accept(items, scanner: scanner)
        }
        func dataScanner(_ scanner: DataScannerViewController, didTapOn item: RecognizedItem) { accept([item], scanner: scanner) }
        func dataScanner(_ scanner: DataScannerViewController, becameUnavailableWithError error: DataScannerViewController.ScanningUnavailable) {
            scanner.stopScanning()
            onError("Camera scanning became unavailable. Close this screen and try again.")
        }
    }
}
#endif
