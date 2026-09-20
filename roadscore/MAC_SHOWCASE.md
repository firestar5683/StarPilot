From the Mac, start the saved showcase on the comma and in a native Mac onroad window:

```sh
./onroad --roadscore route1 --demo
```

Add `--fullscreen` to fill the Mac display while preserving the native layout:

```sh
./onroad --roadscore route1 --demo --fullscreen
```

Press **F** or **F11** to toggle fullscreen. **Escape** returns to the window without stopping playback. The native aspect ratio is preserved with letterboxing; this does not select a different driving UI.

The command prepares both local native replay engines, then releases their start barriers together. The comma primes its local route cache and first camera frame before publishing road state. The Mac decodes its own cached video and follows the comma’s route playhead. Audio plays from the comma only, through its selected output. No ACE generation or model warm-up occurs. The previous single-device saved-replay setup took 17.13 seconds for loading, replay parameters and UI startup; measure the paired path separately.

Use Galaxy for engagement and turn-signal controls. The Mac follows the same applied presentation selections. No browser control page opens and no video is streamed from the comma. Small Galaxy status updates keep the local playheads approximately aligned; this is independent playback, not frame-exact mirroring. The buttons affect replay appearance and musical presentation only, never vehicle control. Ctrl+C stops both owned demo sessions and leaves the resident ACE worker intact.

Left, Right and Off replace the recorded turn signals until Recorded is selected again. This applies to the music, native arrows and ordinary lane-change prompts on both displays. Off releases the shaker smoothly without starting more pulses. Important native alerts retain priority. Engagement and signal selections are independent.

Each registered alias uses its own matching route and preserved ACE/Prism performance. Replace `route1` in the command with another ready alias; no manual audio staging is needed. Readiness is recorded in the local catalog, and unprepared entries are rejected before playback. Never substitute another route's music archive to bypass this check.

The event recordings are approximately 5:02 for route1, 5:06 for route2, 7:33 for route3 and 1:45 for route4. Route1 remains the primary showcase. Route3 includes an accepted-music extension at the ending: a two-second blend followed by 6.3 seconds of repeated accepted material. Route4's original recording logged one output-scheduling underflow; its saved PCM is continuous, and the subsequent 20-second saved-playback check had no output flags.

Route2 completed its full saved recording on the Mac, including the recorded tail after the last road frame. Route3 and route4 use the same saved path and have separate archive checks and short playback checks; this is not a claim of full-route physical listening acceptance. Galaxy's Off, opposite-direction override and Recorded reset were checked against real route2 events on the comma, including the native arrow and prompt.

The local configuration is ignored by Git: `roadscore/assets/demo_catalog.json` stores the explicit comma address, local controls port and registered routes. The comma has its own catalog pointing to persistent local assets. Each entry needs the route identity, a compatible completed archive and an optional matching curve plan. No discovery or automatic target switching occurs.

The dual-native mode completed a full301.7-second FiiO audible run with Galaxy controls reaching both screens and successful cleanup. Tracking skew was85ms median and171ms at the95th percentile. Network delays sometimes paused corrections while replay continued. There were no callback or clock exceptions, but28 audio status flags and21 forward clock corrections were recorded, so completion does not establish glitch-free output. Fullscreen also passed an8-second native Mac replay check with no output flags or clock exceptions. The public JLab speaker still needs its own physical output/timing check.

For a Mac-only interactive fallback, use:

```sh
./onroad --roadscore route1 --prepared-showcase --unpaired
```

This opens native onroad replay on the Mac and processes the same preserved core with the current presentation layer. It needs the route cached on the Mac and ignored `roadscore/assets/prepared_showcase.json`, containing `route`, `archive` and optional `curve_plan`. The Mac uses its selected system audio output. A comma Bluetooth correction does not automatically apply to a Mac output.

Compatible archives contain `dry.wav`, `launch.json`, `audio_blocks.jsonl`, `replay_origin.json` and `rhythm_timeline.json`. Original dry PCM is used at unity gain, with the recorded model/DAC clock. The final mix is not processed twice. `--score-archive PATH` explicitly selects another compatible archive for the independent mode.

Both saved launchers support `--muted`, `--duration SECONDS` and `--no-browser`. Paired `--check` contacts Galaxy to verify the target is offroad; independent `--check` validates local prerequisites only. The controls server binds to loopback and refuses an occupied port. The paired target must be an explicit private IPv4 address on Galaxy port 8082.

The independent mode can follow Galaxy controls with `--paired-comma URL`, but controls alone do not synchronize playback. The paired `--demo` launcher additionally holds both starts and enables playhead following. The Mac follows the comma; it never adjusts the comma's audio clock to match its screen. `--demo --screen-mirror` explicitly enables JPEG capture for the earlier browser mirror. Normal paired playback does not capture or encode a video feed.

Ordinary `./onroad --roadscore route1` remains the fresh-generation path. Gold music and historical recordings are preserved. The deliverable is interactive replay; an MP4 is not a substitute.
