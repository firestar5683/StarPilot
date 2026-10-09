# Run this fork as the installed StarPilot on comma

The pilot branch is based on the user's installed upstream Dom commit
`15bbbf3cc4ad251c173abf01fff931951202331a`. Its tree differs from that version
only under `tools/galaxy_bluetooth`; driving/runtime source and prebuilt files
are retained from Dom. This establishes source equality, not new road testing.

Run the following in the comma SSH terminal while parked. The existing theme
changes are outside the added folder and can remain in the checkout. Commands
use normal Git switching; they do not force-reset or delete your changes. If Git
reports a conflict, stop and inspect it rather than forcing the switch.

## Switch the installed repository

```sh
git -C /data/openpilot remote add galaxy-bt https://github.com/natehuby76/StarPilotBT.git
git -C /data/openpilot fetch galaxy-bt refs/heads/codex/galaxy-bluetooth:refs/remotes/galaxy-bt/codex/galaxy-bluetooth
git -C /data/openpilot switch --track galaxy-bt/codex/galaxy-bluetooth
git -C /data/openpilot remote set-url origin https://github.com/natehuby76/StarPilotBT.git
git -C /data/openpilot config branch.codex/galaxy-bluetooth.remote origin
git -C /data/openpilot config branch.codex/galaxy-bluetooth.merge refs/heads/codex/galaxy-bluetooth
```

Run one command at a time, stopping on an error. The remote-add step is needed
only once. Setting origin and branch tracking to this fork makes subsequent
updates target this fork/branch rather than upstream Dom.

Check the result:

```sh
git -C /data/openpilot branch --show-current
git -C /data/openpilot remote get-url origin
```

Expected branch: `codex/galaxy-bluetooth`. Expected origin:
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
StarPilot Bluetooth enabled. Runtime service startup was confirmed on the pilot
comma; automatic startup after reboot still needs verification.

Look for `Galaxy BLE bridge ready…`. Then restart comma using its normal Restart
control. Confirm StarPilot opens and the phone reconnects without an SSH session.
The SSH connection will close during restart; reconnect with your normal key.

No factory reinstall is required for the initial switch. Factory flashing is the
user's chosen recovery route. A factory flash should be treated as a fresh setup,
including SSH, bridge dependencies and pairing.
