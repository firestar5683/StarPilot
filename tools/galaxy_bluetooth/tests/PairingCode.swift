import Foundation

@main
struct PairingCodeTests {
    static func main() throws {
        let key = String(repeating: "AB", count: 32)
        let good = "{\"type\":\"galaxy-bluetooth\",\"version\":1,\"key\":\"\(key)\"}"
        let parsed = try PairingCode.parse(good)
        precondition(parsed == key.lowercased())
        if CommandLine.arguments.count > 1 {
            let fixture = try String(contentsOfFile: CommandLine.arguments[1], encoding: .utf8)
            let imported = try PairingCode.parse(fixture)
            precondition(imported == key.lowercased())
        }
        for bad in ["https://galaxy.firestar.link/example", good.replacingOccurrences(of: "bluetooth", with: "internet"),
                    good.replacingOccurrences(of: "version\":1", with: "version\":2"),
                    good.replacingOccurrences(of: key, with: "short"),
                    good.replacingOccurrences(of: key, with: String(repeating: "zz", count: 32)),
                    String(repeating: " ", count: 513) + good] {
            do { _ = try PairingCode.parse(bad); fatalError("Invalid QR accepted") }
            catch { /* Expected. */ }
        }
        print("Pairing QR validation passed")
    }
}
