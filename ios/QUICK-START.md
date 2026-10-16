# iPhone quick start

use the SecretGood version of the app with a comma running the matching Bluetooth bridge. the older Dom app uses different Galaxy APIs.

## install

open your TestFlight invitation on the iPhone and install the build offered there.

to build it yourself, open `ios/GalaxyBluetooth.xcodeproj` from the repo in Xcode. choose your signing team, connect your iPhone, select it as the destination and press Run. Follow the phone's trust and Developer Mode prompts if shown.

## pair

1. Leave the comma powered and Offroad for setup. it needs internet for the first bridge installation.
2. enable Bluetooth in comma Settings and open the StarPilot iPhone app pairing code.
3. on the iPhone, open the Settings gear and choose **Scan pairing code**.
4. scan the code and select your comma to finish connecting.
5. allow Bluetooth, Local Network and camera access when asked. the camera scans the pairing code.
6. open Galaxy and check that settings load.

keep the pairing code private. **Forget all app links** on comma replaces the app key; it does not remove the car's Bluetooth pairing. scan the new code to reconnect afterwards.

## choose a connection

- **Automatic:** uses reachable local Wi-Fi, with Bluetooth fallback.
- **Bluetooth only:** nearby settings access without a network on either device.
- **Wi-Fi only:** both devices must be able to reach each other on the local network.

bluetooth cannot carry every Galaxy feature. Recordings, replay, cameras, map tiles, phone internet sharing, Android Auto upload/APK download and login/logout show a Wi-Fi message.

## updates and reports

install native app updates through TestFlight. Galaxy's web UI updates separately from official `SecretGoodStarPilot`; failed downloads keep the saved UI.

for a problem, enable **Developer Mode** in app Settings, reproduce it, then use **Dev / Logs → Copy all reports**. send the report with your phone model, comma version and what you tried. do not share pairing codes or credentials.

the old FFmpeg capture flag and full-display Live View setup belong to the Dom pilot. They are not needed for this branch.
