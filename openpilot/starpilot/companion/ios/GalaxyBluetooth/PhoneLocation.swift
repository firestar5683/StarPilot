import CoreLocation
import Foundation

/// Sends this iPhone's GPS to comma about once a second over the current Galaxy connection.
/// Comma uses it for navigation only when its own GPS and the car's GPS have no fix.
@MainActor
final class PhoneLocation: NSObject, ObservableObject, @preconcurrency CLLocationManagerDelegate {
    static let path = "/api/companion/location"
    nonisolated static let maxAgeMs = 2000.0

    @Published private(set) var sharing = UserDefaults.standard.bool(forKey: "galaxy.phoneGps")
    @Published private(set) var status = ""
    var onSharingChanged: ((Bool) -> Void)?
    private let transport: () -> (any GalaxyRequestTransport)?
    private let manager: CLLocationManager?
    private var sending = false
    private var lastSent = Date.distantPast

    init(transport: @escaping () -> (any GalaxyRequestTransport)?, manager: CLLocationManager? = CLLocationManager()) {
        self.transport = transport
        self.manager = manager
        super.init()
        guard let manager else { return }
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBestForNavigation
        manager.distanceFilter = kCLDistanceFilterNone
        #if os(iOS)
        manager.activityType = .automotiveNavigation
        manager.pausesLocationUpdatesAutomatically = false
        manager.showsBackgroundLocationIndicator = true
        #endif
        if sharing { begin() }
    }

    func setSharing(_ value: Bool) {
        guard value != sharing else { return }
        sharing = value
        UserDefaults.standard.set(value, forKey: "galaxy.phoneGps")
        if value { begin() } else { manager?.stopUpdatingLocation(); status = "" }
        onSharingChanged?(value)
    }

    private func begin() {
        guard let manager else { return }
        switch manager.authorizationStatus {
        case .notDetermined: status = "Allow location to share GPS."; manager.requestWhenInUseAuthorization()
        case .denied, .restricted: status = "Location is off for this app. Turn it on in iPhone Settings."
        default:
            #if os(iOS)
            manager.allowsBackgroundLocationUpdates = true
            #endif
            status = "Waiting for GPS"
            manager.startUpdatingLocation()
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        if sharing { begin() }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        Task { await deliver(location) }
    }

    /// Sends one fix unless another is in flight or one went out under a second ago.
    func deliver(_ location: CLLocation, now: Date = Date()) async {
        guard sharing, !sending, now.timeIntervalSince(lastSent) >= 0.9 else { return }
        guard let body = Self.payload(location, now: now) else { status = "Waiting for GPS"; return }
        guard let transport = transport(), transport.connected else { status = "Waiting for comma"; return }
        sending = true
        defer { sending = false }
        do {
            let response = try await transport.request(path: Self.path, method: "POST", headers: ["Content-Type": "application/json"], body: body)
            lastSent = now
            status = response.status == 200 ? "Sharing GPS with comma"
                : response.status == 405 ? "This comma doesn't take phone GPS yet." : "Comma didn't accept the location."
        } catch { status = "Waiting for comma" }
    }

    /// iOS marks an unknown value with a negative number; those are left out.
    nonisolated static func payload(_ location: CLLocation, now: Date) -> Data? {
        let age = now.timeIntervalSince(location.timestamp) * 1000
        guard age >= 0, age <= maxAgeMs, location.horizontalAccuracy > 0, CLLocationCoordinate2DIsValid(location.coordinate) else { return nil }
        var value: [String: Any] = ["latitude": location.coordinate.latitude, "longitude": location.coordinate.longitude,
                                    "horizontalAccuracy": location.horizontalAccuracy, "ageMs": Int(age.rounded()),
                                    "timestamp": Int64(location.timestamp.timeIntervalSince1970 * 1000)]
        if location.verticalAccuracy > 0 { value["altitude"] = location.altitude; value["verticalAccuracy"] = location.verticalAccuracy }
        if location.speed >= 0 { value["speed"] = location.speed }
        if location.speedAccuracy >= 0 { value["speedAccuracy"] = location.speedAccuracy }
        if location.course >= 0, location.courseAccuracy >= 0 { value["bearing"] = location.course; value["bearingAccuracy"] = location.courseAccuracy }
        return try? JSONSerialization.data(withJSONObject: value)
    }
}
