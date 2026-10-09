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
    private var notify: CBCharacteristic?
    private var key: SymmetricKey?
    private var keyText = ""
    private var session = ""
    var sessionIdentifier: String { session }
    private var supportsReadStream = false
    private var activeReadStream = false
    private var supportsNotifications = false
    private var activeNotifications = false
    private var pairingVerified = false
    private var notificationTag = Data()
    private var notificationCount = 0
    private var notificationBuffer: [Data] = []
    private var notificationTimeout: Task<Void, Never>?
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
        notify = nil
        session = ""
        counter = 0
        supportsReadStream = false
        activeReadStream = false
        supportsNotifications = false
        activeNotifications = false
        pairingVerified = false
        notificationBuffer = []
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
        activeNotifications = supportsNotifications && active.path != "/_bridge/health"
        notificationCount = 0
        notificationBuffer = []
        activeReadStream = supportsReadStream && active.path != "/_bridge/health"
        do {
            notificationTag = try Wire.streamTag(session: session, counter: counter)
            let request = BridgeRequest(id: active.id, session: session, counter: counter, path: active.path,
                                        method: active.method, headers: active.headers, body: active.body.base64EncodedString(),
                                        responseCodec: 2, responseFlow: activeNotifications ? "notify-window8" : activeReadStream ? "read-stream" : nil)
            outgoing = Wire.packets(try Wire.seal(request, key: key, direction: "request"),
                                    size: min(supportsNotifications ? 512 : 180, peripheral.maximumWriteValueLength(for: .withoutResponse)))
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
        } else if activeNotifications {
            drainNotifications()
        } else if let tx {
            peripheral.readValue(for: tx)
        }
    }

    private func finish(_ result: Result<BridgeResponse, Error>) {
        timeoutTask?.cancel()
        notificationTimeout?.cancel()
        timeoutTask = nil
        let previous = active
        active = nil
        outgoing = []
        notificationBuffer = []
        if activeCancelled { previous?.completion.resume(throwing: CancellationError()) }
        else { previous?.completion.resume(with: result) }
        activeCancelled = false
        pump()
    }

    private func failAll(_ error: Error) {
        timeoutTask?.cancel()
        notificationTimeout?.cancel()
        let pending = queue
        queue = []
        let previous = active
        active = nil
        outgoing = []
        notificationBuffer = []
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
        peripheral.discoverCharacteristics([CBUUID(string: Wire.rx), CBUUID(string: Wire.tx), CBUUID(string: Wire.info), CBUUID(string: Wire.notify)], for: service)
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        guard peripheral == self.peripheral else { return }
        guard error == nil else { failConnection(error!.localizedDescription); return }
        rx = service.characteristics?.first { $0.uuid == CBUUID(string: Wire.rx) }
        tx = service.characteristics?.first { $0.uuid == CBUUID(string: Wire.tx) }
        notify = service.characteristics?.first { $0.uuid == CBUUID(string: Wire.notify) }
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
            } else if activeNotifications {
                drainNotifications()
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
        if characteristic.uuid == CBUUID(string: Wire.notify) {
            receiveNotification(data)
            return
        }
        if characteristic.uuid == CBUUID(string: Wire.info) {
            guard data.count == 17, data.first == 1 else { failConnection("Unsupported bridge protocol."); return }
            session = Data(data.dropFirst()).hex
            let handshakeSession = session
            status = "Verifying the pairing key…"
            Task { @MainActor [weak self, weak peripheral] in
                guard let self, let peripheral else { return }
                do {
                    let response = try await self.request(path: "/_bridge/health", method: "GET", headers: [:], body: Data())
                    guard peripheral == self.peripheral, self.session == handshakeSession else { return }
                    guard response.status == 200 else { throw BridgeError.message("Bridge verification failed.") }
                    let health = try JSONDecoder().decode(BridgeHealth.self, from: response.bodyData)
                    guard health.protocol == 1, health.transport == "bluetooth" else {
                        throw BridgeError.message("Unsupported bridge protocol.")
                    }
                    self.supportsReadStream = health.readStream == true
                    self.pairingVerified = true
                    if health.notificationStream == true {
                        guard let notify = self.notify, notify.properties.contains(.notify) else {
                            throw BridgeError.message("Bluetooth services are cached. Forget Galaxy in iPhone Bluetooth Settings, then reconnect.")
                        }
                        self.status = "Enabling fast Bluetooth transfers…"
                        peripheral.setNotifyValue(true, for: notify)
                    } else {
                        try self.completeConnection()
                    }
                } catch {
                    guard peripheral == self.peripheral, self.session == handshakeSession else { return }
                    self.failConnection("Pairing failed: \(error.localizedDescription)")
                }
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
            if activeReadStream, completedResponse == nil, let tx {
                peripheral.readValue(for: tx)
                return
            }
            awaitingAck = true
            peripheral.writeValue(Data([2]) + data.subdata(in: 1..<5), for: rx, type: .withResponse)
        } catch { failConnection("Could not verify the encrypted response: \(error.localizedDescription)") }
    }

    private func completeConnection() throws {
        try PairingKeyStore.save(keyText)
        connectionTimeout?.cancel()
        connected = true
        connecting = false
        status = supportsNotifications ? "Connected with fast Bluetooth transfers" : "Connected over Bluetooth"
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic, error: Error?) {
        guard peripheral == self.peripheral, characteristic.uuid == CBUUID(string: Wire.notify), pairingVerified else { return }
        guard error == nil, characteristic.isNotifying else {
            failConnection(error?.localizedDescription ?? "Bluetooth push subscription ended. Reconnect to check any pending setting change.")
            return
        }
        supportsNotifications = true
        do { try completeConnection() }
        catch { failConnection(error.localizedDescription) }
    }

    func peripheral(_ peripheral: CBPeripheral, didModifyServices invalidatedServices: [CBService]) {
        guard peripheral == self.peripheral, invalidatedServices.contains(where: { $0.uuid == CBUUID(string: Wire.service) }) else { return }
        failConnection("The bridge's Bluetooth services changed. Scan and reconnect.")
    }

    private func receiveNotification(_ data: Data) {
        guard active != nil, activeNotifications else { return }
        do {
            // Unrelated client/request frames must not enter this assembler.
            guard try Wire.notificationPacket(data, tag: notificationTag) != nil else { return }
            notificationTimeout?.cancel()
            let requestID = active?.id
            notificationTimeout = Task { @MainActor [weak self] in
                try? await Task.sleep(nanoseconds: 15_000_000_000)
                guard !Task.isCancelled, let self, self.active?.id == requestID else { return }
                self.failConnection("Bluetooth push stalled. Reconnect to check any pending setting change.")
            }
            if awaitingAck || writeIndex < outgoing.count {
                guard notificationBuffer.count < Wire.notificationWindow else {
                    throw BridgeError.message("Bluetooth notification window exceeded.")
                }
                notificationBuffer.append(data)
            } else {
                try consumeNotification(data)
            }
        } catch { failConnection("Could not verify Bluetooth push data: \(error.localizedDescription)") }
    }

    private func drainNotifications() {
        while active != nil, activeNotifications, !awaitingAck, !notificationBuffer.isEmpty {
            let data = notificationBuffer.removeFirst()
            do { try consumeNotification(data) }
            catch { failConnection("Could not verify Bluetooth push data: \(error.localizedDescription)") }
        }
    }

    private func consumeNotification(_ data: Data) throws {
        guard let packet = try Wire.notificationPacket(data, tag: notificationTag), let peripheral, let rx else { return }
        if let message = try assembler.append(packet), let key {
            let response = try Wire.open(message, as: BridgeResponse.self, key: key, direction: "response")
            guard response.id == active?.id, response.session == session, response.counter == counter,
                  (100...599).contains(response.status), let body = Data(base64Encoded: response.body), body.count <= Wire.maxBody else {
                throw BridgeError.message("Bluetooth response identity did not match the request.")
            }
            completedResponse = response
        }
        notificationCount += 1
        if completedResponse != nil || notificationCount % Wire.notificationWindow == 0 {
            awaitingAck = true
            let sequence = Wire.number(packet.subdata(in: 1..<5))
            peripheral.writeValue(Wire.notificationAck(tag: notificationTag, sequence: sequence), for: rx, type: .withResponse)
        }
    }
}
