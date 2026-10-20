import Foundation
import CryptoKit

@main struct PairingPhoneRegression {
    static func main() throws {
        let key = String(repeating: "A1", count: 32)
        func code(_ id: String? = nil) -> PairingCode { PairingCode(key: key.lowercased(), id: PairingCode.validID(id)) }
        let legacy = code()
        precondition(legacy.id == nil && legacy.key == key.lowercased())
        let first = code("ABCDEF12")
        precondition(first.id == "abcdef12")
        for bad in ["123", "123456789", "zzzzzzzz", "é1234567"] {
            let parsed = code(bad)
            precondition(parsed.id == nil && parsed.key == legacy.key)
        }
        let old = PairingCredential.decode(Data(key.utf8))!
        precondition(old.key == legacy.key && old.id == nil && old.previousId == nil)
        let saved = PairingCredential.replacing(nil, with: first)
        let same = PairingCredential.replacing(saved, with: first)
        precondition(same.id == saved.id && same.previousId == nil)
        let second = code("12345678")
        let replacement = PairingCredential.replacing(saved, with: second)
        precondition(replacement.id == "12345678" && replacement.previousId == "abcdef12")
        precondition(PairingCredential.replacing(replacement, with: second).previousId == "abcdef12")
        let roundTrip = PairingCredential.decode(try JSONEncoder().encode(replacement))
        precondition(roundTrip == replacement)
        precondition(PairingCredential.decode(Data("broken".utf8)) == nil)

        var request = BridgeRequest(id: "test", session: "session", counter: 1,
                                    path: "/_bridge/health", method: "GET", headers: [:], body: "")
        func json(_ request: BridgeRequest) throws -> [String: Any] {
            try JSONSerialization.jsonObject(with: JSONEncoder().encode(request)) as! [String: Any]
        }
        let initial = try json(request)
        precondition(initial["phone"] == nil)
        request.phone = BridgePhone(name: "iPhone", replaces: nil)
        let noReplacement = try json(request)["phone"] as! [String: Any]
        precondition(noReplacement["name"] as? String == "iPhone" && noReplacement["replaces"] == nil)
        precondition(Set(noReplacement.keys) == ["name"])
        request.phone = BridgePhone(name: "iPhone", replaces: replacement.previousId)
        let secret = SymmetricKey(size: .bits256)
        let framed = try Wire.seal(request, key: secret, direction: "request")
        let opened = try Wire.open(Data(framed.dropFirst(4)),
                                   as: BridgeRequest.self, key: secret, direction: "request")
        precondition(opened.phone?.name == "iPhone" && opened.phone?.replaces == "abcdef12")
        let final = try json(request)["phone"] as! [String: Any]
        precondition(Set(final.keys) == ["name", "replaces"])
        print("Phone pairing: old key migration, ID validation, re-scan/replacement and encrypted optional metadata passed")
    }
}
