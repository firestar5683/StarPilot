# SecretGood support

This app targets `firestar5683/StarPilot:SecretGoodStarPilot`. Its Galaxy UI starts at `index.html` under `openpilot/starpilot/galaxy/web`.

The app keeps a bundled UI for offline startup and checks official SecretGood for updates. It verifies downloaded files and keeps the saved copy if an update fails. Sample runtime data is excluded; device identity comes from the connected comma.

Wi-Fi requests first open `/api/auth/session`, keep that comma's cookie and refresh it once after the explicit session-expired response. Writes include the Origin and JSON content headers. Connection failures do not repeat writes.

Discovery uses `_sp-galaxy._tcp`. Bluetooth and Wi-Fi identity checks must identify the same comma before switching automatically.

CarPlay uses `/api/settings/pages/…`, `/api/settings/preview` and `/api/settings/confirm`. Diagnostics use `/api/system/monitor`. The old Dom Params and full-screen MJPEG routes are not used.

Features blocked over Bluetooth keep their 501 response and show a Wi-Fi message. Large media transfers and CarPlay still need real-device testing.

Run `sh ci_scripts/ci_post_clone.sh` from this folder and build the GalaxyBluetooth scheme to check the app. See [Tester guide](TESTER-GUIDE.md) for device checks.
