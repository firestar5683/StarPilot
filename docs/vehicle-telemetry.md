# StarPilot EV Vehicle Telemetry

StarPilot uses the fork-neutral [`system.vehicle_telemetry`](vehicle-telemetry-core.md)
service to expose and/or publish a small normalized vehicle-energy snapshot. Onroad,
the adapter consumes `starpilotCarState`, avoiding a second reader on the primary
`carState` socket. Explicitly offroad, it can consume the already-derived
`pandaStates.ev9VehicleTelemetry` snapshot produced inside pandad's existing sole
Panda/CAN receive loop. `vehicle_telemetryd` itself opens neither raw CAN nor Panda,
never writes CAN traffic, and remains independent of controls.

Its complete subscription set is `starpilotCarState`, `pandaStates`, `carParams`,
and `deviceState`. `deviceState.started` selects exactly one source: onroad never
uses the PandaState fallback, and offroad never refreshes from stale car state.

Normal onroad vehicle decoding belongs in opendbc and the vehicle port. Route-backed
classic-CAN Ioniq/Kona platforms publish DTE, while the validated Hyundai/Kia/Genesis
CAN-FD EV allowlist publishes SOC and DTE. The EV9-only offroad fallback is the narrow
exception: pandad passively derives four energy frames it already receives, then
publishes only normalized, validity-stamped fields. The transport layer still only
validates, caches, and moves normalized values.

## Normalized fields

The daemon currently consumes:

- `fuelGauge` as state of charge (`0.0...1.0`)
- `distanceToEmpty` in meters
- `charging`
- `chargingPortConnected`
- optional `chargingTimeRemaining` in seconds, exposed as whole `minutesToFull`
- `vEgo` and `standstill` for upload cadence

At least one useful energy value is required. Default all-zero `CarState` values,
non-finite numbers, SOC outside `0...100%`, and DTE outside `0...900 km` are not
published as valid telemetry.

The shared CAN-FD path publishes route-validated SOC and range. EV9 additionally
publishes plug and active-charging state only when its redundant sources agree. Its
four inputs run at 10 Hz; samples older than 500 ms and redundant sources more than
150 ms apart are invalid. The daemon additionally requires an advancing source
monotonic timestamp no older than one second and an updated, alive, valid source
message. Candidate 0x2FA charge-time bytes remain intentionally unassigned, so
`minutesToFull` is omitted until another capture validates that signal.

## Persistent cache

The latest valid snapshot is atomically written to:

```text
/data/galaxy/vehicle_telemetry_latest.json
```

The directory is owner-only (`0700`) and files are owner-only (`0600`). Unchanged
values use a 10-second cache heartbeat, below the 15-second `live` window with margin
for the 1 Hz producer and API read cache. Writes are atomic but omit `fsync` on this
live cache to limit flash cost. Stale source frames never refresh the timestamp, and
the first fresh sample after a daemon restart refreshes even unchanged data. Older
valid snapshots remain available as `cached` after the vehicle turns off or the
daemon restarts.

Before wall-clock synchronization, startup may retain an owner-only cache that passes
all schema, type, range, and energy checks while deferring only the future-time test.
It is published at most once after clock sync and only after strict future-time and
30-day-age validation. Normal storage and every API response always reject future
timestamps.

Live parked/charging telemetry exists only while the comma SOM, pandad, ECAN, and
network remain powered. If normal shutdown powers off the SOM, the resident Panda
MCU may continue its vehicle-safety role, but this daemon, API, and exporter do not
run. The last validated disk snapshot becomes available as cached data after the
next boot.

## Configuration

Galaxy's **App Keys → EV Vehicle Telemetry** panel manages this configuration. The
same settings can be edited as an owner-only JSON file. StarPilot keeps its
existing location at `/data/galaxy/vehicle_telemetry_config.json`; the portable
core uses `/data/vehicle_telemetry` on stock openpilot.

For the quickest setup, connect the comma and phone to the same Wi-Fi network
while parked, then open **EV Vehicle Telemetry → Set Up** in Device settings on a
comma 3, or the **EV vehicle telemetry** QR action in comma 4 settings. Scan the QR
and choose **Personal public relay**. The temporary local page guides Tailscale
installation, owner login, Funnel approval, and fetch-token creation, then
shuts down after ten minutes or when the vehicle goes onroad. This restriction
applies only to configuration: the authenticated read-only telemetry API and
low-priority daemon remain available onroad. The setup page is not an
always-running Galaxy or Flask service. The full Galaxy panel remains available
for custom backend sending and advanced FRP settings after the same QR session
authorizes it. From the lightweight page, choose **Open StarPilot Galaxy
controls**; the short-lived capability is carried in an HttpOnly cookie and is
never exposed to Galaxy JavaScript, page URLs, or logs.

StarPilot supports six operating modes:

- `off`: cache only.
- `send`: make outbound-only HTTPS deliveries to a custom backend without
  exposing an inbound telemetry API.
- `local`: serve the authenticated API on the configured LAN port.
- `tailscale`: bind the API to loopback and publish it with a persistent public
  Funnel through the device owner's own free Tailscale account. This is the
  recommended public mode.
- `frp`: bind the API to loopback and supervise an FRP client that publishes a
  stable random subdomain through a self-hosted gateway.
- `galaxy`: let Galaxy serve the LAN and hosted-portal routes.

Create `/data/galaxy/vehicle_telemetry_config.json` as an owner-only file:

```json
{
  "schemaVersion": 1,
  "mode": "galaxy",
  "fetch": {
    "enabled": true,
    "token": "replace-with-at-least-32-random-characters"
  },
  "push": {
    "enabled": true,
    "url": "https://telemetry.example.com/v1/telemetry/ingest",
    "token": "replace-with-a-different-32-character-token",
    "vehicleId": "my-ev9",
    "vehicleName": "2026 Kia EV9",
    "maximumBatteryCapacityKilowattHours": 99.8,
    "drivingIntervalSeconds": 60,
    "chargingIntervalSeconds": 120,
    "parkedIntervalSeconds": 900
  }
}
```

The lightweight setup page exposes the send-only custom backend mode. The Galaxy
panel can additionally enable custom backend sending alongside any access mode,
install and enable the personal relay, guide the owner
through Tailscale login and Funnel approval, rotate the fetch token, preserve
existing push/FRP secrets when their inputs are left blank, display tunnel
status, and copy the generated public URL. Tailscale binaries and state remain
under `/data`; setup never remounts the system partition or installs a systemd
unit. Disabling the relay removes only the telemetry-managed Funnel and retains
the owner's identity for easy re-enable. Gateway setup, wildcard DNS automation,
and FRP TLS guidance are documented in [the fork-neutral core guide](vehicle-telemetry-core.md#frp-mode).

Fetch and push are independent. Remove either section or set its `enabled` field
to `false` when it is not needed. Both tokens must be at least 32 characters;
fetch/push are disabled when their required token is missing or short. Push URLs
must be HTTPS, cannot include user info or fragments, and redirects are not
followed. Backend responses are streamed and discarded rather than buffered or
logged. Stored fetch, push, FRP, Tailscale, and temporary setup credentials live
only in owner-readable files; configuration and status responses expose
token-presence flags instead of secret values.

Legacy `/data/galaxy/telemetry_push.json` push configuration remains supported for
migration. An older combined `/data/galaxy/vehicle_telemetry.json` is accepted only
when it contains a `fetch` or `push` object; telemetry-shaped Galaxy cache files at
that path are never interpreted as configuration. New installations should use the
explicit `_config.json` filename.

## Fetch API

In `galaxy` mode, requests use Galaxy's port and routes below. In `local`,
`tailscale`, and `frp` modes the standalone core serves the same `/api/vehicle/telemetry` and
`/api/vehicle/telemetry/status` paths on the configured local or proxy URL.

Requests require the configured fetch bearer token. The slug-prefixed hosted Galaxy
route additionally requires the paired Galaxy session cookie; direct LAN routes use
the app-specific bearer without that portal cookie:

```http
GET /api/galaxy/telemetry
Authorization: Bearer FETCH_TOKEN
```

`GET /api/vehicle/telemetry` is a compatibility alias. The diagnostic endpoint is:

```http
GET /api/vehicle/telemetry/status
Authorization: Bearer FETCH_TOKEN
```

Responses use `Cache-Control: no-store`. Disabled endpoints return `404`, invalid
authentication returns `401`, and an enabled endpoint without a validated cached
snapshot returns `503`. Diagnostic output reports token presence but never token
values.

### External app pairing

The Galaxy advertises `StarPilot Galaxy._sp-galaxy._tcp.local` on port 8082.
In **Galaxy → App Keys**, choose **Create Pairing QR**. The page shows both a QR
code and a six-digit code for 10 minutes. An external app can scan the QR, or use
mDNS to find the comma and submit the six-digit code.

Pairing creation and exchange accept only RFC1918/link-local/loopback clients and
local hostnames. A code is one-time, expires after 10 minutes, and is removed
after five invalid attempts. The QR contains only the local exchange URL and the
one-time code; it never contains a reusable bearer or Galaxy session.

```http
POST /api/external-app/pair
Content-Type: application/json

{
  "code": "123456",
  "clientName": "RangeBridge",
  "requestedCapabilities": ["vehicleTelemetry"]
}
```

The response supplies URLs for the active operating mode, the telemetry path,
and a client-specific bearer token. Local mode returns the standalone LAN port,
Tailscale and FRP modes return the ready HTTPS proxy URL, and Galaxy mode returns port 8082.
Each paired app gets its own token, so pairing a second app does not break the
first. RangeBridge requests `vehicleTelemetry` and `galaxySession` for LAN and
remote fallback. Galaxy Nav can use the same capability contract; only an
explicit `galaxySession` request returns the portal URL, cookie name, and Galaxy
session token after the one-time LAN exchange.

The hosted Galaxy tunnel preserves the device routing slug when forwarding API
requests. Remote telemetry therefore uses
`https://galaxy.firestar.link/<slug>/api/vehicle/telemetry` with both the paired
Galaxy cookie and the app-specific telemetry bearer. Galaxy exposes that exact
slug-prefixed route and rejects a slug that does not match the device's current
registration. LAN clients continue to use `/api/vehicle/telemetry` directly.
Unauthenticated Galaxy status/session routes expose no reusable session credential;
legacy auto-connect clients must migrate through the one-time pairing exchange.

## Custom backend sending

StarPilot sends an authenticated JSON envelope to the configured URL. A live EV9
validation sample with vehicle name and battery capacity configured produced a
**465-byte JSON body** and a **651-byte prepared HTTP/1.1 request before TLS**:

```json
{
  "schemaVersion": 1,
  "vehicleId": "my-ev9",
  "sentAt": 1784235068410,
  "telemetry": {
    "schemaVersion": 1,
    "source": "StarPilot carState",
    "updatedAt": 1784235068.41,
    "stateOfChargePercent": 77.5,
    "distanceToEmptyKilometers": 408.0,
    "isCharging": false,
    "isPluggedIn": false
  }
}
```

At a 60-second driving interval, this is approximately **27.2 KiB/hour of JSON**
or **38.1 KiB/hour before TLS**. Including TLS/TCP overhead and connection setup,
budget roughly **0.1 to 0.2 MB per driving hour**. A 30-second interval doubles the
JSON body to about 54.5 KiB/hour. Parked at the default 15-minute interval, the
JSON body is under 2 KiB/hour. Connection behavior and mobile-network
retransmissions can raise actual on-wire usage.

The publisher uses openpilot's on-road state for driving cadence, so traffic lights
and other momentary stops do not create parked/driving transition uploads. Charging
takes priority over on-road state. It sends immediately on startup/activity
transitions, periodically at the configured activity interval, and when parked data
materially changes. Failed requests use bounded exponential backoff. Tokens remain
in headers and are never written into the payload or diagnostic status file.

The backend must accept an HTTPS `POST` with `Content-Type: application/json` and
`Authorization: Bearer <token>`, then return a `2xx` response after accepting the
event. It should ignore unknown fields and tolerate an occasional duplicate after
an ambiguous network failure; `vehicleId` plus `sentAt` is the recommended
deduplication key. Redirects are not followed. Optional vehicle fields may be
absent, so backends should use `schemaVersion` and field presence rather than
requiring every example field. The complete envelope, cadence, retry, and timeout
contract is in the [fork-neutral custom backend guide](vehicle-telemetry-core.md#custom-backend-sending).

## DBC information required for vehicle support

EV Vehicle Telemetry expects the vehicle DBC and `CarState` parser to provide:

- battery SOC mapped to `fuelGauge` as a `0.0...1.0` fraction;
- displayed distance to empty mapped to `distanceToEmpty` in meters;
- separate `charging` and `chargingPortConnected` booleans when available;
- the normal `vEgo` in meters per second and `standstill` boolean for cadence.

Stock openpilot v0.11.1 already contains `fuelGauge`, `charging`, `vEgo`, and
`standstill`. `distanceToEmpty` and `chargingPortConnected` are optional schema
extensions in StarPilot; the portable core safely omits them when running on an
unmodified stock schema.

For every new energy signal, document and test its CAN message/bus, start bit,
length, byte order, signedness, factor, offset, unit, expected frequency,
counter/checksum rules, and any validity bit. Reject stale/invalid frames, keep
plugged-in distinct from actively charging, and validate redundant cluster/BMS
sources when possible. A minimal port needs useful SOC or DTE; full RangeBridge
behavior benefits from all four energy/charging fields. The portable guide has
the complete [DBC and unit contract](vehicle-telemetry-core.md#dbc-and-vehicle-port-requirements).

## Adding vehicle support

1. Define the make/model CAN signals in opendbc.
2. Populate the normalized `CarState` fields in the vehicle interface.
3. When possible, validate redundant SOC/DTE sources before publishing them.
4. Add a focused DBC/CarState test for the supported fingerprint.
5. Do not add make/model decoding branches to the telemetry daemon. An offroad
   producer, if genuinely required, must derive data inside an existing sole CAN
   owner and publish a normalized cereal state rather than create another subscriber.

This separation keeps the transport generic and makes new signals suitable for an
upstream opendbc/openpilot contribution.
