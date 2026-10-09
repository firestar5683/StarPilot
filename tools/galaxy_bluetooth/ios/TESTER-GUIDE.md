# iPhone: Wi-Fi first, Bluetooth fallback pilot

This is an experimental development build. Keep comma parked while testing.
Android remains on its earlier Bluetooth-only implementation.

## Install and connect

1. Keep the existing comma bridge running; no bridge update is required for these iPhone changes.
2. Open `GalaxyBluetooth.xcodeproj` in Xcode, select your iPhone, and Run.
3. Allow **Local Network** and Bluetooth access when prompted.
4. Leave **Automatic** selected, check comma's IP address, and choose **Connect**.
5. Scan/select comma once in this new build to remember it for automatic reconnect. Your existing saved key is retained; enter it only if missing. Do not post or screenshot the key.
6. Confirm the header says **Galaxy · Wi-Fi** while phone and comma share a working local network.

The native UI contains Automatic, Wi-Fi only, and Bluetooth only choices.
Automatic reconnects a previously verified Bluetooth device and keeps it available
while using Wi-Fi, for a quicker fallback. Foreground monitoring checks LAN every
3 seconds with a 2-second health timeout. A request already sent to an unavailable
LAN route can take up to 8 seconds to fail. Background operation is not guaranteed.

## Verify switching

1. Pair Bluetooth once while both connections are available.
2. Open Toggles and choose a reversible display preference.
3. Turn Wi-Fi off in **iPhone Settings**, leaving Bluetooth enabled.
4. The header should change to **Bluetooth** without restarting Galaxy or changing pages.
5. Change the display preference, leave/reopen Toggles, and confirm the value saved.
6. Restore Wi-Fi. Within the next successful LAN health check, the header should return to **Wi-Fi**.
7. Also try Bluetooth only, then Wi-Fi only, to verify the explicit choices.

A dropped setting-change response is never replayed automatically on another
connection. If the app reports that it may have saved, reopen the setting and
check its current value before trying again. GET/HEAD reads can fall back to BLE;
HTTP error statuses from Galaxy are returned normally rather than retried.

## GitHub screens and offline startup

The app checks `natehuby76/StarPilotBT`, branch `codex/galaxy-bluetooth`, when it
becomes active and when **Check Galaxy updates** is selected. It resolves one
immutable commit, downloads a compatible manifest and verifies every file's hash
and length. Unchanged files are copied from the saved/bundled version.

Screens are saved locally. Updates do not block connecting or replace files
under an open Galaxy page. A completed update is applied after Disconnect and
Connect, or at the next app launch. Failed, incompatible or partial downloads
keep the previous version. First launch always has the built-in offline copy.

Verify a GitHub update while online, then force-close/reopen with phone Wi-Fi and
cellular off, leaving Bluetooth on. Galaxy should still load over BLE. Internet
access on comma is separate: model downloads still require a connection there.

## Current limits

- Local HTTP uses the existing Galaxy port 8082. This pilot has an endpoint-scoped
  ATS exception for **192.168.10.85**. Another HTTP IP may need a matching entry
  in `NSAppTransportSecurity > NSExceptionDomains` and an app rebuild. The app
  accepts explicit private IPv4 addresses only; it does not scan the network.
- LAN uses Galaxy's existing HTTP access; it does not add encryption or a new
  authenticated LAN pairing mechanism. Use the trusted local network and comma
  address you configured. Device identity across LAN and BLE is not yet bound.
- No firestar.link/cloud fallback, background BLE service, hotspot automation,
  large video streaming/download route, or production app distribution yet.
- GitHub interface updates are a prototype feature. App Store/TestFlight review
  of downloaded JavaScript and native bridge access is not established.
- iPhone-to-comma LAN requests were verified from the Mac using production Swift;
  real iPhone permission, UI, pairing and route-switch testing is still required.

## Publishing a Galaxy interface update

Edit the bundled Galaxy assets and run:

```sh
python3 scripts/generate_galaxy_manifest.py
python3 scripts/generate_galaxy_manifest.py --check
```

Commit the updated files **and** `galaxy-native-manifest.json` together to the
configured release branch. This updates only the interface assets, not installed
Swift app code. A new native feature still needs a new signed app build. The
manifest's `nativeBridge` must change when a new interface requires an incompatible
native contract, so old apps keep their working saved version.
