# Test results

The combined `secretgood-ios-integration` branch includes the iPhone app under `ios/` and the comma bridge here. It was synced with official SecretGood through `e62a518` when the combined PR was prepared.

Local checks passed:

- 38 bridge tests covering framing, encryption, notifications, pairing, startup, discovery and API forwarding.
- Swift tests for Wi-Fi cookies, session refresh, device identity, read caching, reconnects and localhost recovery.
- Galaxy asset checks and toggle search tests.
- An unsigned iOS Simulator build.

Earlier checks on the initial SecretGood integration also passed 19 Galaxy HTTP tests and 27 Bluetooth UI/status tests. Those are historical results, not a rerun against every later upstream commit.

Pairing, settings access and reconnects have had personal device testing. CarPlay, radio recovery and longer sessions across different phones and head units still need broader testing. Check the PR's CI results for the current commit; local test results do not establish that hosted CI passed.

The bridge began in `natehuby76/StarPilotBT:Nate/galaxybt-secretgood` at `11671f58c1e6c58b966bedcd04b1ef34823feb2d`. Pairing keys stay in `/data/galaxy-ble`.
