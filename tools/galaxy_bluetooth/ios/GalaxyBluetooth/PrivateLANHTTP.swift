import Foundation
import Network

/// A local-only HTTP client for the one configured comma endpoint.
@MainActor
final class PrivateLANHTTP {
    private let connection: NWConnection
    private let limit: Int
    private let head: Bool
    private var continuation: CheckedContinuation<(Data, HTTPURLResponse), Error>?
    private var parser: LANHTTPParser
    private var timeout: Task<Void, Never>?
    private var finished = false
    private var sent = false
    private let request: URLRequest
    private init(_ request: URLRequest, limit: Int, host: String) {
        self.request = request; self.limit = limit; head = request.httpMethod == "HEAD"
        parser = LANHTTPParser(limit: limit, headOnly: request.httpMethod == "HEAD")
        connection = NWConnection(host: NWEndpoint.Host(host), port: 8082, using: .tcp)
    }
    static func load(_ request: URLRequest, limit: Int) async throws -> (Data, HTTPURLResponse) {
        guard let url = request.url, url.scheme == "http", url.port == 8082, let host = url.host,
              url.user == nil, url.password == nil, url.fragment == nil,
              (try? LANTransport.endpoint(host)) != nil else { throw BridgeError.message("Invalid local comma endpoint.") }
        let client = PrivateLANHTTP(request, limit: limit, host: host)
        return try await withTaskCancellationHandler(operation: {
            try Task.checkCancellation()
            return try await withCheckedThrowingContinuation { client.start($0) }
        }, onCancel: { Task { @MainActor in client.finish(.failure(CancellationError())) } })
    }
    private func start(_ callback: CheckedContinuation<(Data, HTTPURLResponse), Error>) {
        guard !finished else { callback.resume(throwing: CancellationError()); return }
        continuation = callback
        let timeoutInterval = request.timeoutInterval
        timeout = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(max(0.1, timeoutInterval) * 1_000_000_000))
            guard !Task.isCancelled else { return }
            self?.finish(.failure(URLError(.timedOut)))
        }
        connection.stateUpdateHandler = { [weak self] state in
            Task { @MainActor in
                guard let self, !self.finished else { return }
                switch state {
                case .ready: self.send()
                case .failed: self.finish(.failure(URLError(.cannotConnectToHost)))
                case .cancelled: self.finish(.failure(URLError(.networkConnectionLost)))
                default: break
                }
            }
        }
        connection.start(queue: .main)
    }
    private func send() {
        guard !sent else { return }
        sent = true
        guard let url = request.url, let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            finish(.failure(BridgeError.message("Invalid local URL."))); return
        }
        let target = components.percentEncodedPath + (components.percentEncodedQuery.map { "?" + $0 } ?? "")
        let body = request.httpBody ?? Data()
        var text = "\(request.httpMethod ?? "GET") \(target) HTTP/1.1\r\nHost: \(url.host!):8082\r\nConnection: close\r\nAccept-Encoding: identity\r\nContent-Length: \(body.count)\r\n"
        for (name, value) in request.allHTTPHeaderFields ?? [:] where ["content-type", "accept", "cookie", "range"].contains(name.lowercased()) {
            guard !value.contains("\r"), !value.contains("\n") else { finish(.failure(BridgeError.message("Invalid request header."))); return }
            text += "\(name): \(value)\r\n"
        }
        guard text.utf8.count <= 16_384 else { finish(.failure(BridgeError.message("HTTP headers are too large."))); return }
        text += "\r\n"
        connection.send(content: Data(text.utf8) + body, completion: .contentProcessed { [weak self] error in
            Task { @MainActor in
                guard let self, !self.finished else { return }
                if error != nil { self.finish(.failure(URLError(.networkConnectionLost))) }
                else { self.receive() }
            }
        })
    }
    private func receive() {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self] data, _, ended, error in
            Task { @MainActor in
                guard let self, !self.finished else { return }
                guard error == nil else { self.finish(.failure(URLError(.networkConnectionLost))); return }
                do {
                    if let result = try self.parser.consume(data ?? Data(), ended: ended),
                       let response = HTTPURLResponse(url: self.request.url!, statusCode: result.status, httpVersion: "HTTP/1.1", headerFields: result.headers) {
                        self.finish(.success((result.body, response)))
                    } else { self.receive() }
                } catch { self.finish(.failure(URLError(.cannotParseResponse))) }
            }
        }
    }
    private func finish(_ result: Result<(Data, HTTPURLResponse), Error>) {
        guard !finished else { return }
        finished = true; timeout?.cancel(); connection.stateUpdateHandler = nil; connection.cancel()
        let callback = continuation; continuation = nil
        callback?.resume(with: result)
    }
}

/// Incremental HTTP framing with strict bounds, including chunked responses.
struct LANHTTPParser {
    let limit: Int
    let headOnly: Bool
    private var buffer = Data()
    private var body = Data()
    private var status: Int?
    private var headers: [String: String] = [:]
    private var length: Int?
    private var chunked = false
    private var chunkLength: Int?
    private var lastChunk = false
    private var overhead = 0
    init(limit: Int, headOnly: Bool) { self.limit = limit; self.headOnly = headOnly }
    mutating func consume(_ data: Data, ended: Bool) throws -> LocalResponse? {
        buffer.append(data)
        guard buffer.count + body.count <= limit + 16_388 else { throw URLError(.dataLengthExceedsMaximum) }
        if status == nil {
            guard let range = buffer.range(of: Data("\r\n\r\n".utf8)) else {
                guard buffer.count <= 16_384, !ended else { throw URLError(.cannotParseResponse) }; return nil
            }
            guard range.lowerBound <= 16_384, let text = String(data: buffer[..<range.lowerBound], encoding: .isoLatin1) else { throw URLError(.cannotParseResponse) }
            let lines = text.components(separatedBy: "\r\n")
            let first = (lines.first ?? "").split(separator: " ")
            guard first.count >= 2, ["HTTP/1.0", "HTTP/1.1"].contains(String(first[0])), let code = Int(first[1]), (200...599).contains(code) else { throw URLError(.cannotParseResponse) }
            status = code
            for line in lines.dropFirst() {
                guard let colon = line.firstIndex(of: ":"), colon != line.startIndex else { throw URLError(.cannotParseResponse) }
                let name = line[..<colon].lowercased()
                guard headers[name] == nil else { throw URLError(.cannotParseResponse) }
                headers[name] = line[line.index(after: colon)...].trimmingCharacters(in: .whitespaces)
            }
            if let coding = headers["content-encoding"], coding.lowercased() != "identity" { throw URLError(.cannotDecodeContentData) }
            if let encoding = headers["transfer-encoding"] {
                guard encoding.lowercased() == "chunked", headers["content-length"] == nil else { throw URLError(.cannotParseResponse) }
                chunked = true
            }
            if let value = headers["content-length"] {
                guard let count = Int(value), (0...limit).contains(count) else { throw URLError(.dataLengthExceedsMaximum) }; length = count
            }
            buffer = Data(buffer[range.upperBound...])
            if headOnly || code == 204 || code == 304 { return result(Data()) }
        }
        if chunked {
            while true {
                if lastChunk {
                    // Accept an empty trailer or bounded well-formed trailers.
                    if buffer.starts(with: Data("\r\n".utf8)) {
                        guard buffer.count == 2 else { throw URLError(.cannotParseResponse) }; return result(body)
                    }
                    if let range = buffer.range(of: Data("\r\n\r\n".utf8)) {
                        guard range.upperBound == buffer.count, range.lowerBound <= 16_384,
                              let trailers = String(data: buffer[..<range.lowerBound], encoding: .isoLatin1),
                              trailers.components(separatedBy: "\r\n").allSatisfy({ $0.contains(":") }) else { throw URLError(.cannotParseResponse) }
                        return result(body)
                    }
                    guard buffer.count <= 16_384 else { throw URLError(.cannotParseResponse) }; break
                }
                if chunkLength == nil {
                    guard let range = buffer.range(of: Data("\r\n".utf8)) else {
                        guard buffer.count <= 1024 else { throw URLError(.cannotParseResponse) }; break
                    }
                    guard range.lowerBound <= 1024, let line = String(data: buffer[..<range.lowerBound], encoding: .ascii),
                          let token = line.split(separator: ";", omittingEmptySubsequences: false).first,
                          !token.isEmpty, token.allSatisfy(\.isHexDigit), let count = Int(token, radix: 16), count <= limit - body.count else { throw URLError(.cannotParseResponse) }
                    overhead += range.upperBound
                    guard overhead <= 65_536 else { throw URLError(.cannotParseResponse) }
                    buffer = Data(buffer[range.upperBound...]); chunkLength = count
                    if count == 0 { lastChunk = true; continue }
                }
                let count = chunkLength!
                guard buffer.count >= count + 2 else { break }
                guard buffer.subdata(in: count..<count + 2) == Data("\r\n".utf8) else { throw URLError(.cannotParseResponse) }
                body.append(buffer.prefix(count)); buffer = Data(buffer.dropFirst(count + 2)); chunkLength = nil
            }
        } else if let length {
            guard buffer.count <= length else { throw URLError(.cannotParseResponse) }
            if buffer.count == length { return result(buffer) }
        } else {
            guard buffer.count <= limit else { throw URLError(.dataLengthExceedsMaximum) }
            if ended { return result(buffer) }
        }
        if ended { throw URLError(.cannotParseResponse) }
        return nil
    }
    private func result(_ body: Data) -> LocalResponse { LocalResponse(status: status!, headers: headers, body: body) }
}
