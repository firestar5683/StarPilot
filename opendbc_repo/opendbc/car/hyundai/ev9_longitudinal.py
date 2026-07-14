from dataclasses import dataclass
from enum import IntEnum
import math

import numpy as np

from opendbc.car import CanData
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai.values import CarControllerParams


EV9_LONG_TEST_ENABLED_PARAM = "KiaEv9LongitudinalTestEnabled"
EV9_LONG_TEST_STAGE_PARAM = "KiaEv9LongitudinalTestStage"
EV9_LONG_TEST_PROBE_MODE_PARAM = "KiaEv9LongitudinalProbeMode"
EV9_DTC_CAPTURE_PARAM = "KiaEv9DtcCaptureEnabled"
EV9_CRUISE_MAIN_STATE_PARAM = "KiaEv9CruiseMainStateEnabled"
EV9_SOFT_DRIVER_STEERING_OVERRIDE_PARAM = "KiaEv9SoftDriverSteeringOverrideEnabled"
EV9_CLUSTER_HUD_PARAM = "KiaEv9ClusterHudEnabled"
EV9_CLUSTER_OBJECTS_PARAM = "KiaEv9ClusterObjectsEnabled"
EV9_CLUSTER_OBJECTS_ON_MAIN_PARAM = "KiaEv9ClusterObjectsOnMainEnabled"
EV9_CLUSTER_ALTERNATE_LEAD_PARAM = "KiaEv9ClusterAlternateLeadEnabled"
EV9_CLUSTER_SPEED_LIMIT_PARAM = "KiaEv9ClusterSpeedLimitEnabled"
EV9_CLUSTER_MAP_SPEED_LIMIT_FALLBACK_PARAM = "KiaEv9ClusterMapSpeedLimitFallbackEnabled"
EV9_NEUTRAL_LANE_CURVATURE_PARAM = "KiaEv9NeutralLaneCurvatureEnabled"
EV9_REAR_BSM_CLUSTER_FALLBACK_PARAM = "KiaEv9RearBsmClusterFallbackEnabled"
EV9_RAW_BSM_RECONSTRUCTION_PARAM = "KiaEv9RawBsmReconstructionEnabled"
EV9_SOFTWARE_BSM_PARAM = "KiaEv9SoftwareBsmEnabled"
EV9_SOFTWARE_BSM_COMMA_OUTPUT_PARAM = "KiaEv9SoftwareBsmCommaOutputEnabled"
EV9_SOFTWARE_BSM_VEHICLE_OUTPUT_PARAM = "KiaEv9SoftwareBsmVehicleOutputEnabled"
EV9_SOFTWARE_BSM_WARNING_OUTPUT_PARAM = "KiaEv9SoftwareBsmWarningOutputEnabled"
EV9_DIRECT_ANGLE_COMMAND_PARAM = "KiaEv9DirectAngleCommandEnabled"
EV9_DTC_CAPTURE_TARGETS = (0x7C4, 0x7C6, 0x7D0, 0x7D4)
EV9_DTC_CAPTURE_SLOT_FRAMES = 100
EV9_CLUSTER_MAP_SPEED_LIMIT_SOURCES = frozenset(("Map Data", "Mapbox", "Vision"))


@dataclass(frozen=True)
class Ev9BsmWarningOutput:
  mirror_warning_active: bool = False
  flash_phase: int = 0
  sound_active: bool = False


class Ev9BsmWarningAnimator:
  """Reproduce the stock EV9 mirror and one-shot audible/haptic envelope."""

  FLASH_SAMPLES = 20
  FLASH_ON_SAMPLES = 16
  SOUND_SAMPLES = 36

  def __init__(self) -> None:
    self.flash_phase = 0
    self.mirror_warning_active = False
    self.escalated_prev = False
    self.sound_remaining = 0
    self.sound_armed = True

  def update(self, escalated: bool, blinker: bool, sound_enabled: bool) -> Ev9BsmWarningOutput:
    if not blinker:
      self.flash_phase = 0
      self.mirror_warning_active = False
      self.escalated_prev = False
      self.sound_remaining = 0
      self.sound_armed = True
      return Ev9BsmWarningOutput()

    rising = escalated and not self.escalated_prev
    if rising:
      self.flash_phase = 0
      self.mirror_warning_active = True
      if self.sound_armed and sound_enabled:
        self.sound_remaining = self.SOUND_SAMPLES
        self.sound_armed = False
    elif escalated:
      self.flash_phase = (self.flash_phase + 1) % self.FLASH_SAMPLES
      self.mirror_warning_active = True
    elif self.mirror_warning_active and self.flash_phase < self.FLASH_ON_SAMPLES - 1:
      # Stock completes the current 0.8-second ON pulse after BCW clears.
      self.flash_phase += 1
    else:
      self.flash_phase = 0
      self.mirror_warning_active = False

    self.escalated_prev = escalated
    sound_active = bool(sound_enabled and self.sound_remaining > 0)
    if self.sound_remaining > 0:
      self.sound_remaining -= 1
    return Ev9BsmWarningOutput(self.mirror_warning_active, self.flash_phase, sound_active)


def ev9_cluster_display_speed_limit_raw(camera_raw: int | float, fallback_enabled: bool, plan_valid: bool,
                                        plan_source: str, plan_speed_limit: float, is_metric: bool) -> int:
  """Select an EV9 cluster speed-limit value without feeding it back into planning.

  The camera's cluster-display value remains authoritative. Map/vision data is
  used only when the camera explicitly reports no recognition (zero).
  """
  try:
    camera_speed_limit = int(camera_raw)
  except (TypeError, ValueError):
    camera_speed_limit = 0

  if camera_speed_limit != 0:
    return camera_speed_limit
  if not fallback_enabled or not plan_valid or plan_source not in EV9_CLUSTER_MAP_SPEED_LIMIT_SOURCES:
    return 0

  try:
    speed_limit_ms = float(plan_speed_limit)
  except (TypeError, ValueError):
    return 0
  if not math.isfinite(speed_limit_ms) or speed_limit_ms <= 0.0:
    return 0

  unit_factor = CV.MS_TO_KPH if is_metric else CV.MS_TO_MPH
  return min(max(round(speed_limit_ms * unit_factor), 1), 252)


def ev9_default_enabled_param(params, key: str) -> bool:
  """Read a default-on feature before manager has materialized its default."""
  value = params.get(key)
  return value is None or params.get_bool(key)


def update_ev9_cruise_main_latch(current: bool, previous_button: int, button_samples: list[int], enabled: bool) -> bool:
  """Toggle the software cruise-main state once for every physical rising edge."""
  if not enabled:
    return True

  previous = bool(previous_button)
  for sample in button_samples:
    pressed = bool(sample)
    if pressed and not previous:
      current = not current
    previous = pressed
  return current


class EV9LongitudinalProbeMode(IntEnum):
  COMMUNICATION_CONTROL = 0
  DIAGNOSTIC_SESSION_ONLY = 1
  TX_DISABLE_ALL_MESSAGE_TYPES = 2
  RX_TX_DISABLE_NORMAL = 3
  RESET_TX_DISABLE_ALL_MESSAGE_TYPES = 4
  FULL_DISABLE_THEN_RX_ENABLE = 5


EV9_LONG_PROBE_HOLD_SECONDS = 5.0
EV9_ACTUATION_JERK_LOWER = 0.7
EV9_ACTUATION_JERK_UPPER = 0.7
EV9_HOLD_JERK_UPPER = 1.5
EV9_STARTING_JERK_UPPER = 0.5
EV9_STOPPING_JERK_UPPER = 1.0
EV9_SCC_CONTROL_FREQUENCY = 50.0
EV9_STOP_REQUEST_SPEED = 0.5
EV9_STANDSTILL_DELAY_FRAMES = 178
EV9_STOP_RELEASE_DELAY_FRAMES = 6
EV9_START_ACCEL = 0.20
EV9_STARTING_SPEED = 0.5
# StopReq owns the final handoff at 0.5 m/s; the lower points only provide a
# continuous, fail-soft extrapolation if the state transition arrives late.
EV9_STOP_BRAKE_CAP_SPEED_BP = (0.0, 0.46, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
EV9_STOP_BRAKE_CAP_ACCEL_V = (0.0, -0.69, -0.70, -0.87, -1.05, -1.35, -1.65, -2.10, -2.20)


class EV9ActuationAbortReason(IntEnum):
  NONE = 0
  NOT_DRIVE = 1
  BRAKE_PRESSED = 2
  GAS_PRESSED = 3
  CAN_INVALID = 4
  RADAR_INVALID = 5
  PANDA_FAULT = 6
  STOCK_SCC_BASELINE_MISSING = 7


@dataclass(frozen=True)
class EV9LongitudinalStopState:
  stop_request: bool = False
  cruise_standstill: bool = False
  stop_request_frames: int = 0
  release_frames: int = 0


def update_ev9_longitudinal_stop_state(state: EV9LongitudinalStopState, enabled: bool,
                                        stopping: bool, v_ego: float) -> EV9LongitudinalStopState:
  """Reproduce the stock EV9 stop/hold/release timing captured in route b4."""
  if not enabled:
    return EV9LongitudinalStopState()

  if stopping:
    if not state.stop_request and v_ego > EV9_STOP_REQUEST_SPEED:
      return EV9LongitudinalStopState()
    frames = state.stop_request_frames + 1 if state.stop_request else 0
    return EV9LongitudinalStopState(
      stop_request=True,
      cruise_standstill=frames >= EV9_STANDSTILL_DELAY_FRAMES,
      stop_request_frames=frames,
    )

  if state.stop_request:
    release_frames = state.release_frames + 1
    if release_frames <= EV9_STOP_RELEASE_DELAY_FRAMES:
      return EV9LongitudinalStopState(
        stop_request=True,
        cruise_standstill=False,
        stop_request_frames=state.stop_request_frames,
        release_frames=release_frames,
      )

  return EV9LongitudinalStopState()


def ev9_communication_control_requests(probe_mode: EV9LongitudinalProbeMode) -> tuple[bytes, bytes]:
  """Return the bounded probe and matching restore requests.

  Communication type 0x03 covers normal and network-management messages. The
  broad probe uses control type 0x03, matching sunnypilot without suppressing
  the diagnostic response.
  """
  if probe_mode in (EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES,
                    EV9LongitudinalProbeMode.RESET_TX_DISABLE_ALL_MESSAGE_TYPES,
                    EV9LongitudinalProbeMode.FULL_DISABLE_THEN_RX_ENABLE):
    return b"\x28\x01\x03", b"\x28\x00\x03"
  if probe_mode == EV9LongitudinalProbeMode.RX_TX_DISABLE_NORMAL:
    return b"\x28\x03\x01", b"\x28\x00\x01"
  return b"\x28\x01\x01", b"\x28\x00\x01"


def ev9_dtc_capture_messages(elapsed_frame: int, bus: int) -> tuple[list[CanData], bool]:
  """Build a parked, one-shot read-DTC sequence on the controller publisher.

  ADAS 0x730 is deliberately excluded so its active CommunicationControl
  session is never disturbed. Each remaining ECU gets an ISO-TP request and a
  zero-separation flow-control frame in its own one-second slot.
  """
  if elapsed_frame < 0:
    return [], False

  target_index, slot_frame = divmod(elapsed_frame, EV9_DTC_CAPTURE_SLOT_FRAMES)
  if target_index >= len(EV9_DTC_CAPTURE_TARGETS):
    return [], True

  addr = EV9_DTC_CAPTURE_TARGETS[target_index]
  if slot_frame == 0:
    return [CanData(addr, b"\x03\x19\x02\xFF\x00\x00\x00\x00", bus)], False
  if slot_frame == 2:
    return [CanData(addr, b"\x30\x00\x00\x00\x00\x00\x00\x00", bus)], False
  return [], False


class EV9LongitudinalTestStage(IntEnum):
  """Cumulative parked-test stages for replacing EV9 ADAS_DRV transmissions."""

  DISABLED = 0
  SHADOW = 1
  TX_DISABLE = 2
  RADAR_HEARTBEAT = 3       # 0x100
  ADRV_160 = 4              # 0x160
  ADRV_1DA = 5              # 0x1DA
  ADRV_1EA = 6              # 0x1EA
  ADRV_200 = 7              # 0x200
  ADRV_345 = 8              # 0x345
  SCC_INACTIVE = 9          # 0x1A0, forced ACCMode=0 and zero acceleration
  CCNC_STATUS = 10          # 0x161/0x162, neutral parked display state
  BSM_STATUS = 11           # 0x1BA/0x1E5, neutral blind-spot status
  LFAHDA_STATUS = 12        # 0x1E0, neutral legacy cluster status
  ADRV_38C = 13             # 0x38C, captured 5 Hz ADAS status
  ADRV_57A = 14             # 0x57A, captured 10 Hz raw ADAS status
  STEERING_KEEPALIVE = 15   # 0x12A/0xCB, parked inactive steering status
  ACTUATION_PREFLIGHT = 16  # Exercise health/abort gates while SCC remains inactive
  ACTUATION = 17            # Explicitly permit shared-safety acceleration/braking


@dataclass(frozen=True)
class EV9LongitudinalTestConfig:
  enabled: bool = False
  stage: EV9LongitudinalTestStage = EV9LongitudinalTestStage.DISABLED
  probe_mode: EV9LongitudinalProbeMode = EV9LongitudinalProbeMode.COMMUNICATION_CONTROL

  @property
  def armed(self) -> bool:
    return self.enabled and self.stage >= EV9LongitudinalTestStage.TX_DISABLE

  @property
  def actuation_allowed(self) -> bool:
    return self.armed and self.stage >= EV9LongitudinalTestStage.ACTUATION

  @property
  def actuation_test_armed(self) -> bool:
    return self.armed and self.stage >= EV9LongitudinalTestStage.ACTUATION_PREFLIGHT

  @property
  def persistent_suppression_allowed(self) -> bool:
    """Allow a controller-maintained disable only for the validated safe variant.

    TX_DISABLE remains a bounded probe. The first persistent stage recreates
    only the radar heartbeat; SCC_CONTROL is still withheld until SCC_INACTIVE.
    """
    return self.enabled and self.probe_mode in (EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES,
                                                 EV9LongitudinalProbeMode.RESET_TX_DISABLE_ALL_MESSAGE_TYPES,
                                                 EV9LongitudinalProbeMode.FULL_DISABLE_THEN_RX_ENABLE) and \
      self.stage >= EV9LongitudinalTestStage.RADAR_HEARTBEAT


def should_send_ev9_direct_angle_command(config: EV9LongitudinalTestConfig, feature_enabled: bool,
                                         drive_gear: bool, lat_active: bool) -> bool:
  """Gate the downstream 0xCB command needed when ADAS translation is disabled."""
  return feature_enabled and config.armed and config.stage >= EV9LongitudinalTestStage.STEERING_KEEPALIVE and \
    drive_gear and lat_active


EV9_REPLAY_STAGE_BY_ADDRESS: dict[int, EV9LongitudinalTestStage] = {
  0x160: EV9LongitudinalTestStage.ADRV_160,
  0x1DA: EV9LongitudinalTestStage.ADRV_1DA,
  0x1EA: EV9LongitudinalTestStage.ADRV_1EA,
  0x200: EV9LongitudinalTestStage.ADRV_200,
  0x345: EV9LongitudinalTestStage.ADRV_345,
  0x161: EV9LongitudinalTestStage.CCNC_STATUS,
  0x162: EV9LongitudinalTestStage.CCNC_STATUS,
  0x1BA: EV9LongitudinalTestStage.BSM_STATUS,
  0x1E5: EV9LongitudinalTestStage.BSM_STATUS,
  0x1E0: EV9LongitudinalTestStage.LFAHDA_STATUS,
  0x38C: EV9LongitudinalTestStage.ADRV_38C,
  0x57A: EV9LongitudinalTestStage.ADRV_57A,
}


def parse_ev9_longitudinal_test_stage(value: int) -> EV9LongitudinalTestStage:
  try:
    return EV9LongitudinalTestStage(value)
  except ValueError:
    return EV9LongitudinalTestStage.DISABLED


def parse_ev9_longitudinal_probe_mode(value: int) -> EV9LongitudinalProbeMode:
  try:
    return EV9LongitudinalProbeMode(value)
  except ValueError:
    return EV9LongitudinalProbeMode.COMMUNICATION_CONTROL


def get_ev9_longitudinal_test_config(params=None) -> EV9LongitudinalTestConfig:
  if params is None:
    from openpilot.common.params import Params
    params = Params()

  try:
    return EV9LongitudinalTestConfig(
      enabled=params.get_bool(EV9_LONG_TEST_ENABLED_PARAM),
      stage=parse_ev9_longitudinal_test_stage(params.get_int(EV9_LONG_TEST_STAGE_PARAM)),
      probe_mode=parse_ev9_longitudinal_probe_mode(params.get_int(EV9_LONG_TEST_PROBE_MODE_PARAM)),
    )
  except Exception:
    # Source-tree tests may run against a params extension built before these
    # developer-only keys were added. Fail closed in that case.
    return EV9LongitudinalTestConfig()


def advance_ev9_longitudinal_support_stage(current: EV9LongitudinalTestConfig,
                                            requested: EV9LongitudinalTestConfig) -> EV9LongitudinalTestConfig:
  """Permit monotonic live changes without crossing either safety boundary.

  Entering SCC_INACTIVE still requires a fresh controller instance (an ignition
  cycle in the parked test). Once that non-actuating SCC stage is already
  latched, the remaining status-only frames may be added live. Neither
  ACTUATION_PREFLIGHT nor ACTUATION is reachable through this helper.
  """
  before_scc = current.stage <= requested.stage <= EV9LongitudinalTestStage.ADRV_345
  after_scc = EV9LongitudinalTestStage.SCC_INACTIVE <= current.stage <= requested.stage <= \
    EV9LongitudinalTestStage.STEERING_KEEPALIVE
  valid = current.persistent_suppression_allowed and requested.persistent_suppression_allowed and (before_scc or after_scc)
  return requested if valid else current


def filter_ev9_adrv_replay_messages(stage: EV9LongitudinalTestStage, messages: list[CanData]) -> list[CanData]:
  """Keep only cumulative, explicitly staged ADAS_DRV support frames.

  0x51 is intentionally excluded: it was not present in the EV9 stock reference
  route and must not be introduced until separately captured and validated.
  """
  return [msg for msg in messages
          if msg[0] in EV9_REPLAY_STAGE_BY_ADDRESS and stage >= EV9_REPLAY_STAGE_BY_ADDRESS[msg[0]]]


def ev9_longitudinal_test_scc_command(config: EV9LongitudinalTestConfig, enabled: bool, accel: float,
                                      stopping: bool, gas_override: bool,
                                      actuation_permitted: bool = True) -> tuple[bool, float, bool, bool]:
  """Build the bounded EV9 actuation request for the explicit test stage.

  The EV9-specific controller converts the generic stopping state into the
  route-backed stop/hold/restart sequence while preserving the common Hyundai
  CAN-FD safety envelope.
  """
  if config.actuation_allowed and actuation_permitted:
    limited_accel = max(CarControllerParams.ACCEL_MIN, min(accel, CarControllerParams.ACCEL_MAX))
    return enabled, limited_accel, stopping, gas_override
  return False, 0.0, False, False


def ev9_limit_stopping_accel(accel_raw: float, v_ego: float) -> float:
  """Cap low-speed braking with the taper measured in the stock EV9 route."""
  brake_cap = float(np.interp(max(v_ego, 0.0), EV9_STOP_BRAKE_CAP_SPEED_BP, EV9_STOP_BRAKE_CAP_ACCEL_V))
  return min(0.0, max(accel_raw, brake_cap))


def ev9_rate_limit_accel(accel_last: float, accel_raw: float, starting: bool = False,
                         stopping: bool = False) -> float:
  """Apply EV9-specific launch, normal, and stopping-release ramps at 50 Hz."""
  if starting:
    jerk_upper = EV9_STARTING_JERK_UPPER
  elif stopping:
    jerk_upper = EV9_STOPPING_JERK_UPPER
  else:
    jerk_upper = EV9_ACTUATION_JERK_UPPER
  return max(accel_last - EV9_ACTUATION_JERK_LOWER / EV9_SCC_CONTROL_FREQUENCY,
             min(accel_raw, accel_last + jerk_upper / EV9_SCC_CONTROL_FREQUENCY))


def ev9_jerk_upper(stop_request: bool, starting: bool, stopping: bool = False) -> float:
  """Select route-backed hold/stop jerk without changing other platforms."""
  if stop_request:
    return EV9_HOLD_JERK_UPPER
  if starting:
    return EV9_STARTING_JERK_UPPER
  return EV9_STOPPING_JERK_UPPER if stopping else EV9_ACTUATION_JERK_UPPER


def ev9_actuation_abort_reason(config: EV9LongitudinalTestConfig, control_requested: bool, was_active: bool,
                               drive_gear: bool, brake_pressed: bool, gas_pressed: bool, can_valid: bool,
                               radar_valid: bool, panda_faulted: bool,
                               scc_baseline_valid: bool = True) -> EV9ActuationAbortReason:
  """Return an ignition-latching reason to block the bounded EV9 actuation test."""
  if not config.actuation_test_armed or not (control_requested or was_active):
    return EV9ActuationAbortReason.NONE
  if not drive_gear:
    return EV9ActuationAbortReason.NOT_DRIVE
  if brake_pressed:
    return EV9ActuationAbortReason.BRAKE_PRESSED
  if gas_pressed:
    return EV9ActuationAbortReason.GAS_PRESSED
  if not can_valid:
    return EV9ActuationAbortReason.CAN_INVALID
  if not radar_valid:
    return EV9ActuationAbortReason.RADAR_INVALID
  if panda_faulted:
    return EV9ActuationAbortReason.PANDA_FAULT
  if not scc_baseline_valid:
    return EV9ActuationAbortReason.STOCK_SCC_BASELINE_MISSING
  return EV9ActuationAbortReason.NONE
