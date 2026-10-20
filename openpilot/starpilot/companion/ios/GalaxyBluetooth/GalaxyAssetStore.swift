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
                  ["index.html", "manifest.webmanifest", "sentry-push-worker.js"].contains(file.path) || ["assets/", "css/", "js/", "vendor/", "data/"].contains(where: { file.path.hasPrefix($0) }),
                  (0...4_194_304).contains(file.size), Self.isHash(file.sha256) else {
                throw BridgeError.message("Invalid Galaxy update file.")
            }
            total += file.size
        }
        guard total <= 32 * 1_048_576, files.contains(where: { $0.path == "index.html" }),
              files.contains(where: { $0.path == "js/boot.js" }),
              files.contains(where: { $0.path == "js/app.js" }),
              files.contains(where: { $0.path == "data/catalog.json" }),
              !files.contains(where: { $0.path == "data/runtime.json" || $0.path.hasSuffix(".sample.json") }) else { throw BridgeError.message("Galaxy update is incomplete or too large.") }
    }
    static func isHash(_ value: String) -> Bool { value.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) } }
    static func digest(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
}

struct GalaxySource: Equatable {
    let repository: String
    let commit: String
    let branch: String
    var key: String { repository + "@" + commit }

    init(repository: String, commit: String, branch: String) throws {
        let parts = repository.split(separator: "/", omittingEmptySubsequences: false)
        guard parts.count == 2, parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." && $0.utf8.allSatisfy { (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || [45,46,95].contains($0) } }),
              commit.count == 40, commit.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
            throw BridgeError.message("Comma did not provide a supported public GitHub revision.")
        }
        self.repository = repository; self.commit = commit; self.branch = branch
    }
    static func parse(_ data: Data) throws -> GalaxySource {
        struct Status: Decodable {
            struct Installed: Decodable { let commit: String; let branch: String }
            struct Operations: Decodable { let repository: String? }
            let installed: Installed
            let operations: Operations
        }
        let status = try JSONDecoder().decode(Status.self, from: data)
        return try GalaxySource(repository: status.operations.repository ?? "", commit: status.installed.commit, branch: status.installed.branch)
    }
}

@MainActor
final class GalaxyAssetStore: ObservableObject {
    static let resourcePath = "openpilot/starpilot/galaxy/web"
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
        self.cacheRoot = cacheRoot ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("DeviceGalaxyUpdates", isDirectory: true)
        self.defaults = defaults
        self.fetch = fetch
        // Validate saved assets before trusting a previous completed update.
        if let hash = defaults.string(forKey: "galaxy.device.assets.manifest"), GalaxyAssetManifest.isHash(hash) {
            let root = self.cacheRoot.appendingPathComponent(hash, isDirectory: true)
            if Self.verify(root) { status = "Saved Galaxy available; waiting to match your comma." }
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
    func unavailable(_ message: String) {
        status = message + " Using the bundled Galaxy screens; version match is unverified."
        readyRoot = nil
    }
    func check(source: GalaxySource, stillCurrent: () -> Bool = { true }) async {
        guard !checking else { return }
        checking = true
        status = "Checking GitHub for Galaxy updates…"
        defer { checking = false }
        var stage: URL?
        do {
            let commit = source.commit
            if defaults.string(forKey: "galaxy.device.source") == source.key,
               let hash = defaults.string(forKey: "galaxy.device.assets.manifest") {
                let saved = cacheRoot.appendingPathComponent(hash, isDirectory: true)
                if Self.verify(saved) { readyRoot = saved }
            }
            if defaults.string(forKey: "galaxy.device.source") != source.key { readyRoot = nil }
            let base = URL(string: "https://raw.githubusercontent.com/\(source.repository)/\(commit)/\(Self.resourcePath)/")!
            if readyRoot != nil, defaults.string(forKey: "galaxy.device.source") == source.key {
                status = "Galaxy matches comma (\(source.branch), \(commit.prefix(7)))."; return
            }
            struct Tree: Decodable {
                struct Entry: Decodable { let path: String; let type: String; let sha: String; let size: Int? }
                let tree: [Entry]
                let truncated: Bool
            }
            let (treeData, _) = try await download(URL(string: "https://api.github.com/repos/\(source.repository)/git/trees/\(commit)?recursive=1")!, limit: 8 * 1_048_576)
            let tree = try JSONDecoder().decode(Tree.self, from: treeData)
            guard !tree.truncated else { throw BridgeError.message("Galaxy update inventory is incomplete.") }
            let prefix = Self.resourcePath + "/"
            let inventory = tree.tree.filter { $0.type == "blob" && $0.path.hasPrefix(prefix) }
                .filter { !$0.path.hasSuffix("/runtime.json") && !$0.path.hasSuffix(".sample.json") }
                .sorted { $0.path < $1.path }
            let provisional = GalaxyAssetManifest(schema: 1, nativeBridge: 1, files: inventory.map {
                GalaxyAssetManifest.File(path: String($0.path.dropFirst(prefix.count)), sha256: String(repeating: "0", count: 64), size: $0.size ?? -1)
            })
            try provisional.validate()
            let manager = FileManager.default
            try manager.createDirectory(at: cacheRoot, withIntermediateDirectories: true)
            let staging = cacheRoot.appendingPathComponent("staging-" + UUID().uuidString, isDirectory: true)
            stage = staging
            try manager.createDirectory(at: staging, withIntermediateDirectories: true)
            var verified: [GalaxyAssetManifest.File] = []
            for offset in stride(from: 0, to: inventory.count, by: 4) {
                try Task.checkCancellation()
                let batch = Array(inventory[offset..<min(offset + 4, inventory.count)])
                let roots = [readyRoot, bundledRoot].compactMap { $0 }
                let fetch = self.fetch
                try await withThrowingTaskGroup(of: (String, Data).self) { group in
                    for file in batch {
                        group.addTask {
                            let path = String(file.path.dropFirst(prefix.count))
                            func matches(_ bytes: Data) -> Bool {
                                guard bytes.count == file.size else { return false }
                                let object = Data("blob \(bytes.count)\0".utf8) + bytes
                                return Insecure.SHA1.hash(data: object).map { String(format: "%02x", $0) }.joined() == file.sha
                            }
                            for root in roots {
                                if let bytes = try? Data(contentsOf: root.appendingPathComponent(path)), matches(bytes) { return (path, bytes) }
                            }
                            var request = URLRequest(url: base.appendingPathComponent(path))
                            request.timeoutInterval = 15
                            let (bytes, response) = try await fetch(request, max(file.size ?? 0, 1))
                            guard response.statusCode == 200, matches(bytes) else { throw BridgeError.message("Galaxy update verification failed.") }
                            return (path, bytes)
                        }
                    }
                    for try await (path, bytes) in group {
                        let destination = staging.appendingPathComponent(path)
                        try manager.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
                        try bytes.write(to: destination, options: .atomic)
                        verified.append(.init(path: path, sha256: GalaxyAssetManifest.digest(bytes), size: bytes.count))
                    }
                }
                status = "Preparing Galaxy update (\(verified.count)/\(inventory.count))…"
            }
            let manifest = GalaxyAssetManifest(schema: 1, nativeBridge: 1, files: verified.sorted { $0.path < $1.path })
            try manifest.validate()
            let encoder = JSONEncoder(); encoder.outputFormatting = .sortedKeys
            let data = try encoder.encode(manifest)
            let hash = GalaxyAssetManifest.digest(data)
            guard stillCurrent() else { throw CancellationError() }
            if readyRoot?.lastPathComponent == hash {
                try manager.removeItem(at: staging); stage = nil
                defaults.set(commit, forKey: "galaxy.device.commit")
                defaults.set(source.key, forKey: "galaxy.device.source")
                status = "Galaxy matches comma (\(source.branch), \(commit.prefix(7)))."; return
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
            defaults.set(hash, forKey: "galaxy.device.assets.manifest")
            defaults.set(commit, forKey: "galaxy.device.commit")
            defaults.set(source.key, forKey: "galaxy.device.source")
            if let contents = try? manager.contentsOfDirectory(at: cacheRoot, includingPropertiesForKeys: nil) {
                for root in contents where root.standardizedFileURL.path != destination.standardizedFileURL.path && root.standardizedFileURL.path != previous?.standardizedFileURL.path && root.standardizedFileURL.path != inUseRoot?.standardizedFileURL.path { try? manager.removeItem(at: root) }
            }
            status = "Galaxy matched to comma (\(source.branch), \(commit.prefix(7))). Open Galaxy to use it."
        } catch {
            if let stage { try? FileManager.default.removeItem(at: stage) }
            let source = readyRoot == nil ? "the Galaxy version included with this app" : "your saved Galaxy version"
            if let failure = error as? URLError {
                status = "Couldn’t check Galaxy updates (network error \(failure.code.rawValue)). Using \(source)."
            } else if let failure = error as? BridgeError {
                status = "\(failure.localizedDescription) Using \(source)."
            } else if error is CancellationError {
                status = "Galaxy update cancelled. Using \(source)."
            } else {
                status = "Galaxy update could not be read or saved. Using \(source)."
            }
        }
    }
    private func download(_ url: URL, limit: Int) async throws -> (Data, HTTPURLResponse) {
        var request = URLRequest(url: url)
        request.timeoutInterval = 8
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        request.setValue("Galaxy-iPhone-Pilot", forHTTPHeaderField: "User-Agent")
        let result = try await fetch(request, limit)
        guard result.1.statusCode == 200 else { throw BridgeError.message("GitHub update check returned HTTP \(result.1.statusCode).") }
        return result
    }
}
