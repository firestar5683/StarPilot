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
    private(set) var endpoint: URL?
    private(set) var generation = UUID().uuidString
    private(set) var expectedDeviceID: String?

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
        if endpoint != new { endpoint = new; invalidate() }
    }
    static func reportedAddress(_ data: Data) -> String? {
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let ip = json["lanIp"] as? String, (try? endpoint(ip)) != nil else { return nil }
        return ip
    }
    static func deviceID(_ data: Data) -> String? {
        guard let value = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
              value.count == 16, value.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else { return nil }
        return value
    }
    func bind(to identity: String?) {
        if expectedDeviceID != identity { expectedDeviceID = identity; invalidate() }
    }
    func clearEndpoint() { endpoint = nil; invalidate() }
    func invalidate() { connected = false; generation = UUID().uuidString }
    func probe() async -> Bool {
        guard let endpoint else { return false }
        var request = URLRequest(url: endpoint.appendingPathComponent("api/device/status"))
        request.timeoutInterval = 2
        let expectedGeneration = generation
        do {
            let (data, response) = try await PrivateLANHTTP.load(request, limit: 65_536)
            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
            guard !Task.isCancelled, expectedGeneration == generation else { return false }
            var available = response.statusCode == 200 && json?["online"] as? Bool == true
                && ["Parked", "Driving"].contains(json?["status"] as? String ?? "")
            if available, let expectedDeviceID {
                var identityRequest = URLRequest(url: URL(string: endpoint.absoluteString + "/api/params?key=DongleId")!)
                identityRequest.timeoutInterval = 2
                let (identity, identityResponse) = try await PrivateLANHTTP.load(identityRequest, limit: 256)
                available = identityResponse.statusCode == 200 && Self.deviceID(identity) == expectedDeviceID
            }
            guard !Task.isCancelled, expectedGeneration == generation else { return false }
            connected = available
            status = available ? "Local comma verified." : "Local endpoint unavailable or does not match the paired comma."
        } catch { if !Task.isCancelled, expectedGeneration == generation { status = error.localizedDescription; invalidate() } }
        return connected
    }
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        guard connected, let endpoint else { throw URLError(.notConnectedToInternet) }
        guard let relative = URLComponents(string: path), relative.scheme == nil, relative.host == nil,
              relative.fragment == nil, path.hasPrefix("/"), !path.hasPrefix("//"),
              let decoded = relative.percentEncodedPath.removingPercentEncoding,
              !decoded.contains("\\"), !decoded.contains("%"), !decoded.contains("//"),
              !decoded.unicodeScalars.contains(where: { $0.value < 32 }),
              !decoded.split(separator: "/").contains(where: { $0 == "." || $0 == ".." }),
              decoded.hasPrefix("/api/") || decoded == "/assets/components/tools/device_settings_layout.json",
              ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"].contains(method), body.count <= Wire.maxBody,
              let url = URL(string: endpoint.absoluteString + path) else {
            throw BridgeError.message("Invalid Galaxy request.")
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body.isEmpty ? nil : body
        // Bound stale-route delay; long downloads/streams need a separate route.
        request.timeoutInterval = 8
        for (name, value) in headers where ["content-type", "accept", "cookie", "range"].contains(name.lowercased()) {
            request.setValue(value, forHTTPHeaderField: name)
        }
        let (data, response) = try await PrivateLANHTTP.load(request, limit: 8 * Wire.maxBody)
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
    var invalidateLAN: () -> Void
    @Published var mode: ConnectionMode = .automatic
    var connected: Bool { (mode != .bluetooth && lan.connected) || (mode != .lan && bluetooth.connected) }
    var usesLAN: Bool { mode != .bluetooth && lan.connected }
    var label: String { usesLAN ? "Wi-Fi" : bluetooth.connected && mode != .lan ? "Bluetooth" : "Reconnecting…" }
    var catalogSHA256: String? { usesLAN ? lan.catalogSHA256 : bluetooth.catalogSHA256 }
    init(lan: any GalaxyRequestTransport, bluetooth: any GalaxyRequestTransport, invalidateLAN: @escaping () -> Void) {
        self.lan = lan; self.bluetooth = bluetooth; self.invalidateLAN = invalidateLAN
    }
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        try Task.checkCancellation()
        if usesLAN {
            do { return try await lan.request(path: path, method: method, headers: headers, body: body) }
            catch {
                try Task.checkCancellation()
                guard error is URLError else { throw error }
                invalidateLAN()
                // Retry reads only; never replay a setting change.
                if !["GET", "HEAD"].contains(method) {
                    throw BridgeError.message("Wi-Fi disconnected. This change may have saved; reload the setting to confirm before trying again.")
                }
                guard mode == .automatic, bluetooth.connected else { throw error }
            }
        }
        guard mode != .lan, bluetooth.connected else { throw BridgeError.message("Your comma is disconnected. Open Connections to reconnect.") }
        return try await bluetooth.request(path: path, method: method, headers: headers, body: body)
    }
}
