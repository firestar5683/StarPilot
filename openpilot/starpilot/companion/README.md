# Galaxy Android companion

Native Android shell and cellular SOCKS5 uplink, protocol 1, app 1.1.5 (versionCode 7).
Wi-Fi/LAN loads live Galaxy screens from comma. Bluetooth uses screens bundled
in the APK, so Bluetooth screen changes require rebuilding/updating the APK. This directory and the Galaxy changes are source implementation plus a
signed release artifact; physical phone/comma/in-car acceptance is still required.

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

- **Automatic** tries Galaxy Wi-Fi or the saved LAN address first. On home Wi-Fi,
  a fresh install or failed saved address starts a 12-second LAN search. It
  connects automatically when one comma is found and offers a picker when
  several are found. If no Wi-Fi or LAN device is available, or you cancel the
  picker while disconnected, it tries a saved Bluetooth pairing.
- **Galaxy Wi-Fi / LAN only** loads live pages from comma over HTTP port 8082.
- **Bluetooth only** loads bundled pages and sends bounded API requests over BLE.
- **Find Galaxy on LAN** discovers `_sp-galaxy._tcp.` for 12 seconds and
  lets you choose an address. The disconnected screen also has a **Find comma
  on LAN** button. Manual RFC1918 IPv4 entry remains available when
  multicast is blocked. Use a trusted LAN; HTTP/mDNS is not TLS.

Interrupted searches resume after returning from Wi-Fi settings or another app.
A disconnected screen reconnects on return. Automatic-search failures appear
inline; explicit manual searches retain their result dialogs.

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

### Automatic comma setup

After the comma updates to this branch, the manager's `companion_bluetooth`
supervisor automatically prepares `/data/galaxy-ble/stardust-venv` with the pinned
`dbus-next`, PyCryptodome and Zeroconf dependencies, then starts LAN discovery.
No SSH command or Bluetooth pairing is required for LAN discovery. Keep Galaxy
enabled, leave comma parked with internet for its first setup, and install the
updated APK on Android. Both devices must be on the same trusted LAN.

The first setup may take a few minutes. Failed setup retries automatically after
60 seconds. Installation pauses if driving or phone internet sharing starts;
already installed dependencies work offline and while driving. The supervisor
checks actual imports and pinned versions before starting either bridge, and
repairs partial installations automatically. Setup logs are private and rotated
at `/data/galaxy-ble/stardust-setup.log`.
Failed environment verification also backs off for 60 seconds while driving,
so a partial installation does not repeatedly launch Python onroad.

Once paired, the supervisor also starts the BLE adapter and retries if Bluetooth
is off or BlueZ is not ready. It does not change Bluetooth power/bonds, pairing
keys, or the other fork's venv or systemd units. Do not run two Galaxy GATT bridge
services at once. `install_bluetooth.sh` remains an internal setup helper; users
do not need to run it. Automatic setup has been tested on the host, not deployed
to the physical comma here.

AGNOS setup uses its existing `uv` binary and installed Python; it does not
require system `pip` or `ensurepip`, or download another Python installation.
Installation requires prebuilt wheels and never starts a source build. The
pinned Zeroconf 0.151.3 and PyCryptodome 3.23.0 releases publish compatible ARM64
wheels for the comma's Python 3.12 and glibc 2.39. Registration failures,
including Zeroconf-specific exceptions, are cleaned up and retried by the
advertiser without a process restart.

The branch LAN adapter corrects upstream's invalid 16-character DNS-SD service
name and advertises each interface's address separately, so home Wi-Fi clients
are not given the comma hotspot address. Imported upstream implementation files
and their provenance hashes remain unchanged. Android keeps multicast enabled
during the bounded foreground search, resolves services in sequence, and displays
discovery errors. Android 13+ searches the selected Wi-Fi network explicitly.

1. Enable Bluetooth in comma settings. Park and join Galaxy Wi-Fi, or connect to
   comma over a trusted LAN.
2. Choose **Connections → Pair Bluetooth using Wi-Fi / LAN**. This obtains the
   existing key without rotating it. The endpoint requires a local session,
   same-origin POST and the existing parked check.
3. Choose **Bluetooth only**, grant Nearby Devices permission, and connect.
   Android 8–11 requires location permission for foreground BLE discovery;
   Android 12+ uses Scan/Connect with `neverForLocation`.
4. An existing `galaxy-bluetooth` version-1 JSON code or its 64-character hex key
   can also be pasted. Treat it as a credential. Android encrypts it using an
   Android Keystore key; the key is not exposed to the WebView.
5. **Forget Bluetooth on this phone** deletes only this phone's copy.
   **Revoke all paired phones on comma** explicitly rotates the shared key over
   Wi-Fi/LAN while parked, disconnecting all clients, including existing iPhones.

The pairing file remains `/data/galaxy-ble/pairing.json`, compatible with upstream.
No pairing files, secrets or Bluetooth bonds are committed.

### Preserve the other implementation

`upstream/tools/galaxy_bluetooth/` preserves implementation code from
[`firestar5683/StarPilot`, branch `galaxybt`](https://github.com/firestar5683/StarPilot/commits/galaxybt/).
`upstream/SOURCE.json` pins its exact commit and every source blob hash. It includes
the original iOS project, bridge, docs, license and tests. At the user’s request,
the imported web logos/favicons now use the existing StarPilot assets. These
branding-only replacements and the refreshed asset manifest are explicitly
recorded in `branding_overrides`; original upstream hashes remain available. Branch adaptations are
outside it in `bluetooth.py` and the Android project. The other developer's branch
was not modified or pushed.

The iOS implementation code is preserved as supplied, not rebuilt or retrofitted to this
branch's different Galaxy API/UI. Android and the branch adapter share its BLE
wire protocol. The adapter supplies per-BLE-session Galaxy cookies and loopback
Origin while retaining normal endpoint checks; upstream's old API auth
assumptions are not copied into Galaxy.

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
openpilot/starpilot/companion/build_apk.sh
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

See [PORT_VALIDATION.md](PORT_VALIDATION.md) for the SecretGoodStarPilot port,
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

`tests/tunnel_dns_smoke.py` runs the pinned **real ARM64 binary** inside a disposable
Linux ARM64 container with `/dev/net/tun`, NET_ADMIN, Python and `iproute2`.
Mount `../galaxy/bin` at `/b` and the test script at `/test.py`; run
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
