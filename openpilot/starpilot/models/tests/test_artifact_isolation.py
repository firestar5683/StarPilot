from itertools import combinations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from tinygrad import Context, Tensor, TinyJit
from tinygrad.uop.ops import Ops
from tinygrad_repo.examples.openpilot.helpers import dump_pickle

from openpilot.selfdrive.modeld.helpers import load_oob


def stateful_artifact(path, seed):
  state = Tensor([seed, seed + 1], device="CPU").realize()
  weight = Tensor([2., 3.], device="CPU").realize()

  @TinyJit
  def step(x):
    state.assign(state + x * weight).realize()
    return state

  x = Tensor([1., 1.], device="CPU").realize()
  for _ in range(3):
    step(x)
  artifact = {"state": state, "weight": weight, "step": step}
  dump_pickle(artifact, path)
  return artifact


def captured_buffers(artifact):
  return {u.arg.buffer for u in artifact["step"].captured._linear.toposort() if u.op is Ops.BUFFER and u.arg.buffer is not None}


class TestArtifactIsolation(unittest.TestCase):
  def setUp(self):
    self.context = Context(DEV="CPU:LLVM")
    self.context.__enter__()
    self.addCleanup(self.context.__exit__, None, None, None)
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.paths = [Path(self.directory.name) / name for name in ("lateral.pkl", "longitudinal.pkl")]
    self.originals = [stateful_artifact(path, seed) for path, seed in zip(self.paths, (1., 100.), strict=True)]
    self.loads = [self.load(self.paths[0]), self.load(self.paths[1]), self.load(self.paths[0])]

  @staticmethod
  def load(path):
    # Exercise the production loader's CPU branch without opening Metal or any external device.
    with patch("openpilot.selfdrive.modeld.helpers.sys.platform", "linux"), patch("openpilot.selfdrive.modeld.helpers.AGNOS", False):
      return load_oob(path)

  def test_separate_load_arenas_and_captured_buffers_with_originals_alive(self):
    artifacts = self.originals + self.loads
    for artifact in self.loads:
      self.assertIs(artifact["state"].uop.buffer.base, artifact["weight"].uop.buffer.base)
      self.assertIsNot(artifact["state"].uop.buffer, artifact["weight"].uop.buffer)
    for first, second in combinations(artifacts, 2):
      self.assertIsNot(first["state"].uop.buffer.base, second["state"].uop.buffer.base)
      self.assertTrue(captured_buffers(first).isdisjoint(captured_buffers(second)))
    np.testing.assert_array_equal(self.loads[0]["state"].numpy(), self.loads[2]["state"].numpy())

  def test_interleaved_execution_reset_and_repeat_load_do_not_change_other_state(self):
    expected = [artifact["state"].numpy().copy() for artifact in self.loads]
    originals = [artifact["state"].numpy().copy() for artifact in self.originals]
    for index, scale in ((0, 1.), (1, 2.), (0, 3.), (2, 4.), (1, 5.)):
      result = self.loads[index]["step"](Tensor([scale, scale], device="CPU").realize())
      expected[index] += np.array([2., 3.], dtype=np.float32) * scale
      np.testing.assert_array_equal(result.numpy(), expected[index])
      for artifact, state in zip(self.loads, expected, strict=True):
        np.testing.assert_array_equal(artifact["state"].numpy(), state)
    self.loads[0]["state"].uop.buffer.copy_from(Tensor(np.zeros(2, dtype=np.float32), device="CPU").realize().uop.buffer)
    expected[0][:] = 0
    self.loads[0]["step"](Tensor([1., 1.], device="CPU").realize())
    expected[0] += [2., 3.]
    fresh = self.load(self.paths[0])
    np.testing.assert_array_equal(fresh["state"].numpy(), originals[0])
    for artifact, state in zip(self.loads, expected, strict=True):
      np.testing.assert_array_equal(artifact["state"].numpy(), state)
    for artifact, state in zip(self.originals, originals, strict=True):
      np.testing.assert_array_equal(artifact["state"].numpy(), state)
