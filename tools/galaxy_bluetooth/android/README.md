# Galaxy Bluetooth Android pilot

A native Java Android app with a pairing/scanning screen, Android BLE transport and the same bundled Galaxy mobile interface as the iPhone app. Local Galaxy requests use the existing comma bridge. The comma can stay on its current StarPilot installation; this app does not flash or replace it.

The Android source is ready for a first physical-device test, not a completed public pilot. APK compilation, unit tests, Python interoperability, the production JavaScript fetch shim, APK contents and signature verification have passed. No physical Android phone was available: installation, WebView rendering, scanning, pairing, Android Keystore persistence, actual GATT timing and real toggle writes are still unverified on Android hardware.

## Requirements

- An Android phone with Android 8.0/API 26 or newer and Bluetooth Low Energy.
- An updated Android System WebView or Chrome with native web-message support.
- The comma-side Galaxy Bluetooth bridge from this project, running alongside Galaxy on localhost:8082.
- Your own comma's pairing key, entered on the phone. There is no shared pilot key in the APK.

Android 12+ asks for Nearby devices access. Older Android requires Location permission and Location enabled to scan for BLE devices; the app does not request GPS positions. The pairing key is saved only after the comma proves possession, encrypted using Android Keystore, and excluded from backup and device transfer. Forget saved key removes the saved ciphertext. The key-entry screen blocks screenshots.

## First tester

Follow [TESTER-GUIDE.md](TESTER-GUIDE.md). This first APK is debug-signed for controlled testing. Before distributing a continuing cohort release, the StarPilot maintainer should choose the permanent application ID and a publisher-owned signing key, then produce a non-debuggable release. No publisher credentials or private signing keys belong in the repository.

## Build

Open this `android` directory in Android Studio, install SDK platform 36 and build tools 35.0.0, and use JDK 17. Android Studio will set your SDK path in ignored `local.properties`.

From this directory:

```sh
./gradlew assembleDebug testDebugUnitTest lintDebug
```

The APK is `app/build/outputs/apk/debug/app-debug.apk`. The wrapper pins Gradle 8.13 with its official distribution checksum; its generated wrapper JAR checksum was also verified against Gradle's published checksum. Dependencies are pinned for this tested build. Lint reports no errors; four warnings identify newer available versions of Gradle, AndroidX WebKit/Activity and the test-only JSON library.

Galaxy assets are copied at build time from `../ios/GalaxyBluetooth/Resources/Web`, preserving one shared source bundle. Android injects `native-bridge.js` into the mobile entry page; it never modifies the iPhone source files.

Additional checks from the project root:

```sh
node tests/android_fetch.mjs
python scripts/check_android_interop.py --java-home /path/to/jdk17 --json-jar /path/to/org-json.jar
python scripts/check_android_bundle.py android/app/build/outputs/apk/debug/app-debug.apk
```

The interoperability check uses org.json's JVM artifact and a fixed public test key, not an actual comma key. Android uses its platform JSON implementation at runtime. Install bridge test dependencies from `bridge/requirements.txt` to run Python checks.

## Connection and request handling

Bundled content is served by WebViewAssetLoader at `https://appassets.androidplatform.net`. Native web messages accept only this exact origin and the top-level frame. File/content access, mixed content and remote content inside the WebView are disabled. User-selected external HTTPS links open separately in the browser; they do not gain access to the native bridge.

The fetch shim preserves JSON, binary and multipart request bodies within the 1 MiB bound, and turns verified Bluetooth replies into ordinary Fetch Responses. Requests are bounded and serialized off the UI thread. Cancelling a queued request prevents it being sent; an already-sent request drains its response without resending. Disconnects and uncertain outcomes require reconnection and checking the current setting before manually retrying.

The BLE client requests a larger MTU and high-priority connection, negotiates the existing protocol, verifies its fresh challenge/session and request counter, and enables notification credits in eight-packet windows when supported. Final credit follows authenticated response verification. Earlier bridges fall back to read-stream or per-packet ACKs. Responses for other requests/devices are ignored by their stream tag. This introduces no new GATT services and requires no Android-specific bridge fork.

Toggles serves the bundled catalog locally only after its digest matches the authenticated comma catalog. Current values are always read fresh using the smaller settings-specific snapshot. The bridge preserves all setting values, dependencies, lock and vehicle-state flags. A catalog mismatch uses the device response rather than a guessed layout.

## Current limits

- Android radio behavior and actual screen rendering still need physical testing. Automated protocol tests do not replace that check.
- This phase covers foreground use and local settings. Background timers pause when the app leaves the foreground. It is not a background BLE service or an automatic reconnect implementation.
- Remote web resources, push notifications, media streams/video, native file downloads/exports and automatic hotspot setup are not supported by this Android pilot shell.
- Existing Galaxy API actions still determine whether an operation needs internet on the comma. The app does not supply internet or automatically enable a phone hotspot.
- Other accessories, multiple phones, different Android manufacturers and older bridge versions require the listed pilot checks.

## Attribution

The shared Galaxy bundle retains the project's [upstream provenance](../UPSTREAM.json), [license](../UPSTREAM-LICENSE) and [third-party notices](../UPSTREAM-NOTICES.md). AndroidX dependencies and the Gradle wrapper retain their respective licenses; Gradle's distribution license is included in [GRADLE-LICENSE](GRADLE-LICENSE). New Android source is part of the StarPilot fork's licensed experiment.
