#!/usr/bin/env python3
from collections.abc import Callable
import ctypes
from functools import cached_property
import os
import struct
from openpilot.system.hardware import HARDWARE, TICI
os.environ['GMMU'] = '0'
os.environ['DEV'] = 'QCOM' if TICI else 'LLVM'
from tinygrad.device import Device
from tinygrad.tensor import Tensor
import time
import pickle
import numpy as np
import cereal.messaging as messaging
from cereal import car, log
from pathlib import Path
from setproctitle import setproctitle
from cereal.messaging import PubMaster, SubMaster
from cereal.services import SERVICE_LIST
from msgq.visionipc import VisionIpcClient, VisionStreamType, VisionBuf
from openpilot.common.swaglog import cloudlog
from openpilot.common.params import Params
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.file_chunker import file_chunked_exists, open_file_chunked, read_file_chunked
from openpilot.common.realtime import config_realtime_process, DT_MDL
from openpilot.common.transformations.camera import DEVICE_CAMERAS
from openpilot.common.transformations.model import get_warp_matrix
from openpilot.system.camerad.cameras.nv12_info import get_nv12_info
from openpilot.system import sentry
from opendbc.car.car_helpers import get_demo_car_params
from opendbc.car.honda.values import CAR as HONDA_CAR
from openpilot.selfdrive.controls.lib.desire_helper import DesireHelper
from openpilot.selfdrive.controls.lib.drive_helpers import get_accel_from_plan_tomb_raider, smooth_value
from openpilot.selfdrive.modeld.camera_offset import CameraOffset, DEFAULT_CAMERA_HEIGHT
from openpilot.selfdrive.modeld.parse_model_outputs import Parser
from openpilot.selfdrive.modeld.fill_model_msg import fill_model_msg, fill_pose_msg, PublishState, get_curvature_from_output
from openpilot.selfdrive.modeld.constants import ModelConstants, Plan
from openpilot.selfdrive.modeld.compile_modeld import (
  ARTIFACT_FORMAT_VERSION,
  IMAGE_HISTORY_IN_POLICY,
  IMAGE_HISTORY_IN_WARP,
  LEGACY_WARP_INPUTS,
  _detect_vision_keys,
  make_split_input_queues,
  make_supercombo_input_queues,
)
from openpilot.selfdrive.modeld.helpers import get_tg_input_devices, load_oob, tinygrad_dev_config, usbgpu_present
from openpilot.selfdrive.modeld.usbgpu_link import wait_usbgpu_link
from openpilot.starpilot.assets.model_manager import ModelManager, model_uses_external_gpu
from openpilot.starpilot.common.model_versions import is_tinygrad_model_version
from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles, MODELS_PATH, params_memory


PROCESS_NAME = "selfdrive.modeld.modeld"
SEND_RAW_PRED = os.getenv('SEND_RAW_PRED')

BUILTIN_MODEL_KEY = "rdf43"
BUILTIN_MODEL_ALIASES = {BUILTIN_MODEL_KEY, "rdf"}
MODEL_ID_ALIASES = {"sc": "sc2"}


LAT_SMOOTH_SECONDS = 0.1
LONG_SMOOTH_SECONDS = 0.3
SMOOTH_SECONDS_STEP = 0.005

def _model_smooth_seconds(params, key, default):
  if not params.get_bool("DeveloperUI") or params.get_bool("SafeMode"):
    return default
  value = params.get_float(key, return_default=True, default=default)
  return round(min(max(value, SMOOTH_SECONDS_STEP), 2.0) / SMOOTH_SECONDS_STEP) * SMOOTH_SECONDS_STEP


def _should_publish_model_output(model_output, vipc_dropped_frames: int, external_gpu_active: bool = False) -> bool:
  return model_output is not None and vipc_dropped_frames == 0


MIN_LAT_CONTROL_SPEED = 0.3
BIG_MODEL_LOAD_WAIT_TIMEOUT_MS = 30000
BIG_MODEL_RUN_WAIT_TIMEOUT_MS = 3000
EXTERNAL_GPU_POWER_READY_MV = 10000
EXTERNAL_GPU_EGMP_READY_MV = 12500
EXTERNAL_GPU_POWER_STABLE_SECONDS = 3.0
EXTERNAL_GPU_POWER_LOG_INTERVAL_SECONDS = 10.0
LAT_SMOOTH_BP = [2.0, 8.0]


def _set_hcq_wait_timeout(timeout_ms: int) -> None:
  """Update tinygrad's cached HCQ timeout for the external-GPU load/run phase."""
  os.environ["HCQDEV_WAIT_TIMEOUT_MS"] = str(timeout_ms)
  # tinygrad.getenv is cached. Updating os.environ alone leaves the first value
  # in effect for the lifetime of modeld.
  from tinygrad.helpers import getenv
  getenv.cache_clear()


def _external_gpu_power_voltage(device_type: str, panda_states, peripheral_state) -> int | None:
  if device_type == "tici":
    voltage = int(peripheral_state.voltage)
    return voltage if peripheral_state.pandaType != log.PandaState.PandaType.unknown and voltage > 0 else None

  voltages = [
    int(state.voltage) for state in panda_states
    if state.pandaType != log.PandaState.PandaType.unknown and int(state.voltage) > 0
  ]
  return max(voltages, default=None)


def _external_gpu_power_ready(voltage: int | None, now: float, stable_since: float | None,
                              minimum_voltage: int = EXTERNAL_GPU_POWER_READY_MV) -> tuple[bool, float | None]:
  if voltage is None or voltage < minimum_voltage:
    return False, None

  stable_since = now if stable_since is None else stable_since
  return now - stable_since >= EXTERNAL_GPU_POWER_STABLE_SECONDS, stable_since


def _egmp_ready_bus(CP) -> int | None:
  if CP is None or CP.brand != "hyundai":
    return None

  # These platforms use the accessory-mode ECU-disable startup sequence.
  from opendbc.car.hyundai.hyundaicanfd import CanBus
  from opendbc.car.hyundai.values import CAR
  if CP.carFingerprint not in (CAR.HYUNDAI_IONIQ_5_PE, CAR.HYUNDAI_IONIQ_6, CAR.KIA_EV9):
    return None
  return CanBus(CP).ECAN


def _egmp_vehicle_ready(can_messages, bus: int) -> bool:
  return any(
    msg.address == 0x35 and msg.src == bus and len(msg.dat) > 3 and bytes(msg.dat)[3] & 0x40
    for msg in can_messages
  )


def wait_for_external_gpu_power_ready(CP=None) -> None:
  """Wait out vehicle startup power transitions before initializing Chestnut."""
  device_type = HARDWARE.get_device_type()
  egmp_bus = _egmp_ready_bus(CP)
  services = ["pandaStates", "peripheralState"] + (["can"] if egmp_bus is not None else [])
  sm = SubMaster(services)
  vehicle_ready = egmp_bus is None
  stable_since = None
  last_log = 0.0

  while True:
    sm.update(1000)
    now = time.monotonic()
    if egmp_bus is not None and sm.updated["can"] and _egmp_vehicle_ready(sm["can"], egmp_bus):
      if not vehicle_ready:
        cloudlog.warning("e-GMP vehicle entered READY; waiting for external GPU power to stabilize")
      vehicle_ready = True

    voltage = _external_gpu_power_voltage(device_type, sm["pandaStates"], sm["peripheralState"])
    minimum_voltage = EXTERNAL_GPU_EGMP_READY_MV if egmp_bus is not None else EXTERNAL_GPU_POWER_READY_MV
    ready, stable_since = _external_gpu_power_ready(
      voltage,
      now,
      stable_since if vehicle_ready else None,
      minimum_voltage,
    )
    if vehicle_ready and ready:
      cloudlog.warning(f"vehicle power stable at {voltage / 1000:.2f} V; starting external GPU load")
      return

    if now - last_log >= EXTERNAL_GPU_POWER_LOG_INTERVAL_SECONDS:
      detail = "unavailable" if voltage is None else f"{voltage / 1000:.2f} V"
      if not vehicle_ready:
        cloudlog.warning(f"external GPU load deferred: vehicle power is {detail}; waiting for e-GMP READY")
      else:
        cloudlog.warning(f"external GPU load deferred: vehicle power is {detail}; waiting for " +
                         f"{minimum_voltage / 1000:.1f} V to remain stable")
      last_log = now


def get_lateral_smooth_seconds(v_ego: float, maximum: float = 0.0) -> float:
  return float(np.interp(v_ego, LAT_SMOOTH_BP, [maximum, 0.0]))


def get_car_lateral_smooth_seconds(brand: str, v_ego: float, maximum: float) -> float:
  if brand in ("rivian", "subaru"):
    return get_lateral_smooth_seconds(v_ego, maximum)
  return maximum


class ChestnutState:
  """Publish bounded external-GPU and ASM2464 telemetry from modeld."""

  def __init__(self, pm: PubMaster, big: bool):
    self.pm = pm
    self.big = big
    self.valid = True
    self.sends = 0
    self.metrics = {}

  @cached_property
  def power_limit(self) -> int:
    smu = Device["AMD"].iface.dev_impl.smu
    return smu._send_msg(smu.smu_mod.PPSMC_MSG_GetPptLimit, 0, read_back_arg=True, timeout=100)

  def send(self) -> None:
    msg = messaging.new_message("chestnutState")
    state = msg.chestnutState
    self.sends += 1

    # SMU metrics are relatively expensive, so update them at 0.1 Hz while
    # publishing the cached values with the 10 Hz ASM link telemetry.
    if self.big and "AMD" in Device._opened_devices and self.sends % 100 == 1:
      try:
        smu = Device["AMD"].iface.dev_impl.smu
        metrics_t = smu.smu_mod.SmuMetricsExternal_t
        smu._send_msg(smu.smu_mod.PPSMC_MSG_TransferTableSmu2Dram, smu.smu_mod.TABLE_SMU_METRICS, timeout=100)
        metrics_buf = bytearray(smu.adev.vram.view(smu.driver_table_paddr, ctypes.sizeof(metrics_t))[:])
        metrics = metrics_t.from_buffer(metrics_buf).SmuMetrics
        self.metrics = {
          "tempC": metrics.AvgTemperature[smu.smu_mod.TEMP_HOTSPOT],
          "memoryTempC": metrics.AvgTemperature[smu.smu_mod.TEMP_MEM],
          "powerDrawW": metrics.AverageSocketPower,
          "powerLimitW": self.power_limit,
          "gpuUsagePercent": metrics.AverageGfxActivity,
          "gpuClockMhz": metrics.AverageGfxclkFrequencyPostDs,
          "fanSpeedRpm": metrics.AvgFanRpm,
        }
        self.valid = True
      except Exception:
        if self.valid:
          cloudlog.exception("chestnut state read failed")
        self.valid = False
        self.metrics.clear()

    if self.big:
      for key, value in self.metrics.items():
        setattr(state, key, value)

    asm_valid = False
    if "AMD" in Device._opened_devices:
      try:
        asm = Device["AMD"].iface.pci_dev.usb
        state.pcieLtssm = asm.read(0xB450, 1)[0]
        state.supplyVoltage, state.supplyCurrent = struct.unpack("<Hh", bytes(asm.usb.control_read(0xC0, 5))[:4])
        asm_valid = True
      except Exception:
        pass

    msg.valid = asm_valid and (not self.big or self.valid)
    self.pm.send("chestnutState", msg)


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
  if key in BUILTIN_MODEL_ALIASES:
    return BUILTIN_MODEL_KEY
  return MODEL_ID_ALIASES.get(key, key)


def _select_builtin_model(params: Params) -> None:
  params.put("Model", BUILTIN_MODEL_KEY)
  params.put("DrivingModel", BUILTIN_MODEL_KEY)
  params.put("DrivingModelName", "Regret Driven Framework V4")


def _close_tinygrad_disk_cache_connection() -> None:
  """Drop tinygrad's process-global cache connection before loading the next model."""
  import tinygrad.helpers as tinygrad_helpers

  connection = getattr(tinygrad_helpers, "_db_connection", None)
  if connection is None:
    return

  try:
    connection.close()
  except Exception:
    cloudlog.exception("failed to close tinygrad disk cache connection")
  finally:
    tinygrad_helpers._db_connection = None


def get_action_from_model(model_output: dict[str, np.ndarray], prev_action: log.ModelDataV2.Action,
                          lat_action_t: float, long_action_t: float, v_ego: float, mlsim: bool,
                          is_v9: bool, is_v14: bool, is_v15: bool, starpilot_toggles,
                          lat_smooth_seconds=LAT_SMOOTH_SECONDS, long_smooth_seconds=LONG_SMOOTH_SECONDS,
                          honda_accord_11g_lateral: bool = False, is_v16: bool = False) -> log.ModelDataV2.Action:
    if is_v14 or is_v15 or is_v16:
      desired_curv_unscaled, desired_accel = model_output['action'][0]
      if is_v15 or is_v16:
        desired_curvature = float(desired_curv_unscaled) / max(1.0, v_ego) ** 2
      else:
        desired_curvature = float(desired_curv_unscaled) / 100.0
      should_stop = (v_ego < 0.3 and desired_accel < 0.1)

      desired_accel = smooth_value(float(desired_accel), prev_action.desiredAcceleration, long_smooth_seconds)
      if v_ego > MIN_LAT_CONTROL_SPEED:
        desired_curvature = smooth_value(desired_curvature, prev_action.desiredCurvature, lat_smooth_seconds)
      else:
        desired_curvature = prev_action.desiredCurvature

      return log.ModelDataV2.Action(desiredCurvature=float(desired_curvature),
                                    desiredAcceleration=float(desired_accel),
                                    shouldStop=bool(should_stop))

    plan = model_output['plan'][0]
    if 'planplus' in model_output and not honda_accord_11g_lateral:
      recovery_power = getattr(starpilot_toggles, "recovery_power", 1.0)
      plan = plan + recovery_power * model_output['planplus'][0]
      cloudlog.error(f"planplus applied: shape {model_output['planplus'].shape}, RECOVERY_POWER {recovery_power}")
    v_ego_stopping = getattr(starpilot_toggles, "vEgoStopping", 0.3)
    desired_accel, should_stop = get_accel_from_plan_tomb_raider(plan[:,Plan.VELOCITY][:,0],
                                                                 plan[:,Plan.ACCELERATION][:,0],
                                                                 ModelConstants.T_IDXS,
                                                                 action_t=long_action_t,
                                                                 vEgoStopping=v_ego_stopping)
    desired_accel = smooth_value(desired_accel, prev_action.desiredAcceleration, long_smooth_seconds)

    if is_v9:
      # V9: use desired_curvature if present; otherwise do NOT fall back to plan
      if 'desired_curvature' in model_output:
        desired_curvature = float(model_output['desired_curvature'][0, 0])
      else:
        desired_curvature = prev_action.desiredCurvature
    else:
      desired_curvature = get_curvature_from_output(model_output, plan, v_ego, lat_action_t, mlsim=mlsim)
    if v_ego > MIN_LAT_CONTROL_SPEED:
      desired_curvature = smooth_value(desired_curvature, prev_action.desiredCurvature, lat_smooth_seconds)
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


def _load_model_artifact(path: Path):
  """Load legacy pickle artifacts and the streaming OOB format used by large GPU models."""
  with open_file_chunked(path) as artifact_file:
    pickle_header = artifact_file.peek(2)[:2]
    legacy_pickle = (
      len(pickle_header) == 2 and pickle_header[0] == 0x80 and pickle_header[1] <= pickle.HIGHEST_PROTOCOL
    )
    if legacy_pickle:
      return pickle.load(artifact_file)

  with open_file_chunked(path) as artifact_file:
    return load_oob(artifact_file)


class ModelState:
  prev_desire: np.ndarray

  def _build_policy_inputs(self, input_shapes: dict[str, tuple[int, ...]]) -> tuple[dict[str, np.ndarray], str | None]:
    numpy_inputs: dict[str, np.ndarray] = {}
    desire_key = next((key for key in input_shapes if key.startswith("desire")), None)
    if desire_key is not None:
      numpy_inputs[desire_key] = np.zeros(input_shapes[desire_key], dtype=np.float32)
    for key, shape in input_shapes.items():
      if key == desire_key or key == "features_buffer" or "img" in key:
        continue
      numpy_inputs[key] = np.zeros(shape, dtype=np.float32)

    prev_desired_curv_key = next(
      (key for key in ("prev_desired_curv", "prev_desired_curvs") if key in input_shapes),
      None,
    )
    return numpy_inputs, prev_desired_curv_key

  def __init__(self, cam_w: int, cam_h: int, external_gpu_active: bool = False,
               model_id_override: str | None = None, write_model_version: bool = True):
    params = Params()
    selected_model = model_id_override or _resolve_mirrored_param(params, "Model", "DrivingModel") or BUILTIN_MODEL_KEY
    model_id = _canonical_model_id(selected_model)
    requires_external_gpu = model_uses_external_gpu(model_id)
    if requires_external_gpu and not external_gpu_active:
      cloudlog.error(f"Model {model_id} requires an external GPU; falling back to {BUILTIN_MODEL_KEY}")
      model_id = BUILTIN_MODEL_KEY
    use_builtin = model_id == BUILTIN_MODEL_KEY
    loaded_builtin = use_builtin
    if use_builtin:
      model_path = Path(__file__).parent / "models" / "driving_tinygrad.pkl"
    else:
      model_path = MODELS_PATH / f"{model_id}_driving_tinygrad.pkl"

    if not file_chunked_exists(model_path) and not use_builtin:
      cloudlog.error(f"Missing model artifact {model_path}, downloading {model_id}...")
      try:
        ModelManager(params, params_memory).download_model(model_id)
      except Exception:
        cloudlog.exception(f"Failed to download model {model_id}")
    if not file_chunked_exists(model_path) and not use_builtin:
      fallback_path = Path(__file__).parent / "models" / "driving_tinygrad.pkl"
      if file_chunked_exists(fallback_path):
        cloudlog.error(f"Falling back to builtin model artifact after {model_id} download failed")
        model_path = fallback_path
        loaded_builtin = True
        requires_external_gpu = False
    if not file_chunked_exists(model_path):
      raise FileNotFoundError(model_path)

    self.uses_external_gpu = external_gpu_active and requires_external_gpu and not loaded_builtin
    artifact = (_load_model_artifact(model_path) if self.uses_external_gpu
                else pickle.loads(read_file_chunked(str(model_path))))
    if artifact.get("format_version") != ARTIFACT_FORMAT_VERSION:
      raise ValueError(
        f"Unsupported model artifact format {artifact.get('format_version')!r}; "
        f"expected {ARTIFACT_FORMAT_VERSION}"
      )

    self.model_type = artifact["model_type"]
    self.metadata = artifact["metadata"]
    self.policy_order = artifact.get("policy_order", [])
    self.frame_skip = int(artifact["frame_skip"])
    self.image_history_pipeline = artifact.get("image_history_pipeline", IMAGE_HISTORY_IN_WARP)
    self.warp_input_keys = tuple(artifact.get("warp_input_keys", LEGACY_WARP_INPUTS))
    self.policy_input_keys = tuple(artifact["policy_input_keys"])
    self.run_policy = artifact["run_policy"]
    self.warp_enqueue = artifact[(cam_w, cam_h)]
    self.can_prepare_only = self.image_history_pipeline == IMAGE_HISTORY_IN_WARP

    if self.model_type == "supercombo":
      input_shapes = self.metadata["model"]["input_shapes"]
      self.output_slices = self.metadata["model"]["output_slices"]
      self.input_queues, self.npy = make_supercombo_input_queues(input_shapes, self.frame_skip, self.QUEUE_DEV)
      self.policy_input_shapes = input_shapes
    else:
      vision_shapes = self.metadata["vision"]["input_shapes"]
      primary_policy = "on_policy" if "on_policy" in self.policy_order else "policy"
      self.policy_input_shapes = self.metadata[primary_policy]["input_shapes"]
      self.input_queues, self.npy = make_split_input_queues(
        vision_shapes, self.policy_input_shapes, self.frame_skip, self.QUEUE_DEV,
      )
      input_shapes = vision_shapes

    self.road_key, self.wide_key = _detect_vision_keys(input_shapes)
    self.vision_input_names = [self.road_key, self.wide_key]
    self.numpy_inputs, self.prev_desired_curv_key = self._build_policy_inputs(self.policy_input_shapes)
    self.desire_key = next(key for key in self.numpy_inputs if key.startswith("desire"))
    self.off_policy_enabled = "off_policy" in self.policy_order
    self.off_policy_numpy_inputs = dict(self.numpy_inputs) if self.off_policy_enabled else {}
    self.prev_desire = np.zeros(ModelConstants.DESIRE_LEN, dtype=np.float32)
    self.parser = Parser()
    self.aux_parser = Parser(ignore_missing=True)
    self.frame_buf_size = get_nv12_info(cam_w, cam_h)[3]
    self._blob_cache: dict[tuple[str, int], Tensor] = {}

    model_version = _resolve_mirrored_param(params, "ModelVersion", "DrivingModelVersion")
    if not model_version:
      model_version = str(artifact.get("behavior_version") or "")
    if not model_version:
      versions_path = MODELS_PATH / ".model_versions.json"
      if versions_path.is_file():
        try:
          import json
          model_version = str(json.loads(versions_path.read_text()).get(model_id) or "")
        except Exception:
          pass
    if loaded_builtin:
      model_version = str(artifact.get("behavior_version") or "v15")
    self.policy_generation = model_version or ("v15" if loaded_builtin else "v8")
    self.is_v9 = self.policy_generation == "v9"
    self.is_v14 = self.policy_generation == "v14"
    self.is_v15 = self.policy_generation == "v15"
    self.is_v16 = self.policy_generation == "v16"
    self.mlsim = is_tinygrad_model_version(self.policy_generation)
    if write_model_version:
      params.put("ModelVersion", self.policy_generation)
      params.put("DrivingModelVersion", self.policy_generation)

    if self.prev_desired_curv_key is not None:
      self.full_prev_desired_curv = np.zeros(
        (1, ModelConstants.FULL_HISTORY_BUFFER_LEN, ModelConstants.PREV_DESIRED_CURV_LEN),
        dtype=np.float32,
      )
    self.temporal_idxs = slice(
      -1 - (ModelConstants.TEMPORAL_SKIP * (ModelConstants.INPUT_HISTORY_BUFFER_LEN - 1)),
      None,
      ModelConstants.TEMPORAL_SKIP,
    )

  @property
  def QUEUE_DEV(self) -> str:
    if not hasattr(self, "_queue_dev"):
      devices = get_tg_input_devices(PROCESS_NAME, usbgpu=self.uses_external_gpu)
      self._warp_dev = devices["WARP_DEV"]
      self._queue_dev = devices["QUEUE_DEV"]
    return self._queue_dev

  @property
  def WARP_DEV(self) -> str:
    if not hasattr(self, "_warp_dev"):
      _ = self.QUEUE_DEV
    return self._warp_dev

  @staticmethod
  def slice_outputs(model_outputs: np.ndarray, output_slices: dict[str, slice]) -> dict[str, np.ndarray]:
    return {key: model_outputs[np.newaxis, value] for key, value in output_slices.items()}

  def _set_optional_input(self, name: str, inputs: dict[str, np.ndarray]) -> None:
    if name not in self.numpy_inputs or name not in inputs:
      return
    self.numpy_inputs[name][:] = inputs[name]
    if name in self.npy:
      self.npy[name][:] = self.numpy_inputs[name]

  def _parse_split_outputs(self, outputs: list[np.ndarray]) -> dict[str, np.ndarray]:
    vision_output, *policy_outputs = outputs
    parsed = self.parser.parse_vision_outputs(
      self.slice_outputs(vision_output, self.metadata["vision"]["output_slices"])
    )
    policy_results: dict[str, dict[str, np.ndarray]] = {}
    for key, output in zip(self.policy_order, policy_outputs, strict=True):
      sliced = self.slice_outputs(output, self.metadata[key]["output_slices"])
      policy_results[key] = (
        self.aux_parser.parse_off_policy_outputs(sliced)
        if key == "off_policy"
        else self.parser.parse_policy_outputs(sliced)
      )

    for key in self.policy_order:
      if key not in ("on_policy", "policy"):
        parsed.update(policy_results[key])
    primary_key = "on_policy" if "on_policy" in policy_results else "policy"
    parsed.update(policy_results[primary_key])
    return parsed

  def _reset_state(self) -> None:
    if self.model_type == "supercombo":
      self.input_queues, self.npy = make_supercombo_input_queues(
        self.policy_input_shapes, self.frame_skip, self.QUEUE_DEV,
      )
    else:
      vision_shapes = self.metadata["vision"]["input_shapes"]
      self.input_queues, self.npy = make_split_input_queues(
        vision_shapes, self.policy_input_shapes, self.frame_skip, self.QUEUE_DEV,
      )

    for value in self.numpy_inputs.values():
      value.fill(0)
    self.prev_desire.fill(0)
    if self.prev_desired_curv_key is not None:
      self.full_prev_desired_curv.fill(0)
    self._blob_cache.clear()

  def warmup(self) -> None:
    dummy_frames = {
      key: np.zeros(self.frame_buf_size, dtype=np.uint8)
      for key in self.vision_input_names
    }
    # A host pointer is not a valid camera buffer for every warp backend. Match
    # upstream and substitute realized device buffers for warmup only.
    self._blob_cache.update({
      (key, value.ctypes.data): Tensor.zeros(value.shape, dtype="uint8", device=self.WARP_DEV).realize()
      for key, value in dummy_frames.items()
    })
    eye = np.eye(3, dtype=np.float32)
    inputs = {self.desire_key: np.zeros(ModelConstants.DESIRE_LEN, dtype=np.float32)}
    for name, value in self.numpy_inputs.items():
      if name in (self.desire_key, self.prev_desired_curv_key):
        continue
      shape = value.shape[1:] if value.ndim > 1 and value.shape[0] == 1 else value.shape
      inputs[name] = np.zeros(shape, dtype=value.dtype)

    self.run(dummy_frames, dict.fromkeys(self.vision_input_names, eye), inputs, False)
    self._reset_state()

  def run(self, bufs: dict[str, VisionBuf], transforms: dict[str, np.ndarray],
          inputs: dict[str, np.ndarray], prepare_only: bool,
          after_enqueue: Callable[[], None] | None = None) -> dict[str, np.ndarray] | None:
    frames: dict[str, Tensor] = {}
    for key, buf in bufs.items():
      ptr = np.frombuffer(buf.data, dtype=np.uint8).ctypes.data
      cache_key = (key, ptr)
      if cache_key not in self._blob_cache:
        self._blob_cache[cache_key] = Tensor.from_blob(
          ptr, (self.frame_buf_size,), dtype="uint8", device=self.WARP_DEV,
        )
      frames[key] = self._blob_cache[cache_key]

    inputs[self.desire_key][0] = 0
    self.numpy_inputs[self.desire_key].fill(0)
    self.numpy_inputs[self.desire_key].reshape(-1, ModelConstants.DESIRE_LEN)[-1] = inputs[self.desire_key]
    self.npy["desire"][:] = np.where(
      inputs[self.desire_key] - self.prev_desire > 0.99,
      inputs[self.desire_key],
      0,
    )
    self.prev_desire[:] = inputs[self.desire_key]
    for name in self.numpy_inputs:
      if name not in (self.desire_key, self.prev_desired_curv_key):
        self._set_optional_input(name, inputs)
    self.npy["tfm"][:] = transforms[self.road_key]
    self.npy["big_tfm"][:] = transforms[self.wide_key]

    warp_output = self.warp_enqueue(
      **{key: self.input_queues[key] for key in self.warp_input_keys},
      frame=frames[self.road_key],
      big_frame=frames[self.wide_key],
    )

    if self.image_history_pipeline == IMAGE_HISTORY_IN_POLICY:
      output_tensors = self.run_policy(
        **{key: self.input_queues[key] for key in self.policy_input_keys},
        warped=warp_output,
      )
    else:
      img, big_img = warp_output
      if prepare_only:
        return None
      output_tensors = self.run_policy(
        **{key: self.input_queues[key] for key in self.policy_input_keys},
        img=img,
        big_img=big_img,
      )
    if after_enqueue is not None:
      after_enqueue()
    outputs = [output.numpy().flatten() for output in output_tensors]

    if self.uses_external_gpu and any(not np.isfinite(output).all() for output in outputs):
      raise RuntimeError("external GPU model output not finite")

    if self.model_type == "supercombo":
      model_output = outputs[0]
      parsed = self.parser.parse_outputs(self.slice_outputs(model_output, self.output_slices))
      if "prev_feat" in self.npy and "hidden_state" in self.output_slices:
        self.npy["prev_feat"][:] = model_output[self.output_slices["hidden_state"]]
    else:
      parsed = self._parse_split_outputs(outputs)

    if self.prev_desired_curv_key is not None and "desired_curvature" in parsed:
      self.full_prev_desired_curv[0, :-1] = self.full_prev_desired_curv[0, 1:]
      self.full_prev_desired_curv[0, -1, :] = parsed["desired_curvature"][0, :]
      history = self.full_prev_desired_curv[0, self.temporal_idxs]
      self.numpy_inputs[self.prev_desired_curv_key][:] = 0 * history if self.mlsim else history
      if self.prev_desired_curv_key in self.npy:
        self.npy[self.prev_desired_curv_key][:] = self.numpy_inputs[self.prev_desired_curv_key]

    if SEND_RAW_PRED:
      parsed["raw_pred"] = np.concatenate([output.copy() for output in outputs])
    return parsed


def _load_model_state(cam_w: int, cam_h: int, selected_model: str, external_gpu_requested: bool,
                      params: Params) -> ModelState:
  try:
    return ModelState(cam_w, cam_h, external_gpu_requested)
  except Exception:
    if selected_model == BUILTIN_MODEL_KEY:
      raise

    cloudlog.exception(f"Failed to load model {selected_model}; falling back to {BUILTIN_MODEL_KEY}")
    _select_builtin_model(params)
    if external_gpu_requested:
      from tinygrad.helpers import DEV
      device_config = tinygrad_dev_config(False, TICI)
      DEV.value = device_config
      os.environ["DEV"] = device_config
    return ModelState(cam_w, cam_h, False)


def _load_external_gpu_model(cam_w: int, cam_h: int, selected_model: str,
                             CP=None, demo: bool = False) -> ModelState | None:
  """Load and warm the USB-GPU model without running another tinygrad model concurrently."""
  candidate = None
  try:
    if not demo:
      wait_for_external_gpu_power_ready(CP)
    _set_hcq_wait_timeout(BIG_MODEL_LOAD_WAIT_TIMEOUT_MS)
    wait_usbgpu_link()
    candidate = ModelState(
      cam_w,
      cam_h,
      True,
      model_id_override=selected_model,
      write_model_version=False,
    )
    if not candidate.uses_external_gpu:
      raise RuntimeError("external GPU model resolved to the builtin model")
    candidate.warmup()
    return candidate
  except Exception:
    cloudlog.exception("external GPU model load or warmup failed")
    return None
  finally:
    _close_tinygrad_disk_cache_connection()
    _set_hcq_wait_timeout(BIG_MODEL_RUN_WAIT_TIMEOUT_MS)


def main(demo=False):
  cloudlog.warning("modeld init")

  sentry.set_tag("daemon", PROCESS_NAME)
  cloudlog.bind(daemon=PROCESS_NAME)
  setproctitle(PROCESS_NAME)
  config_realtime_process(7, 54)

  params = Params()
  selected_model = _canonical_model_id(_resolve_mirrored_param(params, "Model", "DrivingModel") or BUILTIN_MODEL_KEY)
  usbgpu_present_now = usbgpu_present()
  external_model_selected = model_uses_external_gpu(selected_model)
  external_artifact = MODELS_PATH / f"{selected_model}_driving_tinygrad.pkl"
  external_artifact_ready = external_model_selected and file_chunked_exists(external_artifact)
  external_gpu_requested = usbgpu_present_now and external_model_selected
  params.put_bool("UsbGpuPresent", usbgpu_present_now)
  params.put_bool("UsbGpuCompiled", external_artifact_ready)
  params.put_bool("UsbGpuActive", False)
  params.put_bool("UsbGpuLoading", external_gpu_requested)

  # visionipc clients
  while True:
    available_streams = VisionIpcClient.available_streams("camerad", block=False)
    if available_streams:
      use_extra_client = VisionStreamType.VISION_STREAM_WIDE_ROAD in available_streams and VisionStreamType.VISION_STREAM_ROAD in available_streams
      main_wide_camera = VisionStreamType.VISION_STREAM_ROAD not in available_streams
      break
    time.sleep(.1)

  vipc_client_main_stream = VisionStreamType.VISION_STREAM_WIDE_ROAD if main_wide_camera else VisionStreamType.VISION_STREAM_ROAD
  vipc_client_main = VisionIpcClient("camerad", vipc_client_main_stream, True)
  vipc_client_extra = VisionIpcClient("camerad", VisionStreamType.VISION_STREAM_WIDE_ROAD, False)
  cloudlog.warning(f"vision stream set up, main_wide_camera: {main_wide_camera}, use_extra_client: {use_extra_client}")

  while not vipc_client_main.connect(False):
    time.sleep(0.1)
  while use_extra_client and not vipc_client_extra.connect(False):
    time.sleep(0.1)

  cloudlog.warning(f"connected main cam with buffer size: {vipc_client_main.buffer_len} ({vipc_client_main.width} x {vipc_client_main.height})")
  if use_extra_client:
    cloudlog.warning(f"connected extra cam with buffer size: {vipc_client_extra.buffer_len} ({vipc_client_extra.width} x {vipc_client_extra.height})")

  start_time = time.monotonic()
  cloudlog.warning("loading model")
  model = None
  small_model = None
  big_model = None
  CP = None
  if external_gpu_requested:
    if demo:
      CP = get_demo_car_params()
    else:
      CP = messaging.log_from_bytes(params.get("CarParams", block=True), car.CarParams)

    big_model = _load_external_gpu_model(
      vipc_client_main.width,
      vipc_client_main.height,
      selected_model,
      CP,
      demo,
    )

    small_model = ModelState(
      vipc_client_main.width,
      vipc_client_main.height,
      False,
      model_id_override=BUILTIN_MODEL_KEY,
      write_model_version=False,
    )
    model = big_model if big_model is not None else small_model
    if big_model is not None:
      params.put("ModelVersion", model.policy_generation)
      params.put("DrivingModelVersion", model.policy_generation)
  else:
    model = _load_model_state(vipc_client_main.width, vipc_client_main.height, selected_model, False, params)

  external_gpu_active = model.uses_external_gpu
  params.put_bool("UsbGpuCompiled", external_model_selected and file_chunked_exists(external_artifact))
  params.put_bool("UsbGpuActive", external_gpu_active)
  params.put_bool("UsbGpuLoading", False)
  cloudlog.warning(f"models loaded in {time.monotonic() - start_time:.1f}s, modeld starting")

  # messaging
  publish_services = ["modelV2", "drivingModelData", "cameraOdometry", "starpilotModelV2"]
  if external_gpu_requested:
    publish_services.append("chestnutState")
  pm = PubMaster(publish_services)
  sm = SubMaster(["deviceState", "carState", "roadCameraState", "liveCalibration", "driverMonitoringState", "carControl", "liveDelay", "starpilotPlan"])

  publish_state = PublishState()
  chestnut_state = ChestnutState(pm, external_gpu_active) if external_gpu_requested else None
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


  if CP is None:
    if demo:
      CP = get_demo_car_params()
    else:
      CP = messaging.log_from_bytes(params.get("CarParams", block=True), car.CarParams)
  cloudlog.info("modeld got CarParams: %s", CP.brand)
  honda_accord_11g_lateral = CP.brand == "honda" and CP.carFingerprint == HONDA_CAR.HONDA_ACCORD_11G

  lat_smooth_seconds = 0.0 if honda_accord_11g_lateral else _model_smooth_seconds(params, "LatSmoothSeconds", LAT_SMOOTH_SECONDS)
  long_smooth_seconds = _model_smooth_seconds(params, "LongSmoothSeconds", LONG_SMOOTH_SECONDS)
  long_delay = CP.longitudinalActuatorDelay + long_smooth_seconds
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

    long_smooth_seconds = _model_smooth_seconds(params, "LongSmoothSeconds", LONG_SMOOTH_SECONDS)
    long_delay = CP.longitudinalActuatorDelay + long_smooth_seconds
    desire = DH.desire
    is_rhd = sm["driverMonitoringState"].isRHD
    frame_id = sm["roadCameraState"].frameId
    v_ego = max(sm["carState"].vEgo, 0.)
    lat_smooth_default = CP.lateralSmoothSeconds if (CP.brand == "rivian" or CP.lateralSmoothSeconds > 0.0) else LAT_SMOOTH_SECONDS
    lat_smooth_maximum = _model_smooth_seconds(params, "LatSmoothSeconds", lat_smooth_default)
    lat_smooth_seconds = 0.0 if honda_accord_11g_lateral else get_car_lateral_smooth_seconds(CP.brand, v_ego, lat_smooth_maximum)
    if honda_accord_11g_lateral and not sm.seen['liveDelay']:
      lat_delay = CP.steerActuatorDelay + 0.2
    else:
      lat_delay = sm["liveDelay"].lateralDelay + lat_smooth_seconds
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
    prepare_only = model.can_prepare_only and vipc_dropped_frames > 0
    if prepare_only:
      cloudlog.error(f"skipping model eval. Dropped {vipc_dropped_frames} frames")

    bufs = {
      model.road_key: buf_main,
      model.wide_key: buf_extra,
    }
    transforms = {
      model.road_key: model_transform_main,
      model.wide_key: model_transform_extra,
    }

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
    try:
      send_chestnut = (
        chestnut_state is not None and
        run_count % round(ModelConstants.MODEL_FREQ / SERVICE_LIST["chestnutState"].frequency) == 0
      )
      model_output = model.run(
        bufs,
        transforms,
        inputs,
        prepare_only,
        chestnut_state.send if send_chestnut else None,
      )
    except Exception:
      if not external_gpu_active or small_model is None:
        raise
      cloudlog.exception("external GPU model failed, falling back to builtin model")
      params.put_bool("UsbGpuActive", False)
      model = small_model
      big_model = None
      external_gpu_active = False
      params.put("ModelVersion", model.policy_generation)
      params.put("DrivingModelVersion", model.policy_generation)
      params.put_bool("UsbGpuLoading", False)
      if chestnut_state is not None:
        chestnut_state.big = False
      run_count = 0
      model_output = None

    mt2 = time.perf_counter()
    model_execution_time = mt2 - mt1

    if model_output is not None and vipc_dropped_frames > 0:
      cloudlog.error(f"suppressing model output after dropping {vipc_dropped_frames} frames")

    if _should_publish_model_output(model_output, vipc_dropped_frames, external_gpu_active):
      modelv2_send = messaging.new_message('modelV2')
      starpilot_modelv2_send = messaging.new_message('starpilotModelV2')
      drivingdata_send = messaging.new_message('drivingModelData')
      posenet_send = messaging.new_message('cameraOdometry')

      action = get_action_from_model(
        model_output, prev_action,
        lat_action_t,
        long_action_t,
        v_ego, model.mlsim, model.is_v9, model.is_v14, model.is_v15, starpilot_toggles,
        lat_smooth_seconds, long_smooth_seconds,
        honda_accord_11g_lateral=honda_accord_11g_lateral, is_v16=model.is_v16,
      )
      prev_action = action
      fill_model_msg(drivingdata_send, modelv2_send, model_output, action,
                     publish_state, meta_main.frame_id, meta_extra.frame_id, frame_id,
                     frame_drop_ratio, meta_main.timestamp_eof, model_execution_time, live_calib_seen)

      desire_state = modelv2_send.modelV2.meta.desireState
      l_lane_change_prob = desire_state[log.Desire.laneChangeLeft]
      r_lane_change_prob = desire_state[log.Desire.laneChangeRight]
      lane_change_prob = l_lane_change_prob + r_lane_change_prob
      DH.update(sm['carState'], sm['carControl'].latActive, lane_change_prob, sm['starpilotPlan'], starpilot_toggles, sm['carControl'].enabled)
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
