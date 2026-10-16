"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

The comma-side warp: openpilot's own, where it lives, what loads it, how the
frame loop runs it (Warp), and the small model's reset for a fallback.

The warp stays on the comma (see model_state). openpilot's modeld runs it as
a JIT of its own, driving_warp_{w}x{h}_tinygrad.pkl, one per camera, and the
link runs the same pickle: both camera frames in as one (2, frame size) uint8
input_frame, their transforms as one (2, 3, 3) M_inv, and out the
(2, 6, 128, 256) uint8 frame the link sends. The fork's adapter says where it
is. Nothing compiles one at runtime: a device without one runs the small
model.

load() is what stands between a bad pickle and the car.

tinygrad is the fork's, and only modeld has it: every import of it here is
inside the function that needs it.
"""
from __future__ import annotations

import ctypes
import pickle
from pathlib import Path

# what the warp's TinyJit was captured with: sorted(kwargs) of modeld's call
WARP_INPUT_NAMES = ['M_inv', 'input_frame']
# KGSL allocation flags (msm_kgsl.h) for memory the GPU's accesses snoop the
# CPU's caches on, mapped write-back: KGSL_MEMFLAGS_IOCOHERENT, which
# tinygrad's kgsl bindings lack, and KGSL_CACHEMODE_WRITEBACK (3 << 26). See
# Warp
COHERENT_WRITEBACK = (1 << 31) | (3 << 26)


def init_device(log) -> None:
  """Bring the GPU up now, on the caller's thread, and turn tinygrad's
  compile pool off for the process.

  tinygrad initialises the device on its first kernel run and spawns a libusb
  event thread doing it. A thread created after config_realtime_process(7, 54)
  inherits SCHED_FIFO 54 and the core-7 pin and preempts the frame loop,
  enough to drop ~5% of frames. Failure is not a reason to refuse the accelerator.
  """
  try:
    # modeld never needs the pool (engine/worker.py), and its PARALLEL idle
    # interpreters' handler threads would inherit FIFO 54 on core 7
    from tinygrad.helpers import PARALLEL
    PARALLEL.value = 0
  except Exception:
    log.exception("jetlink: could not turn tinygrad's compile pool off")
  try:
    from tinygrad.tensor import Tensor
    Tensor([0.0]).realize()
  except Exception:
    log.exception("jetlink: could not bring the gpu up before modeld goes realtime")


class Warps:
  """The warps this device's checkout has, where the fork's adapter says."""

  def __init__(self, op):
    self.op = op
    # nothing makes a warp at runtime and the checkout's are there before
    # manager, so the answer holds for the life of the process; the UI asks
    # at 5 Hz
    self._built: bool | None = None

  def geometry(self) -> tuple[int, int, int, int]:
    """(cam_w, cam_h, model_w, model_h) for this device: the warp modeld
    loads. If the link's model disagrees, load() raises and the drive is
    small-model."""
    return tuple(self.op.camera())

  def path(self, cam_w: int, cam_h: int, model_w: int, model_h: int) -> Path:
    return Path(self.op.warp_path(cam_w, cam_h, model_w, model_h))

  def is_cached(self, cam_w: int, cam_h: int, model_w: int, model_h: int) -> bool:
    """Is there a warp for this geometry? Presence only: a pickle from an
    incompatible tinygrad raises in load()."""
    return self.path(cam_w, cam_h, model_w, model_h).is_file()

  def built(self) -> bool:
    """Is there a warp for this device's camera? Without one the link cannot
    run the large model, which the offroad alert says (status.NO_WARP)."""
    if self._built is None:
      self._built = self.is_cached(*self.geometry())
    return self._built

  def load(self, cam_w: int, cam_h: int, model_w: int, model_h: int) -> dict:
    """The warp as openpilot pickles it: {'run': its TinyJit, 'input_specs':
    {name: (shape, dtype, device)}}. Raises if it is not there or is not one
    the frame loop can run.

    modeld's big-model load is wrapped in the fallback to the small model, and a
    warp that cannot be trusted must not reach the car.
    """
    path = self.path(cam_w, cam_h, model_w, model_h)
    if not path.is_file():
      raise RuntimeError(f"no warp for {cam_w}x{cam_h} -> {model_w}x{model_h} at {path}")
    with open(path, 'rb') as f:
      warp = pickle.load(f)
    if not isinstance(warp, dict) or not {'run', 'input_specs'} <= warp.keys():
      raise RuntimeError(f"{path.name} is not a driving warp: {type(warp).__name__}")

    # a JIT pickled before TinyJit captured loads fine and computes nothing; one
    # captured under other names raises JitError on the first frame of a drive
    captured = getattr(warp['run'], 'captured', None)
    if captured is None:
      raise RuntimeError("the warp was pickled before it captured; it computes nothing")
    names = list(getattr(captured, 'expected_names', []))
    if names != WARP_INPUT_NAMES:
      raise RuntimeError(f"the warp expects {names}, the frame loop passes {WARP_INPUT_NAMES}")
    specs = warp['input_specs']
    frames, tfm = tuple(specs['input_frame'][0]), tuple(specs['M_inv'][0])
    if len(frames) != 2 or frames[0] != 2 or tfm != (2, 3, 3):
      raise RuntimeError(f"the warp takes frames {frames} and transforms {tfm}, not two of each")
    made = tuple(getattr(captured.ret, 'shape', ()))
    if made != (2, 6, model_h // 2, model_w // 2):
      raise RuntimeError(f"the warp makes {made}, not a {model_w}x{model_h} model's input")
    return warp


class Warp:
  """The warp as modeld's frame loop runs it: start() with two camera buffers
  and their transforms, wait(), and `output` holds the warped frame, where the
  link sends it from.

  openpilot's warp takes both frames as one buffer, so start() copies the
  camera buffers in, as modeld does, and the transforms beside them. Two
  things the JIT alone does not do, measured on the comma:
  - Its output lives in GPU memory the CPU reads through its cache. tinygrad
    maps a QCOM buffer write-combined, which the CPU reads uncached: copying
    the 393 KB out takes 2.9 ms, the kernel's copy straight from that mapping
    7.3 ms. The Adreno 630 is IO-coherent, so KGSL memory flagged IOCOHERENT
    and write-back is right to read once the GPU is done: 0.22 ms for the
    kernel's copy, the GPU's own time unchanged. It moves before the first
    call, which links the JIT to its buffers' addresses.
  - TinyJit prepares and checks every call's inputs, a graph rewrite per
    input: 0.97 ms of a 1.93 ms call. Every frame's inputs are the same two
    buffers, which start() writes into, so they are checked once, by the
    warm-up's calls through TinyJit, and a frame replays the capture.

  The warm-up, the link of the JIT and its first runs, is paid here rather
  than on modeld's frame loop.
  """

  def __init__(self, warp: dict, frame_size: int):
    import numpy as np
    from tinygrad.device import Device
    from tinygrad.tensor import Tensor
    jit, specs = warp['run'], warp['input_specs']
    (frames_shape, _, _), (tfm_shape, _, _) = specs['input_frame'], specs['M_inv']
    # what it reads of each camera buffer: modeld's frame_copy_size, short of
    # the buffer's end
    self._frame_size = frames_shape[1]
    if self._frame_size > frame_size:
      raise RuntimeError(f"the warp reads {self._frame_size} bytes a frame, past a {frame_size} byte camera buffer")
    out = jit.captured.ret.uop.base.buffer
    self._device = out.device
    if self._device.startswith('QCOM'):
      _make_coherent(out)
    # the two buffers every frame passes, written in place by start()
    self._tensors = {name: Tensor(np.zeros(shape, dtype=dtype), device=device).realize()
                     for name, (shape, dtype, device) in specs.items()}
    for _ in range(2):
      jit(**self._tensors)
    self.wait = Device[self._device].synchronize
    self.wait()
    self.output = out.as_memoryview(allow_zero_copy=True)
    self._frames = np.frombuffer(self._view('input_frame'), dtype=np.uint8).reshape(frames_shape)
    self._at = [self._frames[i].ctypes.data for i in range(2)]
    self._tfm = np.frombuffer(self._view('M_inv'), dtype=np.float32).reshape(tfm_shape)
    self._replay = jit.captured
    self._inputs = [self._tensors[name].uop.base for name in WARP_INPUT_NAMES]

  def _view(self, name: str) -> memoryview:
    """The CPU's view of an input buffer, not a copy of it."""
    return self._tensors[name].uop.base.buffer.as_memoryview(allow_zero_copy=True)

  def start(self, frame: int, big_frame: int, tfm, big_tfm) -> None:
    """Warp the camera buffers at these addresses under their transforms.
    `output` is the frame once wait() returns, until the next start(). The
    GPU is idle here: every start() is waited for before the next."""
    ctypes.memmove(self._at[0], frame, self._frame_size)
    ctypes.memmove(self._at[1], big_frame, self._frame_size)
    self._tfm[0] = tfm
    self._tfm[1] = big_tfm
    self._replay(self._inputs, {})


def _make_coherent(out) -> None:
  """Move a QCOM buffer to KGSL memory flagged IOCOHERENT and write-back.
  Raises if the kernel keeps either flag back (the allocation's record holds
  its answer): write-back memory that is not coherent reads stale frames."""
  from tinygrad.device import Device
  dev = Device[out.device]
  mem = dev._gpu_alloc(out.nbytes, flags=COHERENT_WRITEBACK)
  if mem.meta[0].flags & COHERENT_WRITEBACK != COHERENT_WRITEBACK:
    dev._gpu_free(mem)
    raise RuntimeError(f"the GPU driver kept back IO-coherent memory (flags {mem.meta[0].flags:#x})")
  out.deallocate()
  out.allocate(opaque=mem)


def reset_queues(queues, arrays, prev_desire=None):
  """A small model's reset, captured now: `queues`, its tensors on the GPU,
  zeroed by one TinyJit, then `prev_desire` and each numpy array in `arrays`
  in place. Every buffer keeps its identity, which the model's own JIT is
  linked to, and the reset allocates and compiles nothing, so it may run on
  the frame thread. What an adapter's small_reset returns."""
  from tinygrad import Tensor, TinyJit
  queues, arrays = tuple(queues), tuple(arrays)

  @TinyJit
  def clear():
    Tensor.realize(*(q.assign(0) for q in queues))

  # TinyJit captures on its second call, and one with nothing to run raises
  # there. Its kernels compile here, after init_device() turned the compile
  # pool off
  if queues:
    for _ in range(3):
      clear()

  def reset():
    if queues:
      clear()
    if prev_desire is not None:
      prev_desire.fill(0)
    for array in arrays:
      array.fill(0)

  return reset


def reset_for_stock(state, prev_desire=None):
  """The reset of stock modeld's ModelState layout, captured now, as its warmup
  zeroes it: the recurrent state on the GPU (input_queues named by
  state_pairs) and the one packed host buffer (packed_input), and the desire
  edge. `state` is the ModelState, or a modeld_v2 native bundle's adapter,
  which keeps the same layout."""
  return reset_queues([state.input_queues[name] for name in state.state_pairs], (state.packed_input,), prev_desire)


def prepare_reset(model):
  """Capture the small model's reset before driving, keeping its JIT's buffer identities.

  Its history is stale after the Jetson ran, so a fallback starts from the
  zero history modeld's warmup leaves it at. Nothing is allocated or compiled
  on the failure frame, so never through modeld_v2's reset_warmup_buffers(),
  which compiles on it. jetlink's own, for an adapter without small_reset
  (interface.ModelSide).

  The small model is whatever the fork's modeld runs, and each keeps its
  history its own way. Stock modeld's ModelState, and a modeld_v2 native
  bundle's adapter: the recurrent state on the GPU (state_pairs) and one
  packed host buffer (packed_input), as their warmup zeroes them. A modeld_v2
  legacy bundle's adapter: history queues on the GPU, and numpy inputs. Any
  other ModelState with input_queues (StarPilot's): every queue on the GPU,
  and its numpy inputs (numpy_inputs, or npy); its own _reset_state() makes
  new tensors, which its JIT is not linked to. The fork's tests pin those names.
  """
  adapter = getattr(model, 'adapter', None)
  keeper = model if adapter is None else adapter
  prev_desire = getattr(model, 'prev_desire', None)
  if adapter.is_native if adapter is not None else hasattr(model, 'state_pairs'):
    return reset_for_stock(keeper, prev_desire)
  queues = [q for q in keeper.input_queues.values() if q.device != 'NPY']
  arrays = (keeper.numpy_inputs if hasattr(keeper, 'numpy_inputs') else keeper.npy).values()
  return reset_queues(queues, arrays, prev_desire)
