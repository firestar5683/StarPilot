The prepared Mac showcase runs native onroad replay with a preserved ACE core recording and the current real-time presentation layer. It does not load ACE, contact Chestnut, or regenerate music.

```sh
./onroad --roadscore route1 --prepared-showcase
```

The launcher opens the normal UI and a local control page. Engage/disengage and turn-signal buttons use the same Galaxy command writer and presentation controls as the comma replay. The displayed vehicle state is explicitly a replay simulation. Ctrl+C stops the Mac session and its children.

Local setup lives in ignored `roadscore/assets/prepared_showcase.json`:

```json
{"route":"DONGLE/ROUTE","archive":"/absolute/path/to/completed/core/archive","curve_plan":"/absolute/path/to/optional/showcase_curve_plan.json"}
```

The archive must contain `dry.wav`, `launch.json`, `audio_blocks.jsonl`, `replay_origin.json`, and `rhythm_timeline.json`. The route must already be cached locally. The dry source is used at unity gain; the recorded final mix is never processed a second time. Original model timestamps and measured DAC/sample offsets keep the music aligned to the replay. An optional staged curve plan must match the exact route and replay start.

`--score-archive PATH` selects another compatible complete recording explicitly. `--check` validates the local prerequisites without starting playback. `--muted`, `--duration SECONDS`, and `--no-browser` support verification. Live generation and the existing stored final-score replay retain their separate launch modes.

The Mac uses its selected system audio output. Bluetooth delay estimates from the comma do not transfer automatically to a different Mac output.

Optional paired controls require an explicit Galaxy LAN URL each launch. Replace this example with the comma's private IPv4 address:

```sh
./onroad --roadscore route1 --prepared-showcase --paired-comma http://192.168.1.50:8082
```

The default is unpaired. The comma must already have a fresh, ready RoadScore replay running while offroad. Each button writes the Mac action first, then forwards only that engagement or signal action in the background using the comma's own session ID. The page reports Mac state and whether the comma received or applied the latest command. An unavailable comma leaves the Mac buttons usable. A timeout can mean delivery is unknown; writes are not retried or rolled back automatically.

The local control page remains bound to `127.0.0.1`. Pairing permits only an explicit private IPv4 address on port 8082, without redirects or discovery. The existing LAN Galaxy service uses offroad and fresh replay-session checks; it has no separate HTTP login or encryption. `--check` does not contact the peer. Pairing neither starts the comma nor synchronizes its video or music with the Mac.
