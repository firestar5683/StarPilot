import Foundation
import CryptoKit
import Compression

struct BridgeRequest: Codable {
    let id: String
    let session: String
    let counter: UInt64
    let path: String
    let method: String
    let headers: [String: String]
    let body: String
    var responseCodec: Int? = nil
    var responseFlow: String? = nil
}

struct BridgeResponse: Codable {
    let id: String
    let session: String
    let counter: UInt64
    let status: Int
    let headers: [String: String]
    let body: String

    var bodyData: Data { Data(base64Encoded: body) ?? Data() }
}

struct BridgeHealth: Decodable {
    let `protocol`: Int
    let transport: String
    let readStream: Bool?
}

enum BridgeError: LocalizedError {
    case message(String)
    var errorDescription: String? {
        if case let .message(value) = self { return value }
        return nil
    }
}

enum Wire {
    static let service = "bd490001-6dc1-4de7-a7d0-6cdb441f7650"
    static let rx = "bd490002-6dc1-4de7-a7d0-6cdb441f7650"
    static let tx = "bd490003-6dc1-4de7-a7d0-6cdb441f7650"
    static let info = "bd490004-6dc1-4de7-a7d0-6cdb441f7650"
    static let maxFrame = 2 * 1024 * 1024
    static let maxBody = 1024 * 1024

    static func uint32(_ number: UInt32) -> Data {
        var value = number.bigEndian
        return withUnsafeBytes(of: &value) { Data($0) }
    }

    static func number(_ bytes: Data) -> UInt32 {
        bytes.reduce(UInt32(0)) { ($0 << 8) | UInt32($1) }
    }

    static func seal<T: Encodable>(_ value: T, key: SymmetricKey, direction: String) throws -> Data {
        let plaintext = try JSONEncoder().encode(value)
        guard plaintext.count <= maxFrame else { throw BridgeError.message("Decoded request exceeds the Bluetooth limit.") }
        var compressed = [UInt8](repeating: 0, count: maxFrame)
        let written = plaintext.withUnsafeBytes { bytes in
            compression_encode_buffer(&compressed, compressed.count, bytes.bindMemory(to: UInt8.self).baseAddress!, plaintext.count, nil, COMPRESSION_ZLIB)
        }
        let useCompression = written > 0 && written < plaintext.count
        let encoded = Data([useCompression ? 1 : 0]) + uint32(UInt32(plaintext.count))
            + (useCompression ? Data(compressed.prefix(written)) : plaintext)
        let box = try AES.GCM.seal(encoded, using: key,
                                   authenticating: Data("galaxy-ble-v1/\(direction)".utf8))
        guard let combined = box.combined, combined.count <= maxFrame else {
            throw BridgeError.message("Request exceeds the Bluetooth frame limit.")
        }
        return uint32(UInt32(combined.count)) + combined
    }

    static func open<T: Decodable>(_ data: Data, as: T.Type, key: SymmetricKey, direction: String) throws -> T {
        guard (28...maxFrame).contains(data.count) else { throw BridgeError.message("Invalid encrypted message.") }
        let encoded = try AES.GCM.open(AES.GCM.SealedBox(combined: data), using: key,
                                         authenticating: Data("galaxy-ble-v1/\(direction)".utf8))
        guard encoded.count >= 5 else { throw BridgeError.message("Invalid compressed envelope.") }
        let length = Int(number(encoded.subdata(in: 1..<5)))
        guard (1...maxFrame).contains(length) else { throw BridgeError.message("Invalid decoded message size.") }
        let plaintext: Data
        switch encoded.first {
        case 0: plaintext = Data(encoded.dropFirst(5))
        case 1, 2:
            let compressed = Data(encoded.dropFirst(5))
            guard !compressed.isEmpty else { throw BridgeError.message("Empty compressed message.") }
            var decoded = [UInt8](repeating: 0, count: length + 1)
            let written = compressed.withUnsafeBytes { bytes in
                compression_decode_buffer(&decoded, decoded.count, bytes.bindMemory(to: UInt8.self).baseAddress!, compressed.count, nil, COMPRESSION_ZLIB)
            }
            guard written == length else { throw BridgeError.message("Invalid compressed Bluetooth message.") }
            plaintext = Data(decoded.prefix(written))
        default: throw BridgeError.message("Unknown Bluetooth compression codec.")
        }
        guard plaintext.count == length else { throw BridgeError.message("Incorrect decoded message size.") }
        if encoded.first == 2 {
            guard plaintext.count >= 4 else { throw BridgeError.message("Invalid response envelope.") }
            let metadataLength = Int(number(plaintext.prefix(4)))
            guard metadataLength > 0, metadataLength <= plaintext.count - 4,
                  plaintext.count - 4 - metadataLength <= maxBody,
                  var metadata = try JSONSerialization.jsonObject(with: plaintext.subdata(in: 4..<(4 + metadataLength))) as? [String: Any],
                  metadata["body"] == nil else { throw BridgeError.message("Invalid response metadata.") }
            metadata["body"] = plaintext.dropFirst(4 + metadataLength).base64EncodedString()
            return try JSONDecoder().decode(T.self, from: JSONSerialization.data(withJSONObject: metadata))
        }
        return try JSONDecoder().decode(T.self, from: plaintext)
    }

    static func packets(_ frame: Data, size: Int) -> [Data] {
        let payloadSize = max(15, min(512, size) - 5)
        return stride(from: 0, to: frame.count, by: payloadSize).enumerated().map { sequence, start in
            Data([1]) + uint32(UInt32(sequence)) + frame.subdata(in: start..<min(start + payloadSize, frame.count))
        }
    }
}

struct FrameAssembler {
    private var data = Data()
    private var sequence: UInt32 = 0
    private var expectedLength: Int?

    mutating func append(_ packet: Data) throws -> Data? {
        guard packet.count >= 6, packet.first == 1, Wire.number(packet.subdata(in: 1..<5)) == sequence else {
            throw BridgeError.message("Bluetooth fragments arrived out of order.")
        }
        sequence += 1
        data.append(packet.dropFirst(5))
        if expectedLength == nil, data.count >= 4 {
            let length = Int(Wire.number(data.prefix(4)))
            guard (28...Wire.maxFrame).contains(length) else { throw BridgeError.message("Invalid Bluetooth frame size.") }
            expectedLength = length
        }
        guard data.count <= Wire.maxFrame + 4 else { throw BridgeError.message("Bluetooth response is too large.") }
        if let length = expectedLength, data.count >= length + 4 {
            guard data.count == length + 4 else { throw BridgeError.message("Unexpected trailing response bytes.") }
            let result = Data(data.dropFirst(4))
            self = FrameAssembler()
            return result
        }
        return nil
    }
}

extension Data {
    init?(hex: String) {
        let text = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        guard text.count % 2 == 0 else { return nil }
        var bytes = [UInt8]()
        var index = text.startIndex
        while index < text.endIndex {
            let end = text.index(index, offsetBy: 2)
            guard let byte = UInt8(text[index..<end], radix: 16) else { return nil }
            bytes.append(byte)
            index = end
        }
        self.init(bytes)
    }

    var hex: String { map { String(format: "%02x", $0) }.joined() }
}
