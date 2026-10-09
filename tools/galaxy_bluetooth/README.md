# Galaxy Bluetooth for iPhone

A working prototype source project that bundles StarPilot's existing Galaxy mobile interface inside a native SwiftUI / WKWebView iPhone app. Requests to the comma travel through Core Bluetooth instead of Wi-Fi or a Galaxy relay.

**Hardware validation is pending.** The app compiles and links as an unsigned ARM64 iPhone executable, and automated protocol/proxy tests pass. This has not yet connected to a physical iPhone and comma 4. Bluetooth support in StarPilot does not by itself establish that its installed kernel, controller firmware and BlueZ configuration support this particular LE peripheral service; run the included probe before testing.

## What is included

- An Xcode project for iPhone, iOS 17 or later, with no third-party iOS packages.
- Galaxy mobile and classic assets, pinned to StarPilot commit `2a12dbd0ad94b46f8a7b6099d32d7216b7676f79`.
- A separate Python service on the comma using its existing BlueZ daemon. It does not patch StarPilot, the driving code or the Bluetooth kernel.
- AES-256-GCM encryption using a private pairing key, per-session challenges and monotonic request counters, direction-bound authentication, and compressed messages.
- Request/response fragmentation with explicit acknowledgements. No automatic retry of a settings change.
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

Map search, online map tiles, model downloads and software updates can still require internet access on the phone or comma, as they do in Galaxy today. Bluetooth replaces the connection between the phone and comma; it does not make those external services available offline.

## Run on iPhone

1. Open `ios/GalaxyBluetooth.xcodeproj` in Xcode 16 or later.
2. Select the **GalaxyBluetooth** target, then **Signing & Capabilities**. Choose your personal development team and change the bundle identifier if necessary.
3. Connect your iPhone to your Mac, enable Developer Mode if iOS requests it, select the iPhone as the run destination and click Run.
4. Allow Bluetooth access when prompted.
5. Start the bridge on your comma using the steps below, paste its 64-character pairing key into the app and select **Scan for comma**.
6. Select **Galaxy** in the scan results. The app verifies the key before opening Galaxy and saves the key in the iPhone Keychain.

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
- Request/response bodies are limited to 1 MiB, with a 2 MiB bounded encrypted/decoded envelope. Large exports/uploads return an error.
- Finite event-stream responses, such as a route list, are buffered until complete. Continuous EventSource streams are not implemented; the mobile log view already uses snapshots.
- Video downloads and video/multipart live streams are rejected explicitly. Direct media element loads, continuous camera viewing, direct downloads and browser push notifications are not supported in this prototype.
- A few image elements request dynamic files without the app's API header. These may not render; JSON settings and normal `fetch` / XHR requests are the supported path.
- Galaxy's UI bundle is pinned. A different StarPilot version may need a matching bundle; `UPSTREAM.json` records the revision and three small native-shell adaptations.
- One saved pairing key is supported at a time. The bridge creates independent sessions for up to four clients. Encryption protects payloads; radio jamming or unauthenticated connection flooding can still disrupt availability.

## Development checks

Install `bridge/requirements.txt` in a development Python environment, then run:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/check_bundle.py
python3 scripts/check_interop.py
```

The tests check actual local HTTP forwarding, binary response preservation, finite SSE, body limits, redirect/path restrictions, encryption tamper rejection, GATT packet/ACK behavior, and replay/session rejection. The interoperability check compiles the production Swift wire/parser files on macOS and exchanges messages with Python in both directions. It requires Xcode's command line tools.

To regenerate the included Xcode project after adding Swift files, run `python3 scripts/create_xcode_project.py`.

To check installer recovery from a missing `ensurepip`, download the wheels in `bridge/requirements.txt` to a local directory, then run `python3 scripts/check_installer.py --wheelhouse /path/to/wheels`. Add `--uv-bin /path/to/uv` to exercise the uv path too. These checks run the real installer in temporary directories and confirm dependency isolation and pairing-key preservation. The installer accepts `GALAXY_BLE_PYTHON` and `GALAXY_BLE_DATA_DIR` overrides for development checks.

## Attribution

This project is an independent prototype and is not an official comma.ai or StarPilot app. Bundled Galaxy assets come from [StarPilot](https://github.com/firestar5683/StarPilot) under its upstream licensing; retain `UPSTREAM-LICENSE` and `UPSTREAM-NOTICES.md` when redistributing. The upstream licenses and notices remain applicable to bundled vendor assets.
