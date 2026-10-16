import Foundation
import Security

struct PairingCredential: Codable, Equatable {
    let key: String
    let id: String?
    var previousId: String?

    static func decode(_ data: Data) -> PairingCredential? {
        if let stored = try? JSONDecoder().decode(Self.self, from: data) {
            return Self(key: stored.key, id: PairingCode.validID(stored.id),
                        previousId: PairingCode.validID(stored.previousId))
        }
        guard let key = String(data: data, encoding: .utf8), key.utf8.count == 64,
              key.utf8.allSatisfy({ (48...57).contains($0) || (65...70).contains($0) || (97...102).contains($0) }) else { return nil }
        return Self(key: key.lowercased(), id: nil, previousId: nil)
    }

    static func replacing(_ saved: Self?, with code: PairingCode) -> Self {
        let previous = saved?.id == code.id ? saved?.previousId : saved?.id
        return Self(key: code.key, id: code.id, previousId: previous)
    }
}

enum PairingKeyStore {
    // Scanned credentials are committed only after the encrypted handshake succeeds.
    private static var pending: PairingCredential?
    private static let service = "link.galaxy.bluetooth.pairing"
    private static let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                               kSecAttrService as String: service,
                                               kSecAttrAccount as String: "comma"]

    static func load() -> String { stored()?.key ?? "" }

    private static func stored() -> PairingCredential? {
        var request = query
        request[kSecReturnData as String] = true
        request[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        guard SecItemCopyMatching(request as CFDictionary, &result) == errSecSuccess, let data = result as? Data else { return nil }
        return PairingCredential.decode(data)
    }

    static func stage(_ code: PairingCode) {
        pending = PairingCredential.replacing(stored(), with: code)
    }

    static func credential(for key: String) -> PairingCredential? {
        if let pending, pending.key == key { return pending }
        guard let saved = stored(), saved.key == key else { return nil }
        return saved
    }

    static func phone(for key: String, name: String) -> BridgePhone {
        BridgePhone(name: name, replaces: credential(for: key)?.previousId)
    }

    static func save(_ value: String) throws {
        var credential = credential(for: value) ?? PairingCredential(key: value, id: nil, previousId: nil)
        credential.previousId = nil
        let data = try JSONEncoder().encode(credential)
        let status = SecItemUpdate(query as CFDictionary, [kSecValueData as String: data, kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly] as CFDictionary)
        if status == errSecItemNotFound {
            var item = query
            item[kSecValueData as String] = data
            item[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { throw BridgeError.message("Could not save pairing key in Keychain.") }
        } else if status != errSecSuccess { throw BridgeError.message("Could not update pairing key in Keychain.") }
        pending = nil
    }

    static func remove() { pending = nil; SecItemDelete(query as CFDictionary) }
}
