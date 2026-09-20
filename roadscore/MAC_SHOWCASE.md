From the Mac, start the saved showcase on the comma and mirror its actual onroad screen:

```sh
./onroad --roadscore route1 --demo
```

The command loads the selected A recording on the comma, starts its native route replay, and opens [the Mac display and controls](http://127.0.0.1:56976/). Audio plays from the comma through its selected output. No ACE generation or model warm-up occurs. The first measured saved-replay setup took 17.13 seconds for loading, replay parameters and UI startup.

Galaxy and the Mac page control the same native presentation session. Engagement and turn-signal buttons affect replay appearance and musical presentation only. They do not control a vehicle. The Mac shows actual comma frames; there is no second replay clock to synchronize. Video mirroring requires the local network. Ctrl+C in the launcher stops its owned demo session and leaves the resident ACE worker intact.

Route1 is currently registered and ready. Route2–4 remain unavailable until their own matching core recordings are prepared and verified. Never substitute another route's music archive to bypass this check.

The local configuration is ignored by Git: `roadscore/assets/demo_catalog.json` stores the explicit comma address, local controls port and registered routes. The comma has its own catalog pointing to persistent local assets. Each entry needs the route identity, a compatible completed archive and an optional matching curve plan. No discovery or automatic target switching occurs.

Two short muted paired tests verified native replay, fresh JPEG frames, Galaxy engagement/signal acknowledgments and clean shutdown. Those tests do not establish physical speaker audibility, Bluetooth timing or full-route acceptance. FiiO headphones and the public JLab speaker need separate listening checks.

For a Mac-only interactive fallback, use:

```sh
./onroad --roadscore route1 --prepared-showcase --unpaired
```

This opens native onroad replay on the Mac and processes the same preserved core with the current presentation layer. It needs the route cached on the Mac and ignored `roadscore/assets/prepared_showcase.json`, containing `route`, `archive` and optional `curve_plan`. The Mac uses its selected system audio output. A comma Bluetooth correction does not automatically apply to a Mac output.

Compatible archives contain `dry.wav`, `launch.json`, `audio_blocks.jsonl`, `replay_origin.json` and `rhythm_timeline.json`. Original dry PCM is used at unity gain, with the recorded model/DAC clock. The final mix is not processed twice. `--score-archive PATH` explicitly selects another compatible archive for the independent mode.

Both saved launchers support `--muted`, `--duration SECONDS` and `--no-browser`. Paired `--check` contacts Galaxy to verify the target is offroad; independent `--check` validates local prerequisites only. The controls server binds to loopback and refuses an occupied port. The paired target must be an explicit private IPv4 address on Galaxy port 8082.

The independent mode can also follow Galaxy controls with `--paired-comma URL`, but that does not synchronize its independent video/audio clocks. Use `--demo` for the actual screen mirror.

Ordinary `./onroad --roadscore route1` remains the fresh-generation path. Gold music and the protected movie fallback are unchanged.
