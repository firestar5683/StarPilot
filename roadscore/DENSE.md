# Horizon Drive — denser continuity and musical finalization

## Human baseline and preservation

The review of e3477e2 provisionally accepts sparse Horizon's active-context/anchor continuity and harmonic development. It likes the final cadence but rejects its abrupt entry. This pass preserves that architecture and cadence, and tests a deliberately more transient-rich source. `dense-before-e3477e2` preserves the prior implementation; its recordings remain under results/continuity.

## Focused conditioning experiment

One new identity, Horizon Drive, requests a 108 BPM instrumental electronic/post-rock band with drum kit, bass, rhythm guitar, lead motif and synth counterlines. Eight cached text conditions cover base, explore, develop, build, peak, release, closing and approach. Encoding is local CPU T5Gemma from existing weights; no network or model changes. These words are intentions, not proof that each instrument was produced.

Two fresh seeds were tested. Seed 7301 was selected before the live test for stronger high-frequency transient content and a pulse estimate close to the requested groove. Against sparse Horizon's first 21.92 seconds, its transient detector reports 3.19 vs 1.92 peaks/second, high-band energy share 0.141 vs 0.024, normalized spectral flux 0.109 vs 0.063, and estimated pulse ~107.4 BPM. Seed 7302 also estimates ~107.4 BPM with 3.24 peaks/second. These metrics are diagnostics; they do not identify drums/bass or establish taste. Both seeds are in the collapsed listening diagnostics.

The selected opening is a route-independent generated identity seed. It is not a pre-generated route soundtrack. All subsequent accepted continuations were generated during the live captures; startup uses one matching prewarm as before. This is still the private prototype workflow, not a finished cold arbitrary-route launcher.

## Dense continuity stress test

First, the existing architecture and old prompt-blend/Conductor ran unchanged with the dense source for 210.2 seconds. Seven live jobs were accepted; no fallback loops or PortAudio flags; minimum buffer 10.24 seconds. Playback RTF median ~0.746. No -50 dBFS/100 ms windows appeared before EOF. Pulse estimates across 20-second sections stay near 107–109 BPM, with transient rates roughly 2.2–3.2/second.

Every transition into new model material and every audible suffix-anchor entry is checked in `boundary_metrics.json`: 21.920, 47.926, 73.932, 99.939, 125.945, 151.951, 177.958 and 203.964 seconds. Both the model-created transition into the suffix anchor and the next continuation boundary matter; listening plots shade all anchor intervals. Estimated pulse displacement across the initial stress-test joins ranges from ~0.001 to ~0.150 beats. That is an approximate analysis window result, not proof of sample/beat alignment or inaudibility. Suffix-anchor entries in the initial stress run show estimates up to ~0.257 beats. The later arrangement run shows ~0.35–0.36 beats near 43.84, 95.85 and 199.88 seconds. An interior control window also reaches ~0.311 beats, so these estimates are noisy and confounded by changing instrumentation. Those entries are explicit listening flags, not declared inaudible joins. No silence removal, stretch, gain repair or offline seam editing was applied. This evidence did not justify redesigning the architecture before human listening.

The unchanged per-job budget is 324 latent frames, 44 retained prefix frames, 44 reused suffix-anchor frames, and 236 newly denoised interior frames. Each job appends 26.006 seconds: 21.920 new plus 4.087 reused anchor. The common-context splice remains two seconds. The anchor still repeats; dense human listening must judge whether that repetition becomes conspicuous.

## Arrangement and immediate road response

After the stress test, Horizon Drive's live sequence uses explicit explore/develop/build/peak/release text conditions instead of interpolating base/development embeddings. Closing overrides this cycle using already-available navigation. The prompts request changes in bass movement, percussion density, guitar/synth layers and harmonic tension; they cannot guarantee those outcomes. The initial source and prewarm establish the groove. Accepted-job count advances the cycle, so time/route IDs are not baked into musical logic.

The curve detector is untouched. `DrivingDSP` is enabled only for Horizon Drive: it extracts transient-rich high and low bands from the generated mix, stores short non-feedback delays at estimated eighth/sixteenth intervals, and brings in modest reprises as anticipation develops. A short attack reinforcement marks the event, and release reduces the additions. Existing phrase echoes remain. Severity comes from the detector's predicted lateral-acceleration strength, bounded to modest intensity. This does not provide stems, new drum composition or a guaranteed beat grid. It is a deterministic source-derived rhythmic texture; listening must determine whether it feels like a build or merely extra echoes. No stock drum samples or universal drop.

## Cadence runway

The causal vehicle trigger is unchanged from e3477e2. At that trigger, no more generation is requested, road-event embellishments subside, and the current musical thought is allowed a bounded continuation. A 10 ms spectral-flux pulse estimator examines already-generated recent music. When periodicity confidence is at least .25, it evaluates beat-grid opportunities 0.8–3.5 seconds ahead; otherwise it evaluates local energy-release opportunities. It favors a decayed passage before the landing and avoids an impending attack. It reads only audio already in the buffer, never future route events.

This is **not bar or phrase recognition**. Sparse old guitar also yields apparently high autocorrelation confidence, so confidence alone is insufficient to establish a real beat. A synthetic 120 BPM transient test verifies timing mechanics; the dense source's estimate near requested 108 BPM provides supporting but incomplete empirical evidence. The live delay and alternatives are recorded in ending.json.

The final five-second sonority synthesis is unchanged. Its harmony is estimated from the generated audio leading up to the selected landing, and its start is sample-aligned inside the audio callback. Unlike a naive delayed-start change, samples before that future entry remain unchanged and do not play the cadence early. The existing 300 ms overlap into the cadence is preserved. Tests cover early-playback prevention, bounded delay, weak-pulse release selection, and lack of queued audio. No fixed arbitrary arrival delay or later vehicle trigger was substituted.

## Review and limitations

`results/dense/listen.html` presents the three primary audio tests directly: long dense live continuity, live curve, and phrase-aware live arrival. Timing markers are optional; video links are explicitly labeled optional. Diagnostics and seed candidates are collapsed. All artifacts remain local/private. Human musical success is not claimed.

The implementation still cannot isolate true drum/bass stems, prove exact bar boundaries, guarantee instrumentation or demonstrate modeld coexistence. No new onroad visualization, launcher architecture, training, model shopping or public StarPilot edits occurred.

## Capture/verification limitations

The long final capture and curve dry PCM diagnostics each contain one full-scale channel sample after resampling. Their actual conducted listening captures contain no full-scale samples. Files were not repaired or gain-adjusted. The same-source curve diagnostic differs by about 5.1% RMS from the previous effect over its 27-second window; this establishes that the added processing is present, not that it is compelling.

The local browser rejected file-URL access during layout verification. No workaround was used. All three primary players, WAV headers/durations, local audio/video links, and absence of autoplay were checked statically; browser rendering was not verified. Initial harness setup needed the existing soundfile import path, and video packaging needed the installed ffmpeg absolute path because the shell PATH omitted it. Both were corrected without new dependencies.
