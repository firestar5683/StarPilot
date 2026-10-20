import Foundation
import CryptoKit
import CoreBluetooth

/// What comma hands a phone when its pairing window is open (Settings → Bluetooth → Pair phone on comma).
struct ClaimResult: Equatable {
    let key: String
    let id: String?
    let adapterAddress: String
    let adapterName: String
}

/// Byte layout: galaxy_bluetooth/README.md, "Pairing a phone". The phone sends a P-256 public key and gets its own
/// key back, sealed under an ECDH-derived key, so nothing a nearby listener can read ever contains the key.
enum ClaimCrypto {
    static let requestMagic = Data("GCL1".utf8)
    static let replyMagic = Data("GCR1".utf8)
    static let info = Data("galaxy-claim-v1".utf8)
    static let aad = Data("galaxy-claim-v1/reply".utf8)
    static let point = 65

    static func request(publicKey: P256.KeyAgreement.PublicKey, name: String) -> Data {
        requestMagic + publicKey.x963Representation + Data(String(name.prefix(40)).utf8)
    }

    static func derive(_ privateKey: P256.KeyAgreement.PrivateKey, peer: Data, challenge: Data) throws -> SymmetricKey {
        let secret = try privateKey.sharedSecretFromKeyAgreement(with: P256.KeyAgreement.PublicKey(x963Representation: peer))
        return secret.hkdfDerivedSymmetricKey(using: SHA256.self, salt: challenge, sharedInfo: info, outputByteCount: 32)
    }

    static func open(_ reply: Data, privateKey: P256.KeyAgreement.PrivateKey, challenge: Data) throws -> ClaimResult {
        let reply = Data(reply)
        guard reply.count > 4 + point + 12 + 16, reply.prefix(4) == replyMagic else {
            throw BridgeError.message("comma sent an unexpected reply.")
        }
        let key = try derive(privateKey, peer: reply.subdata(in: 4..<(4 + point)), challenge: challenge)
        let nonce = try AES.GCM.Nonce(data: reply.subdata(in: (4 + point)..<(4 + point + 12)))
        let rest = reply.dropFirst(4 + point + 12)
        let box = try AES.GCM.SealedBox(nonce: nonce, ciphertext: rest.dropLast(16), tag: rest.suffix(16))
        return try parse(try AES.GCM.open(box, using: key, authenticating: aad))
    }

    static func parse(_ json: Data) throws -> ClaimResult {
        guard let value = try JSONSerialization.jsonObject(with: json) as? [String: Any],
              let key = value["key"] as? String, key.utf8.count == 64,
              key.utf8.allSatisfy({ (48...57).contains($0) || (65...70).contains($0) || (97...102).contains($0) }) else {
            throw BridgeError.message("comma sent an unexpected pairing key.")
        }
        let address = (value["adapterAddress"] as? String) ?? ""
        return ClaimResult(key: key.lowercased(), id: PairingCode.validID(value["id"] as? String),
                           adapterAddress: address.range(of: "^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", options: .regularExpression) != nil ? address.uppercased() : "",
                           adapterName: String(((value["adapterName"] as? String) ?? "").prefix(80)))
    }
}

/// A one-shot Bluetooth connection that asks the comma with its pairing window open for a key.
/// It is separate from `BluetoothTransport` so the normal encrypted connection code is untouched.
@MainActor
final class ClaimTransport: NSObject, @preconcurrency CBCentralManagerDelegate, @preconcurrency CBPeripheralDelegate {
    struct Outcome {
        let result: ClaimResult
        let deviceID: UUID
    }

    var onEvent: ((String) -> Void)?
    private var central: CBCentralManager?
    private var peripheral: CBPeripheral?
    private var rx: CBCharacteristic?
    private var tx: CBCharacteristic?
    private var continuation: CheckedContinuation<Outcome, Error>?
    private var privateKey = P256.KeyAgreement.PrivateKey()
    private var name = ""
    private var challenge = Data()
    private var outgoing: [Data] = []
    private var writeIndex = 0
    private var assembler = FrameAssembler()
    private var claimed: ClaimResult?
    private var handingOff = false
    private var timeout: Task<Void, Never>?

    func claim(name: String) async throws -> Outcome {
        guard continuation == nil else { throw BridgeError.message("Pairing is already in progress.") }
        self.name = name
        challenge = Data()
        outgoing = []
        writeIndex = 0
        assembler = FrameAssembler()
        claimed = nil
        handingOff = false
        onEvent?("Phone pairing started")
        privateKey = P256.KeyAgreement.PrivateKey()
        return try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            central = CBCentralManager(delegate: self, queue: .main)
            timeout = Task { @MainActor [weak self] in
                try? await Task.sleep(nanoseconds: 30_000_000_000)
                guard !Task.isCancelled else { return }
                self?.fail("comma didn’t answer. On comma open Settings → Bluetooth → Pair phone, then try again.")
            }
        }
    }

    func cancel() {
        guard continuation != nil else { return }
        onEvent?("Phone pairing cancelled")
        finish(.failure(CancellationError()))
    }

    private func fail(_ message: String) {
        onEvent?("Phone pairing failed: " + message)
        finish(.failure(BridgeError.message(message)))
    }

    private func finish(_ result: Result<Outcome, Error>) {
        guard let continuation else { return }
        self.continuation = nil
        timeout?.cancel()
        central?.stopScan()
        if let peripheral, peripheral.state != .disconnected { central?.cancelPeripheralConnection(peripheral) }
        peripheral = nil; rx = nil; tx = nil; central = nil
        continuation.resume(with: result)
    }

    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        guard central === self.central, continuation != nil else { return }
        switch central.state {
        case .poweredOn: central.scanForPeripherals(withServices: [CBUUID(string: Wire.service)], options: nil)
        case .unauthorized: fail("Allow Bluetooth access in iPhone Settings.")
        case .poweredOff: fail("Turn on Bluetooth to pair with comma.")
        case .unknown, .resetting: break
        default: fail("Bluetooth is unavailable.")
        }
    }

    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral,
                        advertisementData: [String: Any], rssi RSSI: NSNumber) {
        guard central === self.central, continuation != nil, self.peripheral == nil else { return }
        onEvent?("Phone pairing found comma; connecting")
        central.stopScan()
        self.peripheral = peripheral
        peripheral.delegate = self
        central.connect(peripheral, options: nil)
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        guard central === self.central, peripheral == self.peripheral else { return }
        onEvent?("Phone pairing connected; discovering service")
        peripheral.discoverServices([CBUUID(string: Wire.service)])
    }

    func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral, error: Error?) {
        guard central === self.central, peripheral == self.peripheral else { return }
        fail(error?.localizedDescription ?? "Could not connect to comma.")
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        guard central === self.central, peripheral == self.peripheral, continuation != nil else { return }
        if handingOff, let claimed {
            onEvent?("Phone pairing complete; starting encrypted connection")
            finish(.success(Outcome(result: claimed, deviceID: peripheral.identifier)))
        } else {
            fail(error?.localizedDescription ?? "comma disconnected.")
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard peripheral == self.peripheral else { return }
        guard error == nil, let service = peripheral.services?.first(where: { $0.uuid == CBUUID(string: Wire.service) }) else {
            fail("Galaxy Bluetooth service was not found."); return
        }
        peripheral.discoverCharacteristics([CBUUID(string: Wire.rx), CBUUID(string: Wire.tx), CBUUID(string: Wire.info)], for: service)
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        guard peripheral == self.peripheral else { return }
        rx = service.characteristics?.first { $0.uuid == CBUUID(string: Wire.rx) }
        tx = service.characteristics?.first { $0.uuid == CBUUID(string: Wire.tx) }
        guard error == nil, rx != nil, tx != nil,
              let info = service.characteristics?.first(where: { $0.uuid == CBUUID(string: Wire.info) }) else {
            fail("The comma bridge has incompatible Bluetooth characteristics."); return
        }
        peripheral.readValue(for: info)
    }

    func peripheral(_ peripheral: CBPeripheral, didWriteValueFor characteristic: CBCharacteristic, error: Error?) {
        guard peripheral == self.peripheral, characteristic.uuid == CBUUID(string: Wire.rx) else { return }
        if let error { fail(error.localizedDescription); return }
        if claimed != nil {
            // Release this connection before the normal transport connects to the same comma.
            handingOff = true
            onEvent?("Phone pairing key received; closing setup connection")
            central?.cancelPeripheralConnection(peripheral)
            return
        }
        writeIndex += 1
        if writeIndex < outgoing.count, let rx { peripheral.writeValue(outgoing[writeIndex], for: rx, type: .withResponse) }
        else if let tx { peripheral.readValue(for: tx) }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        guard peripheral == self.peripheral else { return }
        if let error { fail(error.localizedDescription); return }
        guard let data = characteristic.value else { fail("Empty Bluetooth response."); return }
        if characteristic.uuid == CBUUID(string: Wire.info) {
            guard data.count == 17, data.first == 1, let rx else { fail("Unsupported bridge protocol."); return }
            challenge = Data(data.dropFirst())
            let body = ClaimCrypto.request(publicKey: privateKey.publicKey, name: name)
            outgoing = Wire.packets(Wire.uint32(UInt32(body.count)) + body,
                                    size: min(180, peripheral.maximumWriteValueLength(for: .withoutResponse)))
            writeIndex = 0
            assembler = FrameAssembler()
            peripheral.writeValue(outgoing[0], for: rx, type: .withResponse)
            return
        }
        guard characteristic.uuid == CBUUID(string: Wire.tx), let tx, let rx else { return }
        if data == Data([0]) {
            // Comma is still working on its answer.
            Task { @MainActor [weak self, weak peripheral] in
                try? await Task.sleep(nanoseconds: 75_000_000)
                guard let self, let peripheral, peripheral == self.peripheral, self.continuation != nil else { return }
                peripheral.readValue(for: tx)
            }
            return
        }
        do {
            if let reply = try assembler.append(data) {
                claimed = try ClaimCrypto.open(reply, privateKey: privateKey, challenge: challenge)
                peripheral.writeValue(Data([2]) + data.subdata(in: 1..<5), for: rx, type: .withResponse)
            } else {
                peripheral.readValue(for: tx)
            }
        } catch { fail("Could not read comma’s pairing reply: \(error.localizedDescription)") }
    }
}
