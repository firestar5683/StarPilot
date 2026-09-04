# StarPilot BLE Live Protocol

The StarPilot companion service is a bonded, read-only Bluetooth LE API. Live
telemetry is published locally by the comma and does not require comma Connect,
cellular service, Wi-Fi, or Internet access.

## GATT contract

Service UUID: `9b6d1000-6f7a-4a5b-8c3d-2e1f0a9b8c7d`

| Characteristic | UUID suffix | Access | Contents |
| --- | --- | --- | --- |
| Status | `1001` | authenticated read | JSON device/protocol capabilities |
| Command | `1002` | authenticated write | JSON read-only request |
| Response | `1003` | authenticated read | JSON response for the writing phone |
| Live state | `1004` | authenticated read + notify | cached frame / notification fragments |

The full UUID for each characteristic uses the same suffix in
`9b6d100x-6f7a-4a5b-8c3d-2e1f0a9b8c7d`.

## Versioning

The API and its binary telemetry frames are versioned independently:

| Layer | Current version | Where it is reported |
| --- | ---: | --- |
| Companion GATT API | `2` | top-level `get_status.protocol_version` |
| Live frame format | `1` | `get_status.live.protocol_version` and each notification/frame |

In short, this document describes **Companion API v2 carrying Live Frame v1**.
Companion API v2 adds the Live state characteristic while keeping the existing
`ping` and `get_status` requests compatible. The live frame starts at v1 because
it is a separate wire format; changing one version does not automatically change
the other.

## Revision-based settings sync

The status payload includes `param_revision`, a monotonic integer representing
the current persistent Params state. It changes when any persistent parameter
changes, including writes from the companion app, the on-device UI, or another
local service.

`get_params` accepts an optional non-negative integer `since` alongside its
existing `keys` array:

```json
{"op":"get_params","keys":["ExampleToggle","ExampleValue"],"since":123}
```

When `since` is absent or zero, the response contains every requested allow-listed
value. Otherwise, it contains only requested values modified after that revision.
A changed value that has since been removed is returned as `null`. Clients use
the status characteristic's `param_revision` as the authoritative revision and
must only save it after every requested batch completes successfully.

`get_status` also advertises the live UUID, frame and notification sizes,
fragment count, and publication rate. It additionally advertises
`live.frame_types` (`[1, 2]`) and `live.health_rate_hz` (`2`) so a client can
feature-detect the health frames before subscribing. `live.path_rate_hz` remains
present for API compatibility but is `0`. `live.rate_hz` is the state-frame rate;
the aggregate stream is also advertised as `live.total_rate_hz` (`12`) and
`live.notification_rate_hz` (`48`) at the default ATT MTU.
`get_live_metadata` returns the selected model plus current alert text and
speed-limit source as compact JSON. Metadata is requested on demand so strings
are not sent in every 10 Hz frame.

## Frame types on the Live characteristic

All frames share the same 16-byte header and 64-byte size and ride the same
notification/reassembly pipeline. They are distinguished by the **frame-type byte
at offset 3**. A client dispatches on that byte and **ignores unknown types**, so
a type-1-only dispatcher remains compatible. A legacy client that assumed every
frame was type 1 must add this check before decoding the payload.

| Type | Name | Rate | Purpose |
| ---: | --- | ---: | --- |
| `1` | State | 10 Hz | driving state (below) |
| `2` | Device/Health | ~2 Hz | CPU/GPU/mem/temps/power/network/storage |

The two types are interleaved on the same notify stream. The `sequence`
counter increments across every frame regardless of type, so fragments are
grouped by sequence exactly as before.

## Live state frame format v1

Frames are exactly 64 bytes, little-endian, and are published at 10 Hz while a
client subscribes to notifications. A client may read the characteristic for
the last cached complete frame, which can be stale when no client is subscribed.
Notifications split each frame into four 20-byte fragments so the feed also
works with Bluetooth's default 23-byte ATT MTU. The
`sequence` counter wraps at 65535 and `monotonic_ms` wraps at 2^32.

Each notification has a four-byte little-endian header followed by 16 bytes of
the state frame:

| Offset | Type | Field |
| ---: | --- | --- |
| 0 | `uint8` | live frame format version (`1`) |
| 1 | `uint16` | frame sequence |
| 3 | `uint8` | high nibble = fragment count, low nibble = zero-based index |
| 4 | `uint8[16]` | frame bytes for this fragment |

A client should collect all four fragments with the same sequence, order them by
the low nibble, concatenate their payloads, and then validate the inner `SP`
magic, version, size, and sequence. An incomplete sequence is discarded when a
newer sequence arrives.

| Offset | Type | Field | Scale/meaning |
| ---: | --- | --- | --- |
| 0 | `char[2]` | magic | ASCII `SP` |
| 2 | `uint8` | live frame format version | `1` |
| 3 | `uint8` | frame type | `1` = state |
| 4 | `uint16` | frame size | `64` |
| 6 | `uint16` | sequence | wraps naturally |
| 8 | `uint32` | monotonic time | milliseconds |
| 12 | `uint32` | flags | bitmask below |
| 16 | `int16` | vehicle speed | 0.01 m/s |
| 18 | `uint16` | set speed | 0.01 m/s |
| 20 | `int16` | acceleration | 0.01 m/s² |
| 22 | `int16` | target acceleration | 0.01 m/s² |
| 24 | `int16` | steering angle | 0.1 degree |
| 26 | `int16` | desired steering angle | 0.1 degree |
| 28 | `int16` | steering torque | 0.1 native unit |
| 30 | `uint16` | lead distance | 0.1 m |
| 32 | `int16` | lead relative speed | 0.01 m/s |
| 34 | `uint16` | lead probability | 0.001 |
| 36 | `uint16` | speed limit | 0.01 m/s |
| 38 | `int16` | speed-limit offset | 0.01 m/s |
| 40 | `uint16` | curve target speed | 0.01 m/s |
| 42 | `uint8` | cruise state | enum from metadata |
| 43 | `uint8` | border state | enum from metadata |
| 44 | `uint8` | alert status | enum from metadata |
| 45 | `uint8` | Conditional Chill reason | enum from metadata |
| 46 | `uint8` | driving profile | acceleration profile enum |
| 47 | `uint8` | longitudinal profile | personality enum |
| 48 | `uint8` | lane-change state | cereal enum |
| 49 | `uint8` | lane-change direction | cereal enum |
| 50 | `uint8` | long-control state | cereal enum |
| 51 | `uint8` | model source | small, big, or big loading |
| 52 | `uint8[4]` | border RGBA | exact comma border color |
| 56 | `uint32` | alert ID | CRC32 of the current alert type, or zero |
| 60 | `uint32` | metadata revision | changes with model metadata/source |

`metadata_revision` tells the client when to request `get_live_metadata` again.
When `alert_id` changes, the same response supplies the current alert type, both
display text lines, status, and speed-limit source. The phone can build its
timeline locally by comparing successive frames.

## State flags

| Bit | State |
| ---: | --- |
| 0 | connected |
| 1 | drive started |
| 2 | openpilot engaged |
| 3 | controls active |
| 4 | cruise available |
| 5 | cruise enabled |
| 6 | Always-On Lateral active |
| 7 | Experimental Mode active |
| 8 | Conditional Chill active |
| 9 | Speed Limit Control enabled |
| 10 | a speed-limit target is available for display |
| 11 | Curve Control enabled |
| 12 | Curve Control actively controls speed |
| 13 | lead present |
| 14 | lateral active |
| 15 | longitudinal active |
| 16 | gas pressed |
| 17 | brake pressed |
| 18 | stopping |
| 19 | standstill |
| 20 | big model active |
| 21 | lateral paused |
| 22 | Traffic Mode active |
| 23 | Switchback Mode active |
| 24 | alert present |
| 25 | core telemetry valid |
| 26 | forcing stop |
| 27 | StarPilot tracking lead |
| 28 | Pulse & Glide is gliding |
| 29 | comma display units are metric |
| 30 | controls overriding |
| 31 | red traffic light detected |

All physical values remain SI on the wire. Bit 29 only tells the phone which
presentation the comma uses so a client can default to matching units.

## Device/Health frame v1 (frame type 2)

Slow-changing device telemetry sourced from `deviceState`, published at ~2 Hz
(every fifth tick of the 10 Hz loop). Same 16-byte header as the state frame with
frame type `2`; the header `flags` field carries the health bitmask below. All
values are little-endian and SI (temps in °C, power in W).

| Offset | Type | Field | Scale/meaning |
| ---: | --- | --- | --- |
| 0 | `char[2]` | magic | ASCII `SP` |
| 2 | `uint8` | live frame format version | `1` |
| 3 | `uint8` | frame type | `2` = device/health |
| 4 | `uint16` | frame size | `64` |
| 6 | `uint16` | sequence | wraps naturally |
| 8 | `uint32` | monotonic time | milliseconds |
| 12 | `uint32` | health flags | bitmask below |
| 16 | `uint8` | CPU usage % | 0–100 (max of per-core list) |
| 17 | `uint8` | GPU usage % | 0–100 |
| 18 | `uint8` | memory usage % | 0–100 |
| 19 | `uint8` | free storage % | 0–100 |
| 20 | `int16` | CPU temp | 0.1 °C (max of list) |
| 22 | `int16` | GPU temp | 0.1 °C (max of list) |
| 24 | `int16` | memory temp | 0.1 °C |
| 26 | `int16` | max temp (fan driver) | 0.1 °C |
| 28 | `int16` | intake/ambient temp | 0.1 °C |
| 30 | `uint8` | thermal status | 0=ok, 2=overheated, 3=critical |
| 31 | `uint8` | fan speed % | 0–100 (desired) |
| 32 | `uint16` | total power draw | 0.01 W |
| 34 | `uint16` | SoM power draw | 0.01 W |
| 36 | `uint16` | 12 V battery reserve | 0.1 Wh (from `carBatteryCapacityUwh`) |
| 38 | `uint8` | screen brightness % | 0–100 |
| 39 | `uint8` | network type | 0=none,1=wifi,2=2G,3=3G,4=4G,5=5G,6=ethernet |
| 40 | `uint8` | network strength | 0=unknown…4=great |
| 41 | `uint8` | reserved | 0 |
| 42 | `uint32` | uptime | seconds (boot-relative monotonic) |
| 46 | `uint8[18]` | reserved | 0 |

### Health flags (offset 12 bitmask)

| Bit | Meaning |
| ---: | --- |
| 0 | onroad (driving) |
| 1 | offroad |
| 2 | network metered |
| 3 | WiFi connected |
| 4 | ethernet connected |
| 5 | cellular connected |
| 6 | device has non-metered WiFi/Ethernet (local-media candidate) |
| 7 | thermal OK |
| 8 | thermal overheated |
| 9 | thermal critical |
| 10 | fan active |
| 11 | low storage (`freeSpacePercent < 10`) |
| 12 | reserved |
| 13 | recently pinged cloud (`lastAthenaPingTime` fresh) |

Bit 6 only describes the device's own non-metered WiFi/Ethernet link. It cannot
prove that the phone is on the same LAN or that the device's local `:8082` is
reachable. A phone must also be on a suitable non-metered local network and
successfully probe `:8082` before pulling video or footage. If that check fails,
do not send heavy media through the galaxy.link tunnel; use BLE for real-time
data and the tunnel only for light scalar JSON. **Never** pull video over the
tunnel — its exit can be metered/cellular.

## Channel responsibilities

The companion is one of three tiers; a client should route requests accordingly:

1. **BLE (this protocol)** — always-on, low-latency, bounded bandwidth. All
   real-time driving state, device health, and connectivity. Nothing real-time
   should ever depend on the network.
2. **Direct LAN / non-metered WiFi (`:8082`)** — where heavy pulls are allowed:
   camera video, JPEG snapshots, route footage, screen recordings. Require health
   flag **bit 6**, a suitable non-metered local network on the phone, and a
   successful reachability probe to the device's local `:8082`. If any check fails,
   do not use the galaxy.link tunnel for heavy media.
3. **galaxy.link tunnel** — remote/opportunistic light control and scalar JSON
   only (params/toggles, navigation destination, status). **No video over the
   tunnel, ever** — its exit can be metered/cellular.

## Client integration

A bonded BLE client discovers the companion service, subscribes to the Live
state characteristic (`…1004`), and reassembles notifications by sequence as
described above. Concretely:

1. **Bond first.** BlueZ requires an authenticated LE bond; unbonded or classic
   (BR/EDR) reads are rejected. Discover the service UUID
   `9b6d1000-6f7a-4a5b-8c3d-2e1f0a9b8c7d`.
2. **Feature-detect** via `get_status`: read `live.frame_types` and
   `live.health_rate_hz` to learn which frame types this device emits.
3. **Subscribe** to the Live characteristic and reassemble each frame from its
   four 20-byte fragments (group by sequence, order by the low nibble,
   concatenate the 16-byte payloads).
4. **Dispatch on the frame-type byte at offset 3** after validating the `SP`
   magic, version, and size. Consume only the types you understand and ignore the
   rest — a type-1-only dispatcher is unaffected by the health frames.
5. Request `get_live_metadata` after connecting and whenever a **type-1** frame's
   `metadata_revision` changes.

The live transport is independent of the Galaxy web interface and exposes no
HTTP page.

## Safety and lifecycle

The API has no operation that engages, accelerates, brakes, steers, or changes a
driving parameter. BlueZ requires an authenticated bond for reads/writes, and
notifications are available only over that paired encrypted link. The publisher
runs only while a client subscribes to the Live characteristic and stops after
the final subscription ends or the companion GATT application is removed.
