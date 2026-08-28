# StarPilot Live MetaDrive Simulator
sudo apt install libnvidia-gl-610   # match the KMD version shown by nvidia-smi (610.88)
cd /home/prabh/Projects/openpilot/.host_runtime/linux/worktree && uv pip install --python .venv/bin/python3 PyOpenGL cuda-python 2>&1 | tail -15

Runs the **entire** openpilot stack (`manager.py` -> modeld/controlsd/plannerd/locationd)
on the host PC, bridged to a **straight-road MetaDrive world**, so you can drive the
various longitudinal modes live and watch them behave.

This is a StarPilot-specific wrapper. Upstream docs: `tools/sim/launch_openpilot.sh` +
`run_bridge.py` (stock MetaDrive bridge).

---

## Quick start

```bash
# one command, pick a mode:
./tools/sim/starpilot_sim.sh hem        # Hybrid Experimental Mode
./tools/sim/starpilot_sim.sh exp        # standard Experimental mode
./tools/sim/starpilot_sim.sh chill      # pure Chill / CCM mode
./tools/sim/starpilot_sim.sh cem        # Conditional Experimental Mode

# extra flags (order doesn't matter):
./tools/sim/starpilot_sim.sh hem --headless   # no UI window
./tools/sim/starpilot_sim.sh hem --joystick   # use a game wheel instead of keyboard
./tools/sim/starpilot_sim.sh hem --cpu        # force CPU backend for the model
./tools/sim/starpilot_sim.sh hem --pkl        # use the precompiled pickle instead of tracing the ONNX live
```

Run it from a **real terminal with a display** (that's where the UI renders and the
keyboard controls work). Press `q` to exit.

### What each mode does

| command   | toggle set                                                                  |
|-----------|-----------------------------------------------------------------------------|
| `exp`     | `ConditionalExperimental=off, ConditionalChill=off, HybridExperimental=off` (full-time experimental) |
| `chill`   | `ConditionalChill=on` (full-time Chill / ACC)                                |
| `cem`     | `ConditionalExperimental=on` (conditional experimental)                      |
| `hem`     | `HybridExperimental=on` (hybrid experimental)                                |

These are mutually exclusive; the launcher sets exactly one.

---

## Prerequisites

- Host build already provisioned under `.host_runtime/linux/worktree` (the launcher
  runs `./dev sync` to refresh it from this repo).
- `metadrive-simulator` installed in the host worktree venv (it is, as a dependency).
- The driving model in the model store: `~/.comma/starpilot/data/models/rdf43_driving_tinygrad.pkl`.
  This is a PC (CUDA) build compiled from `driving_supercombo.onnx` (also kept in the model
  store as `driving_supercombo.onnx`). The launcher copies the pkl into the worktree where
  `modeld` expects it on every launch.
- An NVIDIA GPU with working tinygrad **CUDA** (default model device).

## How the model is built

**Default (Option 1, live-ONNX):** `modeld` loads `driving_supercombo.onnx` directly and
traces it in-memory on the RTX at startup — `OnnxRunner` + `TinyJit` captured live during the
first frames. There is **no** tinygrad-JIT pickle round-trip, so the JIT-unpickler bug (which
rewrites kernel targets to the comma-device default `QCOM`) is never triggered. This is the
reliable path on a PC host. Set `STARPIOT_LIVE_ONNX=<path-to>.onnx` (the sim launcher does
this for you) to enable it; `STARPIOT_MODEL_SIZE` defaults to `512x256`.

**Fallback (--pkl):** a precompiled tinygrad-JIT pickle, built for the PC CUDA backend:

```bash
./dev python selfdrive/modeld/compile_modeld.py \
  --model-type supercombo --model-size 512x256 --camera-resolutions 1928x1208 \
  --supercombo-onnx ~/.comma/starpilot/data/models/driving_supercombo.onnx \
  --behavior-version v15 \
  --output ~/.comma/starpilot/data/models/rdf43_driving_tinygrad.pkl
```

`compile_modeld.py` now skips its JIT pickle round-trip by default (`STARPIOT_DO_JIT_ROUNDTRIP`
re-enables it); that round-trip rewrites compiled device/target refs inside the JIT to the
comma-device default (`QCOM`), producing an artifact that cannot run on a PC CUDA host.
Because the pkl path still goes through this fork's buggy JIT unpickler at load time, prefer
the live-ONNX path.

## GPU notes

- **Model** runs on the RTX via tinygrad **CUDA** (`DEV=CUDA`, `STARPIOT_SIM_DEV=CUDA`).
  The whole model — camera warp **and** policy — is compiled for CUDA (`WARP_DEV=CUDA`).
  Pass `--cpu` to force the CPU backend instead.

### Low MetaDrive FPS / "not using the GPU" (read this)

Two separate things use the GPU in this sim:

1. **tinygrad model** — already CUDA on the RTX (works, verified). Unaffected by the below.
2. **MetaDrive world + camera rendering** (Panda3D). This is the part that was slow.

**Verified diagnosis on this laptop:** the RTX 4050 is **compute-only** — `nvidia-smi` shows
`Disp.A: Off`, 0 MiB — so it is *not* driving the display. MetaDrive renders through Panda3D's
`glxGraphicsPipe`, which runs on the display's GL context. On this host that resolves to
**Mesa llvmpipe software** rendering (checked with `glGetString(GL_RENDERER)` →
`llvmpipe (LLVM 20.1.2)`), i.e. **no GPU at all**, which is exactly why FPS is low.

- Installing `libnvidia-gl-610` adds the NVIDIA GL userspace libs (`10_nvidia.json`,
  `libGLX_nvidia.so`), but it does **not** change the sim's FPS here, because NVIDIA is not
  the display GPU and GLX still uses the iGPU/Mesa stack. (PRIME offload
  `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia` was tried and fails with
  "Could not find a usable pixel format".)
- The real fix is making the *display's* GL hardware-accelerated (proper iGPU GLX on `:0`,
  or an NVIDIA/EGL offscreen render setup) — a system/graphics-config task, not a repo change.

**CUDA image capture is off by default (and must stay off on non-NVIDIA GL).** Installing
`cupy`/`PyOpenGL`/`cuda-python` flips MetaDrive's `_cuda_enable` to `True`; if `image_on_cuda`
then follows it, `cudaGraphicsGLRegisterImage` fails with `cudaErrorUnknown` on a Mesa GL
context and **crashes MetaDrive at sensor init**. The bridge therefore defaults
`image_on_cuda` to `False` (safe CPU `RTMCopyRam` readback). To opt into CUDA images on a
machine where the GL context genuinely is NVIDIA-backed, set `STARPIOT_CUDA_IMAGES=1`.

The sim's `camerad` RGB→NV12 conversion likewise falls back to CPU numpy when no OpenCL ICD
is present; install `nvidia-opencl-icd` if you want that on-GPU too.

---

## Driving controls (keyboard)

| key | action |
|-----|--------|
| `r` | Reset simulation (back to the start point) |
| `i` | Toggle ignition (**starts ON** by default) |
| `2` | Cruise **Set** — engages openpilot (lateral + longitudinal control) |
| `1` | Cruise Resume / accel |
| `3` | Cruise Cancel |
| `q` | Quit everything |
| `w/a/s/d` | Manual throttle / steer / brake |

### "Go back to start, then turn on lateral + longitudinal control like in the car"

1. Press **`r`** — the world resets and the car respawns at the start of the straight road.
2. Press **`2`** (cruise set) — openpilot engages: **lateral** (steering) and
   **longitudinal** (accel/brake) control turn on together, same as hitting the cruise
   set button in the car. `1` bumps the set speed up, `3` cancels.
3. The bridge also auto-engages shortly after startup, so you usually just have to sit back
   and let it drive the straight road.

> **Ignition is ON by default.** If the status line ever shows `Ignition: False`, press
> `i` once to turn it back on. Note the trap: pressing `i` toggles it *off*, so don't press
> it at startup unless you want to switch it off.

---

## Status / known blocker

With the **live-ONNX** path (the default), `modeld` traces the model in-memory on the RTX and
the old QCOM-rewrite blocker is bypassed entirely — there is no JIT pickle to unpickle, so
`CUDA_ERROR_INVALID_IMAGE` from a corrupted camera-warp kernel no longer applies. If you run
with `--pkl` instead, the pickle path still hits this fork's buggy JIT unpickler at load time
(rewrites kernel targets to `QCOM::a630`, then the warp recompiles as a QCOM image), which is
exactly why Option 1 is the default. Fixing the pkl path would require a small change in the
vendored tinygrad to preserve the target device across JIT unpickle.

For a working stop-sign reproduction today, use the replay forensics on a real route:
```bash
./dev python tools/replay/hem_forensic.py <dongleId>/<routeId> --segments 0,1
./dev python tools/replay/mode_sim.py <dongleId>/<routeId> --segment 0
```
