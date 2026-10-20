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
| Galaxy HTML/CSS/JS used over Bluetooth | No, if comma's commit is on GitHub: the app downloads Galaxy from that exact commit (see below) |
| Galaxy HTML/CSS/JS used over Wi-Fi/LAN | No: screens load from comma |
| Comma-side Python/services/API changes only | No, unless the phone protocol or bundled UI also needs a change |

### Galaxy updates over Bluetooth

The app downloads Galaxy from the repository and commit comma is running, so custom branches and their own pages
work too. It learns them from `/api/software/status` (`operations.repository` and `installed.commit`), the same source the iPhone app uses, each time it connects,
and checks when it opens or you choose **Check Galaxy updates** in the menu. Files come from GitHub over the phone's own
internet, are verified against the commit's tree, and apply the next time Bluetooth Galaxy opens. If comma's remote
isn't GitHub or the commit isn't pushed, or an update fails, the app keeps its current copy. A fresh install uses the
copy bundled in the APK.

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
