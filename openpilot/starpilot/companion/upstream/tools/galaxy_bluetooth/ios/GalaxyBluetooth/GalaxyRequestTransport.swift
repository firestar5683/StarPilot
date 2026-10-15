import Foundation

@MainActor
protocol GalaxyRequestTransport: AnyObject {
    var connected: Bool { get }
    var catalogSHA256: String? { get }
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse
}

extension GalaxyRequestTransport {
    var catalogSHA256: String? { nil }
}

/// Share concurrent settings reads and reuse only stable metadata.
@MainActor
final class GalaxyReadCache: GalaxyRequestTransport {
    private let transport: any GalaxyRequestTransport
    private let sessionID: () -> String
    private let now: () -> TimeInterval
    private var session = ""
    private var generation: UInt64 = 0
    private var entries: [String: (BridgeResponse, TimeInterval)] = [:]
    private var pending: [String: (UUID, Task<BridgeResponse, Error>)] = [:]
    var connected: Bool { transport.connected }
    var catalogSHA256: String? { transport.catalogSHA256 }

    init(transport: any GalaxyRequestTransport, sessionID: @escaping () -> String,
         now: @escaping () -> TimeInterval = { ProcessInfo.processInfo.systemUptime }) {
        self.transport = transport
        self.sessionID = sessionID
        self.now = now
    }

    private func invalidate() {
        generation += 1
        entries.removeAll()
        // Already-sent reads still drain, but new reads cannot join an old one.
        pending.removeAll()
    }

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
        let metadata = path == "/api/params/defaults"
            || path == "/assets/components/tools/device_settings_layout.json?v=settings-tier-1"
        guard body.isEmpty, metadata || path == "/api/params/all" || path == "/api/params/all?galaxy_ble_settings=1" else {
            return try await transport.request(path: path, method: method, headers: headers, body: body)
        }
        let relevantHeaders = headers.filter { ["accept", "cookie", "range"].contains($0.key.lowercased()) }
            .map { "\($0.key.lowercased()):\($0.value)" }.sorted().joined(separator: "\n")
        let cacheKey = path + "\n" + relevantHeaders
        if let (response, expires) = entries[cacheKey], expires > now() { return response }
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
        if metadata, response.status == 200, response.bodyData.count <= Wire.maxBody,
           readGeneration == generation, readSession == sessionID(), connected {
            if entries.count >= 16 { entries.removeAll() }
            entries[cacheKey] = (response, now() + 300)
        }
        try Task.checkCancellation()
        return response
    }
}
