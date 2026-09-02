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
| Live state | `1004` | authenticated read + notify | latest frame / notification fragments |

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

`get_status` also advertises the live UUID, frame and notification sizes,
fragment count, and publication rate. `get_live_metadata` returns the selected
model plus current alert text and speed-limit source as compact JSON. Metadata is
requested on demand so strings are not sent in every 10 Hz frame.

## Live state frame format v1

Frames are exactly 64 bytes, little-endian, and are published at 10 Hz. A client
may read the characteristic for the latest complete frame. Notifications split
each frame into four 20-byte fragments so the feed also works with Bluetooth's
default 23-byte ATT MTU. The
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

## Client integration

A bonded BLE client discovers the companion service, subscribes to the Live
state characteristic, and reassembles notifications by sequence as described
above. It should request `get_live_metadata` after connecting and whenever the
frame's `metadata_revision` changes. The live transport is independent of the
Galaxy web interface and exposes no HTTP page.

## Safety and lifecycle

The API has no operation that engages, accelerates, brakes, steers, or changes a
driving parameter. BlueZ requires an authenticated bond for reads/writes, and
notifications are available only over that paired encrypted link. The publisher
starts with the companion GATT application and stops when the application is
removed.
