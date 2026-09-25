import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

_script_path = Path(__file__).resolve().parents[4] / "scripts" / "validate_driving_model.py"
_script_spec = importlib.util.spec_from_file_location("starpilot_test_validate_driving_model", _script_path)
assert _script_spec is not None and _script_spec.loader is not None
validator = importlib.util.module_from_spec(_script_spec)
_script_spec.loader.exec_module(validator)
from openpilot.system.camerad.cameras.nv12_info import get_nv12_info


def outputs(step=0):
  values = {name: np.full(validator.REQUIRED_SHAPES.get(name, (1, 2)), step / 100, dtype=np.float32)
            for name in validator.REQUIRED_KEYS}
  values["action"] = np.array([[step / 1000, step / 100]], dtype=np.float32)
  return values


class FixtureRunner:
  vision_input_names = ("img", "big_img")
  queue_device = warp_device = "CPU"

  def __init__(self, width, height, *_args):
    self.frame_buf_size = get_nv12_info(width, height)[3]
    self.step = 0
    self.frame_hashes = []
    self.inputs = []

  def warmup(self):
    self.step = 0

  def run(self, frames, transforms, inputs):
    self.frame_hashes.append(hash(frames["img"].tobytes()))
    self.inputs.append(inputs)
    self.step += 1
    return outputs(self.step)


def update_action(values, *_args):
  return SimpleNamespace(desiredCurvature=values["action"][0, 0], desiredAcceleration=values["action"][0, 1])


class TestDrivingValidation(unittest.TestCase):
  def test_changed_frames_recurrent_actions_shapes_and_timing(self):
    runner = FixtureRunner(8, 8)
    result = validator.validate_camera(Path("fixture.pkl"), "v15", (8, 8), 5, 42, False,
                                       runner_factory=lambda *_: runner, action_update=update_action,
                                       initial_action=SimpleNamespace(desiredCurvature=0., desiredAcceleration=0.))
    self.assertTrue(result["passed"])
    self.assertEqual(len(set(runner.frame_hashes)), 5)
    self.assertEqual(result["output_shapes"]["plan"], [1, 33, 15])
    self.assertIn("pose", result["changed_outputs"])
    self.assertGreater(result["inference_ms"]["p95"], 0)
    self.assertGreater(runner.inputs[1]["prev_action"][0], 0)
    self.assertEqual(runner.inputs[0]["desire_pulse"][1], 1)
    self.assertEqual(runner.inputs[1]["desire_pulse"].sum(), 0)

  def test_nv12_stride_padding_and_chroma_are_well_formed(self):
    width, height = 1344, 760
    stride, y_height, uv_height, size = get_nv12_info(width, height)
    frame = np.zeros(size, dtype=np.uint8)
    validator.fill_nv12(frame, width, height, 3, 42)
    y = frame[:stride * y_height].reshape(y_height, stride)
    uv = frame[stride * y_height:stride * (y_height + uv_height)].reshape(uv_height, stride)
    self.assertTrue(np.all((y[:height, :width] >= 16) & (y[:height, :width] <= 235)))
    self.assertTrue(np.all(y[height:] == 16))
    self.assertTrue(np.all(uv[:height // 2, :width:2] == 147))
    self.assertTrue(np.all(uv[:height // 2, 1:width:2] == 159))

  def test_missing_nonfinite_wrong_shape_and_frozen_outputs_fail(self):
    for field, value in (("plan", np.full((1, 33, 15), np.nan)), ("lead", np.zeros((1, 2, 6, 4)))):
      with self.subTest(field=field), self.assertRaises(ValueError):
        validator.check_outputs(outputs() | {field: value}, "v15")
    missing_action = outputs()
    del missing_action["action"]
    with self.assertRaisesRegex(ValueError, "Missing"):
      validator.check_outputs(missing_action, "v15")
    validator.check_outputs(missing_action, "v11")
    runner = FixtureRunner(8, 8)
    runner.run = Mock(return_value=outputs())
    with self.assertRaisesRegex(ValueError, "unchanged"):
      validator.validate_camera(Path("fixture.pkl"), "v15", (8, 8), 3, 42, False,
                                runner_factory=lambda *_: runner, action_update=update_action,
                                initial_action=SimpleNamespace(desiredCurvature=0., desiredAcceleration=0.))

  def test_parent_binds_artifact_sources_and_runs_both_camera_processes(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      artifact, source, report = root / "test.pkl", root / "driving_supercombo.onnx", root / "report.json"
      artifact.write_bytes(b"compiled")
      source.write_bytes(b"onnx")
      receipt = {"artifact_sha256": validator.sha256_file(artifact), "behavior_version": "v15",
                 "source_sha256": {source.name: validator.sha256_file(source)}}
      artifact.with_suffix(".build.json").write_text(json.dumps(receipt))
      def child(command, **_kwargs):
        camera = list(map(int, command[command.index("--camera") + 1].split("x")))
        Path(command[command.index("--report") + 1]).write_text(json.dumps({"passed": True, "camera": camera}))
        return SimpleNamespace(returncode=0)
      with patch.object(validator.subprocess, "run", side_effect=child) as child_run:
        self.assertEqual(validator.main([str(artifact), "--version", "v15", "--source-dir", str(root), "--report", str(report)]), 0)
        self.assertEqual(child_run.call_count, 2)
      result = json.loads(report.read_text())
      self.assertTrue(result["sources_verified"])
      self.assertEqual([camera["camera"] for camera in result["cameras"]], [list(camera) for camera in validator.CAMERAS])
      source.write_bytes(b"changed")
      with patch.object(validator.subprocess, "run") as child_run:
        self.assertEqual(validator.main([str(artifact), "--version", "v15", "--source-dir", str(root), "--report", str(report)]), 1)
        child_run.assert_not_called()
      self.assertFalse(json.loads(report.read_text())["passed"])


if __name__ == "__main__":
  unittest.main()
