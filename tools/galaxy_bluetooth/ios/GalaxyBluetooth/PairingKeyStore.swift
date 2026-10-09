import Foundation
import Security

enum PairingKeyStore {
    private static let service = "link.galaxy.bluetooth.pairing"
    private static let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                               kSecAttrService as String: service,
                                               kSecAttrAccount as String: "comma"]

    static func load() -> String {
        var request = query
        request[kSecReturnData as String] = true
        request[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        guard SecItemCopyMatching(request as CFDictionary, &result) == errSecSuccess, let data = result as? Data else { return "" }
        return String(data: data, encoding: .utf8) ?? ""
    }

    static func save(_ value: String) throws {
        let data = Data(value.utf8)
        let status = SecItemUpdate(query as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if status == errSecItemNotFound {
            var item = query
            item[kSecValueData as String] = data
            item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { throw BridgeError.message("Could not save pairing key in Keychain.") }
        } else if status != errSecSuccess { throw BridgeError.message("Could not update pairing key in Keychain.") }
    }

    static func remove() { SecItemDelete(query as CFDictionary) }
}
