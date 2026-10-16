from pathlib import Path
import sys
source = Path("GalaxyBluetooth/GalaxyBluetoothApp.swift").read_text()
start = source.index("struct LegacyGalaxyStatus:")
end = source.index("\n@MainActor", start)
probe = source[start:end]
tests = r'''
@main struct LegacyLinkRegression {
    static func main() {
        let first = "https://galaxy.firestar.link/AbCdEf0123456789"
        let second = "https://galaxy.firestar.link/ZyXwVu9876543210"
        precondition(LegacyGalaxyStatus(paired: true, url: first).browserURL?.absoluteString == first)
        precondition(LegacyGalaxyStatus(paired: true, url: second).browserURL?.absoluteString == second)
        for bad in ["https://galaxy.firestar.link", first + "?key=private", first + "#fragment", "http://galaxy.firestar.link/AbCdEf0123456789", "https://evil.example/AbCdEf0123456789", "https://galaxy.firestar.link:444/AbCdEf0123456789"] {
            precondition(LegacyGalaxyStatus(paired: true, url: bad).browserURL == nil)
        }
        print("Legacy Galaxy links: device-specific address preserved; general and unsafe links rejected")
    }
}
'''
Path(sys.argv[1]).write_text("import Foundation\n" + probe + tests)
