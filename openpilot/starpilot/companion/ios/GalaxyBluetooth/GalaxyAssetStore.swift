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

/// Comma's inventory of its Galaxy pages, from `GET /api/companion/web-manifest`.
struct GalaxyListing: Decodable {
    let schema: Int
    let commit: String?
    let files: [GalaxyAssetManifest.File]
}

/// One GET to comma over Wi-Fi/LAN: the HTTP status and body.
typealias GalaxyPageFetch = @Sendable (_ path: String, _ limit: Int) async throws -> (status: Int, data: Data)

/// Keeps the Bluetooth copy of Galaxy matched to the pages comma serves, downloaded over Wi-Fi/LAN.
@MainActor
final class GalaxyAssetStore: ObservableObject {
    static let notDownloaded = "Galaxy screens aren’t downloaded yet. Connect to comma over Wi-Fi once."
    static let tooOld = "Comma’s software is too old to share Galaxy screens; update comma."
    @Published private(set) var status = GalaxyAssetStore.notDownloaded
    @Published private(set) var checking = false
    @Published private(set) var readyRoot: URL?
    var inUseRoot: URL?
    private let cacheRoot: URL
    private let defaults: UserDefaults
    init(cacheRoot: URL? = nil, defaults: UserDefaults = .standard) {
        self.cacheRoot = cacheRoot ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("DeviceGalaxyUpdates", isDirectory: true)
        self.defaults = defaults
        // Validate saved assets before trusting a previous completed update.
        if let hash = defaults.string(forKey: "galaxy.device.assets.manifest"), GalaxyAssetManifest.isHash(hash) {
            let root = self.cacheRoot.appendingPathComponent(hash, isDirectory: true)
            if Self.verify(root) { readyRoot = root; status = "Using Galaxy screens saved from comma." }
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
    /// True when comma now runs a different build than the one the saved screens came from.
    func olderThan(commit: String?) -> Bool {
        guard readyRoot != nil, let saved = defaults.string(forKey: "galaxy.device.commit"), !saved.isEmpty,
              let commit, !commit.isEmpty else { return false }
        return saved != commit
    }
    /// Over Bluetooth nothing can be downloaded; tell the user when the saved screens are behind comma.
    func noteCommaBuild(commit: String?) {
        if olderThan(commit: commit) { status = "Galaxy screens are from an older comma build. Connect over Wi-Fi to refresh." }
    }
    /// Compares comma's inventory with the saved copy and downloads only what changed. Never skips on an unchanged commit.
    func check(fetch: @escaping GalaxyPageFetch, stillCurrent: () -> Bool = { true }) async {
        guard !checking else { return }
        checking = true
        status = "Checking comma for Galaxy updates…"
        defer { checking = false }
        var stage: URL?
        do {
            let (code, listingData) = try await fetch("/api/companion/web-manifest", 1_048_576)
            // Older comma builds answer 401 (no session) or 404 for the inventory path.
            if code == 401 || code == 404 { throw BridgeError.message(Self.tooOld) }
            guard code == 200 else { throw BridgeError.message("Comma returned HTTP \(code) for the Galaxy inventory.") }
            let listing = try JSONDecoder().decode(GalaxyListing.self, from: listingData)
            guard listing.schema == 1 else { throw BridgeError.message(Self.tooOld) }
            let manifest = GalaxyAssetManifest(schema: 1, nativeBridge: 1, files: listing.files.sorted { $0.path < $1.path })
            try manifest.validate()
            let encoder = JSONEncoder(); encoder.outputFormatting = .sortedKeys
            let data = try encoder.encode(manifest)
            let hash = GalaxyAssetManifest.digest(data)
            guard stillCurrent() else { throw CancellationError() }
            if readyRoot?.lastPathComponent == hash { defaults.set(listing.commit ?? "", forKey: "galaxy.device.commit"); status = "Galaxy matches comma."; return }
            let manager = FileManager.default
            try manager.createDirectory(at: cacheRoot, withIntermediateDirectories: true)
            let staging = cacheRoot.appendingPathComponent("staging-" + UUID().uuidString, isDirectory: true)
            stage = staging
            try manager.createDirectory(at: staging, withIntermediateDirectories: true)
            let saved = readyRoot
            var done = 0
            for offset in stride(from: 0, to: manifest.files.count, by: 4) {
                try Task.checkCancellation()
                let batch = Array(manifest.files[offset..<min(offset + 4, manifest.files.count)])
                try await withThrowingTaskGroup(of: (String, Data).self) { group in
                    for file in batch {
                        group.addTask {
                            func matches(_ bytes: Data) -> Bool { bytes.count == file.size && GalaxyAssetManifest.digest(bytes) == file.sha256 }
                            if let saved, let bytes = try? Data(contentsOf: saved.appendingPathComponent(file.path)), matches(bytes) { return (file.path, bytes) }
                            let (code, bytes) = try await fetch("/" + file.path, max(file.size, 1))
                            guard code == 200, matches(bytes) else { throw BridgeError.message("Galaxy update verification failed.") }
                            return (file.path, bytes)
                        }
                    }
                    for try await (path, bytes) in group {
                        let destination = staging.appendingPathComponent(path)
                        try manager.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
                        try bytes.write(to: destination, options: .atomic)
                    }
                }
                done += batch.count
                status = "Preparing Galaxy update (\(done)/\(manifest.files.count))…"
            }
            guard stillCurrent() else { throw CancellationError() }
            try data.write(to: staging.appendingPathComponent("manifest.json"), options: .atomic)
            let destination = cacheRoot.appendingPathComponent(hash, isDirectory: true)
            if manager.fileExists(atPath: destination.path) { try manager.removeItem(at: destination) }
            try manager.moveItem(at: staging, to: destination)
            stage = nil
            // Keep one previous version while an open WebView is still using it.
            readyRoot = destination
            defaults.set(hash, forKey: "galaxy.device.assets.manifest")
            defaults.set(listing.commit ?? "", forKey: "galaxy.device.commit")
            if let contents = try? manager.contentsOfDirectory(at: cacheRoot, includingPropertiesForKeys: nil) {
                for root in contents where root.standardizedFileURL.path != destination.standardizedFileURL.path && root.standardizedFileURL.path != saved?.standardizedFileURL.path && root.standardizedFileURL.path != inUseRoot?.standardizedFileURL.path { try? manager.removeItem(at: root) }
            }
            status = "Galaxy screens updated from comma. Open Galaxy to use them."
        } catch {
            if let stage { try? FileManager.default.removeItem(at: stage) }
            let using = readyRoot == nil ? "No Galaxy screens are saved yet." : "Using your saved Galaxy screens."
            if let failure = error as? URLError {
                status = "Couldn’t reach comma to check Galaxy updates (network error \(failure.code.rawValue)). \(using)"
            } else if let failure = error as? BridgeError {
                status = "\(failure.localizedDescription) \(using)"
            } else if error is CancellationError {
                status = "Galaxy update cancelled. \(using)"
            } else {
                status = "Galaxy update could not be read or saved. \(using)"
            }
        }
    }
}
