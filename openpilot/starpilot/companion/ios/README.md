# starpilot iPhone app

the iPhone app lives here. the comma Bluetooth bridge is in `openpilot/starpilot/galaxy_bluetooth`.

open `GalaxyBluetooth.xcodeproj` in Xcode and choose the `GalaxyBluetooth` scheme. device and TestFlight builds need your Apple team and signing profile. simulator builds do not need signing.

from this folder, run:

```sh
sh ci_scripts/ci_post_clone.sh
xcodebuild -project GalaxyBluetooth.xcodeproj -scheme GalaxyBluetooth -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

github Actions runs the app tests, simulator build and bridge tests. bluetooth and CarPlay still need a check on real devices.

see [Quick start](QUICK-START.md) for pairing and [Tester guide](TESTER-GUIDE.md) for connection checks.

app source: `natehuby76/ios-clone`, branch `codex/secretgood-galaxy`, commit `081aa0e`. the bundled Galaxy UI keeps its upstream license in `UPSTREAM-GALAXY-LICENSE`. app store ownership and signing are separate from this repo.
