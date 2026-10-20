import Foundation
import CryptoKit

/// The vector comes from comma's own claim.py (galaxy_bluetooth/tests), so both sides agree byte for byte.
@main struct ClaimPairingRegression {
    static func hex(_ text: String) -> Data { Data(hex: text)! }

    static func main() throws {
        let phone = try P256.KeyAgreement.PrivateKey(rawRepresentation: Data(repeating: 0x11, count: 32))
        let challenge = Data((0..<16).map(UInt8.init))
        let reply = hex("4743523104d65a93977caa3d1b081852ff57a79e465f1660577304baead505dd3a48589cf350185e895372df6221ea3a137557e473fddb6755f05bd507c3c533fce9c912856465666768696a6b6c6d6e6f56e085dc7bc3807c9c7cb045c4c1f175f83b778465883907450039ebf7bae2c056f9ce9975cfb418ec470cffe65a07209b6b0194c4f7858fdac068c0fb2f699f06cc4bfb9a8c6734d68a910c8d5329eadf05462b6c59013892e0522f5056974e80082afbb204b6cde770c4d5ed383ffe6f08909da1a7b716088c91d507bd197a3c8f48e8a53deaa7008f209ac1c78f733f078cd862345f0e2fab00241494bc7bc4be2a4769")

        // Comma's reply opens to this phone's key.
        let claim = try ClaimCrypto.open(reply, privateKey: phone, challenge: challenge)
        precondition(claim.key == String(repeating: "ab", count: 32) && claim.id == "0a1b2c3d")
        precondition(claim.adapterAddress == "AA:BB:CC:DD:EE:FF" && claim.adapterName == "comma")

        // Both sides derive the same key.
        let derived = try ClaimCrypto.derive(phone, peer: reply.subdata(in: 4..<69), challenge: challenge)
        precondition(derived.withUnsafeBytes { Data($0) } == hex("3b5c0f6357da2c229949fb3695c3656c009af9b8fa4a7588ce991292c6eb73e0"))

        // A wrong session, another phone, a tampered or truncated reply, or a different magic are all refused.
        func refused(_ body: () throws -> Void) -> Bool { (try? body()) == nil }
        precondition(refused { _ = try ClaimCrypto.open(reply, privateKey: phone, challenge: Data(count: 16)) })
        precondition(refused { _ = try ClaimCrypto.open(reply, privateKey: P256.KeyAgreement.PrivateKey(), challenge: challenge) })
        var tampered = reply; tampered[tampered.count - 1] ^= 1
        precondition(refused { _ = try ClaimCrypto.open(tampered, privateKey: phone, challenge: challenge) })
        precondition(refused { _ = try ClaimCrypto.open(reply.prefix(60), privateKey: phone, challenge: challenge) })
        var other = reply; other[0] = 0x58
        precondition(refused { _ = try ClaimCrypto.open(other, privateKey: phone, challenge: challenge) })

        // The request is magic, 65-byte point, then the name (at most 40 characters).
        let request = ClaimCrypto.request(publicKey: phone.publicKey, name: "Danny’s iPhone")
        precondition(request.prefix(4) == Data("GCL1".utf8) && request.subdata(in: 4..<69) == phone.publicKey.x963Representation)
        precondition(String(decoding: request.dropFirst(69), as: UTF8.self) == "Danny’s iPhone")
        precondition(ClaimCrypto.request(publicKey: phone.publicKey, name: String(repeating: "x", count: 100)).count == 69 + 40)

        // Unexpected contents are refused rather than half used.
        precondition(refused { _ = try ClaimCrypto.parse(Data(#"{"id":"0a1b2c3d"}"#.utf8)) })
        precondition(refused { _ = try ClaimCrypto.parse(Data(#"{"key":"short"}"#.utf8)) })
        let sparse = try ClaimCrypto.parse(Data(#"{"key":"\#(String(repeating: "CD", count: 32))","id":"BAD","adapterAddress":"nope"}"#.utf8))
        precondition(sparse.key == String(repeating: "cd", count: 32) && sparse.id == nil && sparse.adapterAddress == "" && sparse.adapterName == "")
        print("Claim pairing: comma vector, derive, tamper and malformed cases passed")
    }
}
