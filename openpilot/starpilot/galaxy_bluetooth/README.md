# Galaxy phone bridge

Comma side of the Android and iPhone companion apps (`openpilot/starpilot/companion/`).

- `bootstrap.py` — the `galaxy_phone` process. Once a phone has been paired (or
  Retry is tapped), it starts the Bluetooth bridge and LAN discovery as systemd
  units. It leaves Bluetooth off if it's off in comma settings. Nothing is
  downloaded: `bridge/run.sh` runs the bridge on openpilot's Python with the
  vendored packages in `vendor/` (see `vendor/VENDOR.json`).
- `bridge/server.py` — Bluetooth GATT server. Requests are forwarded to the local
  Galaxy server by `bridge/proxy.py`, which blocks Wi-Fi-only features.
- `bridge/lan_discovery.py` — advertises `_sp-galaxy._tcp` on local Wi-Fi/Ethernet.
- `bridge/pairing.py` — the shared pairing key, `/data/galaxy-ble/pairing.json`.
- `phone_ui.py` — pairing code and setup status in comma Settings → Bluetooth.

## Troubleshooting on comma

```sh
cat /data/galaxy-ble/setup-status.json
journalctl -u galaxy-ble-fork.service -n 100 --no-pager
journalctl -u galaxy-lan-discovery.service -n 100 --no-pager
```

Pairing or forgetting a phone doesn't restart the bridge; it reloads the phone
list within a second, and forgetting one phone disconnects only that phone.
Tapping Retry restarts the bridge, which drops any connected phone.

## Tests

```sh
python -m unittest discover -s openpilot/starpilot/galaxy_bluetooth/tests -v
```
