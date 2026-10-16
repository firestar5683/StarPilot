# Test branch validation

Base: official SecretGoodStarPilot `01fd37fa7509174d71a626f66fa5567b4603b00e`.

- 35 bridge/startup/pairing/proxy tests passed, including encrypted framing, ACK windows, reconnect credentials, per-handshake cookie isolation, authenticated mutation headers, explicit session expiry refresh, no network-error mutation replay, Wi-Fi-only restrictions, and respecting Bluetooth power preference.
- 19 real Galaxy HTTP tests passed (16 existing authentication tests plus three new bridge/settings tests). New tests read the actual hub/runtime APIs and preview/confirm a disposable display preference. Cross-session intents are rejected.
- 27 existing Bluetooth UI/status regression tests passed. The large-screen pure test fixture supplies the new phone-row dependency; other radio/device tests retain their original checks.
- All new Python files compile; shell installer scripts pass syntax checks.
- Upstream's AArch64/QCOM artifact validation passed. No shipped native binaries, models, control code or Galaxy web assets differ from the official base. No new device compile is required for these Python/UI additions.
- The iPhone migration's bundled Galaxy files exactly match this comma base (excluding intentional runtime/sample data exclusions).

Host: macOS, isolated Python 3.12 environment. The unchanged Params library and messaging module were compiled for host tests only and are not committed. The real HTTP/UI tests use a test adapter that refuses construction of the device-only QCOM solver; those tests do not execute vehicle calculations. Source and device artifacts remain unchanged.

Not yet checked: boot/install on a physical comma, real BlueZ advertising/ATT performance, QR display/camera scan on device, iPhone 0.2.0 TestFlight installation, and CarPlay. The staged SSH installer has been reviewed and syntax checked, not executed on the user's comma. Passing these tests means ready for personal parked hardware testing, not device validation.

Package wire implementation originates from `natehuby76/StarPilotBT:Nate/galaxybt-secretgood` at `11671f58c1e6c58b966bedcd04b1ef34823feb2d`; its protocol/crypto logic is retained and its proxy/startup/pairing integration is adapted to SecretGood. Persistent app keys remain in `/data/galaxy-ble`.
