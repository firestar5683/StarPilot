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

## Automatic Bluetooth setup

Restart comma after switching to the pilot branch. While parked, the branch
installs the bridge in `/data/galaxy-ble/venv`, preserves its pairing key and
starts it automatically. First setup needs internet on comma. Later boots work
offline unless dependencies need updating. No `/data/continue.sh` edits or
manual service installation are needed. An older background service hook may
remain; startup is idempotent.

In Settings → Bluetooth → Pair phone, check setup status. Enable Bluetooth on
comma. If setup fails, connect comma to internet and choose Retry setup.
Installation errors are in `/data/galaxy-ble/setup.log`; bridge errors are in
`sudo journalctl -u galaxy-ble-fork.service -b --no-pager`.

## Existing settings

Bluetooth setup does not write or reset StarPilot parameters. Before the usual
launch migrations, the first boot with this feature privately saves persistent
parameters and caches to `/data/galaxy-ble/settings-before-pilot.tar.gz`. It keeps
the first successful snapshot across boots and updates. This contains private
credentials: do not send it with tester logs. A failed snapshot is reported in
the startup log and retried on the next boot; it does not clear existing settings.

The pilot retains Dom's existing migrations. Switching from a different version
may run those migrations and change individual settings. Check driving settings
after switching. The snapshot is for recovery with assistance; automatic restore
could overwrite newer settings and is intentionally absent. Factory flashing is
a separate operation and may erase device data.

## Pair a phone without copying a key

On comma 4 while offroad, open Settings → Bluetooth → Pair phone → pair phone. In the updated
iPhone app, choose Scan pairing code, allow camera access and scan the displayed
code. Select the comma found by Bluetooth. The app saves the key in Keychain only
after its encrypted bridge handshake succeeds. No internet is needed to scan.
Enable Bluetooth in StarPilot and wait for automatic setup to show Ready to pair. A native iPhone app rebuild is required for scanning.

The QR contains a private shared Bluetooth key, not a Galaxy web link. Keep it
private. The display closes after two minutes or when going onroad; this hides
the code but does not expire the shared credential. Multiple phones may share
it. Settings → Bluetooth → Pair phone → forget paired phones requires a confirmation slide
and replaces the key atomically. The bridge closes old sessions and rejects old
keys without restarting its Bluetooth advertisement. Previously accepted setting
requests cannot be undone by revocation. Revocation affects this BLE bridge, not
Galaxy's existing web password, cloud sessions or iPhone Bluetooth bonds.

Pilot validation: iOS generic build and automated QR parsing/key preservation,
rotation, old-key rejection and permission checks. Actual comma screen, camera
scanning and revoke/re-pair hardware checks remain required.

## Comma 3X pilot

The same branch and automatic bridge setup apply. Enable Bluetooth in Settings, then pair from **Settings → Bluetooth → Pair phone**. Run `tools/galaxy_bluetooth/bridge/probe.py` with `/data/galaxy-ble/venv/bin/python` and send the report before testing. Physical 3X validation is still pending. See `ios/QUICK-START.md` for the reboot, revocation and Live View checks.

## Updates from Galaxy

Galaxy labels `Nate/galaxy-bluetooth` in this fork as **Nate's BT Build**. Advanced Updates lists branches from the installed repository's `origin`; this fork will not appear on devices whose origin still points to official StarPilot. Complete the fork switch and bridge/boot setup above once per comma.

After setup, open Galaxy's Update Manager, check for updates and follow its confirmation/reboot steps while parked. The comma must have internet through Wi-Fi, a phone hotspot or its own cellular connection. The phone may send the update request over Bluetooth, but Bluetooth does not supply internet to comma. Native iPhone updates come through TestFlight; Galaxy's update buttons update comma software. Dependency changes automatically trigger setup while parked; comma needs internet for those updates.
