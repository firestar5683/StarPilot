The prepared Mac showcase runs native onroad replay with a preserved ACE core recording and the current real-time presentation layer. It does not load ACE, contact Chestnut, or regenerate music.

```sh
./onroad --roadscore route1 --prepared-showcase
```

The launcher opens the normal UI and a local control page. Engage/disengage and turn-signal buttons use the same Galaxy command writer and presentation controls as the comma replay. The displayed vehicle state is explicitly a replay simulation. Ctrl+C stops the Mac session and its children.

Local setup lives in ignored `roadscore/assets/prepared_showcase.json`:

```json
{"route":"DONGLE/ROUTE","archive":"/absolute/path/to/completed/core/archive","curve_plan":"/absolute/path/to/optional/showcase_curve_plan.json","paired_comma":"http://192.168.1.50:8082","controls_port":56976}
```

`paired_comma` and `controls_port` are optional, explicit local choices. Replace the example IP with the comma's actual private IPv4 address. Saving both lets the normal command open the same [demo control page](http://127.0.0.1:56976/) with Mac + comma controls enabled on subsequent launches. No configured target means Mac-only controls; no configured port means an available temporary port. These choices apply only to the matching configured route.

The archive must contain `dry.wav`, `launch.json`, `audio_blocks.jsonl`, `replay_origin.json`, and `rhythm_timeline.json`. The route must already be cached locally. The dry source is used at unity gain; the recorded final mix is never processed a second time. Original model timestamps and measured DAC/sample offsets keep the music aligned to the replay. An optional staged curve plan must match the exact route and replay start.

`--score-archive PATH` selects another compatible complete recording explicitly. `--check` validates the local prerequisites without starting playback. `--muted`, `--duration SECONDS`, and `--no-browser` support verification. Live generation and the existing stored final-score replay retain their separate launch modes.

The Mac uses its selected system audio output. Bluetooth delay estimates from the comma do not transfer automatically to a different Mac output.

The saved target needs no recurring CLI flag. To override it for one launch:

```sh
./onroad --roadscore route1 --prepared-showcase --paired-comma http://192.168.1.50:8082
```

`--unpaired` overrides a saved target for a Mac-only launch. `--port NUMBER` overrides the saved control port; `--port 0` selects an available temporary port. An occupied fixed port produces an error; it does not attach to or replace the existing session.

The comma must already have a fresh, ready RoadScore replay running while offroad. Each button writes the Mac action first, then forwards only that engagement or signal action in the background using the comma's own session ID. The page names the enabled targets and reports whether the comma received or applied the latest command. An unavailable comma leaves the Mac buttons usable. A timeout can mean delivery is unknown; writes are not retried or rolled back automatically.

Configuration is read when the Mac launcher starts. Changing the file or refreshing a currently running page does not enable pairing in that existing Python session. Let it finish or stop it deliberately, launch the demo again, then refresh the same page if using the saved port.

The local control page remains bound to `127.0.0.1`. Pairing permits only an explicit private IPv4 address on port 8082, without redirects or discovery. The existing LAN Galaxy service uses offroad and fresh replay-session checks; it has no separate HTTP login or encryption. `--check` does not contact the peer. Pairing neither starts the comma nor synchronizes its video or music with the Mac.
