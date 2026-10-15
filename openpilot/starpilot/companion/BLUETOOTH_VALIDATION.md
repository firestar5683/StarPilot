# Bluetooth integration validation — 2026-10-13

Branch: `Stardust-APP`. Source changes and artifacts remain uncommitted; no push
or physical-device deployment was performed.

- Imported all 250 upstream source files unchanged. Blob hashes are verified
  against `upstream/SOURCE.json`; `.gitattributes` preserves their line endings.
- Android `testDebugUnitTest`: 6 passing tests (BLE interoperability/security and
  existing SOCKS TCP/UDP behavior).
- Python suite: 63 passing tests covering the adapter, actual Galaxy HTTP
  authentication/session continuity, pairing local/session/origin/parked gates,
  existing companion/uplink guards, and upstream bridge/pairing/LAN discovery.
- JavaScript tests: Bluetooth POST bytes, cancellation and no replay; Galaxy
  companion, navigation, install prompt and shared destinations passed.
- Signed `assembleRelease` and `lintRelease` succeeded. Lint has warnings for
  compatibility APIs, local HTTP, WebView JavaScript, resources and localization;
  zero errors. Python Ruff and `git diff --check` passed.
- APK version 1.1.0, versionCode 2, 1,431,675 bytes. APK SHA-256:
  `a82359799b875f740946a94fda53af7c81f644e3edc461aabc1984ffe9d87679`.
  Signing certificate is unchanged and verified with `apksigner`. Bundled Galaxy
  and Bluetooth fetch assets were compared byte-for-byte to current source.

Reproduce BLE/adapter Python tests from the repository root:

```sh
SP_DISABLE_HOST_PYTEST_REDIRECT=1 uv run --python 3.12.12 --no-sync \
  --with pycryptodome==3.23.0 --with dbus-next==0.2.3 --extra testing \
  python openpilot/starpilot/companion/run_host_tests.py \
  openpilot/starpilot/companion/tests/test_bluetooth.py \
  openpilot/starpilot/galaxy/tests/test_companion.py \
  openpilot/starpilot/galaxy/tests/test_companion_http.py \
  openpilot/starpilot/galaxy/tests/test_companion_data_guards.py \
  openpilot/starpilot/companion/upstream/tools/galaxy_bluetooth/tests/test_bridge.py \
  openpilot/starpilot/companion/upstream/tools/galaxy_bluetooth/tests/test_pairing.py \
  openpilot/starpilot/companion/upstream/tools/galaxy_bluetooth/tests/test_lan_discovery.py
node --test openpilot/starpilot/companion/tests/test_bluetooth_fetch.mjs
```

The host runner stubs native Params/IPC/solver imports. These results do not prove
BlueZ permissions, real GATT timing, Wi-Fi routing on a Samsung phone, Android
background behavior, or comma 3X/4 hardware support. See README for the one-time
comma dependency install and physical acceptance checklist. The original iOS
project was preserved but not built or tested against this branch's API.

## StarPilot branding correction

Imported iPhone web logos and favicons now reuse the existing StarPilot Galaxy
icons, StarPilot logo and monochrome mark, including PNG, SVG, ICO, apple-touch
and Safari pinned-tab variants. The web asset manifest has updated sizes and
SHA-256 hashes. SOURCE.json retains original source hashes and separately lists
11 branding/metadata overrides. Implementation files still match upstream.
Android already used StarPilot artwork and does not package the imported iPhone
web directory; its signed APK and version remain unchanged.
