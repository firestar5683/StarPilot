"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

A queued graph's history buffers, in numpy: the reference the server's staging
is held to.

openpilot folds these into the tinygrad JIT on the GPU. Shipping the history
across the link would cost ~10 MB a frame, so the queues live on the server and
the comma sends only the newest warped frame and the packed scalars. The hidden
state the graph returns stays there too: the next frame pushes it into the
features queue, where modeld's prev_feat went. The fork's tests/test_queues.py
checks this against the tinygrad original, and the staging conformance fixture
(JetlinkKit/Scripts/make_conformance_fixtures.py) holds the Swift server's
queues to this, bit for bit.

openpilot's rolling `cat(buf[1:], new)`, stored in float16 rather than cast at
the model boundary, which gives the same values since each row is cast once.
Pass dtype=np.float32 for openpilot's exact intermediates.

A stateful graph (openpilot #38916) does the queueing itself, so there is
nothing here for one of those.
"""
from __future__ import annotations

import numpy as np

from jetlink.spec import DRIVING_OUTPUT, ModelSpec


class PolicyQueues:
  """The server's state for one queued model. Everything `run_policy` owned in
  the JIT, and the prev_feat modeld carried from one frame's output to the next."""

  def __init__(self, spec: ModelSpec, dtype=np.float16):
    self.spec = spec
    hidden, size = spec.hidden_range, int(np.prod(spec.prev_feat_shape))
    if hidden is None or hidden[1] - hidden[0] != size:
      raise ValueError(f"a queued graph needs a hidden_state output of {size} floats to feed back; "
                       f"its output_slices give {hidden}")
    self._hidden = slice(*hidden)
    self.img_q = np.zeros(spec.img_buf_shape, dtype)
    self.big_img_q = np.zeros(spec.img_buf_shape, dtype)
    self.feat_q = np.zeros(spec.feat_q_shape, dtype)
    self.desire_q = np.zeros(spec.desire_q_shape, dtype)
    # float32, as the comma held it: the values the reply carried and the
    # comma sent back, cast into the queue at the same point
    self.prev_feat = np.zeros(spec.prev_feat_shape, np.float32)

  def reset(self) -> None:
    """RESET_QUEUES: empty history, and nothing to feed back."""
    for q in (self.img_q, self.big_img_q, self.feat_q, self.desire_q, self.prev_feat):
      q[...] = 0

  def new_client(self) -> None:
    """A hello: the next frame feeds back zeros, as a new modeld's prev_feat
    did. The queues stay until the client resets them."""
    self.prev_feat[...] = 0

  def after_run(self, outputs: dict[str, np.ndarray], dest=None) -> None:
    """Keep this frame's hidden state for the next one.

    Only after a frame whose outputs are all finite: modeld fed back only
    what infer_end returned, and it raises on NOT_FINITE and on a failed run.
    `dest` is unused; the fork's test_queues still passes it.
    """
    self.prev_feat.reshape(-1)[...] = np.asarray(outputs[DRIVING_OUTPUT], np.float32).reshape(-1)[self._hidden]

  def step(self, warped: np.ndarray, packed: np.ndarray) -> dict[str, np.ndarray]:
    """Advance the queues one frame and return the model's inputs, as new arrays.

    warped: (2, 6, H, W) uint8 from openpilot's warp. packed: flat float32,
    laid out per ModelSpec.packed_shapes. The features queue takes prev_feat,
    the hidden state after_run kept.
    """
    spec, fs = self.spec, self.spec.frame_skip
    if warped.shape != spec.warped_shape:
      raise ValueError(f"warped {warped.shape} != {spec.warped_shape}")
    if packed.size != spec.packed_nelem:
      raise ValueError(f"packed {packed.size} != {spec.packed_nelem}")
    desire, traffic_convention, action_t = (packed[at] for at, _ in spec.packed_layout.values())
    for q, row in ((self.img_q, warped[0]), (self.big_img_q, warped[1]),
                   (self.desire_q, desire), (self.feat_q, self.prev_feat)):
      q[:-1] = q[1:]
      q[-1] = row.reshape(q.shape[1:])
    shapes, dtype, des = spec.input_shapes, self.img_q.dtype, self.desire_q
    # features_buffer is declared 4-D (1,32,32,512); the queue's (32,1,16384)
    # rows are the same values, so a reshape covers it
    return {
      'img': self.img_q[::fs].copy().reshape(shapes['img']),
      'big_img': self.big_img_q[::fs].copy().reshape(shapes['big_img']),
      'desire_pulse': des.reshape(-1, fs, *des.shape[1:]).max(axis=1).reshape(shapes['desire_pulse']),
      'traffic_convention': traffic_convention.astype(dtype).reshape(shapes['traffic_convention']),
      'action_t': action_t.astype(dtype).reshape(shapes['action_t']),
      'features_buffer': self.feat_q[::fs].copy().reshape(shapes['features_buffer']),
    }
