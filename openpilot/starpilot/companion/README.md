# StarPilot companion apps

Phone apps for Galaxy. Both talk to the comma over Wi-Fi/LAN or Bluetooth and
share one pairing key.

```
companion/
├── android/   Android app (Gradle project, build_apk.sh, host tests)
├── ios/       iPhone app (Xcode project, CarPlay, tests) — see ios/README.md
└── run_host_tests.py
```

The comma side lives elsewhere:

- `openpilot/starpilot/galaxy_bluetooth/` — Bluetooth bridge, LAN discovery and
  the pairing screen, run by the `galaxy_phone` process.
- `openpilot/starpilot/galaxy/companion*.py` — phone internet sharing.

Over Bluetooth, pairing, phone internet sharing, APK downloads, recordings,
replay, cameras and map tiles are blocked; they need Wi-Fi.

## Pairing and phone music

One step pairs the app and phone music. On comma open Settings → Bluetooth →
**Pair phone**; comma opens a two-minute window that takes one phone.

- Android: tap **Pair with comma** in the app. It gets its key, then bonds for music
  and shows one system prompt to approve.
- iPhone: tap **Pair with comma** in the app, then tap comma once in
  Settings → Bluetooth (iOS cannot start a Bluetooth bond from an app).
- No app: tap comma in the phone's Bluetooth settings to pair music only.

Forgetting a Bluetooth device in comma Settings also removes its app key. Installing
Spotify (`/api/spotify/upload`) is blocked over Bluetooth like the other large uploads.

## Phone GPS

Each app can send the phone's GPS to comma about once a second, over Bluetooth or
Galaxy Wi-Fi. Comma publishes it as `phoneGps` and navigation uses it only when
comma's own GPS and the car's GPS have no fix. Galaxy → Navigation → GPS Source can
instead ignore the phone or prefer it; mapd follows the same choice.

- Android: Connections → **Share phone GPS with comma**. Runs as a foreground
  service with a notification.

`POST /api/companion/location` with JSON: `latitude`, `longitude`,
`horizontalAccuracy` (m) and `ageMs` (phone-measured age, at most 2000) are
required; `altitude`, `verticalAccuracy`, `speed`, `speedAccuracy`, `bearing`,
`bearingAccuracy` and `timestamp` (Unix ms) are optional. Leave out unknown
values. Comma dates the fix by its own clock minus `ageMs`, never by `timestamp`.
Refused through the remote tunnel.

## Android

Install: join the Galaxy hotspot, open Galaxy → **Galaxy Access & Install** →
**Android companion**, and install the APK. Later updates install from inside
the app: tap **Update app** while connected over Galaxy Wi-Fi/LAN, allow
installation from StarPilot if Android asks, and confirm the Android update dialog.
The APK streams into Android's installer; there is no file to find in Downloads.
After replacement, an **Update installed → Reopen** notification opens the new app.
Enable app notifications for this prompt. If notifications are disabled, open
StarPilot normally; the app confirms the completed update on launch.

### When an APK rebuild is needed

| Change | Rebuild Android APK? |
| --- | --- |
| Kotlin/Java code, native bridge, updater, phone GPS, Bluetooth or services | Yes |
| Android manifest, permissions, resources, icons, Gradle config or dependencies | Yes |
| Files in `android/app/src/main/assets/`, including `bluetooth-fetch.js` | Yes |
| Galaxy HTML/CSS/JS used over Bluetooth | Yes: Gradle bundles `galaxy/web` into the APK |
| Galaxy HTML/CSS/JS used over Wi-Fi/LAN | No for those connections: screens load from comma. Rebuild too if Bluetooth should get the same change |
| Comma-side Python/services/API changes only | No, unless the phone protocol or bundled UI also needs a change |
| iOS-only code or documentation | No |

Release checklist: increment both `versionCode` and `versionName`, run relevant
host/unit tests, then run `build_apk.sh` (release build and lint). Keep the existing
signing key so Android can update in place and retain pairing/settings. Verify the
APK's package ID, version and signing certificate; distribute the generated APK
and matching `.version` together. Test an upgrade on a phone: Update, Android
confirmation, Reopen, and retained settings. Building does not deploy to comma.
An old app without the native updater needs one manual APK installation first.

Build (JDK 17+, Android SDK 37):

```sh
openpilot/starpilot/companion/android/build_apk.sh
```

This builds and lints the release APK and copies it to
`openpilot/starpilot/galaxy/bin/starpilot-companion.apk` with its `.version`.
Bump `versionCode`/`versionName` in `android/app/build.gradle.kts` first.

Signing uses `~/.starpilot/companion.jks` (alias `companion`, override with
`COMPANION_KEYSTORE`) and the password in `~/.starpilot/companion-signing-password`
or `COMPANION_KEY_PASSWORD`. The key is not in the repo. **Back it up** — without
it, installed apps can't be updated. Certificate SHA-256:

```
d9e72cbb842e9530b4b686dec424cdeb8f2982109be6875fa73594c33332fc3a
```

## Tests

From the repo root:

```sh
uv run --extra testing --with pycryptodome==3.23.0 --with dbus-next==0.2.3 --with zeroconf==0.151.3 \
  python openpilot/starpilot/companion/run_host_tests.py
node --test openpilot/starpilot/companion/android/tests/test_bluetooth_fetch.mjs
(cd openpilot/starpilot/companion/android && ./gradlew testDebugUnitTest)
```

`run_host_tests.py` stubs native modules so it runs on a laptop; it also takes
explicit test paths. iPhone tests are in `ios/README.md`.
