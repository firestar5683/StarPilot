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

## LAN discovery follow-up — 1.1.4

Read-only inspection of the user's comma found Galaxy and the companion
supervisor running, but the isolated companion Python environment was missing;
no LAN advertiser was running. No device files, dependencies or settings were
changed. The supervisor now automatically installs and verifies the isolated
environment while parked with internet; no manual setup command is required.
It retries failures, reuses a valid environment offline, and cancels installation
when driving or phone internet sharing starts. No Bluetooth bonds, pairing keys,
other fork environments or systemd units are changed by setup.

The pinned Zeroconf library also reproduced `BadTypeInNameException` for the
original 16-byte `starpilot-galaxy` service name. A branch adapter now publishes
`_sp-galaxy._tcp.local.` with a separate address/hostname on each interface.
The preserved upstream snapshot remains unchanged. Android now searches home
Wi-Fi automatically when no usable address is saved, exposes a search button,
holds a bounded multicast lock, serializes resolution and reports failures.
Searches resume after returning from Wi-Fi settings or another app; a disconnected
screen reconnects on resume. Automatic-search failures appear inline, a single
result connects automatically, and canceling a multiple-result picker falls back
to saved Bluetooth in automatic mode while disconnected. Interrupted pickers are
dismissed before searching again, and healthy connections are preserved on resume.

Broken environment verification backs off for 60 seconds while driving. Setup
requires prebuilt wheels, preventing repeated source builds from exceeding the
180-second installation deadline. All four resolved dependencies passed wheel-only
resolution for Python 3.12 / aarch64-manylinux_2_39. PyPI publishes the matching
[Zeroconf 0.151.3](https://pypi.org/project/zeroconf/0.151.3/#files) and
[PyCryptodome 3.23.0](https://pypi.org/project/pycryptodome/3.23.0/#files) wheels.
The adapter converts registration exceptions to the upstream loop's retryable
error type and continues cleanup when a publisher's close operation fails.

- Signed APK 1.1.4, versionCode 6; release build, lint and signature verification passed.
- APK SHA-256: `a76141344a3491cf26fa8a752d47261b00bcc9d78d0bb4abffadab7bb742fd5f`.
- Signing certificate SHA-256 (unchanged):
  `d9e72cbb842e9530b4b686dec424cdeb8f2982109be6875fa73594c33332fc3a`.
- All 9 Android JVM tests passed, including new lifecycle recovery cases. These
  exercise the recovery controller, not an Android Activity on real hardware.
  Python regressions cover real
  Zeroconf name validation, per-interface records, registration cleanup, source
  provenance, companion HTTP and automatic environment setup. Setup coverage
  includes offline reuse, failure retries, partial installs, drive/data guards,
  timeouts, descendant termination and supervisor startup without a pairing key.
- All 31 targeted Python tests passed. A fresh temporary environment completed
  actual wheel-only automatic installation, pinned import verification, offline reuse and
  pairing preservation. Ruff, shell syntax and `git diff --check` passed.
- Read-only device checks confirmed writable setup storage, Python 3.12.3 and
  uv 0.12.19. System pip/ensurepip are absent, so the installer uses uv on AGNOS.
- Lint has 0 errors and 27 warnings. Physical Android discovery remains unverified;
  no phone was connected over ADB. Updated comma source, internet while parked
  for automatic first setup, and installation of APK 1.1.4 are required for the fix.
