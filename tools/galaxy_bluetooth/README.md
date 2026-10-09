# Nate’s Galaxy companion

iPhone app for StarPilot’s Galaxy interface. Uses local Wi-Fi first, with encrypted Bluetooth fallback. Screens are saved for offline use and updated from `Nate/galaxy-bluetooth`.

## Setup

- [Install on comma](INSTALL-ON-COMMA.md)
- [iPhone tester quick start](ios/QUICK-START.md)
- [Connection testing details](ios/TESTER-GUIDE.md)
- [Live View and CarPlay pilot](ios/CARPLAY-PILOT.md)
- [Android prototype](android/README.md)

Open `ios/GalaxyBluetooth.xcodeproj`, select your signing team and iPhone, then Run. On comma 4, open **Settings → Bluetooth → Pair phone**. Scan its code in the app and select the comma. The bridge needs a one-time installation.

## Connection

Galaxy screens → native transport → LAN HTTP or encrypted BLE → Galaxy on comma.

Local settings work without internet. Downloads and online maps still need internet on the device handling them. Remote cellular access and automatic hotspot activation are not implemented.

The Bluetooth bridge uses a shared key, session challenges and request counters. **Forget paired phones** replaces the key for all phones. Setting changes are never replayed automatically. LAN uses Galaxy’s existing HTTP endpoint; its device-ID check prevents accidental mixups but does not add TLS or authentication.

## Status

iOS build, bridge tests and routing/update checks pass. Bluetooth startup after reboot was verified on the pilot comma. Camera scanning, revoke/re-pair and network switching still need hardware checks. Android has no physical-device test yet.

See [validation](VALIDATION.md) and [upstream notices](UPSTREAM-NOTICES.md).

Comma 3X: phone pairing is available in Bluetooth settings. The bridge and capture hooks are shared; physical 3X testing is pending. `bridge/probe.py` reports Bluetooth and encoder compatibility without credentials. See `ios/QUICK-START.md`.

## Automatic bridge setup

The pilot's manager runs `bootstrap.py` on comma. First parked boot installs the
bridge in its own environment; later boots reuse it. Dependency changes are
installed while parked. Bluetooth settings show setup status and Retry setup.
`settings_backup.py` saves one private parameter/cache snapshot before existing
launch migrations. Setup never resets StarPilot parameters or pairing keys.
Do not share the backup; it contains credentials. See INSTALL-ON-COMMA.md.
