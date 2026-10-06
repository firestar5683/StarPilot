# Galaxy companion

Galaxy is StarPilot's Vue browser interface for device status, saved preferences,
and local tools. The managed service listens on port 8082. On the device's local
network, open the address and QR code shown by the native Galaxy page. Direct
local connections establish a browser session automatically. Remote or proxied
connections use the existing password-backed session; account pairing and a
managed remote tunnel are not available.

## Run and test

`./dev galaxy` starts a desktop server on loopback. The Python entry point is
`python -m openpilot.starpilot.galaxy.server`; its default host is `127.0.0.1`.
Use `--host 0.0.0.0` only when a LAN bind is intended. The managed service is
selected by the manager and can be disabled with `STARPILOT_GALAXY_DISABLE=1`
in the manager environment. A manual server cannot share its port with the
managed service. Static browser files are under `web/`, with no JavaScript
package installation required.

For frontend or backend work, `./dev galaxy --live [--port N]` builds the shared
host cache, releases its lock so `./c3`, `./c4` and `./onroad` can run alongside,
then follows edits under this package. An open page reloads itself after each
edit; other changes here restart the server first. Refresh a page opened before
the session once. Edits outside the package need `./dev sync` and a restart.
The reload script exists only in the host cache, never in this directory.
Add `--no-autoreload` to keep following edits but refresh by hand.

Run the package tests with `./dev pytest openpilot/starpilot/galaxy/tests`.
Browser JavaScript tests use Node 24; set `STARPILOT_NODE` to an existing Node
24 executable when needed. A static preview can serve `web/` over loopback;
it labels its sample System Monitor data and cannot edit a device.

## Pages and owners

| Page | Current source and operations |
| --- | --- |
| Home and Tools | Local status cards, navigation, theme, drawer, pinned tiles, and hash routes. |
| System Monitor and Plots | Bounded local process/device and driving-message samples. Unavailable data stays unknown; leaving a page stops its polling. |
| Logs and Recordings | Current crash-report previews, closed local segment inventory, one-segment summary, and Quick road playback from a closed `qcamera.ts`. |
| Software & Updates | Read-only installed and updater status. Refresh rereads reported Params; it does not check, download, switch branches, install, roll back, or reboot. |
| Driving and Device Preferences | Saved settings through typed owners shared with native controls, including SLC, lateral and longitudinal tuning, conditional modes, display, cameras, and sounds. |
| Vehicle Controls | One saved manual vehicle choice for the next start, or Auto for normal detection. |
| Models and Model Laboratory | Verified model catalog management and parked Laboratory configuration. Paired inference is unavailable in the production model runner. |
| Bluetooth | Local BlueZ adapter and device operations, including pairing confirmation. Bluetooth audio routing is unavailable. |
| Maps | Local map status and a parked catalog-region download, progress, or cancellation. A completed selection takes effect at the next map service start. |
| Cameras and Sentry | Saved PiP and V-ASM settings and bounded Sentry event metadata. The crop editor uses a browser-local still image; it does not upload that image. |
| Sound packs | Catalog status, verified download and cancellation through the local sound owner. |

The Vue router in `web/js/app.js` and the route handlers in `server.py` are the
current route map. API groups include `/api/auth`, `/api/system/monitor`,
`/api/software/status`, `/api/settings`, `/api/models`, `/api/maps`,
`/api/sounds`, `/api/bluetooth`, `/api/vehicle-selection`, `/api/recordings`,
`/api/sentry/events`, and `/api/flm`. An unknown API route returns an error;
there is no arbitrary Params or shell-command endpoint.

## Access and operation rules

The server requires the actual peer and socket destination to be local for
passwordless access. Proxy headers select the password-backed path. The Host
must match the destination address, and JSON writes require that same origin.
Sessions use opaque HttpOnly, SameSite=Strict cookies; a local session cannot
authorize a remote request. A session is checked again after slower reads and
before sensitive results are returned. The server bounds connections, request
bodies, file reads, and operation concurrency.

Saved-setting writes use an authenticated preview/confirm transaction. Their
owners recheck current saved-source identity, vehicle eligibility, and fresh
offroad evidence before committing. A saved choice is not proof that a driving
feature is active. Map, model, Bluetooth, sound, and other operations each have
their own authority checks; browser text is never a command to execute. A lost
save response has an unknown outcome: refresh before repeating an action.

Status endpoints distinguish missing, invalid, stale, or changed inputs from
valid zero values. Crash and recording readers recheck file identity and skip
active or symlinked sources. Quick road media is prepared from one closed
segment in a bounded temporary cache, then served to the authenticated same
origin; it is removed when Galaxy stops. Plots and System Monitor stop or retire
requests when hidden, signed out, expired, or superseded. Sample rates and
message ages describe observed data, not driving-control timing.

Galaxy does not provide cloud drive history, full-resolution multi-camera
recording playback, remote account setup, or updater actions. See
[model contracts](../models/README.md) for Laboratory runtime eligibility and
[map operations](../maps/MAP_OPERATIONS.md) for offline-region ownership.

## Source and notices

The UI adapts StarPilot's earlier Vue Galaxy design; the adapted StarPilot
source remains under the repository [LICENSE](../../../LICENSE). The bundled
Vue and Bootstrap Icons assets retain their respective MIT notices in
`web/vendor/notices/`. Other asset notices remain beside their files.
