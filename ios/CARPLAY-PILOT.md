# CarPlay testing

CarPlay support is in `GalaxyBluetooth/CarPlaySceneDelegate.swift`. It uses native CarPlay templates for the overview, temperatures, rates and Galaxy settings.

Physical CarPlay needs Apple's approved entitlement and a matching signing profile. Check the target's signing setup before testing; a TestFlight invitation alone does not provide the entitlement.

## Check on a head unit

- Open each top-level page and confirm values stay readable in light and dark mode.
- Open settings categories and use the top-bar arrows to reach the remaining pages.
- Check Back navigation and numeric controls. Change and restore a display preference to confirm saving.
- Disconnect and reconnect the phone. Check that stale readings clear and the connection recovers.

Keep initial tests parked. Share the head unit, iPhone/iOS version and a photo of any layout problem. Copy the app's connection reports after a failure.

The old Dom full-screen video capture instructions do not apply to SecretGood. CarPlay does not show a full comma-screen video stream.
