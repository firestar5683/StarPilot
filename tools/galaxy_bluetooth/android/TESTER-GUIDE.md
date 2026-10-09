# First Android tester

Build: **Galaxy Bluetooth Pilot 0.1.0**, package `link.firestar.galaxybt.pilot`, Android 8.0 or newer. This is an early debug-signed test build. Start with a parked comma and a reversible display setting such as units.

## Connect

1. Install the supplied APK on your Android phone. If Android asks, allow installation from the app you use to open that APK.
2. Update Android System WebView or Chrome if the app requests it.
3. Start the existing Galaxy Bluetooth bridge on your own comma, following the project [bridge setup](../README.md#run-the-bridge-on-comma). Keep it running until this test is complete.
4. Open **Galaxy Bluetooth Pilot** and enter your comma's 64-character pairing key. Keep that key private; it is not a GitHub account token or Wi-Fi password.
5. Tap **Scan for comma**, allow Nearby devices access, and select Galaxy. On Android 11 or older, Android also needs Location permission and the Location setting enabled for scanning.
6. Wait for **Connected over Bluetooth · local settings**. Open Toggles.

## Check local settings

1. With Bluetooth still enabled, turn the phone's Wi-Fi and cellular off. Open Toggles and time how long it takes until the correct controls appear.
2. Note the current value of a reversible display setting, change it once and confirm it on the comma. Leave Toggles and reopen it to confirm the saved value is read back. Restore its original value and confirm again.
3. Disconnect from the app and scan/reconnect. Confirm the saved key is available and Toggles reloads current values.
4. Put the app in the background and bring it back. Confirm it either still works or clearly asks for reconnection; never treat a timeout as proof a change did not happen.
5. Stop and restart the comma bridge. Confirm the phone reports a lost connection and can reconnect. If the comma reports `Failed to register advertisement`, reset its Bluetooth and start the bridge again; include that occurrence in the report.
6. To test both devices without a network, first use the project's optional bridge startup service so losing SSH does not stop it. Then disable networking on both devices, retain Bluetooth, and repeat the read/change/read-back check.

Do not run iPhone and Android tests simultaneously until each has passed alone. Then test switching phones and reconnecting with existing Bluetooth accessories as a separate check. Each device uses its own authenticated session, while bridge notifications may be shared.

## Report

Share only the phone model, Android version, Android System WebView/Chrome version, app version, installed StarPilot branch/commit, approximate Toggles load time, and whether each check passed. For a failure, include the visible app message and the bridge's timing/error lines. Do not include pairing keys, Wi-Fi passwords or complete parameter dumps.

APK contents and cryptographic interoperability have passed automated checks. A maintainer should review this first physical result before inviting more testers. A continuing cohort needs a publisher-owned release signing key, a fixed app identifier, update/rollback instructions and completed Android hardware checks; the initial debug build is not the official StarPilot app release.
