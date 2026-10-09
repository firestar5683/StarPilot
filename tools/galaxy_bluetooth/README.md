# Nate’s Galaxy companion

iPhone app for StarPilot’s Galaxy interface. Uses local Wi-Fi first, with encrypted Bluetooth fallback. Screens are saved for offline use and updated from `Nate/galaxy-bluetooth`.

## Setup

- [Install on comma](INSTALL-ON-COMMA.md)
- [iPhone setup and testing](ios/TESTER-GUIDE.md)
- [Live View and CarPlay pilot](ios/CARPLAY-PILOT.md)
- [Android prototype](android/README.md)

Open `ios/GalaxyBluetooth.xcodeproj`, select your signing team and iPhone, then Run. On comma 4, open **Settings → Pair phone**. Scan its code in the app and select the comma. The bridge needs a one-time installation.

## Connection

Galaxy screens → native transport → LAN HTTP or encrypted BLE → Galaxy on comma.

Local settings work without internet. Downloads and online maps still need internet on the device handling them. Remote cellular access and automatic hotspot activation are not implemented.

The Bluetooth bridge uses a shared key, session challenges and request counters. **Forget paired phones** replaces the key for all phones. Setting changes are never replayed automatically. LAN uses Galaxy’s existing HTTP endpoint; its device-ID check prevents accidental mixups but does not add TLS or authentication.

## Status

iOS build, bridge tests and routing/update checks pass. Bluetooth startup after reboot was verified on the pilot comma. Camera scanning, revoke/re-pair and network switching still need hardware checks. Android has no physical-device test yet.

See [validation](VALIDATION.md) and [upstream notices](UPSTREAM-NOTICES.md).
