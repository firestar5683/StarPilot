# Uniden radar detectors

This directory holds the first part of Uniden R4, R8, and R9 support, ported
from the earlier `BluetoothWorkInaunerCP` branch. So far it is only the
detector's wire format; nothing connects to a detector yet.

`protocol.py` contains:

- the detector's GATT characteristic UUIDs and its two-command startup handshake
- parsers for alert and telemetry notifications
- matching for advertised names such as `R4@…`, `R8W@…`, and `R9@…`
- `strongest()`, which chooses the alert to act on

It has no Bluetooth or StarPilot imports.

## Planned connection

The earlier branch vendored `bleak` and `dbus-fast` (about 26k lines) and used
a separate manager daemon to own the adapter. Stardust already talks to BlueZ
with `jeepney` in `bluetooth/owner.py`, so
the detector client should use jeepney too:

1. **Pair the detector in Galaxy's Bluetooth page.** That page's owner already
   runs a pairing session with an agent and prompts. Its device filter
   (`BlueZ._devices`) currently hides LE-only devices that have no name match or
   audio/HID profile, so it needs to recognize `uniden_name()`.
2. **Connect over LE as a central.** Call `Device1.Connect`, wait for
   `ServicesResolved`, find the characteristics by UUID under the device path,
   `StartNotify` the alert and telemetry characteristics, and write the
   handshake to `WRITE_UUID` without response. Notifications arrive as
   `PropertiesChanged` `Value` signals.
3. **Share the adapter.** Before each connect attempt, probe the
   cross-process admission lock (`/data/starpilot/bluetooth-owner.lock`) and
   skip the attempt while Android Auto pairing or a Galaxy scan or pairing
   holds it.
4. **Connect only when it is useful.** The earlier daemon connected while
   onroad and for 60 seconds after a manual connect, and disconnected
   otherwise.
5. **Publish its state through the new Stardust interfaces:** a cereal service
   or a small owner-backed document. The earlier branch used ad-hoc
   `/dev/shm/params` files, which Stardust has no equivalent for.

From there, Uniden state could also be offered through an authenticated,
read-only Galaxy route.

## Not ported

- The onroad radar banner.
- Alert sounds played with `aplay`.
- Speed-limit-controller auto-slowdown tiers. The slowdown changes driving
  behavior, so it belongs in Stardust's SLC owner and its qualification rules
  rather than as a direct offset.
