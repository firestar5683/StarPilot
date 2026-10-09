import Foundation
import CryptoKit
import Network
import Combine
import UniformTypeIdentifiers

@MainActor
final class LoopbackServer: ObservableObject {
    @Published var url: URL?
    @Published var error = ""
    let localSecret = UUID().uuidString + UUID().uuidString
    private var listener: NWListener?
    private var connections: [UUID: LocalConnection] = [:]
    private var webRoot: URL
    private let transport: any GalaxyRequestTransport
    private var catalog: Data?
    private var catalogSHA256: String?

    init(transport: any GalaxyRequestTransport, webRoot: URL? = nil) {
        self.transport = transport
        let root = webRoot ?? Bundle.main.resourceURL!.appendingPathComponent("Web", isDirectory: true)
        self.webRoot = root
        self.catalog = try? Data(contentsOf: root.appendingPathComponent("assets/components/tools/device_settings_layout.json"))
        self.catalogSHA256 = catalog.map { SHA256.hash(data: $0).map { String(format: "%02x", $0) }.joined() }
    }

    func useWebRoot(_ root: URL) {
        webRoot = root
        catalog = try? Data(contentsOf: root.appendingPathComponent("assets/components/tools/device_settings_layout.json"))
        catalogSHA256 = catalog.map { SHA256.hash(data: $0).map { String(format: "%02x", $0) }.joined() }
    }

    func start() {
        guard listener == nil else { return }
        do {
            let parameters = NWParameters.tcp
            parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
            let listener = try NWListener(using: parameters)
            self.listener = listener
            listener.stateUpdateHandler = { [weak self, weak listener] state in
                Task { @MainActor in
                    guard let self else { return }
                    switch state {
                    case .ready:
                        if let port = listener?.port { self.url = URL(string: "http://127.0.0.1:\(port.rawValue)/") }
                    case .failed(let failure): self.error = failure.localizedDescription
                    default: break
                    }
                }
            }
            listener.newConnectionHandler = { [weak self] connection in
                Task { @MainActor in self?.accept(connection) }
            }
            listener.start(queue: .main)
        } catch { self.error = error.localizedDescription }
    }

    func stop() {
        listener?.cancel()
        listener = nil
        url = nil
        for client in Array(connections.values) { client.close() }
    }

    private func accept(_ connection: NWConnection) {
        guard connections.count < 64 else { connection.cancel(); return }
        let id = UUID()
        let client = LocalConnection(connection: connection, handle: { [weak self] request in
            guard let self else { return .error(503, "App is shutting down.") }
            return await self.handle(request)
        }, onClose: { [weak self] in self?.connections.removeValue(forKey: id) })
        connections[id] = client
        client.start()
    }

    private func handle(_ request: LocalRequest) async -> LocalResponse {
        guard let base = url, let port = base.port, request.headers["host"] == "127.0.0.1:\(port)" else {
            return .error(403, "Invalid local host.")
        }
        if let origin = request.headers["origin"], origin != "http://127.0.0.1:\(port)" {
            return .error(403, "Cross-origin requests are blocked.")
        }
        guard request.target.hasPrefix("/"), !request.target.hasPrefix("//"),
              let components = URLComponents(string: request.target), components.scheme == nil, components.host == nil,
              let path = components.percentEncodedPath.removingPercentEncoding,
              !path.contains("\\"), !path.contains("%"), !path.contains("//"),
              !path.split(separator: "/").contains(where: { $0 == ".." || $0 == "." }) else {
            return .error(400, "Invalid local path.")
        }
        if path.hasPrefix("/_gateway/") { return .error(404, "Choose your connection in the native app.") }
        let dynamic = path.hasPrefix("/api/") || path == "/assets/components/tools/device_settings_layout.json"
        if dynamic {
            guard request.headers["x-galaxy-local"] == localSecret else { return .error(403, "Missing app request key.") }
            guard transport.connected else { return .error(503, "Your comma is disconnected. Open Connections to reconnect.") }
            // Verify the device's catalog during the authenticated BLE handshake.
            // Unknown or different versions continue through the ordinary proxy.
            if request.method == "GET", request.body.isEmpty,
               request.target == "/assets/components/tools/device_settings_layout.json?v=settings-tier-1",
               request.headers["range"] == nil, let catalog, let catalogSHA256,
               transport.catalogSHA256 == catalogSHA256 {
                return LocalResponse(status: 200, headers: ["content-type": "application/json"], body: catalog)
            }
            do {
                let response = try await transport.request(path: request.target, method: request.method,
                                                          headers: request.headers, body: request.body)
                return LocalResponse(status: response.status, headers: response.headers, body: response.bodyData)
            } catch { return .error(502, error.localizedDescription) }
        }
        guard ["GET", "HEAD"].contains(request.method) else { return .error(405, "Method is not supported for bundled files.") }
        let assetPath: String
        if path.hasPrefix("/assets/") { assetPath = String(path.dropFirst()) }
        else if ["/", "/mobile", "/mobile/"].contains(path) { assetPath = "assets/mobile/index.html" }
        else if path == "/manifest.json" { assetPath = "assets/manifest.json" }
        else { assetPath = "classic.html" }
        let file = webRoot.appendingPathComponent(assetPath).standardizedFileURL
        guard file.path.hasPrefix(webRoot.standardizedFileURL.path + "/"), let data = try? Data(contentsOf: file) else {
            return .error(404, "Bundled Galaxy asset was not found.")
        }
        let mime: String
        switch file.pathExtension {
        case "js", "mjs": mime = "text/javascript"
        case "css": mime = "text/css"
        case "html": mime = "text/html; charset=utf-8"
        case "json", "webmanifest": mime = "application/json"
        case "svg": mime = "image/svg+xml"
        default: mime = UTType(filenameExtension: file.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
        }
        return LocalResponse(status: 200, headers: ["content-type": mime], body: data)
    }
}

@MainActor
private final class LocalConnection {
    let connection: NWConnection
    let handle: @MainActor (LocalRequest) async -> LocalResponse
    let onClose: @MainActor () -> Void
    private var data = Data()
    private var requestTask: Task<Void, Never>?
    private var headerTimeout: Task<Void, Never>?
    private var closed = false

    init(connection: NWConnection, handle: @escaping @MainActor (LocalRequest) async -> LocalResponse,
         onClose: @escaping @MainActor () -> Void) {
        self.connection = connection
        self.handle = handle
        self.onClose = onClose
    }

    func start() {
        connection.stateUpdateHandler = { [weak self] state in
            Task { @MainActor in
                if case .failed = state { self?.close() }
                if case .cancelled = state { self?.close() }
            }
        }
        connection.start(queue: .main)
        headerTimeout = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: 10_000_000_000)
            if !Task.isCancelled { self?.close() }
        }
        receive()
    }

    fileprivate func close() {
        guard !closed else { return }
        closed = true
        headerTimeout?.cancel()
        requestTask?.cancel()
        connection.stateUpdateHandler = nil
        connection.cancel()
        onClose()
    }

    private func receive() {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self] chunk, _, ended, failure in
            Task { @MainActor in self?.consume(chunk, ended: ended, failure: failure) }
        }
    }

    private func consume(_ chunk: Data?, ended: Bool, failure: NWError?) {
        guard !closed else { return }
        data.append(chunk ?? Data())
        guard failure == nil, data.count <= Wire.maxBody + 16_388 else { close(); return }
        do {
            guard let request = try LocalRequest.parse(data) else {
                if ended { close() } else { receive() }
                return
            }
            headerTimeout?.cancel()
            data = Data()
            // Detect browser aborts while a Bluetooth request is queued.
            connection.receive(minimumIncompleteLength: 1, maximumLength: 1) { [weak self] bytes, _, done, failure in
                Task { @MainActor in
                    if done || failure != nil || bytes?.isEmpty == false { self?.close() }
                }
            }
            requestTask = Task { @MainActor in
                let response = await handle(request)
                guard !Task.isCancelled, !closed else { close(); return }
                send(response, headOnly: request.method == "HEAD")
            }
        } catch { send(.error(400, error.localizedDescription), headOnly: false) }
    }

    private func send(_ response: LocalResponse, headOnly: Bool) {
        headerTimeout?.cancel()
        connection.send(content: response.encoded(headOnly: headOnly), completion: .contentProcessed { [weak self] _ in
            Task { @MainActor in self?.close() }
        })
    }
}
