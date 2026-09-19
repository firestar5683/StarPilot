# Stable Audio on Chestnut: bounded feasibility investigation

## Decision

**The faster-than-playback gate is unresolved because model-weight access is blocked, not because an architectural incompatibility was found.** No Stable Audio WAV was generated, and no end-to-end model timing is claimed.

Stable Audio 3 Small-Music is a credible candidate for a narrow native tinygrad implementation. Representative diffusion and audio-decoder blocks ran on the actual Chestnut USB AMD backend with encouraging warm latency. This supports pursuing one full generation after weight access is available; it does not justify replacing the working MusicGen implementation yet. Keep the MusicGen hybrid as the demonstrated fallback. Do not begin RoadScore production implementation from this result.

Only the two requested model families were investigated. MusicGen was not optimized or modified. All additions are in this experimental directory; the device scratch directory is `/data/sa3-feasibility`. CPU settings were restored after the hardware test.

## Blocking evidence

Authenticated requests using the already-configured Hugging Face credential received **HTTP 403, account not in the authorized list**, for both:

- [Stable Audio 3 Small-Music](https://huggingface.co/stabilityai/stable-audio-3-small-music)
- [Stable Audio Open Small](https://huggingface.co/stabilityai/stable-audio-open-small)

The credential itself was not printed, copied to the device, or saved in results. See [access.json](results/access.json). The access requests were raised during the investigation and the checks were repeated before reporting. The owner needs to accept the repository access conditions with the account used by that credential; fine-grained token permissions may also need adjustment. No alternate restricted download route was attempted.

SA3 redistributes its T5Gemma assets in the same repository, so access to that repository is also needed for its released text-conditioning path. The public repository file listing was available; the actual checkpoint/configuration files were not.

## Actual architecture inspected

Primary implementation: [Stability-AI/stable-audio-3](https://github.com/Stability-AI/stable-audio-3), pinned source commit `779434a908193105335fd8d833418603625b2859`.

The most useful reference for a narrow port is the project's own self-contained [MLX DiT implementation](https://github.com/Stability-AI/stable-audio-3/blob/779434a908193105335fd8d833418603625b2859/optimized/mlx/models/defs/dit_mlx.py), plus its SAME-S and sampling implementations. MLX itself will not run on Chestnut; the reusable part is the explicitly expressed model math and weight mapping.

| Component | Released implementation | Narrow tinygrad route |
|---|---|---|
| Diffusion model | 20 layers, width 1024, 16 heads, 64-dimensional heads, standard self/cross attention, 4096-wide SwiGLU inner dimension | Native matmuls, RMS normalization, RoPE, FP32 softmax, SiLU, residuals and conditional scale/shift/gates |
| Conditioning | 768-dimensional T5Gemma embeddings, learned prompt padding, duration and timestep Fourier embeddings, 64 memory tokens | CPU tokenizer/text encoder initially; port encoder only if CPU latency prevents the gate |
| Sampling | Eight ping-pong rectified-flow steps; normal inference example uses guidance 1 | A small explicit update loop; keep latents on Chestnut between steps |
| Inpainting | Per-position mask plus 256-channel source latents, projected into each DiT layer | Existing linear and masking operations; no new attention primitive |
| SAME-S decoder | Six 768-wide transformer blocks, differential attention, DyT normalization, SwiGLU, shifted local chunks | Two attention products and subtraction; tanh affine normalization; reshape/slice/cat; pre-fused weight-normalized convolution |
| Waveform reconstruction | 256-dimensional latents → 16 stereo audio patches per latent → 4096 waveform samples per latent | Native decoder, then reshape and CPU WAV write; no separate autoregressive vocoder |

At 44.1 kHz, one latent represents 4096 samples (~10.77 latent frames/second). Eight denoising passes process the whole latent sequence, rather than hundreds or thousands of sequential token predictions. This is the architectural reason to expect a substantially different speed regime from MusicGen. It is not proof of a particular wall time.

References: [SAME-S decoder](https://github.com/Stability-AI/stable-audio-3/blob/779434a908193105335fd8d833418603625b2859/optimized/mlx/models/defs/same_s_decoder.py), [sampling and waveform reconstruction](https://github.com/Stability-AI/stable-audio-3/blob/779434a908193105335fd8d833418603625b2859/optimized/mlx/models/defs/sa3_pipeline.py), [T5Gemma encoder](https://github.com/Stability-AI/stable-audio-3/blob/779434a908193105335fd8d833418603625b2859/optimized/mlx/models/defs/t5gemma_mlx.py).

## tinygrad / USB compatibility assessment

No obvious fundamental operator blocker was found for Small-Music. The repository already provides matmul, softmax, sin/cos, tanh, SiLU, reductions, slicing/reshaping/concatenation, convolutions and TinyJit. RMSNorm and DyT can be expressed directly. Differential attention is two ordinary attention results subtracted; it does not require a custom CUDA kernel. Weight normalization can be folded into convolution weights during conversion.

The synthetic test actually exercised the attention, normalization, RoPE, feed-forward, conditional gating and local-conditioning projections on `USBIface`, `gfx1200`. It did **not** exercise the entire decoder's chunk-shift/reconstruction pipeline, the final convolution, real checkpoint loading, the sampler, or text encoding. There is no numerical parity claim against the actual SA3 checkpoint.

The existing transport is tinygrad's custom USB AMD route. CUDA/TensorRT, Apple's CoreML/MLX, and the CPU LiteRT/XNNPACK release are not drop-in Chestnut backends. Small-Music uses standard attention; the Medium model's different backend requirements are not a reason to reject Small. A general PyTorch backend compatibility layer is unnecessary for the proposed route.

## Measured synthetic hardware test — not music generation

[Probe](layer_probe.py), [raw timings](results/layer_probe.json), [log](results/layer_probe.log).

| Representative block | Shape | First call, compilation included | Capture call | Warm median, three replays |
|---|---|---:|---:|---:|
| SA3 DiT | `[1, 384, 1024]` (320 latents + 64 memory positions) | 22.558 s | 1.231 s | **10.774 ms** |
| SAME-S decoder | `[160, 34, 768]` (first-half chunk layout for 320 latents) | 21.699 s | 0.940 s | **23.331 ms** |

The represented latent length would correspond to 29.72 seconds of audio **if it were generated and decoded**. No audio was generated by this probe. The weights and inputs are deterministic random arrays, not downloaded trained parameters. Device synchronization is included in timings. Synthetic block initialization took 3.52 and 1.75 seconds respectively.

Simple arithmetic, `20 × 8 × 10.774 ms + 6 × 23.331 ms`, gives about **1.86 seconds for those repeated block workloads**. This is only a screening extrapolation. It omits text encoding, input/output projections, sampler work, codec mapping and layout changes, loading, full-model memory/cache effects, and distinct learned weights. It is neither a measured generation time nor a reliable lower/upper bound. It is encouraging enough that rejecting SA3 as inherently too slow would be unjustified.

Peak sampled host RSS for the probe was **185,114,624 bytes**; peak tracked tinygrad buffers were **178,425,616 bytes**. Those are **single-block test allocations, not model memory requirements**. They must not be compared with the full MusicGen model's RAM/VRAM as though they represented equivalent workloads. Complete physical VRAM usage was not measured.

## Requested success-gate record

| Metric | SA3 Small-Music | Stable Audio Open Small |
|---|---|---|
| Actual generated duration | None | None |
| End-to-end generation time | Not measured: weights inaccessible | Not measured: weights inaccessible |
| Waveform decode time | Not measured | Not measured |
| Cold/warm full-model performance | Not measured | Not measured |
| Full-model host RAM | Not measured | Not measured |
| Full-model tracked Chestnut allocation | Not measured | Not measured |
| Faster-than-playback success | **Not demonstrated** | **Not demonstrated** |
| CPU versus Chestnut | Only synthetic block math ran on Chestnut; host prepared inputs and dispatched | Source inspection only |

For an actual SA3 attempt, the preferred initial split is CPU text/tokenization plus Chestnut DiT **and SAME-S decode**, followed by CPU WAV writing. Leaving a slow general PyTorch audio decoder on the comma CPU could erase the diffusion speed advantage. Text encoding must be included in a fresh-prompt benchmark; cached-conditioning results should be reported separately.

## Continuation and audio conditioning

SA3 explicitly supports both. Its [SAME-S encoder](https://github.com/Stability-AI/stable-audio-3/blob/779434a908193105335fd8d833418603625b2859/optimized/mlx/models/defs/same_s_encoder.py) reuses the decoder's six-block transformer machinery, with the direction and projections changed. Audio-to-audio initializes from encoded audio with chosen noise. Inpainting/continuation supplies masked source latents to the DiT; the published sampler can restore retained latents after sampling.

That is a small extension **after** a correct text-to-audio/decoder port, rather than a new generative architecture. Reusing previously generated SA3 latents may avoid waveform re-encoding. MusicGen codec tokens cannot be used as SA3 latents; a MusicGen WAV would need SAME-S encoding. Musical continuity, boundary quality and conditioning speed remain untested here.

## Secondary candidate assessment

[Stable Audio Open Small](https://huggingface.co/stabilityai/stable-audio-open-small) is also a credible few-step design, but a less compelling first choice for this music project. Its model card explicitly rates its sound-effect/field-recording performance above music. It supports short stereo generation and eight-step ping-pong sampling.

Its [paper](https://arxiv.org/html/2505.08175v1) describes a 16-layer, 1024-wide diffusion transformer, a 64-channel 21.5 Hz latent space, a separate audio autoencoder and T5 text encoder. The paper also demonstrates audio-to-audio initialization. It does not establish SA3-style trained inpainting as an interchangeable feature of this checkpoint.

The CPU headline is not a comma benchmark: the paper's edge result uses a Vivo X200 Pro with Cortex-X925/X4/A720 cores and 12 GB RAM, plus selective dynamic INT8. Reported runtime falls from 15.3 to 6.6 seconds and peak RAM from 6.5 to 3.6 GB. That newer phone and memory budget cannot be equated with this comma's ~3.5 GiB RAM and older CPU cores. A Chestnut native port could still be fast; the CPU result alone does not establish that.

The [official Arm example](https://github.com/ARM-software/ML-examples/tree/main/kleidiai-examples/audiogen) exports conditioning, DiT and autoencoder separately and runs them through LiteRT/XNNPACK. Source commit inspected: `0e453847ea28043194c32791a591d0f5a8a5ae2e`. Stable Audio Tools source commit inspected: `3241adba4fc2a85cf5b29d9eb68d42f40a28e820`. The export requires the gated model configuration and weights; no ready-to-run local path was available without those assets. No secondary hardware benchmark was attempted.

## Port size and decisive next test

**Complexity estimate: moderate, model-specific work; not a general runtime project.** SA3 needs a weight loader/converter, full DiT, SAME-S decoder, exact sampling/conditioning glue, and stage-level reference comparisons. The reference code makes a few hundred lines of core tensor math plausible, but validation and dependency integration are meaningful additional work. A one-session port is plausible, not guaranteed. The synthetic block probe is not that port.

Once access is enabled, the narrow experiment should be limited to one fixed ~30-second shape, batch one, eight steps, guidance one, and two seeds. Stream/shard weights to avoid loading a multi-gigabyte FP32 checkpoint and a full duplicate in host RAM. Keep the working MusicGen Python environment intact; T5Gemma requires a different/newer text runtime or a narrow native encoder.

Validate one DiT forward and a decoder slice against the released reference before judging generated audio. Measure cold startup to WAV, fresh-prompt warm generation, cached-prompt generation, GPU decode, host RSS and tracked allocations separately. Require text → trained Chestnut inference → listenable WAV, with warm end-to-end time below audio duration. If weights or correctness cannot be established in the bounded attempt, retain MusicGen rather than inferring success from layer arithmetic.

Full-model GPU sharing with openpilot is still unproven; nothing here changes the earlier exclusive-device-ownership finding.

## Reproduce the completed block probe

The probe reuses only the first gate's isolated Python environment and tinygrad source. Copy this directory's `layer_probe.py`, `run_probe.sh`, and `power_probe.py` into `/data/sa3-feasibility`, then, while offroad and with Chestnut available:

```sh
ssh comma@192.168.3.111 '/usr/local/venv/bin/python /data/sa3-feasibility/power_probe.py'
```

The wrapper temporarily enables the normal capped big-core configuration, enforces a six-minute subprocess timeout, and restores the prior CPU settings. Before/after snapshots match. No driving parameters, manager processes, production code, or MusicGen implementation were changed.
