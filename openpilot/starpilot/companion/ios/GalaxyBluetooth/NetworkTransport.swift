import Foundation
import Combine

/// Each request has an isolated, bounded buffer.
final class BoundedHTTP: NSObject, URLSessionDataDelegate, @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: CheckedContinuation<(Data, HTTPURLResponse), Error>?
    private var buffer = Data()
    private var response: HTTPURLResponse?
    private var task: URLSessionDataTask?
    private var session: URLSession?
    private var cancelled = false
    private let limit: Int
    init(limit: Int) { self.limit = limit }

    static func load(_ request: URLRequest, limit: Int) async throws -> (Data, HTTPURLResponse) {
        let client = BoundedHTTP(limit: limit)
        return try await withTaskCancellationHandler(operation: {
            try Task.checkCancellation()
            return try await withCheckedThrowingContinuation { client.start(request, continuation: $0) }
        }, onCancel: { client.cancel() })
    }
    private func start(_ request: URLRequest, continuation: CheckedContinuation<(Data, HTTPURLResponse), Error>) {
        lock.lock(); defer { lock.unlock() }
        guard !cancelled else { continuation.resume(throwing: CancellationError()); return }
        self.continuation = continuation
        let config = URLSessionConfiguration.ephemeral
        config.urlCache = nil
        config.httpCookieStorage = nil
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        config.connectionProxyDictionary = [:]
        let session = URLSession(configuration: config, delegate: self, delegateQueue: nil)
        self.session = session
        task = session.dataTask(with: request)
        task?.resume()
    }
    private func cancel() {
        lock.lock(); cancelled = true; let task = task; lock.unlock()
        task?.cancel()
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse,
                    completionHandler: @escaping (URLSession.ResponseDisposition) -> Void) {
        guard let http = response as? HTTPURLResponse, response.expectedContentLength <= limit else {
            completionHandler(.cancel); return
        }
        self.response = http
        completionHandler(.allow)
    }
    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        guard buffer.count + data.count <= limit else { dataTask.cancel(); return }
        buffer.append(data)
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        lock.lock(); let callback = continuation; continuation = nil; let cancelled = cancelled; lock.unlock()
        if cancelled { callback?.resume(throwing: CancellationError()) }
        else if let error { callback?.resume(throwing: error) }
        else if let response { callback?.resume(returning: (buffer, response)) }
        else { callback?.resume(throwing: BridgeError.message("Invalid HTTP response.")) }
        session.finishTasksAndInvalidate()
        self.session = nil
    }
}

@MainActor
final class LANTransport: ObservableObject, GalaxyRequestTransport {
    @Published private(set) var connected = false
    @Published private(set) var status = "Local connection not checked yet."
    var onEvent: ((String) -> Void)?
    private(set) var endpoint: URL?
    private(set) var generation = UUID().uuidString
    private(set) var expectedDeviceID: String?
    private(set) var verifiedDeviceID: String?

    private var cookie: String?
    private var sessionTask: (UUID, Task<String, Error>)?
    private let load: (URLRequest, Int) async throws -> (Data, HTTPURLResponse)
    init(load: @escaping (URLRequest, Int) async throws -> (Data, HTTPURLResponse) = { try await PrivateLANHTTP.load($0, limit: $1) }) {
        self.load = load
    }

    // An explicit private IPv4 address prevents cloud/loopback endpoints from being treated as the local comma.
    static func endpoint(_ address: String) throws -> URL {
        let parts = address.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 4, parts.allSatisfy({ !$0.isEmpty && $0.allSatisfy(\.isNumber) }),
              parts.allSatisfy({ String(Int($0) ?? -1) == $0 }),
              let a = Int(parts[0]), let b = Int(parts[1]), parts.allSatisfy({ (0...255).contains(Int($0) ?? -1) }),
              a == 10 || (a == 172 && (16...31).contains(b)) || (a == 192 && b == 168),
              let url = URL(string: "http://\(parts.joined(separator: ".")):8082") else {
            throw BridgeError.message("Enter your comma’s local IP address, such as 192.168.10.85.")
        }
        return url
    }
    func configure(address: String) throws {
        let new = try Self.endpoint(address)
        if endpoint != new { endpoint = new; invalidate(reason: "Comma LAN address changed") }
    }
    static func reportedAddress(_ data: Data) -> String? {
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let addresses = json["addresses"] as? [[String: Any]] else { return nil }
        return addresses.compactMap { row -> String? in
            guard let text = row["url"] as? String, let url = URL(string: text),
                  let host = url.host, let expected = try? endpoint(host),
                  url.scheme == "http", url.port == 8082, url.user == nil, url.password == nil,
                  url.host == expected.host else { return nil }
            return host
        }.first
    }
    static func deviceID(_ data: Data) -> String? {
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              json["schemaVersion"] as? Int == 1, json["monitor"] as? String == "local",
              let value = json["instance"] as? String,
              value.count == 16, value.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else { return nil }
        return value
    }
    func bind(to identity: String?) {
        if expectedDeviceID != identity { expectedDeviceID = identity; invalidate(reason: "Paired comma identity changed") }
    }
    func clearEndpoint() { endpoint = nil; invalidate(reason: "Saved LAN endpoint cleared") }
    func invalidate(reason: String = "LAN verification reset") {
        cookie = nil; sessionTask?.1.cancel(); sessionTask = nil
        connected = false; verifiedDeviceID = nil; generation = UUID().uuidString
        onEvent?(reason)
    }
    func probe() async -> Bool {
        guard endpoint != nil else { return false }
        let expectedGeneration = generation
        do {
            let (data, response) = try await authenticated(path: "/data/runtime.json", method: "GET", headers: [:], body: Data(), limit: 4096)
            guard !Task.isCancelled, expectedGeneration == generation else { return false }
            let identity = Self.deviceID(data)
            let available = response.statusCode == 200 && identity != nil
                && (expectedDeviceID == nil || identity == expectedDeviceID)
            guard !Task.isCancelled, expectedGeneration == generation else { return false }
            let changed = connected != available
            connected = available
            verifiedDeviceID = available ? identity : nil
            status = available ? "Local comma verified." : "Local endpoint unavailable or does not match the paired comma."
            if changed { onEvent?(available ? "LAN probe succeeded; comma identity verified" : "LAN probe rejected: HTTP \(response.statusCode), unavailable status or identity mismatch") }
        } catch {
            if !Task.isCancelled, expectedGeneration == generation {
                status = error.localizedDescription
                invalidate(reason: "LAN probe failed: \(Self.failureCode(error))")
            }
        }
        return connected
    }
    static func failureCode(_ error: Error) -> String {
        let value = error as NSError
        if let url = error as? URLError {
            let name: String
            switch url.code {
            case .timedOut: name = "timeout"
            case .networkConnectionLost: name = "connection lost"
            case .notConnectedToInternet: name = "no network route"
            case .cannotConnectToHost: name = "cannot reach comma"
            case .cancelled: name = "cancelled"
            default: name = "network error"
            }
            return "\(name) (\(value.domain) \(value.code))"
        }
        return "\(value.domain) \(value.code)"
    }
    private func sessionCookie(endpoint: URL, generation original: String) async throws -> String {
        if let cookie { return cookie }
        let token: UUID
        let pending: Task<String, Error>
        if let existing = sessionTask { (token, pending) = existing }
        else {
            token = UUID()
            pending = Task {
                var request = URLRequest(url: endpoint.appendingPathComponent("api/auth/session"))
                request.timeoutInterval = 8
                let (data, response) = try await load(request, 65_536)
                let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                let cookies = HTTPCookie.cookies(withResponseHeaderFields: response.allHeaderFields.reduce(into: [String: String]()) {
                    if let key = $1.key as? String { $0[key] = String(describing: $1.value) }
                }, for: endpoint)
                guard response.statusCode == 200, json?["authenticated"] as? Bool == true,
                      json?["localAccess"] as? Bool == true,
                      let value = cookies.first(where: { $0.name == "galaxy_session" && !$0.value.isEmpty }) else {
                    throw BridgeError.message("Couldn’t open a local Galaxy session. Connect directly to comma’s Wi-Fi.")
                }
                return "galaxy_session=\(value.value)"
            }
            sessionTask = (token, pending)
        }
        defer { if sessionTask?.0 == token { sessionTask = nil } }
        let value = try await pending.value
        try Task.checkCancellation()
        guard original == generation, self.endpoint == endpoint else { throw CancellationError() }
        cookie = value
        return value
    }

    private func authenticated(path: String, method: String, headers: [String: String], body: Data,
                               limit: Int) async throws -> (Data, HTTPURLResponse) {
        guard let endpoint else { throw URLError(.notConnectedToInternet) }
        let original = generation
        for attempt in 0...1 {
            let usedCookie = try await sessionCookie(endpoint: endpoint, generation: original)
            guard original == generation else { throw CancellationError() }
            var request = URLRequest(url: URL(string: endpoint.absoluteString + path)!)
            request.httpMethod = method
            request.httpBody = body.isEmpty ? nil : body
            request.timeoutInterval = LocalRequest.isPackageUpload(method: method, target: path) ? 120 : 8
            for (name, value) in headers where ["accept", "range", "content-type"].contains(name.lowercased()) {
                request.setValue(value, forHTTPHeaderField: name)
            }
            request.setValue(usedCookie, forHTTPHeaderField: "Cookie")
            if !["GET", "HEAD"].contains(method) {
                request.setValue(endpoint.absoluteString, forHTTPHeaderField: "Origin")
                request.setValue(LocalRequest.isPackageUpload(method: method, target: path) ? "application/octet-stream" : "application/json", forHTTPHeaderField: "Content-Type")
            }
            let result = try await load(request, limit)
            try Task.checkCancellation()
            guard original == generation, self.endpoint == endpoint else { throw CancellationError() }
            let message = (try? JSONSerialization.jsonObject(with: result.0)) as? [String: Any]
            if attempt == 0, result.1.statusCode == 401,
               message?["error"] as? String == "Refresh the local Galaxy session" {
                // The server rejected this operation before execution. Retry only this explicit response.
                if cookie == usedCookie { cookie = nil }
                continue
            }
            return result
        }
        throw BridgeError.message("Galaxy session expired. Reconnect to comma.")
    }

    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        guard connected else { throw URLError(.notConnectedToInternet) }
        guard SecretGoodGalaxy.validTarget(path),
              ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"].contains(method), body.count <= LocalRequest.bodyLimit(method: method, target: path) else {
            throw BridgeError.message("Invalid Galaxy request.")
        }
        let (data, response) = try await authenticated(path: path, method: method, headers: headers, body: body, limit: 8 * Wire.maxBody)
        var responseHeaders: [String: String] = [:]
        for (key, value) in response.allHeaderFields {
            if let name = key as? String, ["content-type", "content-range", "accept-ranges", "content-disposition"].contains(name.lowercased()) {
                responseHeaders[name.lowercased()] = String(describing: value)
            }
        }
        return BridgeResponse(id: UUID().uuidString, session: generation, counter: 0, status: response.statusCode,
                              headers: responseHeaders, body: data.base64EncodedString())
    }
}

enum ConnectionMode: String, CaseIterable, Identifiable {
    case automatic, lan, bluetooth
    var id: String { rawValue }
    var title: String { switch self { case .automatic: "Automatic"; case .lan: "Wi-Fi only"; case .bluetooth: "Bluetooth only" } }
}

@MainActor
final class PreferredTransport: ObservableObject, GalaxyRequestTransport {
    let lan: any GalaxyRequestTransport
    let bluetooth: any GalaxyRequestTransport
    var invalidateLAN: (String) -> Void
    @Published var mode: ConnectionMode = .automatic
    var connected: Bool { (mode != .bluetooth && lan.connected) || (mode != .lan && bluetooth.connected) }
    var usesLAN: Bool { mode != .bluetooth && lan.connected }
    var label: String { usesLAN ? "Wi-Fi" : bluetooth.connected && mode != .lan ? "Bluetooth" : "Reconnecting…" }
    var catalogSHA256: String? { usesLAN ? lan.catalogSHA256 : bluetooth.catalogSHA256 }
    init(lan: any GalaxyRequestTransport, bluetooth: any GalaxyRequestTransport, invalidateLAN: @escaping (String) -> Void) {
        self.lan = lan; self.bluetooth = bluetooth; self.invalidateLAN = invalidateLAN
    }
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        try Task.checkCancellation()
        if usesLAN {
            do { return try await lan.request(path: path, method: method, headers: headers, body: body) }
            catch {
                try Task.checkCancellation()
                guard error is URLError else { throw error }
                invalidateLAN("LAN request failed: \(LANTransport.failureCode(error))")
                // Retry reads only; never replay a setting change.
                if !["GET", "HEAD"].contains(method) {
                    throw BridgeError.message("Wi-Fi disconnected. This change may have saved; reload the setting to confirm before trying again.")
                }
                guard mode == .automatic, bluetooth.connected else { throw error }
            }
        }
        if SecretGoodGalaxy.needsWiFi(path) {
            return BridgeResponse(id: UUID().uuidString, session: "wifi-required", counter: 0, status: 501,
                                  headers: ["content-type": "application/json"],
                                  body: Data("{\"error\":\"Connect to comma over local Wi-Fi to use this feature.\"}".utf8).base64EncodedString())
        }
        guard mode != .lan, bluetooth.connected else { throw BridgeError.message("Your comma is disconnected. Open Connections to reconnect.") }
        return try await bluetooth.request(path: path, method: method, headers: headers, body: body)
    }
}

@MainActor
enum LANDiscoveryMatch {
    static func first(addresses: [String], expectedDeviceID: String?, stillCurrent: () -> Bool,
                      probe: (String, String) async -> Bool) async -> String? {
        guard let identity = expectedDeviceID, !identity.isEmpty else { return nil }
        var seen = Set<String>()
        for address in addresses.prefix(16) {
            guard !Task.isCancelled, stillCurrent() else { return nil }
            guard seen.insert(address).inserted, (try? LANTransport.endpoint(address)) != nil else { continue }
            let verified = await probe(address, identity)
            guard !Task.isCancelled, stillCurrent() else { return nil }
            if verified { return address }
        }
        return nil
    }
}
