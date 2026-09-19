# SA3 Small-Music trained-weight Chestnut experiment

## Result

**Warm 30-second generation passes the numerical speed gate: 18.53 seconds to a playable WAV, RTF 0.618.** The actual trained diffusion model and SAME-S waveform decoder ran on Chestnut through native tinygrad USB AMD (`USBIface`, `gfx1200`). Human listening acceptance is still required; waveform validity and reference agreement do not establish musical quality by themselves.

CPU text encoding took 3.761 seconds. Adding this measured stage gives 22.29 seconds / 30 seconds = **0.743 RTF**. This is a sum of separately measured stages, not a fresh prompt re-encoded during each warm run. The encoder was unloaded before GPU model loading to limit host memory. A production process that reloads the encoder for each changed prompt will incur additional startup cost.

No RoadScore production code or MusicGen code/environment was modified. The secondary model was not pursued because SA3 now demonstrates the requested speed. This is a bounded feasibility prototype, not a production integration.

## Listening files

- [30 seconds, seed 991](trained_results/trained_30s_r0.wav)
- [30 seconds, seed 992](trained_results/trained_30s_r1.wav)
- [30 seconds, seed 993, fully warm benchmark](trained_results/trained_30s_r2.wav)
- [12 seconds, cold shape benchmark](trained_results/trained_12s_r0.wav)

Prompt: “Instrumental cinematic electronic music, warm synthesizer chords, melodic strings, steady drums, no vocals”. Stereo 44.1 kHz PCM16. All outputs were checked for finite, non-silent samples. Peak normalization before PCM export is recorded as `output_gain`; raw peaks sometimes exceed 1.0.

## Measured performance

| Test | Audio | Diffusion | GPU decode | Total to WAV | RTF |
|---|---:|---:|---:|---:|---:|
| First baseline output, compilation included | 30 s | 100.277 s | 23.235 s | 124.064 s | 4.135 |
| Second baseline output, decoder JIT capture | 30 s | 17.678 s | 3.966 s | 21.952 s | 0.732 |
| Third baseline output, fully warm | 30 s | 17.528 s | 0.695 s | 18.529 s | **0.618** |
| First 12-second shape, compilation included | 12 s | 63.814 s | 23.280 s | 87.427 s | 7.286 |
| Independent fixed-30 retry, fully warm | 30 s | 18.084 s | 0.706 s | 19.092 s | **0.636** |

Cold process start to first WAV was **177.157 seconds**, including imports, text model loading/encoding, GPU weight upload and compilation. That is not faster than playback. Diagnostic reference dumps add overhead to first runs. Warm totals include GPU synchronization, waveform transfer, WAV writing and latent saving. Download/conversion are excluded. The independent retry reuses cached text conditioning and adds persistent input buffers; this change did not improve speed materially. All three retry WAVs are byte-identical to their corresponding baseline WAVs (see the WAV manifest).

**12 seconds did not pass.** The next 12-second denoising run took roughly 15 seconds before decoding, and its decoder hung/timed out during JIT capture after changing shapes in the same process. No complete warm 12-second timing is claimed. The experimental process was terminated and Chestnut reset for the fixed-30 retry; three fixed-30 outputs then completed. Cause is not established. Prefer one fixed duration per worker for a prototype, while treating this as an unresolved runtime reliability problem.

## Memory and execution split

- Peak sampled **main-process** host RSS: **2,042,085,376 bytes (2.04 GB)**. Compiler subprocesses are excluded, so this is not total system peak RAM. The cached-text retry used about 196 MB main-process RSS; this excludes the earlier CPU text stage.
- Peak tracked tinygrad buffers across baseline shapes: **1,218,829,230 bytes (1.22 GB)**. This is allocator accounting, not complete physical VRAM measurement. Physical VRAM was not independently measured.
- CPU: tokenizer and FP32 T5Gemma encoder, duration/timestep Fourier features, NumPy random noise, scheduling/compilation, transfers, normalization and WAV writing.
- Chestnut: FP16 trained 20-layer DiT with selected FP32 normalization/softmax/math, all eight denoising passes and sampler tensor updates, trained SAME-S decoder and waveform reconstruction.
- Host big cores 4–7 were temporarily enabled at the normal 1,689,600 kHz cap/performance governor, offroad. Wrappers restore the prior configuration; no manager processes were stopped.

Warm dispatch instrumentation returned from the DiT call in about 0.084 seconds, while synchronized whole steps took about 2.2–2.4 seconds. The remaining time includes asynchronous GPU execution and eager sampler/runtime overhead; it cannot all be attributed to CPU or USB. Fusing sampler arithmetic into the captured graph is a plausible small follow-up, but is unmeasured and unnecessary for the demonstrated 30-second threshold. No major optimization effort was undertaken.

## Correctness and port scope

The [native port](native_sa3.py) implements model-specific tensor math and TinyJit; no general PyTorch compatibility layer or tinygrad backend changes were needed. [Conversion](convert_weights.py) streams tensors to FP16 NPY files and folds decoder weight normalization. The pretrained audio encoder is omitted: basic text generation does not require it.

[Reference validation](trained_results/validation.json) compares first DiT forwards and decoder prefix slices for both durations against the released CPU PyTorch implementations using converted FP16 weights promoted to FP32:

| Comparison | Cosine similarity | Relative RMSE |
|---|---:|---:|
| DiT 30 s | 0.999768 | 0.02154 |
| DiT 12 s | 0.999702 | 0.02444 |
| Decoder 30 s | 0.999725 | 0.02364 |
| Decoder 12 s | 0.999853 | 0.01756 |

These checks support the narrow port's numerical correctness; they are not exhaustive per-step/full-waveform parity or a listening evaluation. Decoder checks use eight input latent frames and the first four decoded frames to avoid truncated-context boundary effects.

Pinned trained model: `stabilityai/stable-audio-3-small-music`, revision `0fef1392cd842149a2b6d445e181c97608faac06`. Released source: `Stability-AI/stable-audio-3`, commit `779434a908193105335fd8d833418603625b2859`. Model assets stay in scratch storage, not this repository. Existing authenticated access was used without logging credentials.

See [the prior architecture/access investigation](ARCHITECTURE_GATE.md) for source links and historical synthetic results. Its weight-access blocker is now resolved; its synthetic arithmetic is superseded by these trained-weight measurements.

## Continuation result

[Warm continuation WAV](trained_results/continuation_30s_r2.wav), [alternate continuation](trained_results/continuation_30s_r1.wav), [source WAV](trained_results/trained_30s_r0.wav), [raw results](trained_results/continuation_result.json).

The model received the first 86 source latent frames (7.9877 seconds) with the trained inpainting mask/local conditioning. It generated the remainder of a 30-second output, then retained latents were restored before decoding. All three saved continuations retain those 86 latent frames exactly. Full raw waveform equality at the boundary is not claimed: decoder context and independently reported peak normalization can affect PCM output.

The fully warm run generated **22.0123 seconds of new material** in **19.3357 seconds total**, including 18.3408 seconds of diffusion and 0.6893 seconds of GPU decoding. **RTF per new audio = 0.8784**; RTF against the entire 30-second file = 0.6445. Cached text was used. The decoder-capture run took 22.3218 seconds (1.0141 RTF per new audio), so prewarming matters. This establishes execution and speed, not perceptual continuity. Listen around the eight-second transition.

No waveform encoder was ported: this inexpensive continuation path reuses SA3-generated source latents. Arbitrary external audio conditioning still requires the SAME-S encoder and is not demonstrated. The continuation worker completed three outputs and restored CPU settings.

## Recommendation

Use **SA3 at a fixed approximately 30-second duration as the leading experimental generator**, subject to human listening acceptance and runtime reliability work. Preserve MusicGen as the known-working fallback. Prewarm the model and generate buffered music; do not promise immediate cold-start or subsecond reaction.

This does **not** establish coexistence with openpilot inference. Exclusive GPU ownership, total host memory including compiler workers, concurrent workload scheduling and driving-time behavior remain untested. Do not interpret an offroad speed pass as authorization or evidence for production deployment.

## Reproduction

Device scratch root: `/data/sa3-feasibility`. [Benchmark](benchmark_sa3.py), [offroad/CPU wrapper](power_trained.py), [runtime environment](run_trained.sh), [CPU reference check](verify_trained.py). The isolated SA3 venv has its own Transformers dependencies; it reads existing Torch dependencies without modifying MusicGen's venv.

With model conversion and environment already staged, run:

```sh
ssh comma@192.168.3.111 '/usr/local/venv/bin/python /data/sa3-feasibility/power_trained.py --durations 30 --repeats 3 --tag reproduced'
```

For cached conditioning add `--conditioning /data/sa3-feasibility/trained_results/conditioning.npy`. Cached runs do not measure fresh prompt encoding. Keep one shape per process given the observed mixed-shape failure. Raw evidence: [baseline JSON](trained_results/trained_result.json), [fixed-30 retry JSON](trained_results/stable30_result.json), and logs in `trained_results/`.
