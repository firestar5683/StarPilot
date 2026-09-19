# Latest human baseline and dense test

Human review provisionally passes e3477e2's sparse Horizon continuity and harmonic development, and likes the final cadence. It requests a denser rhythmic stress test and a less abrupt cadence entry. This supersedes the older rejection notes below where they refer to the improved anchor architecture. Current pass: [DENSE.md](DENSE.md), [STATUS.md](STATUS.md), `results/dense/listen.html`. No new subjective acceptance is claimed.

# Current listening pass supersedes the numerical preference below

Human review rejected Nocturne, earlier-endpoint trimming and level matching as a continuity solution. **Horizon is now primary.** See [CONTINUITY.md](CONTINUITY.md), [STATUS.md](STATUS.md) and `results/continuity/listen.html` for the new two-sided inpainting experiment, disclosed recurring anchors, live captures and performance. No subjective musical success is claimed. The remainder of this document is preserved historical evidence from the rejected pass.

# Musical-quality pass

Preserved baseline: local tag `quality-baseline-149c3cb`, original `results/final_timed`, curve/arrival videos and sustained run. Repeated baseline replay before integration changes: 100.1 s, three accepted continuations, zero fallbacks/output flags, 6.218 s rendered lead. Evidence: `results/quality/baseline_replay`.

Human feedback: causal curve felt anticipated; musical quality not accepted. Generic identity, apparent cutouts/disjoint continuations, excessive volume swell, and premature fade ending require improvement. Numeric continuity is not subjective acceptance.

## Findings and bounded changes

The original final_timed dry capture contains 22.8 s below -50 dBFS (100 ms RMS windows), versus 0.2 s in the new 100 s style-switch run. Original generated WAVs themselves contain long near-silent passages; the Conductor and PortAudio were not their primary cause. Several passages fade before the retained tail ends, so continuation inherits an ending rather than ongoing musical context. A matched-seed fresh test reduced near silence from 2.6 s to 0.0 s by conditioning for a longer piece while keeping the 30 s compute shape. Continuing from the old faded tail still produced 6.8 s. These results establish an integration problem; they do not explain every model-internal pause.

The narrow chamber experiment retains ~8 s of context but ends the usable window at latent frame 301 (~27.96 s), before the troublesome final tail. The next continuation uses exactly that same endpoint. Crossfade duration remains two seconds. Three new passages contained 0.2 / 0.0 / 0.0 s below -50 dBFS in their usable new regions. Context RMS matching corrects independent normalization; silence is never amplified as a reference. Shared-prefix correlations in the exploratory sequences were positive, so broad phase cancellation was not the dominant gap mechanism.

Tradeoff: each trimmed window contributes 19.969 s instead of 22.012 s. Generation is roughly 19.4–20.3 s, depending on simultaneous display/I/O load; useful RTF straddles 1.0. Do not reuse the old 0.878 RTF claim for this quality mode. A matching prewarm restores ~48 s startup buffer. Fallback repeats the current generated tail to preserve context rather than substituting the original seed. It waits until two seconds remain; the first combined run's five-second threshold inserted an unnecessary loop shortly before completion.

Four identities were each tested with initial/base/development/closing material: Nocturne (chamber), Horizon (post-rock), Orbit (analog), Canopy (organic ambient). These are four candidates, not four accepted strong styles. The chamber direction was strongest numerically. Untrimmed 96 s sequences contained 5.6 / 11.7 / 25.7 / 14.0 s below -50 dBFS respectively, including intended closing sections. Orbit and Horizon remain poor continuity candidates in these tests. Nocturne is the default; user listening must determine actual distinctiveness and musical merit.

The causal detector is unchanged. A small alternative Conductor keeps more of the original full-band material and adds delayed phrase echoes, with much less gain/brightness modulation. Long-range navigation still selects development/closing conditioning for later material. This does not prove arrangement, harmony or exact rhythmic control. No new model, training, weight changes or model optimization were performed.

Arrival now separates preparation from ending. Recent valid arrive guidance within 40 m arms the system; speed below 0.15 m/s for two seconds triggers a final gesture. Context can survive navigation invalidation for 30 s, but a new valid route clears it. Sequential evaluation triggers at route 255.257926352 s, versus the old fade at 234.505508006 s. A five-second source-informed final sonority estimates pitch classes from music already played. It is a candidate resolution, not a guaranteed tonic cadence. EOF cannot trigger it; an already-started gesture may finish after replay ends.

The runtime style selector affects future requests. In the verified 100 s run, a manual test request at 146.026 s changed the playing identity at 175.927 s. Zero underruns/fallbacks. Audio source cutoffs and muted-output assertions passed. These manual test times are not runtime road-event triggers.

## Listening

Open `results/quality/listen.html`. It contains matched-seed duration examples, four style candidates, same-source Conductor A/B, continuation-level A/B, and a short arrival A/B. All files remain local/private and require a click to play. Final integrated review files will be listed in STATUS.md.

## Display investigation

The repository's `./onroad` is a host-worktree launcher. The bench has no built replay executable. Full normal-UI replay additionally needs camera VisionIPC and appropriate UI services; that was not made a dependency. The private fallback uses the already installed pyray and OpenCV to show the timestamp-aligned road video and actual RoadScore/model decision state. It does not draw invented lane/path geometry or run the driving model. The original UI manager is paused temporarily while its display process is replaced, then resumed; no production files or onroad parameters are changed. Initial tests exposed a pyray pointer conversion and an incorrect large-screen assumption; both are recorded failures, with corrected final testing required.

## Live integration checks

The first combined display/music run had one early fallback and no underruns. A matching-style prewarm plus corrected buffer policy produced a second 100.1 s run with zero fallbacks/underruns, three accepted continuations, 6.209 s rendered anticipation lead, and a verified future style change. Its dry near-silence total was 0.2 s, wet 1.0 s, compared with original dry 22.8 s / wet 24.9 s. Different prompts/seeds mean this integrated comparison is not a controlled isolated musical preference test; matched-seed and same-source A/B files are provided separately.

The full live arrival run triggered at 255.258 s, held the final gesture beyond log EOF, and captured 90.6 s. It had zero underruns and one background source-loop extension after the ending had begun; that unnecessary source work was then removed. The ring-only phase now advances the audio clock without fetching more source or requesting new generation. A final short arrival regression and a final cold native-display run verify this change and the corrected small-screen layout.

Musical limitations remain: no isolated stems, guaranteed beat grid, verified tonal center, precise cadence, or accepted four-style lineup. The deterministic final sonority can be stylistically unlike its source. Echoes may feel like an effect rather than genuine arrangement development. Long-term quality and source activity remain model-dependent. None of these are hidden by the zero-underrun metric.

## Final acceptance

The final cold native-display run passed: 100.1 s, four live continuations, zero output flags/fallbacks, zero near-silent 100 ms windows in both dry/wet captures, and 6.2108 s anticipation lead. Pinning presentation to cores 0–3 restored median 19.284 s generation / 19.969 s usable material (0.966 RTF). This is a narrow throughput margin, not an indefinite-playback guarantee. The original UI and CPU settings were restored; RoadScore processes were stopped. Final detector/musical tests passed.

The corrected 536×240 native layout is visible in `results/quality/native_display_final.png`. Active software frame age was median 73 ms / p95 115 ms / max 379 ms; no future frames. Post-EOF last-frame hold is recorded separately, not counted as live synchronization error. These are software timestamps, not photon/acoustic measurements.

Best integrated reviews: `results/quality/curve_review.html` and `results/quality/arrival_review.html`. The final arrival regression captured 35.8 s, zero output flags/loops and the complete final gesture. It used prewarmed source; the longer 90.6 s arrival run separately verifies live closing generation. Subjective musical acceptance is still yours.
