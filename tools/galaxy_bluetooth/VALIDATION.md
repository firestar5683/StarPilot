# Validation — October 8, 2026

| Check | Result |
|---|---|
| iPhone compilation and linking | Passed, using Apple Swift 6.4 in Swift 5 mode, iPhoneOS 27.0 SDK, ARM64 target, iOS 17 minimum |
| iPhone compiler warnings | None in the final compile/link run |
| Xcode project and Info.plist parsing | Passed |
| Python protocol/proxy/GATT session tests | 25 tests passed, including notification framing/MTU, eight-packet credits, wrong/stale ACK rejection, final verification, subscription/authentication gating, multiple client isolation, timeout/cancellation without repeating a mutation, catalog digest verification, settings-only field projection and safe fallback, and existing codec/proxy/replay checks |
| Installer with unavailable ensurepip | Passed with uv and pip 26.2.1 using real isolated environments and local dependency wheels; recovered a partial environment and preserved the pairing key on reinstall |
| Swift → Python and Python → Swift | Passed for encrypted/compact messages, notification stream tags/fragments, unrelated-frame filtering, truncated-frame rejection and tagged window ACKs using production wire code |
| Swift HTTP parser | Passed for partial bodies and malformed/duplicate/chunked header rejection |
| Production loopback HTTP server on macOS | Passed for serving Galaxy HTML/modules, API forwarding to a fixture, request key enforcement, origin rejection, digest-matched local catalog serving, mismatch fallback and disconnected responses |
| Production Swift settings read cache | Passed for concurrent read sharing, uncached current values, write/reconnect/TTL invalidation, header variants, failed responses, cancellation and reads spanning writes |
| Bundled Galaxy references | All 352 checked module/HTML/CSS asset references resolve |
| Frontend settings startup | Passed using bundled Vue reactivity: one initial load when developer mode is enabled, one refresh on an actual change, a single-key language read, the settings-only endpoint and no unused defaults request |
| Signed Xcode build for a physical iPhone | Optimized app passed in the user's Xcode with automatic signing and their personal team; latest report shows Build succeeded, no issues |
| Xcode simulator build | Passed in the user's Xcode; a simulator launch was not used for Bluetooth testing |
| Physical iPhone launch and Bluetooth exchange | App launched after turning off debugger attachment; user reported connection and dashboard loading with iPhone Wi-Fi/cellular disabled |
| Toggles over Bluetooth | Compact read-stream responses delivered on hardware but took approximately 61 seconds of transfer time. Notification streams delivered those three responses in 24.75 seconds. The smaller settings-only load and a real setting change remain pending |
| comma 4 BlueZ prerequisites | Passed in the user's device probe: powered hci0, central/peripheral roles, GATT server and advertising interfaces, five supported advertising instances and zero active before bridge startup; Galaxy HTTP status 200 |
| comma 4 GATT and advertisement registration | Passed; foreground bridge reported ready on hci0 and forwarding to localhost:8082 |
| Bluetooth coexistence with other accessories | Pending |
| Both devices without network connectivity | Pending; the bridge must run independently of the SSH session before this test |
| Video / continuous stream support | Not implemented in this prototype |

The unsigned executable used for compiler validation is a temporary development output, not an installable application included with this source project. Open the supplied Xcode project and sign it using your development team to install it on your iPhone.

The automated tests use a local fixture API and a fixed public test key. They do not contact or change settings on a real comma device. Passing them confirms the bridge implementation and cross-language protocol agree; hardware timing, BlueZ behavior and installed StarPilot API compatibility still need the included device test steps.

The first comma 4 installation attempt reported that `ensurepip` was unavailable. The revised installer creates its environment without pip, recognizes `/usr/local/venv`, and uses existing uv or pip to install into the bridge environment. The user confirmed `/usr/comma/shims/uv` and pip 26.2.1 are available on the device. The revised installation succeeded, and the user supplied successful probe and bridge startup output.

The bridge is installed separately from the user's existing StarPilot Dom installation. Current upstream Dom commit `934dadbcdbaaaac78dd6badd09a1ebadd298bae8` has the same Galaxy asset tree as the pinned bundle, and all 171 Galaxy route paths in the pinned server are present in its server source. This is a source compatibility check; matching paths do not establish complete behavior or device timing compatibility.

Read-only diagnosis of the user's Galaxy API found `/api/params/all` was approximately 1.55 MB, including roughly 1.46 MB of `LiveTorqueParameters`. This key is absent from the settings catalog and unused by the bundled frontend. Running the corrected production proxy against that API returned HTTP 200 with approximately 92 KB, preserved all 765 other values exactly, and produced an encrypted/compressed frame of approximately 27 KB. This check used the Mac's network connection for diagnosis; the iPhone's corrected Bluetooth transfer and a real toggle write remain pending. The settings catalog was approximately 190 KB and defaults approximately 20 KB, both below the existing BLE body limit.

The first performance update was measured using read-only HTTP responses from the same device, with a public test key and representative envelope metadata. Compact responses were approximately 19 KB for current parameters (previously 27 KB), 25 KB for the catalog (41 KB), and 6 KB for defaults (9 KB). At the same 180-byte packet size, the first Settings load needed approximately 287 response packets instead of 447; one final ACK per response reduced modeled response read/ACK operations from 894 to 290. Startup also avoids a separate full-parameter transfer just to read language. These counts excluded request writes, wait polling, radio latency and rendering.

The user's subsequent hardware trace confirmed the compact read stream was active with 512-byte packets. Catalog: 24,773 bytes / 49 packets / 28.07 seconds. Current parameters: 19,157 bytes / 38 packets / 24.74 seconds. Defaults: 6,074 bytes / 12 packets / 8.19 seconds. Combined preparation time was 0.38 seconds; transfer time was 61.00 seconds. This established sequential read latency as the remaining bottleneck despite the smaller payloads. Those three frames would use 102 notification packets and 14 window ACKs at the same payload size, avoiding the 99 sequential read requests. A subsequent hardware trace confirmed notification streaming: catalog 50 packets / 11.45 seconds, current parameters 39 packets / 9.79 seconds, defaults 13 packets / 3.51 seconds, totaling 24.75 seconds. Per-packet latency remains approximately 0.24 seconds.

The next optimization removes unused defaults from Toggles and serves its bundled catalog locally only when the authenticated bridge reports the exact SHA-256 of the device catalog. The additional catalog is copied unchanged from public StarPilot Dom commit `934dadbcdbaaaac78dd6badd09a1ebadd298bae8`, and its bytes match the device catalog. A different/missing digest falls back to Bluetooth rather than showing a mismatched layout.

Only Toggles requests `/api/params/all?galaxy_ble_settings=1`. For the audited catalog, the proxy omits five large dashboard/history fields that appear in neither the catalog nor bundled mobile scripts. It retains every other current parameter, including vehicle state, locks and profiles. The normal all-parameters endpoint keeps its prior behavior. On a different/unavailable catalog, the settings-only request also returns the ordinary full snapshot.

Read-only checks of the production proxy against the device returned HTTP 200, 760 retained values, a 25,326-byte settings body and an 8,232-byte compact encrypted frame, modeled as 17 notification packets at 512 bytes (previously 102 packets across catalog, values and defaults). That is approximately 83% fewer settings response packets. At the previous trace's per-packet timing, transfer alone would be roughly four seconds, but this is an estimate, not new measured Bluetooth latency. No device setting was changed. The signed iPhone build succeeded at 13:26 with no issues; updated bridge deployment and hardware timing remain pending.

## Android first-test build — October 8, 2026

Android source adds a Java native pairing/scanning screen, Android BLE client, Keystore-wrapped pairing storage, origin/main-frame-restricted native web messages and an async Fetch adapter. It reuses the existing comma protocol and bridge without changing their source, and copies the shared Galaxy assets only at build time. No tester pairing key or publisher private key is embedded.

- Gradle wrapper build `assembleDebug testDebugUnitTest lintDebug` passed using JDK 17, AGP 8.13.2, Gradle 8.13, compile/target SDK 36 and minimum SDK 26.
- Eight JVM unit tests passed for malformed envelopes/JSON/compression, expansion bounds, body limits, fragment ordering/trailing bytes, unrelated notification tags and request routing.
- Production Android Java ↔ Python interoperability passed for JSON and binary bodies, legacy and compact codecs, ATT payloads 20/180/244/512, tagged window ACKs, authenticated tamper/direction rejection and path validation. These use a public test key and contact no device.
- Production Android Fetch shim tests passed for fresh settings reads, UTF-8 setting writes, static/external routing, HEAD responses, upload bounds, abort without retry, and frame/origin gating.
- APK signature verification passed with APK signature scheme v2. Packaging checks found all 175 shared Galaxy files intact except the intended HTML shim insertion, plus the native shim and no pairing/private signing files. Official Gradle distribution and wrapper checksums, and Android SDK package checksums, were verified.
- Android lint passed with no errors and four dependency-version availability warnings (Gradle, AndroidX WebKit/Activity and test-only JSON). The tested dependencies are explicitly pinned.

No physical Android device was available, and this APK was not installed or launched in an emulator. Actual WebView rendering, runtime permission flows, scanning, MTU negotiation, notification timing, Keystore persistence on device, setting changes/read-back, reconnection, multiple phones and accessory coexistence remain pending. This is an installable debug test build for the first tester; a publisher-owned release signing key and physical results are needed before a wider continuing cohort. Android README and TESTER-GUIDE record those steps and current media/network/background limitations.

## iPhone LAN-first/GitHub update iteration

- Generic iOS Debug build succeeds with the current Xcode installation.
- Production Swift LAN priority/read fallback, explicit mode selection, no mutation replay, normal HTTP error handling, and private-address validation pass.
- Production GitHub asset tests cover full manifest/hash verification, offline restart, unchanged manifest fast checks, failed update rollback, keeping an active older interface through successive updates, traversal rejection and corrupt-cache rejection.
- Real HTTP fixtures verify redirects are not followed, declared/streamed response bounds and cancellation. Production Swift also passed a read-only LAN health probe and status request against comma's existing Galaxy server.
- Existing Swift/Python framing, loopback and metadata-cache checks pass.
- Asset manifest covers 175 files / 5,070,834 bytes. GitHub downloads use immutable commit URLs, at most four concurrent file requests, 32 MiB bundle and 4 MiB file limits.
- New iPhone UI, permissions and physical Wi-Fi-to-BLE switching are still unverified. No bridge/driving-code changes are required for this iteration. Android was not modified.
- The later network iteration removes the comma-IP ATS exception and uses an endpoint-scoped native local TCP client; only app loopback retains an HTTP ATS exception. No automatic cloud transport, foreground-to-background service guarantee, media streaming, App Store approval or internet sharing is claimed.

## Hotspot/shared-Wi-Fi/SIM network iteration

- Private IPv4 endpoints include common iPhone/Android hotspot and home-network addresses, learned from authenticated BLE when a registered identifier is available; manual entry remains supported. No fixed comma IP or broad ATS exception remains.
- Incremental native HTTP framing tests cover fragmented chunked and connection-close responses, upload/response bounds, duplicate/ambiguous lengths, truncation and malformed chunks. Existing routing/GitHub/HTTP client tests pass.
- Production native local TCP health/status requests passed against comma. A mismatched identifier was rejected, then the correct paired-device identifier was accepted; no private identifier is printed or embedded.
- Local-network path changes invalidate LAN and trigger address rediscovery. Automatic discovery itself and personal/other-phone hotspot switching still require physical iPhone testing. SIM-only nearby operation uses BLE; no remote cellular/cloud transport or hotspot-enabling API is claimed.
