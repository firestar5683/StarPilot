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

If the app already reaches comma over Wi-Fi/LAN, **Pair with comma** opens that window itself (the call
Galaxy's Bluetooth page makes), so nothing needs touching on comma. Without a Wi-Fi/LAN session it waits for
the window as above.

- Android: tap **Pair with comma** in the app. It gets its key, then bonds for music
  and shows one system prompt to approve.
  Opening Galaxy over Wi-Fi/LAN on a phone with no comma key starts this by itself, once per launch
  (it asks for the Nearby devices permission first); if comma cannot open a window it stays quiet and
  **Pair with comma** remains in the menu.
- iPhone: tap **Pair with comma** in the app, then tap comma once in
  Settings → Bluetooth (iOS cannot start a Bluetooth bond from an app).
- No app: tap comma in the phone's Bluetooth settings to pair music only.

Forgetting a Bluetooth device in comma Settings also removes its app key. Installing
Spotify (`/api/spotify/upload`) is blocked over Bluetooth like the other large uploads.

## Phone GPS

Each app can send the phone's GPS to comma about once a second, over Bluetooth or
Galaxy Wi-Fi. Comma carries it inside the navigation message as `phoneGps`, keeps the last fix for
10 seconds, and navigation uses it only when comma's own GPS and the car's GPS have no fix. Galaxy → Navigation → GPS Source can
instead ignore the phone or prefer it; mapd follows the same choice.

The 10-second hold is an expiry allowance, not an update interval. Navigation
checks for new phone fixes five times a second and forwards each new measurement
at the next check; without new fixes it publishes its usual once-a-second heartbeat.
The car map smooths movement between fixes using speed and heading for at most
2.5 seconds, then holds the position until another fix arrives or the hold expires.
Stationary phones retain the full 10-second allowance without predicted movement.

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
| Galaxy HTML/CSS/JS used over Bluetooth | No: the app downloads these pages from comma over Wi-Fi/LAN (see below) |
| Galaxy HTML/CSS/JS used over Wi-Fi/LAN | No: screens load from comma |
| Comma-side Python/services/API changes only | No, unless the phone protocol also needs a change |

### Galaxy screens over Bluetooth

Neither app bundles Galaxy's pages. Bluetooth Galaxy shows a copy the app saved from comma, so **connect to comma over
Wi-Fi/LAN once** before using Bluetooth. Until then the Bluetooth route says it needs one Wi-Fi visit.

- Whenever the phone reaches comma over Wi-Fi/LAN (and from **Refresh Galaxy screens** in the menu), the app reads
  `GET /api/companion/web-manifest`, which lists every file in `galaxy/web` with its SHA-256 and comma's commit. It downloads
  only the files that changed, verifies each hash, and keeps the old copy if anything fails.
- The pages come from comma itself, so custom and unpushed branches work and nothing depends on GitHub.
- If comma updated since the last Wi-Fi visit, Bluetooth still opens the saved copy and says it is from an older comma build.
  Join comma's Wi-Fi to refresh.
- A comma without the manifest route is too old to share its screens; update comma.

### Handing the signing key to another developer

Updates install over an existing app only when signed with the same `companion.jks`; a different key forces every user to
uninstall first. To pass signing on, copy `~/.starpilot/companion.jks` and `~/.starpilot/companion-signing-password` to the
new developer over a private channel (a password manager share, not git or chat), or have them point `COMPANION_KEYSTORE`
and `COMPANION_PASSWORD_FILE` at wherever the files live. Keep a backup: losing the key means a forced reinstall.

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
