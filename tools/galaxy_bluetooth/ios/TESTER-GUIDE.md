# iPhone: Wi-Fi first, Bluetooth fallback pilot

This is an experimental development build. Keep comma parked while testing.

## Install and connect

1. Keep the existing comma bridge running; no bridge update is required for these iPhone changes.
2. Open `GalaxyBluetooth.xcodeproj` in Xcode, select your iPhone, and Run.
3. Allow **Local Network** and Bluetooth access when prompted.
4. Leave **Automatic** selected and **Find comma’s address over Bluetooth** enabled. You may leave the IP blank for automatic discovery, or enter a private local IP manually.
5. Scan/select comma once in this new build to remember it for automatic reconnect. Your existing saved key is retained; enter it only if missing. Do not post or screenshot the key.
6. Confirm the header says **Galaxy · Wi-Fi** while phone and comma share a working local network.

The native UI contains Automatic, Wi-Fi only, and Bluetooth only choices.
Automatic reconnects a previously verified Bluetooth device and keeps it available
while using Wi-Fi, for a quicker fallback. Foreground monitoring checks LAN every
3 seconds with a 2-second health timeout per request. A bound-device check also reads its identifier. Network changes invalidate LAN and trigger a new discovery attempt. A request already sent to an unavailable
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

## Hotspot, shared Wi-Fi and comma SIM

| Comma connection | Phone-to-comma route | Internet for model downloads |
| --- | --- | --- |
| This iPhone's Personal Hotspot | Try the comma's hotspot client IP; BLE if unreachable | Comma uses the hotspot's cellular internet |
| Another phone's hotspot/shared Wi-Fi | LAN if both devices can reach each other; otherwise BLE | Comma uses that network if it provides internet |
| SIM only, no shared Wi-Fi | BLE while nearby | Comma uses its own SIM |
| Wi-Fi with no internet | LAN if reachable; otherwise BLE | Needs a separate working comma internet connection |

Personal Hotspot must be enabled by the user. The app does not turn it on or
configure comma's Wi-Fi credentials. Some hotspots/guest networks isolate
clients; a failed direct-IP probe simply keeps Bluetooth. Automatic address
learning retries at most every 20 seconds (or after a new BLE session/network
change) while LAN is unavailable; normal Galaxy screens remain on BLE.

Test each network type on real hardware, including moving comma from home Wi-Fi
to a phone hotspot. No bridge change is needed. **Bluetooth mode does not imply
comma is offline:** online operations still run on comma through its own hotspot,
Wi-Fi or SIM. Galaxy's device-status `online` flag means Galaxy responds; the app
does not present it as proof of internet access.

SIM does not expose comma directly to the phone. Connecting from outside BLE/local
network range still needs the remote firestar.link transport, which is not yet
implemented in this prototype.

## GitHub screens and offline startup

The app checks `natehuby76/StarPilotBT`, branch `Nate/galaxy-bluetooth`, when it
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

- Local HTTP uses the existing Galaxy port 8082 through an endpoint-scoped native
  TCP client. Any valid private IPv4 address can be configured or learned from
  the authenticated BLE peer; no IP-specific app rebuild, network-wide scanning,
  DNS endpoint or global/private-range ATS exception is needed. Internet requests
  retain normal HTTPS protections. The only HTTP ATS exception is app loopback.
- When a registered comma is paired, LAN health also checks its DongleId against
  the identifier read over authenticated BLE. A mismatch stays on Bluetooth.
  This avoids accidentally switching to a different comma; it does not add TLS
  or cryptographic server authentication to Galaxy's existing LAN HTTP. Use a
  trusted hotspot/local network. Unregistered devices require manual IP entry.
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
