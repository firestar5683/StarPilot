# Private integration pass

Music remains frozen at f3216fa: ignition_arc, existing continuation, 0.8 curve threshold. Human listening review remains pending.

## First unseen attempt — immutable evidence

`results/integration/first_attempt/` preserves command, f3216fa launcher, console/exit status, native host logs and bench capture. The supplied route `<private-route-id>` was launched by route ID only, without prior route inspection, caching, manual excerpt or source changes. Exit 0 without intervention: 3,631 accepted camera frames, 9,860 nonempty path/lane draws, navigation, eight curve activations, six new Chestnut jobs, 174.6 audio seconds, zero underruns/repeats. This first attempt predates host audio return, so capture was on the muted bench. UI rendering is instrumented, not visually reviewed.

Only after preserving this result was the complete native file listing cached locally: 60 files, 1,214,246,322 bytes, ten segments, road/wide/driver/low-resolution cameras plus rlog/qlog. Private signed URLs are not retained in the library manifest.

## Ownership

Mac: existing native replay and existing UI own route resolution, video and original cereal time. Ordered SSH forwards only already-published music services to the bench. The shared app and Chestnut generate/render final PCM. A Unix socket returns bounded final stereo float32 blocks through SSH. The Mac owns its audio device and FLAC capture. `--audible` means Mac speakers; the remote comma is always muted.

PCM packets carry the existing callback/source clock. The host measures remote monotonic offset, schedules output at callback time +250ms, caps the receive queue at two seconds, and records target/actual DAC estimates and late/drop counters. There is no unbounded streaming buffer. Default automation runs mute the output after capturing the identical rendered samples. A 66.2-second test had zero late frames, zero starved callbacks, zero output flags, and a maximum queue of three 100ms blocks. Physical speaker audibility and acoustic AV timing have not been listened to.

Comma: same launcher detects `/TICI`, selects the existing source tree and a privately built native replay executable. Same cereal bridge, app, musical core and generation scheduling; local output. Actual existing UI temporarily owns display; original manager resumes on cleanup. Native hardware acceptance subsequently passed; see the completed results below.

## Library and archive lifecycle

`./routes-tool inventory` reports the private library. `./routes-tool fetch DONGLE/ROUTE` uses the same authenticated native route API endpoints and fallback order, downloading all compatible listed log/camera files without printing signed URLs. Native replay reads ordinary `<route>--<segment>` directories under `routes/<dongle>/<route>/`. Resolution is library, configured `ROADSCORE_ROUTE_PATHS`/native realdata, then native remote resolution. No allowlist and no route-specific runtime features.

Scores live inside the same route parent at `roadscore/<session>/score.flac`, with timing, model/job boundaries, phase/curve/ending decisions and metadata. Actual rendered output is saved; replay does not regenerate it. A route-owned latest pointer selects the last completed score. `./routes-tool delete DONGLE/ROUTE --confirm-route DONGLE/ROUTE` explicitly removes the private route parent and its owned scores. It is implemented but no real routes have been deleted.

The repository's `system/loggerd/deleter.py` recursively deletes individual realdata segment directories, not a route parent. Therefore future live recording must rotate audio and metadata into corresponding segment-owned subdirectories. The demo library is not falsely claimed to be integrated with live realdata pruning. No live recording integration is implemented in this pass.

`./onroad --routeid DONGLE/ROUTE --roadscore --replay` selects a stored final score and bypasses receiver, clock SSH and worker startup. Playback anchors to the original first model logMonoTime and recorded host DAC/file origin. The first 30-second Mac stored-score test passes with no output flags. Pause/seek/rate discontinuities fail rather than silently desynchronizing.

## Native build notes

The device lacked a replay executable. `prototype/build_native_replay.py` compiles existing openpilot replay/msgq/VisionIPC sources and generated cereal headers into `/data/roadscore/native_build`, linking managed AGNOS dependencies. It does not modify `/data/openpilot`. The first device adapter run exposed an absent private msgq directory; the general launcher now creates its namespace before subscribing. The subsequent acceptance results and software-decoder correction are recorded below.

## Human next step

Do the listening review at results/unattended/listen.html before the next musical prompt.

## Completed native and stored-score acceptance

The actual comma UI passed first on the existing fixture (1,301 camera frames, 2,351 nonempty path draws, 3,206 lane draws; 66.3 audio seconds, two accepted jobs, no underruns/repeats). Normal UI ownership was restored afterward.

The community fixture then exposed `VIDIOC_STREAMON CAPTURE failed` in Qualcomm's hardware decoder. This is preserved in `results/integration/native_decoder_failure`. Native mode now consistently selects the existing software decoder. The retry (`results/integration/native_community`) passed: 84.7 audio seconds, two jobs, no underruns/repeats, 1,732 accepted camera frames and 3,007 nonempty path/lane draws. Its final score archived automatically. Empty-model/empty-audio sessions now fail before archival. None of these later integration fixes changes the preserved first unseen Mac result.

The same final contiguous samples were verified during stored-score playback on both hosts. Mac: 0.19ms maximum alignment error, invalid/unreachable compute-host argument, no generation. Comma: 14.3ms maximum alignment error with the generation worker stopped. Both had zero output flags. `stored_score.py` advances a contiguous sample cursor and verifies its PCM digest against the original FLAC sample range. These are instrumented output-path checks; acoustic output was not heard. A virtual loopback input stalled in CoreAudio setup and was terminated without collecting audio.

An intentional SIGTERM stopped native replay and restored the ordinary UI (PID134958 observed afterward). The external integration worker was stopped and `POWER_RESTORED` verified before the no-worker native stored-score test. The subsequent full-route Mac test failed closed on excessive transport delay; its worker was stopped. The final native full-route test completed; details follow.

## Final host scheduling correction

Callback-timestamp jitter initially accumulated up to27ms of inserted spacing in a174.4-second returned stream. The corrected host scheduler anchors the first block to the measured clock, then presents the contiguous PCM sample sequence. It checks sequence continuity and records DAC timing error, queue occupancy, output flags and late/starvation counters. A subsequent84.5-second run had exactly4,800 frames between block starts, zero inserted spacing, and0.36ms maximum measured scheduling error. The fixed added delay is250ms; LAN clock-offset uncertainty adds a few milliseconds. Saved-score playback uses the same contiguous-sample principle.

## Natural EOF

Repository inspection found that native headless `--no-loop` waits after the final segment instead of terminating. `replay_end.py` supervises the native player's own final-segment exhaustion/status and closes the cereal pipe after exhaustion. Segment bounds are never sent to the musical runtime. No ending is armed by EOF; an already-triggered cadence may finish. Intermediate segment waits and paused replay do not count as EOF. Unit coverage includes those distinctions. Full-route empirical validation subsequently passed natural EOF handling; see below.

## Ownership and privacy details

RoadScore made no source edits in the public Mac StarPilot checkout. Final inspection found unrelated concurrent changes there; they were left untouched. The bench had pre-existing July28 active-theme symlink differences; they were left untouched. All new compilation outputs and Python integration code are in private RoadScore directories. No upload, push or PR occurred. The private route library contains170 verified compatible files, totaling3,099,393,010 bytes. Original first-attempt and historical development evidence remains separate from deletable demo-library entries.

The complete musical core, worker, prompts/styles, continuation and detector remain byte-for-byte unchanged from f3216fa. Only rendering/presentation, transport, supervision, cache and archive plumbing changed.

## Longer Mac run — explicit failed acceptance

`results/normal_1789519804` rendered309.6 seconds and completed11 jobs without renderer underruns/repeats, then stopped. The last model packet took approximately767ms from host send timestamp to bench receipt, above the750ms source-clock tolerance. The audio return recorded97 starved10ms callbacks and969ms maximum timing error. This identifies an end-to-end transport/OS scheduling delay; radio alone is not proven responsible. The wrapper failed closed and did not replace the last good archive. `results/integration/long_mac_failure.json` preserves the outcome. Do not call this a full-route Mac success. Longer network-jitter recovery remains outside the completed work. The final native test removes the network from the critical replay/render/audio path.

## Final full native route and cleanup

The whole cached community route completed through the actual native UI and local Chestnut (`results/integration/native_full`, session `normal_1789520509`). Cold startup173.898s; replay575.288s; final rendered audio571.9s. There were21 accepted jobs at19.685–20.067s each (median19.884s), zero emergency repeats and one active output underrun at90.2s. The observed callback gap was about305ms; it did not overlap an app GC event. No claim is made that the hardware dropout is repaired or reproduced by the saved PCM. The archive explicitly marks its timing quality as non-clean and retains per-block DAC timing.

The existing arrival detector triggered at563.672s from recent destination context and parked standstill. It selected a3.126s runway and finished the cadence at audio571.726s. No route-specific timestamp/configuration was added. Native final-segment exhaustion ended replay naturally; EOF itself did not arm an ending.

The actual UI accepted11,270 camera frames, made21,795 nonempty path and22,014 lane draws, and transitioned offroad at the recorded ending. This remains instrumented rather than visually observed. Worker processes were absent after cleanup, `POWER_RESTORED` was recorded, saved/before and restored/after CPU JSON matched exactly, and the ordinary UI was running again (PID139744).

The full score is copied to `routes/<private-route-id>/roadscore/normal_1789520509/` on Mac and comma. This contains actual lossless rendered audio, timing,21 generation records, navigation/curve/arrival decisions, implementation provenance and explicit output-quality flags. It is the latest-score selection. Human listening and physical screen/audio confirmation remain pending.

A final cross-host test replayed the full native-produced score on Mac for10seconds with an invalid compute-host address, zero output flags, and contiguous source samples verified=True. It correctly disclosed the source recording's output interruption.
