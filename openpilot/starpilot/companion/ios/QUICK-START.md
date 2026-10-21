# iPhone quick start

use the SecretGood version of the app with a comma running the matching Bluetooth bridge. the older Dom app uses different Galaxy APIs.

## install

open your TestFlight invitation on the iPhone and install the build offered there.

to build it yourself, open `openpilot/starpilot/companion/ios/GalaxyBluetooth.xcodeproj` from the repo in Xcode. choose your signing team, connect your iPhone, select it as the destination and press Run. Follow the phone's trust and Developer Mode prompts if shown.

## pair

1. Leave the comma powered and Offroad for setup. it needs internet for the first bridge installation.
2. on comma open Settings → Bluetooth → **Pair phone**. the window stays open for two minutes.
3. on the iPhone, open the app and tap **Pair with comma**. allow Bluetooth and Local Network access when asked.
4. when the app says so, open iPhone Settings → Bluetooth and tap your comma once. that pairs phone music; iOS does not let an app do it.
5. open Galaxy and check that settings load.

the app and phone music pair in the same window. **Forget** on a Bluetooth device in comma Settings also removes its app key; it does not remove the car's Bluetooth pairing. tap **Pair with comma** again to reconnect afterwards.

## choose a connection

- **Automatic:** uses reachable local Wi-Fi, with Bluetooth fallback.
- **Bluetooth only:** nearby settings access without a network on either device.
- **Wi-Fi only:** both devices must be able to reach each other on the local network.

bluetooth cannot carry every Galaxy feature. Recordings, replay, cameras, map tiles, phone internet sharing, Android Auto upload/APK download and login/logout show a Wi-Fi message.

## updates and reports

install native app updates through TestFlight. Galaxy's web UI is downloaded from your comma over Wi-Fi/LAN (connect once before using Bluetooth) and refreshed whenever you reconnect; failed downloads keep the saved UI.

for a problem, enable **Developer Mode** in app Settings, reproduce it, then use **Dev / Logs → Copy all reports**. send the report with your phone model, comma version and what you tried. do not share pairing codes or credentials.

the old FFmpeg capture flag and full-display Live View setup belong to the Dom pilot. They are not needed for this branch.
