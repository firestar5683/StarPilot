import Foundation
import Network

struct MJPEGParser {
    private var wire = Data()
    private var body = Data()
    private var headersRead = false
    private var chunked = false
    private var chunkRemaining: Int?
    private var chunkTrailer = false
    private var frameLength: Int?
    private let delimiter = Data("\r\n\r\n".utf8)
    mutating func append(_ data: Data) throws -> [Data] {
        wire.append(data)
        guard wire.count <= 750_000 else { throw URLError(.dataLengthExceedsMaximum) }
        if !headersRead {
            guard let end = wire.range(of: delimiter) else {
                guard wire.count <= 16_384 else { throw URLError(.cannotParseResponse) }; return []
            }
            let header = String(decoding: wire[..<end.lowerBound], as: UTF8.self).lowercased()
            guard let code = header.components(separatedBy: "\r\n").first?.split(separator: " ").dropFirst().first,
                  let status = Int(code) else { throw URLError(.cannotParseResponse) }
            if status != 200 {
                let message: String
                switch status {
                case 404: message = "Comma is missing the Live View endpoint. Update your fork and reboot comma while parked."
                case 403: message = "Comma rejected this phone’s pairing, or diagnostics are disabled in an older build. Check comma setup, then reconnect Bluetooth."
                case 503: message = "Live View is disabled on comma. Enable diagnostics before connecting."
                default: message = "Comma returned HTTP \(status) for Live View."
                }
                throw BridgeError.message(message)
            }
            guard header.contains("content-type: multipart/x-mixed-replace"), header.contains("boundary=galaxy-frame") else {
                throw BridgeError.message("Comma returned an unexpected Live View format (HTTP 200). Check that Galaxy is running the updated fork.")
            }
            chunked = header.contains("transfer-encoding: chunked")
            wire.removeSubrange(..<end.upperBound); headersRead = true
        }
        if !chunked { body.append(wire); wire.removeAll(keepingCapacity: true) }
        else {
            while !wire.isEmpty {
                if chunkTrailer {
                    guard wire.count >= 2 else { break }
                    guard wire.prefix(2) == Data("\r\n".utf8) else { throw URLError(.cannotParseResponse) }
                    wire.removeFirst(2); chunkTrailer = false; chunkRemaining = nil
                }
                if chunkRemaining == nil {
                    guard let line = wire.range(of: Data("\r\n".utf8)) else {
                        guard wire.count < 128 else { throw URLError(.cannotParseResponse) }; break
                    }
                    let text = String(decoding: wire[..<line.lowerBound], as: UTF8.self).split(separator: ";").first ?? ""
                    guard let size = Int(text, radix: 16), (0...750_000).contains(size) else { throw URLError(.cannotParseResponse) }
                    if size == 0 { throw URLError(.networkConnectionLost) }
                    chunkRemaining = size; wire.removeSubrange(..<line.upperBound)
                }
                guard let remaining = chunkRemaining else { break }
                let count = min(remaining, wire.count)
                body.append(wire.prefix(count)); wire.removeFirst(count)
                chunkRemaining = remaining - count
                if chunkRemaining == 0 { chunkTrailer = true }
                if count == 0 { break }
            }
        }
        guard body.count <= 750_000 else { throw URLError(.dataLengthExceedsMaximum) }
        var frames: [Data] = []
        while true {
            if frameLength == nil {
                guard let end = body.range(of: delimiter) else {
                    guard body.count <= 1024 else { throw URLError(.cannotParseResponse) }; break
                }
                let headers = String(decoding: body[..<end.lowerBound], as: UTF8.self).lowercased()
                guard headers.contains("--galaxy-frame"), headers.contains("content-type: image/jpeg"),
                      let lengthLine = headers.components(separatedBy: "\r\n").first(where: { $0.hasPrefix("content-length:") }),
                      let size = Int(lengthLine.dropFirst("content-length:".count).trimmingCharacters(in: .whitespacesAndNewlines)),
                      (1...650_000).contains(size) else { throw URLError(.cannotParseResponse) }
                frameLength = size; body.removeSubrange(..<end.upperBound)
            }
            guard let size = frameLength, body.count >= size else { break }
            frames.append(Data(body.prefix(size))); body.removeFirst(size); frameLength = nil
        }
        return frames
    }
}

final class LiveStream: @unchecked Sendable {
    private let connection: NWConnection
    private let queue = DispatchQueue(label: "StarPilot.LiveStream")
    private let request: Data
    private let frame: @Sendable (Data) -> Void
    private let failure: @Sendable (String) -> Void
    private var parser = MJPEGParser()
    private var stopped = false
    init(host: String, headers: [String: String], frame: @escaping @Sendable (Data) -> Void,
         failure: @escaping @Sendable (String) -> Void) {
        connection = NWConnection(host: NWEndpoint.Host(host), port: 8082, using: .tcp)
        let fields = headers.map { "\($0.key): \($0.value)\r\n" }.joined()
        request = Data("GET /api/companion/stream HTTP/1.1\r\nHost: \(host):8082\r\nConnection: close\r\n\(fields)\r\n".utf8)
        self.frame = frame; self.failure = failure
    }
    func start() {
        connection.stateUpdateHandler = { [weak self] state in
            guard let self, !self.stopped else { return }
            switch state {
            case .ready:
                self.connection.send(content: self.request, completion: .contentProcessed { [weak self] error in
                    guard let self else { return }
                    if let error { self.fail(error.localizedDescription) } else { self.receive() }
                })
            case .failed(let error): self.fail(error.localizedDescription)
            default: break
            }
        }
        connection.start(queue: queue)
    }
    func stop() { queue.async { [weak self] in self?.stopped = true; self?.connection.cancel() } }
    private func fail(_ message: String) {
        guard !stopped else { return }
        stopped = true; connection.cancel(); failure(message)
    }
    private func receive() {
        guard !stopped else { return }
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self] data, _, complete, error in
            guard let self, !self.stopped else { return }
            if let data {
                do {
                    // Prefer the newest complete frame when the network batches frames.
                    if let latest = try self.parser.append(data).last { self.frame(latest) }
                } catch { self.fail(error.localizedDescription); return }
            }
            if let error { self.fail(error.localizedDescription) }
            else if complete { self.fail("Reconnecting live stream…") }
            else { self.receive() }
        }
    }
}
