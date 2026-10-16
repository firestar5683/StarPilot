# SecretGood Galaxy migration

The iPhone app now targets `firestar5683/StarPilot:SecretGoodStarPilot` only.
Bundled web source: `ff1beb12902ac441d3423f54cc12e9354c25e124`, `openpilot/starpilot/galaxy/web`.
The bundled files retain their upstream contents and license. Sample runtime data is excluded; runtime identity always comes from the connected comma.

- Wi-Fi sessions are scoped to the configured endpoint and connection generation. An explicit session-expired 401 refreshes once. Network failures never replay a mutation.
- CarPlay consumes `/api/settings/pages/…`, then `/api/settings/preview` and `/api/settings/confirm`. It does not write raw Params or replace server permission checks.
- Galaxy updates follow SecretGood, verify Git object hashes and keep the previous verified UI if downloading or verification fails.
- `_sp-galaxy._tcp` is the discovery service. BLE identity and LAN verification use the same runtime instance.
- The bridge must support SecretGood's `/api/…` and `/data/runtime.json` requests and its authenticated session context. The Dom bridge is not compatible.
- Bluetooth-only features rejected with 501 keep their server response. Media, replay and upload support still depends on the comma's Wi-Fi endpoints and the app's bounded request sizes; this is not a claim that large transfers have been device-tested.
- Native diagnostics use `/api/system/monitor`. The old full-screen MJPEG endpoint is retired; camera features live in SecretGood's Galaxy UI.

Validation: run `CI_PRIMARY_REPOSITORY_PATH="$PWD" sh ci_scripts/ci_post_clone.sh` and build the GalaxyBluetooth Xcode scheme. Real comma pairing, BLE endpoint/session compatibility, media and CarPlay still require testing against the matching comma build.
