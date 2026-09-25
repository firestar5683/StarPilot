import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from tinygrad import Context, Device
from tinygrad.helpers import OPENPILOT_HACKS, TC_MIN_GLOBALS, TC_OPT


class TestHelperImport(unittest.TestCase):
  def test_catalog_compile_import_does_not_select_or_open_device(self):
    # A fresh process covers the real transitive import, without a prior module
    # cache or the host's selected device concealing import-time probing.
    code = '''
import importlib
from unittest.mock import patch
from tinygrad import Context, Device

def unexpected_probe(*args):
  raise AssertionError("catalog import attempted device auto-selection")

with Context(DEV=""), patch.object(type(Device), "_select_device", property(unexpected_probe)), \\
     patch.object(type(Device), "__getitem__", side_effect=AssertionError("catalog import opened a device")):
  importlib.import_module("openpilot.starpilot.models.compile")
'''
    for module in ("tinygrad_repo.examples.openpilot.helpers", "openpilot.starpilot.models.compile"):
      with self.subTest(module=module):
        source = code.replace("openpilot.starpilot.models.compile", module)
        result = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  @staticmethod
  def load_helper():
    path = Path(__file__).resolve().parents[4] / "tinygrad_repo/examples/openpilot/helpers.py"
    spec = importlib.util.spec_from_file_location("benchmark_import_regression", path)
    assert spec is not None and spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    # Import under QCOM, then call under another device to catch settings that
    # were incorrectly captured by an import-time decorator.
    with Context(DEV="QCOM"):
      spec.loader.exec_module(helper)
    return helper

  def test_benchmark_uses_call_time_device_and_preserves_results(self):
    helper = self.load_helper()
    for device, expected in (("AMD", (1, 2, 32)), ("QCOM", (1, 7, 11)), ("CPU", (1, 7, 11))):
      with self.subTest(device=device):
        events, elapsed = [], []
        array = np.array([1., 2.], dtype=np.float32)
        output = SimpleNamespace(realize=lambda events=events: events.append("realize"), numpy=lambda array=array: array)
        fake_device = SimpleNamespace(synchronize=lambda events=events: events.append("sync"))

        def run(value, expected=expected, events=events, output=output):
          self.assertEqual(value, 9)
          self.assertEqual((OPENPILOT_HACKS.value, TC_OPT.value, TC_MIN_GLOBALS.value), expected)
          events.append("run")
          return output

        with Context(DEV=device, OPENPILOT_HACKS=0, TC_OPT=7, TC_MIN_GLOBALS=11), \
             patch.object(type(Device), "default", property(lambda _, fake_device=fake_device: fake_device)), \
             patch.object(helper, "get_parameters", side_effect=lambda value: [value]), \
             patch.object(helper.time, "perf_counter", side_effect=(10., 10.25)):
          result = helper.benchmark(run, cb=elapsed.append, value=9)
          self.assertEqual((OPENPILOT_HACKS.value, TC_OPT.value, TC_MIN_GLOBALS.value), (0, 7, 11))
        self.assertEqual(events, ["sync", "run", "realize", "sync"])
        self.assertEqual(elapsed, [.25])
        np.testing.assert_array_equal(result[0], array)
        self.assertIsNot(result[0], array)

  def test_benchmark_restores_context_on_failure(self):
    helper = self.load_helper()
    error = RuntimeError("benchmark failed")
    fake_device = SimpleNamespace(synchronize=lambda: None)

    def fail():
      self.assertEqual((OPENPILOT_HACKS.value, TC_OPT.value, TC_MIN_GLOBALS.value), (1, 2, 32))
      raise error

    with Context(DEV="AMD", OPENPILOT_HACKS=0, TC_OPT=7, TC_MIN_GLOBALS=11), \
         patch.object(type(Device), "default", property(lambda _: fake_device)):
      with self.assertRaises(RuntimeError) as caught:
        helper.benchmark(fail)
      self.assertIs(caught.exception, error)
      self.assertEqual((OPENPILOT_HACKS.value, TC_OPT.value, TC_MIN_GLOBALS.value), (0, 7, 11))

  def test_lazy_onnx_parser_preserves_metadata_without_gpu_probe(self):
    from openpilot.starpilot.models.compile import make_metadata_dict
    from openpilot.starpilot.models.tests.test_compile import stateful_onnx

    shapes = {"new_img": (2, 6, 2, 2), "state": (1, 2), "desire": (1, 2)}
    runner = SimpleNamespace(graph_inputs={name: SimpleNamespace(shape=shape) for name, shape in shapes.items()})
    get_device = type(Device).__getitem__

    def disk_only(device, name):
      self.assertEqual(name.split(":", 1)[0], "DISK")
      return get_device(device, name)

    with tempfile.TemporaryDirectory() as temporary, Context(DEV="CPU:LLVM"), \
         patch.object(type(Device), "__getitem__", disk_only):
      path = Path(temporary) / "metadata.onnx"
      path.write_bytes(stateful_onnx())
      metadata = make_metadata_dict(path, runner)
    self.assertEqual(metadata, {"model_checkpoint": None, "output_slices": {"fixture": slice(0, 2)},
                                "input_shapes": shapes, "output_shapes": {"outputs": (1, 2), "next_state": (1, 2)}})
