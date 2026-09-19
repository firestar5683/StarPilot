# Event checkpoint — RoadScore branch

Current event work and exact failures are recorded in [EVENT.md](EVENT.md). Source is migrated. Official Chestnut validation and 30 W Prism preparation pass; native replay still has unresolved timing/ending-context failures. A 45 W fixed-decoder comparison passed 40/40 and full-model testing is starting. No event-baseline or judging-batch pass is claimed. All automated audio remains muted; no files have been pushed by this work.

Everything below describes preserved **pre-event** evidence, not the current event unit.

---

# Current result — Prism demo hardening from 08ba22e

**Prism is the primary native demo candidate; Aurora is the verified selectable backup. Circuit is archived.** The requested instrumented regressions pass. The intermittent GPU/link fault remains unresolved, so this is not a production-reliability claim.

- The final pre-commit gate catches committed quiet gaps before playback, preserves soft passages/intentional outro fades, and permits at most two same-role deterministic rerolls within the buffer deadline. Known bad native/reference cases and real route rerolls are preserved.
- Thirty native continuations produced 840s of new music in 694.97s (0.827 RTF); all remain accepted by the final policy. Final-policy full curve replay measured 0.888 RTF including qualification/persistence, with 64.8s minimum buffer and no two-second quiet span.
- Full native Prism arrival, curve and community routes passed normal UI/camera/path/lane/causal checks without underflows, emergency fallbacks or output flags. Aurora completed a full 254.2s route and archived correctly. Its startup exposed screen-off CPU interference; the private CPU-only supervisor fix subsequently corrected that transition automatically during SA3 preparation.
- The first composer-stop test exposed callback blocking. After the fix, four accepted-music holds completed with zero output errors and truthful DEGRADED status. No reset or model handoff occurs during playback.
- The smaller fixed-chunk decoder reproducer localizes genuine link loss to after submit and before the driver timeout handler. Compute-only also fails; a 40-repeat idle comparison passes. Root cause is still unknown.
- Mac fresh retest, SA3 and Mac/native stored replay pass. The first Mac fresh test missed deadlines during a 1.138s transport burst; retain that operational risk and prefer native playback for the demo.
- Curve Apex V4 and the conservative bridge are available in the focused review. Human musical/salience judgment and live modeld coexistence remain unverified. Twenty focused tests and the existing regression coverage pass.

[Evidence report](ACE_DEMO_HARDENING.md) · [Focused listening review](results/ace_demo_20260916/index.html) · [Launch/recovery checklist](results/ace_demo_20260916/DEMO_CHECKLIST.md) · [Validation](results/ace_demo_20260916/validation.json).

**Clean shutdown verified:** owned workers/replays stopped; locks free; normal offroad UI/manager and saved CPU settings restored. Mac and bench remain muted, both session mute locks are present, and no speaker or Bluetooth output was intentionally enabled. Public StarPilot is clean; MusicGen is untouched; route/audio artifacts remain private/local.

---

The records below are historical and are superseded by the current evidence above.

# Historical result — ACE stability pass from b719139

**ACE remains the strongest composition candidate, but the full stability/continuity gate has not passed.** Read the [current report](ACE_STABILITY.md) and [Mac/Chestnut listening review](results/ace_stability_20260916/index.html). Earlier checkpoint claims below are superseded by this pass’s evidence.

- Deterministic Mac/native harness, three new identities at30/45/60s, five identical native repeats, same-latent VAE tests, layer/step diagnostics and the15–60s shape sweep are complete.
- Fixed45s continuations retained555s of new music in454.17s compute (RTF0.818). Two20-job soaks passed. Three complete native routes reached EOF with39accepted fresh jobs total and zero underflow/fallback/hang. Native stored playback and a headless Mac fresh ACE transport retest passed.
- Aurora and Circuit each completed six linked native sections, with exact prefixes and at most0.1/0.2s measured quiet. Their prepared bundles are available; human approval and full-route tests for these two profiles remain pending.
- The terminal-fade guard repairs the earlier flow, but full Prism routes exposed5.1s and2.7s interior gaps. Both reproduce with identical inputs in the official reference. Seed/role/prefix/preservation/refreshed-timbre counterfactuals did not provide a reliable real-time fix. **Musical continuity remains failed.**
- Three56s decoder/runtime failures are preserved, including two VAE-only probes at2.470GB allocation. The latest captured an unhealthy link read before process teardown. Recovery restored the bench; initiating cause remains unresolved. **Do not claim production reliability.**
- V3 signal/curve gestures are rendered and tested; perceived salience and subjective port fidelity require human listening. Exact reconstruction of the old approved performance is blocked by missing original random preparation state; honest recovered-code/new-boundary A/Bs are supplied.
- Cold ACE buffer preparation took about12.6minutes. Warm throughput does not imply instant readiness. No live driving/modeld coexistence claim follows from offroad replay.

Fresh native SA3 fallback passed:116.6s captured, three jobs atRTF0.776–0.780, zero underflows/fallbacks/output flags. All owned workers/replays have stopped; the normal offroad bench UI is restored and CPU restoration is verified. Mac and bench remained muted; no speaker or Bluetooth output was intentionally enabled. Public StarPilot is clean; route/audio files remain private/local. MusicGen is untouched.

---

## Previous checkpoint record (b719139; historical)

# RoadScore — ACE Chestnut result

**ACE now generates and decodes music locally on Chestnut faster than playback at useful short horizons.** Keep it as the primary experimental composer; SA3 remains the working default/fallback. The prepared-identity continuation loop needs no Mac during generation. Arbitrary new identity preparation is still a Mac development step, not a demonstrated comma CPU capability.

[Start with the listening review](results/ace_chestnut_20260916/index.html). It includes native music, a142s verse→prechorus→chorus→bridge→outro, arrival, distinct V2 gestures, and the actual native road score. Nothing autoplays. Human approval applies to the earlier Mac ACE reference; **native continuity, endings, and gesture salience remain unapproved until listening**.

| Measurement | Result |
|---|---|
| FP16 generation + native decode |15s in7.42s;30s in12.55s full decode or15.39s bounded decode;45s in22.52s |
| Warm continuation |28s genuinely new material in20.36–20.97s isolated;21.57–21.81s during native replay |
| Longer horizons |60s takes80.07s;90s latents decoded only after recovery, so no complete90s RTF claim |
| Memory |~4.215GB tracked GPU peak; composer~471–493MiB host peak/RSS, plus compiler helpers and replay/audio/UI |
| Cold readiness |447.8s including initial58s score and both graph shapes; preparation must precede playback |
| Native ACE replay |Full254.3s arrival route,7 accepted fresh sections, minimum buffer8.1s; zero fallbacks, underflows, or output flags; camera/path/lanes/nav/10 curve activations verified |
| Arrival |41.2s of generated outro heard before cadence; weak harmonic confidence used source-tail release, not an invented chord |
| Mac fresh ACE |Composer kept up, but PCM transport failed clean timing:46 starved callbacks /21,257 late samples. Preserved as a failure, not a pass |
| Stored-score regression |Mac120s: exact samples, zero flags,0.604ms alignment. Native ACE120s: exact samples, zero flags,8.104ms |
| Fresh SA3 fallback |Mac120s,3 new sections atRTF0.782–0.784, zero starvation/late frames/output flags;0.524ms alignment |
| Precision |Native numerical checks pass against official references. INT8 storage offered no speed/resident-memory benefit; rejected. Explicit32-token alignment failed the unchanged maximum-error gate; rejected |

Use the existing command with `--composer ace` to select the experimental prepared backend. Omitting it keeps SA3. Runtime consumes causal cereal messages, not future route files. Route-owned archives remain private and compatible with stored-score replay. No public StarPilot or MusicGen edits.

**Readiness classification: Level3, demonstrated prebuffer viability; Level4 throughput evidence on a full offroad route, not a reliability or production claim.** Two earlier stress-test GPU hangs required recovery. modeld coexistence and real driving are untested. ACE→SA3 seamless handoff is not implemented. A Mac transport-timing issue remains explicit. Final regression and cleanup details follow in the engineering report.

[Architecture, experiments and limitations](ACE_CHESTNUT.md) · [Native replay evidence](results/ace_chestnut_20260916/native_replay_audit.json) · [Mac failed capture evidence](results/ace_chestnut_20260916/mac_replay_audit.json).

Final checks:68 unit tests and5 V2 gesture tests pass; native ACE and default SA3 fresh regressions pass as described above; stored playback passes on both hosts. Owned workers are stopped, normal bench UI is restored, real offroad state verified, and CPU settings restored to their saved snapshot. **Mac and bench remained muted; no speaker or Bluetooth audio was enabled.**

## Previous pass (historical)

# RoadScore — composition strategy review

Continue from private checkpoint`a7dc34f` /`overnight-review`. The human rejected the previous section-bank music. That verdict stands; the old engineering successes do not establish musical acceptance.

**Start with [the new listening review](results/composition_20260916/index.html).** One page contains SA3/ACE comparisons, YuE's limited result, generated transitions, source-derived gestures, actual arrival excerpts, replay evidence and timings. Nothing autoplays. All musical judgments remain pending human listening.

## Recommendation

Keep SA3 as the demonstrated fast Chestnut backend, but do **not** assume it has solved composition. Listen to ACE-Step's90-second structured piece and outro next to the single aggressive SA3 control. ACE is a plausible longer-horizon composer candidate; it has not earned a musical win or a Chestnut port. YuE ran but was slow and much of its latter half was near-silent. No fine-tuning, compatibility layer, or speculative accelerator port was undertaken.

The minimum prototype separates longer-horizon generated material from immediate source-derived musical gestures. It now uses continuous generated transitions rather than the rejected independent section bank. This is still an experiment, not a claim of convincing verse/chorus hierarchy or seamless multi-model composition.

## What changed and what was measured

| Area | Evidence |
|---|---|
| SA3 control | One fresh K-pop/game-score identity, five extreme roles, three context-conditioned transitions.28.05s role outputs take about19.3s. Live26.006s continuations run at medianRTF0.77–0.78 on Chestnut. |
| ACE-Step1.5 | Official MLX stack on local M1 Max.90s in108.03s (RTF1.20); five30s reference-conditioned roles take63–91s;40s transition73.33s. Actual decoded WAVs retained. |
| YuE2 | Official MPS implementation generated81.279s in374.55s (RTF4.61), without hitting token caps.37.7s near silence; symbolic keyF minor despiteD-minor prompt. No further porting investment. |
| Gesture bank | Source-derived hats, fills, crashes and finite nav/arrival phrases. Tempo/phase estimated; no new guessed chord pitches. Synthetic first-signal onset115ms, zero scheduling lateness. Physical response also includes polling/output buffering. |
| Causal road controls | Native signal, curve and nav inputs produced gestures. Upcoming curve payoff follows current forecast revisions until one beat away; no future route data. Stored overlay exposes only decisions already reached on its sample timeline. |
| Arrival | Native arrival:35.236s of outro-conditioned material before cadence. Full community run:21.653s, with corrected counter. Whether either sounds like an intentional outro is unverified. |
| Native fresh replay | Arrival253.9s/8 jobs and curve176.3s/6 jobs; zero fallback loops, renderer underflows or output flags. Camera/path/lane evidence preserved. |
| Mac fresh replay | Full community route571.6s/21 jobs, normal UI, zero starvation/late samples/output flags, maximum alignment0.324ms. Route-owned archive complete. |
| Capture limitation | Fresh video-recording attempts failed timing checks on both hosts; originals retained. No tolerances weakened. Separate stored-score video validation follows below. |
| Tests |63 passed, including real-log future-mutation causality, gesture scheduling/cancellation, outro accounting and archived decision visibility. |

[Full architecture, model screen and limitations](COMPOSITION.md) · [Measured replay evidence](results/composition_20260916/regressions.json) · [Preserved failures](results/composition_20260916/failures.json) · [Local route inventory](results/composition_20260916/route_library.json).

## Musical acceptance questions

- Obvious SA3 section hierarchy? **Pending listening.**
- Better generated transitions and fewer audible splices? **Pending listening.** Context-generated comparisons exist; no seam-quality claim.
- Alternative structurally better than SA3? **Pending listening.** ACE is the next comparison, not a declared winner.
- Alternative ready for Chestnut? **No demonstrated port.** Memory/runtime estimates do not establish impossibility or a pass.
- Useful hybrid? **A plausible direction, partly prototyped.** Immediate gestures and long-horizon SA3 conditioning run; a coherent ACE→SA3 composition system has not been demonstrated.
- Immediate signal / curve punctuation? **Sample-timed prototype demonstrated.** Beat/key accuracy and musical effectiveness remain unverified.
- Actual outro before cadence? **Generated outro-conditioned material demonstrably played first.** Its musical concluding behavior still requires a human.
- Existing replay intact? **Fresh Mac/native tests passed without video recording.** Recording failures are explicit; stored tests and final cleanup are appended below.

All work remains private in Desktop/RoadScore and the offroad bench. Cached routes were not redownloaded or published. MusicGen and the public StarPilot source were untouched. Product audible defaults were preserved; this development session remains muted.

## Stored replay and shutdown — complete

- Mac stored replay with normal-UI video:180.03s, exact contiguous archived samples, no generation or output flags, maximum clock alignment0.583ms. [Synchronized video](results/composition_20260916/road_synchronized.mp4). Captured UI has occasional frame gaps (maximum149ms); timestamps are preserved.
- Native stored arrival:253.84s of callbacks, contiguous archived samples verified, no generation or output flags, maximum clock alignment9.90ms. Normal bench UI restored afterward.
- Resident Chestnut worker stopped; saved CPU settings restored exactly. Real bench state remains offroad.
- Mac output muted, both session mute locks retained, all tested audio streams muted. **No speaker output or Bluetooth audio output was intentionally enabled; bench test output remained muted.** Physical listening is deferred.

Source/strategy checkpoints this pass:`08246ed`,`0b72f6e`,`9ee1dbb`,`dc27742`; final private checkpoint recorded in Git. Earlier rejected music and both failed capture attempts remain available as evidence.
