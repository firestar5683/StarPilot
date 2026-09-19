# RoadScore at COMMA_HACK 7

RoadScore turns causally delivered road context into a locally generated adaptive score. ACE-Step 1.5 turbo is the pretrained base model; **Prism** is the primary prepared musical profile and Aurora is an explicit alternative.

Our work includes the native tinygrad Chestnut port, continuation and buffering, pre-playback quality checks and bounded rerolls, immediate deterministic gestures, replay integration, UI, and private score archives. We did not train ACE-Step.

The pipeline is:

recorded cereal → semantic road state → section requests → ACE on Chestnut → quality checks → PCM arrangement and gestures → output → route-owned archive

Only already-delivered messages enter musical decisions. The ordinary replay engine owns route resolution, camera video, path/lane display, and playback timing. Existing generated music may be held when fresh material is unavailable; holds are recorded and are not counted as new generation.

## Event status

Source lives in this repository on the `RoadScore` branch and on the event comma at `/data/openpilot/roadscore`. `/data/roadscore` is a compatibility symlink. See [EVENT.md](EVENT.md) for current measurements and preserved failures.

The official Chestnut example passed. Unrestricted decoder runs lost GPU access; a 30 W cap passed 40 repeated decodes and full Prism preparation. At that cap, warm continuation takes approximately 44s per 28s of new music (RTF 1.57). A 45 W comparison is underway. **The event native-replay acceptance gate is not yet complete.** Live/modeld coexistence and physical speaker/Bluetooth validation remain pending.

## Run on the event comma

```sh
cd /data/openpilot
python3 roadscore/prototype/worker_service.py start --composer ace --profile prism
python3 roadscore/prototype/worker_service.py status
./onroad --routeid '<dongle>/<route>' --roadscore --muted --duration 3600
```

Wait for the resident worker to be ready before replay. Initial preparation can take about ten minutes; warm throughput is a separate measurement. The duration is a watchdog, and recorded route EOF ends normal playback. ACE is now the default composer. SA3 requires explicit selection and separately staged assets; it is not currently a verified event fallback.

The ACE worker defaults to the tested 30 W cap. An explicit `AM_POWER_LIMIT` override is experimental and must be recorded with performance results. Set `ROADSCORE_DEVICE` or `--bench` for host-side device selection. Stop only the owned worker with `worker_service.py stop`.

Automated sessions must use `--muted` and keep `.session-muted`. This restriction does not change the product's eventual normal audible behavior. Attended listening needs a deliberately selected output; do not infer Bluetooth or speaker validation from captured audio.

## Private data

Routes, model weights, generated audio, result logs, and local fixture settings are ignored by Git. Do not publish them. Historical source on the public branch exposed real route identifiers; those identifiers have been removed from the current working files, but existing public history is unchanged. Local redaction does not change comma Connect sharing permissions.

Historical fixture helpers require private environment settings instead of real IDs in source. These helpers are not the arbitrary-route runtime. Keep any `fixtures.private.env` local.

<details>
<summary>Historical pre-event notes (superseded, not event validation)</summary>

## Historical prototype notes

The older instructions and measurements below are preserved for history. Their Horizon identity, special excerpt launchers and early replay limitations are superseded by the current `./onroad` path above.

# Latest listening gate: Horizon Drive

Run `./review_roadscore.sh` for the three primary audio tests: dense live continuity, energetic live curve, and phrase-aware live arrival. Timing/anchor markers are optional, and synchronized video links are labeled separately. See STATUS.md and DENSE.md. The bench remains muted by default; all work is private under this Desktop folder.

Earlier sections below are historical. The active-context/anchor system is preserved; the new identity and cadence runway are the current listening candidate.

# Current review: Horizon continuity

Run `./review_roadscore.sh` to open the new private listening lab. Generation boundaries and reused four-second identity anchors are marked. See STATUS.md and CONTINUITY.md for current measurements and limitations. The bench default is Horizon with rolling inpainting; the speaker remains muted. Musical acceptance is pending human listening.

The sections below describe the prior prototype and remain for command/reference history; older Nocturne preference and trimming claims are superseded by the current status.

# RoadScore — private bench prototype

Everything here is local/private. No remotes or uploads are configured. The public StarPilot checkout is unchanged.

## Run the current musical-quality demo

From this directory on the Mac:

```sh
./run_roadscore_onroad.sh
```

Requires the already-staged bench at `comma@192.168.3.111`, its existing Chestnut and local SA3 assets. No route downloads or dependency installs occur. Default: route 202, seconds 110–210. The recorded drive appears on the comma display with a small RoadScore overlay. Open `http://192.168.3.111:8088` during playback to select a future musical style. `./run_roadscore_demo.sh` runs without taking over the display. Cold preparation takes roughly 2–3 minutes; an existing healthy worker is reused.

**The bench speaker stays silent by default.** Actual rendered music is saved to `results/latest/heard.wav` after the run. Open that file locally when ready to listen. `results/roadscore_causal_demo.mp4` is a preserved synchronized video/audio demonstration of the successful 100-second run.

Other excerpts (numeric start/duration are replay selections, never runtime event triggers):

```sh
./run_roadscore_demo.sh <private-route-name> 170 87
./run_roadscore_demo.sh <private-route-name> 0 600
```

The native display and live video panel currently support the default route-202 excerpt only; it hides video for other routes rather than showing unrelated footage. Audio/event handling works independently of video.

## What is live and what is recorded

The dedicated replay process alone reads rlogs and republishes original cereal messages at original timing. The runtime consumes those messages. It does not read offline event selections or future route outputs. A Python audit guard additionally denies runtime route-file opens. Future-mutation tests cover the actual selected route's event detector.

Chestnut generates SA3 continuations locally in a single worker. The unchanged curve detector controls a lighter brightness/level envelope plus phrase echoes. Navigation can bias future generated development/closing passages. It does not claim that SA3 newly composes in response to a six-second-ahead curve. Navigation can choose cached broad approach/closing conditioning for later blocks; exact keys, instruments, tempo and cadences are not controlled.

In the current musical mode, valid `arrive` guidance within 40 m arms an ending; speed below 0.15 m/s for two seconds triggers it. Context expires after 30 s and resets on a new valid route. The final sonority uses estimated harmony from music already played; it is not a guaranteed tonic cadence. An already-triggered gesture can finish after log EOF. EOF itself never triggers arrival.

## Files and evidence

- `PLAN.md`: architecture baseline and implementation deviations.
- `STATUS.md`: actual test results, limitations and checkpoints.
- `prototype/`: narrow publisher, runtime, model worker, tests and local server.
- `routes/`: immutable cached original route artifacts and preflight validation.
- `results/`: saved renders, traces, model timing, comparisons and demo video.
- `chestnut_stable_audio/`, `chestnut_music/`: prior isolated feasibility work; MusicGen unchanged.

On the bench everything is under `/data/roadscore`, with pretrained SA3 files reused from `/data/sa3-feasibility`. Existing openpilot modules are imported read-only. The worker temporarily enables capped big CPU cores while offroad and restores the previous settings when stopped by its wrapper.

## Restart/failure behavior

Each run archives the previous `/data/roadscore/results/current` directory. The supervisor refuses duplicate invocations and reuses only the specific existing SA3 worker. Failed/late generation extends generated audio rather than blocking the output callback. Errors and fallback counts remain visible. A new run ignores older job IDs. Seek/pause/speed changes and live onroad integration are outside this prototype.

The output WAV records the rendered callback buffers before muting; it is not a microphone recording of the speaker. Physical acoustic output was not subjectively evaluated during unattended testing.

## Review without the bench

Open `results/curve_review.html` or `results/arrival_review.html` locally. Press play to hear the saved render; neither page auto-plays sound or makes network requests. The adjacent MP4 files also play directly. Keep these private because they contain your road footage.

Tests use the existing bench Python environment (the Mac system Python does not include scipy):

```sh
ssh comma@192.168.3.111 'PYTHONPATH=/data/roadscore/prototype:/data/roadscore-feasibility/venv/lib/python3.12/site-packages /usr/local/venv/bin/python -m unittest discover -s /data/roadscore/prototype -p test_core.py'
```

## Musical-quality listening pass

Open `results/quality/curve_review.html` for the best combined demo, `results/quality/arrival_review.html` for the later ending, and `results/quality/listen.html` for short A/B files and four distinct style candidates. Nocturne is the default because it was strongest numerically; the others still need listening and have known continuity problems. See `QUALITY.md` for controlled experiments and `STATUS.md` for the latest integrated evidence.

The native presentation uses the bench’s existing pyray/OpenCV and temporarily hands display ownership back and forth with the original UI manager. It shows actual road video and RoadScore/model decisions; normal onroad lane/path rendering is not integrated. The original UI resumes on exit.

Style selection affects future generation, so expect roughly 30–50 seconds before a request reaches playback. The current piece continues in the meantime. All four seeds and prompt embeddings are already staged locally.

Quality mode keeps the 30 s model shape, conditions ongoing passages for a longer piece and uses a ~27.96 s active window with ~8 s retained context. That produces ~19.97 s of usable new audio per ~19.4–20.3 s job in the initial combined tests. The final display-pinned run measured 19.28 s (0.966 useful RTF). This remains near real time with a narrow margin; generated-tail loops remain necessary protection for longer or slower runs. No guaranteed indefinitely loop-free claim.

Baseline rollback: tag `quality-baseline-149c3cb` and the original `results/final_timed` artifacts remain untouched. Only local checkpoints exist.

</details>
