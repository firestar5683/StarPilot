# Galaxy Bluetooth for iPhone

A working prototype source project that bundles StarPilot's existing Galaxy mobile interface inside a native SwiftUI / WKWebView iPhone app. Requests to the comma travel through Core Bluetooth instead of Wi-Fi or a Galaxy relay.

**Hardware testing is in progress.** A signed app has launched on a physical iPhone, connected to the comma 4 bridge, and loaded the dashboard with the phone's Wi-Fi and cellular disabled. The bridge excludes unused learning history that initially exceeded its body limit. Subsequent device logs confirmed compact responses but approximately 61 seconds spent transferring Toggles data through sequential Bluetooth reads. The app and bridge now support push notifications in bounded batches; that transfer mode and a real setting change still need hardware verification. Automated protocol/proxy tests pass. Run the included BlueZ probe before testing on another device.

## What is included

- An Xcode project for iPhone, iOS 17 or later, with no third-party iOS packages.
- Galaxy mobile and classic assets, pinned to StarPilot commit `2a12dbd0ad94b46f8a7b6099d32d7216b7676f79`.
- A separate Python service on the comma using its existing BlueZ daemon. It does not patch StarPilot, the driving code or the Bluetooth kernel.
- AES-256-GCM encryption using a private pairing key, per-session challenges and monotonic request counters, direction-bound authentication, and compressed messages.
- MTU-aware fragmentation, compact HTTP response compression, and negotiated push notifications with eight fragments per acknowledgement window. Older apps/bridges retain the read-stream or original per-fragment acknowledgement mode. No automatic retry of a settings change.
- Shared concurrent settings reads and a five-minute in-memory catalog/defaults cache, cleared after any write or new connection. Current toggle values are never cached.
- Read-only hardware diagnostics, automated bridge tests and Swift/Python interoperability checks.

## How the connection works

```text
Galaxy interface bundled on iPhone
  → HTTP server bound only to 127.0.0.1 on that same iPhone
  → native Core Bluetooth transport
  → encrypted BLE GATT messages
  → comma-side bridge
  → Galaxy at 127.0.0.1:8082 on the comma
```

The two HTTP hops stay inside their respective devices. The iPhone-to-comma connection uses Bluetooth. Galaxy's screens and server-side settings behavior are retained. The phone's loopback server rejects external origins and requires a private app header for API requests.

For faster loading, the authenticated health response advertises `notificationStream`. After verifying it, the phone subscribes to a separate notification characteristic (`bd490005-6dc1-4de7-a7d0-6cdb441f7650`) before opening Galaxy. The bridge compresses raw HTTP bytes before base64 encoding and pushes up to eight MTU-bounded fragments without requiring reads. Each window has a tagged ACK that releases the next batch. The final ACK follows successful decryption and verification of the entire response. Shared notifications carry a session/request tag; publishers are serialized, and the phone ignores frames for other clients or requests. Subscriptions alone cannot execute an API request: the request still must pass authentication, session and replay checks.

Bursts stop after eight packets without an ACK. Missing credit times out after 15 seconds without retransmitting fragments or the HTTP request. The phone also detects a 15-second stall after a transfer begins and retains its overall request timeout. An interrupted transfer requires reconnection and checking the setting's outcome. Small requests use the larger negotiated write payload too. The existing RX/TX/INFO characteristics retain their UUIDs and flags, and older bridges/apps use read-stream or per-fragment ACK mode.

When updating from the earlier read-only prototype, disconnect the app and forget the comma/Galaxy entry in iPhone **Settings > Bluetooth** once so iOS discovers the new characteristic. The native app handles service invalidation and reports a stale service cache explicitly rather than silently staying in the slow read mode. Keep the app's pairing key; forgetting the system Bluetooth entry does not replace it.

Startup reads only `LanguageSetting`, rather than the entire parameter snapshot. Toggles reuses its catalog/defaults for up to five minutes; opening it again still fetches current values. Any non-GET request invalidates cached metadata and concurrent reads before and after forwarding the write. The cache does not persist across connections.

Map search, online map tiles, model downloads and software updates can still require internet access on the phone or comma, as they do in Galaxy today. Bluetooth replaces the connection between the phone and comma; it does not make those external services available offline.

Local toggles and settings are intended to work with Wi-Fi and cellular disabled on either or both devices. Bluetooth must stay enabled, Galaxy must be running on the comma, and the bridge must remain running. The bridge omits `LiveTorqueParameters` from `/api/params/all`: it is internal learning history, is not in the Toggles catalog, and is unused by the bundled UI. Every other parameter is retained. This changes the transferred snapshot only; it does not delete or modify the parameter on the comma.

## Run on iPhone

1. Open `ios/GalaxyBluetooth.xcodeproj` in Xcode 16 or later.
2. Select the **GalaxyBluetooth** target, then **Signing & Capabilities**. Choose your personal development team and change the bundle identifier if necessary.
3. Connect your iPhone to your Mac, enable Developer Mode if iOS requests it, select the iPhone as the run destination and click Run.
4. Allow Bluetooth access when prompted.
5. Start the bridge on your comma using the steps below, paste its 64-character pairing key into the app and select **Scan for comma**.
6. Select **Galaxy** in the scan results. The app verifies the key before opening Galaxy and saves the key in the iPhone Keychain.

If Xcode fails while copying iPhone debugging symbols, try **Product > Scheme > Edit Scheme > Run > Info** and turn off **Debug executable**, then run again. This launches without attaching the debugger; it does not fix an unavailable USB connection.

An iOS Simulator can help inspect the shell but cannot validate this Bluetooth connection. A development-signed install from Xcode is required; this project is not an App Store submission or a signed IPA.

## Run the bridge on comma

Use the SSH address you already use for your own comma. In the examples, replace `YOUR_COMMA` with that address. Installation needs internet access once to install Python packages. Ordinary local settings requests can then operate over Bluetooth without a shared Wi-Fi network.

Copy the bridge folder from this project:

```sh
ssh YOUR_COMMA 'mkdir -p /data/galaxy-ble/app'
scp -r bridge YOUR_COMMA:/data/galaxy-ble/app/
ssh YOUR_COMMA
sh /data/galaxy-ble/app/bridge/install.sh
```

The installer creates a separate virtual environment in `/data/galaxy-ble/venv` and a private key file at `/data/galaxy-ble/pairing.json`. It preserves an existing key. It does not overwrite the openpilot environment or start a background service.

On AGNOS, the installer also checks StarPilot's managed Python at `/usr/local/venv`. It creates the bridge environment without `ensurepip`, then uses an existing `uv` or pip 22.3+ to install only into that environment. This handles devices where the system's `python3-venv` package is absent. A normal Python installation with `ensurepip` is also supported. If none of those installers is available, it stops with a diagnostic instead of modifying system packages.

Turn Bluetooth on in StarPilot, then check the prerequisites:

```sh
/data/galaxy-ble/venv/bin/python /data/galaxy-ble/app/bridge/probe.py
```

Look for `powered`, `gattServer`, and `advertising` to be true, and for Galaxy to answer with HTTP status 200. The controller must support LE peripheral advertising, with an available advertising instance. The reported BlueZ interfaces are prerequisites; successful advertising and an actual connection are the final confirmation.

Start the bridge in the foreground for the first test:

```sh
/data/galaxy-ble/venv/bin/python /data/galaxy-ble/app/bridge/server.py
```

Keep this SSH session open. The bridge should report that it is ready. Press Ctrl-C to stop it. If BlueZ denies access, inspect the device's existing D-Bus permissions; running the same foreground command with `sudo` can distinguish a permissions issue from unsupported hardware. The optional service below assumes the device has a `comma` user with access to BlueZ.

If you need to view the pairing key again, run this locally on the comma and do not share its output:

```sh
/data/galaxy-ble/venv/bin/python -c 'import json; print(json.load(open("/data/galaxy-ble/pairing.json"))["key"])'
```

## First hardware checks

Test while parked. Open Home and verify device status, then open Settings and read the existing values. Change an ordinary display preference and confirm it on the comma. Disconnect and reconnect, and confirm the key is remembered.

For an offline test, disable Wi-Fi and cellular on the iPhone while leaving Bluetooth enabled. Open Toggles, read a display preference, change it, and verify the result on the comma. Before disabling the comma's network too, use the startup service below so the bridge survives the SSH session ending. Repeat with both devices offline, then reconnect and read back the preference. Settings load errors remain visible with a **Retry loading toggles** button; retrying this button only reads the settings.

If a mutating request times out after transmission, its outcome can be unknown. Reconnect and read the setting before retrying. Cancelling a queued request removes it; cancelling a partially sent request closes the connection; an already-sent request may finish on the comma while the app drains its response.

## Optional startup service

After a successful foreground hardware test, install the included service:

```sh
sudo cp /data/galaxy-ble/app/bridge/galaxy-ble.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now galaxy-ble
sudo journalctl -u galaxy-ble -f
```

The service runs as `comma` and waits for Bluetooth to be available. Bluetooth must remain enabled in StarPilot. Automatic startup has not yet been tested on the user's device.

## Stop and remove

For a foreground test, press Ctrl-C. If you enabled the startup service:

```sh
sudo systemctl disable --now galaxy-ble
sudo rm /etc/systemd/system/galaxy-ble.service
sudo systemctl daemon-reload
```

You can then remove `/data/galaxy-ble` and delete the iPhone app. Flashing back to stock is not required to remove this bridge. Only remove that directory after confirming it contains this project's files and pairing key.

## Current limits

- The app runs in the foreground. It does not claim background reconnect or persistent background execution.
- HTTP API requests are serialized over Bluetooth. Settings and status are the first hardware validation target; high-frequency plots may be slow.
- Request/response bodies are limited to 1 MiB, with a 2 MiB bounded encrypted/decoded envelope. The all-parameters snapshot may be read up to 8 MiB before its unused internal learning history is omitted; the resulting BLE response must still fit the 1 MiB limit. Large exports/uploads return an error.
- Finite event-stream responses, such as a route list, are buffered until complete. Continuous EventSource streams are not implemented; the mobile log view already uses snapshots.
- Video downloads and video/multipart live streams are rejected explicitly. Direct media element loads, continuous camera viewing, direct downloads and browser push notifications are not supported in this prototype.
- A few image elements request dynamic files without the app's API header. These may not render; JSON settings and normal `fetch` / XHR requests are the supported path.
- Galaxy's UI bundle is pinned. A different StarPilot version may need a matching bundle; `UPSTREAM.json` records the revision and the native-shell adaptations.
- One saved pairing key is supported at a time. The bridge creates independent sessions for up to four clients. Encryption protects payloads; radio jamming or unauthenticated connection flooding can still disrupt availability.

## Development checks

Install `bridge/requirements.txt` in a development Python environment, then run:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/check_bundle.py
python3 scripts/check_interop.py
node tests/settings_load.mjs
```

The tests check actual local HTTP forwarding, binary response preservation, finite SSE, body limits, redirect/path restrictions, encryption tamper rejection, GATT packet/ACK behavior, and replay/session rejection. The interoperability check compiles the production Swift wire/parser files on macOS and exchanges messages with Python in both directions. It requires Xcode's command line tools.

To compare response sizes without modifying settings, run `python3 scripts/benchmark_settings.py --galaxy-url http://YOUR_COMMA:8082`. Add `--packet-size 512` only to model a connection whose negotiated MTU permits that payload. The default comparison uses 180-byte packets. This prints byte/operation counts for legacy reads, read streams and windowed notifications, never parameter values or keys, and does not measure actual Bluetooth loading time. Both the bridge and iPhone app must be updated for the full optimization.

To regenerate the included Xcode project after adding Swift files, run `python3 scripts/create_xcode_project.py`.

To check installer recovery from a missing `ensurepip`, download the wheels in `bridge/requirements.txt` to a local directory, then run `python3 scripts/check_installer.py --wheelhouse /path/to/wheels`. Add `--uv-bin /path/to/uv` to exercise the uv path too. These checks run the real installer in temporary directories and confirm dependency isolation and pairing-key preservation. The installer accepts `GALAXY_BLE_PYTHON` and `GALAXY_BLE_DATA_DIR` overrides for development checks.

## Attribution

This project is an independent prototype and is not an official comma.ai or StarPilot app. Bundled Galaxy assets come from [StarPilot](https://github.com/firestar5683/StarPilot) under its upstream licensing; retain `UPSTREAM-LICENSE` and `UPSTREAM-NOTICES.md` when redistributing. The upstream licenses and notices remain applicable to bundled vendor assets.
