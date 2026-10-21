import Foundation

@MainActor
protocol GalaxyRequestTransport: AnyObject {
    var connected: Bool { get }
    var catalogSHA256: String? { get }
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse
    /// GET one Galaxy page file (not an API call). Only the Wi-Fi/LAN transport can do this.
    func page(path: String) async throws -> BridgeResponse
}

extension GalaxyRequestTransport {
    var catalogSHA256: String? { nil }
    func page(path: String) async throws -> BridgeResponse {
        throw BridgeError.message("Galaxy screens can only be downloaded from comma over Wi-Fi.")
    }
}

enum SecretGoodGalaxy {
    static func validTarget(_ path: String) -> Bool {
        guard path.hasPrefix("/"), !path.hasPrefix("//"),
              let parts = URLComponents(string: path), parts.scheme == nil, parts.host == nil, parts.fragment == nil,
              let decoded = parts.percentEncodedPath.removingPercentEncoding,
              !decoded.contains("%"), !decoded.contains("\\"), !decoded.contains("//"),
              !decoded.unicodeScalars.contains(where: { $0.value < 32 }),
              !decoded.split(separator: "/").contains(where: { $0 == "." || $0 == ".." }) else { return false }
        return decoded.hasPrefix("/api/") || decoded == "/data/runtime.json"
    }
    /// A Galaxy page file under the same roots the app accepts when it saves comma's screens.
    static func validPage(_ path: String) -> Bool {
        guard path.hasPrefix("/"), path.utf8.allSatisfy({ (48...57).contains($0) || (65...90).contains($0) || (97...122).contains($0) || [45, 46, 47, 95].contains($0) }) else { return false }
        let file = String(path.dropFirst())
        let parts = file.split(separator: "/", omittingEmptySubsequences: false)
        guard !parts.isEmpty, parts.allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }), file != "data/runtime.json" else { return false }
        return ["index.html", "manifest.webmanifest", "sentry-push-worker.js"].contains(file)
            || ["assets/", "css/", "js/", "vendor/", "data/"].contains(where: { file.hasPrefix($0) })
    }
    static func needsWiFi(_ path: String) -> Bool {
        let path = URLComponents(string: path)?.path ?? path
        return ["/api/recordings/", "/api/replay/", "/api/cameras/", "/api/maps/tiles/",
                "/api/android-auto/upload", "/api/android-auto/apk", "/api/phone-internet/", "/api/spotify/upload"].contains(where: { path.hasPrefix($0) })
            || ["/api/auth/login", "/api/auth/logout"].contains(path)
    }
}

/// Coalesce simultaneous identical reads. View/intent tokens are never cached for later use.
@MainActor
final class GalaxyReadCache: GalaxyRequestTransport {
    private let transport: any GalaxyRequestTransport
    private let sessionID: () -> String
    private var session = ""
    private var generation: UInt64 = 0
    private var pending: [String: (UUID, Task<BridgeResponse, Error>)] = [:]
    var connected: Bool { transport.connected }
    var catalogSHA256: String? { transport.catalogSHA256 }

    init(transport: any GalaxyRequestTransport, sessionID: @escaping () -> String,
         now: @escaping () -> TimeInterval = { ProcessInfo.processInfo.systemUptime }) {
        self.transport = transport
        self.sessionID = sessionID
    }

    private func invalidate() {
        generation += 1
        // Already-sent reads still drain, but new reads cannot join an old one.
        pending.removeAll()
    }

    func page(path: String) async throws -> BridgeResponse { try await transport.page(path: path) }

    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        try Task.checkCancellation()
        if session != sessionID() {
            session = sessionID()
            invalidate()
        }
        guard connected else { throw BridgeError.message("Connect to your comma over Bluetooth first.") }
        if method != "GET" {
            invalidate()
            defer { invalidate() }
            return try await transport.request(path: path, method: method, headers: headers, body: body)
        }
        guard body.isEmpty, path.hasPrefix("/api/"), headers.keys.allSatisfy({ !["authorization", "range"].contains($0.lowercased()) }) else {
            return try await transport.request(path: path, method: method, headers: headers, body: body)
        }
        let relevantHeaders = headers
            .map { "\($0.key.lowercased()):\($0.value)" }.sorted().joined(separator: "\n")
        let cacheKey = path + "\n" + relevantHeaders
        let token: UUID
        let task: Task<BridgeResponse, Error>
        if let existing = pending[cacheKey] {
            (token, task) = existing
        } else {
            // Bound cache variants even when a local client changes headers.
            guard pending.count < 16 else {
                return try await transport.request(path: path, method: method, headers: headers, body: body)
            }
            token = UUID()
            task = Task { try await transport.request(path: path, method: method, headers: headers, body: body) }
            pending[cacheKey] = (token, task)
        }
        let readGeneration = generation
        let readSession = session
        defer { if pending[cacheKey]?.0 == token { pending.removeValue(forKey: cacheKey) } }
        let response = try await task.value
        guard readGeneration == generation, readSession == sessionID(), connected else {
            throw BridgeError.message("Connection or saved settings changed during this read. Load the page again.")
        }
        try Task.checkCancellation()
        return response
    }
}
