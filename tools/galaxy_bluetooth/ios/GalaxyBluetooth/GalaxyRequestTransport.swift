import Foundation

@MainActor
protocol GalaxyRequestTransport: AnyObject {
    var connected: Bool { get }
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse
}
