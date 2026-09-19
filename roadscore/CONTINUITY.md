# Horizon continuity experiment

Human review rejected the previous Nocturne preference and earlier-tail trimming. That rejection is the baseline for this pass; the old zero-underrun/near-silence measurements did not establish a good song.

## What changed

The fixed 324-frame, eight-step SA3 worker now optionally inpaints **between two active pieces of musical context**. Four seconds of the preceding passage remain at the front. A four-second identity anchor, selected from the already-generated opening's active middle, remains at the back. The same anchor returns about every 26 seconds. It is explicitly reused music, and its ranges are shaded purple in the listening plots.

The model generates the roughly 21.92-second interior between those anchors. The runtime appends about 26.01 seconds per job, including the reused 4.09-second anchor. The retained prefix is removed except for a two-second common-context crossfade. No silence removal, time stretching, gain repair, stem separation, or hidden offline arrangement is applied. Even latent-frame boundaries preserve the decoder's two-frame grouping. MusicGen, native SA3 model weights and the public repository remain untouched.

The initial Horizon opening stops at 21.92 seconds, before its rejected terminal fade. This trimming alone is **not** the solution: a matched-seed prefix-only control still fades near the end, whereas adding the trailing inpaint anchor keeps that ending active. The probe holds prompt, duration, noise seed, input prefix and sampler constant for that comparison.

Ongoing conceptual duration remains 120 seconds. The runtime uses a small phrase-level prompt-embedding blend between the existing base and development prompts: establish, explore, develop, build, release. These are generation intentions, not verified musical states or guaranteed linear intensity control. Navigation can choose a related closing prompt. There is no new style catalog. Horizon is the current bench default.

## Evidence and performance

`results/continuity/listen.html` contains the new review and energy plots, with the rejected raw Horizon/chamber regression cases inside the diagnostics section. The controlled anchored journey is 125.945 seconds. True new-material boundaries are 21.920, 47.926, 73.932 and 99.939 seconds; the end anchors are separately shaded. Human judgment is still required at every join.

Four warm probe jobs took 19.268–19.428 seconds. Playback RTF is 0.741–0.747; RTF against newly generated interior alone is 0.879–0.886. Each job adds 6.58–6.74 seconds of buffer headroom when the reused anchor is included. About 84% of each appended passage is newly denoised material. Startup buffering does not count as sustainable throughput.

The old ~0.97 useful RTF came from discarding the last ~2 seconds while retaining ~8 seconds of context: only 19.97 usable seconds remained per job. The older untrimmed ~0.878 figure used ~22 seconds. The new strategy improves useful musical yield, not GPU speed. Its novel-material RTF remains similar to the old untrimmed case.

The first cold job of the final worker took 96.750 seconds including graph capture; the second warm-up took 22.505 seconds. These job timers exclude initial model/weight loading. Sixteen accepted live jobs took 19.231–19.441 seconds (median 19.341), with decoder execution around 0.7 seconds. The 210.1-second long capture accepted seven live continuations, held at least 10.24 seconds buffered, and had zero fallback loops/output flags and no -50 dBFS/100 ms gaps in dry or wet music. All four runs together captured 517.6 seconds; this is finite validation, not an indefinite soak test. CPU handles cached conditioning, noise, replay, resampling, arranging and the Conductor. Chestnut runs DiT and decoder. Resource measurements are worker peak RSS and tracked GPU allocation sampled after decode, **not total system RAM or a verified peak-VRAM trace**. Exact live metrics are in `results/continuity/live_metrics.json`.

Measured positive headroom and the live captures support sustainable average operation at this bench load; they do not guarantee indefinite operation, all seeds, all prompts, thermal conditions or coexistence with modeld. No simultaneous driving inference was attempted.

## Curve and arrival

The Conductor and curve detector are unchanged. The 100.1-second Horizon curve capture retains 6.208 seconds of callback-measured anticipation. Reported DAC buffering adds ~0.100 seconds, yielding ~6.108 seconds by that estimate; the speaker was muted, so neither is acoustic evidence. Video packaging accounts for this delay using actual callback timestamps.

Actual route203 cereal shows reverse near 232.2 seconds, navigation invalidation near 241 seconds, braking reverse near 243.9 seconds and park near 255.1 seconds. The runtime now requires recent arrive context within 40 m, reverse below 2 m/s with braking sustained 0.8 seconds, and explicit navigation invalidation; park/standstill or a sustained stop remain fallbacks. It does not treat reverse alone, lost navigation alone, or EOF as arrival. A new valid route clears the context.

The verified trigger is 244.654812 seconds. Rendering starts around 244.935743; the reported DAC estimate is 245.035743. The difference includes local harmony analysis and callback scheduling. Two related closing jobs were accepted before resolution, and the source contains no -50 dBFS/100 ms gaps before the ending. A five-second source-informed sonority then decays. It may still be stylistically imperfect; listen to the generated closing and exact landing together.

## Limits and regression scope

There is no claim yet that the boundaries are hard to hear, the anchor sounds like a natural refrain, the arc develops convincingly, or the synthesized final chord is the right cadence. No amount of numerical evidence substitutes for that listening decision.

Musical logic contains no route IDs, excerpt timestamps, future route reads or precomputed event locations. The same generated-source policy was run on a second cached route. Route IDs and excerpt times occur only in test/publisher selection and offline evidence. The privacy guard remains active. Thirteen detector/musical unit tests pass, including reverse-without-destination and route-reset cases. The public tree and custom display were not edited.

A validation-shell edit while that shell was running caused an extra trailing command error after all three initial captures were saved; the captures and audits completed. The final script passes shell syntax validation, and the longer run was launched separately. This was an orchestration error, not an audio/runtime failure.

Normal existing-onroad replay integration and safe live modeld coexistence remain future work. No new custom visualization was built.
