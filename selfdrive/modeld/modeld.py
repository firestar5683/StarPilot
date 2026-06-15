#!/usr/bin/env python3
import os
from openpilot.system.hardware import TICI
os.environ['DEV'] = 'QCOM' if TICI else 'LLVM'
from tinygrad.tensor import Tensor
from tinygrad.dtype import dtypes
import time
import pickle
import numpy as np
import cereal.messaging as messaging
from cereal import car, log
from pathlib import Path
from setproctitle import setproctitle
from cereal.messaging import PubMaster, SubMaster
from msgq.visionipc import VisionIpcClient, VisionStreamType, VisionBuf
from openpilot.common.swaglog import cloudlog
from openpilot.common.params import Params
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import config_realtime_process, DT_MDL
from openpilot.common.transformations.camera import DEVICE_CAMERAS
from openpilot.common.transformations.model import get_warp_matrix
from openpilot.system import sentry
from opendbc.car.car_helpers import get_demo_car_params
from openpilot.selfdrive.controls.lib.desire_helper import DesireHelper
from openpilot.selfdrive.controls.lib.drive_helpers import get_accel_from_plan_tomb_raider, smooth_value
from openpilot.selfdrive.modeld.camera_offset import CameraOffset, DEFAULT_CAMERA_HEIGHT
from openpilot.selfdrive.modeld.parse_model_outputs import Parser
from openpilot.selfdrive.modeld.fill_model_msg import fill_model_msg, fill_pose_msg, PublishState, get_curvature_from_output
from openpilot.selfdrive.modeld.constants import ModelConstants, Plan
from openpilot.selfdrive.modeld.models.commonmodel_pyx import DrivingModelFrame, CLContext
from openpilot.selfdrive.modeld.runners.tinygrad_helpers import qcom_tensor_from_opencl_address
from openpilot.starpilot.common.model_versions import (
  is_tinygrad_model_version,
  uses_combined_driving_artifacts,
  uses_split_off_policy_artifacts,
)
from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles, MODELS_PATH, params_memory


PROCESS_NAME = "selfdrive.modeld.modeld"
SEND_RAW_PRED = os.getenv('SEND_RAW_PRED')

BUILTIN_MODEL_KEY = "sc2"
BUILTIN_MODEL_ALIASES = {BUILTIN_MODEL_KEY, "sc"}


LAT_SMOOTH_SECONDS = 0.0
LONG_SMOOTH_SECONDS = 0.3
MIN_LAT_CONTROL_SPEED = 0.3


def _get_param_str(params: Params, key: str, default: str = "") -> str:
  try:
    val = params.get(key)
  except Exception:
    return default
  if val is None:
    return default
  if isinstance(val, bytes):
    try:
      return val.decode("utf-8")
    except Exception:
      return default
  if isinstance(val, (dict, list)):
    return default
  return str(val)


def _get_default_param_str(params: Params, key: str) -> str:
  try:
    val = params.get_default_value(key)
  except Exception:
    return ""
  if val is None:
    return ""
  if isinstance(val, bytes):
    try:
      return val.decode("utf-8")
    except Exception:
      return ""
  return str(val)


def _resolve_mirrored_param(params: Params, primary_key: str, secondary_key: str) -> str:
  primary_val = _get_param_str(params, primary_key).strip()
  secondary_val = _get_param_str(params, secondary_key).strip()
  if primary_val == secondary_val:
    return secondary_val or primary_val

  primary_default = _get_default_param_str(params, primary_key).strip()
  secondary_default = _get_default_param_str(params, secondary_key).strip()
  primary_non_default = bool(primary_val) and primary_val != primary_default
  secondary_non_default = bool(secondary_val) and secondary_val != secondary_default

  if secondary_non_default:
    return secondary_val
  if primary_non_default:
    return primary_val
  return secondary_val or primary_val


def _canonical_model_id(model_id: str) -> str:
  key = (model_id or "").strip().lower()
  return BUILTIN_MODEL_KEY if key in BUILTIN_MODEL_ALIASES else key


def get_action_from_model(model_output: dict[str, np.ndarray], prev_action: log.ModelDataV2.Action,
                          lat_action_t: float, long_action_t: float, v_ego: float, mlsim: bool,
                          is_v9: bool, is_v14: bool, is_v15: bool, starpilot_toggles) -> log.ModelDataV2.Action:
    if is_v14 or is_v15:
      desired_curv_unscaled, desired_accel = model_output['action'][0]
      if is_v15:
        desired_curvature = float(desired_curv_unscaled) / max(1.0, v_ego) ** 2
      else:
        desired_curvature = float(desired_curv_unscaled) / 100.0
      should_stop = (v_ego < 0.3 and desired_accel < 0.1)

      desired_accel = smooth_value(float(desired_accel), prev_action.desiredAcceleration, LONG_SMOOTH_SECONDS)
      if v_ego > MIN_LAT_CONTROL_SPEED:
        desired_curvature = smooth_value(desired_curvature, prev_action.desiredCurvature, LAT_SMOOTH_SECONDS)
      else:
        desired_curvature = prev_action.desiredCurvature

      return log.ModelDataV2.Action(desiredCurvature=float(desired_curvature),
                                    desiredAcceleration=float(desired_accel),
                                    shouldStop=bool(should_stop))

    plan = model_output['plan'][0]
    if 'planplus' in model_output:
      recovery_power = getattr(starpilot_toggles, "recovery_power", 1.0)
      plan = plan + recovery_power * model_output['planplus'][0]
      cloudlog.error(f"planplus applied: shape {model_output['planplus'].shape}, RECOVERY_POWER {recovery_power}")
    v_ego_stopping = getattr(starpilot_toggles, "vEgoStopping", 0.3)
    desired_accel, should_stop = get_accel_from_plan_tomb_raider(plan[:,Plan.VELOCITY][:,0],
                                                                 plan[:,Plan.ACCELERATION][:,0],
                                                                 ModelConstants.T_IDXS,
                                                                 action_t=long_action_t,
                                                                 vEgoStopping=v_ego_stopping)
    desired_accel = smooth_value(desired_accel, prev_action.desiredAcceleration, LONG_SMOOTH_SECONDS)

    if is_v9:
      # V9: use desired_curvature if present; otherwise do NOT fall back to plan
      if 'desired_curvature' in model_output:
        desired_curvature = float(model_output['desired_curvature'][0, 0])
      else:
        desired_curvature = prev_action.desiredCurvature
    else:
      desired_curvature = get_curvature_from_output(model_output, plan, v_ego, lat_action_t, mlsim=mlsim)
    if v_ego > MIN_LAT_CONTROL_SPEED:
      desired_curvature = smooth_value(desired_curvature, prev_action.desiredCurvature, LAT_SMOOTH_SECONDS)
    else:
      desired_curvature = prev_action.desiredCurvature

    return log.ModelDataV2.Action(desiredCurvature=float(desired_curvature),
                                  desiredAcceleration=float(desired_accel),
                                  shouldStop=bool(should_stop))

class FrameMeta:
  frame_id: int = 0
  timestamp_sof: int = 0
  timestamp_eof: int = 0

  def __init__(self, vipc=None):
    if vipc is not None:
      self.frame_id, self.timestamp_sof, self.timestamp_eof = vipc.frame_id, vipc.timestamp_sof, vipc.timestamp_eof

class ModelState:
  frames: dict[str, DrivingModelFrame]
  inputs: dict[str, np.ndarray]
  output: np.ndarray
  prev_desire: np.ndarray  # for tracking the rising edge of the pulse

  def _build_policy_inputs(self, input_shapes: dict[str, tuple[int, ...]]) -> tuple[dict[str, np.ndarray], str | None]:
    numpy_inputs: dict[str, np.ndarray] = {}

    # Always-supported inputs (if model expects them)
    desire_key_init = next((k for k in input_shapes if k.startswith('desire')), None)
    if desire_key_init:
      numpy_inputs[desire_key_init] = np.zeros((1, ModelConstants.INPUT_HISTORY_BUFFER_LEN, ModelConstants.DESIRE_LEN), dtype=np.float32)
    if 'traffic_convention' in input_shapes:
      numpy_inputs['traffic_convention'] = np.zeros((1, ModelConstants.TRAFFIC_CONVENTION_LEN), dtype=np.float32)
    if 'features_buffer' in input_shapes:
      numpy_inputs['features_buffer'] = np.zeros((1, ModelConstants.INPUT_HISTORY_BUFFER_LEN,  ModelConstants.FEATURE_LEN), dtype=np.float32)
    if 'action_t' in input_shapes:
      numpy_inputs['action_t'] = np.zeros(input_shapes['action_t'], dtype=np.float32)
    if 'prev_action' in input_shapes:
      numpy_inputs['prev_action'] = np.zeros(input_shapes['prev_action'], dtype=np.float32)

    # Optional inputs for non-v11 (and some v10/v9 variants)
    # Lateral control params
    if 'lateral_control_params' in input_shapes:
      numpy_inputs['lateral_control_params'] = np.zeros((1, ModelConstants.LATERAL_CONTROL_PARAMS_LEN), dtype=np.float32)

    # Previous desired curvature: handle both singular and plural key names across model versions
    prev_desired_curv_key = None
    if 'prev_desired_curv' in input_shapes:
      prev_desired_curv_key = 'prev_desired_curv'
      numpy_inputs['prev_desired_curv'] = np.zeros((1, ModelConstants.INPUT_HISTORY_BUFFER_LEN, ModelConstants.PREV_DESIRED_CURV_LEN), dtype=np.float32)
    elif 'prev_desired_curvs' in input_shapes:
      prev_desired_curv_key = 'prev_desired_curvs'
      numpy_inputs['prev_desired_curvs'] = np.zeros((1, ModelConstants.INPUT_HISTORY_BUFFER_LEN, ModelConstants.PREV_DESIRED_CURV_LEN), dtype=np.float32)

    return numpy_inputs, prev_desired_curv_key

  def __init__(self, context: CLContext):
    # Dynamically build paths based on current model ID
    params = Params()
    model_id_raw = _resolve_mirrored_param(params, "Model", "DrivingModel") or BUILTIN_MODEL_KEY
    model_id = _canonical_model_id(model_id_raw)

    model_version = _resolve_mirrored_param(params, "ModelVersion", "DrivingModelVersion")

    model_dir = MODELS_PATH
    use_builtin_model = model_id == BUILTIN_MODEL_KEY
    model_download_id = model_id
    if use_builtin_model and (_canonical_model_id(_get_param_str(params, "Model")) != model_id or
                              _canonical_model_id(_get_param_str(params, "DrivingModel")) != model_id):
      params.put("Model", model_id)
      params.put("DrivingModel", model_id)

    if use_builtin_model and not model_version:
      model_version = "v11"
      params.put("ModelVersion", model_version)
      params.put("DrivingModelVersion", model_version)
    # Use built-in files for defaults when a custom model isn't selected.
    if use_builtin_model:
        models_dir = Path(__file__).parent / "models"
        VISION_PKL_PATH = models_dir / "driving_vision_tinygrad.pkl"
        POLICY_PKL_PATH = models_dir / "driving_policy_tinygrad.pkl"
        OFF_POLICY_PKL_PATH = models_dir / "driving_off_policy_tinygrad.pkl"
        VISION_METADATA_PATH = models_dir / "driving_vision_metadata.pkl"
        POLICY_METADATA_PATH = models_dir / "driving_policy_metadata.pkl"
        OFF_POLICY_METADATA_PATH = models_dir / "driving_off_policy_metadata.pkl"
    else:
        VISION_PKL_PATH = model_dir / f"{model_id}_driving_vision_tinygrad.pkl"
        POLICY_PKL_PATH = model_dir / f"{model_id}_driving_policy_tinygrad.pkl"
        OFF_POLICY_PKL_PATH = model_dir / f"{model_id}_driving_off_policy_tinygrad.pkl"
        VISION_METADATA_PATH = model_dir / f"{model_id}_driving_vision_metadata.pkl"
        POLICY_METADATA_PATH = model_dir / f"{model_id}_driving_policy_metadata.pkl"
        OFF_POLICY_METADATA_PATH = model_dir / f"{model_id}_driving_off_policy_metadata.pkl"

    def ensure_artifact(path: Path, suffix: str | None = None, optional: bool = False) -> Path | None:
      if path.is_file():
        return path

      if use_builtin_model:
        if optional:
          cloudlog.warning(f"Optional builtin model artifact missing: {path}")
          return None
        raise FileNotFoundError(
          f"Missing builtin model artifact: {path}. "
          "Rebuild model artifacts locally (./build or scons target) and deploy them."
        )

      cloudlog.error(f"Missing model artifact {path}, downloading {model_download_id}...")
      from openpilot.starpilot.assets.model_manager import ModelManager
      ModelManager(params, params_memory).download_model(model_download_id)

      if path.is_file():
        return path

      if optional:
        cloudlog.warning(f"Optional model artifact missing: {path}")
        return None

      raise FileNotFoundError(path)

    # If ModelVersion is not set or not available, try to determine it from available model data
    if not model_version:
      cloudlog.warning(f"ModelVersion not available for model {model_id}, attempting to determine from model data")
      try:
        # Try to get version from the model versions JSON file
        versions_file = model_dir / ".model_versions.json"
        if versions_file.is_file():
          import json
          with open(versions_file, "r") as f:
            version_map = json.load(f)
          version_lookup_keys = [model_id]
          if model_id and not model_id.endswith("2"):
            version_lookup_keys.append(f"{model_id}2")
          for key in version_lookup_keys:
            if key in version_map:
              model_version = version_map[key]
              cloudlog.warning(f"Determined model version from JSON: {model_version} ({key})")
              params.put("ModelVersion", model_version)
              params.put("DrivingModelVersion", model_version)
              break
        else:
          cloudlog.error("Model versions JSON file not found, defaulting to v8")
          model_version = "v8"
      except Exception as e:
        cloudlog.error(f"Failed to determine model version: {e}, defaulting to v8")
        model_version = "v8"

    VISION_METADATA_PATH = ensure_artifact(VISION_METADATA_PATH, "driving_vision_metadata.pkl")
    with open(VISION_METADATA_PATH, 'rb') as f:
      vision_metadata = pickle.load(f)
    self.vision_input_shapes =  vision_metadata['input_shapes']
    self.vision_input_names = list(self.vision_input_shapes.keys())
    self.vision_output_slices = vision_metadata['output_slices']
    vision_output_size = vision_metadata['output_shapes']['outputs'][1]

    POLICY_METADATA_PATH = ensure_artifact(POLICY_METADATA_PATH, "driving_policy_metadata.pkl")
    with open(POLICY_METADATA_PATH, 'rb') as f:
      policy_metadata = pickle.load(f)
    self.policy_input_shapes =  policy_metadata['input_shapes']
    self.policy_output_slices = policy_metadata['output_slices']
    policy_output_size = policy_metadata['output_shapes']['outputs'][1]
    # Add policy_generation attribute after loading policy_metadata
    self.policy_generation = model_version or "v8"
    self.is_v11 = (self.policy_generation == "v11")
    self.is_v10 = (self.policy_generation == "v10")
    self.is_v12 = (self.policy_generation == "v12")
    self.is_v13 = (self.policy_generation == "v13")
    self.is_v14 = (self.policy_generation == "v14")
    self.is_v15 = (self.policy_generation == "v15")
    self.is_v9 = (self.policy_generation == "v9")
    self.mlsim = is_tinygrad_model_version(self.policy_generation)
    self.policy_has_plan = 'plan' in self.policy_output_slices

    self.frames = {name: DrivingModelFrame(context, ModelConstants.TEMPORAL_SKIP) for name in self.vision_input_names}
    self.prev_desire = np.zeros(ModelConstants.DESIRE_LEN, dtype=np.float32)

    self.full_features_buffer = np.zeros((1, ModelConstants.FULL_HISTORY_BUFFER_LEN,  ModelConstants.FEATURE_LEN), dtype=np.float32)
    self.full_desire = np.zeros((1, ModelConstants.FULL_HISTORY_BUFFER_LEN, ModelConstants.DESIRE_LEN), dtype=np.float32)
    self.temporal_idxs = slice(-1-(ModelConstants.TEMPORAL_SKIP*(ModelConstants.INPUT_HISTORY_BUFFER_LEN-1)), None, ModelConstants.TEMPORAL_SKIP)


    # policy inputs (built dynamically to support all generations)
    self.numpy_inputs, self.prev_desired_curv_key = self._build_policy_inputs(self.policy_input_shapes)

    # Off-policy model (optional)
    self.off_policy_enabled = False
    self.off_policy_input_shapes: dict[str, tuple[int, ...]] = {}
    self.off_policy_output_slices: dict[str, slice] = {}
    self.off_policy_numpy_inputs: dict[str, np.ndarray] = {}
    self.off_policy_prev_desired_curv_key: str | None = None
    self.off_policy_desire_key: str | None = None
    self.off_policy_inputs: dict[str, Tensor] | None = None
    self.off_policy_output: np.ndarray | None = None

    off_policy_metadata = None
    if uses_split_off_policy_artifacts(self.policy_generation) or OFF_POLICY_METADATA_PATH.is_file() or OFF_POLICY_PKL_PATH.is_file():
      resolved_off_policy_meta = ensure_artifact(OFF_POLICY_METADATA_PATH, "driving_off_policy_metadata.pkl", optional=True)
      if resolved_off_policy_meta is not None:
        with open(resolved_off_policy_meta, 'rb') as f:
          off_policy_metadata = pickle.load(f)

    if off_policy_metadata is not None:
      self.off_policy_input_shapes = off_policy_metadata['input_shapes']
      self.off_policy_output_slices = off_policy_metadata['output_slices']
      self.off_policy_has_plan = 'plan' in self.off_policy_output_slices
      off_policy_output_size = off_policy_metadata['output_shapes']['outputs'][1]
      self.off_policy_numpy_inputs, self.off_policy_prev_desired_curv_key = self._build_policy_inputs(self.off_policy_input_shapes)
      self.off_policy_desire_key = next((k for k in self.off_policy_numpy_inputs if k.startswith('desire')), None)
      self.off_policy_inputs = {k: Tensor(v, device='NPY').realize() for k, v in self.off_policy_numpy_inputs.items()}
      self.off_policy_output = np.zeros(off_policy_output_size, dtype=np.float32)
      resolved_off_policy_pkl = ensure_artifact(OFF_POLICY_PKL_PATH, "driving_off_policy_tinygrad.pkl", optional=True)
      if resolved_off_policy_pkl is not None:
        with open(resolved_off_policy_pkl, "rb") as f:
          self.off_policy_run = pickle.load(f)
        self.off_policy_enabled = True
    else:
      self.off_policy_has_plan = False

    # Optional temporal buffer for previous desired curvature (allocate only if any model expects it)
    if self.prev_desired_curv_key is not None or self.off_policy_prev_desired_curv_key is not None:
      self.full_prev_desired_curv = np.zeros((1, ModelConstants.FULL_HISTORY_BUFFER_LEN, ModelConstants.PREV_DESIRED_CURV_LEN), dtype=np.float32)


    # img buffers are managed in openCL transform code
    self.vision_inputs: dict[str, Tensor] = {}
    self.vision_output = np.zeros(vision_output_size, dtype=np.float32)
    self.policy_inputs = {k: Tensor(v, device='NPY').realize() for k,v in self.numpy_inputs.items()}
    self.policy_output = np.zeros(policy_output_size, dtype=np.float32)
    self.parser = Parser()
    self.off_policy_parser = Parser(ignore_missing=True)

    VISION_PKL_PATH = ensure_artifact(VISION_PKL_PATH, "driving_vision_tinygrad.pkl")
    with open(VISION_PKL_PATH, "rb") as f:
      self.vision_run = pickle.load(f)

    POLICY_PKL_PATH = ensure_artifact(POLICY_PKL_PATH, "driving_policy_tinygrad.pkl")
    with open(POLICY_PKL_PATH, "rb") as f:
      self.policy_run = pickle.load(f)

  @property
  def desire_key(self) -> str:
    return next(key for key in self.numpy_inputs if key.startswith('desire'))

  def slice_outputs(self, model_outputs: np.ndarray, output_slices: dict[str, slice]) -> dict[str, np.ndarray]:
    parsed_model_outputs = {k: model_outputs[np.newaxis, v] for k,v in output_slices.items()}
    return parsed_model_outputs

  def run(self, bufs: dict[str, VisionBuf], transforms: dict[str, np.ndarray],
                inputs: dict[str, np.ndarray], prepare_only: bool) -> dict[str, np.ndarray] | None:
    # Model decides when action is completed, so desire input is just a pulse triggered on rising edge
    inputs[self.desire_key][0] = 0
    new_desire = np.where(inputs[self.desire_key] - self.prev_desire > .99, inputs[self.desire_key], 0)
    self.prev_desire[:] = inputs[self.desire_key]

    self.full_desire[0,:-1] = self.full_desire[0,1:]
    self.full_desire[0,-1] = new_desire
    self.numpy_inputs[self.desire_key][:] = self.full_desire.reshape((1,ModelConstants.INPUT_HISTORY_BUFFER_LEN,ModelConstants.TEMPORAL_SKIP,-1)).max(axis=2)
    if self.off_policy_enabled and self.off_policy_desire_key is not None:
      self.off_policy_numpy_inputs[self.off_policy_desire_key][:] = self.numpy_inputs[self.desire_key]

    if 'traffic_convention' in self.numpy_inputs:
      self.numpy_inputs['traffic_convention'][:] = inputs['traffic_convention']
    if self.off_policy_enabled and 'traffic_convention' in self.off_policy_numpy_inputs:
      self.off_policy_numpy_inputs['traffic_convention'][:] = inputs['traffic_convention']

    if 'action_t' in self.numpy_inputs:
      self.numpy_inputs['action_t'][:] = inputs['action_t']
    if self.off_policy_enabled and 'action_t' in self.off_policy_numpy_inputs:
      self.off_policy_numpy_inputs['action_t'][:] = inputs['action_t']

    if 'prev_action' in self.numpy_inputs:
      self.numpy_inputs['prev_action'][:] = inputs['prev_action']
    if self.off_policy_enabled and 'prev_action' in self.off_policy_numpy_inputs:
      self.off_policy_numpy_inputs['prev_action'][:] = inputs['prev_action']

    if 'lateral_control_params' in self.numpy_inputs:
      self.numpy_inputs['lateral_control_params'][:] = inputs['lateral_control_params']
    if self.off_policy_enabled and 'lateral_control_params' in self.off_policy_numpy_inputs:
      self.off_policy_numpy_inputs['lateral_control_params'][:] = inputs['lateral_control_params']

    if prepare_only:
      return None

    imgs_cl = {name: self.frames[name].prepare(bufs[name], transforms[name].flatten()) for name in self.vision_input_names}

    if TICI:
      # The imgs tensors are backed by opencl memory, only need init once
      for key in imgs_cl:
        if key not in self.vision_inputs:
          self.vision_inputs[key] = qcom_tensor_from_opencl_address(imgs_cl[key].mem_address, self.vision_input_shapes[key], dtype=dtypes.uint8)
    else:
      for key in imgs_cl:
        frame_input = self.frames[key].buffer_from_cl(imgs_cl[key]).reshape(self.vision_input_shapes[key])
        self.vision_inputs[key] = Tensor(frame_input, dtype=dtypes.uint8).realize()

    self.vision_output = self.vision_run(**self.vision_inputs).contiguous().realize().uop.base.buffer.numpy()
    vision_outputs_dict = self.parser.parse_vision_outputs(self.slice_outputs(self.vision_output, self.vision_output_slices))

    self.full_features_buffer[0,:-1] = self.full_features_buffer[0,1:]
    self.full_features_buffer[0,-1] = vision_outputs_dict['hidden_state'][0, :]
    if 'features_buffer' in self.numpy_inputs:
      self.numpy_inputs['features_buffer'][:] = self.full_features_buffer[0, self.temporal_idxs]
    if self.off_policy_enabled and 'features_buffer' in self.off_policy_numpy_inputs:
      self.off_policy_numpy_inputs['features_buffer'][:] = self.full_features_buffer[0, self.temporal_idxs]

    self.policy_output = self.policy_run(**self.policy_inputs).contiguous().realize().uop.base.buffer.numpy()
    policy_outputs_dict = self.parser.parse_policy_outputs(self.slice_outputs(self.policy_output, self.policy_output_slices))

    # TODO model only uses last value now
    if hasattr(self, 'full_prev_desired_curv') and 'desired_curvature' in policy_outputs_dict:
      self.full_prev_desired_curv[0,:-1] = self.full_prev_desired_curv[0,1:]
      self.full_prev_desired_curv[0,-1,:] = policy_outputs_dict['desired_curvature'][0, :]

      if self.prev_desired_curv_key is not None:
        # Tinygrad-era policy models expect zeros for prev_desired_curv(s); older ones use history.
        if is_tinygrad_model_version(self.policy_generation):
          self.numpy_inputs[self.prev_desired_curv_key][:] = 0 * self.full_prev_desired_curv[0, self.temporal_idxs]
        else:
          self.numpy_inputs[self.prev_desired_curv_key][:] = self.full_prev_desired_curv[0, self.temporal_idxs]

      if self.off_policy_enabled and self.off_policy_prev_desired_curv_key is not None:
        if self.is_v9 or uses_split_off_policy_artifacts(self.policy_generation) or uses_combined_driving_artifacts(self.policy_generation):
          self.off_policy_numpy_inputs[self.off_policy_prev_desired_curv_key][:] = 0 * self.full_prev_desired_curv[0, self.temporal_idxs]
        else:
          self.off_policy_numpy_inputs[self.off_policy_prev_desired_curv_key][:] = self.full_prev_desired_curv[0, self.temporal_idxs]

    combined_outputs_dict = {**vision_outputs_dict}
    if self.off_policy_enabled:
      self.off_policy_output = self.off_policy_run(**self.off_policy_inputs).contiguous().realize().uop.base.buffer.numpy()
      off_policy_outputs_dict = self.off_policy_parser.parse_policy_outputs(
        self.slice_outputs(self.off_policy_output, self.off_policy_output_slices)
      )
      if self.policy_has_plan:
        off_policy_outputs_dict.pop('plan', None)
      combined_outputs_dict = {**combined_outputs_dict, **off_policy_outputs_dict, **policy_outputs_dict}
    else:
      combined_outputs_dict = {**combined_outputs_dict, **policy_outputs_dict}
    if SEND_RAW_PRED:
      raw_pred = [self.vision_output.copy(), self.policy_output.copy()]
      if self.off_policy_enabled and self.off_policy_output is not None:
        raw_pred.append(self.off_policy_output.copy())
      combined_outputs_dict['raw_pred'] = np.concatenate(raw_pred)

    return combined_outputs_dict


def main(demo=False):
  params = Params()
  selected_version = _resolve_mirrored_param(params, "ModelVersion", "DrivingModelVersion")
  if uses_combined_driving_artifacts(selected_version):
    from openpilot.selfdrive.modeld.modeld_v16 import main as combined_main

    return combined_main(demo=demo)

  cloudlog.warning("modeld init")

  sentry.set_tag("daemon", PROCESS_NAME)
  cloudlog.bind(daemon=PROCESS_NAME)
  setproctitle(PROCESS_NAME)
  config_realtime_process(7, 54)

  cloudlog.warning("setting up CL context")
  cl_context = CLContext()
  cloudlog.warning("CL context ready; loading model")
  model = ModelState(cl_context)
  cloudlog.warning("models loaded, modeld starting")

  # visionipc clients
  while True:
    available_streams = VisionIpcClient.available_streams("camerad", block=False)
    if available_streams:
      use_extra_client = VisionStreamType.VISION_STREAM_WIDE_ROAD in available_streams and VisionStreamType.VISION_STREAM_ROAD in available_streams
      main_wide_camera = VisionStreamType.VISION_STREAM_ROAD not in available_streams
      break
    time.sleep(.1)

  vipc_client_main_stream = VisionStreamType.VISION_STREAM_WIDE_ROAD if main_wide_camera else VisionStreamType.VISION_STREAM_ROAD
  vipc_client_main = VisionIpcClient("camerad", vipc_client_main_stream, True, cl_context)
  vipc_client_extra = VisionIpcClient("camerad", VisionStreamType.VISION_STREAM_WIDE_ROAD, False, cl_context)
  cloudlog.warning(f"vision stream set up, main_wide_camera: {main_wide_camera}, use_extra_client: {use_extra_client}")

  while not vipc_client_main.connect(False):
    time.sleep(0.1)
  while use_extra_client and not vipc_client_extra.connect(False):
    time.sleep(0.1)

  cloudlog.warning(f"connected main cam with buffer size: {vipc_client_main.buffer_len} ({vipc_client_main.width} x {vipc_client_main.height})")
  if use_extra_client:
    cloudlog.warning(f"connected extra cam with buffer size: {vipc_client_extra.buffer_len} ({vipc_client_extra.width} x {vipc_client_extra.height})")

  # messaging
  pm = PubMaster(["modelV2", "drivingModelData", "cameraOdometry", "starpilotModelV2"])
  sm = SubMaster(["deviceState", "carState", "roadCameraState", "liveCalibration", "driverMonitoringState", "carControl", "liveDelay", "starpilotPlan"])

  publish_state = PublishState()
  # setup filter to track dropped frames
  frame_dropped_filter = FirstOrderFilter(0., 10., 1. / ModelConstants.MODEL_FREQ)
  frame_id = 0
  last_vipc_frame_id = 0
  run_count = 0

  model_transform_main = np.zeros((3, 3), dtype=np.float32)
  model_transform_extra = np.zeros((3, 3), dtype=np.float32)
  live_calib_seen = False
  buf_main, buf_extra = None, None
  meta_main = FrameMeta()
  meta_extra = FrameMeta()
  camera_offset = CameraOffset()
  camera_offset.set_target(params.get_float("CameraOffset", return_default=True))


  if demo:
    CP = get_demo_car_params()
  else:
    CP = messaging.log_from_bytes(params.get("CarParams", block=True), car.CarParams)
  cloudlog.info("modeld got CarParams: %s", CP.brand)

  # TODO this needs more thought, use .2s extra for now to estimate other delays
  # TODO Move smooth seconds to action function
  long_delay = CP.longitudinalActuatorDelay + LONG_SMOOTH_SECONDS
  prev_action = log.ModelDataV2.Action()

  DH = DesireHelper()

  starpilot_toggles = get_starpilot_toggles(sm)

  while True:
    # Keep receiving frames until we are at least 1 frame ahead of previous extra frame
    while meta_main.timestamp_sof < meta_extra.timestamp_sof + 25000000:
      buf_main = vipc_client_main.recv()
      meta_main = FrameMeta(vipc_client_main)
      if buf_main is None:
        break

    if buf_main is None:
      cloudlog.debug("vipc_client_main no frame")
      continue

    if use_extra_client:
      # Keep receiving extra frames until frame id matches main camera
      while True:
        buf_extra = vipc_client_extra.recv()
        meta_extra = FrameMeta(vipc_client_extra)
        if buf_extra is None or meta_main.timestamp_sof < meta_extra.timestamp_sof + 25000000:
          break

      if buf_extra is None:
        cloudlog.debug("vipc_client_extra no frame")
        continue

      if abs(meta_main.timestamp_sof - meta_extra.timestamp_sof) > 10000000:
        cloudlog.error(f"frames out of sync! main: {meta_main.frame_id} ({meta_main.timestamp_sof / 1e9:.5f}),\
                         extra: {meta_extra.frame_id} ({meta_extra.timestamp_sof / 1e9:.5f})")

    else:
      # Use single camera
      buf_extra = buf_main
      meta_extra = meta_main

    sm.update(0)
    desire = DH.desire
    is_rhd = sm["driverMonitoringState"].isRHD
    frame_id = sm["roadCameraState"].frameId
    v_ego = max(sm["carState"].vEgo, 0.)
    lat_delay = sm["liveDelay"].lateralDelay + LAT_SMOOTH_SECONDS
    lateral_control_params = np.array([v_ego, lat_delay], dtype=np.float32)
    if sm.frame % 60 == 0:
      camera_offset.set_target(params.get_float("CameraOffset", return_default=True))

    if sm.updated["liveCalibration"] and sm.seen['roadCameraState'] and sm.seen['deviceState']:
      device_from_calib_euler = np.array(sm["liveCalibration"].rpyCalib, dtype=np.float32)
      dc = DEVICE_CAMERAS[(str(sm['deviceState'].deviceType), str(sm['roadCameraState'].sensor))]
      model_transform_main = get_warp_matrix(device_from_calib_euler, dc.ecam.intrinsics if main_wide_camera else dc.fcam.intrinsics, False).astype(np.float32)
      model_transform_extra = get_warp_matrix(device_from_calib_euler, dc.ecam.intrinsics, True).astype(np.float32)
      camera_height = sm["liveCalibration"].height[0] if sm["liveCalibration"].height else DEFAULT_CAMERA_HEIGHT
      model_transform_main, model_transform_extra = camera_offset.update(
        model_transform_main,
        model_transform_extra,
        str(sm["deviceState"].deviceType),
        str(sm["roadCameraState"].sensor),
        camera_height,
        main_wide_camera,
      )
      live_calib_seen = True

    traffic_convention = np.zeros(2)
    traffic_convention[int(is_rhd)] = 1

    vec_desire = np.zeros(ModelConstants.DESIRE_LEN, dtype=np.float32)
    if desire >= 0 and desire < ModelConstants.DESIRE_LEN:
      vec_desire[desire] = 1

    # tracked dropped frames
    vipc_dropped_frames = max(0, meta_main.frame_id - last_vipc_frame_id - 1)
    frames_dropped = frame_dropped_filter.update(min(vipc_dropped_frames, 10))
    if run_count < 10: # let frame drops warm up
      frame_dropped_filter.x = 0.
      frames_dropped = 0.
    run_count = run_count + 1

    frame_drop_ratio = frames_dropped / (1 + frames_dropped)
    prepare_only = vipc_dropped_frames > 0
    if prepare_only:
      cloudlog.error(f"skipping model eval. Dropped {vipc_dropped_frames} frames")

    bufs = {name: buf_extra if 'big' in name else buf_main for name in model.vision_input_names}
    transforms = {name: model_transform_extra if 'big' in name else model_transform_main for name in model.vision_input_names}

    frame_delay = DT_MDL  # Average time elapsed since the current frame finished exposing.
    action_delay = DT_MDL / 2  # Target the midpoint between current output and the next model step.
    lat_action_t = lat_delay + frame_delay + action_delay
    long_action_t = long_delay + frame_delay + action_delay

    inputs:dict[str, np.ndarray] = {
      model.desire_key: vec_desire,
      'traffic_convention': traffic_convention,
    }
    if 'action_t' in model.numpy_inputs or (model.off_policy_enabled and 'action_t' in model.off_policy_numpy_inputs):
      inputs['action_t'] = np.array([lat_action_t, long_action_t], dtype=np.float32)
    if 'prev_action' in model.numpy_inputs or (model.off_policy_enabled and 'prev_action' in model.off_policy_numpy_inputs):
      inputs['prev_action'] = np.array([
        prev_action.desiredCurvature * max(1.0, v_ego) ** 2,
        prev_action.desiredAcceleration,
      ], dtype=np.float32)
    # Include optional inputs only if the loaded model expects them
    if 'lateral_control_params' in model.numpy_inputs:
      inputs['lateral_control_params'] = lateral_control_params

    mt1 = time.perf_counter()
    model_output = model.run(bufs, transforms, inputs, prepare_only)
    mt2 = time.perf_counter()
    model_execution_time = mt2 - mt1

    if model_output is not None:
      modelv2_send = messaging.new_message('modelV2')
      starpilot_modelv2_send = messaging.new_message('starpilotModelV2')
      drivingdata_send = messaging.new_message('drivingModelData')
      posenet_send = messaging.new_message('cameraOdometry')

      action = get_action_from_model(
        model_output, prev_action,
        lat_action_t,
        long_action_t,
        v_ego, model.mlsim, model.is_v9, model.is_v14, model.is_v15, starpilot_toggles,
      )
      prev_action = action
      fill_model_msg(drivingdata_send, modelv2_send, model_output, action,
                     publish_state, meta_main.frame_id, meta_extra.frame_id, frame_id,
                     frame_drop_ratio, meta_main.timestamp_eof, model_execution_time, live_calib_seen)

      desire_state = modelv2_send.modelV2.meta.desireState
      l_lane_change_prob = desire_state[log.Desire.laneChangeLeft]
      r_lane_change_prob = desire_state[log.Desire.laneChangeRight]
      lane_change_prob = l_lane_change_prob + r_lane_change_prob
      DH.update(sm['carState'], sm['carControl'].latActive, lane_change_prob, sm['starpilotPlan'], starpilot_toggles)
      modelv2_send.modelV2.meta.laneChangeState = DH.lane_change_state
      modelv2_send.modelV2.meta.laneChangeDirection = DH.lane_change_direction
      starpilot_modelv2_send.starpilotModelV2.turnDirection = DH.turn_direction
      drivingdata_send.drivingModelData.meta.laneChangeState = DH.lane_change_state
      drivingdata_send.drivingModelData.meta.laneChangeDirection = DH.lane_change_direction

      fill_pose_msg(posenet_send, model_output, meta_main.frame_id, vipc_dropped_frames, meta_main.timestamp_eof, live_calib_seen)
      pm.send('modelV2', modelv2_send)
      pm.send('starpilotModelV2', starpilot_modelv2_send)
      pm.send('drivingModelData', drivingdata_send)
      pm.send('cameraOdometry', posenet_send)
    last_vipc_frame_id = meta_main.frame_id

    # Update planner-driven parameters
    if sm.updated['starpilotPlan']:
      starpilot_toggles = get_starpilot_toggles(sm)

if __name__ == "__main__":
  try:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true', help='A boolean for demo mode.')
    args = parser.parse_args()
    main(demo=args.demo)
  except KeyboardInterrupt:
    cloudlog.warning(f"child {PROCESS_NAME} got SIGINT")
  except Exception:
    sentry.capture_exception()
    raise
