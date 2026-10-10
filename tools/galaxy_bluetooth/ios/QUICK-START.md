# StarPilot iPhone testing — quick start

You need an iPhone and your own comma 4 or comma 3X running the pilot branch. Comma 3X support is ready for initial hardware testing; it has not yet been verified on a physical 3X.

If Nate sends a TestFlight invitation, install Apple’s TestFlight app and open the invitation on your iPhone. Skip steps 1–2 below. Otherwise, installing the source ZIP needs a Mac with Xcode; the ZIP is not a tap-to-install iPhone download.

Keep the comma parked for setup and initial testing.

## 1. Get the files

Nate will send you **GalaxyBluetooth.zip**. Unzip it on your Mac. The instructions below assume the extracted folder is named **GalaxyBluetooth**.

Use your own Apple account, SSH key and comma pairing code. You do not need Nate’s credentials.

## 2. Install the iPhone app

1. Install Xcode from the Mac App Store. Its version must support your iPhone’s iOS version.
2. Open **GalaxyBluetooth → ios → GalaxyBluetooth.xcodeproj**.
3. In Xcode, open **Settings → Accounts** and sign in with your Apple account. A free account works for this phone build.
4. Select the project in the left sidebar, then the **GalaxyBluetooth** app target. Open **Signing & Capabilities**, enable **Automatically manage signing**, and select your **Personal Team**.
5. If Xcode says the bundle identifier is unavailable, change it to something unique, such as `com.yourname.starpilottester`.
6. Connect your iPhone to the Mac with a USB cable, unlock it and tap **Trust** if asked. Select your iPhone as the run destination at the top of Xcode.
7. If requested, enable **Developer Mode** under iPhone **Settings → Privacy & Security**, restart the phone and confirm it.
8. Press **⌘R**. Follow any device-preparation or trust prompts. If iOS asks you to trust the developer, find your account under **Settings → General → VPN & Device Management**.
9. Allow Bluetooth, Local Network and camera access when requested. Camera access is for scanning the pairing code.

Free-account installations expire after **seven days**. Connect the phone and press **⌘R** again to reinstall. TestFlight installations use the expiration shown in TestFlight.

## 3. Set up your comma

The complete experiment needs the **Nate/galaxy-bluetooth** branch of [Nate’s fork](https://github.com/natehuby76/StarPilotBT/tree/Nate/galaxy-bluetooth), including its Bluetooth bridge and phone-pairing screen. Installing the iPhone app alone does not install these on comma.

The pilot is based on a specific StarPilot Dom version. Check compatibility before replacing another branch or fork.

Follow **INSTALL-ON-COMMA.md** in the extracted folder. It covers switching to the pilot branch. Restart comma while parked with internet access; Bluetooth setup then runs automatically. Run its commands in the comma SSH terminal, one at a time. Stop if a command reports an error; send Nate the error instead of forcing the change.

To connect from your Mac Terminal, replace `YOUR_COMMA_IP` with the address shown by your comma:

```sh
ssh comma@YOUR_COMMA_IP
```

If your SSH setup uses a separate key file, use:

```sh
ssh -i /path/to/your/private-key -o IdentitiesOnly=yes comma@YOUR_COMMA_IP
```

If SSH is not set up yet, set it up on your own comma first. Your SSH public key must be authorized on that device.

## 4. Pair and connect

1. Enable Bluetooth on comma, then display its QR code: **Settings → Bluetooth → Pair phone** on comma 4, or **Settings → Bluetooth → Pair phone → MANAGE → Pair phone** on comma 3X.
2. Open the iPhone app and tap the circular **Settings** gear.
3. Tap **Scan pairing code**, scan your comma’s code, then select your comma from the Bluetooth device list to finish pairing.
4. Leave the connection mode on **Automatic**. Connect both devices to the same reachable Wi-Fi network for LAN access; Bluetooth provides nearby fallback.
5. Open the **Galaxy** tab. Check that its Toggles page loads.

Do not share the QR code or pairing key. Each tester pairs with their own comma.

## 5. Enable diagnostics and Live View

In your comma SSH terminal, run:

```sh
command -v ffmpeg
mkdir -p /data/galaxy-ble
touch /data/galaxy-ble/diagnostics-enabled
```

The first command should print an FFmpeg path. If it does not, send Nate the result before testing video. Reboot while parked to load the installed capture hooks:

```sh
sudo reboot
```

SSH disconnects during reboot. Reconnect using the same Mac Terminal command from step 3.

On the phone, open **Diagnostics** for grouped onboard readings and the separate **External GPU / Chestnut** panel. Missing Chestnut readings do not prove it is disconnected; the device may not be reporting telemetry.

Open **Live View** for the full comma screen. It needs reachable local Wi-Fi. Wake the comma’s screen if video is blank; the current pilot pauses capture when that screen sleeps. 

## 6. Comma 3X compatibility check

Run this in the comma SSH terminal after installing the bridge:

```sh
/data/galaxy-ble/venv/bin/python /data/openpilot/tools/galaxy_bluetooth/bridge/probe.py
```

Send Nate the output. It contains the hardware model, Python version, Bluetooth capabilities, Galaxy status and a Live View encoder check; it does not include the pairing key. Look for a powered adapter with `gattServer: true`, `advertising: true`, `galaxyHTTPStatus: 200`, and `liveEncoder.available: true`. An encoder failure affects video; test Galaxy settings separately. If Bluetooth is missing, enable it in comma Settings and rerun the check.

After reboot, confirm the phone can reconnect without starting anything manually. Test forgetting phones from comma Bluetooth settings: the old code should stop working, and scanning the new code should restore access. QR codes close after two minutes or when comma enters driving mode.

For the first Live View test, keep the comma awake and parked. Report video FPS, dropped frames, temperatures and any UI lag with Live View on versus off. Unavailable sensors should remain blank; do not treat them as zero readings.

## 7. First checks and feedback

- **Galaxy:** change a harmless display preference, reopen the setting and confirm it saved.
- **Bluetooth:** turn Wi-Fi off in iPhone Settings, leaving Bluetooth on. Confirm Galaxy’s local settings still work. Live video requires Wi-Fi.
- **Diagnostics:** check temperatures and rates update, and Chestnut readings stay in their own panel.
- **Live View:** confirm the image follows the comma screen and note the displayed FPS.
- **Failure:** after ten seconds without a frame, tap **Copy diagnostics** and paste the report to Nate. The same button is available in Diagnostics.

Send your iPhone model/iOS version, comma model and branch/version, network type, what you tried and what happened. Avoid screenshots of pairing codes or logs containing credentials.

## Apple references

- [Free-account testing and seven-day limits](https://developer.apple.com/support/compare-memberships/)
- [Distribution options, including TestFlight](https://help.apple.com/xcode/mac/current/en.lproj/dev31de635e5.html)

## Keeping the pilot updated

After the one-time comma setup, Galaxy's Update Manager can update the installed branch. In Advanced Updates it is labeled **Nate's BT Build**; the Git branch remains `Nate/galaxy-bluetooth`. This appears only when comma's origin is Nate's fork. Comma needs internet for downloading updates, even if the app connects over Bluetooth. Follow update/reboot prompts while parked. Get native iPhone updates from TestFlight. Dependency changes automatically trigger setup while parked with comma internet access.

## Automatic setup and existing settings

First setup needs internet on comma. Restart while parked, enable Bluetooth and
open Settings → Bluetooth → Pair phone. Wait for Ready to pair, then scan its QR
code. If setup fails, reconnect comma to internet and choose Retry setup. Once
installed, Bluetooth works without internet. No SSH bridge setup is required.

The Bluetooth installer preserves existing settings and pairing keys. The first
boot privately backs up persistent parameters and caches on comma. StarPilot's
existing migrations still apply when changing versions, so check your driving
settings afterwards. Do not share the settings backup: it contains credentials.
