from pathlib import Path

import numpy as np

from starpilot.system.adj_spot_monitor_vision import VASMDaemon
from starpilot.system.adj_spot_monitor_vision_inference import MODEL_INPUT_SIZE, V_ASM_MODEL_PATH, VASMInference


class FakeParams:
  def __init__(self, config=None):
    self.config = config or {}

  def get(self, key):
    assert key == "VASMAnnotationConfig"
    return self.config


class FakeMemoryParams:
  def __init__(self):
    self.values = {}

  def put(self, key, value):
    self.values[key] = value


class FakeInference:
  def __init__(self):
    self.loaded = []
    self.reset_count = 0

  def load_config(self, config):
    self.loaded.append(config)

  def reset_state(self):
    self.reset_count += 1


def test_inference_geometry_supports_single_annotated_side():
  inference = VASMInference(Path("unused.onnx"))
  inference.load_config({
    "width": 200,
    "height": 100,
    "poly_left": [[10, 10], [80, 10], [80, 80], [10, 80]],
    "poly_right": [],
  })

  inference._prepare_geometry(100, 200)

  assert inference.configured_sides == ("left",)
  assert inference.bboxes["left"] is not None
  assert inference.bboxes["right"] is None


def test_model_loads_with_repo_inference_backend():
  inference = VASMInference(V_ASM_MODEL_PATH)

  assert inference.load(), inference.last_error
  inference.net.setInput(np.zeros((1, 3, MODEL_INPUT_SIZE, MODEL_INPUT_SIZE), dtype=np.float32))

  out = inference.net.forward()
  # Supports both tri-class (1, 3) master model and legacy binary (1, 2)
  assert out.shape in ((1, 3), (1, 2)), out.shape


def test_model_runs_from_nv12_camera_frame():
  inference = VASMInference(V_ASM_MODEL_PATH)
  assert inference.load(), inference.last_error
  inference.load_config({
    "width": MODEL_INPUT_SIZE,
    "height": MODEL_INPUT_SIZE,
    "poly_left": [[0, 0], [MODEL_INPUT_SIZE, 0], [MODEL_INPUT_SIZE, MODEL_INPUT_SIZE], [0, MODEL_INPUT_SIZE]],
    "poly_right": [],
  })
  nv12 = np.zeros((MODEL_INPUT_SIZE * 3 // 2, MODEL_INPUT_SIZE), dtype=np.uint8)

  assert inference.update(nv12, MODEL_INPUT_SIZE, MODEL_INPUT_SIZE, 0.5, 0.85, 0.05, "left") == (False, False)


def test_classifier_output_maps_class_1_confidence():
  inference = VASMInference(Path("unused.onnx"))
  inference.load_config({
    "width": 100, "height": 100,
    "poly_left": [[0, 0], [100, 0], [100, 100], [0, 100]],
    "poly_right": [],
  })
  inference._prepare_geometry(100, 100)

  class FakeNet:
    def setInput(self, blob):
      pass

    def forward(self):
      # Tri-class output: [0_nocar, 1_car, 2_distant_or_rear]
      return np.array([[0.05, 0.95, 0.00]], dtype=np.float32)

  inference.net = FakeNet()
  inference._valid = True
  left_active, right_active = inference.update(
    np.zeros((150, 100), dtype=np.uint8), 100, 100, 0.5, 0.85, 0.05, "left"
  )
  assert inference.left_confidence == np.float32(0.95)
  assert left_active and not right_active


def test_annotation_changes_reload_without_process_restart():
  first = {"width": 200, "height": 100, "poly_left": [[1, 1], [10, 1], [10, 10]], "poly_right": []}
  second = {"width": 200, "height": 100, "poly_left": [], "poly_right": [[20, 1], [30, 1], [30, 10]]}
  daemon = VASMDaemon.__new__(VASMDaemon)
  daemon.params = FakeParams(first)
  daemon.inference = FakeInference()
  daemon._annotation_config = object()
  daemon._annotation_loaded = False

  assert daemon._load_annotation_config()
  assert not daemon._load_annotation_config()
  daemon.params.config = second
  assert daemon._load_annotation_config()

  assert daemon.inference.loaded == [first, second]


def test_publish_writes_freshness_and_maps_camera_sides_to_ui_sides():
  daemon = VASMDaemon.__new__(VASMDaemon)
  daemon.params_memory = FakeMemoryParams()
  daemon._last_pub_left = False
  daemon._last_pub_right = False
  daemon._last_pub_left_conf = -1.0
  daemon._last_pub_right_conf = -1.0
  daemon._last_update_at = 0.0

  daemon._publish(True, False, 0.9, 0.1, 123, updated_at=50.0)

  assert daemon.params_memory.values["VASMLastUpdateMonoTime"] == "50.0"
  assert daemon.params_memory.values["VASMLeftActive"] == "0"
  assert daemon.params_memory.values["VASMRightActive"] == "1"