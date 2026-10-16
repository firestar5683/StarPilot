# Bluetooth phone testing

The combined app and bridge branch is `natehuby76/StarPilotBT:secretgood-ios-integration`, based on official `SecretGoodStarPilot`. The app source and tests are under `ios/`.

## Setup

Install the matching branch on comma while Offroad. First bridge setup needs internet on comma. Enable Bluetooth, open the StarPilot iPhone app pairing code and scan it from the app's Settings page.

Once paired, Bluetooth settings access works without a network on either device. Internet downloads still use comma's own connection.

The script `scripts/install_secretgood_phone_test.sh` targets the separate `secretgood-phone-test` branch. It does not install this combined branch. Check its target before using it.

## Checks

- Select Bluetooth only. Load several settings sections, then change and restore a display preference.
- Close and reopen the app, switch Developer Mode, toggle phone Bluetooth and restart comma while Offroad. Check reconnects and saved settings.
- Turn comma Bluetooth off. The bridge should leave it off. Turn it back on with the normal control and reconnect.
- Select Wi-Fi only. Check that Galaxy loads and a display setting saves.
- Try a Wi-Fi-only feature over Bluetooth and check the message. These include recordings, replay, cameras, map tiles, phone internet sharing, Android Auto upload/APK download and login/logout.
- Use **Forget all app links** and check that the old app key stops working. Scan the new code to reconnect. Car Bluetooth pairings should remain intact.

## Discovery and logs

Opening the iPhone pairing code requests a fresh bridge registration while Offroad. It restarts `galaxy-ble-fork.service` and closes any active app connection. It does not toggle the radio, remove bonds or replace the pairing key.

If BlueZ releases the advertisement or the adapter/system bus becomes unavailable, the bridge clears its ready marker and exits so systemd can restart it. An idle phone does not trigger a restart. A registered advertisement alone does not prove a phone can receive it.

After a failure, copy **Dev / Logs → Copy all reports** on the phone. On comma, collect:

```sh
journalctl -u galaxy-ble-fork.service -n 100 --no-pager
cat /data/galaxy-ble/setup-status.json
cat /data/galaxy-ble/bridge-ready.json
```

Setup details are also in `/data/galaxy-ble/setup.log`. Bridge events cover startup, advertisement registration, handshake attempts and shutdown without logging keys or payloads.

## Automated tests

From the repo root:

```sh
python -m unittest discover -s openpilot/starpilot/galaxy_bluetooth/tests -v
```

With the SecretGood runtime dependencies installed, also run:

```sh
python -m unittest openpilot.starpilot.galaxy_bluetooth.tests.integration_secretgood_http -v
```

The HTTP tests use temporary settings and access directories. See `VALIDATION.md` for recorded results and remaining device checks.
