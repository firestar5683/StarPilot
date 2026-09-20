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

The Mac uses its selected system audio output. Bluetooth delay estimates from the comma do not transfer automatically to a different Mac output. Current controls do not synchronize a second device's playback.
