import Foundation
import CryptoKit
import Combine

struct GalaxyAssetManifest: Codable {
    struct File: Codable { let path: String; let sha256: String; let size: Int }
    let schema: Int
    let nativeBridge: Int
    let files: [File]
    func validate() throws {
        guard schema == 1, nativeBridge == 1, (1...512).contains(files.count),
              Set(files.map(\.path)).count == files.count else { throw BridgeError.message("Galaxy update needs a compatible app version.") }
        var total = 0
        for file in files {
            let parts = file.path.split(separator: "/", omittingEmptySubsequences: false)
            guard !parts.isEmpty, parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }),
                  file.path.utf8.allSatisfy({ (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || [45, 46, 47, 95].contains($0) }),
                  file.path == "classic.html" || file.path.hasPrefix("assets/"),
                  (0...4_194_304).contains(file.size), Self.isHash(file.sha256) else {
                throw BridgeError.message("Invalid Galaxy update file.")
            }
            total += file.size
        }
        guard total <= 32 * 1_048_576, files.contains(where: { $0.path == "assets/mobile/index.html" }),
              files.contains(where: { $0.path == "assets/mobile/js/api.js" }) else { throw BridgeError.message("Galaxy update is incomplete or too large.") }
    }
    static func isHash(_ value: String) -> Bool { value.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) } }
    static func digest(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
}

@MainActor
final class GalaxyAssetStore: ObservableObject {
    // Nate’s pilot update channel.
    static let repository = "natehuby76/StarPilotBT"
    static let branch = "Nate/galaxy-bluetooth"
    static let resourcePath = "tools/galaxy_bluetooth/ios/GalaxyBluetooth/Resources/Web"
    @Published private(set) var status = "Galaxy is available offline."
    @Published private(set) var checking = false
    @Published private(set) var readyRoot: URL?
    var inUseRoot: URL?
    let bundledRoot: URL
    private let cacheRoot: URL
    private let defaults: UserDefaults
    private let fetch: (URLRequest, Int) async throws -> (Data, HTTPURLResponse)
    init(bundledRoot: URL? = nil, cacheRoot: URL? = nil, defaults: UserDefaults = .standard,
         fetch: @escaping (URLRequest, Int) async throws -> (Data, HTTPURLResponse) = { try await BoundedHTTP.load($0, limit: $1) }) {
        self.bundledRoot = bundledRoot ?? Bundle.main.resourceURL!.appendingPathComponent("Web", isDirectory: true)
        self.cacheRoot = cacheRoot ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("GalaxyUpdates", isDirectory: true)
        self.defaults = defaults
        self.fetch = fetch
        // Validate saved assets before trusting a previous completed update.
        if let hash = defaults.string(forKey: "galaxy.assets.manifest"), GalaxyAssetManifest.isHash(hash) {
            let root = self.cacheRoot.appendingPathComponent(hash, isDirectory: true)
            if Self.verify(root) { readyRoot = root; status = "Using saved Galaxy from GitHub." }
        }
    }
    private static func verify(_ root: URL) -> Bool {
        guard let data = try? Data(contentsOf: root.appendingPathComponent("manifest.json")),
              GalaxyAssetManifest.digest(data) == root.lastPathComponent,
              let manifest = try? JSONDecoder().decode(GalaxyAssetManifest.self, from: data),
              (try? manifest.validate()) != nil else { return false }
        return manifest.files.allSatisfy { file in
            guard let data = try? Data(contentsOf: root.appendingPathComponent(file.path)) else { return false }
            return data.count == file.size && GalaxyAssetManifest.digest(data) == file.sha256
        }
    }
    func check() async {
        guard !checking else { return }
        checking = true
        status = "Checking GitHub for Galaxy updates…"
        defer { checking = false }
        var stage: URL?
        do {
            struct Commit: Decodable { let sha: String }
            let branch = Self.branch.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed.subtracting(CharacterSet(charactersIn: "/")))!
            let (commitData, _) = try await download(URL(string: "https://api.github.com/repos/\(Self.repository)/commits/\(branch)")!, limit: 1_048_576)
            let commit = try JSONDecoder().decode(Commit.self, from: commitData).sha
            guard commit.count == 40, commit.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
                throw BridgeError.message("Invalid GitHub revision.")
            }
            let base = URL(string: "https://raw.githubusercontent.com/\(Self.repository)/\(commit)/\(Self.resourcePath)/")!
            let (data, _) = try await download(base.appendingPathComponent("galaxy-native-manifest.json"), limit: 262_144)
            let manifest = try JSONDecoder().decode(GalaxyAssetManifest.self, from: data)
            try manifest.validate()
            let hash = GalaxyAssetManifest.digest(data)
            if readyRoot?.lastPathComponent == hash { status = "Galaxy is up to date."; return }
            let manager = FileManager.default
            try manager.createDirectory(at: cacheRoot, withIntermediateDirectories: true)
            let staging = cacheRoot.appendingPathComponent("staging-" + UUID().uuidString, isDirectory: true)
            stage = staging
            try manager.createDirectory(at: staging, withIntermediateDirectories: true)
            var completed = 0
            // Verify every file before publishing an update.
            for offset in stride(from: 0, to: manifest.files.count, by: 4) {
                try Task.checkCancellation()
                let batch = Array(manifest.files[offset..<min(offset + 4, manifest.files.count)])
                let saved = readyRoot
                let bundled = bundledRoot
                let fetch = self.fetch
                try await withThrowingTaskGroup(of: (String, Data).self) { group in
                    for file in batch {
                        group.addTask {
                            for root in [saved, bundled].compactMap({ $0 }) {
                                if let bytes = try? Data(contentsOf: root.appendingPathComponent(file.path)), bytes.count == file.size,
                                   GalaxyAssetManifest.digest(bytes) == file.sha256 { return (file.path, bytes) }
                            }
                            var request = URLRequest(url: base.appendingPathComponent(file.path))
                            request.timeoutInterval = 15
                            let (bytes, response) = try await fetch(request, max(file.size, 1))
                            guard response.statusCode == 200, bytes.count == file.size,
                                  GalaxyAssetManifest.digest(bytes) == file.sha256 else { throw BridgeError.message("Galaxy update verification failed.") }
                            return (file.path, bytes)
                        }
                    }
                    for try await (path, bytes) in group {
                        let destination = staging.appendingPathComponent(path)
                        try manager.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
                        try bytes.write(to: destination, options: .atomic)
                        completed += 1
                    }
                }
                status = "Preparing Galaxy update (\(completed)/\(manifest.files.count))…"
            }
            try data.write(to: staging.appendingPathComponent("manifest.json"), options: .atomic)
            try Task.checkCancellation()
            let destination = cacheRoot.appendingPathComponent(hash, isDirectory: true)
            if manager.fileExists(atPath: destination.path) { try manager.removeItem(at: destination) }
            try manager.moveItem(at: staging, to: destination)
            stage = nil
            // Keep one previous version while an open WebView is still using it.
            let previous = readyRoot
            readyRoot = destination
            defaults.set(hash, forKey: "galaxy.assets.manifest")
            if let contents = try? manager.contentsOfDirectory(at: cacheRoot, includingPropertiesForKeys: nil) {
                for root in contents where root.standardizedFileURL.path != destination.standardizedFileURL.path && root.standardizedFileURL.path != previous?.standardizedFileURL.path && root.standardizedFileURL.path != inUseRoot?.standardizedFileURL.path { try? manager.removeItem(at: root) }
            }
            status = "Galaxy update ready. It applies when you next open Galaxy."
        } catch {
            if let stage { try? FileManager.default.removeItem(at: stage) }
            status = "GitHub unavailable or update incompatible. Using saved Galaxy."
        }
    }
    private func download(_ url: URL, limit: Int) async throws -> (Data, HTTPURLResponse) {
        var request = URLRequest(url: url)
        request.timeoutInterval = 8
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        request.setValue("Galaxy-iPhone-Pilot", forHTTPHeaderField: "User-Agent")
        let result = try await fetch(request, limit)
        guard result.1.statusCode == 200 else { throw BridgeError.message("GitHub update unavailable.") }
        return result
    }
}
