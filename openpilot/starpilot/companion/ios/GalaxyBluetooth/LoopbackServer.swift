import Foundation
import CryptoKit
import Network
import Combine
import UniformTypeIdentifiers

@MainActor
final class LoopbackServer: ObservableObject {
    @Published var url: URL?
    @Published var error = ""
    private(set) var lifecycleEvents: [String] = []
    private(set) var listenerState = "stopped"
    private var availabilityTask: Task<Bool, Never>?
    private(set) var recentRequests: [String] = []
    var diagnosticSummary: String {
        let mobile = webRoot.map { FileManager.default.fileExists(atPath: $0.appendingPathComponent("index.html").path) } ?? false
        let script = webRoot.map { FileManager.default.fileExists(atPath: $0.appendingPathComponent("js/app.js").path) } ?? false
        return "Local server ready: \(url != nil)\nLocal listener state: \(listenerState)\nRecent local server events:\n\(lifecycleEvents.joined(separator: "\n"))\nAsset source: \(webRoot == nil ? "not downloaded" : "saved from comma")\nMobile HTML exists: \(mobile)\nGalaxy script exists: \(script)\nLocal server error present: \(!error.isEmpty)"
    }
    static func reportPath(_ target: String) -> String {
        let path = String(target.prefix(512)).split(separator: "?", maxSplits: 1).first.map(String.init) ?? ""
        if ["/assets/", "/js/", "/css/", "/vendor/"].contains(where: { path.hasPrefix($0) }) { return String(path.prefix(200)) }
        if path.hasPrefix("/api/") { return "/api/" + (path.split(separator: "/").dropFirst().first.map(String.init) ?? "") + "/…" }
        return path == "/" ? "/" : "[other path]"
    }
    let localSecret = UUID().uuidString + UUID().uuidString
    private var listener: NWListener?
    private var connections: [UUID: LocalConnection] = [:]
    private var webRoot: URL?
    private let transport: any GalaxyRequestTransport
    private let probe: (URL) async -> Bool
    private var catalog: Data?
    private var catalogSHA256: String?

    init(transport: any GalaxyRequestTransport, webRoot: URL? = nil,
         probe: @escaping (URL) async -> Bool = { url in
             var request = URLRequest(url: url.appendingPathComponent("_native/health"))
             request.timeoutInterval = 2
             guard let (data, response) = try? await BoundedHTTP.load(request, limit: 256) else { return false }
             return response.statusCode == 200 && data == Data("galaxy-loopback-ready".utf8)
         }) {
        self.transport = transport
        self.probe = probe
        self.webRoot = webRoot

    }

    func useWebRoot(_ root: URL) {
        webRoot = root

    }

    private func record(_ event: String) {
        lifecycleEvents.append("\(ISO8601DateFormatter().string(from: Date())) \(event)")
        if lifecycleEvents.count > 20 { lifecycleEvents.removeFirst(lifecycleEvents.count - 20) }
    }

    // Probe real HTTP service after suspension; an old URL is not proof of readiness.
    func ensureAvailable() async -> Bool {
        if let availabilityTask { return await availabilityTask.value }
        let task = Task { @MainActor in
            self.start()
            await self.waitUntilReady()
            if let url = self.url, await self.probe(url) {
                self.record("Local HTTP health check passed")
                return true
            }
            self.record("Local HTTP health check failed; restarting listener")
            self.stop()
            self.start()
            await self.waitUntilReady()
            guard let url = self.url, await self.probe(url) else {
                self.stop()
                self.error = "Galaxy couldn’t reconnect. Try again."
                self.record("Local HTTP recovery failed")
                return false
            }
            self.record("Local HTTP recovery succeeded")
            return true
        }
        availabilityTask = task
        defer { availabilityTask = nil }
        return await task.value
    }

    private func waitUntilReady() async {
        for _ in 0..<40 {
            if url != nil || listener == nil { return }
            try? await Task.sleep(nanoseconds: 50_000_000)
        }
    }

    func start() {
        guard listener == nil else { return }
        error = ""
        listenerState = "starting"
        record("Starting local listener")
        do {
            let parameters = NWParameters.tcp
            parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
            let listener = try NWListener(using: parameters)
            self.listener = listener
            listener.stateUpdateHandler = { [weak self, weak listener] state in
                Task { @MainActor in
                    guard let self, let listener, self.listener === listener else { return }
                    switch state {
                    case .ready:
                        self.listenerState = "ready"
                        self.error = ""
                        if let port = listener.port { self.url = URL(string: "http://127.0.0.1:\(port.rawValue)/") }
                        self.record("Local listener ready")
                    case .failed(let failure):
                        self.stop()
                        self.listenerState = "failed"
                        self.error = failure.localizedDescription
                        self.record("Local listener failed: \(failure)")
                    case .waiting:
                        self.url = nil
                        self.listenerState = "waiting"
                        self.record("Local listener waiting")
                    case .cancelled:
                        self.stop()
                    default: break
                    }
                }
            }
            listener.newConnectionHandler = { [weak self, weak listener] connection in
                Task { @MainActor in
                    guard let self, let listener, self.listener === listener else { connection.cancel(); return }
                    self.accept(connection)
                }
            }
            listener.start(queue: .main)
        } catch { listenerState = "failed"; self.error = error.localizedDescription; record("Could not create local listener") }
    }

    func stop() {
        let oldListener = listener
        listener = nil
        oldListener?.cancel()
        listenerState = "stopped"
        record("Local listener stopped")
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
        let start = Date()
        let response = await respond(request)
        recentRequests.append("\(ISO8601DateFormatter().string(from: Date())) \(request.method) \(Self.reportPath(request.target)) → \(response.status), \(response.body.count) bytes, \(String(format: "%.2f", Date().timeIntervalSince(start)))s")
        if recentRequests.count > 60 { recentRequests.removeFirst(recentRequests.count - 60) }
        return response
    }

    static let nativeSearchScript = #"""
    // Native Bluetooth search adapter v1. The verified upstream assets stay unchanged on disk.
    if (window.__galaxyNative) {
      const reportSearch = (phase, count) => {
        try { window.webkit?.messageHandlers?.galaxyDiagnostics?.postMessage({ kind: 'search', phase, count }) } catch (_) {}
      }
      SettingsSearchIndex.prototype.collect = async function(generation, controller) {
        const seen = new Set(INITIAL_PAGES)
        const queue = [...INITIAL_PAGES]
        let failed = 0, reportedResults = false
        reportSearch('started', 0)
        const current = () => this.generation === generation && !controller.signal.aborted
        for (let cursor = 0; cursor < queue.length && current(); cursor++) {
          const page = queue[cursor]
          const timed = new AbortController()
          let timer, abort
          try {
            const expired = new Promise((_, reject) => {
              abort = () => { timed.abort(); reject(new DOMException('Search stopped', 'AbortError')) }
              controller.signal.addEventListener('abort', abort, { once: true })
              timer = setTimeout(abort, 20000)
            })
            const read = (async () => {
              const response = await this.fetcher(`./api/settings/pages/${encodeURIComponent(page)}`,
                { credentials: 'same-origin', cache: 'no-store', signal: timed.signal })
              if (response.status === 401) { this.stop(); this.unauthorized(); return null }
              if (!response.ok) throw new Error('Settings unavailable')
              const data = await response.json()
              if (data?.page !== page || !Array.isArray(data.rows) || typeof data.title !== 'string') throw new Error('Invalid settings page')
              return data
            })()
            const data = await Promise.race([read, expired])
            if (!current() || !data) return
            const section = PAGE_SECTIONS.get(page.split('/')[0]) || 'Toggles'
            for (const row of data.rows) {
              if (typeof row?.label !== 'string' || !row.label) continue
              if (typeof row.page === 'string' && row.page && !seen.has(row.page) && seen.size < 64) {
                seen.add(row.page); queue.push(row.page)
              }
              if (row.page || isPipCropRow(row)) continue
              this.entries.push({ page, label: row.label, title: data.title, section,
                search: searchable(row, data.title, section) })
            }
          } catch {
            if (!current()) return
            failed++
          } finally {
            clearTimeout(timer)
            if (abort) controller.signal.removeEventListener('abort', abort)
          }
          // Publish each page immediately; one slow page must not hide earlier matches.
          if (current() && this.entries.length && !reportedResults) {
            reportedResults = true; reportSearch('results', this.entries.length)
          }
          if (current()) this.publish({ status: 'loading', entries: [...this.entries], failed })
        }
        if (!current()) return
        this.status = failed ? 'partial' : 'ready'
        reportSearch(this.status, this.entries.length)
        this.publish({ status: this.status, entries: [...this.entries], failed })
      }
      const closeSearch = ToggleSearch.methods.close
      ToggleSearch.methods.close = function() { this.index.stop(); closeSearch.call(this) }
      const searchKey = ToggleSearch.methods.onKey
      ToggleSearch.methods.onKey = function(event) {
        if (event.key === 'Escape') this.index.stop()
        searchKey.call(this, event)
      }
      const chooseSearchHit = ToggleSearch.methods.choose
      ToggleSearch.methods.choose = function(hit) { this.index.stop(); chooseSearchHit.call(this, hit) }
      ToggleSearch.template = ToggleSearch.template.replace("state.status === 'partial' && !state.entries.length", "state.status === 'partial' && !results.length")
    }
    """#

    private func respond(_ request: LocalRequest) async -> LocalResponse {
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
        if path == "/_native/health", request.method == "GET" {
            return LocalResponse(status: 200, headers: ["content-type": "text/plain"], body: Data("galaxy-loopback-ready".utf8))
        }
        if path.hasPrefix("/_gateway/") { return .error(404, "Choose your connection in the native app.") }
        let dynamic = path.hasPrefix("/api/") || path == "/data/runtime.json"
        if dynamic {
            guard request.headers["x-galaxy-local"] == localSecret else { return .error(403, "Missing app request key.") }
            guard transport.connected else { return .error(503, "Your comma is disconnected. Open Connections to reconnect.") }
            do {
                let response = try await transport.request(path: request.target, method: request.method,
                                                          headers: request.headers, body: request.body)
                return LocalResponse(status: response.status, headers: response.headers, body: response.bodyData)
            } catch { return .error(502, error.localizedDescription) }
        }
        guard ["GET", "HEAD"].contains(request.method) else { return .error(405, "Method is not supported for Galaxy files.") }
        guard let webRoot else { return .error(503, "Galaxy screens aren’t downloaded yet. Connect to comma over Wi-Fi once.") }
        let assetPath = path == "/" ? "index.html" : String(path.dropFirst())
        let file = webRoot.appendingPathComponent(assetPath).standardizedFileURL
        guard file.path.hasPrefix(webRoot.standardizedFileURL.path + "/"), var data = try? Data(contentsOf: file) else {
            return .error(404, "Galaxy asset was not found.")
        }
        if assetPath == "js/toggle-search.js", let source = String(data: data, encoding: .utf8),
           source.contains("export class SettingsSearchIndex"), source.contains("export const ToggleSearch") {
            data.append(Data(("\n" + Self.nativeSearchScript).utf8))
            record("Native incremental toggle search enabled")
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

    private var packageTimeout = false

    private func consume(_ chunk: Data?, ended: Bool, failure: NWError?) {
        guard !closed else { return }
        data.append(chunk ?? Data())
        guard failure == nil, data.count <= LocalRequest.maxPackageBody + 16_388 else { close(); return }
        if !packageTimeout, let end = data.range(of: Data("\r\n\r\n".utf8)),
           let header = String(data: data[..<end.lowerBound], encoding: .utf8),
           let first = header.components(separatedBy: "\r\n").first {
            let parts = first.split(separator: " ")
            if parts.count == 3, LocalRequest.isPackageUpload(method: String(parts[0]), target: String(parts[1])) {
                packageTimeout = true
                headerTimeout?.cancel()
                headerTimeout = Task { @MainActor [weak self] in
                    try? await Task.sleep(nanoseconds: 120_000_000_000)
                    if !Task.isCancelled { self?.close() }
                }
            }
        }
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
