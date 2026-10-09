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
