import math
import struct
import threading
import time
import zlib

from dataclasses import dataclass
from enum import IntEnum, IntFlag
from typing import Any

from cereal import messaging

from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog


LIVE_PROTOCOL_VERSION = 1
LIVE_FRAME_TYPE_STATE = 1
LIVE_FRAME_TYPE_HEALTH = 2
LIVE_FRAME_RATE_HZ = 10
# The health frame tracks deviceState (~2 Hz), emitted every Nth tick of the 10 Hz loop.
LIVE_HEALTH_TICK_DIVISOR = LIVE_FRAME_RATE_HZ // 2
LIVE_HEALTH_FRAME_RATE_HZ = LIVE_FRAME_RATE_HZ // LIVE_HEALTH_TICK_DIVISOR
# Retained in the Companion API v2 status payload for client compatibility.
LIVE_PATH_FRAME_RATE_HZ = 0
LIVE_FRAME_SIZE = 64
LIVE_FRAME_MAGIC = b"SP"
LIVE_NOTIFICATION_SIZE = 20
LIVE_NOTIFICATION_HEADER_SIZE = 4
LIVE_NOTIFICATION_PAYLOAD_SIZE = LIVE_NOTIFICATION_SIZE - LIVE_NOTIFICATION_HEADER_SIZE
LIVE_NOTIFICATION_FRAGMENT_COUNT = LIVE_FRAME_SIZE // LIVE_NOTIFICATION_PAYLOAD_SIZE
LIVE_TOTAL_FRAME_RATE_HZ = LIVE_FRAME_RATE_HZ + LIVE_HEALTH_FRAME_RATE_HZ
LIVE_TOTAL_NOTIFICATION_RATE_HZ = LIVE_TOTAL_FRAME_RATE_HZ * LIVE_NOTIFICATION_FRAGMENT_COUNT
LIVE_PARAMS_REFRESH_INTERVAL_S = 1.0
LIVE_OVERRUN_SLEEP_S = 0.01

# Below this free-storage percentage the health frame raises the low-storage flag.
LIVE_LOW_STORAGE_PERCENT = 10
# An Athena ping newer than this many seconds counts as a fresh cloud contact.
LIVE_ATHENA_FRESH_S = 70.0

NETWORK_TYPE_CELLULAR = (2, 3, 4, 5)
NETWORK_TYPE_WIFI = 1
NETWORK_TYPE_ETHERNET = 6
THERMAL_STATUS_OK = 0
THERMAL_STATUS_OVERHEATED = 2
THERMAL_STATUS_CRITICAL = 3


class LiveFlags(IntFlag):
  CONNECTED = 1 << 0
  STARTED = 1 << 1
  ENGAGED = 1 << 2
  ACTIVE = 1 << 3
  CRUISE_AVAILABLE = 1 << 4
  CRUISE_ENABLED = 1 << 5
  ALWAYS_ON_LATERAL = 1 << 6
  EXPERIMENTAL_MODE = 1 << 7
  CONDITIONAL_CHILL = 1 << 8
  SPEED_LIMIT_CONTROL = 1 << 9
  SPEED_LIMIT_ACTIVE = 1 << 10
  CURVE_CONTROL = 1 << 11
  CURVE_CONTROL_ACTIVE = 1 << 12
  LEAD_PRESENT = 1 << 13
  LATERAL_ACTIVE = 1 << 14
  LONGITUDINAL_ACTIVE = 1 << 15
  GAS_PRESSED = 1 << 16
  BRAKE_PRESSED = 1 << 17
  STOPPING = 1 << 18
  STANDSTILL = 1 << 19
  BIG_MODEL = 1 << 20
  LATERAL_PAUSED = 1 << 21
  TRAFFIC_MODE = 1 << 22
  SWITCHBACK_MODE = 1 << 23
  ALERT_PRESENT = 1 << 24
  TELEMETRY_VALID = 1 << 25
  FORCING_STOP = 1 << 26
  TRACKING_LEAD = 1 << 27
  PULSE_AND_GLIDE = 1 << 28
  METRIC = 1 << 29
  OVERRIDING = 1 << 30
  RED_LIGHT = 1 << 31


class HealthFlags(IntFlag):
  ONROAD = 1 << 0
  OFFROAD = 1 << 1
  NETWORK_METERED = 1 << 2
  WIFI_CONNECTED = 1 << 3
  ETHERNET_CONNECTED = 1 << 4
  CELLULAR_CONNECTED = 1 << 5
  # Device has a non-metered Wi-Fi/Ethernet link; the phone must still verify local reachability.
  LOCAL_NON_METERED_LINK = 1 << 6
  THERMAL_OK = 1 << 7
  THERMAL_OVERHEATED = 1 << 8
  THERMAL_CRITICAL = 1 << 9
  FAN_ACTIVE = 1 << 10
  LOW_STORAGE = 1 << 11
  CLOUD_PINGED = 1 << 13


class CruiseState(IntEnum):
  UNAVAILABLE = 0
  AVAILABLE = 1
  ENABLED = 2
  STANDSTILL = 3
  NON_ADAPTIVE = 4


class BorderState(IntEnum):
  NONE = 0
  DISENGAGED = 1
  ENGAGED = 2
  ALWAYS_ON_LATERAL = 3
  LONGITUDINAL_ONLY = 4
  OVERRIDE = 5
  EXPERIMENTAL = 6
  CONDITIONAL_OVERRIDE = 7
  SWITCHBACK = 8
  TRAFFIC = 9
  PULSE_AND_GLIDE = 10


class ConditionalChillReason(IntEnum):
  NONE = 0
  LEAD = 1
  SPEED = 2
  MANUAL = 3


class ModelSource(IntEnum):
  SMALL = 0
  BIG = 1
  BIG_LOADING = 2


BORDER_COLORS = {
  BorderState.NONE: (0, 0, 0, 0),
  BorderState.DISENGAGED: (18, 40, 57, 255),
  BorderState.ENGAGED: (22, 127, 64, 255),
  BorderState.ALWAYS_ON_LATERAL: (10, 186, 181, 255),
  BorderState.LONGITUDINAL_ONLY: (255, 105, 180, 255),
  BorderState.OVERRIDE: (137, 146, 141, 255),
  BorderState.EXPERIMENTAL: (218, 111, 37, 255),
  BorderState.CONDITIONAL_OVERRIDE: (255, 214, 0, 255),
  BorderState.SWITCHBACK: (139, 108, 197, 255),
  BorderState.TRAFFIC: (201, 34, 49, 255),
  BorderState.PULSE_AND_GLIDE: (24, 72, 150, 255),
}

CC_USER_EXPERIMENTAL = 1
CC_USER_CHILL = 2
CC_LEAD = 4
CC_SPEED = 6
CE_USER_DISABLED = 1


def _service(sm: Any, name: str) -> Any | None:
  try:
    return sm[name]
  except (KeyError, IndexError, TypeError, AttributeError):
    return None


def _sm_bool(sm: Any, collection: str, name: str, default: bool = False) -> bool:
  values = getattr(sm, collection, None)
  if isinstance(values, dict):
    return bool(values.get(name, default))
  try:
    return bool(values[name])
  except (KeyError, IndexError, TypeError, AttributeError):
    return default


def _raw_enum(value: Any, default: int = 0) -> int:
  try:
    return int(getattr(value, "raw", value))
  except (TypeError, ValueError):
    return default


def _param_bool(params: Params, key: str) -> bool:
  if isinstance(params, dict):
    return bool(params.get(key, False))
  try:
    return bool(params.get_bool(key))
  except (AttributeError, TypeError, ValueError):
    return bool(params.get(key))


def _param_int(params: Params, key: str, default: int = 0) -> int:
  if isinstance(params, dict):
    return int(params.get(key, default))
  try:
    return int(params.get_int(key, default=default))
  except (AttributeError, TypeError, ValueError):
    try:
      value = params.get(key)
      return default if value is None else int(value)
    except (AttributeError, TypeError, ValueError):
      return default


def _param_text(params: Params, key: str, limit: int = 128) -> str:
  if isinstance(params, dict):
    return str(params.get(key, ""))[:limit]
  try:
    value = params.get(key, encoding="utf-8") or ""
  except TypeError:
    value = params.get(key) or ""
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")
  return str(value)[:limit]


def _finite(value: Any, default: float = 0.0) -> float:
  try:
    result = float(value)
    return result if math.isfinite(result) else default
  except (TypeError, ValueError):
    return default


def _scaled(value: Any, scale: float, low: int, high: int) -> int:
  return min(high, max(low, round(_finite(value) * scale)))


def _max_finite(values: Any, default: float = 0.0) -> float:
  """Reduce a capnp list (or scalar) to the max of its finite values."""
  try:
    finite = [float(v) for v in values if math.isfinite(float(v))]
  except (TypeError, ValueError):
    return _finite(values, default)
  return max(finite) if finite else default


def _pack_live_header(frame_type: int, sequence: int, monotonic_ms: int, flags: int) -> bytes:
  return struct.pack(
    "<2sBBHHII",
    LIVE_FRAME_MAGIC,
    LIVE_PROTOCOL_VERSION,
    int(frame_type) & 0xFF,
    LIVE_FRAME_SIZE,
    int(sequence) & 0xFFFF,
    int(monotonic_ms) & 0xFFFFFFFF,
    int(flags) & 0xFFFFFFFF,
  )


def _crc32(text: str) -> int:
  return zlib.crc32(text.encode("utf-8", errors="replace")) & 0xFFFFFFFF


def _cruise_state(cruise: Any) -> CruiseState:
  if cruise is None or not bool(getattr(cruise, "available", False)):
    return CruiseState.UNAVAILABLE
  if bool(getattr(cruise, "nonAdaptive", False)):
    return CruiseState.NON_ADAPTIVE
  if bool(getattr(cruise, "standstill", False)):
    return CruiseState.STANDSTILL
  if bool(getattr(cruise, "enabled", False)):
    return CruiseState.ENABLED
  return CruiseState.AVAILABLE


def _conditional_chill(params: Params, params_memory: Params) -> tuple[bool, ConditionalChillReason]:
  if not _param_bool(params, "ConditionalChill"):
    return False, ConditionalChillReason.NONE
  status = _param_int(params_memory, "CCStatus")
  if status == CC_LEAD:
    return True, ConditionalChillReason.LEAD
  if status == CC_SPEED:
    return True, ConditionalChillReason.SPEED
  if status == CC_USER_CHILL:
    return True, ConditionalChillReason.MANUAL
  if status == CC_USER_EXPERIMENTAL:
    return False, ConditionalChillReason.MANUAL
  return False, ConditionalChillReason.NONE


def _lateral_desired_angle(controls_state: Any, car_control: Any) -> float:
  lateral = getattr(controls_state, "lateralControlState", None)
  if lateral is not None:
    try:
      selected = getattr(lateral, lateral.which())
    except (AttributeError, TypeError):
      selected = lateral
    desired = getattr(selected, "steeringAngleDesiredDeg", None)
    if desired is not None:
      return _finite(desired)
  actuators = getattr(car_control, "actuators", None)
  return _finite(getattr(actuators, "steeringAngleDeg", 0.0))


def _onroad_overrides(events: Any) -> tuple[bool, bool]:
  try:
    return (
      any(bool(getattr(event, "overrideLateral", False)) for event in events),
      any(bool(getattr(event, "overrideLongitudinal", False)) for event in events),
    )
  except TypeError:
    return False, False


def _border_state(started: bool, selfdrive_state: Any, starpilot_car_state: Any, starpilot_plan: Any,
                  events: Any, params_memory: Params, switchback: bool) -> BorderState:
  if not started:
    return BorderState.NONE

  enabled = bool(getattr(selfdrive_state, "enabled", False))
  active = bool(getattr(selfdrive_state, "active", False))
  pause_lateral = bool(getattr(starpilot_car_state, "pauseLateral", False))
  always_on_lateral = not enabled and bool(getattr(starpilot_car_state, "alwaysOnLateralEnabled", False))
  traffic = bool(getattr(starpilot_car_state, "trafficModeEnabled", False))
  overriding = _raw_enum(getattr(selfdrive_state, "state", 0)) == 4
  lateral_override, longitudinal_override = _onroad_overrides(events)
  override_applies = overriding and (
    longitudinal_override if enabled and pause_lateral else
    lateral_override if always_on_lateral else
    lateral_override or longitudinal_override
  )

  if override_applies:
    state = BorderState.OVERRIDE
  elif enabled and pause_lateral:
    state = BorderState.LONGITUDINAL_ONLY
  elif switchback and (enabled or always_on_lateral):
    state = BorderState.SWITCHBACK
  elif traffic and enabled:
    state = BorderState.TRAFFIC
  elif always_on_lateral:
    state = BorderState.ALWAYS_ON_LATERAL
  elif enabled and _param_int(params_memory, "CEStatus") == CE_USER_DISABLED:
    state = BorderState.CONDITIONAL_OVERRIDE
  elif enabled and bool(getattr(selfdrive_state, "experimentalMode", False)):
    state = BorderState.EXPERIMENTAL
  elif active or enabled:
    state = BorderState.ENGAGED
  else:
    state = BorderState.DISENGAGED

  if (
    bool(getattr(starpilot_car_state, "pulseAndGlide", False)) and
    bool(getattr(starpilot_plan, "pulseGlideCoasting", False))
  ):
    state = BorderState.PULSE_AND_GLIDE
  return state


@dataclass(frozen=True)
class LiveSnapshot:
  flags: int = int(LiveFlags.CONNECTED)
  vehicle_speed: float = 0.0
  set_speed: float = 0.0
  acceleration: float = 0.0
  target_acceleration: float = 0.0
  steering_angle: float = 0.0
  desired_steering_angle: float = 0.0
  steering_torque: float = 0.0
  lead_distance: float = 0.0
  lead_relative_speed: float = 0.0
  lead_probability: float = 0.0
  speed_limit: float = 0.0
  speed_limit_offset: float = 0.0
  curve_target_speed: float = 0.0
  cruise_state: int = int(CruiseState.UNAVAILABLE)
  border_state: int = int(BorderState.NONE)
  alert_status: int = 0
  conditional_chill_reason: int = int(ConditionalChillReason.NONE)
  driving_profile: int = 0
  longitudinal_profile: int = 0
  lane_change_state: int = 0
  lane_change_direction: int = 0
  long_control_state: int = 0
  model_source: int = int(ModelSource.SMALL)
  border_color: tuple[int, int, int, int] = BORDER_COLORS[BorderState.NONE]
  alert_id: int = 0
  metadata_revision: int = 0

  def pack(self, sequence: int, monotonic_ms: int) -> bytes:
    header = _pack_live_header(LIVE_FRAME_TYPE_STATE, sequence, monotonic_ms, self.flags)
    telemetry = struct.pack(
      "<hHhhhhhHhHHhH",
      _scaled(self.vehicle_speed, 100.0, -32768, 32767),
      _scaled(self.set_speed, 100.0, 0, 65535),
      _scaled(self.acceleration, 100.0, -32768, 32767),
      _scaled(self.target_acceleration, 100.0, -32768, 32767),
      _scaled(self.steering_angle, 10.0, -32768, 32767),
      _scaled(self.desired_steering_angle, 10.0, -32768, 32767),
      _scaled(self.steering_torque, 10.0, -32768, 32767),
      _scaled(self.lead_distance, 10.0, 0, 65535),
      _scaled(self.lead_relative_speed, 100.0, -32768, 32767),
      _scaled(self.lead_probability, 1000.0, 0, 1000),
      _scaled(self.speed_limit, 100.0, 0, 65535),
      _scaled(self.speed_limit_offset, 100.0, -32768, 32767),
      _scaled(self.curve_target_speed, 100.0, 0, 65535),
    )
    state = struct.pack(
      "<10B4BII",
      int(self.cruise_state) & 0xFF,
      int(self.border_state) & 0xFF,
      int(self.alert_status) & 0xFF,
      int(self.conditional_chill_reason) & 0xFF,
      int(self.driving_profile) & 0xFF,
      int(self.longitudinal_profile) & 0xFF,
      int(self.lane_change_state) & 0xFF,
      int(self.lane_change_direction) & 0xFF,
      int(self.long_control_state) & 0xFF,
      int(self.model_source) & 0xFF,
      *(min(255, max(0, int(channel))) for channel in self.border_color),
      int(self.alert_id) & 0xFFFFFFFF,
      int(self.metadata_revision) & 0xFFFFFFFF,
    )
    frame = header + telemetry + state
    if len(frame) != LIVE_FRAME_SIZE:
      raise AssertionError(f"Invalid live frame size: {len(frame)}")
    return frame


def live_notification_fragments(frame: bytes) -> tuple[bytes, ...]:
  """Split a live frame into notifications that fit the default 23-byte ATT MTU."""
  if len(frame) != LIVE_FRAME_SIZE:
    raise ValueError(f"Live frame must be {LIVE_FRAME_SIZE} bytes")
  sequence = struct.unpack_from("<H", frame, 6)[0]
  fragments = []
  for index in range(LIVE_NOTIFICATION_FRAGMENT_COUNT):
    fragment_info = (LIVE_NOTIFICATION_FRAGMENT_COUNT << 4) | index
    start = index * LIVE_NOTIFICATION_PAYLOAD_SIZE
    payload = frame[start:start + LIVE_NOTIFICATION_PAYLOAD_SIZE]
    fragments.append(struct.pack("<BHB", LIVE_PROTOCOL_VERSION, sequence, fragment_info) + payload)
  return tuple(fragments)


def build_live_snapshot(sm: Any, params: Params, params_memory: Params) -> LiveSnapshot:
  device_state = _service(sm, "deviceState")
  car_state = _service(sm, "carState")
  selfdrive_state = _service(sm, "selfdriveState")
  car_control = _service(sm, "carControl")
  controls_state = _service(sm, "controlsState")
  radar_state = _service(sm, "radarState")
  longitudinal_plan = _service(sm, "longitudinalPlan")
  model = _service(sm, "drivingModelData")
  starpilot_car_state = _service(sm, "starpilotCarState")
  starpilot_plan = _service(sm, "starpilotPlan")
  events = _service(sm, "onroadEvents") or ()

  started = bool(getattr(device_state, "started", False))
  engaged = bool(getattr(selfdrive_state, "enabled", False))
  active = bool(getattr(selfdrive_state, "active", False))
  cruise = getattr(car_state, "cruiseState", None)
  conditional_chill, conditional_reason = _conditional_chill(params, params_memory)
  speed_limit_control = _param_bool(params, "SpeedLimitController")
  show_speed_limit = speed_limit_control or _param_bool(params, "ShowSpeedLimits")
  speed_limit = _finite(getattr(starpilot_plan, "slcSpeedLimit", 0.0))
  curve_control = _param_bool(params, "CurveSpeedController")
  curve_active = bool(getattr(starpilot_plan, "cscControllingSpeed", False))
  lead = getattr(radar_state, "leadOne", None)
  lead_present = bool(getattr(lead, "status", False))
  lat_active = bool(getattr(car_control, "latActive", False))
  long_active = bool(getattr(car_control, "longActive", False))
  long_control_state = _raw_enum(getattr(controls_state, "longControlState", 0))
  stopping = long_control_state == 2 or bool(getattr(longitudinal_plan, "shouldStop", False))
  alert_type = str(getattr(selfdrive_state, "alertType", ""))
  alert_status = _raw_enum(getattr(selfdrive_state, "alertStatus", 0))
  alert_present = bool(alert_type) or alert_status != 0
  always_on_lateral = not engaged and bool(getattr(starpilot_car_state, "alwaysOnLateralEnabled", False))
  big_model = _param_bool(params, "UsbGpuActive")
  big_model_loading = _param_bool(params, "UsbGpuLoading")
  pulse_and_glide = (
    bool(getattr(starpilot_car_state, "pulseAndGlide", False)) and
    bool(getattr(starpilot_plan, "pulseGlideCoasting", False))
  )
  overriding = _raw_enum(getattr(selfdrive_state, "state", 0)) == 4
  switchback = _param_bool(params_memory, "SwitchbackModeEnabled")

  flags = LiveFlags.CONNECTED
  flag_values = (
    (LiveFlags.STARTED, started),
    (LiveFlags.ENGAGED, engaged),
    (LiveFlags.ACTIVE, active),
    (LiveFlags.CRUISE_AVAILABLE, bool(getattr(cruise, "available", False))),
    (LiveFlags.CRUISE_ENABLED, bool(getattr(cruise, "enabled", False))),
    (LiveFlags.ALWAYS_ON_LATERAL, always_on_lateral),
    (LiveFlags.EXPERIMENTAL_MODE, bool(getattr(selfdrive_state, "experimentalMode", False))),
    (LiveFlags.CONDITIONAL_CHILL, conditional_chill),
    (LiveFlags.SPEED_LIMIT_CONTROL, speed_limit_control),
    (LiveFlags.SPEED_LIMIT_ACTIVE, show_speed_limit and speed_limit > 0.0),
    (LiveFlags.CURVE_CONTROL, curve_control),
    (LiveFlags.CURVE_CONTROL_ACTIVE, curve_active),
    (LiveFlags.LEAD_PRESENT, lead_present),
    (LiveFlags.LATERAL_ACTIVE, lat_active),
    (LiveFlags.LONGITUDINAL_ACTIVE, long_active),
    (LiveFlags.GAS_PRESSED, bool(getattr(car_state, "gasPressed", False))),
    (LiveFlags.BRAKE_PRESSED, bool(getattr(car_state, "brakePressed", False))),
    (LiveFlags.STOPPING, stopping),
    (LiveFlags.STANDSTILL, bool(getattr(car_state, "standstill", False))),
    (LiveFlags.BIG_MODEL, big_model),
    (LiveFlags.LATERAL_PAUSED, bool(getattr(starpilot_car_state, "pauseLateral", False))),
    (LiveFlags.TRAFFIC_MODE, bool(getattr(starpilot_car_state, "trafficModeEnabled", False))),
    (LiveFlags.SWITCHBACK_MODE, switchback),
    (LiveFlags.ALERT_PRESENT, alert_present),
    (LiveFlags.TELEMETRY_VALID, started and all(_sm_bool(sm, "valid", name) for name in ("carState", "selfdriveState", "carControl"))),
    (LiveFlags.FORCING_STOP, bool(getattr(starpilot_plan, "forcingStop", False))),
    (LiveFlags.TRACKING_LEAD, bool(getattr(starpilot_plan, "trackingLead", False))),
    (LiveFlags.PULSE_AND_GLIDE, pulse_and_glide),
    (LiveFlags.METRIC, _param_bool(params, "IsMetric")),
    (LiveFlags.OVERRIDING, overriding),
    (LiveFlags.RED_LIGHT, bool(getattr(starpilot_plan, "redLight", False))),
  )
  for flag, enabled in flag_values:
    if enabled:
      flags |= flag

  v_ego_cluster = _finite(getattr(car_state, "vEgoCluster", 0.0))
  vehicle_speed = v_ego_cluster if v_ego_cluster != 0.0 else _finite(getattr(car_state, "vEgo", 0.0))
  # vCruiseCluster and its fallback are published in kph.
  set_speed_kph = _finite(getattr(car_state, "vCruiseCluster", 0.0))
  if set_speed_kph == 0.0:
    set_speed_kph = _finite(getattr(controls_state, "vCruiseDEPRECATED", 0.0))
  set_speed = set_speed_kph * CV.KPH_TO_MS

  border_state = _border_state(started, selfdrive_state, starpilot_car_state, starpilot_plan, events, params_memory, switchback)
  model_source = ModelSource.BIG_LOADING if big_model_loading else ModelSource.BIG if big_model else ModelSource.SMALL
  model_key = _param_text(params, "DrivingModel")
  model_name = _param_text(params, "DrivingModelName")
  model_version = _param_text(params, "DrivingModelVersion")
  metadata_revision = _crc32(f"{model_key}\0{model_name}\0{model_version}\0{int(model_source)}")

  model_meta = getattr(model, "meta", None)
  return LiveSnapshot(
    flags=int(flags),
    vehicle_speed=max(0.0, vehicle_speed),
    set_speed=max(0.0, set_speed),
    acceleration=_finite(getattr(car_state, "aEgo", 0.0)),
    target_acceleration=_finite(getattr(longitudinal_plan, "aTarget", 0.0)),
    steering_angle=_finite(getattr(car_state, "steeringAngleDeg", 0.0)),
    desired_steering_angle=_lateral_desired_angle(controls_state, car_control),
    steering_torque=_finite(getattr(car_state, "steeringTorque", 0.0)),
    lead_distance=_finite(getattr(lead, "dRel", 0.0)) if lead_present else 0.0,
    lead_relative_speed=_finite(getattr(lead, "vRel", 0.0)) if lead_present else 0.0,
    lead_probability=_finite(getattr(lead, "modelProb", 0.0)) if lead_present else 0.0,
    speed_limit=max(0.0, speed_limit),
    speed_limit_offset=_finite(getattr(starpilot_plan, "slcSpeedLimitOffset", 0.0)),
    curve_target_speed=max(0.0, _finite(getattr(starpilot_plan, "cscSpeed", 0.0))),
    cruise_state=int(_cruise_state(cruise)),
    border_state=int(border_state),
    alert_status=alert_status,
    conditional_chill_reason=int(conditional_reason),
    driving_profile=_param_int(params, "AccelerationProfile"),
    longitudinal_profile=_raw_enum(getattr(selfdrive_state, "personality", _param_int(params, "LongitudinalPersonality", 1))),
    lane_change_state=_raw_enum(getattr(model_meta, "laneChangeState", 0)),
    lane_change_direction=_raw_enum(getattr(model_meta, "laneChangeDirection", 0)),
    long_control_state=long_control_state,
    model_source=int(model_source),
    border_color=BORDER_COLORS[border_state],
    alert_id=_crc32(alert_type) if alert_present else 0,
    metadata_revision=metadata_revision,
  )


@dataclass(frozen=True)
class HealthSnapshot:
  flags: int = 0
  cpu_usage: int = 0
  gpu_usage: int = 0
  memory_usage: int = 0
  free_storage: int = 0
  cpu_temp: float = 0.0
  gpu_temp: float = 0.0
  memory_temp: float = 0.0
  max_temp: float = 0.0
  intake_temp: float = 0.0
  thermal_status: int = THERMAL_STATUS_OK
  fan_speed: int = 0
  power_draw: float = 0.0
  som_power_draw: float = 0.0
  battery_reserve_wh: float = 0.0
  screen_brightness: int = 0
  network_type: int = 0
  network_strength: int = 0
  uptime_s: int = 0

  def pack(self, sequence: int, monotonic_ms: int) -> bytes:
    header = _pack_live_header(LIVE_FRAME_TYPE_HEALTH, sequence, monotonic_ms, self.flags)
    payload = struct.pack(
      "<4B5h2B3H4BI18x",
      min(100, max(0, int(self.cpu_usage))),
      min(100, max(0, int(self.gpu_usage))),
      min(100, max(0, int(self.memory_usage))),
      min(100, max(0, int(self.free_storage))),
      _scaled(self.cpu_temp, 10.0, -32768, 32767),
      _scaled(self.gpu_temp, 10.0, -32768, 32767),
      _scaled(self.memory_temp, 10.0, -32768, 32767),
      _scaled(self.max_temp, 10.0, -32768, 32767),
      _scaled(self.intake_temp, 10.0, -32768, 32767),
      min(255, max(0, int(self.thermal_status))),
      min(100, max(0, int(self.fan_speed))),
      _scaled(self.power_draw, 100.0, 0, 65535),
      _scaled(self.som_power_draw, 100.0, 0, 65535),
      _scaled(self.battery_reserve_wh, 10.0, 0, 65535),
      min(100, max(0, int(self.screen_brightness))),
      min(255, max(0, int(self.network_type))),
      min(255, max(0, int(self.network_strength))),
      0,
      max(0, int(self.uptime_s)) & 0xFFFFFFFF,
    )
    frame = header + payload
    if len(frame) != LIVE_FRAME_SIZE:
      raise AssertionError(f"Invalid health frame size: {len(frame)}")
    return frame


def build_health_snapshot(sm: Any, params: Params, monotonic_ns: int = 0) -> HealthSnapshot:
  device_state = _service(sm, "deviceState")
  started = bool(getattr(device_state, "started", False))
  offroad = _param_bool(params, "IsOffroad") if not started else False

  network_type = _raw_enum(getattr(device_state, "networkType", 0))
  metered = bool(getattr(device_state, "networkMetered", False))
  wifi = network_type == NETWORK_TYPE_WIFI
  ethernet = network_type == NETWORK_TYPE_ETHERNET
  cellular = network_type in NETWORK_TYPE_CELLULAR
  thermal_status = _raw_enum(getattr(device_state, "thermalStatus", THERMAL_STATUS_OK))
  fan_speed = int(_finite(getattr(device_state, "fanSpeedPercentDesired", 0)))
  free_storage = _finite(getattr(device_state, "freeSpacePercent", 0.0))
  battery_uwh = _finite(getattr(device_state, "carBatteryCapacityUwh", 0.0))
  ping_ns = _finite(getattr(device_state, "lastAthenaPingTime", 0.0))
  cloud_fresh = ping_ns > 0 and 0 <= (monotonic_ns - ping_ns) < LIVE_ATHENA_FRESH_S * 1e9

  flags = HealthFlags(0)
  flag_values = (
    (HealthFlags.ONROAD, started),
    (HealthFlags.OFFROAD, not started and offroad),
    (HealthFlags.NETWORK_METERED, metered),
    (HealthFlags.WIFI_CONNECTED, wifi),
    (HealthFlags.ETHERNET_CONNECTED, ethernet),
    (HealthFlags.CELLULAR_CONNECTED, cellular),
    (HealthFlags.LOCAL_NON_METERED_LINK, (wifi or ethernet) and not metered),
    (HealthFlags.THERMAL_OK, thermal_status == THERMAL_STATUS_OK),
    (HealthFlags.THERMAL_OVERHEATED, thermal_status == THERMAL_STATUS_OVERHEATED),
    (HealthFlags.THERMAL_CRITICAL, thermal_status == THERMAL_STATUS_CRITICAL),
    (HealthFlags.FAN_ACTIVE, fan_speed > 0),
    (HealthFlags.LOW_STORAGE, free_storage < LIVE_LOW_STORAGE_PERCENT),
    (HealthFlags.CLOUD_PINGED, cloud_fresh),
  )
  for flag, enabled in flag_values:
    if enabled:
      flags |= flag

  return HealthSnapshot(
    flags=int(flags),
    cpu_usage=round(_max_finite(getattr(device_state, "cpuUsagePercent", ()))),
    gpu_usage=int(_finite(getattr(device_state, "gpuUsagePercent", 0))),
    memory_usage=int(_finite(getattr(device_state, "memoryUsagePercent", 0))),
    free_storage=round(free_storage),
    cpu_temp=_max_finite(getattr(device_state, "cpuTempC", ())),
    gpu_temp=_max_finite(getattr(device_state, "gpuTempC", ())),
    memory_temp=_finite(getattr(device_state, "memoryTempC", 0.0)),
    max_temp=_finite(getattr(device_state, "maxTempC", 0.0)),
    intake_temp=_finite(getattr(device_state, "intakeTempC", 0.0)),
    thermal_status=thermal_status,
    fan_speed=fan_speed,
    power_draw=_finite(getattr(device_state, "powerDrawW", 0.0)),
    som_power_draw=_finite(getattr(device_state, "somPowerDrawW", 0.0)),
    battery_reserve_wh=battery_uwh / 1e6,
    screen_brightness=int(_finite(getattr(device_state, "screenBrightnessPercent", 0))),
    network_type=network_type,
    network_strength=_raw_enum(getattr(device_state, "networkStrength", 0)),
    uptime_s=int(monotonic_ns // 1_000_000_000),
  )


def live_metadata(params: Params, current: dict[str, Any] | None = None) -> dict[str, Any]:
  current = current or {
    "alert": {"id": 0, "type": "", "text1": "", "text2": "", "status": 0},
    "speed_limit_source": "",
  }
  return {
    "model": {
      "key": _param_text(params, "DrivingModel", 32),
      "name": _param_text(params, "DrivingModelName", 48),
      "version": _param_text(params, "DrivingModelVersion", 16),
      "big_model": _param_bool(params, "UsbGpuActive"),
    },
    "alert": current["alert"],
    "speed_limit_source": current["speed_limit_source"],
  }


def build_live_details(sm: Any) -> dict[str, Any]:
  selfdrive_state = _service(sm, "selfdriveState")
  starpilot_plan = _service(sm, "starpilotPlan")
  alert_type = str(getattr(selfdrive_state, "alertType", ""))
  alert_status = _raw_enum(getattr(selfdrive_state, "alertStatus", 0))
  return {
    "alert": {
      "id": _crc32(alert_type) if alert_type or alert_status else 0,
      "type": alert_type[:40],
      "text1": str(getattr(selfdrive_state, "alertText1", ""))[:32],
      "text2": str(getattr(selfdrive_state, "alertText2", ""))[:32],
      "status": alert_status,
    },
    "speed_limit_source": str(getattr(starpilot_plan, "slcSpeedLimitSource", ""))[:16],
  }


class LiveTelemetryPublisher:
  SERVICES = (
    "deviceState", "carState", "selfdriveState", "carControl", "controlsState", "radarState",
    "longitudinalPlan", "drivingModelData", "starpilotCarState", "starpilotPlan", "onroadEvents",
  )

  def __init__(self, callback, params: Params, params_memory: Params, sm_factory=messaging.SubMaster,
               monotonic=time.monotonic):
    self._callback = callback
    self.params = params
    self.params_memory = params_memory
    self._sm_factory = sm_factory
    self._monotonic = monotonic
    self._stop = threading.Event()
    self._thread: threading.Thread | None = None
    self._sequence = 0
    self._params_cache: dict[str, Any] = {}
    self._params_cache_time: float | None = None
    self._details_lock = threading.Lock()
    self._details = build_live_details({})

  def start(self) -> None:
    if self._thread is not None and self._thread.is_alive():
      return
    self._stop.clear()
    self._thread = threading.Thread(target=self._run, name="ble_live_publisher", daemon=True)
    self._thread.start()

  def close(self) -> None:
    self._stop.set()
    if self._thread is not None and self._thread.is_alive():
      self._thread.join(timeout=1.0)

  def _emit(self, frame: bytes) -> None:
    self._sequence = (self._sequence + 1) & 0xFFFF
    self._callback(frame)

  def _cached_params(self, monotonic: float) -> dict[str, Any]:
    if self._params_cache_time is None or monotonic - self._params_cache_time >= LIVE_PARAMS_REFRESH_INTERVAL_S:
      self._params_cache = {
        "ConditionalChill": _param_bool(self.params, "ConditionalChill"),
        "SpeedLimitController": _param_bool(self.params, "SpeedLimitController"),
        "ShowSpeedLimits": _param_bool(self.params, "ShowSpeedLimits"),
        "CurveSpeedController": _param_bool(self.params, "CurveSpeedController"),
        "UsbGpuActive": _param_bool(self.params, "UsbGpuActive"),
        "UsbGpuLoading": _param_bool(self.params, "UsbGpuLoading"),
        "IsMetric": _param_bool(self.params, "IsMetric"),
        "DrivingModel": _param_text(self.params, "DrivingModel"),
        "DrivingModelName": _param_text(self.params, "DrivingModelName"),
        "DrivingModelVersion": _param_text(self.params, "DrivingModelVersion"),
        "AccelerationProfile": _param_int(self.params, "AccelerationProfile"),
        "LongitudinalPersonality": _param_int(self.params, "LongitudinalPersonality", 1),
        "IsOffroad": _param_bool(self.params, "IsOffroad"),
      }
      self._params_cache_time = monotonic
    return self._params_cache

  def publish_once(self, sm: Any) -> bytes:
    monotonic = self._monotonic()
    snapshot = build_live_snapshot(sm, self._cached_params(monotonic), self.params_memory)
    frame = snapshot.pack(self._sequence, round(monotonic * 1000.0))
    details = build_live_details(sm)
    with self._details_lock:
      self._details = details
    self._emit(frame)
    return frame

  def publish_health_once(self, sm: Any) -> bytes:
    monotonic = self._monotonic()
    snapshot = build_health_snapshot(sm, self._cached_params(monotonic), round(monotonic * 1e9))
    frame = snapshot.pack(self._sequence, round(monotonic * 1000.0))
    self._emit(frame)
    return frame

  def details(self) -> dict[str, Any]:
    with self._details_lock:
      return {
        "alert": dict(self._details["alert"]),
        "speed_limit_source": self._details["speed_limit_source"],
      }

  def _run(self) -> None:
    try:
      sm = self._sm_factory(list(self.SERVICES))
      period = 1.0 / LIVE_FRAME_RATE_HZ
      next_update = self._monotonic()
      tick = 0
      while not self._stop.is_set():
        sm.update(0)
        self.publish_once(sm)
        if tick % LIVE_HEALTH_TICK_DIVISOR == 0:
          self.publish_health_once(sm)
        tick += 1
        next_update += period
        delay = max(0.0, next_update - self._monotonic())
        if delay == 0.0:
          next_update = self._monotonic()
          delay = LIVE_OVERRUN_SLEEP_S
        if self._stop.wait(delay):
          return
    except Exception:
      cloudlog.exception("Bluetooth live telemetry publisher failed")
