# Validation — October 8, 2026

| Check | Result |
|---|---|
| iPhone compilation and linking | Passed, using Apple Swift 6.4 in Swift 5 mode, iPhoneOS 27.0 SDK, ARM64 target, iOS 17 minimum |
| iPhone compiler warnings | None in the final compile/link run |
| Xcode project and Info.plist parsing | Passed |
| Python protocol/proxy/GATT session tests | 23 tests passed, including notification framing/MTU, eight-packet credits, wrong/stale ACK rejection, final verification, subscription/authentication gating, multiple client isolation, timeout/cancellation without repeating a mutation, and existing codec/proxy/replay checks |
| Installer with unavailable ensurepip | Passed with uv and pip 26.2.1 using real isolated environments and local dependency wheels; recovered a partial environment and preserved the pairing key on reinstall |
| Swift → Python and Python → Swift | Passed for encrypted/compact messages, notification stream tags/fragments, unrelated-frame filtering, truncated-frame rejection and tagged window ACKs using production wire code |
| Swift HTTP parser | Passed for partial bodies and malformed/duplicate/chunked header rejection |
| Production loopback HTTP server on macOS | Passed for serving Galaxy HTML/modules, API forwarding to a fixture, request key enforcement, origin rejection and disconnected responses |
| Production Swift settings read cache | Passed for concurrent read sharing, uncached current values, write/reconnect/TTL invalidation, header variants, failed responses, cancellation and reads spanning writes |
| Bundled Galaxy references | All 352 checked module/HTML/CSS asset references resolve |
| Frontend settings startup | Passed using bundled Vue reactivity: one initial load when developer mode is enabled, one refresh on an actual change, and a single-key language read |
| Signed Xcode build for a physical iPhone | Optimized app passed in the user's Xcode with automatic signing and their personal team; latest report shows Build succeeded, no issues |
| Xcode simulator build | Passed in the user's Xcode; a simulator launch was not used for Bluetooth testing |
| Physical iPhone launch and Bluetooth exchange | App launched after turning off debugger attachment; user reported connection and dashboard loading with iPhone Wi-Fi/cellular disabled |
| Toggles over Bluetooth | Compact read-stream responses delivered on hardware but took approximately 61 seconds of transfer time. Notification-stream timing and a real setting change remain pending |
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

The user's subsequent hardware trace confirmed the compact read stream was active with 512-byte packets. Catalog: 24,773 bytes / 49 packets / 28.07 seconds. Current parameters: 19,157 bytes / 38 packets / 24.74 seconds. Defaults: 6,074 bytes / 12 packets / 8.19 seconds. Combined preparation time was 0.38 seconds; transfer time was 61.00 seconds. This established sequential read latency as the remaining bottleneck despite the smaller payloads. Those three frames would use 102 notification packets and 14 window ACKs at the same payload size, avoiding the 99 sequential read requests. Notification throughput is not yet measured on the hardware; both app and bridge need the new version, with the phone's remembered Bluetooth service cache refreshed.
