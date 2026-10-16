# StarPilot iPhone app

The iPhone companion and its Swift tests live here alongside the comma Bluetooth bridge in `openpilot/starpilot/galaxy_bluetooth`.

Open `GalaxyBluetooth.xcodeproj` and use the `GalaxyBluetooth` scheme. Simulator builds do not need an Apple signing account. Device and TestFlight builds require the maintainer’s Apple team and signing setup.

Run the regression checks on macOS from this folder:

```sh
CI_PRIMARY_REPOSITORY_PATH="$PWD" sh ci_scripts/ci_post_clone.sh
xcodebuild -project GalaxyBluetooth.xcodeproj -scheme GalaxyBluetooth -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

GitHub Actions runs these checks for changes to the app or companion bridge. Hardware pairing, Bluetooth reliability and CarPlay still need real-device testing.

Imported from `natehuby76/ios-clone`, branch `codex/secretgood-galaxy`, commit `081aa0e`. Bundled Galaxy resources retain their upstream license in `UPSTREAM-GALAXY-LICENSE`.

App Store ownership and signing credentials are managed separately from this source repository.
