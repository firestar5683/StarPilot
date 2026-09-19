# Chestnut musical controllability experiment

This is an isolated feasibility experiment, not Orchestra/RoadScore implementation. No replay, Galaxy, driving integration, or playback service is added.

## Recommendation

Use **one Chestnut-generated musical identity, a persistent phase-aligned loop derived from it, and deterministic intensity/brightness/swell controls** as the minimum viable Orchestra. Preserve generated EnCodec tokens and request audio-prefix-conditioned continuations asynchronously as optional future material. Audition/select new passages before replacing the bed. Do not make event timing or persistence depend on a new model response.

MusicGen Small supports a real continuation path with a small extension to the existing native tinygrad harness. This is stronger than independent text prompts: every branch has the same exact eight-second audio-token prefix. However, neither the model API nor this small experiment establishes guaranteed motif/key/tempo retention in newly generated material, a reliable intensity knob, independently editable instruments, or a cadence on demand. Prefix identity is not evidence that the generated suffix is musically coherent. Human listening is decisive.

The hybrid approach preserves source identity by construction; it controls energy and texture without asking the model to rewrite the song at each event. This is a narrower musical claim than generating orchestrated stems or harmonic tension/resolution. If those are mandatory, this gate is still unproven.

## Result and validation

**Conditional recommendation: hybrid Orchestra.** Real continuation and changed prompt conditioning work on Chestnut. Dependable model-only intensity, instrumentation, key/BPM, and harmonic resolution are not established. The continuous source-preserving DSP demo is the strongest demonstrated route to persistence and controllable energy. Human listening acceptance remains open; no audio-quality judgment is claimed by the coding agent.

The experiment began at 02:53 UTC on 14 September 2026 and finished within the 35-minute bound. No second model or general runtime extension was attempted. CPU settings were restored exactly after both generation and verification; before/after JSON snapshots match.

All four branches retained their 400-frame (eight-second) source-token prefix exactly. Their full delay masks match the installed official Transformers implementation. A separate short-prefix cached-execution test compared the last four positions of a 16-position sequence against CPU Transformers under low and high conditioning, including JIT reuse after replacing the prompt. Cosine similarity was 0.99999356 / 0.99999386, with mean absolute logit error about 0.0106. This is an approximate FP16 correctness check, not exhaustive validation of every generated token. All prompt lengths were 49–59 tokens, within the 64-token padded input.

The three newly generated branch suffixes differ on 94–96% of their codec-token positions. They are actual new generations, not copies of the prefix or each other. Token difference does not measure musical difference. WAV headers, finite/non-silent output, clipping, and hashes were independently checked; see `results/wav_manifest.json`.

## What was tested

Hardware/runtime are unchanged from the [first gate](../README.md): comma four CPU plus Chestnut through tinygrad USBIface, MusicGen Small FP16 weights. All 24 autoregressive music transformer layers execute on Chestnut. CPU handles T5 text conditioning, sampling/masking, and EnCodec waveform decoding. The offline DSP experiment also runs on the comma CPU. No external audio or remote inference is used.

1. Generate a new 12-second base passage on Chestnut.
2. Retain its final eight seconds of EnCodec tokens.
3. Teacher-force those exact tokens through the decoder, then generate eight new seconds under neutral, low-intensity, or high-intensity text conditioning.
4. Take the high branch's eight newly generated seconds as another prefix and generate an eight-second release.
5. Derive periodic low/neutral/high DSP variants from one passage of the generated base, with identical timing and notes. Render repeated loops and a continuous rise/release listening example.

Neutral/low/high share the same prefix and sampling seed (321). The common prompt requests a repeating synth motif, soft strings, A minor, 100 BPM, and instrumental cinematic downtempo. Only the arrangement/mood suffix changes. This is one paired branching experiment, not a statistically meaningful prompt-adherence study.

The extension adds no model layers and leaves `native_decoder.py` unchanged. It supplies forced prefix tokens using the official delayed-codebook convention and updates preallocated cross-attention/mask buffer contents between prompts. Keeping the same buffers matters because TinyJit captures those buffers. The self-attention cache is overwritten from position zero for each branch. Prefix processing is sequential and costs roughly as much as generating the same duration; batched prefill or prefix-cache snapshots were deliberately not implemented.

## Measured performance and prompt response

| Run | Retained + new audio | GPU loop including prefix/sampling | CPU decode | Entire run including conditioning-buffer update |
|---|---:|---:|---:|---:|
| base | 0 + 12 s | 124.32 s | 27.59 s | 157.31 s |
| neutral | 8 + 8 s | 100.32 s | 35.07 s | 138.43 s |
| low | 8 + 8 s | 100.36 s | 34.77 s | 138.16 s |
| high | 8 + 8 s | 100.39 s | 34.55 s | 137.98 s |
| release | 8 + 8 s | 100.24 s | 34.50 s | 137.76 s |

The base includes cold JIT execution. Later runs reuse the JIT and change cross-attention conditioning buffers. CPU text encodings were computed beforehand in 1.12–1.17 seconds per prompt; add that for an unseen prompt. The entire-run column includes roughly 3 seconds to update GPU conditioning buffers but excludes model loading and those precomputed text encodings. GPU-loop time includes CPU sampling and USB transfers; it is not pure shader time.

Warm continuations therefore add eight seconds of music in approximately **139 seconds including a fresh prompt** (~17.4 times the new audio duration). About 49.7 seconds are spent ingesting the retained prefix through the first new-token logits. Steady steps remain 0.125 seconds, close to the first gate: the added latency comes from processing context and decoding twice as much audio, not a large steady-step slowdown.

Peak sampled process RSS was **2,125,008,896 bytes (2.13 GB)**, including CPU reference checks/loading; peak tracked tinygrad buffers were **1,014,611,536 bytes (1.01 GB)**, not full physical VRAM. The five generation runs completed in about 13 minutes after imports, including model preparation and CPU reference checks. No output contained nonfinite values or clipped samples.

On newly generated suffixes, RMS was neutral **0.1886**, low **0.2032**, high **0.1701**, release **0.1714**. Spectral centroid was neutral **1365 Hz**, low **1193 Hz**, high **1316 Hz**, release **1164 Hz**. Thus the low prompt produced a darker spectrum, but the high prompt did not exceed neutral on either of these coarse intensity proxies. They do not measure musical quality or perceived intensity; this is evidence against treating prompt labels as calibrated controls.

New-suffix pitch-class profile cosine similarity to the base was **0.991 neutral / 0.997 low / 0.967 high**; release-to-high was **0.995**. These descriptive numbers support tonal relatedness, but cannot establish a shared melody, exact key, functional harmony, or perceptually seamless switching. The first 7.8 decoded seconds of neutral/low/high were sample-identical. Differences near the prefix's decoded end illustrate why retaining exact tokens does not make every codec boundary sample identical.

## Listening guide

Files are in [results](results/). Names `*_full.wav` include the retained prefix; names `*_new.wav` contain only newly generated material. No prefix duration is counted as new generation.

- [Base identity, 12 seconds](results/base_full.wav).
- [Neutral continuation](results/neutral_full.wav), [lower-intensity prompt](results/low_full.wav), [higher-intensity prompt](results/high_full.wav): each is 16 seconds, with identical token conditioning for the first eight seconds and new music beginning at 8.0 seconds. Judge the transition and the new suffix, not only the shared opening.
- [Release continuation](results/release_full.wav): high branch material for eight seconds, then the release attempt.
- [Model continuation chain](results/model_tension_release_chain.wav): base → high → release, 28 seconds. New high material begins at 12 seconds; release begins at 20 seconds. A 120 ms blend in the shared decoded context handles codec boundary differences without shifting the musical timeline.
- [Hybrid persistent score](results/hybrid_tension_release.wav): one generated source loop, continuous low → high → low DSP adaptation. This directly tests the recommended minimum architecture.
- [Low loop](results/loop_low.wav), [neutral loop](results/loop_neutral.wav), [high loop](results/loop_high.wav): four cycles each, all using the same source phase. Compare repeat boundaries and energy.
- [Matched model comparison](results/model_variants_comparison.wav): neutral, low, then high new material, eight seconds each with half-second gaps.
- `neutral_matched.wav`, `low_matched.wav`, `high_matched.wav`, and `release_matched.wav` normalize the new suffixes to the same RMS target, subject to recorded peak limiting. RMS matching is not perceptual LUFS normalization.

Listening questions: Does the model continuation retain the same song? Do low/high differ in the intended direction beyond loudness? Does the release feel like a resolution or just another passage? Does the hybrid loop repeat unobtrusively? Is its energy change expressive enough for the project? The automated measurements cannot answer these questions.

## DSP loop experiment

The primary loop uses a **4.864-second** source period, starting at 1.568 seconds in the generated base, with a 120 ms seam blend. This corresponds to eight hypothesized beats at 98.68 BPM. Autocorrelation's strongest candidate was 66.96 BPM; the near-100 candidate was also strong and was selected using the requested-tempo prior. The [alternative loop](results/loop_alternative_tempo.wav) retains the strongest autocorrelation interpretation (7.168-second period). Neither choice establishes the downbeat or harmonic phrase boundary.

The main [hybrid demo](results/hybrid_tension_release.wav) lasts **38.912 seconds**: low for 0–9.728 s, rising energy to 19.456 s, high through 24.320 s, release through 34.048 s, then low. A short reverse swell made from the generated source precedes the peak. No new instrument or outside audio is added. Level and spectral changes act on the same notes and phase; they are not separately generated stems.

The low/neutral/high loops have RMS **0.0993 / 0.1497 / 0.1824** with a common headroom gain. The periodic seam's sample jump is 0.0124, below the largest interior sample step (0.2508); this rules out a large simple splice jump, not an audible rhythmic/harmonic mismatch. The entire offline analysis-and-WAV rendering script took 5.56 seconds on the restored comma CPU configuration, excluding imports. That is not a real-time playback/deadline benchmark.

## Capability boundaries

| Requirement | Model-only evidence | Minimum hybrid capability |
|---|---|---|
| Persistent identity | Exact source-token prefix; new suffix identity requires listening | Repeat and transform the same generated phrase; notes/timing retained |
| Low/high intensity | Paired text-conditioned branches; intended direction is not guaranteed | Continuous gain and spectral balance, with common phase |
| Looping/crossfades | Generation is not constrained to close a musical loop | Select a candidate periodic passage, soften seam, repeat; phrase/downbeat quality still needs listening |
| Tension/release | High → release continuation attempt | Timed rise/fall in energy and source-derived reverse swell; not a guaranteed harmonic cadence |
| Switching without changing songs | Possible through continuation, unproven across arbitrary assets | Crossfade aligned DSP variants of the same loop; avoid arbitrary branch layering |
| Tempo/key | Text requests only; no hard BPM/key input in this Small checkpoint | Retain actual source timing/pitches; validate/annotate them before adding harmony or bar-level events |
| Instrumentation | Text can request arrangement; mixed mono output, no instrument isolation | Filter/mix texture controls, not independent string/drum stems |

The loop extractor's onset autocorrelation and chroma statistics are rough short-clip descriptors. They are not validated beat/downbeat/key estimates. A seam blend prevents a simple splice discontinuity but cannot fix a broken chord progression. No time stretching or pitch shifting is used; there is no claim the source obeys the requested 100 BPM or A minor.

## Smallest Orchestra design implied by the evidence

- A session stores one chosen generated phrase, its original audio codes, loop boundaries, and a common sample/phrase clock. Add human-verified tempo/key only if needed; otherwise avoid inventing harmony over the mix.
- The timing-critical side reads the existing source and smoothly automates intensity, spectral balance, and source-derived swells. Keep all variants phase-aligned. Hold the current bed when generation is late or fails.
- A separate non-critical generation task requests continuations from recent source tokens. Preserve the initial identity anchor too, so long continuation chains do not become the only available context. Long-term drift prevention using that anchor is a proposal, not a tested conditioning feature.
- Treat each generated continuation as a candidate sequential passage, not a synchronized stem. Listen/select before adding it to the usable pool for the demo. Replace a bed only at an acceptable phrase boundary; a generic crossfade does not establish harmonic compatibility.
- Chestnut continues to contribute actual musical composition. DSP makes that locally generated composition persistent and responsive. No prerecorded library is substituted.

Do not add a large melody model, source-separation model, symbolic composer, key-control training, or generalized PyTorch compatibility work to the MVP. The earlier exclusive Chestnut ownership limitation remains: this experiment does not prove coexistence with driving inference.

## Sources checked before implementation

[Transformers MusicGen documentation, v4.46.3](https://huggingface.co/docs/transformers/v4.46.3/en/model_doc/musicgen) documents audio-prompted continuation and the shared prompt/output duration limit. [The matching source](https://github.com/huggingface/transformers/blob/v4.46.3/src/transformers/models/musicgen/modeling_musicgen.py) supplies the exact BOS and delayed-codebook semantics used here.

[AudioCraft's model catalog](https://github.com/facebookresearch/audiocraft/blob/main/docs/MUSICGEN.md) distinguishes the 300M Small checkpoint from the 1.5B Melody checkpoint with chroma conditioning. Melody guidance is not a switch we can enable in these Small weights. A larger-model migration was outside this bounded experiment.

## Reproduction on the provisioned device

The scripts assume the first gate's isolated environment and weights under `/data/roadscore-feasibility`. Copy `probe.py` there as `controllability_probe.py`, alongside `native_decoder.py`, `run_probe.sh`, and `power_probe.py`. Run offroad with Chestnut available:

```sh
ssh comma@192.168.3.111 '/usr/local/venv/bin/python /data/roadscore-feasibility/power_probe.py'
```

The wrapper temporarily enables the big CPU cores at the normal openpilot cap, then restores the prior settings. Its generation timeout is 1400 seconds. Output names are fixed; another run overwrites the device's controllability outputs. `arrange.py` derives only offline listening artifacts from those outputs. `verify.py` checks prefix/mask construction and cached GPU logits against the CPU implementation; it is a separate exclusive GPU run. Copy those files plus `power_verify.py` and `run_verify.sh` into the same device directory, then run:

```sh
ssh comma@192.168.3.111 '/usr/local/venv/bin/python /data/roadscore-feasibility/power_verify.py'
ssh comma@192.168.3.111 '/data/roadscore-feasibility/venv/bin/python /data/roadscore-feasibility/arrange.py'
```

`result.json`, `arrangement.json`, `validation.json`, logs, and CPU setting snapshots accompany the WAVs. Full physical VRAM utilization is not available; tracked tinygrad buffers must not be described as complete device memory consumption. This experiment does not include real-time playback scheduling, long-duration thermal tests, or human-rated musical acceptance.
