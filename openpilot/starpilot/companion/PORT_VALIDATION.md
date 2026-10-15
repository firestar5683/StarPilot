# SecretGoodStarPilot companion port — 2026-10-15

Branch: `companion-secretgood`, based on upstream `7456d3a81d`.
The original `Stardust-APP` worktree is preserved. This port is uncommitted;
no push, device deployment, Bluetooth pairing, or flashing was performed.

## Integration

Only the companion worktree changes were transplanted; old Stardust history was
not merged. Upstream server routes (including replay, Toyota tools and settings
recovery), process entries, restart identity, map accounting and updater fixes
are retained. No Params registry or native build inputs were changed by the port.
Upstream native artifacts are retained; the existing pinned ARM64 tunnel is reused.

Bluetooth now obtains live restart metadata via `/api/companion/runtime`, an
alias of upstream `/data/runtime.json`. Bundled static metadata cannot detect a
device restart. The BLE fetch adapter maps only that runtime path to the API;
other bundled assets stay local. Replay requires Wi-Fi/LAN, enforced by both
the JavaScript transport and comma adapter before any replay operation starts.
The preserved upstream Bluetooth/iOS source snapshot remains unchanged.

## Android release

- Version 1.1.1, versionCode 3; signed `assembleRelease` and `lintRelease` passed.
- APK size: 1,474,830 bytes.
- APK SHA-256: `95428fc2fcc949588007382bbb878db15742d9fce3872abfb472eb7868f154f1`.
- Signing certificate SHA-256 (unchanged):
  `d9e72cbb842e9530b4b686dec424cdeb8f2982109be6875fa73594c33332fc3a`.
- `apksigner verify --print-certs` passed.
- All 109 bundled Galaxy application assets and `bluetooth-fetch.js` match source
  byte-for-byte (`.gitattributes` is repository metadata, not an APK asset).
- Existing compatibility/deprecation lint warnings remain; no lint errors.

## Validation

- 109 Node tests passed: all `galaxy/tests/*.mjs` plus the BLE fetch tests.
- 6 Android JVM tests passed: BLE wire interoperability and SOCKS TCP/UDP.
- 85 Python tests passed across companion protocol/HTTP/data guards, Bluetooth
  adapter, upstream HTTP server, replay HTTP and fast-update tests.
- 49 additional Python tests passed across hotspot, hotspot HTTP and navigation HTTP.
- 32 preserved upstream BLE bridge, pairing and LAN discovery tests passed using
  pinned `dbus-next==0.2.3` and `pycryptodome==3.23.0`.
- Ruff checks on changed Python integration files and companion adapters passed.
- `git diff --check` passed.

The Python tests used `run_host_tests.py` with the existing Python 3.12 environment.
This stubs native Params/IPC/solver imports and does not establish device ABI coverage.
Five extra `test_defaults_recovery_http.py` tests could not complete fixture setup:
they require native IPC and filesystem-backed Params (`get_param_path`) beyond
this runner. They are not included in the passing counts. A temporary IPC-stub
extension used to diagnose that limitation was removed; production code and
upstream tests were not weakened to make them pass.

Physical acceptance remains outstanding: Android 8–11 and 12+, comma 3X/4 BLE
pair/connect/reconnect, settings changes across disconnects, key rotation, LAN
discovery, concurrent cellular sharing, routing and DNS teardown/recovery,
phone sleep/background behavior, and navigation/sharing. See README.md.
The preserved iOS implementation was not rebuilt or validated against this API.
