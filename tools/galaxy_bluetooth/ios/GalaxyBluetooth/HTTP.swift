import Foundation

struct LocalRequest {
    let method: String
    let target: String
    let headers: [String: String]
    let body: Data

    static func parse(_ data: Data) throws -> LocalRequest? {
        guard let separator = data.range(of: Data("\r\n\r\n".utf8)) else {
            if data.count > 16_384 { throw BridgeError.message("HTTP headers are too large.") }
            return nil
        }
        guard separator.lowerBound <= 16_384,
              let head = String(data: data[..<separator.lowerBound], encoding: .utf8) else {
            throw BridgeError.message("Invalid HTTP headers.")
        }
        let lines = head.components(separatedBy: "\r\n")
        let first = (lines.first ?? "").split(separator: " ")
        guard first.count == 3, ["HTTP/1.1", "HTTP/1.0"].contains(String(first[2])),
              ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"].contains(String(first[0])) else {
            throw BridgeError.message("Invalid HTTP request.")
        }
        var headers: [String: String] = [:]
        for line in lines.dropFirst() {
            guard let colon = line.firstIndex(of: ":"), colon != line.startIndex else { throw BridgeError.message("Malformed header.") }
            let name = line[..<colon].lowercased()
            guard headers[name] == nil else { throw BridgeError.message("Duplicate HTTP header.") }
            headers[name] = line[line.index(after: colon)...].trimmingCharacters(in: .whitespaces)
        }
        guard headers["transfer-encoding"] == nil else { throw BridgeError.message("Chunked uploads are not supported.") }
        let length: Int
        if let raw = headers["content-length"] {
            guard let parsed = Int(raw), parsed >= 0, parsed <= Wire.maxBody else { throw BridgeError.message("Invalid upload size.") }
            length = parsed
        } else { length = 0 }
        let available = data.count - separator.upperBound
        guard available >= length else { return nil }
        guard available == length else { throw BridgeError.message("HTTP pipelining is not supported.") }
        return LocalRequest(method: String(first[0]), target: String(first[1]), headers: headers,
                            body: data.subdata(in: separator.upperBound..<data.count))
    }
}

struct LocalResponse {
    let status: Int
    let headers: [String: String]
    let body: Data

    static func error(_ status: Int, _ message: String) -> LocalResponse {
        LocalResponse(status: status, headers: ["content-type": "application/json"],
                      body: (try? JSONSerialization.data(withJSONObject: ["error": message])) ?? Data())
    }

    func encoded(headOnly: Bool = false) -> Data {
        var text = "HTTP/1.1 \(status) \(HTTPURLResponse.localizedString(forStatusCode: status))\r\n"
        for (key, value) in headers where !["content-length", "connection", "cache-control"].contains(key.lowercased()) {
            guard !key.contains("\r"), !key.contains("\n"), !value.contains("\r"), !value.contains("\n") else { continue }
            text += "\(key): \(value)\r\n"
        }
        text += "Content-Length: \(body.count)\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n\r\n"
        return Data(text.utf8) + (headOnly ? Data() : body)
    }
}

