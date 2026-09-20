From the Mac, start the saved showcase on the comma and in a native Mac onroad window:

```sh
./onroad --roadscore route1 --demo
```

The command prepares both local native replay engines, then releases their start barriers together. The Mac decodes its own cached video and follows the comma’s route playhead. Audio plays from the comma only, through its selected output. No ACE generation or model warm-up occurs. The previous single-device saved-replay setup took 17.13 seconds for loading, replay parameters and UI startup; measure the paired path separately.

Use Galaxy for engagement and turn-signal controls. The Mac follows the same applied presentation selections. No browser control page opens and no video is streamed from the comma. Small Galaxy status updates keep the local playheads approximately aligned; this is independent playback, not frame-exact mirroring. The buttons affect replay appearance and musical presentation only, never vehicle control. Ctrl+C stops both owned demo sessions and leaves the resident ACE worker intact.

Route1 is currently registered and ready. Route2–4 remain unavailable until their own matching core recordings are prepared and verified. Never substitute another route's music archive to bypass this check.

The local configuration is ignored by Git: `roadscore/assets/demo_catalog.json` stores the explicit comma address, local controls port and registered routes. The comma has its own catalog pointing to persistent local assets. Each entry needs the route identity, a compatible completed archive and an optional matching curve plan. No discovery or automatic target switching occurs.

The previous screen-mirror mode passed two short muted tests. Its audible test later exposed a DAC clock mapping error; the stable per-stream clock mapping and native dual-replay path require their own device validation. FiiO headphones and the public JLab speaker need separate listening checks.

For a Mac-only interactive fallback, use:

```sh
./onroad --roadscore route1 --prepared-showcase --unpaired
```

This opens native onroad replay on the Mac and processes the same preserved core with the current presentation layer. It needs the route cached on the Mac and ignored `roadscore/assets/prepared_showcase.json`, containing `route`, `archive` and optional `curve_plan`. The Mac uses its selected system audio output. A comma Bluetooth correction does not automatically apply to a Mac output.

Compatible archives contain `dry.wav`, `launch.json`, `audio_blocks.jsonl`, `replay_origin.json` and `rhythm_timeline.json`. Original dry PCM is used at unity gain, with the recorded model/DAC clock. The final mix is not processed twice. `--score-archive PATH` explicitly selects another compatible archive for the independent mode.

Both saved launchers support `--muted`, `--duration SECONDS` and `--no-browser`. Paired `--check` contacts Galaxy to verify the target is offroad; independent `--check` validates local prerequisites only. The controls server binds to loopback and refuses an occupied port. The paired target must be an explicit private IPv4 address on Galaxy port 8082.

The independent mode can follow Galaxy controls with `--paired-comma URL`, but controls alone do not synchronize playback. The paired `--demo` launcher additionally holds both starts and enables playhead following. `--demo --screen-mirror` retains the earlier explicit browser mirror for diagnosis; it is not the normal demo.

Ordinary `./onroad --roadscore route1` remains the fresh-generation path. Gold music and historical recordings are preserved. The deliverable is interactive replay; an MP4 is not a substitute.
