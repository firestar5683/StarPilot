# StarPilot Live / CarPlay pilot

The phone receives a continuous JPEG stream of the full comma display over local Wi-Fi, targeting 20 FPS at 960 pixels wide. The actual received FPS is shown on the phone. Bluetooth carries diagnostics only. Hardware throughput and capture overhead still need measurement.

CarPlay shows read-only temperatures, frame rates and observed message rates. Opening it selects Live View on the phone for when the phone is foregrounded. It does not unlock the phone or force it to the foreground. Custom driving-screen video is not included in the CarPlay display.

## Enable on comma

Update the installed fork to `Nate/galaxy-bluetooth`. Check its Git remote and branch before pulling. While parked, run in the comma SSH terminal:

```sh
command -v ffmpeg
mkdir -p /data/galaxy-ble
touch /data/galaxy-ble/diagnostics-enabled
sudo systemctl restart galaxy-ble-fork.service
sudo reboot
```

Confirm the first command prints an FFmpeg path before enabling capture. Reboot loads the Galaxy routes and UI capture hooks. The bridge must already be installed. Capture is disabled without the flag and only runs while an authenticated phone requests frames; it stops about four seconds after requests stop.

To disable:

```sh
rm -f /data/galaxy-ble/diagnostics-enabled
```

## Phone check

1. Rebuild/run in Xcode. Pair with comma once in this build to update the stored key’s accessibility for CarPlay after the phone’s first unlock.
2. Connect via local Wi-Fi, then open **Live View & diagnostics** or **Live** from Galaxy.
3. Check the displayed image against the complete comma screen, including overlays. Verify orientation and text readability. Capture uses raylib’s framebuffer. FFmpeg JPEG encoding runs in a background worker with a one-frame queue; old frames are dropped. Hardware capture and performance have not yet been verified.
4. Compare UI FPS with Live View on and off. Stop if capture causes UI stalls. Errors stop capture temporarily; stale images are removed from the phone.
5. Disconnect Wi-Fi: the image disappears, while diagnostics may continue through paired Bluetooth. Stop the comma UI or disconnect the phone and confirm stale values disappear.

If no fresh frame arrives for ten seconds, tap **Copy diagnostics** and paste the report to the developer. It includes recent connection events and capture/encoder errors, without pairing keys or authentication headers. Update both the phone app and comma fork for capture details. On comma, the same capture report is available at `/dev/shm/galaxy-companion/capture-status.json`.

Temperatures include reported CPU, onboard GPU, memory, DSP, modem, PMIC, intake, exhaust, GNSS and SoC values; available kernel thermal/hwmon sensors; and Chestnut GPU/memory when present. Sensor availability varies, and some kernel sensors duplicate existing readings. Missing/default zero values are not displayed as measured temperatures.

FPS is derived from UI frames and camera/model frame counters. Other subscribed services show observed updates per second, not rendering FPS. It is not an FPS measurement of every Linux process. First samples need another update to establish rates.

## CarPlay check

`CarPlaySceneDelegate.swift` and the scene configuration are included. Physical CarPlay requires Apple’s approved driving-task entitlement and a matching signing profile. TestFlight alone does not grant it. The entitlement file is provided but is **not enabled in the regular phone build**.

With approval, set the target’s **Code Signing Entitlements** to `GalaxyBluetooth/CarPlay.entitlements`, build and test through CarPlay. The delegate presents a native read-only list and selects the phone’s Live View. Simulator/live vehicle behavior remains untested. CarPlay cannot display an arbitrary full-screen camera/overlay stream through these templates.

## Scope

This adds one optional helper and small hooks in the UI renderer, UI state loop and Galaxy startup. No vehicle controls or settings are written. Screen/diagnostics reads require an opt-in flag and HMAC requests signed with the existing pairing key. LAN responses use Galaxy’s existing HTTP and are not encrypted; use a trusted local network. No screen recordings are retained on disk; only the latest JPEG and telemetry live in shared memory. A stream session reconnects every minute and rechecks pairing-key revocation. FFmpeg must be available in the comma UI environment. If encoding fails, capture pauses and the phone shows no live frame.
