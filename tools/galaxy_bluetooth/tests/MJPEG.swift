import Foundation

enum BridgeError: Error { case message(String) }

@main
struct MJPEGTests {
    static func main() throws {
        let pictures = [Data([0xff, 0xd8, 1, 2, 0xff, 0xd9]), Data([0xff, 0xd8, 3, 0xff, 0xd9])]
        let body = pictures.reduce(into: Data()) { bytes, image in
            bytes.append(Data("--galaxy-frame\r\nContent-Type: image/jpeg\r\nContent-Length: \(image.count)\r\n\r\n".utf8))
            bytes.append(image); bytes.append(Data("\r\n".utf8))
        }
        for chunked in [false, true] {
            var wire = Data("HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=galaxy-frame\r\n\(chunked ? "Transfer-Encoding: chunked\r\n" : "")\r\n".utf8)
            if chunked {
                for offset in stride(from: 0, to: body.count, by: 7) {
                    let part = body.subdata(in: offset..<min(offset + 7, body.count))
                    wire.append(Data("\(String(part.count, radix: 16))\r\n".utf8)); wire.append(part); wire.append(Data("\r\n".utf8))
                }
            } else { wire.append(body) }
            for fragment in [1, 2, 3, 17, 65_536] {
                var parser = MJPEGParser(); var decoded: [Data] = []
                for offset in stride(from: 0, to: wire.count, by: fragment) {
                    do { decoded += try parser.append(wire.subdata(in: offset..<min(offset + fragment, wire.count))) }
                    catch { print("Failed chunked=\(chunked) fragment=\(fragment) offset=\(offset)"); throw error }
                }
                precondition(decoded == pictures, "Fragmented frames changed")
            }
        }
        for invalid in ["HTTP/1.1 403 Forbidden\r\n\r\n", "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"] {
            var parser = MJPEGParser()
            do { _ = try parser.append(Data(invalid.utf8)); fatalError("Invalid response accepted") } catch {}
        }
        var parser = MJPEGParser()
        let oversized = Data("HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=galaxy-frame\r\n\r\n--galaxy-frame\r\nContent-Type: image/jpeg\r\nContent-Length: 9999999\r\n\r\n".utf8)
        do { _ = try parser.append(oversized); fatalError("Oversized frame accepted") } catch {}
        print("MJPEG fragmentation, chunking, authentication errors and size bounds passed")
    }
}
