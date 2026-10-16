# SecretGood phone test build

Repository: `natehuby76/StarPilotBT`
Branch: `secretgood-phone-test`
Official base: `firestar5683/StarPilot:SecretGoodStarPilot` at `01fd37fa7509174d71a626f66fa5567b4603b00e`.

This is the official SecretGood source and its shipped device artifacts, with phone-app Bluetooth startup, pairing, authenticated API forwarding and Wi-Fi discovery added. No vehicle controls, models, tuning defaults, migration rules or Galaxy web files are changed. It does not depend on PR #221 being merged.

## Install

If your comma already runs `natehuby76/StarPilotBT`, use its Software settings: check for updates, select `secretgood-phone-test` as the target branch, download it and install while parked. Confirm the installed repository and branch after reboot. If the branch selector cannot change between these layouts, use the staged SSH installation below.

Over SSH on the parked comma, download and run the staged installer:

```sh
curl -fL --output /tmp/install-secretgood-phone-test.sh https://raw.githubusercontent.com/natehuby76/StarPilotBT/secretgood-phone-test/scripts/install_secretgood_phone_test.sh
bash /tmp/install-secretgood-phone-test.sh
```

It downloads a separate checkout, verifies the exact repository/branch and SecretGood base, rechecks Offroad state, preserves the previous checkout as `/data/openpilot-before-secretgood-<timestamp>`, and reboots. It does not delete Params or pairing keys. SecretGood's unchanged launcher handles its required AGNOS version (currently 19.8.1); allow time for that official OS update if your device is older. This script has been syntax/review checked, not run against your comma.

The standard `installer.comma.ai/<user>/<branch>` assumes a repository named `openpilot`. Your repository is named `StarPilotBT`, and that alias currently returns 404. Do not use an unverified generic installer link for this branch.

Connect the comma to the internet for the first phone bridge setup. Subsequent Bluetooth use requires no network. In comma Settings → Bluetooth, enable Bluetooth, then open **StarPilot iPhone app → Pair** and scan the private code in the iPhone app. **Forget all app links** rotates the app key; it does not remove the car's or other Bluetooth devices' pairings. The existing radio power/device controls still use SecretGood's shared BluetoothOwner.

The phone must run the SecretGood app migration from `natehuby76/ios-clone`, branch `codex/secretgood-galaxy` (version 0.2.0), PR #1. Xcode Cloud build 28 has been started from that branch for internal TestFlight testing. The older Dom app is not compatible with these new Galaxy APIs. The native app's bundled Galaxy files match this comma base exactly.

## Parked checks

- Bluetooth only: connect, open Galaxy settings, read several sections, change and restore one appearance setting.
- Close/reopen the app; switch Developer Mode; turn phone Bluetooth off/on; restart the comma; confirm recovery and saved settings.
- Turn comma Bluetooth off. The phone bridge must not turn it back on. Turn it back on with the normal comma control and reconnect.
- Wi-Fi only: use the comma's local address; verify Galaxy loads and settings save through its local login session.
- Bluetooth recordings, replay, cameras, map tiles, phone internet sharing, Android Auto upload/APK download and login/logout return a Wi-Fi-required message.
- Copy the iPhone's Developer Mode → Dev / Logs reports after any failure. On comma, setup status is `/data/galaxy-ble/setup-status.json`, setup log `/data/galaxy-ble/setup.log`, runtime logs `journalctl -u galaxy-ble-fork.service -u galaxy-lan-discovery.service`.

First startup uses SecretGood's own settings migration and recovery rules. A local build/test result does not establish vehicle qualification or successful radio operation on your comma. Keep initial testing parked.

## Validation

`python -m unittest discover -s openpilot/starpilot/galaxy_bluetooth/tests -v` checks encryption/framing, notification windows, key rotation, proxy login/retry/isolation, blocked media and startup/radio preference handling.

On a configured SecretGood runtime, run `python -m unittest openpilot.starpilot.galaxy_bluetooth.tests.integration_secretgood_http -v` for the actual HTTP settings pages and display preview/confirm tests. Tests use temporary Params and access directories.

`python tools/laptop_device_build/validate_artifacts.py .` checks the shipped AArch64/QCOM artifacts. This branch retains upstream prebuilt binaries; it does not rebuild or claim device inference validation.
