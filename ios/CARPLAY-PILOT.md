# carplay testing

carplay support is in `GalaxyBluetooth/CarPlaySceneDelegate.swift`. it uses native CarPlay templates for the overview, temperatures, rates and Galaxy settings.

physical CarPlay needs Apple's approved entitlement and a matching signing profile. check the target's signing setup before testing; a TestFlight invitation alone does not provide the entitlement.

## check on a head unit

- open each top-level page and confirm values stay readable in light and dark mode.
- open settings categories and use the top-bar arrows to reach the remaining pages.
- check Back navigation and numeric controls. change and restore a display preference to confirm saving.
- Disconnect and reconnect the phone. check that stale readings clear and the connection recovers.

keep initial tests parked. Share the head unit, iPhone/iOS version and a photo of any layout problem. Copy the app's connection reports after a failure.

the old Dom full-screen video capture instructions do not apply to SecretGood. carplay does not show a full comma-screen video stream.
