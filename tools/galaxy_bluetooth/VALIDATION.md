# Validation — October 8, 2026

| Check | Result |
|---|---|
| iPhone compilation and linking | Passed, using Apple Swift 6.4 in Swift 5 mode, iPhoneOS 27.0 SDK, ARM64 target, iOS 17 minimum |
| iPhone compiler warnings | None in the final compile/link run |
| Xcode project and Info.plist parsing | Passed |
| Python protocol/proxy/GATT session tests | 11 tests passed |
| Installer with unavailable ensurepip | Passed with uv and pip 26.2.1 using real isolated environments and local dependency wheels; recovered a partial environment and preserved the pairing key on reinstall |
| Swift → Python and Python → Swift | Passed for encrypted, compressed messages using production wire code |
| Swift HTTP parser | Passed for partial bodies and malformed/duplicate/chunked header rejection |
| Production loopback HTTP server on macOS | Passed for serving Galaxy HTML/modules, API forwarding to a fixture, request key enforcement, origin rejection and disconnected responses |
| Bundled Galaxy references | All 352 checked module/HTML/CSS asset references resolve |
| Physical iPhone installation and Bluetooth exchange | Pending |
| comma 4 BlueZ advertising/peripheral capability and coexistence | Pending |
| Signed Xcode build / simulator launch | Not performed successfully in the restricted session; Xcode's build process could not complete while simulator services were inaccessible |
| Video / continuous stream support | Not implemented in this prototype |

The unsigned executable used for compiler validation is a temporary development output, not an installable application included with this source project. Open the supplied Xcode project and sign it using your development team to install it on your iPhone.

The automated tests use a local fixture API and a fixed public test key. They do not contact or change settings on a real comma device. Passing them confirms the bridge implementation and cross-language protocol agree; hardware timing, BlueZ behavior and installed StarPilot API compatibility still need the included device test steps.

The first comma 4 installation attempt reported that `ensurepip` was unavailable. The revised installer creates its environment without pip, recognizes `/usr/local/venv`, and uses existing uv or pip to install into the bridge environment. The user confirmed `/usr/comma/shims/uv` and pip 26.2.1 are available on the device. A successful device installation with the revised script is still pending.
