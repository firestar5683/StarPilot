# Verified Future-Horizon Findings
Baseline: architecture investigation in the preceding conversation, StarPilot 64f8b75551196af9149ff92c47331ef3c3ff31a5. Model trajectories: 33 quadratic offsets 0–10 s; lane/edge positions 0–192 m without times. Longitudinal ego plan: 17 samples through 2.5 s; MPC lead trajectories: 13 through 10 s. navInstruction includes current guidance and up to three maneuvers; navRoute is event-driven full geometry without timed trajectory. Full rlogs required; modelV2/navRoute absent from qlogs. Mapd producer source is not available here; determine actual usefulness from logs.

Sources: selfdrive/modeld/constants.py and fill_model_msg.py; selfdrive/controls/lib/longitudinal_planner.py; cereal/services.py, log.capnp, custom.capnp; starpilot/navigation/navigationd.py and route_engine.py; tools/replay/replay.cc; system/loggerd/loggerd.cc.

# Implementation baseline
Private external workspace only. No uploads/push/PRs. Use cached original rlogs and existing LogReader/messaging. Replay historical model outputs; never run driving inference concurrently with SA3. Runtime detector/music process receives published events only and never reads route files. Historical logMonoTime controls availability; timestampEof + trajectory offsets establishes observation-relative prediction time. Never use end-of-file as arrival. Offline event selection may identify excerpts but not provide runtime triggers.

One event first: sustained model-predicted curve, then slowdown if needed. Predicted lateral acceleration = orientationRate.z * velocity.x. Require persistence ~0.3 s and avoid low-speed artifacts; initial 0.8 m/s² curve threshold, 0.5 release. Validate actual anticipation using later vehicle motion in offline evaluation only.

One exclusive Chestnut worker runs existing native SA3, fixed 30 s. Measured warm generation+decode 18.53 s; CPU prompt encode 3.76 s; continuation 19.34 s per ~22 new seconds; cold startup ~177 s. Cache conditioning, reuse ~8 s tail, prewarm, buffer ~52 s, request at 30 s remaining. Deterministic generated-tail loop if late. No finite buffer guarantees survival of a GPU hang. No model shopping or optimization absent integration blocker.

CPU Conductor: anticipation → event → release, brightness/filter/gain/rhythmic envelopes applied to locally generated music. No steering-to-pan or speed-to-tempo. Six-second-ahead curves cannot depend on new SA3 output. Navigation can influence later composition only when already available with sufficient lead (roughly 30–52 s under buffer policy). No precise neural cadence/tempo/stem promises.

# Order and acceptance
Inventory all three routes lightly, choose defensible curve, get sequential on-device replay and generated audio audible early. Validate >=2 s anticipatory response, no future leakage, repeatability, timestamps. Local git checkpoint. Then continuous generation, late-job fallback, synchronized local UI/video, navigation/reroute, arrival, slowdown, polish. Prefer existing replay executable; if unavailable use narrow paced LogReader publisher. Isolated messaging prefix. No production changes.

Test future-mutation invariance, missing/invalid/stale messages, persistence, low speed, source ages, audio continuity/clipping/deadlines, reroute invalidation, arrival independent of file ending. Ten-minute rehearsal target. Standalone local debug UI acceptable. Record actual results and failures in STATUS.md. Keep best known runnable checkpoint.

# Empirical implementation notes
- The bench has no compiled tools/replay/replay executable. A narrow original-message publisher uses existing LogReader/cereal instead. One-segment prefetch avoids a measured ~1.2 s segment-load delay; audio result resampling occurs in a background thread.
- Recording commit c3e4ec630f41c4baa43254a90f718abd1bf764a1 parses with the checkout schema. carState.yawRate is zero in these recordings; offline physical verification uses steering and video, never that zero field.
- Route 202 is the primary bend demonstration. Route 201 has four valid route-geometry updates; route 203 supplies arrival validation.
- Camera frame zero is ~1.451 s after route-202 log origin. The selected video export accounts for this offset; frame-count agreement alone did not establish temporal alignment.
- First curve anticipation occurs at 135.275 s; sustained steering onset is ~141.53–141.58 s depending on sampling, ~6.26 s later. Runtime has no copy of the steering-evaluation timestamp.
- Locally encoded approach/closing prompts are cached so repeated CPU encoding does not consume the 2.7 s continuation throughput margin.
- Bench output is now muted by user instruction; rendered audio is recorded before zeroing speaker samples. The capture is not acoustic evidence.
- Arrival prototype uses the navigation producer's creeping-speed scale (<2 m/s), not a strict parked-state threshold. A strict <1 m/s rule missed route 203 before nav invalidated at arrival. Valid arrival-zone context held for 3 s triggers a 6 s fade. Harmonic cadence remains unproven.

- A long run sustained 575.8 s, 23 accepted continuations and no output flags. Rejecting stale navigation-conditioned work can intentionally require a generated-source loop even while the worker is faster than playback.
- Bound a continuing curve peak to its initial estimate ±2 s and matching direction, avoiding indefinite drift into a later bend. Exact physical-apex alignment remains a listening/video tuning task.
- Audio sample counts alone have a callback-boundary ambiguity relative to replay. Final evidence records callback monotonic wall time against replay origin; it does not claim acoustic output timing.

# Current continuity pass (supersedes prior quality preference)
Human review rejected Nocturne and the earlier endpoint trimming/level-match approach. Horizon is the primary source. The private experiment now uses the existing inpaint mask to preserve active four-second context at both ends of a 324-frame window. The trailing anchor is a disclosed recurring fragment selected from already-generated opening audio. Chestnut generates the ~21.92-second interior; ~4.09 seconds are reused identity material. This is a hybrid composition strategy, not 26 seconds of wholly novel output. No silence repair, stretching or route-specific soundtrack selection.

The four-job raw Horizon probe produces 125.945 seconds including its initial source. Warm jobs take 19.27–19.43 seconds: useful playback RTF .741–.747 and unique-material RTF .879–.886. This supports live validation, not subjective acceptance or an indefinite performance guarantee. Compare actual envelope plots and listen across disclosed boundaries in results/continuity/listen.html. Original failed artifacts and tag continuity-before-865e43d are preserved.

After the raw probe, validate the identical runtime policy muted on the existing curve, arrival and a second route. Keep the detector unchanged. A small prompt-embedding blend supplies establish/explore/develop/build/release intent; it cannot guarantee a perceptual trajectory. Arrival investigation found reverse at ~232.2 s and park at ~255.1 s. Do not equate the first reverse with the exact ending: require recent destination context plus sustained low-speed braking reverse and subsequent navigation invalidation, or a verified stop/park fallback. Continue the generated closing while that maneuver begins.

Normal onroad replay integration and live modeld coexistence remain later milestones. Do not extend native_display. This pass runs without display takeover and packages the existing timestamp-aligned road video for private listening.

# Dense musical pass
Human review provisionally accepts the e3477e2 sparse Horizon continuity and likes its cadence. Preserve the active-context/anchor method. Stress-test one energetic Horizon Drive identity with percussion/bass/layered-arrangement prompts; no alternate models, training, route-specific tuning, onroad UI or production work. First unchanged dense stress run completed 210.2 seconds with seven jobs and zero flags/loops. Then use explicit arrangement-stage prompts, a modest generated-transient reprise vocabulary, and a 0.8–3.5-second pulse/release-aware runway into the same cadence. The causal vehicle trigger and road detector remain unchanged. See DENSE.md and results/dense for the new gate and disclosed anchor-entry timing flags.
