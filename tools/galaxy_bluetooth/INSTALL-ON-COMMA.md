# Run this fork as the installed StarPilot on comma

The pilot branch is based on the user's installed upstream Dom commit
`15bbbf3cc4ad251c173abf01fff931951202331a`. Its tree differs from that version
under `tools/galaxy_bluetooth` plus phone-pairing, diagnostics and screen-capture
hooks. Driving-control code and prebuilt files are retained from Dom.
This establishes source equality for driving code, not new road testing.

Run the following in the comma SSH terminal while parked. The existing theme
changes are outside the added folder and can remain in the checkout. Commands
use normal Git switching; they do not force-reset or delete your changes. If Git
reports a conflict, stop and inspect it rather than forcing the switch.

## Switch the installed repository

```sh
git -C /data/openpilot remote add galaxy-bt https://github.com/natehuby76/StarPilotBT.git
git -C /data/openpilot fetch galaxy-bt refs/heads/Nate/galaxy-bluetooth:refs/remotes/galaxy-bt/Nate/galaxy-bluetooth
git -C /data/openpilot switch --track galaxy-bt/Nate/galaxy-bluetooth
git -C /data/openpilot remote set-url origin https://github.com/natehuby76/StarPilotBT.git
git -C /data/openpilot config branch.Nate/galaxy-bluetooth.remote origin
git -C /data/openpilot config branch.Nate/galaxy-bluetooth.merge refs/heads/Nate/galaxy-bluetooth
```

Run one command at a time, stopping on an error. The remote-add step is needed
only once. Setting origin and branch tracking to this fork makes subsequent
updates target this fork/branch rather than upstream Dom.

Check the result:

```sh
git -C /data/openpilot branch --show-current
git -C /data/openpilot remote get-url origin
```

Expected branch: `Nate/galaxy-bluetooth`. Expected origin:
`https://github.com/natehuby76/StarPilotBT.git`.

## Use the fork's bridge at startup

Stop any manually running bridge first with Ctrl-C in its terminal. The separate
bridge environment and private pairing file stay at `/data/galaxy-ble`; the
service now reads its source from the installed fork, not the earlier copied app.

```sh
sh /data/openpilot/tools/galaxy_bluetooth/bridge/install.sh
bash /data/openpilot/tools/galaxy_bluetooth/bridge/start-at-boot.sh
sudo journalctl -u galaxy-ble-fork.service -n 20 --no-pager
```

Comma's system partition is read-only. The helper links the unit into writable
`/run/systemd/system`, then starts it. Runtime registration disappears on reboot,
so call the helper on every boot from the writable `/data/continue.sh` launcher.
The device's `/usr/comma/comma.sh` executes this launcher.

First read `cat /data/continue.sh`. For a launcher containing only the shebang,
`cd /data/openpilot` and `exec ./launch_openpilot.sh`, use:

```sh
cat > /data/continue.sh <<'EOF'
#!/usr/bin/env bash
bash /data/openpilot/tools/galaxy_bluetooth/bridge/start-at-boot.sh >> /data/galaxy-ble/boot.log 2>&1 &
cd /data/openpilot
exec ./launch_openpilot.sh
EOF
chmod +x /data/continue.sh
bash -n /data/continue.sh
```

For a launcher with other custom commands, preserve them and insert only the
background helper call before the existing exec. The helper's service commands
have time limits and never prompt for sudo passwords. Its background invocation
does not block StarPilot startup if Bluetooth fails. Inspect `/data/galaxy-ble/boot.log`
if service registration fails after reboot. Recheck the hook if an installer
replaces `/data/continue.sh`.

An existing pairing key is preserved. If this is a fresh setup, the installer
prints the new key for entry into the phone app; do not share that output.
The unit intentionally skips startup if its source, environment or pairing file
is missing. It runs as comma and restarts failures after 10 seconds. Keep
StarPilot Bluetooth enabled. Runtime service startup and startup after reboot were confirmed on the pilot
comma.

Look for `Galaxy BLE bridge ready…`. Then restart comma using its normal Restart
control. Confirm StarPilot opens and the phone reconnects without an SSH session.
The SSH connection will close during restart; reconnect with your normal key.

No factory reinstall is required for the initial switch. Factory flashing is the
user's chosen recovery route. A factory flash should be treated as a fresh setup,
including SSH, bridge dependencies and pairing.

## Pair a phone without copying a key

On comma 4 while offroad, open Settings → Pair phone → pair phone. In the updated
iPhone app, choose Scan pairing code, allow camera access and scan the displayed
code. Select the comma found by Bluetooth. The app saves the key in Keychain only
after its encrypted bridge handshake succeeds. No internet is needed to scan.
Enable Bluetooth in StarPilot; install the bridge and boot hook once per device
as above. QR pairing removes key-copying, but does not install dependencies or
enable the bridge by itself. A native iPhone app rebuild is required for scanning.

The QR contains a private shared Bluetooth key, not a Galaxy web link. Keep it
private. The display closes after two minutes or when going onroad; this hides
the code but does not expire the shared credential. Multiple phones may share
it. Settings → Pair phone → forget paired phones requires a confirmation slide
and replaces the key atomically. The bridge closes old sessions and rejects old
keys without restarting its Bluetooth advertisement. Previously accepted setting
requests cannot be undone by revocation. Revocation affects this BLE bridge, not
Galaxy's existing web password, cloud sessions or iPhone Bluetooth bonds.

Pilot validation: iOS generic build and automated QR parsing/key preservation,
rotation, old-key rejection and permission checks. Actual comma screen, camera
scanning and revoke/re-pair hardware checks remain required.

## Comma 3X pilot

The same branch and bridge installer apply. Enable Bluetooth in Settings, then pair from **Settings → Device → Pair phone**. Run `tools/galaxy_bluetooth/bridge/probe.py` with `/data/galaxy-ble/venv/bin/python` and send the report before testing. Physical 3X validation is still pending. See `ios/QUICK-START.md` for the reboot, revocation and Live View checks.
