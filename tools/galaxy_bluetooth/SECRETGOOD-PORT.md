# SecretGoodStarPilot port

Draft import from natehuby76/StarPilotBT at aec7d4c912bbd2f8fc281043b55a9b7f0798d4ec.

This copies the existing comma-side Bluetooth package for review. It does not enable or start it. The iPhone app is maintained separately in natehuby76/ios-clone; the old bundled iOS project is deliberately excluded.

## Integration still required

SecretGoodStarPilot uses an openpilot/ source directory and the new openpilot.starpilot.galaxy service. The Dom service and UI hooks cannot be copied directly.

- Adapt package placement, bootstrap paths and process registration to this layout.
- Integrate phone pairing and the diagnostics switch with starpilot/ui/bluetooth_compact.py and bluetooth_large.py, respecting the shared BluetoothOwner lifecycle.
- Adapt the HTTP proxy to the new authenticated Galaxy server and settings schema. Do not bypass its authorization, session or parked-only mutation checks.
- Connect read-only telemetry and optional screen capture to the current UI lifecycle.
- Update settings-catalog validation and app asset compatibility.
- Run bridge/protocol tests, then validate pairing, reconnects, settings reads and diagnostics on comma with the current iPhone app.

The original four-commit update and eight-file diff are preserved in PR #220. This draft is a starting point for the rewritten branch, not a ready-to-install build. No driving, model or vehicle-control files are changed.
