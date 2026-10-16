# Galaxy phone bridge

Comma side of the Android and iPhone companion apps (`openpilot/starpilot/companion/`).

- `bootstrap.py` — the `galaxy_phone` process. While parked with internet it
  installs the bridge's Python dependencies into `/data/galaxy-ble/venv`, then
  starts the Bluetooth bridge and LAN discovery as systemd units. It won't install
  while a phone is sharing its internet, and leaves Bluetooth off if it's off in
  comma settings.
- `bridge/server.py` — Bluetooth GATT server. Requests are forwarded to the local
  Galaxy server by `bridge/proxy.py`, which blocks Wi-Fi-only features.
- `bridge/lan_discovery.py` — advertises `_sp-galaxy._tcp` on local Wi-Fi/Ethernet.
- `bridge/pairing.py` — the shared pairing key, `/data/galaxy-ble/pairing.json`.
- `phone_ui.py` — pairing code and setup status in comma Settings → Bluetooth.

## Troubleshooting on comma

```sh
cat /data/galaxy-ble/setup-status.json
cat /data/galaxy-ble/setup.log
journalctl -u galaxy-ble-fork.service -n 100 --no-pager
journalctl -u galaxy-lan-discovery.service -n 100 --no-pager
```

Opening the pairing code on comma restarts the bridge, which drops any connected
phone. It doesn't change the pairing key or Bluetooth pairings.

## Tests

```sh
python -m unittest discover -s openpilot/starpilot/galaxy_bluetooth/tests -v
```
