# Chestnut music-generation feasibility gate

## Verdict and current status

**Local neural music generation is demonstrated. Conditional GO for an asynchronous, replay-based hackathon demo.** This is an isolated experiment, not RoadScore production code.

On 2026-09-13 America/Chicago (2026-09-14 UTC), comma `192.168.3.111` generated a 2-second clip and two different 8-second clips from instrumental text conditioning. The entire MusicGen music-token transformer executed on Chestnut; text encoding, sampling, and waveform decoding executed on the comma CPU. No remote inference or prerecorded audio input was used. Network access downloaded dependencies and pretrained weights only.

The generated WAVs are the deliverables, not merely transformer outputs:

- [8 seconds, seed 123](results/clip_8s_seed123.wav)
- [8 seconds, seed 124](results/clip_8s_seed124.wav)
- [Initial 2-second output](results/first_2s.wav)

These files are valid, finite, non-silent audio with no clipped samples. **Perceptual musical quality has not been independently verified by the agent, which cannot listen to audio in this session.** A listening check was requested from the user; no judgment was received before this report. The demonstrated technical gate must not be confused with proof of polished musical quality, coherent stems, or long-form composition.

The practical decision:

1. **Can Chestnut generate music locally?** Yes: text-conditioned MusicGen inference and decoded WAV output completed on this device.
2. **Best demonstrated model/runtime?** MusicGen Small FP16, a narrow native tinygrad decoder with fixed KV storage and TinyJit, and CPU PyTorch for T5/EnCodec. The generic tinygrad PyTorch bridge was abandoned after bounded attempts.
3. **How fast?** Warm 8-second generation: 50.74 seconds on the GPU path plus 18.11 seconds for CPU decode, 68.85 seconds total. Real-time factor 8.61: a value above one means slower than playback.
4. **Coexist with driving inference?** Independent processes concurrently owning Chestnut did not work. A second owner failed with `libusb_set_configuration: Resource busy`. No driving-model deadline, preemption, thermal-soak, or combined-VRAM test was performed. Coexistence is not established.
5. **Another local architecture if coexistence fails?** Use recorded model messages during the replay demo and let Chestnut generate musical material asynchronously. Keep the model loaded; arrange, loop, and schedule its locally generated output while it generates further material. For live use, QCOM driving inference with Chestnut dedicated to music is an untested candidate; a shared GPU owner/scheduler is substantial additional work. Neither is a proven driving-safe fallback.

**Do not pivot solely because local music generation was thought impossible. Do pivot or change scope if simultaneous live driving inference on Chestnut, continuous newly generated audio at playback speed, or high-quality isolated synchronized stems are mandatory this weekend. Those gates have not passed.**

## Measurements

Hardware: ARM64 AGNOS, Linux 4.9.103, roughly 3.5 GiB host RAM, no swap; Chestnut `gfx1200`, `USBIface`, reported VRAM capacity 8,539,602,944 bytes, USB link 5000 Mbit/s. Repository revision: `6b8bb279d4a6bf5ca4c5e92a8f45edd37bba1bf7` on host and device. The vendored tinygrad belongs to that tree.

For the main benchmark, CPUs 4–7 were temporarily enabled, set to the normal openpilot 1,689,600 kHz cap, and used with four PyTorch threads. They are normally offline while offroad. No openpilot processes were stopped or driving modes activated. Original CPU settings were restored; [before](results/power_before.json) and [after](results/power_after.json) agree.

| Measurement | First 8-second run | Second 8-second run, same loaded process |
|---|---:|---:|
| Audio duration / format | 8 s, 32 kHz mono PCM16 | 8 s, 32 kHz mono PCM16 |
| Music-token generation | 100.60 s, includes JIT warmup | 50.74 s |
| CPU waveform decode | 18.73 s | 18.11 s |
| Generation + decode | 119.33 s | 68.85 s |
| Real-time factor | 14.92 | 8.61 |
| Steady token-step wall time | 0.1261 s | 0.1259 s |
| Output peak amplitude | 0.888 | 0.732 |
| Clipped-sample fraction | 0 | 0 |

Full cold process launch to the first 8-second WAV: **167.92 seconds**, including imports, checkpoint loading, text encoding, a test-only CPU reference forward, GPU weight placement, compilation, generation, and decoding. CPU text conditioning separately measured **0.684 seconds**. The warm run reused the same conditioning with a different random seed; warm prompt changes were not benchmarked.

Sampled process RSS high-water mark: **2,116,182,016 bytes (2.12 GB)**, including the test-only reference computation. Runtime snapshots were about 1.15 GB after CPU transformer release and 1.68 GB after the second decode. Sampling was every 50 ms, so this is not an exact kernel-accounted RSS maximum.

Peak tinygrad-tracked active buffer allocation: **928,465,340 bytes (0.93 GB)**. This is an allocation-counter estimate, principally Chestnut tensors, **not full physical VRAM utilization**; allocator caches, runtime reservations, and other allocations are not fully represented. Full peak physical VRAM was not measured.

The initial 2-second attempt used the offroad little cores, two PyTorch threads, and an earlier JIT setup. It took 133.30 seconds for generation, 14.40 seconds for decoding, and 234.48 seconds from process start. Do not extrapolate that cold result to steady performance.

Raw evidence: [main measurements](results/bench8_result.json), [run log](results/bench8.log), [initial measurements](results/first_2s.json), [environment versions](results/requirements.freeze.txt).

## Actual execution boundary

```text
Text prompt
  -> comma CPU: tokenizer + pretrained T5 text encoder + projection
  -> Chestnut: embeddings, positions, all 24 MusicGen transformer layers,
               self/cross-attention, KV cache, feed-forward layers, output heads
  -> comma CPU: classifier-free guidance, top-k sampling, codebook delay pattern
  -> Chestnut: next autoregressive step, repeating until all codes are generated
  -> comma CPU: pretrained EnCodec waveform decoder
  -> 32 kHz mono WAV on /data/roadscore-feasibility
```

The CPU reference logits are used only for verification, never for selecting generated tokens. The native generation implementation constructs its numerical tensors on `AMD`; the measured device interface is `USBIface`. TinyJit captures the GPU work for subsequent steps. Kernel counter values include graph dispatches and are not a count of every internal GPU shader during graph replay.

The model is [Meta MusicGen Small](https://huggingface.co/facebook/musicgen-small), pinned to revision `4c8334b02c6ec4e8664a91979669a501ec497792`. Architecture and delay-pattern handling follow [Transformers v4.46.3 MusicGen](https://github.com/huggingface/transformers/blob/v4.46.3/src/transformers/models/musicgen/modeling_musicgen.py). Model weights retain their original license (CC-BY-NC-4.0); upstream implementation attribution and licensing apply to reused architecture/code.

## What was tried and what was rejected

- **Normal ACE-Step / ROCm:** not a demonstrated path. The device does not expose `/dev/kfd`; Chestnut uses tinygrad's custom USB transport. ACE-Step's documented PyTorch/ROCm installation is not a bridge to that transport. ACE-Step was not installed or benchmarked.
- **tinygrad PyTorch bridge + MusicGen:** installed PyTorch 2.10 CPU ARM64 and compiled the existing extension successfully. A bridge GPU smoke test passed. The complete transformer produced excessive graph/scheduling overhead before the first token. An interrupted attempt reported an AMD synchronization failure during finalization. A layer-boundary materialization attempt also failed to produce a first token within the allotted several minutes and was stopped. No general compatibility layer was developed.
- **Checkpoint loading:** the original 2.36 GB safetensors mapping failed with `Cannot allocate memory`. A streaming conversion to nineteen <=64 MiB target FP16 shards (1.18 GB total) solved loading without changing kernel memory policy or adding swap.
- **Native tinygrad subset:** a small explicit implementation of the existing MusicGen decoder, using existing tensor operations, fixed KV caches, and TinyJit, completed end-to-end generation.
- **Other candidates:** Stable Audio Open Small and TinyMusician were inspected as alternatives. They were not benchmarked once the native MusicGen path succeeded. No speed or compatibility claims about them on Chestnut are justified by this experiment.

## Correctness and remaining limits

The first four input/output steps of **both** runs were checked against CPU Transformers using the same FP16 weights, text conditioning, and token inputs, including JIT execution and cache reuse. All eight checks passed cosine similarity >0.999; observed minimum was **0.999966**. Mean absolute logit errors ranged from 0.0018 to 0.0256. This is approximate FP16 agreement, not bitwise equivalence or an exhaustive model-port validation. See [validation](results/validation.json) and saved step arrays.

Both full outputs decoded successfully and had finite, nonzero samples without clipping. These checks do not establish listening quality, absence of incidental vocals, genre adherence, or harmonic compatibility between independently generated clips. The WAV files, rather than claims about their aesthetic quality, are provided for review.

The USB contention result is in [coexistence probe](results/coexist_lock.log). Separate ownership is blocked; a process priority or VRAM budget alone does not solve it. A single-owner scheduler would need measured deadlines and safe bounded GPU work. Music token-step wall time exceeds the 50 ms model frame interval; GPU-only execution time and available interleaving headroom have not been isolated.

No real-time audio-output jitter, route alignment, camera replay, modeld coexistence, or continuous thermal-soak test was attempted. Those are outside this generation gate. The device's onroad state remained false. No RoadScore daemon, UI, cereal schema, controls integration, or production source change was introduced.

## Reproduce on this device

Everything installed on-device is under `/data/roadscore-feasibility`, including its own venv, package/model caches, scripts, weights, logs, and WAVs. openpilot's Python environment was not changed. Benchmarks are offroad only.

The already-provisioned device can repeat the main benchmark:

```bash
ssh comma@192.168.3.111 \
  '/usr/local/venv/bin/python /data/roadscore-feasibility/power_bench.py --seconds 8 --repeats 2 --tag bench8'
```

This temporarily enables the big CPU cores, pins the experimental process to them, and restores prior CPU settings on exit while still offroad. Reusing the same tag overwrites that tag's previous outputs on-device; choose another tag to preserve them. The repository's copied evidence remains unchanged. Do not start this while another GPU owner is active. Repeats reuse the prompt and change the seed.

To provision a new isolated experiment directory, copy this directory's Python/shell scripts and `results/requirements.freeze.txt` to `/data/roadscore-feasibility`, then on the comma:

```bash
mkdir -p /data/roadscore-feasibility/cache /data/roadscore-feasibility/tmp
export UV_CACHE_DIR=/data/roadscore-feasibility/cache/uv
export TMPDIR=/data/roadscore-feasibility/tmp
uv venv --python /usr/bin/python3.12 /data/roadscore-feasibility/venv
uv pip install --python /data/roadscore-feasibility/venv/bin/python \
  -r /data/roadscore-feasibility/requirements.freeze.txt
/data/roadscore-feasibility/venv/bin/python /data/roadscore-feasibility/download.py
/data/roadscore-feasibility/venv/bin/python /data/roadscore-feasibility/shard.py
/usr/local/venv/bin/python /data/roadscore-feasibility/power_bench.py --seconds 8 --repeats 2 --tag bench8
```

`run_native.sh` sets the tinygrad path to the installed repository and selects `DEV=USB+AMD:LLVM`. `verify_native.py` checks `bench8` artifacts against the CPU reference; run it in the experimental venv after generation. The existing generic bridge is not needed by the demonstrated native path.

## Hackathon implication

The viable scope is a persistent local generator producing short material ahead of a deterministic arranger. With the measured configuration, plan approximately **one new 8-second asset per 69 seconds** at steady state, after a roughly three-minute cold startup. Keep locally generated material playing through repeats/transitions while further material is generated. Pitch/key/BPM matching, seamless looping, and stem controllability remain musical engineering tasks; MusicGen does not provide proven synchronized isolated stems here.

A replay demo can dedicate Chestnut to music and consume recorded openpilot predictions, satisfying genuine local generation without competing GPU owners. A live system requiring Chestnut driving inference and simultaneous music generation has **not** passed feasibility. Do not begin the full RoadScore build until the user accepts the audible material and this asynchronous/replay scope.
