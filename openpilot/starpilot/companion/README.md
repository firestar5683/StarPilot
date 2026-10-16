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
- `openpilot/starpilot/galaxy/companion*.py` — phone internet sharing and
  Wi-Fi pairing endpoints.

Over Bluetooth, pairing, phone internet sharing, APK downloads, recordings,
replay, cameras and map tiles are blocked; they need Wi-Fi.

## Android

Install: join the Galaxy hotspot, open Galaxy → **Galaxy Access & Install** →
**Android companion**, and install the APK. Later updates install from inside
the app.

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
