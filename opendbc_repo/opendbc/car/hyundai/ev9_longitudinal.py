from dataclasses import dataclass
from enum import IntEnum

from opendbc.car import CanData


EV9_LONG_TEST_ENABLED_PARAM = "KiaEv9LongitudinalTestEnabled"
EV9_LONG_TEST_STAGE_PARAM = "KiaEv9LongitudinalTestStage"
EV9_LONG_TEST_PROBE_MODE_PARAM = "KiaEv9LongitudinalProbeMode"
EV9_DTC_CAPTURE_PARAM = "KiaEv9DtcCaptureEnabled"
EV9_CRUISE_MAIN_STATE_PARAM = "KiaEv9CruiseMainStateEnabled"
EV9_SOFT_DRIVER_STEERING_OVERRIDE_PARAM = "KiaEv9SoftDriverSteeringOverrideEnabled"
EV9_CLUSTER_HUD_PARAM = "KiaEv9ClusterHudEnabled"
EV9_CLUSTER_OBJECTS_PARAM = "KiaEv9ClusterObjectsEnabled"
EV9_CLUSTER_ALTERNATE_LEAD_PARAM = "KiaEv9ClusterAlternateLeadEnabled"
EV9_REAR_BSM_CLUSTER_FALLBACK_PARAM = "KiaEv9RearBsmClusterFallbackEnabled"
EV9_DTC_CAPTURE_TARGETS = (0x7C4, 0x7C6, 0x7D0, 0x7D4)
EV9_DTC_CAPTURE_SLOT_FRAMES = 100


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
EV9_ACTUATION_ACCEL_MIN = -0.50
EV9_ACTUATION_ACCEL_MAX = 0.30
EV9_ACTUATION_MAX_SPEED = 5.0


class EV9ActuationAbortReason(IntEnum):
  NONE = 0
  NOT_DRIVE = 1
  BRAKE_PRESSED = 2
  GAS_PRESSED = 3
  CAN_INVALID = 4
  RADAR_INVALID = 5
  PANDA_FAULT = 6
  SPEED_LIMIT = 7


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
  ACTUATION = 17            # Explicitly permit tightly bounded acceleration/braking


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
  """Force a non-actuating SCC frame until the final explicit test stage."""
  if config.actuation_allowed and actuation_permitted:
    limited_accel = max(EV9_ACTUATION_ACCEL_MIN, min(accel, EV9_ACTUATION_ACCEL_MAX))
    return enabled, limited_accel, stopping, gas_override
  return False, 0.0, False, False


def ev9_actuation_abort_reason(config: EV9LongitudinalTestConfig, control_requested: bool, was_active: bool,
                               drive_gear: bool, brake_pressed: bool, gas_pressed: bool, can_valid: bool,
                               radar_valid: bool, panda_faulted: bool, v_ego: float) -> EV9ActuationAbortReason:
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
  if v_ego > EV9_ACTUATION_MAX_SPEED:
    return EV9ActuationAbortReason.SPEED_LIMIT
  return EV9ActuationAbortReason.NONE
