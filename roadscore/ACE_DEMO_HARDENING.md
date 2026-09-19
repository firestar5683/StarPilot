# Prism demo hardening

Prism is the primary ACE identity; Aurora is the selectable backup; Circuit is archived and excluded from active selection. The native comma path is the recommended demo path. The quality gate, bounded retries and accepted-music holds have passed their focused hardware tests. **The intermittent GPU/link fault is not fixed, and this is not a production-reliability certification.** Prism/Aurora route checks, SA3, Mac/native stored playback and final shutdown checks all passed.

All work is private under Desktop/RoadScore and `/data/roadscore`. Baseline `08ba22e` is preserved as `ace-demo-baseline-08ba22e`. Public StarPilot and MusicGen are untouched.

## Measured results

| Check | Result |
|---|---|
| Native Prism soak | 30 accepted continuations; 840 seconds of new music in 694.97 seconds, **0.827 RTF**; no retries |
| Soak continuity | All 30 latent prefixes exact outside the 12-frame blend; longest quiet span 0.6 seconds in the 868-second joined render |
| Final-policy full curve replay | **0.888 RTF** including qualification/persistence; 363 seconds of new music in 322.19 seconds; 13 jobs |
| Final-policy memory | 5,789,487,104 tracked Chestnut bytes including allocator cache; worker host high-water mark 761 MiB |
| Cold Prism preparation | 511.9 seconds; 112 seconds of accepted starting music; four jobs, no retries |
| Arrival route | 254.1 seconds captured; seven jobs; one successful reroll; minimum buffer 42.9 seconds |
| Community route | 570.3 seconds; 19 jobs; one successful reroll; minimum buffer 41.3 seconds |
| Corrected curve route | 402.9 seconds; 13 jobs; minimum buffer 64.8 seconds; **no two-second quiet spans** |
| Normal native replay | All three Prism routes reached EOF with camera/path/lane/navigation data and causal delivery verified; zero underflows, emergency fallbacks or output flags |
| Focused section flow | 204 seconds, six fresh transitions, no retries; longest quiet span 0.3 seconds |
| Composer-stop containment | 176.7 seconds; four accepted-music holds; zero underflows/output flags; no two-second quiet spans; DEGRADED reported |
| Mac fresh retest | 176.4 seconds; zero missed frames/starvation/output flags; maximum alignment error 0.923 ms |
| Mac stored playback | 120.01 seconds; exact contiguous samples; no generation; zero flags; maximum alignment error 1.125 ms |
| Aurora full route | 254.2 seconds; seven jobs, no retries/holds/output errors; minimum buffer 64.6 seconds; profile archive verified |
| SA3 regression | 116.9 seconds, four fresh jobs at 0.758–0.777 RTF; no underflows/fallbacks/output flags; CPU restoration verified |
| Native stored regression | 120.02 seconds of the Aurora archive; exact contiguous samples, no generation, zero flags; maximum alignment error 8.708 ms |

The 30-section soak used the first gate revision. Every saved section was rechecked with the final playback-scale policy and remained accepted. The final policy was then measured in real replay, including the full curve run. The soak's conservative 90-second buffer audit is **post-run modeling**, not live playback evidence. Its standalone 1,059 MiB host peak includes accumulating the whole 14-minute WAV; this is distinct from the resident-worker measurement above.

The final curve run spent 192.80 seconds in sampling and 104.17 seconds in decode. DiT and VAE execute on Chestnut; quality inspection, arrangement, gestures, playback and file handling execute on CPU. Prepared profile embeddings are supplied from the existing Mac preparation workflow. No Mac inference or cloud generation participates in native replay.

## Pre-commit quality and continuity

Only newly committed material is assessed; retained context and discarded lookahead cannot trigger rejection. Version `prism-precommit-v2` previews the existing neutral output DSP at the fixed 0.65 output gain, without route/event inputs. It measures DC-removed 100 ms RMS windows, using conservative relative thresholds and absolute bounds. Non-outro material is rejected for a two-second near-silent interval, with one window of alignment allowance, or a four-second severe collapse. Sparse and uniformly soft material supplies its own reference scale.

Intentional outro fades use a separate policy. Terminal fade and sparse final phrases are allowed; non-finite/broken output, entirely silent output and absurdly long leading silence are rejected. The arrival test rejected 7.8 seconds of leading outro silence and accepted its reroll before playback.

The original attempt plus at most two deterministic rerolls preserves the same source and role. Each attempt requires the measured estimate, at least 30 seconds, plus 10 seconds of reserve before its playback deadline. Rejected WAVs, latents, seeds, spans, reasons, wall times and remaining buffer are retained in the route-owned quality archive.

Known-case results:

- Community chorus: all three attempts failed, with 5.8/5.2/7.1-second raw-policy gaps, taking 70.26 seconds. No successful reroll is claimed.
- Curve verse: original 2.7-second gap rejected; first reroll accepted with a 0.1-second gap; 46.37 seconds total.
- New playback-scale counterexample: original rejected; reroll accepted in 48.04 seconds total with 42.4 seconds of the test reserve remaining. Official Mac reference reproduces both decisions and the measured 1.9/1.6-second preview spans.

The 11 fixtures include recorded good/bad outputs and explicitly labeled soft/rest transforms. The 20 focused tests pass. Existing regression coverage also passed, including the causal future-mutation test in the proper openpilot host runtime.

The section grammar remains verse → prechorus → chorus → verse → bridge → chorus, with current delivered navigation controlling the outro. Prism's bridge keeps the same tonal center and contrasts arrangement/timbre. Three additional reference bridge variants are available for listening; the previously selected conservative conditioning remains active. No new harmony experiment was promoted without human review.

Curve Apex V4 adds an unpitched crash, low transient and stereo flutter. V3 turn waveforms remain unchanged. Controlled V4 rendering had no late events, peak 0.718 and essentially unchanged overall RMS relative to V3. **Musical salience and subjective continuity still require listening.**

## Failures preserved, fixes and limits

The first curve archive passed runtime counters but contained a two-second final-output quiet passage. Raw decoder thresholds missed it. The final gate measures through neutral playback processing and accounts for window alignment. The original archive remains labeled `curve_v1`; the corrected full curve archive contains no two-second quiet spans. No route-specific timestamp or musical parameter was added.

The first injected worker stop held music but caused four output underflows: each immediately followed construction of a hold while holding the callback lock. Buffer construction now occurs outside that lock, as for normal continuations. The repeated test completed four holds with no output errors after CPU restoration. Holds are labeled reused accepted music, not fresh generation. No seamless ACE→SA3 handoff or in-playback reset is implemented. This controlled stop test does not prove every possible USB failure will be harmless to the host.

The first Mac fresh run had a 1.138-second packet-delay burst exceeding its 250 ms reserve, producing 151 starved callbacks and 71,088 skipped samples despite healthy composition. A quiet-host retest passed with no transport-code or latency change. The initiating network/host-scheduling cause is unresolved; this is why native playback is preferred for the demo.

The smaller GPU reproducer repeats one fixed 375-frame VAE graph with resident input, no DiT, replay or full-file assembly. Back-to-back readback failed after 22 successes; compute-only failed after two successes, before PCM readback. A one-second-idle comparison passed 40 iterations with identical PCM hashes. Both genuine failures showed a healthy link after submission, then an inaccessible GPU and link register `0x0` **before the driver timeout handler**, while the USB bridge remained readable. Corrupted timeline reads are not counted as progress. This narrows the interval but does not identify root cause, and diagnostic sampling can alter timing.

Two separate cold benchmark attempts omitted `TC_OPT=2`; their upload-drain failures are preserved as invalid harness configurations, not production ACE regressions. Correctly configured real generation and replay passed as reported above. The private worker retains fixed initial-30/continuation-45 shapes, pre-job link checks, a resident model and a timeout snapshot that avoids the driver's interrupt/reset storm. There is no silent power cycling. See [GPU findings](results/ace_demo_20260916/GPU_FINDINGS.md).

Aurora cold preparation exposed another operational issue: normal screen-off power saving offlined the large CPU cores after the supervisor configured them. This first backup preparation took 846.5s and required an explicit CPU-only correction. Repository code ties that action to ignition-off/screen-off power saving, separately from thermal state. The private supervisor now maintains only its CPU-online settings while the real device remains offroad, without calling amplifier/power-save APIs or reasserting clock limits over later thermal decisions. It restores its saved settings on exit. The helper was exercised against the actual offlined cores; three guard tests cover no writes onroad and stopping writes on an onroad transition. The SA3 run exercised a real screen-off transition: the supervisor automatically restored all four CPU-online bits, completed replay without output errors and restored its saved settings on exit. The correction did not call amplifier APIs or reassert clock limits.

No live driving or simultaneous modeld coexistence was tested. Arbitrary new identity preparation on the comma is not demonstrated. Repeated bad samples can still force explicitly reported musical holds; the measurements do not establish indefinite fresh composition under arbitrary failures.

## Review and operation

- [Focused nine-section listening page](results/ace_demo_20260916/index.html)
- [Launch and recovery checklist](results/ace_demo_20260916/DEMO_CHECKLIST.md)
- [Route evidence](results/ace_demo_20260916/replay_results.json)
- [Final-policy performance](results/ace_demo_20260916/v2_performance.json)
- [Exact source/seed reference comparison](results/ace_demo_20260916/gain_reference_audit.json)
- [Corrected containment audit](results/ace_demo_20260916/containment_audit.json)

[Final validation](results/ace_demo_20260916/validation.json) and [cleanup evidence](results/ace_demo_20260916/cleanup.json) are saved. All owned workers/replays are stopped, GPU/session/display/service locks are free, the normal offroad UI and manager are restored, and saved CPU settings match their restoration snapshot. Both session mute locks remain active and Mac system mute is on. No speaker or Bluetooth output was intentionally enabled; the bench remained muted. Physical speaker confirmation is deferred to the user.
