# Validation — October 8, 2026

| Check | Result |
|---|---|
| iPhone compilation and linking | Passed, using Apple Swift 6.4 in Swift 5 mode, iPhoneOS 27.0 SDK, ARM64 target, iOS 17 minimum |
| iPhone compiler warnings | None in the final compile/link run |
| Xcode project and Info.plist parsing | Passed |
| Python protocol/proxy/GATT session tests | 13 tests passed, including oversized learning-history filtering, preservation of toggle values, and upstream/output snapshot bounds |
| Installer with unavailable ensurepip | Passed with uv and pip 26.2.1 using real isolated environments and local dependency wheels; recovered a partial environment and preserved the pairing key on reinstall |
| Swift → Python and Python → Swift | Passed for encrypted, compressed messages using production wire code |
| Swift HTTP parser | Passed for partial bodies and malformed/duplicate/chunked header rejection |
| Production loopback HTTP server on macOS | Passed for serving Galaxy HTML/modules, API forwarding to a fixture, request key enforcement, origin rejection and disconnected responses |
| Bundled Galaxy references | All 352 checked module/HTML/CSS asset references resolve |
| Signed Xcode build for a physical iPhone | Passed in the user's Xcode with automatic signing and their personal team |
| Xcode simulator build | Passed in the user's Xcode; a simulator launch was not used for Bluetooth testing |
| Physical iPhone launch and Bluetooth exchange | App launched after turning off debugger attachment; user reported connection and dashboard loading with iPhone Wi-Fi/cellular disabled |
| Toggles over Bluetooth | First hardware test failed at the 1 MiB response limit. The corrected bridge/UI still need to be installed and retested on the device |
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
