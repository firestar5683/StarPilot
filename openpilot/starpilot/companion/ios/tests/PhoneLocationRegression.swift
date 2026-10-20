import CoreLocation
import Foundation

struct BridgeResponse { let status: Int; let bodyData: Data }
enum Wire { static let maxBody = 1_048_576 }
enum BridgeError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let text) = self { return text }; return nil }
}

@MainActor final class RecordingComma: GalaxyRequestTransport {
    var connected = true
    var bodies: [[String: Any]] = []
    func request(path: String, method: String, headers: [String: String], body: Data) async throws -> BridgeResponse {
        precondition(path == PhoneLocation.path && method == "POST" && headers["Content-Type"] == "application/json")
        bodies.append(try JSONSerialization.jsonObject(with: body) as! [String: Any])
        return BridgeResponse(status: 200, bodyData: Data("{\"ok\":true}".utf8))
    }
}

func fix(at time: Date, course: Double = 90, courseAccuracy: Double = 10, speed: Double = 20, vertical: Double = 4) -> CLLocation {
    CLLocation(coordinate: CLLocationCoordinate2D(latitude: 40, longitude: -110), altitude: 1200, horizontalAccuracy: 5,
               verticalAccuracy: vertical, course: course, courseAccuracy: courseAccuracy, speed: speed, speedAccuracy: -1, timestamp: time)
}

@main
struct PhoneLocationRegression {
    @MainActor static func main() async {
        let now = Date()
        let known = try! JSONSerialization.jsonObject(with: PhoneLocation.payload(fix(at: now.addingTimeInterval(-0.3)), now: now)!) as! [String: Any]
        precondition(known["ageMs"] as? Int == 300 && known["bearing"] as? Double == 90 && known["speedAccuracy"] == nil)

        // iOS reports unknown values as negative numbers; they are left out.
        let unknown = try! JSONSerialization.jsonObject(with: PhoneLocation.payload(fix(at: now, courseAccuracy: -1, speed: -1, vertical: -1), now: now)!) as! [String: Any]
        precondition(unknown["bearing"] == nil && unknown["speed"] == nil && unknown["altitude"] == nil)
        precondition(PhoneLocation.payload(fix(at: now.addingTimeInterval(-3)), now: now) == nil)

        UserDefaults.standard.set(true, forKey: "galaxy.phoneGps")
        let comma = RecordingComma()
        let sharing = PhoneLocation(transport: { comma }, manager: nil)
        await sharing.deliver(fix(at: now), now: now)
        await sharing.deliver(fix(at: now.addingTimeInterval(0.5)), now: now.addingTimeInterval(0.5))
        precondition(comma.bodies.count == 1 && sharing.status == "Sharing GPS with comma")
        await sharing.deliver(fix(at: now.addingTimeInterval(1)), now: now.addingTimeInterval(1))
        precondition(comma.bodies.count == 2)

        comma.connected = false
        await sharing.deliver(fix(at: now.addingTimeInterval(2)), now: now.addingTimeInterval(2))
        precondition(comma.bodies.count == 2 && sharing.status == "Waiting for comma")
        sharing.setSharing(false)
        comma.connected = true
        await sharing.deliver(fix(at: now.addingTimeInterval(3)), now: now.addingTimeInterval(3))
        precondition(comma.bodies.count == 2)
        UserDefaults.standard.removeObject(forKey: "galaxy.phoneGps")
        print("phone location ok")
    }
}
