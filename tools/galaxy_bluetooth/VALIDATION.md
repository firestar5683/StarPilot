# Validation

- iOS generic and development-signed builds passed.
- 28 Python bridge/pairing tests passed: framing, authentication, replay rejection, key rotation, old-key rejection and file permissions.
- Swift QR parsing passed with a Python-generated payload and malformed/version/size cases.
- LAN routing tests passed: priority, read fallback, no write replay, device identity and private IP validation.
- Local HTTP framing, redirect, size-bound and cancellation checks passed.
- Asset updates passed: file hashes, offline restart, rollback, traversal rejection and active-screen retention.
- Bluetooth startup after reboot reached bridge-ready on the pilot comma.
- Earlier Android build, signature and automated checks passed.

Pending: camera scan on iPhone, comma QR layout, revoke/re-pair, hotspot and LAN/BLE switching, setting write/read-back, Android hardware and release distribution.

Live / CarPlay pilot: 36 bridge/companion tests pass; iOS builds pass. GPU capture, capture overhead and physical CarPlay remain untested. MJPEG fragmentation/chunking/size-bound tests pass. CarPlay requires the approved entitlement; regular phone signing is unchanged.

Encoder integration with StarPilot’s pinned raylib 5.5.0.2: 40 distinct 960×480 JPEGs in 2.23 seconds on Mac, latest frame age 0.053 seconds. This does not measure comma GPU readback or end-to-end phone FPS.
