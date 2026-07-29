from dataclasses import dataclass

import numpy as np
from opendbc.can import CANPacker
from opendbc.car import Bus, DT_CTRL, make_tester_present_msg, rate_limit, structs
from opendbc.car.common.filter_simple import FirstOrderFilter
from opendbc.car.lateral import apply_driver_steer_torque_limits, apply_steer_angle_limits_vm, common_fault_avoidance, get_max_angle_delta_vm, get_max_angle_vm
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.hyundai import hyundaicanfd, hyundaican
from opendbc.car.hyundai.carstate import CANFD_NATIVE_BLINDSPOT_STALE_NS, EV9_RAW_BLINDSPOT_STALE_NS
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.ev9_longitudinal import EV9_ACTUATION_JERK_LOWER, EV9_ACTUATION_JERK_UPPER, \
                                                   EV9LongitudinalStopState, \
                                                   EV9ActuationAbortReason, \
                                                   ev9_actuation_abort_reason, \
                                                   ev9_longitudinal_scc_command, \
                                                   shape_ev9_longitudinal_accel, update_ev9_longitudinal_stop_state, \
                                                   filter_ev9_adrv_replay_messages, \
                                                   should_send_ev9_direct_angle_command
from opendbc.car.hyundai.values import HyundaiFlags, Buttons, CarControllerParams, CAR, CANFD_ANGLE_LONGITUDINAL_CAR, \
                                        CANFD_RADAR_LIVE_LONGITUDINAL_CAR, \
                                        kia_ev6_gt_line_longitudinal_tuning
from opendbc.car.interfaces import CarControllerBase
from opendbc.car.carlog import carlog
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.params import Params

VisualAlert = structs.CarControl.HUDControl.VisualAlert
LongCtrlState = structs.CarControl.Actuators.LongControlState

# EPS faults if you apply torque while the steering angle is above 90 degrees for more than 1 second
# All slightly below EPS thresholds to avoid fault
MAX_ANGLE = 85
MAX_ANGLE_FRAMES = 89
MAX_ANGLE_CONSECUTIVE_FRAMES = 2
CANFD_BLINDSPOT_STATUS_STALE_NS = 200_000_000
CANFD_CAMERA_LEAD_STALE_NS = 300_000_000
CANFD_LEAD_MIN_DISTANCE = 0.1
CANFD_FALLBACK_LEAD_DISTANCE = 20.0
HYUNDAI_DASH_DISENGAGE_BLINK_TIME = 1.0
HYUNDAI_CANFD_SCC_ACCEL_STEP = 5.0 / 50.0
HYUNDAI_CANFD_SCC_DECEL_STEP = 12.5 / 50.0
IONIQ_6_RESPONSE_MULTIPLIER = 1.2
IONIQ_6_CANFD_SCC_ACCEL_STEP = (6.0 / 50.0) * IONIQ_6_RESPONSE_MULTIPLIER
IONIQ_6_CANFD_SCC_DECEL_STEP = (15.0 / 50.0) * IONIQ_6_RESPONSE_MULTIPLIER
GENESIS_G90_STOP_HOLD_SPEED_BP = [0.0, 0.03, 0.08, 0.16, 0.3, 0.5, 0.8, 1.2, 2.0, 3.0]
GENESIS_G90_STOP_HOLD_ACCEL_V = [-0.10, -0.10, -0.12, -0.18, -0.30, -0.50, -0.75, -1.00, -1.40, -1.80]
GENESIS_G90_STOP_HOLD_RELAX_SPEED_BP = [0.0, 0.08, 0.16, 0.3, 0.5, 0.8, 1.2, 2.0, 3.0]
GENESIS_G90_STOP_HOLD_RELAX_STEP_V = [0.10, 0.10, 0.08, 0.06, 0.04, 0.035, 0.03, 0.022, 0.018]
GENESIS_G90_RELEASE_SPEED_BP = [0.0, 0.3, 0.6]
GENESIS_G90_RELEASE_ACCEL_STEP_V = [0.05, 0.07, 0.11]
GENESIS_G90_RELEASE_DECEL_STEP_V = [0.16, 0.18, 0.18]
GENESIS_G90_RELEASE_MAX_SPEED = 0.8
IONIQ_6_LONG_MIN_JERK = 0.5 * IONIQ_6_RESPONSE_MULTIPLIER
IONIQ_6_LONG_JERK_LIMIT = 4.8 * IONIQ_6_RESPONSE_MULTIPLIER
IONIQ_6_LONG_LOOKAHEAD_JERK_BP = [2.0, 5.0, 20.0]
IONIQ_6_LONG_LOOKAHEAD_JERK_V = [0.3 / IONIQ_6_RESPONSE_MULTIPLIER,
                                 0.45 / IONIQ_6_RESPONSE_MULTIPLIER,
                                 0.6 / IONIQ_6_RESPONSE_MULTIPLIER]
IONIQ_6_DYNAMIC_LOWER_JERK_BP = [-2.0, -1.5, -1.0, -0.25, -0.1, -0.025, -0.01, -0.005]
IONIQ_6_DYNAMIC_LOWER_JERK_V = [3.3, 1.5, 1.0, 0.8, 0.7, 0.65, 0.55, 0.5]
IONIQ_6_LAUNCH_HOLD_SPEED_BP = [0.0, 0.6, 1.25, 2.5]
IONIQ_6_LAUNCH_HOLD_SPEED_V = [0.75, 0.6, 0.4, 0.0]
IONIQ_6_STOP_BRAKE_CAP_MAX_SPEED = 2.0
IONIQ_6_STOP_BRAKE_CAP_SPEED_BP = [0.0, 0.08, 0.25, 0.6, 1.2, 2.0, 3.0]
IONIQ_6_STOP_BRAKE_CAP_ACCEL_V = [-0.15, -0.16, -0.22, -0.42, -0.78, -1.15, -1.40]
EV6_GT_LINE_STOP_BRAKE_CAP_MAX_SPEED = 1.2
IONIQ_6_STOP_HOLD_JERK_BP = [0.0, 0.15, 0.6, 1.2, 2.0, 3.0]
IONIQ_6_STOP_HOLD_JERK_V = [0.35, 0.40, 0.48, 0.65, 0.85, 1.10]
IONIQ_6_STOP_RELEASE_JERK_BP = [0.0, 0.15, 0.5]
IONIQ_6_STOP_RELEASE_JERK_V = [3.6 * IONIQ_6_RESPONSE_MULTIPLIER,
                               4.2 * IONIQ_6_RESPONSE_MULTIPLIER,
                               4.8 * IONIQ_6_RESPONSE_MULTIPLIER]
REDNECK_BUTTON_COPIES = 2
REDNECK_BUTTON_COPIES_TIME = 7
REDNECK_BUTTON_COPIES_TIME_IMPERIAL = [REDNECK_BUTTON_COPIES_TIME + 3, 70]
REDNECK_BUTTON_COPIES_TIME_METRIC = [REDNECK_BUTTON_COPIES_TIME, 40]
ANGLE_SAFETY_BASELINE_MODEL = str(CAR.KIA_SPORTAGE_HEV_2026)
DEFAULT_ANGLE_SMOOTHING_VEGO_BP = [5.0, 10.0, 20.0]
DEFAULT_ANGLE_SMOOTHING_ALPHA_V = [0.2, 0.1, 0.0]
EV9_STOP_REQUEST_SPEED = 0.47
EV9_STANDSTILL_DELAY_FRAMES = 178
EV9_STOP_RELEASE_DELAY_FRAMES = 6
EV9_HIGH_ANGLE_GAIN_BP = [70.0, 120.0, 220.0, 320.0]
EV9_HIGH_ANGLE_GAIN_CAP_V = [0.85, 0.55, 0.30, 0.16]
EV9_HIGH_ANGLE_GAIN_MIN = 0.004
EV9_SOFT_DRIVER_OVERRIDE_AUTHORITY = 0.35
EV9_SOFT_DRIVER_OVERRIDE_MAX_DELTA = 8.0
EV9_HIGH_ANGLE_INHIBIT_ENTER = 85.0
EV9_HIGH_ANGLE_INHIBIT_RELEASE = 70.0
BLINDSPOT_WARNING_FLASH_SAMPLES = 20
BLINDSPOT_WARNING_FLASH_ON_SAMPLES = 16
BLINDSPOT_WARNING_SOUND_SAMPLES = 36


def egmp_dynamic_longitudinal_tuning(CP) -> bool:
  return CP.carFingerprint in (CAR.HYUNDAI_IONIQ_6, CAR.KIA_EV9) or \
    kia_ev6_gt_line_longitudinal_tuning(CP.carFingerprint, getattr(CP, "carVin", ""))


def should_reset_ev6_gt_line_longitudinal_tuning(CP, long_control_state: LongCtrlState) -> bool:
  return kia_ev6_gt_line_longitudinal_tuning(CP.carFingerprint, getattr(CP, "carVin", "")) and \
    long_control_state == LongCtrlState.off


@dataclass
class Ioniq6LongitudinalTuningState:
  desired_accel: float = 0.0
  actual_accel: float = 0.0
  accel_last: float = 0.0
  jerk_upper: float = 0.0
  jerk_lower: float = 0.0
  launch_active: bool = False
  stopping: bool = False
  stopping_count: int = 0
  long_control_state_last: LongCtrlState = LongCtrlState.off


def reset_ev6_gt_line_longitudinal_tuning(state: Ioniq6LongitudinalTuningState, CP,
                                           long_control_state: LongCtrlState) -> Ioniq6LongitudinalTuningState:
  if should_reset_ev6_gt_line_longitudinal_tuning(CP, long_control_state):
    return Ioniq6LongitudinalTuningState(long_control_state_last=long_control_state)
  return state


@dataclass
class GenesisG90LongitudinalTuningState:
  actual_accel: float = 0.0
  release_active: bool = False
  long_control_state_last: LongCtrlState = LongCtrlState.off


@dataclass(frozen=True)
class EV9LongitudinalTuningState:
  stop_request: bool = False
  cruise_standstill: bool = False
  stop_request_frames: int = 0
  release_frames: int = 0


@dataclass(frozen=True)
class BlindspotWarningOutput:
  mirror_lamp_active: bool = False
  sound_active: bool = False


@dataclass(frozen=True)
class EV9BlindspotWarningInputs:
  source_fresh: bool = False
  left_detected: bool = False
  right_detected: bool = False
  left_stalk_active: bool = False
  right_stalk_active: bool = False


@dataclass
class BlindspotWarningState:
  flash_phase: int = 0
  mirror_warning_active: bool = False
  escalated_prev: bool = False
  sound_remaining: int = 0
  sound_armed: bool = True


def update_blindspot_warning(state: BlindspotWarningState, escalated: bool,
                             blinker: bool) -> BlindspotWarningOutput:
  if not blinker:
    state.flash_phase = 0
    state.mirror_warning_active = False
    state.escalated_prev = False
    state.sound_remaining = 0
    state.sound_armed = True
    return BlindspotWarningOutput()

  rising = escalated and not state.escalated_prev
  if rising:
    state.flash_phase = 0
    state.mirror_warning_active = True
    if state.sound_armed:
      state.sound_remaining = BLINDSPOT_WARNING_SOUND_SAMPLES
      state.sound_armed = False
  elif escalated:
    state.flash_phase = (state.flash_phase + 1) % BLINDSPOT_WARNING_FLASH_SAMPLES
    state.mirror_warning_active = True
  elif state.mirror_warning_active and state.flash_phase < BLINDSPOT_WARNING_FLASH_ON_SAMPLES - 1:
    state.flash_phase += 1
  else:
    state.flash_phase = 0
    state.mirror_warning_active = False

  state.escalated_prev = escalated
  sound_active = state.sound_remaining > 0
  if state.sound_remaining > 0:
    state.sound_remaining -= 1
  return BlindspotWarningOutput(
    mirror_lamp_active=state.mirror_warning_active and state.flash_phase < BLINDSPOT_WARNING_FLASH_ON_SAMPLES,
    sound_active=sound_active,
  )


def get_ev9_blindspot_warning_inputs(CS, now_nanos: int) -> EV9BlindspotWarningInputs:
  native_timestamp = int(getattr(CS, "native_blindspot_ts", 0))
  native_age = int(now_nanos) - native_timestamp
  source_fresh = native_timestamp > 0 and 0 <= native_age <= CANFD_NATIVE_BLINDSPOT_STALE_NS
  if source_fresh:
    left_detected = int(getattr(CS, "native_left_blindspot_state", 0)) in (1, 2)
    right_detected = int(getattr(CS, "native_right_blindspot_state", 0)) in (1, 2)
  else:
    fallback_timestamp = int(getattr(CS, "ev9_reconstructed_blindspot_ts", 0))
    fallback_age = int(now_nanos) - fallback_timestamp
    source_fresh = fallback_timestamp > 0 and 0 <= fallback_age <= EV9_RAW_BLINDSPOT_STALE_NS
    if not source_fresh:
      return EV9BlindspotWarningInputs()
    left_detected = bool(getattr(CS, "ev9_reconstructed_left_blindspot", False))
    right_detected = bool(getattr(CS, "ev9_reconstructed_right_blindspot", False))

  left_stalk_active = bool(getattr(CS, "left_blinker_stalk", False))
  right_stalk_active = bool(getattr(CS, "right_blinker_stalk", False))
  if left_stalk_active and right_stalk_active:
    left_stalk_active = False
    right_stalk_active = False

  return EV9BlindspotWarningInputs(
    source_fresh=True,
    left_detected=left_detected,
    right_detected=right_detected,
    left_stalk_active=left_stalk_active,
    right_stalk_active=right_stalk_active,
  )


def _jerk_limited_integrator(desired_accel: float, last_accel: float, jerk_upper: float, jerk_lower: float) -> float:
  step = (jerk_upper if desired_accel >= last_accel else jerk_lower) * DT_CTRL * 5.0
  return float(np.clip(desired_accel, last_accel - step, last_accel + step))


def _calculate_ioniq_6_dynamic_lower_jerk(accel_error: float) -> float:
  if accel_error < 0.0:
    scaled_values = np.array(IONIQ_6_DYNAMIC_LOWER_JERK_V) * (IONIQ_6_LONG_JERK_LIMIT / IONIQ_6_DYNAMIC_LOWER_JERK_V[0])
    return float(np.interp(accel_error, IONIQ_6_DYNAMIC_LOWER_JERK_BP, scaled_values))
  return IONIQ_6_LONG_MIN_JERK


def should_track_stop_accel_directly(stopping: bool, v_ego: float,
                                     accel_cmd: float, actual_accel: float) -> bool:
  return bool(stopping and v_ego > EV6_GT_LINE_STOP_BRAKE_CAP_MAX_SPEED and accel_cmd < actual_accel)


def should_use_ev6_gt_line_stop_direct_tracking(ev6_gt_line: bool, stopping: bool, v_ego: float,
                                                 accel_cmd: float, actual_accel: float) -> bool:
  return bool(ev6_gt_line and stopping and v_ego > EV6_GT_LINE_STOP_BRAKE_CAP_MAX_SPEED and accel_cmd < actual_accel)


def update_ev9_longitudinal_tuning(state: EV9LongitudinalTuningState, enabled: bool,
                                   stopping: bool, v_ego: float) -> EV9LongitudinalTuningState:
  if not enabled:
    return EV9LongitudinalTuningState()

  if stopping:
    if not state.stop_request and v_ego > EV9_STOP_REQUEST_SPEED:
      return EV9LongitudinalTuningState()
    frames = state.stop_request_frames + 1 if state.stop_request else 0
    return EV9LongitudinalTuningState(
      stop_request=True,
      cruise_standstill=frames >= EV9_STANDSTILL_DELAY_FRAMES,
      stop_request_frames=frames,
    )

  if state.stop_request:
    release_frames = state.release_frames + 1
    if release_frames <= EV9_STOP_RELEASE_DELAY_FRAMES:
      return EV9LongitudinalTuningState(
        stop_request=True,
        cruise_standstill=False,
        stop_request_frames=state.stop_request_frames,
        release_frames=release_frames,
      )

  return EV9LongitudinalTuningState()


def update_blindspot_warning(state: BlindspotWarningState, escalated: bool,
                             blinker: bool) -> BlindspotWarningOutput:
  if not blinker:
    state.flash_phase = 0
    state.mirror_warning_active = False
    state.escalated_prev = False
    state.sound_remaining = 0
    state.sound_armed = True
    return BlindspotWarningOutput()

  rising = escalated and not state.escalated_prev
  if rising:
    state.flash_phase = 0
    state.mirror_warning_active = True
    if state.sound_armed:
      state.sound_remaining = BLINDSPOT_WARNING_SOUND_SAMPLES
      state.sound_armed = False
  elif escalated:
    state.flash_phase = (state.flash_phase + 1) % BLINDSPOT_WARNING_FLASH_SAMPLES
    state.mirror_warning_active = True
  elif state.mirror_warning_active and state.flash_phase < BLINDSPOT_WARNING_FLASH_ON_SAMPLES - 1:
    state.flash_phase += 1
  else:
    state.flash_phase = 0
    state.mirror_warning_active = False

  state.escalated_prev = escalated
  sound_active = state.sound_remaining > 0
  if state.sound_remaining > 0:
    state.sound_remaining -= 1
  return BlindspotWarningOutput(
    mirror_lamp_active=state.mirror_warning_active and state.flash_phase < BLINDSPOT_WARNING_FLASH_ON_SAMPLES,
    sound_active=sound_active,
  )


def reset_egmp_longitudinal_tuning(state: Ioniq6LongitudinalTuningState) -> Ioniq6LongitudinalTuningState:
  state.desired_accel = 0.0
  state.actual_accel = 0.0
  state.accel_last = 0.0
  state.jerk_upper = 0.0
  state.jerk_lower = 0.0
  state.launch_active = False
  return state


def update_ioniq_6_longitudinal_tuning(state: Ioniq6LongitudinalTuningState, accel_cmd: float, v_ego: float, a_ego: float,
                                       long_control_state: LongCtrlState, long_active: bool,
                                       ev6_gt_line: bool = False, low_speed_stop_brake_cap: bool = False) -> Ioniq6LongitudinalTuningState:
  starting = long_control_state == LongCtrlState.starting
  stopping = long_control_state == LongCtrlState.stopping
  restart_from_stop = state.long_control_state_last in (LongCtrlState.stopping, LongCtrlState.starting) and \
                      long_control_state in (LongCtrlState.starting, LongCtrlState.pid) and accel_cmd > 0.0 and v_ego < 0.5

  state.stopping = long_active and stopping
  state.stopping_count = state.stopping_count + 1 if state.stopping else 0

  if not long_active:
    state.desired_accel = 0.0
    state.actual_accel = 0.0
    state.accel_last = 0.0
    state.jerk_upper = 0.0
    state.jerk_lower = 0.0
    state.launch_active = False
    state.long_control_state_last = long_control_state
    return state

  if accel_cmd <= 0.0 or v_ego >= IONIQ_6_LAUNCH_HOLD_SPEED_BP[-1]:
    state.launch_active = False
  elif starting or (state.launch_active and v_ego < IONIQ_6_LAUNCH_HOLD_SPEED_BP[-1]) or \
      (state.long_control_state_last == LongCtrlState.starting and long_control_state == LongCtrlState.pid and v_ego < IONIQ_6_LAUNCH_HOLD_SPEED_BP[-1]):
    state.launch_active = True

  upper_speed_limit = float(np.interp(v_ego, [0.0, 5.0, 20.0], [2.0, 3.0, 2.0])) * IONIQ_6_RESPONSE_MULTIPLIER if long_control_state == LongCtrlState.pid else IONIQ_6_LONG_MIN_JERK
  lower_speed_limit = float(np.interp(v_ego, [0.0, 5.0, 20.0], [5.0, 3.5, 3.0])) * IONIQ_6_RESPONSE_MULTIPLIER

  future_t_upper = float(np.interp(v_ego, IONIQ_6_LONG_LOOKAHEAD_JERK_BP, IONIQ_6_LONG_LOOKAHEAD_JERK_V))
  future_t_lower = float(np.interp(v_ego, IONIQ_6_LONG_LOOKAHEAD_JERK_BP, IONIQ_6_LONG_LOOKAHEAD_JERK_V))

  accel_error = accel_cmd - state.accel_last
  j_ego_upper = float(np.clip(accel_error / future_t_upper, -IONIQ_6_LONG_JERK_LIMIT, IONIQ_6_LONG_JERK_LIMIT))
  j_ego_lower = float(np.clip(accel_error / future_t_lower, -IONIQ_6_LONG_JERK_LIMIT, IONIQ_6_LONG_JERK_LIMIT))
  desired_jerk_upper = min(max(j_ego_upper, IONIQ_6_LONG_MIN_JERK), upper_speed_limit)

  dynamic_accel_error = a_ego - state.accel_last
  dynamic_lower_jerk = _calculate_ioniq_6_dynamic_lower_jerk(dynamic_accel_error)
  state.jerk_upper = desired_jerk_upper
  state.jerk_lower = min(dynamic_lower_jerk, lower_speed_limit)

  if state.stopping:
    stop_brake_cap_max_speed = EV6_GT_LINE_STOP_BRAKE_CAP_MAX_SPEED if ev6_gt_line or low_speed_stop_brake_cap else \
      IONIQ_6_STOP_BRAKE_CAP_MAX_SPEED
    if v_ego <= stop_brake_cap_max_speed:
      stop_brake_cap = float(np.interp(v_ego, IONIQ_6_STOP_BRAKE_CAP_SPEED_BP, IONIQ_6_STOP_BRAKE_CAP_ACCEL_V))
      state.desired_accel = min(0.0, max(accel_cmd, stop_brake_cap))
      state.jerk_upper = min(state.jerk_upper, float(np.interp(v_ego, IONIQ_6_STOP_HOLD_JERK_BP, IONIQ_6_STOP_HOLD_JERK_V)) * IONIQ_6_RESPONSE_MULTIPLIER)
    else:
      state.desired_accel = float(np.clip(accel_cmd, CarControllerParams.ACCEL_MIN, 0.0))
  else:
    state.desired_accel = float(np.clip(accel_cmd, CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))
    if state.launch_active:
      state.desired_accel = max(state.desired_accel, float(np.interp(v_ego, IONIQ_6_LAUNCH_HOLD_SPEED_BP, IONIQ_6_LAUNCH_HOLD_SPEED_V)))
      state.jerk_upper = max(state.jerk_upper, float(np.interp(v_ego, [0.0, 2.5], [4.8, 3.2])) * IONIQ_6_RESPONSE_MULTIPLIER)
      state.jerk_lower = max(state.jerk_lower, 1.0)
    if restart_from_stop:
      state.jerk_upper = min(state.jerk_upper, float(np.interp(v_ego, IONIQ_6_STOP_RELEASE_JERK_BP, IONIQ_6_STOP_RELEASE_JERK_V)))

  state.actual_accel = _jerk_limited_integrator(state.desired_accel, state.accel_last, state.jerk_upper, state.jerk_lower)
  state.accel_last = state.actual_accel
  state.long_control_state_last = long_control_state
  return state


def update_genesis_g90_longitudinal_tuning(state: GenesisG90LongitudinalTuningState, accel_cmd: float, v_ego: float,
                                           long_control_state: LongCtrlState, long_active: bool) -> GenesisG90LongitudinalTuningState:
  if not long_active:
    state.actual_accel = 0.0
    state.release_active = False
    state.long_control_state_last = long_control_state
    return state

  stopping = long_control_state == LongCtrlState.stopping
  if stopping and v_ego <= GENESIS_G90_STOP_HOLD_SPEED_BP[-1]:
    state.release_active = False
    stop_brake_cap = float(np.interp(v_ego, GENESIS_G90_STOP_HOLD_SPEED_BP, GENESIS_G90_STOP_HOLD_ACCEL_V))
    target_hold = min(0.0, max(accel_cmd, stop_brake_cap))
    if state.actual_accel < target_hold:
      relax_step = float(np.interp(v_ego, GENESIS_G90_STOP_HOLD_RELAX_SPEED_BP, GENESIS_G90_STOP_HOLD_RELAX_STEP_V))
      state.actual_accel = min(state.actual_accel + relax_step, target_hold)
    else:
      state.actual_accel = target_hold
  else:
    if state.long_control_state_last == LongCtrlState.stopping and long_control_state == LongCtrlState.pid and \
        accel_cmd > 0.0 and v_ego < GENESIS_G90_RELEASE_MAX_SPEED:
      state.release_active = True

    if state.release_active:
      accel_step = float(np.interp(v_ego, GENESIS_G90_RELEASE_SPEED_BP, GENESIS_G90_RELEASE_ACCEL_STEP_V))
      decel_step = float(np.interp(v_ego, GENESIS_G90_RELEASE_SPEED_BP, GENESIS_G90_RELEASE_DECEL_STEP_V))
      state.actual_accel = float(np.clip(accel_cmd, state.actual_accel - decel_step, state.actual_accel + accel_step))
      if v_ego >= GENESIS_G90_RELEASE_MAX_SPEED or accel_cmd <= 0.0 or state.actual_accel >= accel_cmd - 1e-3:
        state.release_active = False
    else:
      state.actual_accel = accel_cmd

  state.long_control_state_last = long_control_state
  return state


def get_baseline_safety_cp():
  from opendbc.car.hyundai.interface import CarInterface
  return CarInterface.get_non_essential_params(ANGLE_SAFETY_BASELINE_MODEL)


def get_angle_smoothing_alpha(CP, v_ego: float) -> float:
  return float(np.interp(v_ego, DEFAULT_ANGLE_SMOOTHING_VEGO_BP, DEFAULT_ANGLE_SMOOTHING_ALPHA_V))


def direct_angle_request_allowed(v_ego_raw, measured_angle, last_angle, drive_gear, VM, params):
  safety_v_ego = max(v_ego_raw - 1.0, 1.0)
  max_safety_angle = get_max_angle_vm(safety_v_ego, VM, params)
  return drive_gear and abs(measured_angle) <= max_safety_angle and abs(last_angle) <= max_safety_angle


def compute_torque_reduction_gain(steering_torque, v_ego, lat_active, last_gain):
  if lat_active:
    ceiling = np.interp(v_ego, [0.5, 1.5], [1.0, 0.85])
    shelf = np.interp(v_ego, [2.0, 11.0], [0.45, 0.6])
    floor = np.interp(v_ego, [2.0, 22.0], [0.1, 0.3])
    bp1 = np.interp(v_ego, [2.0, 11.0], [75.0, 125.0])
    bp2 = np.interp(v_ego, [2.0, 11.0], [125.0, 150.0])
    bp3 = np.interp(v_ego, [2.0, 11.0], [175.0, 275.0])
    bp4 = np.interp(v_ego, [2.0, 22.0], [400.0, 700.0])
    target = np.interp(abs(steering_torque), [bp1, bp2, bp3, bp4], [ceiling, shelf, shelf, floor])
  else:
    target = 0.0

  gain = rate_limit(target, last_gain, -0.014, 0.004)
  return round(gain / 0.004) * 0.004


def apply_ev9_high_angle_gain_cap(CP, gain: float, steering_angle_deg: float, lat_active: bool) -> float:
  if CP.carFingerprint != CAR.KIA_EV9 or not CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING or not lat_active:
    return gain

  cap = float(np.interp(abs(steering_angle_deg), EV9_HIGH_ANGLE_GAIN_BP, EV9_HIGH_ANGLE_GAIN_CAP_V))
  return max(EV9_HIGH_ANGLE_GAIN_MIN, min(gain, cap))


def ev9_driver_override_active(CP, steering_pressed: bool, lat_active: bool) -> bool:
  return CP.carFingerprint == CAR.KIA_EV9 and CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING and lat_active and \
         steering_pressed


def update_ev9_high_angle_inhibit(CP, inhibited: bool, steering_angle_deg: float, lat_active: bool,
                                  protection_enabled: bool) -> bool:
  """Latch EV9 angle actuation off before the EPS high-angle timer can fault."""
  applicable = CP.carFingerprint == CAR.KIA_EV9 and CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING
  if not applicable or not protection_enabled or not lat_active:
    return False
  if inhibited:
    return abs(steering_angle_deg) > EV9_HIGH_ANGLE_INHIBIT_RELEASE
  return abs(steering_angle_deg) >= EV9_HIGH_ANGLE_INHIBIT_ENTER


def ev9_dynamic_steering_icons(CP, feature_enabled: bool, lat_active: bool, gain: float,
                               driver_override: bool, high_angle_inhibited: bool,
                               legacy_lka_icon: int, legacy_lfa_icon: int,
                               downstream_angle_command_available: bool = True) -> tuple[int, int, bool | None]:
  """Return EV9 grey/green steering state plus the CCNC actuation override."""
  applicable = CP.carFingerprint == CAR.KIA_EV9 and CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING
  if not applicable or not feature_enabled:
    return legacy_lka_icon, legacy_lfa_icon, None

  meaningfully_actuating = bool(lat_active and gain > EV9_HIGH_ANGLE_GAIN_MIN and
                                not driver_override and not high_angle_inhibited and downstream_angle_command_available)
  if lat_active:
    icon = 2 if meaningfully_actuating else 1
    return icon, icon, meaningfully_actuating
  return 1, 0, False


def ev9_reconstructed_steering_available(lat_active: bool, controls_enabled: bool,
                                         always_on_lateral_enabled: bool) -> bool:
  """Report feature availability independently from temporary actuation loss."""
  return bool(lat_active or controls_enabled or always_on_lateral_enabled)


def update_angle_command(CP, angle_filter, desired_angle: float, steering_angle_deg: float, v_ego: float,
                         steering_pressed: bool, lat_active: bool, soft_driver_override_enabled: bool = False) -> float:
  if ev9_driver_override_active(CP, steering_pressed, lat_active):
    if not soft_driver_override_enabled:
      angle_filter.x = steering_angle_deg
      return steering_angle_deg

    # Hands-on torque already reduces the requested EPS gain. Preserve a small,
    # bounded portion of path authority instead of also snapping the requested
    # angle to the measured wheel angle, which removes all useful correction.
    desired_delta = (desired_angle - steering_angle_deg) * EV9_SOFT_DRIVER_OVERRIDE_AUTHORITY
    override_target = steering_angle_deg + float(np.clip(desired_delta,
                                                          -EV9_SOFT_DRIVER_OVERRIDE_MAX_DELTA,
                                                          EV9_SOFT_DRIVER_OVERRIDE_MAX_DELTA))
    angle_filter.update_alpha(get_angle_smoothing_alpha(CP, v_ego))
    filtered_angle = angle_filter.update(override_target)
    filtered_angle = float(np.clip(filtered_angle,
                                   steering_angle_deg - EV9_SOFT_DRIVER_OVERRIDE_MAX_DELTA,
                                   steering_angle_deg + EV9_SOFT_DRIVER_OVERRIDE_MAX_DELTA))
    angle_filter.x = filtered_angle
    return filtered_angle

  angle_filter.update_alpha(get_angle_smoothing_alpha(CP, v_ego))
  return angle_filter.update(desired_angle)


def process_hud_alert(enabled, fingerprint, hud_control):
  sys_warning = (hud_control.visualAlert in (VisualAlert.steerRequired, VisualAlert.ldw))

  # initialize to no line visible
  # TODO: this is not accurate for all cars
  sys_state = 1
  if hud_control.leftLaneVisible and hud_control.rightLaneVisible or sys_warning:  # HUD alert only display when LKAS status is active
    sys_state = 3 if enabled or sys_warning else 4
  elif hud_control.leftLaneVisible:
    sys_state = 5
  elif hud_control.rightLaneVisible:
    sys_state = 6

  # initialize to no warnings
  left_lane_warning = 0
  right_lane_warning = 0
  if hud_control.leftLaneDepart:
    left_lane_warning = 1 if fingerprint in (CAR.GENESIS_G90, CAR.GENESIS_G80) else 2
  if hud_control.rightLaneDepart:
    right_lane_warning = 1 if fingerprint in (CAR.GENESIS_G90, CAR.GENESIS_G80) else 2

  return sys_warning, sys_state, left_lane_warning, right_lane_warning


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.CAN = CanBus(CP)
    self.params = CarControllerParams(CP)
    self.packer = CANPacker(dbc_names[Bus.pt])
    self.angle_limit_counter = 0
    self.VM = VehicleModel(CP)
    self.BASELINE_VM = VehicleModel(get_baseline_safety_cp()) if CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING else self.VM
    self.angle_filter = FirstOrderFilter(0.0, 0.2, DT_CTRL)
    self.direct_angle_request_allowed = True

    self.accel_last = 0
    self.apply_torque_last = 0
    self.apply_angle_last = 0.0
    self.car_fingerprint = CP.carFingerprint
    self.last_button_frame = 0
    self.redneck_button_frame = 0
    self.ecu_disable_failed = False
    self._ecu_disable_checked = False
    self._params = Params()
    if CP.carFingerprint == CAR.KIA_EV9:
      self._ev9_long_tuning = EV9LongitudinalTuningState()
    # These are fixed parts of the EV9 production profile. Runtime feature
    # Params previously allowed an incomplete combination of steering streams.
    self.ev9_soft_driver_override_enabled = CP.carFingerprint == CAR.KIA_EV9
    self.ev9_dynamic_steering_icon_enabled = CP.carFingerprint == CAR.KIA_EV9
    self.ev9_high_angle_fault_protection_enabled = CP.carFingerprint == CAR.KIA_EV9
    self.ev9_high_angle_inhibited = False
    self._left_blindspot_warning = BlindspotWarningState()
    self._right_blindspot_warning = BlindspotWarningState()
    self._ev9_actuation_fault_reason = EV9ActuationAbortReason.NONE
    self._ev9_scc_counter = 0
    self._ev9_stop_state = EV9LongitudinalStopState()
    self.long_active_ecu = self.CP.openpilotLongitudinalControl
    self._ioniq_6_lane_change_ui_side = None
    self._ioniq_6_lane_change_ui_frames = 0
    self._ioniq_6_long_tuning = Ioniq6LongitudinalTuningState()
    self._genesis_g90_long_tuning = GenesisG90LongitudinalTuningState()
    self._dash_lat_disengage_blink_frame = 0
    self._dash_lat_disengage_init = False
    self._dash_prev_lat_active = False

  def _update_dash_icon_state(self, CC):
    if CC.latActive:
      self._dash_lat_disengage_init = False
    elif self._dash_prev_lat_active:
      self._dash_lat_disengage_init = True

    if not self._dash_lat_disengage_init:
      self._dash_lat_disengage_blink_frame = self.frame

    disengaging = self._dash_lat_disengage_init and \
                  (self.frame - self._dash_lat_disengage_blink_frame) * DT_CTRL < HYUNDAI_DASH_DISENGAGE_BLINK_TIME
    self._dash_prev_lat_active = CC.latActive
    lat_or_enabled = CC.enabled or CC.latActive
    lka_icon = 2 if lat_or_enabled else 3 if disengaging else 1
    lfa_icon = 2 if lat_or_enabled else 3 if disengaging else 0

    return lka_icon, lfa_icon

  def _get_canfd_scc_lead_state(self, CC, CS, now_nanos):
    openpilot_lead_visible = bool(getattr(CS, "openpilot_lead_visible", False) or CC.hudControl.leadVisible)
    openpilot_lead_distance = float(np.clip(getattr(CS, "openpilot_lead_distance", 0.0), 0.0, 204.7))
    openpilot_lead_rel_speed = float(np.clip(getattr(CS, "openpilot_lead_rel_speed", 0.0), -16.4, 34.7))
    stock_camera_lead_fresh = now_nanos - getattr(CS, "stock_camera_lead_ts", 0) <= CANFD_CAMERA_LEAD_STALE_NS
    stock_camera_lead_visible = stock_camera_lead_fresh and getattr(CS, "stock_camera_lead_visible", False)

    if openpilot_lead_visible and openpilot_lead_distance > CANFD_LEAD_MIN_DISTANCE:
      return True, openpilot_lead_distance, openpilot_lead_rel_speed
    if stock_camera_lead_visible:
      lead_distance = float(np.clip(getattr(CS, "stock_camera_lead_distance", 0.0), 0.0, 204.7))
      lead_rel_speed = float(np.clip(getattr(CS, "stock_camera_lead_rel_speed", 0.0), -16.4, 34.7))
      return True, lead_distance, lead_rel_speed
    if openpilot_lead_visible:
      return True, CANFD_FALLBACK_LEAD_DISTANCE, 0.0

    return False, 0.0, 0.0

  @staticmethod
  def _get_redneck_button(CS):
    return {
      1: Buttons.RES_ACCEL,
      2: Buttons.SET_DECEL,
    }.get(getattr(CS, "redneck_send_button", 0), Buttons.NONE)

  def _create_can_redneck_button_messages(self, CS):
    send_button = self._get_redneck_button(CS)
    if send_button == Buttons.NONE or (self.frame - self.last_button_frame) * DT_CTRL <= 0.1:
      return []

    copies_xp = REDNECK_BUTTON_COPIES_TIME_METRIC if CS.is_metric else REDNECK_BUTTON_COPIES_TIME_IMPERIAL
    copies = int(np.interp(REDNECK_BUTTON_COPIES_TIME, copies_xp, [1, REDNECK_BUTTON_COPIES]))
    can_sends = [hyundaican.create_clu11(self.packer, self.frame, CS.clu11, send_button, self.CP)] * copies
    CS.redneck_last_sent_button = getattr(CS, "redneck_send_button", 0)

    if (self.frame - self.last_button_frame) * DT_CTRL >= 0.15:
      self.last_button_frame = self.frame

    return can_sends

  def _create_canfd_redneck_button_messages(self, CS):
    send_button = self._get_redneck_button(CS)
    if send_button == Buttons.NONE or self.CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS or \
        (self.frame - self.last_button_frame) * DT_CTRL <= 0.2:
      return []

    self.redneck_button_frame += 1
    button_counter_offset = [1, 1, 0, None][self.redneck_button_frame % 4]
    if button_counter_offset is None:
      return []

    can_sends = [
      hyundaicanfd.create_buttons(self.packer, self.CP, self.CAN, (CS.buttons_counter + button_counter_offset) % 0xF, send_button)
      for _ in range(20)
    ]
    CS.redneck_last_sent_button = getattr(CS, "redneck_send_button", 0)
    self.last_button_frame = self.frame
    return can_sends

  def update(self, CC, CS, now_nanos, starpilot_toggles):
    actuators = CC.actuators
    hud_control = CC.hudControl
    lka_icon, lfa_icon = self._update_dash_icon_state(CC)
    ev9_ccnc_steering_active = None

    if not self.CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING:
      self.params = CarControllerParams(self.CP, CS.out.vEgoRaw)
    direct_angle_control = self.CP.carFingerprint in CANFD_ANGLE_LONGITUDINAL_CAR and self.long_active_ecu
    measured_steering_angle = CS.angle_steering_angle if direct_angle_control else CS.out.steeringAngleDeg
    angle_lat_active = CC.latActive
    if direct_angle_control and CC.latActive:
      drive_gear = CS.out.gearShifter == structs.CarState.GearShifter.drive
      angle_lat_active = direct_angle_request_allowed(CS.out.vEgoRaw, measured_steering_angle, self.apply_angle_last,
                                                      drive_gear, self.BASELINE_VM, self.params) and not CS.angle_steering_fault
    self.direct_angle_request_allowed = angle_lat_active
    apply_angle = measured_steering_angle

    if self.CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING:
      v_ego_raw = CS.out.vEgoRaw
      desired_angle = float(np.clip(actuators.steeringAngleDeg,
                                    -self.params.ANGLE_LIMITS.STEER_ANGLE_MAX,
                                    self.params.ANGLE_LIMITS.STEER_ANGLE_MAX))
      steering_angle_deg = float(np.clip(CS.out.steeringAngleDeg,
                                         -self.params.ANGLE_LIMITS.STEER_ANGLE_MAX,
                                         self.params.ANGLE_LIMITS.STEER_ANGLE_MAX))
      self.ev9_high_angle_inhibited = update_ev9_high_angle_inhibit(
        self.CP, self.ev9_high_angle_inhibited, CS.out.steeringAngleDeg, CC.latActive,
        self.ev9_high_angle_fault_protection_enabled,
      )
      if self.ev9_high_angle_inhibited:
        # Reset the smoother to measured angle, then let the existing vehicle-model
        # limiters move the transmitted request toward it at a safety-bounded rate.
        self.angle_filter.x = steering_angle_deg
        desired_angle = steering_angle_deg
      else:
        desired_angle = update_angle_command(self.CP, self.angle_filter, desired_angle, steering_angle_deg, CS.out.vEgo,
                                             CS.out.steeringPressed, CC.latActive, self.ev9_soft_driver_override_enabled)

      apply_angle = apply_steer_angle_limits_vm(desired_angle, self.apply_angle_last, v_ego_raw,
                                                measured_steering_angle, angle_lat_active, self.params, self.VM)

      if str(self.CP.carFingerprint) != ANGLE_SAFETY_BASELINE_MODEL:
        apply_angle = apply_steer_angle_limits_vm(apply_angle or desired_angle, self.apply_angle_last, v_ego_raw,
                                                  measured_steering_angle, angle_lat_active, self.params, self.BASELINE_VM)

      if direct_angle_control and angle_lat_active:
        # Match Panda's 1 m/s speed tolerance so a shrinking absolute limit stays inside its jerk envelope.
        safety_v_ego = max(v_ego_raw - 1.0, 1.0)
        max_angle_delta = min(get_max_angle_delta_vm(safety_v_ego, self.BASELINE_VM, self.params),
                              self.params.ANGLE_LIMITS.MAX_ANGLE_RATE)
        apply_angle = float(np.clip(apply_angle,
                                    self.apply_angle_last - max_angle_delta,
                                    self.apply_angle_last + max_angle_delta))

      apply_torque = compute_torque_reduction_gain(CS.out.steeringTorque, v_ego_raw, CC.latActive, self.apply_torque_last)
      apply_torque = apply_ev9_high_angle_gain_cap(self.CP, apply_torque, CS.out.steeringAngleDeg, CC.latActive)
      if self.ev9_high_angle_inhibited:
        apply_torque = 0.0
      apply_steer_req = CC.latActive and apply_torque != 0.0
      torque_fault = False

      if apply_angle is None:
        apply_torque = 0
        apply_angle = measured_steering_angle
        apply_steer_req = False

      self.apply_angle_last = apply_angle
      if not angle_lat_active:
        self.apply_angle_last = float(np.clip(measured_steering_angle,
                                              -self.params.ANGLE_LIMITS.STEER_ANGLE_MAX,
                                              self.params.ANGLE_LIMITS.STEER_ANGLE_MAX))
        self.angle_filter.x = self.apply_angle_last
      driver_override = ev9_driver_override_active(self.CP, CS.out.steeringPressed, CC.latActive)
      ev9_direct_path_required = self.CP.carFingerprint == CAR.KIA_EV9 and self.long_active_ecu
      ev9_direct_path_available = not ev9_direct_path_required or should_send_ev9_direct_angle_command(
        CS.out.gearShifter == structs.CarState.GearShifter.drive, CC.latActive,
      ) and not getattr(CS, "mdps_lka_angle_fault", False)
      lka_icon, lfa_icon, ev9_ccnc_steering_active = ev9_dynamic_steering_icons(
        self.CP, self.ev9_dynamic_steering_icon_enabled, CC.latActive, apply_torque,
        driver_override, self.ev9_high_angle_inhibited, lka_icon, lfa_icon, ev9_direct_path_available,
      )
    else:
      # steering torque
      new_torque = int(round(actuators.torque * self.params.STEER_MAX))
      apply_torque = apply_driver_steer_torque_limits(new_torque, self.apply_torque_last, CS.out.steeringTorque, self.params)

      # >90 degree steering fault prevention
      self.angle_limit_counter, apply_steer_req = common_fault_avoidance(abs(CS.out.steeringAngleDeg) >= MAX_ANGLE, CC.latActive,
                                                                         self.angle_limit_counter, MAX_ANGLE_FRAMES,
                                                                         MAX_ANGLE_CONSECUTIVE_FRAMES)

      if not CC.latActive:
        apply_torque = 0

      # Hold torque with induced temporary fault when cutting the actuation bit
      # FIXME: we don't use this with CAN FD?
      torque_fault = CC.latActive and not apply_steer_req

    self.apply_torque_last = apply_torque

    # accel + longitudinal
    accel_cmd = float(np.clip(actuators.accel, CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))
    accel = accel_cmd
    stopping = actuators.longControlState == LongCtrlState.stopping
    set_speed_in_units = hud_control.setSpeed * (CV.MS_TO_KPH if CS.is_metric else CV.MS_TO_MPH)
    CS.redneck_last_sent_button = 0

    can_sends = []

    # Check EcuDisableFailed once after init() has run
    if not self._ecu_disable_checked and self.frame > 0:
      self.ecu_disable_failed = self._params.get_bool("EcuDisableFailed")
      self._ecu_disable_checked = True

    # When ECU disable was skipped (car started in READY mode), don't send any
    # longitudinal messages - stock ECU is still active and these would conflict
    self.long_active_ecu = self.CP.openpilotLongitudinalControl and not self.ecu_disable_failed

    use_egmp_dynamic_long_tuning = egmp_dynamic_longitudinal_tuning(self.CP) and self.long_active_ecu and \
                                   actuators.longControlState in (LongCtrlState.starting, LongCtrlState.pid, LongCtrlState.stopping)
    is_ev6_gt_line = kia_ev6_gt_line_longitudinal_tuning(self.CP.carFingerprint, getattr(self.CP, "carVin", ""))
    is_ev9 = self.CP.carFingerprint == CAR.KIA_EV9
    if is_ev9 and (self._ev9_long_tuning.stop_request or not CC.enabled or CC.cruiseControl.override):
      self._ioniq_6_long_tuning = reset_egmp_longitudinal_tuning(self._ioniq_6_long_tuning)
    if should_reset_ev6_gt_line_longitudinal_tuning(self.CP, actuators.longControlState):
      self._ioniq_6_long_tuning = reset_ev6_gt_line_longitudinal_tuning(self._ioniq_6_long_tuning, self.CP,
                                                                         actuators.longControlState)
    elif use_egmp_dynamic_long_tuning and self.frame % 5 == 0:
      self._ioniq_6_long_tuning = update_ioniq_6_longitudinal_tuning(self._ioniq_6_long_tuning, accel_cmd,
                                                                      CS.out.vEgo, CS.out.aEgo,
                                                                      actuators.longControlState, self.long_active_ecu,
                                                                      ev6_gt_line=is_ev6_gt_line,
                                                                      low_speed_stop_brake_cap=is_ev9)
    use_egmp_smoothed_accel = use_egmp_dynamic_long_tuning and (
      accel_cmd >= self._ioniq_6_long_tuning.actual_accel or
      self._ioniq_6_long_tuning.launch_active or
      self._ioniq_6_long_tuning.stopping
    )
    if should_use_ev6_gt_line_stop_direct_tracking(is_ev6_gt_line, self._ioniq_6_long_tuning.stopping,
                                                   CS.out.vEgo, accel_cmd, self._ioniq_6_long_tuning.actual_accel):
      use_egmp_smoothed_accel = False
    if is_ev9 and should_track_stop_accel_directly(self._ioniq_6_long_tuning.stopping, CS.out.vEgo,
                                                   accel_cmd, self._ioniq_6_long_tuning.actual_accel):
      use_egmp_smoothed_accel = False
    if use_egmp_dynamic_long_tuning:
      if use_egmp_smoothed_accel:
        accel = self._ioniq_6_long_tuning.actual_accel
        stopping = self._ioniq_6_long_tuning.stopping
      else:
        accel = float(np.clip(accel_cmd,
                              self.accel_last - IONIQ_6_CANFD_SCC_DECEL_STEP,
                              self.accel_last + IONIQ_6_CANFD_SCC_ACCEL_STEP))
        self._ioniq_6_long_tuning.desired_accel = accel_cmd
        self._ioniq_6_long_tuning.actual_accel = accel
        self._ioniq_6_long_tuning.accel_last = accel
        self._ioniq_6_long_tuning.jerk_upper = 3.0
        self._ioniq_6_long_tuning.jerk_lower = 5.0 if CC.enabled else 1.0
        self._ioniq_6_long_tuning.launch_active = False
        self._ioniq_6_long_tuning.stopping = stopping
        self._ioniq_6_long_tuning.long_control_state_last = actuators.longControlState

    if self.CP.carFingerprint == CAR.GENESIS_G90 and self.long_active_ecu:
      self._genesis_g90_long_tuning = update_genesis_g90_longitudinal_tuning(self._genesis_g90_long_tuning, accel_cmd,
                                                                              CS.out.vEgo, actuators.longControlState,
                                                                              self.long_active_ecu)
      accel = self._genesis_g90_long_tuning.actual_accel

    # *** common hyundai stuff ***

    # tester present - w/ no response (keeps relevant ECU disabled)
    if self.frame % 100 == 0 and not (self.CP.flags & HyundaiFlags.CANFD_CAMERA_SCC) and self.long_active_ecu:
      # for longitudinal control, either radar or ADAS driving ECU
      addr, bus = 0x7d0, self.CAN.ECAN if self.CP.flags & (HyundaiFlags.CANFD | HyundaiFlags.CAN_CANFD_BLENDED) else 0
      if self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING.value:
        addr, bus = 0x730, self.CAN.ECAN
      can_sends.append(make_tester_present_msg(addr, bus, suppress_response=True))

      # for blinkers
      if self.CP.flags & HyundaiFlags.ENABLE_BLINKERS:
        can_sends.append(make_tester_present_msg(0x7b1, self.CAN.ECAN, suppress_response=True))

    # *** CAN/CAN FD specific ***
    if self.CP.flags & HyundaiFlags.CANFD:
      can_sends.extend(self.create_canfd_msgs(now_nanos, apply_steer_req, apply_torque, apply_angle, set_speed_in_units, accel,
                                              stopping, hud_control, CS, CC, starpilot_toggles, lka_icon, lfa_icon,
                                              ev9_ccnc_steering_active))
    else:
      can_sends.extend(self.create_can_msgs(apply_steer_req, apply_torque, torque_fault, set_speed_in_units, accel,
                                            stopping, hud_control, actuators, CS, CC, lfa_icon))

    new_actuators = actuators.as_builder()
    if self.CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING:
      new_actuators.steeringAngleDeg = apply_angle
      new_actuators.torque = 0
      new_actuators.torqueOutputCan = 0
    else:
      new_actuators.torque = apply_torque / self.params.STEER_MAX
      new_actuators.torqueOutputCan = apply_torque
    new_actuators.accel = accel

    self.frame += 1
    return new_actuators, can_sends

  def create_can_msgs(self, apply_steer_req, apply_torque, torque_fault, set_speed_in_units, accel, stopping, hud_control, actuators, CS, CC, lfa_icon):
    can_sends = []
    can_canfd_blended = bool(self.CP.flags & HyundaiFlags.CAN_CANFD_BLENDED)

    # HUD messages
    sys_warning, sys_state, left_lane_warning, right_lane_warning = process_hud_alert(CC.enabled, self.car_fingerprint,
                                                                                      hud_control)

    if can_canfd_blended:
      can_sends.extend(hyundaican.create_lkas11_can_canfd_blended(self.packer, self.frame, self.CP, apply_torque, apply_steer_req,
                                                                  torque_fault, CS.lkas11, sys_warning, sys_state, CC.enabled,
                                                                  hud_control.leftLaneVisible, hud_control.rightLaneVisible,
                                                                  left_lane_warning, right_lane_warning, CS.msg_364))
    else:
      can_sends.append(hyundaican.create_lkas11(self.packer, self.frame, self.CP, apply_torque, apply_steer_req,
                                                torque_fault, CS.lkas11, sys_warning, sys_state, CC.enabled,
                                                hud_control.leftLaneVisible, hud_control.rightLaneVisible,
                                                left_lane_warning, right_lane_warning))

    # Button messages
    if not self.long_active_ecu:
      if CC.cruiseControl.cancel:
        can_sends.append(hyundaican.create_clu11(self.packer, self.frame, CS.clu11, Buttons.CANCEL, self.CP))
      elif CC.cruiseControl.resume:
        # send resume at a max freq of 10Hz
        if (self.frame - self.last_button_frame) * DT_CTRL > 0.1:
          # send 25 messages at a time to increases the likelihood of resume being accepted
          can_sends.extend([hyundaican.create_clu11(self.packer, self.frame, CS.clu11, Buttons.RES_ACCEL, self.CP)] * 25)
          if (self.frame - self.last_button_frame) * DT_CTRL >= 0.15:
            self.last_button_frame = self.frame
      else:
        can_sends.extend(self._create_can_redneck_button_messages(CS))

    if self.long_active_ecu and can_canfd_blended:
      can_sends.extend(hyundaican.create_radar_aux_messages(self.packer, self.CAN, self.frame))

    if self.frame % 2 == 0 and self.long_active_ecu:
      # TODO: unclear if this is needed
      jerk = 3.0 if actuators.longControlState == LongCtrlState.pid else 1.0
      use_fca = self.CP.flags & HyundaiFlags.USE_FCA.value
      if can_canfd_blended:
        can_sends.extend(hyundaican.create_acc_commands_can_canfd_blended(self.packer, CC.enabled, accel, jerk,
                                                                          int(self.frame / 2), hud_control,
                                                                          set_speed_in_units, stopping,
                                                                          CC.cruiseControl.override, use_fca, self.CP))
      else:
        can_sends.extend(hyundaican.create_acc_commands(self.packer, CC.enabled, accel, jerk, int(self.frame / 2),
                                                        hud_control, set_speed_in_units, stopping,
                                                        CC.cruiseControl.override, use_fca, self.CP))

    # 20 Hz LFA MFA message
    if self.frame % 5 == 0 and self.CP.flags & HyundaiFlags.SEND_LFA.value:
      can_sends.append(hyundaican.create_lfahda_mfc(self.packer, CC.enabled, self.frame, self.CP, lfa_icon))

    # 5 Hz ACC options
    if self.frame % 20 == 0 and self.long_active_ecu and not can_canfd_blended:
      can_sends.extend(hyundaican.create_acc_opt(self.packer, self.CP))

    # 2 Hz front radar options
    if self.frame % 50 == 0 and self.long_active_ecu and not can_canfd_blended:
      can_sends.append(hyundaican.create_frt_radar_opt(self.packer))

    return can_sends

  def create_canfd_msgs(self, now_nanos, apply_steer_req, apply_torque, apply_angle, set_speed_in_units, accel, stopping,
                        hud_control, CS, CC, starpilot_toggles, lka_icon, lfa_icon, ev9_ccnc_steering_active=None):
    can_sends = []

    lka_steering = self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING
    lka_steering_long = lka_steering and self.long_active_ecu
    ccnc_non_hda2 = self.CP.flags & HyundaiFlags.CCNC and not lka_steering
    # If suppression fails, card.py strips longitudinal ownership and Panda's
    # LONG flag. The complete EV9 reconstruction profile therefore runs only
    # while this process still owns longitudinal control.
    ev9_long_active = self.CP.carFingerprint == CAR.KIA_EV9 and self.long_active_ecu
    cruise_state = getattr(CS.out, "cruiseState", None)
    cruise_available = bool(getattr(cruise_state, "available", False))
    ev9_main_mode = bool(getattr(CS, "ev9_cruise_main_on", cruise_available)) and not getattr(CS.out, "accFaulted", False)
    use_egmp_dynamic_long_tuning = egmp_dynamic_longitudinal_tuning(self.CP) and self.long_active_ecu and \
                                   CC.actuators.longControlState in (LongCtrlState.starting, LongCtrlState.pid, LongCtrlState.stopping)
    use_egmp_smoothed_accel = use_egmp_dynamic_long_tuning and (
      CC.actuators.accel >= self._ioniq_6_long_tuning.actual_accel or
      self._ioniq_6_long_tuning.launch_active or
      self._ioniq_6_long_tuning.stopping
    )

    # steering control
    preserve_stock_lkas = bool(self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING) and not self.long_active_ecu
    angle_lkas_alt = bool(self.CP.flags & HyundaiFlags.CANFD_ANGLE_STEERING and
                          self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT)
    ccnc_angle_long = self.CP.carFingerprint in CANFD_ANGLE_LONGITUDINAL_CAR and \
      self.CP.flags & HyundaiFlags.CCNC and angle_lkas_alt and self.long_active_ecu
    steering_msg_active = apply_steer_req
    ev9_panda_faulted = ev9_long_active and bool(getattr(CS, "panda_faulted", True))
    if angle_lkas_alt:
      # Angle LKAS_ALT cars fault if the angle-steering status drops inactive during torque limiting.
      # Hold the angle status active while lateral is active; VM/safety limits handle actuation.
      steering_msg_active = CC.latActive
    if ev9_panda_faulted:
      # A recovered/sticky Panda fault can be acceptable for completing a
      # neutral ownership handoff, but never for vehicle actuation. Preserve
      # the required steering stream with an inactive request at the measured
      # angle and zero torque reduction gain.
      steering_msg_active = False
      apply_torque = 0
      apply_angle = float(getattr(CS, "mdps_steering_angle", CS.out.steeringAngleDeg))

    gear = getattr(getattr(CS, "out", None), "gearShifter", None)
    drive_gear = gear == structs.CarState.GearShifter.drive
    ev9_actuation_permitted = not ev9_panda_faulted
    if ev9_long_active:
      abort_reason = ev9_actuation_abort_reason(
        bool(CC.enabled or CC.latActive),
        bool(CS.out.canValid),
        bool(getattr(CS, "openpilot_radar_valid", False)),
        bool(getattr(CS, "panda_faulted", True)),
        hyundaicanfd.ev9_scc_control_baseline_available(),
      )
      ev9_actuation_permitted = abort_reason == EV9ActuationAbortReason.NONE
      if abort_reason != self._ev9_actuation_fault_reason:
        if abort_reason == EV9ActuationAbortReason.NONE:
          carlog.warning(f"EV9 ACTUATION INHIBIT CLEARED: {self._ev9_actuation_fault_reason.name}")
        else:
          carlog.error(f"EV9 ACTUATION INHIBITED: {abort_reason.name}")
        self._ev9_actuation_fault_reason = abort_reason
      if self.frame % 100 == 0:
        actuation_status = "".join((
          f"EV9 ACTUATION: permitted={ev9_actuation_permitted}, enabled={CC.enabled}, ",
          f"requestedAccel={accel:.3f}, vEgo={CS.out.vEgo:.3f}",
        ))
        carlog.warning(actuation_status)
    if angle_lkas_alt:
      steering_msg_active = bool(steering_msg_active and drive_gear)
    openpilot_owns_lka_alt = angle_lkas_alt and drive_gear and (CC.latActive or CC.enabled)
    if not ev9_long_active and bool(getattr(CS.out, "standstill", False)) and not CC.latActive:
      openpilot_owns_lka_alt = False
    forward_stock_lkas = angle_lkas_alt and not openpilot_owns_lka_alt
    ev9_direct_angle_mode = ev9_long_active
    if not forward_stock_lkas and not ev9_direct_angle_mode:
      can_sends.extend(hyundaicanfd.create_steering_messages(self.packer, self.CP, self.CAN, CC.enabled,
                                                             steering_msg_active, apply_torque, apply_angle,
                                                             CS.stock_lfa_msg,
                                                             CS.stock_lkas_msg if preserve_stock_lkas else None,
                                                             lka_icon=lka_icon))
    if ev9_direct_angle_mode:
      measured_angle = float(getattr(CS, "mdps_steering_angle", CS.out.steeringAngleDeg))
      inactive_steering = hyundaicanfd.create_ev9_inactive_steering_messages(
        self.packer, self.CAN, measured_angle, self.frame,
      )
      # 0x12A is part of Panda's full host lease and remains a neutral 100 Hz
      # status stream in every gear. Only 0xCB changes from inactive status to
      # the safety-limited direct angle command in Drive.
      can_sends.append(inactive_steering[0])
      if drive_gear:
        direct_active = should_send_ev9_direct_angle_command(
          drive_gear, CC.latActive,
        ) and ev9_actuation_permitted and not getattr(CS, "mdps_lka_angle_fault", False)
        can_sends.append(hyundaicanfd.create_ev9_direct_angle_command(
          self.packer, self.CAN, apply_angle if direct_active else measured_angle,
          direct_active, apply_torque if direct_active else 0.0, self.frame,
        ))
      else:
        can_sends.append(inactive_steering[1])
    elif ccnc_angle_long:
      direct_steering_active = drive_gear and CC.latActive and self.direct_angle_request_allowed and not CS.angle_steering_fault
      inactive_steering_angle = float(np.clip(CS.angle_steering_angle,
                                              -self.params.ANGLE_LIMITS.STEER_ANGLE_MAX,
                                              self.params.ANGLE_LIMITS.STEER_ANGLE_MAX))
      if drive_gear:
        can_sends.append(hyundaicanfd.create_angle_adas_cmd(
          self.packer, self.CAN,
          apply_angle if direct_steering_active else inactive_steering_angle,
          direct_steering_active, apply_torque if direct_steering_active else 0.0,
        ))
      else:
        can_sends.extend(hyundaicanfd.create_inactive_angle_steering_messages(
          self.packer, self.CAN, inactive_steering_angle,
        ))

    # prevent LFA from activating on LKA steering cars by sending "no lane lines detected" to ADAS ECU
    suppress_lfa = bool(lka_steering)
    if angle_lkas_alt:
      # LKAS_ALT and its camera companion must move together: either openpilot
      # owns both messages or panda forwards both stock messages.
      suppress_lfa = bool(lka_steering and openpilot_owns_lka_alt)
    if self.frame % 5 == 0 and suppress_lfa:
      can_sends.append(hyundaicanfd.create_suppress_lfa(self.packer, self.CAN, CS.lfa_block_msg,
                                                        self.CP.flags & HyundaiFlags.CANFD_LKA_STEERING_ALT))

    # LFA and HDA icons
    if self.frame % 5 == 0 and (not lka_steering or lka_steering_long):
      if ev9_long_active:
        dash_scene = getattr(CS, "ev9_dash_scene", None)
        can_sends.extend(hyundaicanfd.create_ccnc_angle_long_status_messages(
          self.packer, self.CP, self.CAN, self.frame // 5, CC.enabled, ev9_main_mode,
          CC.hudControl, CS.out, CS.is_metric,
          # EV9's temporary angle lockout deliberately drops latActive while
          # AOL remains available. Keep the reconstructed wheel grey during
          # that non-actuating interval; steering_active below remains gated by
          # the full actuation interlock.
          steering_available=ev9_reconstructed_steering_available(
            CC.latActive, CC.enabled, bool(getattr(CS, "ev9_always_on_lateral_enabled", False)),
          ),
          steering_active=bool(ev9_ccnc_steering_active and ev9_actuation_permitted),
          hba_icon=CS.hba_icon, dash_scene=dash_scene,
        ))
      elif ccnc_non_hda2:
        can_sends.extend(hyundaicanfd.create_ccnc(self.packer, self.CAN, self.long_active_ecu, CC.enabled, CC.hudControl,
                                                  CC.leftBlinker, CC.rightBlinker, CS.msg_161, CS.msg_162, CS.msg_1b5,
                                                  CS.is_metric, CS.out, CS.out.cruiseState.available, lfa_icon))
      else:
        can_sends.append(hyundaicanfd.create_lfahda_cluster(self.packer, self.CAN, CC.enabled, CS.stock_lfahda_cluster_msg,
                                                            lfa_icon=lfa_icon))

    # blinkers
    if lka_steering and self.CP.flags & HyundaiFlags.ENABLE_BLINKERS:
      can_sends.extend(hyundaicanfd.create_spas_messages(self.packer, self.CAN, CC.leftBlinker, CC.rightBlinker))

    lane_change_ui_side = None
    if self.CP.carFingerprint == CAR.HYUNDAI_IONIQ_6:
      if CC.leftBlinker and not CC.rightBlinker:
        lane_change_ui_side = "left"
      elif CC.rightBlinker and not CC.leftBlinker:
        lane_change_ui_side = "right"

      if lane_change_ui_side != self._ioniq_6_lane_change_ui_side:
        self._ioniq_6_lane_change_ui_side = lane_change_ui_side
        self._ioniq_6_lane_change_ui_frames = 0

      if lane_change_ui_side is None or not self.long_active_ecu:
        self._ioniq_6_lane_change_ui_frames = 0
      else:
        # The stock Ioniq 6 lane-change animation stops when the ADAS ECU is disabled,
        # so replay the captured ECAN cluster frames ourselves while OP long is active.
        can_sends.extend(hyundaicanfd.create_ioniq_6_cluster_lane_change_messages(self.CAN,
                                                                                   self._ioniq_6_lane_change_ui_frames,
                                                                                   lane_change_ui_side))
        self._ioniq_6_lane_change_ui_frames += 1

    if self.long_active_ecu:
      if lka_steering:
        adrv_messages = hyundaicanfd.create_adrv_messages(self.packer, self.CAN, self.frame)
        if ev9_long_active:
          adrv_messages = filter_ev9_adrv_replay_messages(adrv_messages)
          counter_divisors = {0x160: 2, 0x1DA: 100, 0x1EA: 5, 0x200: 5, 0x345: 20}
          adrv_messages = [hyundaicanfd.create_ev9_adrv_message(msg[0], self.CAN.ECAN, self.frame // counter_divisors[msg[0]])
                           for msg in adrv_messages]
          status_messages = ((0x1E0, 5), (0x38C, 20))
          adrv_messages.extend(hyundaicanfd.create_ev9_adrv_message(address, self.CAN.ECAN, self.frame // divisor)
                               for address, divisor in status_messages if self.frame % divisor == 0)
          if self.frame % 5 == 0:
            blindspot_inputs = get_ev9_blindspot_warning_inputs(CS, now_nanos)
            left_escalated = blindspot_inputs.left_detected and blindspot_inputs.left_stalk_active
            right_escalated = blindspot_inputs.right_detected and blindspot_inputs.right_stalk_active
            left_warning = update_blindspot_warning(
              self._left_blindspot_warning, left_escalated, blindspot_inputs.left_stalk_active,
            )
            right_warning = update_blindspot_warning(
              self._right_blindspot_warning, right_escalated, blindspot_inputs.right_stalk_active,
            )
            adrv_messages.extend(hyundaicanfd.create_ccnc_blindspot_status_messages(
              self.packer, self.CP, self.CAN, self.frame // 5,
              blindspot_inputs.left_detected, blindspot_inputs.right_detected,
              left_escalated, right_escalated, drive_gear,
              left_warning.mirror_lamp_active, right_warning.mirror_lamp_active,
              left_warning.sound_active, right_warning.sound_active,
            ))
        can_sends.extend(adrv_messages)
        # Ioniq 5/6: front radar treats ADAS_DRV's 0x100 broadcast as its host heartbeat
        # and stops publishing object tracks when it disappears. Spoof it periodically on
        # PT bus so the radar keeps tracking.
        standard_radar_heartbeat = self.CP.carFingerprint in CANFD_RADAR_LIVE_LONGITUDINAL_CAR and self.frame % 4 == 0
        ev9_radar_heartbeat = ev9_long_active
        if standard_radar_heartbeat or ev9_radar_heartbeat:
          heartbeat_counter = self.frame if ev9_radar_heartbeat else self.frame // 4
          can_sends.append(hyundaicanfd.create_accelerator_brake_alt_spoof(0, heartbeat_counter, CS.out.brakePressed,
                                                                            CS.out.gasPressed, self.CP.carFingerprint))
      elif not ccnc_non_hda2:
        can_sends.extend(hyundaicanfd.create_fca_warning_light(self.packer, self.CAN, self.frame))
      if self.CP.carFingerprint == CAR.HYUNDAI_IONIQ_6 and self.frame % 5 == 0:
        rear_stale = now_nanos - CS.blindspots_rear_corners_ts > CANFD_BLINDSPOT_STATUS_STALE_NS
        front_stale = now_nanos - CS.blindspots_front_corner_1_ts > CANFD_BLINDSPOT_STATUS_STALE_NS
        if CS.blindspots_rear_corners_ts > 0 and CS.blindspots_front_corner_1_ts > 0 and rear_stale and front_stale:
          can_sends.extend(hyundaicanfd.create_blindspot_status_messages(self.packer, self.CAN,
                                                                         CS.blindspots_rear_corners,
                                                                         CS.blindspots_front_corner_1,
                                                                         CS.left_blindspot_from_radar,
                                                                         CS.right_blindspot_from_radar,
                                                                         CC.leftBlinker,
                                                                         CC.rightBlinker))
      if self.CP.carFingerprint == CAR.HYUNDAI_IONIQ_6 and lane_change_ui_side is None:
        can_sends.extend(hyundaicanfd.create_ioniq_6_cluster_blindspot_messages(self.CAN, self.frame,
                                                                                 CS.left_blindspot_from_radar,
                                                                                 CS.right_blindspot_from_radar,
                                                                                 CC.leftBlinker,
                                                                                 CC.rightBlinker))
      if self.frame % 2 == 0:
        lead_visible, lead_distance, lead_rel_speed = self._get_canfd_scc_lead_state(
          CC, CS, now_nanos, physical_lead_only=ev9_long_active,
        )
        scc_enabled, scc_accel, scc_stopping, scc_gas_override = ev9_longitudinal_scc_command(
          CC.enabled, accel, stopping, CC.cruiseControl.override,
          actuation_permitted=ev9_actuation_permitted,
        ) if ev9_long_active else (CC.enabled, accel, stopping, CC.cruiseControl.override)
        acc_kwargs = {
          "main_mode_acc": int(ev9_main_mode if ev9_long_active else CS.out.cruiseState.available),
          "direct_accel": True,
          "jerk_lower": 5.0,
          "jerk_upper": 3.0 if CC.actuators.longControlState == LongCtrlState.pid else 1.0,
          "lead_distance": lead_distance,
          "lead_rel_speed": lead_rel_speed,
          "lead_visible": lead_visible,
        }
        if use_egmp_dynamic_long_tuning:
          if use_egmp_smoothed_accel:
            acc_kwargs["jerk_lower"] = self._ioniq_6_long_tuning.jerk_lower
            acc_kwargs["jerk_upper"] = self._ioniq_6_long_tuning.jerk_upper
        if ev9_long_active:
          self._ev9_stop_state = update_ev9_longitudinal_stop_state(
            self._ev9_stop_state, scc_enabled and not scc_gas_override, scc_stopping, float(CS.out.vEgo),
          )
          scc_starting = CC.actuators.longControlState == LongCtrlState.starting
          if scc_enabled and not scc_gas_override:
            scc_accel_raw, scc_accel_value, scc_jerk_upper = shape_ev9_longitudinal_accel(
              self.accel_last, scc_accel, float(CS.out.vEgo), scc_starting, scc_stopping, self._ev9_stop_state,
            )
          else:
            scc_accel_raw = 0.0
            scc_accel_value = 0.0
            scc_jerk_upper = EV9_ACTUATION_JERK_UPPER
          can_sends.append(hyundaicanfd.create_ev9_acc_control(
            self.packer, self.CAN, self._ev9_scc_counter, scc_enabled, scc_accel_raw, scc_accel_value,
            self._ev9_stop_state.stop_request, self._ev9_stop_state.cruise_standstill, scc_gas_override,
            set_speed_in_units, int(ev9_main_mode), lead_distance, lead_rel_speed, lead_visible, float(CS.out.vEgo),
            jerk_lower=EV9_ACTUATION_JERK_LOWER,
            jerk_upper=scc_jerk_upper,
          ))
          self._ev9_scc_counter = (self._ev9_scc_counter + 1) & 0xFF
        else:
          can_sends.append(hyundaicanfd.create_acc_control(
            self.packer, self.CAN, scc_enabled, self.accel_last, scc_accel, scc_stopping, scc_gas_override,
            set_speed_in_units, hud_control, cruise_info=CS.cruise_info if ccnc_non_hda2 else None, **acc_kwargs,
          ))
        self.accel_last = scc_accel_value if ev9_long_active else scc_accel
    else:
      # button presses
      if (self.frame - self.last_button_frame) * DT_CTRL > 0.25:
        # cruise cancel - suppress when stock ACC is the fallback (ECU disable failed),
        # so openpilot doesn't fight/cancel the user's stock cruise
        if CC.cruiseControl.cancel and not self.ecu_disable_failed:
          if self.CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS:
            can_sends.append(hyundaicanfd.create_acc_cancel(self.packer, self.CP, self.CAN, CS.cruise_info))
            self.last_button_frame = self.frame
          else:
            for _ in range(20):
              can_sends.append(hyundaicanfd.create_buttons(self.packer, self.CP, self.CAN, CS.buttons_counter + 1, Buttons.CANCEL))
            self.last_button_frame = self.frame

        # cruise standstill resume
        elif CC.cruiseControl.resume:
          if self.CP.flags & HyundaiFlags.CANFD_ALT_BUTTONS:
            # TODO: resume for alt button cars
            pass
          else:
            for _ in range(20):
              can_sends.append(hyundaicanfd.create_buttons(self.packer, self.CP, self.CAN, CS.buttons_counter + 1, Buttons.RES_ACCEL))
            self.last_button_frame = self.frame
        else:
          can_sends.extend(self._create_canfd_redneck_button_messages(CS))

    return can_sends
