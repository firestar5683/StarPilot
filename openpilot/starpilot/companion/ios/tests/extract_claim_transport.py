from pathlib import Path
import sys

source = Path('GalaxyBluetooth/ClaimPairing.swift').read_text().replace('import CoreBluetooth\n', '').replace('@preconcurrency ', '')
bluetooth = r'''
protocol CBCentralManagerDelegate: AnyObject {}
protocol CBPeripheralDelegate: AnyObject {}
enum CBManagerState { case poweredOn, unauthorized, poweredOff, unknown, resetting, unsupported }
enum CBPeripheralState { case connected, disconnected }
enum CBCharacteristicWriteType { case withResponse, withoutResponse }
final class CBUUID: NSObject {
    let value: String
    init(string: String) { value = string }
    override func isEqual(_ other: Any?) -> Bool { (other as? CBUUID)?.value == value }
}
@MainActor final class CBCharacteristic {
    let uuid: CBUUID
    var value: Data?
    init(_ uuid: String) { self.uuid = CBUUID(string: uuid) }
}
@MainActor final class CBService {
    let uuid = CBUUID(string: Wire.service)
    var characteristics: [CBCharacteristic]?
}
@MainActor final class CBPeripheral: NSObject {
    let identifier = UUID()
    var delegate: CBPeripheralDelegate?
    var services: [CBService]?
    var state: CBPeripheralState = .connected
    var writes: [Data] = []
    func discoverServices(_ uuids: [CBUUID]) {}
    func discoverCharacteristics(_ uuids: [CBUUID], for service: CBService) {}
    func readValue(for characteristic: CBCharacteristic) {}
    func maximumWriteValueLength(for type: CBCharacteristicWriteType) -> Int { 180 }
    func writeValue(_ data: Data, for characteristic: CBCharacteristic, type: CBCharacteristicWriteType) { writes.append(data) }
}
@MainActor final class CBCentralManager {
    static var instances: [CBCentralManager] = []
    var state = CBManagerState.poweredOn
    var cancellations = 0
    init(delegate: CBCentralManagerDelegate, queue: DispatchQueue) { Self.instances.append(self) }
    func scanForPeripherals(withServices services: [CBUUID], options: [String: Any]?) {}
    func stopScan() {}
    func connect(_ peripheral: CBPeripheral, options: [String: Any]?) {}
    func cancelPeripheralConnection(_ peripheral: CBPeripheral) { cancellations += 1 }
}
'''
tests = r'''
@main struct ClaimTransportRegression {
    @MainActor static func main() async throws {
        let transport = ClaimTransport()
        var events: [String] = []
        transport.onEvent = { events.append($0) }
        var previous: CBCentralManager?
        for attempt in 0..<2 {
            let count = CBCentralManager.instances.count
            let task = Task { try await transport.claim(name: "iPhone") }
            for _ in 0..<100 where CBCentralManager.instances.count == count { await Task.yield() }
            precondition(CBCentralManager.instances.count == count + 1)
            let central = CBCentralManager.instances.last!
            if let previous {
                previous.state = .poweredOff
                transport.centralManagerDidUpdateState(previous)
            }
            let peripheral = CBPeripheral()
            transport.centralManagerDidUpdateState(central)
            transport.centralManager(central, didDiscover: peripheral, advertisementData: [:], rssi: 0)
            transport.centralManager(central, didConnect: peripheral)
            let rx = CBCharacteristic(Wire.rx), tx = CBCharacteristic(Wire.tx), info = CBCharacteristic(Wire.info)
            let service = CBService()
            service.characteristics = [rx, tx, info]
            peripheral.services = [service]
            transport.peripheral(peripheral, didDiscoverServices: nil)
            transport.peripheral(peripheral, didDiscoverCharacteristicsFor: service, error: nil)
            let challenge = Data(repeating: UInt8(attempt + 1), count: 16)
            info.value = Data([1]) + challenge
            transport.peripheral(peripheral, didUpdateValueFor: info, error: nil)
            precondition(peripheral.writes.count == 1)
            var request = FrameAssembler()
            let body = try request.append(peripheral.writes[0])!
            transport.peripheral(peripheral, didWriteValueFor: rx, error: nil)
            precondition(central.cancellations == 0, "A retry must not complete using the previous phone key")
            let server = P256.KeyAgreement.PrivateKey()
            let key = try ClaimCrypto.derive(server, peer: body.subdata(in: 4..<69), challenge: challenge)
            let id = attempt == 0 ? "11223344" : "55667788"
            let credential = String(repeating: attempt == 0 ? "ab" : "cd", count: 32)
            let json = try JSONSerialization.data(withJSONObject: ["key": credential, "id": id])
            let box = try AES.GCM.seal(json, using: key, authenticating: ClaimCrypto.aad)
            let reply = ClaimCrypto.replyMagic + server.publicKey.x963Representation + box.combined!
            for packet in Wire.packets(Wire.uint32(UInt32(reply.count)) + reply, size: 180) {
                tx.value = packet
                transport.peripheral(peripheral, didUpdateValueFor: tx, error: nil)
            }
            let completions = events.filter { $0.contains("pairing complete") }.count
            transport.peripheral(peripheral, didWriteValueFor: rx, error: nil)
            precondition(central.cancellations == 1)
            precondition(events.filter { $0.contains("pairing complete") }.count == completions,
                         "Setup must disconnect before the encrypted transport starts")
            peripheral.state = .disconnected
            transport.centralManager(central, didDisconnectPeripheral: peripheral, error: nil)
            let result = try await task.value
            precondition(result.result.key == credential && result.result.id == id)
            previous = central
            if attempt == 0 {
                let count = CBCentralManager.instances.count
                let cancelled = Task { try await transport.claim(name: "iPhone") }
                for _ in 0..<100 where CBCentralManager.instances.count == count { await Task.yield() }
                let abandoned = CBCentralManager.instances.last!
                transport.cancel()
                abandoned.state = .poweredOff
                transport.centralManagerDidUpdateState(abandoned)
                do { _ = try await cancelled.value; preconditionFailure("Cancelled pairing returned a credential") }
                catch is CancellationError { }
            }
        }
        precondition(events.filter { $0.contains("pairing complete") }.count == 2)
        print("Repeated pairing, stale callbacks and setup handoff passed")
    }
}
'''
Path(sys.argv[1]).write_text(source + '\n' + bluetooth + '\n' + tests)
