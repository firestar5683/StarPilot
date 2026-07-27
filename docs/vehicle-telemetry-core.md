# EV Vehicle Telemetry core

The `system.vehicle_telemetry` package turns generic `CarState` energy fields
into a small authenticated snapshot without participating in vehicle control or
writing CAN traffic. It is designed to run unchanged on stock openpilot and on
forks that provide an adapter for a different cereal source.

The daemon and network transports require the host SOM to remain powered. A fork
may retain a validated snapshot across shutdown, but live telemetry is unavailable
while the host, message bus, or network is off; a separately resident vehicle
interface MCU does not keep this Python service running.

The daemon is always available—including while the vehicle is onroad—but defaults
to `off`: it keeps the latest valid
snapshot locally and exposes nothing on the network until configured. Custom
backend sending is independent and can also be enabled alongside any fetch mode.

StarPilot registers its adapter daemon with `system/manager/process_config.py`.
On stock openpilot, run the fork-neutral daemon directly with:

```sh
python3 -m openpilot.system.vehicle_telemetry.daemon
```

For automatic startup, add the following alongside the other always-running
Python processes in the target fork's manager configuration:

```python
PythonProcess("vehicle_telemetryd", "system.vehicle_telemetry.daemon", always_run, nice=19),
```

## Modes

| Mode | HTTP owner | Intended use |
| --- | --- | --- |
| `off` | none | Cache only |
| `send` | none | Outbound-only HTTPS delivery to a custom backend |
| `local` | telemetry daemon | Bearer-authenticated LAN fetch |
| `tailscale` | telemetry daemon + personal Tailscale Funnel | Stable public HTTPS URL owned by the device owner |
| `frp` | telemetry daemon + `frpc` | Stable authenticated remote URL through an FRP gateway |
| `galaxy` | fork adapter | A fork-owned portal serves and configures telemetry |

The stock configuration lives at
`/data/vehicle_telemetry/vehicle_telemetry_config.json` and must be owned by the
daemon user with mode `0600`. Set `OPENPILOT_VEHICLE_TELEMETRY_DIR` to override
the directory for development.

```json
{
  "schemaVersion": 1,
  "mode": "local",
  "fetch": {
    "enabled": true,
    "token": "replace-with-at-least-32-random-characters",
    "bindAddress": "0.0.0.0",
    "port": 7766
  },
  "push": {
    "enabled": false,
    "url": "https://telemetry.example/v1/ingest",
    "token": "replace-with-a-different-32-character-token",
    "vehicleId": "my-vehicle",
    "vehicleName": "My vehicle",
    "drivingIntervalSeconds": 60,
    "chargingIntervalSeconds": 120,
    "parkedIntervalSeconds": 900
  }
}
```

Fetch endpoints are `GET /api/vehicle/telemetry` and
`GET /api/vehicle/telemetry/status`. Both require
`Authorization: Bearer <token>`. `GET /health` discloses no vehicle data and is
available for local process checks. The authenticated, read-only API remains
available onroad; only the temporary setup page is parked/offroad-only.

## Custom backend sending

Choose **Custom backend** in the temporary setup page for outbound-only sending,
or configure the `push` object alongside any API mode. The explicit send-only
shape is:

```json
{
  "schemaVersion": 1,
  "mode": "send",
  "fetch": {"enabled": false},
  "push": {
    "enabled": true,
    "url": "https://telemetry.example/v1/ingest",
    "token": "replace-with-at-least-32-random-characters",
    "vehicleId": "my-vehicle",
    "vehicleName": "My EV",
    "maximumBatteryCapacityKilowattHours": 99.8,
    "drivingIntervalSeconds": 60,
    "chargingIntervalSeconds": 120,
    "parkedIntervalSeconds": 900
  }
}
```

The backend contract is intentionally small:

- accept `POST` over HTTPS at the configured URL;
- require `Authorization: Bearer <token>` and `Content-Type: application/json`;
- accept the versioned JSON envelope below and ignore fields it does not need;
- return any `2xx` status after accepting the event; redirects are not followed;
- tolerate a duplicate event after an ambiguous network failure, preferably by
  deduplicating on `vehicleId` plus `sentAt`.

```json
{
  "schemaVersion": 1,
  "vehicleId": "my-vehicle",
  "sentAt": 1784235068410,
  "telemetry": {
    "schemaVersion": 1,
    "source": "openpilot carState",
    "updatedAt": 1784235068.41,
    "vehicleFingerprint": "KIA EV9 2024",
    "stateOfChargePercent": 77.5,
    "distanceToEmptyKilometers": 408.0,
    "isCharging": true,
    "isPluggedIn": true,
    "minutesToFull": 300,
    "speedMetersPerSecond": 0.0,
    "standstill": true,
    "vehicleName": "My EV",
    "maximumBatteryCapacityKilowattHours": 99.8
  }
}
```

Optional or unavailable telemetry fields may be absent. `sentAt` is Unix time in
milliseconds; `updatedAt` is Unix time in seconds for the underlying sample. The
sender posts immediately on startup and activity transitions, then uses the
configured driving, charging, or parked interval. Failed deliveries use bounded
exponential backoff up to five minutes. Each request uses three-second connect
and five-second response timeouts, closes the response, follows no redirects,
and never places the token in the JSON body or status file. No inbound port,
listener, DNS record, or relay is needed in `send` mode.

The reference cache uses a 10-second unchanged-value heartbeat so a freshly observed
sample remains inside the 15-second `live` contract. These live-cache writes are
atomic but intentionally skip `fsync`. A structurally valid cache can be retained
before wall-clock synchronization, but it is not published until the synchronized
clock proves that its timestamp is neither future-dated nor older than 30 days;
normal storage and serving never relax that timestamp check.

## Use with RangeBridge

[RangeBridge](https://github.com/LowkeyNEXT/RangeBridge) can read the core API
directly; a Galaxy server or shared relay is not required. Perform the initial
credential handoff while the phone and comma are on the same Wi-Fi:

1. Open the temporary setup QR and choose **Tailscale** or **This Wi-Fi only**.
2. Finish the owner login/Funnel approval when using Tailscale, then copy the
   displayed API URL and generated fetch token.
3. In **RangeBridge → Vehicle Data → Connections → StarPilot Galaxy → Manual**,
   enter the base URL without `/api/vehicle/telemetry` and the bearer token.
4. For local mode, use **LAN URL** such as `http://192.168.1.50:7766`. For
   Tailscale Funnel, use **Portal URL** such as
   `https://ev-telemetry.example-tailnet.ts.net`. Leave cookie and session token
   blank; the bearer token is sufficient.
5. Select **Connect / Refresh**. RangeBridge automatically tries the stable
   `/api/vehicle/telemetry` compatibility path and stores the credential in the
   iOS Keychain.

The token is obtained only from the temporary LAN setup page. After pairing,
RangeBridge can fetch through the public Tailscale URL while the comma is onroad;
the API remains read-only and bearer-authenticated. Rotate the token from setup
if a phone or copied credential is lost.

The same endpoint can be checked before configuring RangeBridge:

```sh
curl -H "Authorization: Bearer FETCH_TOKEN" \
  https://your-device.your-tailnet.ts.net/api/vehicle/telemetry
```

## Recommended public mode: personal Tailscale Funnel

`tailscale` is the easiest public mode and requires no shared StarPilot relay,
inbound port forwarding, custom DNS, or maintainer account. Each device owner
signs the comma into their own free Tailscale account and approves Funnel once.
The daemon then restores the persistent Funnel automatically after restarts and
derives its stable `https://<device>.<tailnet>.ts.net` URL from Tailscale.

On stock openpilot, after registering the low-priority daemon as shown above:

```sh
# Downloads the official static package, verifies its published SHA-256, creates
# an owner-only identity, enables loopback fetch, and prints a new fetch token once.
python3 -m openpilot.system.vehicle_telemetry.tailscale enable

# Run after the daemon reports that it is ready, then open the returned ownerURL.
python3 -m openpilot.system.vehicle_telemetry.tailscale login

# Inspect setup/Funnel state or disable only the telemetry-managed Funnel.
python3 -m openpilot.system.vehicle_telemetry.tailscale status
python3 -m openpilot.system.vehicle_telemetry.tailscale disable
```

The initial owner login and first Funnel policy approval are intentionally
interactive security boundaries; they cannot be silently pre-approved by the
device. Everything after those approvals is autonomous. Funnel provides TLS and
hides the comma's public IP, but normal tailnet ACLs do not authenticate public
Funnel callers. The telemetry bearer token remains mandatory application-level
authorization and should be paired or copied only over the LAN.

The dedicated `tailscaled` uses userspace networking and runs at nice level 19.
It explicitly disables Tailscale SSH, route acceptance, and DNS changes; Funnel
maps only HTTPS port 443 to the loopback telemetry API, never port 22 or Galaxy.
The public API is GET-only and cache-only: it never reads CAN or calls controls.
It has four fixed worker slots, a four-connection listen queue, three-second
socket timeouts, 2 KiB request-line and 8 KiB/32-count header limits, a global
two-request-per-second token bucket with burst eight, a stricter failed-login
bucket, and one-second disk-read caching. Overload receives `503` without
creating another handler thread. This gives abusive traffic fixed local work and
memory bounds; public exposure can never guarantee zero resource use.

## Temporary LAN setup page

The portable core includes a dependency-free setup page for devices without a
fork-specific configuration UI:

```sh
python3 -m openpilot.system.vehicle_telemetry.setup launch
```

The launcher selects a private Wi-Fi/Ethernet address and starts a nice-level-19
standard-library HTTP process. It refuses cellular and public interface
addresses and refuses to start while the vehicle is onroad. The command reports
only non-secret host/port/status metadata; native comma UI reads the complete QR
target from the owner-only session record instead of exposing it to stdout.
The page offers the four common choices—personal Tailscale relay, custom backend
sending, local-only access, and cache-only/off—and can generate or rotate the owner fetch token.
FRP and hosted fork modes remain advanced configuration options.

The session closes after ten minutes, when **Finish** is pressed, or when the
vehicle goes onroad. It has two worker slots, three-second socket timeouts,
bounded headers and 16 KiB request bodies, fixed-memory rate limiting, and no
external scripts, fonts, images, analytics, or CDN requests. A random 256-bit
secret in the QR/URL authorizes the session; it is passed to the child over a
pipe rather than process arguments. The first valid request moves that capability
into a short-lived HttpOnly, SameSite cookie, and the page source contains no
copy of it. The page immediately removes the query from browser history, uses a
strict Content Security Policy, and writes its temporary launch record owner-only
with mode `0600` inside a `0700` directory.

Treat the initial local setup as a trusted-LAN ceremony: its temporary page uses
plain HTTP so a phone can open it without certificate warnings. Do not perform
setup on public or untrusted Wi-Fi. Once configured, Tailscale/FRP access and
custom-backend delivery use HTTPS, and the reusable credentials remain in
owner-only files and redacted API responses.

Python-based comma UIs can display a QR immediately with:

```python
from openpilot.system.vehicle_telemetry.setup import launch_vehicle_telemetry_setup

session = launch_vehicle_telemetry_setup()
show_qr(session["url"])
```

C++/Qt UIs can run the short-lived `launch` command and read the owner-only
`telemetry_setup_session.json` record from the telemetry data directory. The
web server itself exits independently, so dismissing the QR does not leave an
always-running UI framework.

## FRP mode

FRP mode binds the local API to loopback, writes an owner-only generated client
configuration, and supervises an externally installed `frpc` executable. It
creates a random persistent subdomain when `subdomain` is `auto`, so the public
URL remains stable across reboots without exposing the dongle ID or VIN.

```json
{
  "schemaVersion": 1,
  "mode": "frp",
  "fetch": {
    "enabled": true,
    "token": "replace-with-at-least-32-random-characters",
    "port": 7766
  },
  "tunnel": {
    "provider": "frp",
    "binaryPath": "/data/vehicle_telemetry/bin/frpc",
    "serverAddress": "example.com",
    "serverPort": 7000,
    "token": "replace-with-the-gateway-frp-token",
    "subdomainHost": "example.com",
    "subdomain": "auto",
    "trustedCaFile": "/data/vehicle_telemetry/gateway-ca.crt",
    "serverName": "example.com"
  }
}
```

FRP's server must use the matching `subdomainHost` and wildcard DNS. The public
URL becomes `https://vt-<random>.example.com/api/vehicle/telemetry`. Bearer
authorization still applies after the tunnel.

The repository also includes an optional gateway helper:

```sh
python3 -m openpilot.system.vehicle_telemetry.gateway \
  /etc/vehicle-telemetry/gateway.json \
  --output-dir /var/lib/vehicle-telemetry
```

It runs on an Internet-reachable Linux gateway, never on the comma. The helper
generates `frps` configuration and uses a scoped Cloudflare API token to maintain
two A records: an apex DNS-only record for the FRP control channel, and a proxied
wildcard record for public HTTPS. For coverage by free Universal SSL, dedicate a
zone and set `subdomainHost` to that zone apex. The Cloudflare token needs only
DNS edit permission for that zone.

```json
{
  "frp": {
    "binaryPath": "/usr/local/bin/frps",
    "bindPort": 7000,
    "vhostHTTPPort": 80,
    "subdomainHost": "example.com",
    "token": "replace-with-at-least-32-random-characters",
    "certFile": "/etc/vehicle-telemetry/frps.crt",
    "keyFile": "/etc/vehicle-telemetry/frps.key"
  },
  "dns": {
    "zoneId": "cloudflare-zone-id",
    "zoneName": "example.com",
    "apiToken": "scoped-cloudflare-dns-token",
    "address": "auto",
    "refreshSeconds": 300
  }
}
```

FRP transport TLS and server identity verification are required. Configure an
FRP server certificate, place its issuing CA in `trustedCaFile`, and set the
matching `serverName`; the client refuses to start without all three. FRP and
Cloudflare credentials never appear in telemetry
responses or status documents. The Cloudflare token is attached only to requests
whose destination is the fixed Cloudflare API; the separate public-address lookup
uses an unauthenticated session.

The helper's Cloudflare wildcard mode terminates public TLS at Cloudflare and
forwards HTTP to `vhostHTTPPort`. Use it only when that origin hop is protected
by a firewall/private link, or put `vhostHTTPPort` on loopback behind an
authenticated HTTPS origin proxy. Tailscale Funnel remains the recommended
zero-maintenance public mode because it avoids this extra gateway boundary.

## DBC and vehicle-port requirements

The transport never decodes make/model CAN messages. A supported vehicle must
decode its energy signals in opendbc and map them into the generic `CarState`
contract below. `fuelGauge`, `vEgo`, and `standstill` are broadly available;
`distanceToEmpty`, `charging`, and `chargingPortConnected` may need to be added
to the vehicle port. Unsupported or default all-zero energy values are rejected
instead of being presented as real telemetry.

At minimum, a useful port needs a valid state-of-charge or distance-to-empty
signal. For complete EV telemetry, the DBC/port needs:

| Information | Generic `CarState` field | Normalized value expected by the core | Required? |
| --- | --- | --- | --- |
| Battery state of charge | `fuelGauge` | Fraction from `0.0` to `1.0` | SOC or DTE |
| Displayed distance to empty | `distanceToEmpty` | Meters | SOC or DTE; optional schema extension on openpilot v0.11.1 |
| Actively charging | `charging` | Boolean | Recommended |
| Charge cable/port connected | `chargingPortConnected` | Boolean | Recommended; optional schema extension on openpilot v0.11.1 |
| Vehicle speed | `vEgo` | Meters per second | Cadence only |
| Standstill state | `standstill` | Boolean | Cadence only |

Each new DBC signal definition must identify the correct CAN message and bus,
start bit, bit length, byte order, signedness, factor, offset, valid range, and
unit. The vehicle `CarState` parser must also honor the message's normal
freshness rules: expected frequency, counter/rolling-counter checks, checksum,
and validity bits where the platform supplies them. Do not publish stale or
invalid frames as current battery data.

Stock openpilot v0.11.1 already exposes `fuelGauge`, `charging`, `vEgo`, and
`standstill`, so the portable core works without cereal changes when the vehicle
port fills those fields. That release does not yet define `distanceToEmpty` or
`chargingPortConnected`; a fork that wants those richer fields must add them to
its opendbc `CarState` schema (using non-conflicting field ordinals), regenerate
the cereal bindings through the normal build, and populate them in the vehicle
parser. The core uses optional attribute reads, so the exact same transport code
runs with or without those extensions.

Convert units in the vehicle port, not in this transport. Examples:

- map a DBC SOC value of `77.5 %` to `ret.fuelGauge = 0.775`;
- map a DBC range value of `408 km` to `ret.distanceToEmpty = 408000.0`;
- keep plugged-in and actively-charging separate when the vehicle exposes both;
- validate independent cluster/BMS copies of SOC or range before choosing one;
- do not infer charging merely from low speed, ignition state, or a nonzero SOC.

The core accepts partial support but requires at least one useful, nonzero energy
value. It rejects non-finite values, SOC outside `0...100%`, distance to empty
outside `0...900 km`, and the default all-zero energy shape. A vehicle port should
set a feature/availability flag when its fork-specific adapter requires one. A fork
can also expose independent SOC, DTE, charging, and plug validity flags so an absent
source is omitted rather than converted to a plausible zero/false value.

Required tests for a new port should cover raw CAN-to-DBC scaling, the final
`CarState` units, invalid/freshness behavior, charging versus plugged-in state,
and at least one realistic nonzero telemetry sample for the supported
fingerprint.

To add a vehicle:

1. Decode the make/model signals in opendbc with correct scaling and validity.
2. Populate the generic `CarState` fields in the units above.
3. Validate redundant SOC, range, and charging sources where possible.
4. Add focused DBC, freshness, and `CarState` tests.
5. Keep make/model branches out of the telemetry transport.
