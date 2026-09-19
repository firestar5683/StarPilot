# COMMA_HACK 7 event integration

Pre-event private baseline: `8a957d1`, preserved as tag `pre-event-8a957d1` in Desktop/RoadScore. The original source, routes, models and evidence remain there unchanged.

Event source lives under `roadscore/` in StarPilot on `RoadScore`. Existing module layout is retained to reduce migration risk. Generated artifacts, routes and model weights are excluded from Git. Historical reports describe the pre-event bench, not event validation.

Target: `comma@192.168.63.143`. Automated runs remain physically muted. Physical listening and live driving require attended validation; no live safety claims.

Status: source migrated on `RoadScore`; official example passed; bounded GPU recovery investigation and full Prism validation in progress. See current checkpoint below.

## Night-one checkpoint: hardware connection interrupted

- Source migration committed; event comma switched from `Dom` at `b990a776b2` to `RoadScore` at `e0aa4543aa` (verify full revision on reconnect). Existing active-theme changes on the comma were preserved.
- Event inventory: comma four (`mici`), SDM845, AGNOS `19.6.20`, kernel `4.9.103`, 3606 MiB RAM, no swap, roughly 82 GiB free on `/data`; CPU0–3 online at inventory. Real `IsOnroad` was false.
- USB showed only root hubs and Quectel modem. **No Chestnut detected**. GPU capacity/link/firmware cannot be reported yet.
- `bluetoothctl show` timed out without controller details; `pactl` was unavailable. ALSA listed the onboard sdm845 card. No Bluetooth sink was selected and no audio stream was opened.
- Official repository cloned; its setup first failed because `/home` is a 100 MB overlay. Restarted with cache and temporary files under `/data`. The first cache was preserved under `.cache/uv-first-attempt`. Installation completion is not verified.
- Replay build started; compiler warnings were recorded, but executable completion is not verified.
- ACE profiles transferred (approximately 20 MB). Weight transfer reached approximately 585–601 MB before SSH reset; it is incomplete. VAE and fixed reproducer fixture still need verification/staging.
- At the network interruption, no RoadScore GPU worker or replay had been started. No model timing or event hardware success is claimed.
- Mac migration tests: 20 hardening tests plus 61 core/settings/clock/archive tests passed. Logs are private under `roadscore/results/event_night_one/`.
- The first inventory script encountered an offline CPU-policy sysfs read error. The committed tool now records unavailable reads as null instead of aborting.

## Resume sequence

1. Confirm device IP and Chestnut power/USB connection. Set `ROADSCORE_DEVICE` if changed.
2. Bring the event branch up to the latest local commit, preserving the device's theme changes. Do not push private data. `/data/roadscore` is a compatibility symlink to the repo subdirectory.
3. On comma: `bash /data/roadscore/tools/bootstrap_event.sh`. This verifies real offroad state, keeps automated audio muted, finishes dependencies and builds replay. It does not start GPU work.
4. On Mac: `python3 roadscore/tools/stage_event_assets.py`. This resumes ACE weights/profiles and the exact saved decoder fixture from Desktop. `--known-route DONGLE/ROUTE` optionally stages an already-used regression route without score archives. No judging submission acquisition before the Phase 1 gate.
5. Finish the official repo's `uv sync --locked --python 3.12` with `UV_CACHE_DIR=/data/roadscore/.cache/uv TMPDIR=/data/roadscore/tmp`, then `tools/setup.py`. Stage `models/yolo26n.onnx` from the already-exported official Mac example.
6. Run `bash /data/roadscore/tools/official_chestnut.sh`; it refuses a busy GPU, verifies offroad, saves logs, and runs official USB validation plus YOLO. Stop and preserve any failure.
7. Start `prototype/worker_service.py start --composer ace --profile prism`; capture cold preparation and warm continuation metrics, then stop the owned worker before the decoder reproducer.
8. Run `tools/decoder_repro.py`; use its fixed input and unique output folder. If the link fails, ask an engineer before further hardware debugging. Then native replay, attended audio checks, and the remaining ordered brief.

SA3 source and local converted weights exist, but its event assets/environment have not been fully staged or validated. Do not call it an available event fallback yet. Aurora's prepared profile transferred but likewise has no event-generation result.

Phase 2 has **not started**: no official judging runs, no identity reveal, no winner, and no submitted-route characterization or seed selection. Its required event hardware/native replay gate is unmet. Live adapter work, modeld coexistence and physical listening remain pending; no live drive is authorized by a test result.


### Latest connection update

The device briefly returned, and the event branch was fast-forwarded successfully to `cfdd608238`, including the repo-level `./onroad --roadscore` dispatch. Setup and model transfer were resumed. Connectivity failed again; the resumed transfer exited on SSH timeout. The last observed USB inventory still contained no Chestnut. This is an intermittent connection/hardware blocker, not a completed event bringup. The bootstrap/replay and official setup resume logs are on the comma; their final status must be checked after reconnection.

The root launcher dispatch was tested in isolation: explicit `--roadscore` routes to the integrated launcher with all arguments preserved; ordinary replay routes to the original host runner. Both cases passed. Total completed local checks: 81 regression tests and 2 launcher cases. No judging runs were attempted.


### Hardware interruption finding

A subsequent read confirmed the same hostname `comma-14765f`, the `/data/roadscore` symlink, deployed `cfdd608`, and approximately 80 GiB free. Its uptime had reset to about one minute, so at least one actual reboot occurred; the cause is unknown. Fresh SSH then timed out again. No automatic power cycle or GPU reset was performed by this task. Further heavy setup is paused pending stable power/connectivity and Chestnut enumeration. Stale local SSH clients were closed; remote final process state cannot be certified while disconnected. No RoadScore worker, replay, audio stream, or judging run was started by this pass.

## Current event checkpoint

Source and dependencies are deployed on the event comma. Both working trees use the `RoadScore` branch. Changes remain local or are copied directly to the comma; no further publishing is authorized.

- Official Chestnut USB and YOLO examples passed on gfx1200, firmware ed4e39b7-CLEAN, with 8,539,602,944 bytes reported VRAM.
- All 744 staged ACE weight/profile files passed SHA256 verification. Native replay built successfully after repairing interrupted zero-length objects.
- First Prism attempt failed during the second VAE invocation. The first decode/readback succeeded, but no completed music asset was produced. GPU config became inaccessible, while the bridge remained readable. Timeline data repeated the bridge identifier. No driver reset was attempted by the timeout handler.
- The user reported handling the hardware and confirmed no engineer is available. An explicit offroad controller power recovery restored link 0x78. A controlled decoder-only repeat test is underway; no event Prism or native replay pass is claimed yet.
- All tests remain physically muted. No Bluetooth output was enabled.

## Route privacy

A read-only check found the RoadScore branch already present on the public repository at 51ea668d73. No RoadScore route recordings, generated scores, or result directories are tracked, but historical reports and helpers exposed real route identifiers. The user was informed. Identifiers have been removed from the local working files; historical fixture tools now require private environment settings. This does not remove identifiers from existing public Git history or change comma Connect permissions. No remote history rewrite or push was performed. The exact local audit is in ignored `results/event_night_one/route_privacy_audit.json`.

The controlled default decoder test reproduced the fault: cold call 163.49s, capture call 8.10s, both identical finite PCM; repeat index 2 lost GPU access. Peak tracked allocation was 2,470,055,936 bytes, far below reported capacity. A no-graph diagnostic (`JIT=2`) is in progress. This is a repeated event-unit failure, not a memory-capacity pass/fail inference or an identified root cause.

### Controlled decoder result: 30 W cap

Normal graph execution at 30 W completed 40/40 identical finite PCM outputs. Cold call 164.416s, capture 9.363s, warm median 2.760s (max 2.791s), host peak 321.10 MiB, tracked GPU peak 2,470,055,936 bytes. All link samples remained healthy; CPU settings restored. The no-graph attempt instead stalled on call index 1 with GPU configuration still readable and timeline 238 versus target 288.

This is evidence of load-sensitive behavior, not proof of a faulty supply. Full Prism preparation now runs under the same 30 W cap, recorded in the service state and generation provenance. Default model settings remain unchanged. No official-runtime comparison is needed unless the full workload fails.

The UI working change exposes current job elapsed time through native/host status transport. It still requires native replay validation. Privacy cleanup, diagnostics and UI changes remain uncommitted in both RoadScore working trees, with no push.

User-reported power source: approximately 120 W, 12 V brick; rating and delivered voltage/current have not been independently measured. The cap result does not establish that the supply is undersized.

### Full Prism preparation and native integration

At 30 W, Prism prepared 112s of accepted audio in 591.215s from worker start, with 38.228s model load and 783,356 KiB peak host RSS. All four initial sections passed without rerolls. Warm continuation required approximately 44s per 28s of new material (RTF 1.57–1.58); this cap is stable so far but is not faster than playback.

The first native replay rendered camera/path/lanes and the overlay, then its audio process failed after 22.1s when an ACE request accessed an absent legacy SA3 anchor. No underflow occurred before the exception. Evidence remains in `results/normal_1789793308/failed_score`. The general fix excludes SA3 anchors/cache checks from ACE requests without changing its boundary DSP policy. Native receiver/launcher supervision now propagates score-process failures. A same-route muted retry is running under `results/normal_1789793554`. Its first fresh music request succeeded in reaching the worker. No full replay pass is claimed until EOF and audit.

### Replay retry outcomes and next bounded power test

- `normal_1789793554`: full 254.1s EOF, 5,091 camera frames, navigation, 10 curves, zero future-input violations, zero underflow, all blocks muted. Failed fresh-generation acceptance: one real quality rejection followed by a zero-attempt deadline deferral was incorrectly counted as a second bad generation. The healthy worker was marked failed and accepted music was held.
- General correction: `GenerationBudget` distinguishes deadline deferrals from quality failures and uses measured warm generation cost to reserve time with accepted-music holds. Three targeted regression tests pass.
- `normal_1789793863`: accepted three fresh continuations (~46s each), no GPU fault. Later holds could not preserve the exact latent context after an intentionally faded closing section; generation was deliberately suspended. At route time ~227.5s, the separate causal replay bridge detected 1.35s timing drift and stopped. This is not a clean native pass. Original current-run files are retained in its `failed_score` folder.
- The replay timing guard has not been relaxed. Phase 2 remains unstarted. No modeld coexistence or live driving claim.
- Resident Prism was stopped cleanly before a bounded 45 W fixed-decoder test (40 calls). The default ACE worker cap stays 30 W unless explicitly overridden. Further musical logic changes wait on this performance/stability comparison.

ACE is now the event default; explicit SA3 selection is preserved. Composer tests pass with the existing analysis environment (the system Python lacked SciPy). Native launcher supervision and UI state changes remain local/unpublished.

### Coexistence investigation (read-only, not executed)

Actual native Params report `Model=DrivingModel=rdf43`, version v15, real `IsOnroad=false`. The built-in model path uses the QCOM backend and does not select an external-GPU artifact merely because Chestnut is connected. Model Lab configuration must still be checked before any test.

The existing `selfdrive/test/process_replay/process_replay.py` supports isolated `modeld` execution in an `OpenpilotPrefix`, feeding road/wide camera frames and device/calibration/car state; it publishes modelV2, drivingModelData and cameraOdometry. The cached known route contains `fcamera.hevc`, `ecamera.hevc` and rlog. A bounded test should call that local harness directly and record execution times first alone, then during ACE generation. Do not use the CI model-replay report/upload entrypoint for private routes. No coexistence or live-driving test has been run.

### 45 W full preparation

The explicitly capped 45 W resident worker completed 112 seconds of accepted Prism audio in 530.441 seconds, including 38.190 seconds model load. Peak host RSS was 758,308 KiB; tracked allocation reached 5,789,487,104 bytes. Initial 28-second music required 13.651 seconds generation plus 6.206 seconds decode (0.709 RTF excluding cold compile). Warm continuation required 19.51–19.59 seconds generation plus 10.30–10.32 seconds decode per 28 new seconds (1.065–1.068 compute RTF; 30.12–30.42 seconds wall). This does not establish sustained faster-than-playback continuation.

Native muted replay `normal_1789795416` is running without continuous UI video encoding. Camera/path auditing and the overlay image remain enabled; the causal timing guard is unchanged. No event native pass is claimed before its final audit. Exact preparation metadata is preserved privately in `results/event_night_one/prism_power45/`.

### First clean event native replay — 45 W

`normal_1789795416` passed the instrumented native gate through final-segment EOF: 254.1 seconds captured, six accepted fresh generation jobs, zero accepted-music holds, zero underflows, zero emergency fallbacks, no worker failure, zero output flags and all blocks muted. Camera accepted 5,088 frames; path/lane drawing, navigation and ten curve activations were observed. All request timestamps were causal. Maximum source-clock drift was 24.671 ms. Continuous UI video encoding was disabled; the overlay snapshot and UI audit remain available. This single pass does not prove that encoding caused the earlier timing failure.

The local private evidence is `results/event_night_one/prism_power45/`: preparation metadata, native audit, overlay and captured score. The reusable post-run audit correctly rejects the earlier full-route failure and has three focused negative-evidence tests. It does not claim human musical approval, physical speaker/Bluetooth validation or modeld coexistence. Phase 2 has not yet begun; the native prerequisite is now met. No upload or push was performed.

### Private judging batch setup

After local checkpoint `f75a98181f`, all eleven unique submissions returned native route-file listings. Private complete-route caching has begun. The private manifest fixes anonymous labels, route-derived seeds, common Prism/45 W/muted settings and objective excerpt rules before any judging playback. Exact identities and acquisition logs remain ignored/private.

Checkpoint `963d069778` adds optional deterministic sampling: separate preparation/continuation seed streams, request sequence independent of wall-clock job filenames, and rejection of a mismatched resident preparation. Legacy sampling remains unchanged unless explicitly configured. Three seed tests and six composer tests pass. Submission A's first attempt is preparing; the single-attempt runner waits for its matching preparation and complete ordinary route cache, then performs muted native replay. It refuses automatic reruns. No listening scores or winner exist. Range-disambiguation entries remain blocked from launch until their metadata decision is recorded.
