# connection testing

start with a powered, Offroad comma and the matching SecretGood phone build. pair once with Settings → Bluetooth → Pair phone on comma, then Pair with comma in the app.

## wi-fi and Bluetooth

1. select **Automatic** and connect both devices to the same local network. confirm the app shows Wi-Fi and Galaxy loads.
2. open a display preference. turn Wi-Fi off in iPhone Settings, leaving Bluetooth on.
3. confirm the app switches to Bluetooth and settings still load. change the display preference, reopen it and check that it saved.
4. restore Wi-Fi and check that Automatic returns to it.
5. repeat with **Bluetooth only** and **Wi-Fi only** selected.

if a setting change loses its response, reload the setting before trying again. the app does not repeat writes automatically after a connection failure.

## hotspots

comma can use a hotspot, Wi-Fi or its SIM for internet. that is separate from the phone's connection to comma. bluetooth settings access needs no internet; model and software downloads still need internet on comma.

some hotspots isolate clients. if direct Wi-Fi access fails, use Bluetooth or another reachable local network. the app does not enable Personal Hotspot or configure comma's Wi-Fi password.

## reconnects

check closing and reopening the app, switching Developer Mode, turning phone Bluetooth off and on, and restarting comma while Offroad. confirm it reconnects without manual setup.

turn comma Bluetooth off and confirm the bridge leaves it off. turn it back on using the normal comma control, then reconnect.

## galaxy UI updates

the app has no bundled Galaxy pages. whenever it connects to comma over Wi-Fi/LAN (or you choose **Check** on the Galaxy screens row) it downloads comma's own web UI, verifies every file against comma's manifest and saves it. a comma without that manifest is too old to share its screens.

an update does not replace an open page. it takes effect when Galaxy next opens. failed or incomplete updates keep the previous copy. a fresh install cannot open Galaxy over Bluetooth until it has downloaded the screens once over Wi-Fi. if comma updated since, Bluetooth still opens the saved copy and says it is from an older comma build.

download the screens over comma's Wi-Fi first, then reopen with phone Wi-Fi and cellular off and Bluetooth on. Galaxy should still load its saved screens. swift changes require a new app build.

## feedback

enable Developer Mode in Settings and use **Dev / Logs → Copy all reports** after a failure. include the connection mode, device versions, what you tried and any error you received. keep pairing codes and passwords out of screenshots.
