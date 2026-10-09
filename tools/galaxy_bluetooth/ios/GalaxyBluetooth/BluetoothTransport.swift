import Foundation
import Combine
import CoreBluetooth
import CryptoKit

struct NearbyDevice: Identifiable {
    let id: UUID
    let name: String
    let signal: Int
}

@MainActor
final class BluetoothTransport: NSObject, ObservableObject, GalaxyRequestTransport, @preconcurrency CBCentralManagerDelegate, @preconcurrency CBPeripheralDelegate {
    @Published var devices: [NearbyDevice] = []
    @Published var status = "Turn on Bluetooth, then scan for your comma."
    @Published var isScanning = false
    @Published var connected = false
    @Published var connecting = false

    private var central: CBCentralManager!
    private var peripherals: [UUID: CBPeripheral] = [:]
    private var peripheral: CBPeripheral?
    private var rx: CBCharacteristic?
    private var tx: CBCharacteristic?
    private var key: SymmetricKey?
    private var keyText = ""
    private var session = ""
    private var counter: UInt64 = 0
    private var queue: [Pending] = []
    private var active: Pending?
    private var outgoing: [Data] = []
    private var writeIndex = 0
    private var assembler = FrameAssembler()
    private var awaitingAck = false
    private var completedResponse: BridgeResponse?
    private var activeCancelled = false
    private var timeoutTask: Task<Void, Never>?
    private var scanTimeout: Task<Void, Never>?
    private var connectionTimeout: Task<Void, Never>?

    private struct Pending {
        let id: String
        let path: String
        let method: String
        let headers: [String: String]
        let body: Data
        let completion: CheckedContinuation<BridgeResponse, Error>
    }

    override init() {
        super.init()
        central = CBCentralManager(delegate: self, queue: .main)
    }

    func scan() {
        guard central.state == .poweredOn else { status = "Bluetooth is unavailable or permission is required."; return }
        devices = []
        peripherals = [:]
        central.scanForPeripherals(withServices: [CBUUID(string: Wire.service)], options: nil)
        isScanning = true
        status = "Looking for the Galaxy Bluetooth bridge…"
        scanTimeout?.cancel()
        scanTimeout = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: 15_000_000_000)
            guard !Task.isCancelled, let self else { return }
            self.central.stopScan()
            self.isScanning = false
            self.status = self.devices.isEmpty ? "No bridge found. Start the bridge on your comma and enable Bluetooth in StarPilot." : "Select your comma to connect."
        }
    }

    func connect(_ device: NearbyDevice, pairingKey: String) {
        guard let bytes = Data(hex: pairingKey), bytes.count == 32 else {
            status = "Paste the 64-character pairing key created on your comma."
            return
        }
        guard let found = peripherals[device.id] else { return }
        disconnect()
        key = SymmetricKey(data: bytes)
        keyText = bytes.hex
        peripheral = found
        found.delegate = self
        connecting = true
        status = "Connecting to \(device.name)…"
        central.connect(found, options: nil)
        connectionTimeout = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: 20_000_000_000)
            guard !Task.isCancelled, let self, !self.connected else { return }
            self.failConnection("Bluetooth connection timed out. Check the comma bridge and pairing key.")
        }
    }

    func disconnect() {
        central.stopScan()
        scanTimeout?.cancel()
        connectionTimeout?.cancel()
        isScanning = false
        connected = false
        connecting = false
        failAll(BridgeError.message("Bluetooth connection closed."))
        if let peripheral { central.cancelPeripheralConnection(peripheral) }
        peripheral = nil
        rx = nil
        tx = nil
        session = ""
        counter = 0
    }

    private func failConnection(_ message: String) {
        disconnect()
        status = message
    }

    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        let id = UUID().uuidString
        return try await withTaskCancellationHandler(operation: {
            try Task.checkCancellation()
            return try await withCheckedThrowingContinuation { continuation in
                guard rx != nil, tx != nil, !session.isEmpty else {
                    continuation.resume(throwing: BridgeError.message("Connect to your comma over Bluetooth first."))
                    return
                }
                guard queue.count < 32, body.count <= Wire.maxBody else {
                    continuation.resume(throwing: BridgeError.message("Bluetooth queue is full or upload exceeds 1 MiB."))
                    return
                }
                queue.append(Pending(id: id, path: path, method: method, headers: headers, body: body, completion: continuation))
                pump()
            }
        }, onCancel: { [weak self] in
            DispatchQueue.main.async { self?.cancel(id) }
        })
    }

    private func cancel(_ id: String) {
        if let index = queue.firstIndex(where: { $0.id == id }) {
            queue.remove(at: index).completion.resume(throwing: CancellationError())
        } else if active?.id == id {
            if writeIndex >= outgoing.count {
                // Drain an already-sent response so navigating away from a poll
                // does not tear down a healthy Bluetooth session.
                activeCancelled = true
            } else {
                failConnection("Request cancelled. Reconnect before sending another request.")
            }
        }
    }

    private func pump() {
        guard active == nil, !queue.isEmpty, let peripheral, let key, !session.isEmpty else { return }
        active = queue.removeFirst()
        guard let active else { return }
        counter += 1
        assembler = FrameAssembler()
        completedResponse = nil
        activeCancelled = false
        awaitingAck = false
        writeIndex = 0
        do {
            let request = BridgeRequest(id: active.id, session: session, counter: counter, path: active.path,
                                        method: active.method, headers: active.headers, body: active.body.base64EncodedString())
            outgoing = Wire.packets(try Wire.seal(request, key: key, direction: "request"),
                                    size: min(180, peripheral.maximumWriteValueLength(for: .withResponse)))
            timeoutTask = Task { @MainActor [weak self] in
                let seconds: UInt64 = active.path == "/_bridge/health" ? 10 : 90
                try? await Task.sleep(nanoseconds: seconds * 1_000_000_000)
                guard !Task.isCancelled, let self, self.active?.id == active.id else { return }
                self.failConnection("Bluetooth request timed out. Its outcome may be unknown; reconnect to check before retrying.")
            }
            writeNext()
        } catch {
            finish(.failure(error))
        }
    }

    private func writeNext() {
        guard let peripheral, let rx, active != nil else { return }
        if writeIndex < outgoing.count {
            peripheral.writeValue(outgoing[writeIndex], for: rx, type: .withResponse)
        } else if let tx {
            peripheral.readValue(for: tx)
        }
    }

    private func finish(_ result: Result<BridgeResponse, Error>) {
        timeoutTask?.cancel()
        timeoutTask = nil
        let previous = active
        active = nil
        outgoing = []
        if activeCancelled { previous?.completion.resume(throwing: CancellationError()) }
        else { previous?.completion.resume(with: result) }
        activeCancelled = false
        pump()
    }

    private func failAll(_ error: Error) {
        timeoutTask?.cancel()
        let pending = queue
        queue = []
        let previous = active
        active = nil
        outgoing = []
        previous?.completion.resume(throwing: error)
        pending.forEach { $0.completion.resume(throwing: error) }
    }

    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        switch central.state {
        case .poweredOn: status = "Ready to scan for your comma."
        case .unauthorized: failConnection("Allow Bluetooth access in iPhone Settings.")
        case .poweredOff: failConnection("Bluetooth is turned off.")
        default: failConnection("Bluetooth is unavailable.")
        }
    }

    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral,
                        advertisementData: [String: Any], rssi RSSI: NSNumber) {
        peripherals[peripheral.identifier] = peripheral
        let device = NearbyDevice(id: peripheral.identifier,
                                  name: advertisementData[CBAdvertisementDataLocalNameKey] as? String ?? peripheral.name ?? "Galaxy",
                                  signal: RSSI.intValue)
        if let index = devices.firstIndex(where: { $0.id == device.id }) { devices[index] = device }
        else { devices.append(device) }
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        guard peripheral == self.peripheral else { return }
        peripheral.discoverServices([CBUUID(string: Wire.service)])
    }

    func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral, error: Error?) {
        guard peripheral == self.peripheral else { return }
        failConnection(error?.localizedDescription ?? "Could not connect to your comma.")
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        guard peripheral == self.peripheral else { return }
        failConnection(error?.localizedDescription ?? "Your comma disconnected. Scan to reconnect.")
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard peripheral == self.peripheral else { return }
        guard error == nil, let service = peripheral.services?.first(where: { $0.uuid == CBUUID(string: Wire.service) }) else {
            failConnection("Galaxy Bluetooth service was not found."); return
        }
        peripheral.discoverCharacteristics([CBUUID(string: Wire.rx), CBUUID(string: Wire.tx), CBUUID(string: Wire.info)], for: service)
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        guard peripheral == self.peripheral else { return }
        guard error == nil else { failConnection(error!.localizedDescription); return }
        rx = service.characteristics?.first { $0.uuid == CBUUID(string: Wire.rx) }
        tx = service.characteristics?.first { $0.uuid == CBUUID(string: Wire.tx) }
        guard rx != nil, tx != nil, let info = service.characteristics?.first(where: { $0.uuid == CBUUID(string: Wire.info) }) else {
            failConnection("The comma bridge has incompatible Bluetooth characteristics."); return
        }
        peripheral.readValue(for: info)
    }

    func peripheral(_ peripheral: CBPeripheral, didWriteValueFor characteristic: CBCharacteristic, error: Error?) {
        guard peripheral == self.peripheral, characteristic.uuid == CBUUID(string: Wire.rx), active != nil else { return }
        if let error { failConnection(error.localizedDescription); return }
        if awaitingAck {
            awaitingAck = false
            if let response = completedResponse {
                completedResponse = nil
                finish(.success(response))
            } else if let tx {
                peripheral.readValue(for: tx)
            }
        } else {
            writeIndex += 1
            writeNext()
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        guard peripheral == self.peripheral else { return }
        if let error { failConnection(error.localizedDescription); return }
        guard let data = characteristic.value else { failConnection("Empty Bluetooth response."); return }
        if characteristic.uuid == CBUUID(string: Wire.info) {
            guard data.count == 17, data.first == 1 else { failConnection("Unsupported bridge protocol."); return }
            session = Data(data.dropFirst()).hex
            status = "Verifying the pairing key…"
            Task { @MainActor [weak self] in
                guard let self else { return }
                do {
                    let response = try await self.request(path: "/_bridge/health", method: "GET", headers: [:], body: Data())
                    guard response.status == 200 else { throw BridgeError.message("Bridge verification failed.") }
                    try PairingKeyStore.save(self.keyText)
                    self.connectionTimeout?.cancel()
                    self.connected = true
                    self.connecting = false
                    self.status = "Connected over Bluetooth"
                } catch { self.failConnection("Pairing failed: \(error.localizedDescription)") }
            }
            return
        }
        guard characteristic.uuid == CBUUID(string: Wire.tx), active != nil, let rx else { return }
        if data == Data([0]) {
            let requestID = active?.id
            Task { @MainActor [weak self, weak peripheral] in
                try? await Task.sleep(nanoseconds: 75_000_000)
                guard !Task.isCancelled, let self, self.active?.id == requestID, self.active != nil, let tx = self.tx,
                      let peripheral, peripheral == self.peripheral else { return }
                peripheral.readValue(for: tx)
            }
            return
        }
        do {
            if let message = try assembler.append(data), let key {
                let response = try Wire.open(message, as: BridgeResponse.self, key: key, direction: "response")
                guard response.id == active?.id, response.session == session, response.counter == counter,
                      (100...599).contains(response.status), Data(base64Encoded: response.body) != nil else {
                    throw BridgeError.message("Bluetooth response identity did not match the request.")
                }
                completedResponse = response
            }
            awaitingAck = true
            peripheral.writeValue(Data([2]) + data.subdata(in: 1..<5), for: rx, type: .withResponse)
        } catch { failConnection("Could not verify the encrypted response: \(error.localizedDescription)") }
    }
}
