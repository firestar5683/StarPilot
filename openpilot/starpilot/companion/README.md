# StarPilot companion apps

## Where things live

```
ios/                                    iPhone app (natehuby76, PR #224/#225)
openpilot/starpilot/galaxy_bluetooth/   comma-side phone bridge shared by both apps:
                                        BLE GATT server, Galaxy proxy, pairing, LAN
                                        discovery, setup supervisor, comma pairing UI
openpilot/starpilot/galaxy/companion*.py  Galaxy endpoints for the phone uplink and
                                        Wi-Fi pairing (`bluetooth_pairing`)
openpilot/starpilot/companion/          this Android app
├── android/                            Gradle project, build_apk.sh, host-side tests
├── docs/                               validation records
└── run_host_tests.py
```

Nate's `ios/` and `galaxy_bluetooth/` stay where his upstream PRs put them so his
future changes apply cleanly. Both apps speak the same BLE wire protocol and use
the same comma pairing key.

# Galaxy Android companion

Native Android shell and cellular SOCKS5 uplink, protocol 1, app 1.1.11 (versionCode 13).

Update notifications work on Android 12 and newer. Android 12 does not require a
runtime notification permission; its **App updates** channel works by default unless
disabled in system settings. On Android 13+, notifications are optional and are not
requested at first launch. Choose **Connections → Notification settings** to opt in
and receive an **App updates** pop-up when your comma has a newer APK. The app checks
when opened and after connecting, plus about every
15 minutes in the background (Android may delay background work). Checks use Galaxy
Wi-Fi or the last connected comma address on the same LAN, independently of phone
internet sharing. Bluetooth-only connections cannot download or check for APKs.
Each available version alerts once; tapping opens Galaxy's update page, where
**Update app** downloads directly inside StarPilot and opens Android's normal
installation confirmation without launching a browser. The first in-app update may
open Android's **Install unknown apps** setting once; allow StarPilot and return to
resume automatically. Apps older than 1.1.10 use the previous browser handoff once
to install a current release; later updates stay in StarPilot.
The same option opens Android settings if permission was previously denied, or lets
you change the App updates channel's sound and pop-up behavior.
Wi-Fi/LAN loads live Galaxy screens from comma. Bluetooth uses screens bundled
in the APK, so Bluetooth screen changes require rebuilding/updating the APK. This directory and the Galaxy changes are source implementation plus a
signed release artifact; physical phone/comma/in-car acceptance is still required.
Screen rotation is handled in the existing activity so it resizes the UI without
destroying the authenticated Bluetooth session or reloading the current page.

## Use

1. Enable the existing Galaxy hotspot, and join `TheGalaxy-XXXX` on Android.
2. Open Galaxy → **Galaxy Access & Install** → **Android companion**. Download
   the APK locally, allow that browser to install unknown apps, and install it.
   The QR code opens `http://172.31.254.1:8082/app.apk` without requiring an
   existing browser cookie. APK downloads are blocked on the tunnel server.
3. Open StarPilot and enable **Phone internet**. Both the comma setting and the
   phone preference start disabled. Keep mobile data enabled. The phone must
   have a validated cellular network; outbound sockets never use the Wi-Fi
   process binding or the Galaxy remote tunnel.
4. Sharing continues in a foreground service with a Stop notification action.
   **Resume sharing after phone restart** is separately opt-in, defaults off,
   and keeps the foreground service waiting for Galaxy Wi-Fi after reboot.
5. Share a Google Maps place to StarPilot, or open a `geo:`/`google.navigation:`
   URI. Short-link expansion uses cellular and a bounded Google-host redirect
   allowlist. The live Galaxy navigation page parses and selects the destination
   with the existing revision-checked API.

The fallback screen accepts numeric RFC1918 LAN addresses on port 8082. This is
for viewing Galaxy; internet sharing is restricted to `172.31.254.0/24` and the
SOCKS listener accepts only the gateway `172.31.254.1`. The WebView bridge is
never available to remote pages or cross-origin frames/resources.

## Bluetooth and LAN connections

Use the **Connections** button at the top of the Android app:

- **Automatic** always checks Wi-Fi before Bluetooth. It asks the saved Galaxy Wi-Fi
  or LAN address for a short authenticated acknowledgement before opening the page.
  If a saved LAN address does not answer, it searches the current network. With a
  saved Bluetooth pairing, that automatic discovery gets a 2.5-second head start
  before Bluetooth; without a pairing, it continues searching for up to 12 seconds.
  A resolved LAN service opens after a brief 500 ms window for other commas. It
  connects automatically when one comma is found and offers a picker when
  several are found. If no Wi-Fi or LAN device is available, or you cancel the
  picker while disconnected, it tries a saved Bluetooth pairing.
- **Wi-Fi & LAN** loads live pages from comma over HTTP port 8082.
- **Bluetooth** loads bundled pages and sends bounded API requests over BLE.
- **Find comma on this network** discovers `_sp-galaxy._tcp.` for 12 seconds and
  lets you choose an address. The disconnected screen also has a **Find comma
  on LAN** button. Manual RFC1918 IPv4 entry remains available when
  multicast is blocked. Use a trusted LAN; HTTP/mDNS is not TLS.

Interrupted searches resume after returning from Wi-Fi settings or another app.
A disconnected screen reconnects on return. Automatic-search failures appear
inline; explicit manual searches retain their result dialogs. Tapping any route
on the connection screen cancels the previous Wi-Fi, discovery, or Bluetooth
attempt before starting the selected one.

This selects a connection without replaying in-flight requests. Switch modes
using Connections if an established connection drops. A failed settings change
may already have applied; check its result before retrying. BLE requests are
serialized, capped at 1 MiB body / 2 MiB frame, and never automatically retried.
Canceled queued work is removed; canceling an already-sent mutation cannot undo it.

Bluetooth supports small settings, status and destination requests. Camera
images, recordings, replay, APK transfer, map tiles and large/continuous transfers need
Wi-Fi/LAN. The system monitor retains its short freshness limit and may show
unavailable on a slow BLE link. Bluetooth does **not** provide phone internet;
that feature still requires the Galaxy hotspot. Internet-dependent navigation
searches need an internet connection on comma.

Bluetooth-only limitations appear in blue information boxes with a Bluetooth
icon and a **Connection options** button. Recordings/replay, recorded-drive
analysis, camera previews, motion-event images, map previews, package transfers,
log downloads and phone internet explain that they require Wi-Fi/LAN. Supported
settings and destination controls remain available, and genuine failures keep
their normal error styling. Blocked recording and camera requests do not poll
or repeatedly retry. These screens require APK 1.1.6 or newer over Bluetooth.

### Automatic comma setup

The manager's `galaxy_phone` process (`openpilot.starpilot.galaxy_bluetooth.bootstrap`)
owns the phone bridge for both Android and iPhone. While parked with internet it
installs the pinned `dbus-next`, PyCryptodome and Zeroconf into
`/data/galaxy-ble/venv` using AGNOS's `uv`, then starts the BLE bridge and LAN
discovery as runtime systemd units. Setup never downloads over a phone's shared
internet; it waits for sharing to stop. Status appears in comma Settings →
Bluetooth, and the log is `/data/galaxy-ble/setup.log`. Bluetooth stays off unless
it is enabled in comma settings; LAN discovery runs either way.

The bridge proxies requests to the local Galaxy server with a per-BLE-session
Galaxy cookie and loopback Origin, so Galaxy's normal authentication and
parked-only checks still apply. Pairing credentials, the phone uplink, APK
downloads, recordings, replay, cameras, map tiles and Android Auto uploads are
refused over Bluetooth and require Wi-Fi/LAN.

LAN discovery advertises `_sp-galaxy._tcp` and publishes each interface's own
address separately, so home Wi-Fi clients are not given the comma hotspot
address. Registration failures, including Zeroconf-specific exceptions, are
cleaned up and retried. Android keeps multicast enabled during the bounded
foreground search, resolves services in sequence, and displays discovery errors.
Android 13+ searches the selected Wi-Fi network explicitly.

Once paired, Android remembers the last authenticated BLE address and tries it for
four seconds before falling back to a normal low-latency scan.

1. Enable Bluetooth in comma settings. Park and join Galaxy Wi-Fi, or connect to
   comma over a trusted LAN.
2. Choose **Connections → Pair over Wi-Fi**. This obtains the
   existing key without rotating it. The endpoint requires a local session,
   same-origin POST and the existing parked check.
3. Choose **Connections → Bluetooth**, grant Nearby Devices permission, and connect.
   Android 8–11 requires location permission for foreground BLE discovery;
   Android 12+ uses Scan/Connect with `neverForLocation`.
4. An existing `galaxy-bluetooth` version-1 JSON code or its 64-character hex key
   can also be pasted. Treat it as a credential. Android encrypts it using an
   Android Keystore key; the key is not exposed to the WebView.
5. **Forget pairing on this phone** deletes only this phone's copy.
   **Revoke all paired phones** explicitly rotates the shared key over
   Wi-Fi/LAN while parked, disconnecting all clients, including existing iPhones.

The pairing file remains `/data/galaxy-ble/pairing.json`, compatible with upstream.
No pairing files, secrets or Bluetooth bonds are committed.

### Shared phone bridge

The comma-side bridge and the iPhone app are natehuby76's SecretGood port
([PR #224](https://github.com/firestar5683/StarPilot/pull/224), docs as in
[PR #225](https://github.com/firestar5683/StarPilot/pull/225)), imported as his
commits. This branch adds the Android-specific Wi-Fi-only paths, per-interface LAN
advertising and the phone-sharing install pause to it; keep those when taking
his later updates. `android/tests/test_ble_wire_vectors.py` checks that the
bridge decodes the same frames as the Android JVM test fixtures.

### Bluetooth verification and device acceptance

Host tests cover Python↔JVM AES-GCM vectors, compressed/compact replies,
fragmentation at payload sizes 20/180/512, tampering/direction/sequence rejection,
upstream replay/notification tests, pairing authorization and source preservation.
JavaScript tests check POST bytes, cancellation, HTTP errors and no replay.
The release is built with lint and the existing signing identity.

Physical acceptance is still required on Android 8–11 and 12+, comma 3X/4:
BlueZ permissions/discovery, connect/reconnect/background, multiple nearby commas,
key rotation with an existing iPhone, LAN discovery on real routers, Wi-Fi loss
during a save, and concurrent cellular sharing. The app authenticates the BLE
challenge before showing controls. It currently tries the first matching
advertiser, so keep only the intended comma nearby for initial hardware testing.
No device has been deployed or flashed here.

References: [Android Bluetooth permissions](https://developer.android.com/develop/connectivity/bluetooth/bt-permissions),
[BluetoothGatt](https://developer.android.com/reference/android/bluetooth/BluetoothGatt).

## Build and signing

Toolchain: JDK 17 or newer (validated with Android Studio's bundled JBR), Android
SDK platform 37, target SDK 35, min SDK 26, Android Gradle Plugin 9.4.1, and
Gradle 9.6.0. The wrapper distribution checksum is pinned. No third-party UI
framework is used. JUnit is a test-only dependency.

From the repository root:

```sh
openpilot/starpilot/companion/android/build_apk.sh
```

The script runs `assembleRelease lintRelease`, then copies the signed APK and
version to `openpilot/starpilot/galaxy/bin/starpilot-companion.apk{,.version}`.
Set `JAVA_HOME` and `ANDROID_HOME` for nonstandard installations. Signing uses
`COMPANION_KEYSTORE` (default `~/.starpilot/companion.jks`), alias `companion`,
and `COMPANION_KEY_PASSWORD` or the local password file
`~/.starpilot/companion-signing-password`. The script never invents a replacement
key. Increment versionCode/versionName for subsequent releases.

The initial local release key was generated during implementation. **Back up
both local signing files securely.** Neither is in this repository; losing the
key prevents updates over the installed app. Certificate SHA-256:

```
d9e72cbb842e9530b4b686dec424cdeb8f2982109be6875fa73594c33332fc3a
```

To create a key for a separate distribution, generate a strong password outside
the repository and use `keytool -genkeypair -alias companion -keyalg RSA
-keysize 4096 -validity 10000 -keystore <private-path>`. Let keytool prompt for
passwords; do not put secrets into command history. Set the corresponding
signing environment variables before building. This produces a different app
signing identity and cannot update the provided release in place.

## Comma routing and data guard

The manager starts `companion_uplink_daemon` only on the primary comma instance.
The root worker runs in a pipe-leased systemd unit. No modem, NetworkManager
connection profile, dnsmasq configuration, `/etc` file, Bluetooth bond or
physical-device data is changed by installing this source.

- Heartbeats: 5 seconds; phone lease: 15 seconds; root pipe lease: 8 seconds.
- Credentials: session-random, mode-0600 lease/config files, never in status JSON.
- Tunnel: `spuplink0`; mapped DNS: `198.18.0.2`, pool `198.19.0.0/16`.
- Temporary policy table **18082**, default metric **2000**, rule priorities
  **18000/18001**. The first rule preserves main-table non-default routes. The
  second selects the phone default only while no other interface passes a
  device-bound numeric TCP probe. This also handles an unusable modem whose
  default route is still installed, without deleting or changing its route.
- `resolvectl dns/domain/default-route` is per-link and runtime-only. Teardown
  reverts DNS, removes our rules/table/link, and flushes resolver caches. An
  ownership marker allows cleanup after a worker crash. Existing conflicting
  interfaces, policy rules, routing tables or mapped-DNS subnets are rejected.
- State: `/dev/shm/starpilot-companion.json` (private lease) and
  `/run/starpilot-companion/status.json` (public state, no credentials).
- Uploader and athena defer all uploads regardless of their cellular overrides;
  stream callbacks abort transfers when the phone activates. Normal/fast git
  update downloads and AGNOS streams are also gated. Offline map areas are
  explicitly classified cellular; route-corridor tiles remain allowed.

The policy default is visible with `ip -4 route show table 18082`, rather than
plain `ip route`. On a modem/Wi-Fi recovery, the worker removes the phone policy
and DNS together. Interface-bound probes establish TCP reachability, not full
application-level internet health; captive or selectively filtered networks
still need physical testing.

## Validation

See [docs/PORT_VALIDATION.md](docs/PORT_VALIDATION.md) for the SecretGoodStarPilot port,
current APK provenance, regression results, and remaining device checks.

Host Python tests deliberately stub unavailable native Params, msgq and the
longitudinal solver import. They do not write actual Params or claim device ABI
coverage. Run from the repository root (select an installed compatible Python):

```sh
uv run --python 3.12.12 --no-sync --extra testing python openpilot/starpilot/companion/run_host_tests.py
node --test openpilot/starpilot/galaxy/tests/test_companion.mjs openpilot/starpilot/galaxy/tests/test_share_destination.mjs
cd openpilot/starpilot/companion/android
./gradlew testDebugUnitTest
```

`run_host_tests.py` also accepts explicit pytest paths. Verification included
hotspot/navigation HTTP regressions and the fast-update suite. The existing
AGNOS manifest test uses native Params during fixture cleanup and cannot run
unmodified under this stub runner; AGNOS stream admission/abort is tested
independently. Native SOCKS
unit tests use real loopback TCP/UDP sockets and an injected cellular transport;
they verify authentication, domain resolution, bidirectional counting, denylist
rejection and UDP association behavior.

`android/tests/tunnel_dns_smoke.py` runs the pinned **real ARM64 binary** inside a disposable
Linux ARM64 container with `/dev/net/tun`, NET_ADMIN, Python and `iproute2`.
Mount `openpilot/starpilot/galaxy/bin` at `/b` and the test script at `/test.py`; run
`python /test.py`. It asserts A answers in the mapped pool and empty successful
AAAA answers. Do not run that script in a device or host network namespace.

Still required before device release: install on a physical Android phone,
exercise cellular CONNECT/UDP while attached to Galaxy Wi-Fi, verify resolved
and routing restoration on the comma, modem/Wi-Fi recovery, disconnect/disable
latency, real navigation and sharing, phone sleep/OEM battery behavior, and an
in-car Android Auto projection regression. No emulator/ADB device was available
in the implementation environment. No device deployment or in-car claim is made.

## Platform decisions and sources

Android network-security XML supports domain rules, not RFC1918 CIDR rules.
To retain arbitrary direct-LAN fallback, cleartext is enabled at the platform
layer and every WebView navigation/resource is restricted in application code
to the selected numeric private origin. Service HTTP is fixed to the hotspot
origin; short-link HTTP is HTTPS-only with an allowlist. This is a deliberate
adjustment to the plan's unrepresentable XML private-range allowlist.
See [Android network security configuration](https://developer.android.com/privacy-and-security/security-config).

The foreground service uses `connectedDevice` plus `CHANGE_NETWORK_STATE`, as
specified by [Android foreground service types](https://developer.android.com/develop/background-work/services/fgs/service-types#connected-device).

Tunnel source/release: [hev-socks5-tunnel 2.18.0](https://github.com/heiher/hev-socks5-tunnel/releases/tag/2.18.0).
The MIT license and binary SHA-256 are retained beside the prebuilt binary. The
container test verified JSON-as-YAML configuration and the actual mapped-DNS
behavior, rather than relying only on the config renderer unit test.
