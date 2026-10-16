# StarPilot iPhone app

The iPhone app lives here. The comma Bluetooth bridge is in `openpilot/starpilot/galaxy_bluetooth`.

Open `GalaxyBluetooth.xcodeproj` in Xcode and choose the `GalaxyBluetooth` scheme. Device and TestFlight builds need your Apple team and signing profile. Simulator builds do not need signing.

From this folder, run:

```sh
sh ci_scripts/ci_post_clone.sh
xcodebuild -project GalaxyBluetooth.xcodeproj -scheme GalaxyBluetooth -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

GitHub Actions runs the app tests, simulator build and bridge tests. Bluetooth and CarPlay also need testing on real devices.

See [Quick start](QUICK-START.md) for pairing and [Tester guide](TESTER-GUIDE.md) for connection checks.

App source: `natehuby76/ios-clone`, branch `codex/secretgood-galaxy`, commit `081aa0e`. The bundled Galaxy UI keeps its upstream license in `UPSTREAM-GALAXY-LICENSE`. App Store ownership and signing are separate from this repo.
