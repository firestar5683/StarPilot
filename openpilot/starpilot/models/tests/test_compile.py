import importlib.util
import base64
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import unittest
from functools import partial
from unittest.mock import patch

import numpy as np

_script_path = Path(__file__).resolve().parents[4] / "scripts" / "model_compiler.py"
_script_spec = importlib.util.spec_from_file_location("starpilot_test_model_compiler", _script_path)
assert _script_spec is not None and _script_spec.loader is not None
model_compiler = importlib.util.module_from_spec(_script_spec)
_script_spec.loader.exec_module(model_compiler)


def varint(value):
  result = bytearray()
  while value > 127:
    result.append((value & 127) | 128)
    value >>= 7
  return bytes(result) + bytes([value])


def field(number, value):
  if isinstance(value, int):
    return varint(number << 3) + varint(value)
  if isinstance(value, str):
    value = value.encode()
  return varint((number << 3) | 2) + varint(len(value)) + value


def value_info(name, shape):
  dimensions = b"".join(field(1, field(1, dimension)) for dimension in shape)
  return field(1, name) + field(2, field(1, field(1, 1) + field(2, dimensions)))


def stateful_onnx():
  inputs = {"new_img": (2, 6, 2, 2), "state": (1, 2), "desire": (1, 2)}
  add = field(1, "state") + field(1, "desire") + field(2, "next_state") + field(4, "Add")
  identity = field(1, "next_state") + field(2, "outputs") + field(4, "Identity")
  graph = field(1, add) + field(1, identity) + field(2, "stateful-fixture")
  graph += b"".join(field(11, value_info(name, shape)) for name, shape in inputs.items())
  graph += field(12, value_info("outputs", (1, 2))) + field(12, value_info("next_state", (1, 2)))
  metadata = field(1, "output_slices") + field(2, base64.b64encode(pickle.dumps({"fixture": slice(0, 2)})))
  return field(1, 8) + field(7, graph) + field(8, field(2, 13)) + field(14, metadata)


class CompileTest(unittest.TestCase):
  def test_legacy_split_and_supercombo_history_survive_arena_round_trip(self):
    from tinygrad import Context, TinyJit
    from openpilot.starpilot.models.compile import (compile_jit, make_random_images, make_run_split_policy, make_run_supercombo,
                                                   make_split_input_queues, make_supercombo_input_queues, FAST_POLICY_INPUTS)
    image_shapes = {"input_imgs": (1, 12, 2, 2), "big_input_imgs": (1, 12, 2, 2)}
    policy_shapes = {"features_buffer": (1, 3, 2), "desire": (1, 2, 2), "traffic_convention": (1, 2)}
    def vision(inputs):
      values = [inputs[name].cast("float32").mean().reshape(1, 1) for name in image_shapes]
      return {"outputs": values[0].cat(values[1], dim=1)}
    def policy(inputs):
      return {"outputs": inputs["features_buffer"].sum(axis=1) + inputs["desire"].sum(axis=1) + inputs["traffic_convention"]}
    def supercombo(inputs):
      return {"outputs": policy(inputs)["outputs"] + vision(inputs)["outputs"]}
    with Context(DEV="CPU:LLVM", IMAGE=0, FLOAT16=0, JIT_BATCH_SIZE=0):
      for kind in ("split", "supercombo"):
        with self.subTest(kind=kind):
          if kind == "split":
            metadata = {"vision": {"input_shapes": image_shapes, "output_slices": {"hidden_state": slice(0, 2)}},
                        "policy": {"input_shapes": policy_shapes}}
            run = make_run_split_policy(vision, {"policy": policy}, metadata, ["policy"], 2)
            queues = partial(make_split_input_queues, image_shapes, policy_shapes, 2)
          else:
            metadata = {"model": {"input_shapes": image_shapes | policy_shapes}}
            run = make_run_supercombo(supercombo, metadata, 2)
            queues = partial(make_supercombo_input_queues, image_shapes | policy_shapes, 2)
          compile_jit(TinyJit(run, prune=True), partial(make_random_images, ["warped"], (2, 6, 2, 2)),
                      FAST_POLICY_INPUTS, queues, validation_runs=5)

  def test_source_selection_rejects_ambiguity_and_missing_split_component(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      (root / "driving_supercombo.onnx").write_bytes(b"one")
      self.assertEqual(set(model_compiler.source_files(root, "test")), {"supercombo"})
      (root / "supercombo.onnx").write_bytes(b"two")
      with self.assertRaisesRegex(ValueError, "Ambiguous"):
        model_compiler.source_files(root, "test")
    with self.assertRaisesRegex(ValueError, "Split input requires"):
      model_compiler.driving_compile_args({"vision": Path("vision.onnx")}, "split")

  def test_multi_policy_order_and_explicit_behavior_version(self):
    kind, arguments = model_compiler.driving_compile_args({key: Path(key + ".onnx") for key in ("vision", "on-policy", "off-policy")}, "split")
    self.assertEqual(kind, "vision_multi_policy")
    self.assertEqual(arguments, ["--vision-onnx", "vision.onnx", "--on-policy-onnx", "on-policy.onnx", "--off-policy-onnx", "off-policy.onnx"])
    args = model_compiler.parse_args(["--example", "--version", "v15"])
    self.assertEqual((args.model, args.version, args.frame_skip), ("example", "v15", None))

  def test_failed_compile_preserves_existing_output(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      (root / "driving_supercombo.onnx").write_bytes(stateful_onnx())
      output = root / "test_driving_tinygrad.pkl"
      output.write_bytes(b"previous artifact")
      with patch.object(model_compiler.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "compiler")):
        with self.assertRaises(subprocess.CalledProcessError):
          model_compiler.main(["--model", "test", "--version", "v16", "--input-dir", str(root), "--output-dir", str(root)])
      self.assertEqual(output.read_bytes(), b"previous artifact")

  def test_build_receipt_hashes_exact_sources_and_artifact(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      source = root / "driving_supercombo.onnx"
      source.write_bytes(stateful_onnx())
      def compile_stub(command, **kwargs):
        Path(command[command.index("--output") + 1]).write_bytes(b"compiled bytes")
      with patch.object(model_compiler.subprocess, "run", side_effect=compile_stub):
        model_compiler.main(["--model", "test", "--version", "v16", "--input-dir", str(root), "--output-dir", str(root)])
      output = root / "test_driving_tinygrad.pkl"
      receipt = json.loads(output.with_suffix(".build.json").read_text())
      self.assertEqual(receipt["source_sha256"], {source.name: model_compiler.sha256_file(source)})
      self.assertEqual(receipt["artifact_sha256"], model_compiler.sha256_file(output))
      self.assertEqual(receipt["artifact_abi"], "tinygrad_single_v1_arena")

  def test_stateful_onnx_compiles_warp_and_replays_arena_on_cpu(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      source, artifact = root / "fixture.onnx", root / "fixture.pkl"
      source.write_bytes(stateful_onnx())
      environment = dict(os.environ, DEV="CPU:LLVM", JIT_BATCH_SIZE="0", IMAGE="0", FLOAT16="0")
      environment.pop("WARP_DEV", None)
      command = [sys.executable, "-m", "openpilot.starpilot.models.compile", "--model-type", "supercombo",
                 "--model-size", "4x4", "--camera-resolutions", "8x8", "--behavior-version", "v16",
                 "--supercombo-onnx", str(source), "--output", str(artifact)]
      result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=90)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      with patch.dict(os.environ, environment):
        from tinygrad import Context
        from tinygrad_repo.examples.openpilot.helpers import load_pickle
        from openpilot.starpilot.models.compile import make_stateful_input_queues
        with Context(DEV="CPU:LLVM"):
          loaded = load_pickle(artifact, out_of_band=True)
          queues, host = make_stateful_input_queues(loaded["metadata"]["model"], loaded["execution_device"])
          from tinygrad import Tensor
          warped = Tensor(np.zeros((2, 6, 2, 2), dtype=np.uint8)).realize()
          host["desire"][:] = (1, 2)
          for step in range(1, 4):
            output, = loaded["run_policy"](warped=warped, **{name: queues[name] for name in loaded["policy_input_keys"]})
            np.testing.assert_array_equal(output.numpy(), [[step, step * 2]])
          self.assertEqual(loaded["compiler_revision"], "9d0446a4ba8a532c8b674fb6ad795af015cd9dcf")
          self.assertEqual(loaded["frame_skip"], 1)
          self.assertIn((8, 8), loaded)


if __name__ == "__main__":
  unittest.main()
