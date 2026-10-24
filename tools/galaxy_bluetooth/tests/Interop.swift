import Foundation
import CryptoKit

@main
struct Interop {
    static func main() throws {
        let key = SymmetricKey(data: Data((0..<32).map(UInt8.init)))
        let oldHealth = try JSONDecoder().decode(BridgeHealth.self, from: Data("{\"protocol\":1,\"transport\":\"bluetooth\"}".utf8))
        let newHealth = try JSONDecoder().decode(BridgeHealth.self, from: Data("{\"protocol\":1,\"transport\":\"bluetooth\",\"readStream\":true}".utf8))
        let pushHealth = try JSONDecoder().decode(BridgeHealth.self, from: Data("{\"protocol\":1,\"transport\":\"bluetooth\",\"notificationStream\":true}".utf8))
        precondition(oldHealth.readStream == nil && newHealth.readStream == true)
        precondition(oldHealth.notificationStream == nil && pushHealth.notificationStream == true)
        let input = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
        let request = try Wire.open(Data(input.dropFirst(4)), as: BridgeRequest.self, key: key, direction: "request")
        precondition(request.path == "/api/params")
        precondition(request.body == String(repeating: "settings", count: 4096))
        let response = BridgeResponse(id: request.id, session: request.session, counter: request.counter, status: 200,
                                      headers: ["content-type": "application/json"], body: request.body)
        let frame = try Wire.seal(response, key: key, direction: "response")
        var assembler = FrameAssembler()
        var complete: Data?
        for fragment in Wire.packets(frame, size: 20) { complete = try assembler.append(fragment) }
        let decoded = try Wire.open(complete!, as: BridgeResponse.self, key: key, direction: "response")
        precondition(decoded.body == request.body)
        var tampered = Data(frame.dropFirst(4))
        tampered[tampered.count - 1] ^= 1
        do {
            let _: BridgeResponse = try Wire.open(tampered, as: BridgeResponse.self, key: key, direction: "response")
            fatalError("Tampered response was accepted")
        } catch {}
        try frame.write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
        let compact = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[3]))
        let rawBody = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[4]))
        let compactResponse = try Wire.open(Data(compact.dropFirst(4)), as: BridgeResponse.self, key: key, direction: "response")
        precondition(compactResponse.bodyData == rawBody && compactResponse.status == 200)
        for size in [20, 180, 244, 512] {
            var compactAssembler = FrameAssembler()
            var completeCompact: Data?
            for fragment in Wire.packets(compact, size: size) {
                precondition(fragment.count <= size)
                completeCompact = try compactAssembler.append(fragment)
            }
            let decoded = try Wire.open(completeCompact!, as: BridgeResponse.self, key: key, direction: "response")
            precondition(decoded.bodyData == rawBody)
        }
        let notifications = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[5]))
        let tag = try Wire.streamTag(session: String(repeating: "01", count: 16), counter: 2)
        let otherTag = try Wire.streamTag(session: String(repeating: "01", count: 16), counter: 3)
        var offset = 0
        var count = 0
        var pushAssembler = FrameAssembler()
        var acknowledgements = Data()
        var pushComplete: Data?
        while offset < notifications.count {
            let length = Int(Wire.number(notifications.subdata(in: offset..<(offset + 4))))
            offset += 4
            let notification = notifications.subdata(in: offset..<(offset + length))
            offset += length
            let unrelated = try Wire.notificationPacket(notification, tag: otherTag)
            precondition(unrelated == nil)
            let packet = try Wire.notificationPacket(notification, tag: tag)!
            pushComplete = try pushAssembler.append(packet)
            count += 1
            if count % Wire.notificationWindow == 0 || pushComplete != nil {
                acknowledgements.append(Wire.notificationAck(tag: tag, sequence: Wire.number(packet.subdata(in: 1..<5))))
            }
        }
        let pushed = try Wire.open(pushComplete!, as: BridgeResponse.self, key: key, direction: "response")
        precondition(pushed.bodyData == rawBody)
        do {
            _ = try Wire.notificationPacket(Data([3]) + tag + Data(repeating: 0, count: 4), tag: tag)
            fatalError("Truncated notification was accepted")
        } catch {}
        try acknowledgements.write(to: URL(fileURLWithPath: CommandLine.arguments[6]))

        let valid = Data("PUT /api/params HTTP/1.1\r\nHost: 127.0.0.1:9000\r\nContent-Length: 2\r\n\r\n{}".utf8)
        let incomplete = try LocalRequest.parse(Data(valid.dropLast()))
        precondition(incomplete == nil)
        let parsed = try LocalRequest.parse(valid)!
        precondition(parsed.method == "PUT" && parsed.body == Data("{}".utf8))
        for invalid in ["POST /api/params HTTP/1.1\r\nContent-Length: -1\r\n\r\n",
                        "POST /api/params HTTP/1.1\r\nContent-Length: 0\r\nContent-Length: 2\r\n\r\n{}",
                        "POST /api/params HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n"] {
            do { _ = try LocalRequest.parse(Data(invalid.utf8)); fatalError("Invalid HTTP request was accepted") }
            catch {}
        }
        precondition(oldHealth.catalogSHA256 == nil && oldHealth.notificationStream == nil)
        print("Swift/Python encrypted framing and HTTP parser checks passed")
    }
}
