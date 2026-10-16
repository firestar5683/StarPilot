# bluetooth phone testing

the combined app and bridge branch is `natehuby76/StarPilotBT:secretgood-ios-integration`, based on official `SecretGoodStarPilot`. the app source and tests are under `ios/`.

## setup

install the matching branch on comma while Offroad. first bridge setup needs internet on comma. enable Bluetooth, open the StarPilot iPhone app pairing code and scan it from the app's Settings page.

once paired, Bluetooth settings access works without a network on either device. internet downloads still use comma's own connection.

the script `scripts/install_secretgood_phone_test.sh` targets the separate `secretgood-phone-test` branch. it does not install this combined branch. check its target before using it.

## checks

- select Bluetooth only. Load several settings sections, then change and restore a display preference.
- close and reopen the app, switch Developer Mode, toggle phone Bluetooth and restart comma while Offroad. check reconnects and saved settings.
- turn comma Bluetooth off. the bridge should leave it off. turn it back on with the normal control and reconnect.
- select Wi-Fi only. check that Galaxy loads and a display setting saves.
- try a Wi-Fi-only feature over Bluetooth and check the message. these include recordings, replay, cameras, map tiles, phone internet sharing, Android Auto upload/APK download and login/logout.
- use **Forget all app links** and check that the old app key stops working. scan the new code to reconnect. Car Bluetooth pairings should remain intact.

## discovery and logs

opening the iPhone pairing code requests a fresh bridge registration while Offroad. it restarts `galaxy-ble-fork.service` and closes any active app connection. it does not toggle the radio, remove bonds or replace the pairing key.

if BlueZ releases the advertisement or the adapter/system bus becomes unavailable, the bridge clears its ready marker and exits so systemd can restart it. an idle phone does not trigger a restart. a registered advertisement alone does not prove a phone can receive it.

after a failure, copy **Dev / Logs → Copy all reports** on the phone. on comma, collect:

```sh
journalctl -u galaxy-ble-fork.service -n 100 --no-pager
cat /data/galaxy-ble/setup-status.json
cat /data/galaxy-ble/bridge-ready.json
```

setup details are also in `/data/galaxy-ble/setup.log`. bridge events cover startup, advertisement registration, handshake attempts and shutdown without logging keys or payloads.

## automated tests

from the repo root:

```sh
python -m unittest discover -s openpilot/starpilot/galaxy_bluetooth/tests -v
```

with the SecretGood runtime dependencies installed, also run:

```sh
python -m unittest openpilot.starpilot.galaxy_bluetooth.tests.integration_secretgood_http -v
```

the HTTP tests use temporary settings and access directories. see `VALIDATION.md` for recorded results and remaining device checks.
