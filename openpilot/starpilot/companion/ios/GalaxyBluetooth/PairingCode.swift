import Foundation

/// A phone's key from comma and comma's id for it (kept so a re-pair can replace the old entry).
struct PairingCode {
    let key: String
    let id: String?

    static func validID(_ value: String?) -> String? {
        guard let value, value.utf8.count == 8,
              value.utf8.allSatisfy({ (48...57).contains($0) || (65...70).contains($0) || (97...102).contains($0) }) else { return nil }
        return value.lowercased()
    }
}
