"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

Every size on the wire, derived from the model's ONNX metadata.

Two graph layouts are in the wild. The queued one takes its history as
stacked inputs (img, features_buffer, desire_pulse) and the server keeps the
queues; see queues.PolicyQueues. It mirrors get_policy_npy_shapes /
make_input_queues in openpilot's selfdrive/modeld/compile_modeld.py up to
openpilot #38916. feat_dim is prod(fb[2:]); older forks use fb[2], which gives
32 rather than 16384 for the big model's (1,32,32,512) features_buffer.
tests/test_queues.py catches the drift.

The stateful one (openpilot #38916, 2026-09-15; Cinque Terre V3 onwards)
carries its history in the graph: the newest warped frame goes in as new_img,
each queue goes in as state_<q> and comes back advanced as next_state_<q>, and
the hidden state never leaves the graph.

Either way the wire carries the newest frame and three scalars, and the reply
the outputs less hidden_state (protocol 3): the queued graph's server feeds its
own hidden state back, which modeld did through prev_feat until then.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from jetlink.onnx_meta import parse_file
from jetlink.protocol import INFER_REQ_SIZE, INFER_RESP_SIZE

# openpilot ModelConstants; duplicated so the server needs no openpilot import
MODEL_RUN_FREQ = 20
MODEL_CONTEXT_FREQ = 5
DEFAULT_FRAME_SKIP = MODEL_RUN_FREQ // MODEL_CONTEXT_FREQ  # 4

CHUNK = 4 << 20  # model upload chunk

# the driving output every layout has, 18452 floats in openpilot's layout
DRIVING_OUTPUT = 'outputs'
# the slice of it that stays on the server; 16384 of the 18452
HIDDEN_STATE = 'hidden_state'
# the input only a stateful graph has; see the module docstring
STATEFUL_FRAME = 'new_img'
STATE_OUTPUT_PREFIX = 'next_'


@dataclass(frozen=True)
class ModelSpec:
  """Everything both ends need to agree on, derived from the ONNX."""
  sha256: str
  nbytes: int
  frame_skip: int
  input_shapes: dict[str, tuple[int, ...]]
  output_shapes: dict[str, tuple[int, ...]]
  output_slices: dict[str, slice]
  checkpoint: str | None

  # --- layout ---
  @property
  def stateful(self) -> bool:
    """The graph keeps its own history (openpilot #38916)."""
    return STATEFUL_FRAME in self.input_shapes

  @property
  def state_pairs(self) -> dict[str, str]:
    """state_<q> input -> the next_state_<q> output that feeds it next frame.
    Empty for a queued graph. Same rule as openpilot's ModelState."""
    return {n: STATE_OUTPUT_PREFIX + n for n in self.input_shapes
            if STATE_OUTPUT_PREFIX + n in self.output_shapes}

  # --- vision ---
  @property
  def img_shape(self) -> tuple[int, ...]:
    return self.input_shapes['img']  # (1, 12, H, W); queued graphs only

  @property
  def n_frames(self) -> int:
    return self.img_shape[1] // 6

  @property
  def model_hw(self) -> tuple[int, int]:
    # new_img is (2, 6, H, W) and img (1, 12, H, W): the last two either way
    shape = self.input_shapes[STATEFUL_FRAME] if self.stateful else self.img_shape
    return shape[-2], shape[-1]

  @property
  def img_buf_shape(self) -> tuple[int, int, int, int]:
    h, w = self.model_hw
    return (self.frame_skip * (self.n_frames - 1) + 1, 6, h, w)

  @property
  def warped_shape(self) -> tuple[int, int, int, int]:
    """What `warp` on the comma produces: narrow and wide stacked."""
    h, w = self.model_hw
    return (2, 6, h, w)

  @property
  def warped_nbytes(self) -> int:
    return math.prod(self.warped_shape)  # uint8

  # --- recurrent / scalar inputs ---
  @property
  def feat_dim(self) -> int:
    """Flattened per-frame feature size. (1,32,32,512) -> 16384."""
    fb = self.input_shapes['features_buffer']
    return math.prod(fb[2:])

  @property
  def packed_shapes(self) -> dict[str, tuple[int, ...]]:
    """The floats a frame sends after the image: compile_modeld's
    packed_npy_inputs less prev_feat, which the server keeps."""
    scalars = {'traffic_convention': tuple(self.input_shapes['traffic_convention']),
               'action_t': tuple(self.input_shapes['action_t'])}
    if self.stateful:
      # the pulse is the graph's own input
      return {'desire': (math.prod(self.input_shapes['desire']),), **scalars}
    return {'desire': (self.input_shapes['desire_pulse'][2],), **scalars}

  @property
  def prev_feat_shape(self) -> tuple[int, int]:
    """The hidden state a queued graph's server feeds back each frame."""
    return (self.input_shapes['features_buffer'][0], self.feat_dim)

  @property
  def packed_layout(self) -> dict[str, tuple[slice, tuple[int, ...]]]:
    """Where each of packed_shapes sits in the flat floats: name -> (slice, shape)."""
    out, offset = {}, 0
    for name, shape in self.packed_shapes.items():
      out[name] = (slice(offset, offset + math.prod(shape)), shape)
      offset += math.prod(shape)
    return out

  @property
  def packed_nelem(self) -> int:
    return sum(math.prod(s) for s in self.packed_shapes.values())

  def feed_back(self, packed, output) -> None:
    """Nothing: the server feeds the hidden state back itself (protocol 3).
    Kept for the modeld glue that still calls it after every frame."""

  @property
  def packed_nbytes(self) -> int:
    return self.packed_nelem * 4  # float32

  @property
  def feat_q_shape(self) -> tuple[int, int, int]:
    fb = self.input_shapes['features_buffer']
    return (self.frame_skip * fb[1], fb[0], self.feat_dim)

  @property
  def desire_q_shape(self) -> tuple[int, int, int]:
    dp = self.input_shapes['desire_pulse']
    return (self.frame_skip * dp[1], dp[0], dp[2])

  # --- output ---
  @property
  def output_nelem(self) -> int:
    return math.prod(self.output_shapes[DRIVING_OUTPUT])

  @property
  def output_nbytes(self) -> int:
    return self.output_nelem * 4  # we return float32, as openpilot's JIT does

  # cached: the client reads these on every frame, and a frozen dataclass
  # without slots has a __dict__ to keep them in
  @cached_property
  def hidden_range(self) -> tuple[int, int] | None:
    """[start, stop) of hidden_state in the output: what the reply leaves out.
    Its ends resolve as Python slicing resolves them, an open end or one
    counted from the back included, which is also how the Swift server reads
    them (NamedSlice.range(in:)). None when the model names no such slice or
    it takes nothing, and then the reply is whole."""
    s = self.output_slices.get(HIDDEN_STATE)
    if s is None or s.step not in (None, 1):
      return None
    start, stop, _ = s.indices(self.output_nelem)
    return (start, stop) if start < stop else None

  @cached_property
  def reply_nelem(self) -> int:
    """The floats an INFER_RESP carries: the output less hidden_state."""
    h = self.hidden_range
    return self.output_nelem - (h[1] - h[0] if h else 0)

  # --- wire sizes ---
  @property
  def infer_req_nbytes(self) -> int:
    return INFER_REQ_SIZE + self.warped_nbytes + self.packed_nbytes

  @property
  def infer_resp_nbytes(self) -> int:
    """Without telemetry; with Flag.WANT_HIDDEN it is INFER_RESP_SIZE +
    output_nbytes."""
    return INFER_RESP_SIZE + self.reply_nelem * 4

  # -- the wire form of a spec ---------------------------------------------
  # One encoder and one decoder: both ends and the bench need this, and copies
  # would drift the moment a field is added.

  def to_dict(self) -> dict:
    return {
      'sha256': self.sha256,
      'nbytes': self.nbytes,
      'frame_skip': self.frame_skip,
      'checkpoint': self.checkpoint,
      'input_shapes': {k: list(v) for k, v in self.input_shapes.items()},
      'output_shapes': {k: list(v) for k, v in self.output_shapes.items()},
      'output_slices': {k: [v.start, v.stop] for k, v in self.output_slices.items()},
    }

  @classmethod
  def from_dict(cls, d: dict) -> ModelSpec:
    return cls(
      sha256=d['sha256'], nbytes=d['nbytes'],
      frame_skip=d.get('frame_skip', DEFAULT_FRAME_SKIP),
      input_shapes={k: tuple(v) for k, v in d['input_shapes'].items()},
      output_shapes={k: tuple(v) for k, v in d['output_shapes'].items()},
      output_slices={k: slice(*v) for k, v in d['output_slices'].items()},
      checkpoint=d.get('checkpoint'))

  @classmethod
  def load(cls, path: str | Path) -> ModelSpec:
    """A spec saved as to_dict's JSON."""
    return cls.from_dict(json.loads(Path(path).read_text()))


def sha256_file(path: str, bufsize: int = 1 << 20) -> tuple[str, int]:
  h = hashlib.sha256()
  n = 0
  with open(path, 'rb') as f:
    while chunk := f.read(bufsize):
      h.update(chunk)
      n += len(chunk)
  return h.hexdigest(), n


def spec_from_onnx(path: str, frame_skip: int = DEFAULT_FRAME_SKIP,
                   sha256: str | None = None, nbytes: int | None = None) -> ModelSpec:
  meta = parse_file(path)
  if sha256 is None or nbytes is None:
    sha256, nbytes = sha256_file(path)
  return ModelSpec(sha256=sha256, nbytes=nbytes, frame_skip=frame_skip, input_shapes=dict(meta.inputs),
                   output_shapes=dict(meta.outputs), output_slices=meta.output_slices, checkpoint=meta.model_checkpoint)
