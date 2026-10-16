# Connection testing

Start with a powered, Offroad comma and the matching SecretGood phone build. Pair once using the comma's private QR code.

## Wi-Fi and Bluetooth

1. Select **Automatic** and connect both devices to the same local network. Confirm the app shows Wi-Fi and Galaxy loads.
2. Open a display preference. Turn Wi-Fi off in iPhone Settings, leaving Bluetooth on.
3. Confirm the app switches to Bluetooth and settings still load. Change the display preference, reopen it and check that it saved.
4. Restore Wi-Fi and check that Automatic returns to it.
5. Repeat with **Bluetooth only** and **Wi-Fi only** selected.

If a setting change loses its response, reload the setting before trying again. The app does not repeat writes automatically after a connection failure.

## Hotspots

Comma can use a hotspot, Wi-Fi or its SIM for internet. That is separate from the phone's connection to comma. Bluetooth settings access needs no internet; model and software downloads still need internet on comma.

Some hotspots isolate clients. If direct Wi-Fi access fails, use Bluetooth or another reachable local network. The app does not enable Personal Hotspot or configure comma's Wi-Fi password.

## Reconnects

Check closing and reopening the app, switching Developer Mode, turning phone Bluetooth off and on, and restarting comma while Offroad. Confirm it reconnects without manual setup.

Turn comma Bluetooth off and confirm the bridge leaves it off. Turn it back on using the normal comma control, then reconnect.

## Galaxy UI updates

The app checks `firestar5683/StarPilot:SecretGoodStarPilot` when it becomes active or you choose **Check Galaxy updates**. It downloads the web UI from one commit and verifies the files before saving them.

An update does not replace an open page. It takes effect when Galaxy next opens. Failed or incomplete updates keep the previous copy; a fresh install includes a bundled copy.

Check an update while online, then reopen with phone Wi-Fi and cellular off and Bluetooth on. Galaxy should still load its saved screens. Swift changes require a new app build.

## Feedback

Enable Developer Mode in Settings and use **Dev / Logs → Copy all reports** after a failure. Include the connection mode, device versions, what you did and the error shown. Keep pairing codes and passwords out of screenshots.
