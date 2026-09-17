import numpy as np
from cereal import log
from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY
from openpilot.common.realtime import DT_CTRL, DT_MDL

MIN_SPEED = 1.0
CONTROL_N = 17
CAR_ROTATION_RADIUS = 0.0
# This is a turn radius smaller than most cars can achieve
MAX_CURVATURE = 0.2
MAX_VEL_ERR = 5.0  # m/s

# EU guidelines
MAX_LATERAL_JERK = 5.0  # m/s^3
MAX_LATERAL_ACCEL_NO_ROLL = 3.0  # m/s^2


def clamp(val, min_val, max_val):
  clamped_val = float(np.clip(val, min_val, max_val))
  return clamped_val, clamped_val != val

def smooth_value(val, prev_val, tau, dt=DT_MDL):
  alpha = 1 - np.exp(-dt/tau) if tau > 0 else 1
  return alpha * val + (1 - alpha) * prev_val

def clip_curvature(v_ego, prev_curvature, new_curvature, roll, jerk_factor=1.0, lat_accel_factor=1.0) -> tuple[float, bool]:
  # This function respects ISO lateral jerk and acceleration limits + a max curvature
  v_ego = max(v_ego, MIN_SPEED)
  max_curvature_rate = (MAX_LATERAL_JERK * jerk_factor) / (v_ego ** 2)  # inexact calculation, check https://github.com/commaai/openpilot/pull/24755
  new_curvature = np.clip(new_curvature,
                          prev_curvature - max_curvature_rate * DT_CTRL,
                          prev_curvature + max_curvature_rate * DT_CTRL)

  effective_lat_accel = MAX_LATERAL_ACCEL_NO_ROLL * lat_accel_factor
  roll_compensation = roll * ACCELERATION_DUE_TO_GRAVITY
  min_curvature = (-effective_lat_accel + roll_compensation) / v_ego ** 2
  max_curvature = (effective_lat_accel + roll_compensation) / v_ego ** 2
  if lat_accel_factor < 1.0:
    # A tightened maneuver clamp must not clip curvature already being commanded
    # (e.g. lane change on a curve); it only limits further growth.
    min_curvature = min(min_curvature, prev_curvature)
    max_curvature = max(max_curvature, prev_curvature)
  # Saturation is reported against the stock envelope only: riding an intentionally
  # tightened lane-change ceiling is comfort shaping, not steering saturation, and
  # must not trip the "Turn Exceeds Steering Limit" alert.
  stock_min_curvature = (-MAX_LATERAL_ACCEL_NO_ROLL + roll_compensation) / v_ego ** 2
  stock_max_curvature = (MAX_LATERAL_ACCEL_NO_ROLL + roll_compensation) / v_ego ** 2
  limited_accel = bool(new_curvature < stock_min_curvature or new_curvature > stock_max_curvature)
  new_curvature, _ = clamp(new_curvature, min_curvature, max_curvature)

  new_curvature, limited_max_curv = clamp(new_curvature, -MAX_CURVATURE, MAX_CURVATURE)
  return float(new_curvature), limited_accel or limited_max_curv


def get_accel_from_plan(speeds, accels, t_idxs, action_t=DT_MDL, vEgoStopping=0.3):
  if len(speeds) == len(t_idxs):
    v_now = speeds[0]
    a_now = accels[0]
    v_target = np.interp(action_t, t_idxs, speeds)
    a_target = 2 * (v_target - v_now) / (action_t) - a_now
  else:
    v_now = 0.0
    v_target = 0.0
    a_target = 0.0
  should_stop = (v_now < vEgoStopping and a_target < 0.1)
  return a_target, should_stop


# Backward-compatible alias used by tinygrad_modeld.
get_accel_from_plan_tomb_raider = get_accel_from_plan


def lateral_calibration_ready(sm) -> bool:
  return sm.all_checks(['liveCalibration']) and sm['liveCalibration'].calStatus == log.LiveCalibrationData.Status.calibrated


def get_lateral_active(enabled: bool, active: bool, always_on_lateral_enabled: bool,
                       steer_fault_temporary: bool, steer_fault_permanent: bool,
                       standstill: bool, steer_at_standstill: bool, lateral_check: bool,
                       steer_fault_latched: bool = False) -> bool:
  lateral_allowed = (enabled and active) or always_on_lateral_enabled
  return lateral_allowed and not steer_fault_temporary and not steer_fault_permanent and \
         not steer_fault_latched and (not standstill or steer_at_standstill) and lateral_check


def update_lateral_fault_latch(previous_latched: bool, lateral_requested: bool,
                               steer_fault_temporary: bool, reset: bool = False) -> bool:
  """Keep a temporary-fault latch until lateral is no longer requested or reset explicitly."""
  if not lateral_requested or reset:
    return False
  return previous_latched or steer_fault_temporary


def get_kona_non_scc_lateral_active(enabled: bool, active: bool, always_on_lateral_enabled: bool,
                                    steer_fault_temporary: bool, steer_fault_permanent: bool,
                                    standstill: bool, steer_at_standstill: bool, lateral_check: bool,
                                    steering_pressed: bool, previous_lateral_active: bool) -> bool:
  """Avoid the Kona EPS torque fault when AOL is enabled over driver steering input."""
  lateral_active = get_lateral_active(enabled, active, always_on_lateral_enabled,
                                      steer_fault_temporary, steer_fault_permanent,
                                      standstill, steer_at_standstill, lateral_check)
  if not lateral_active:
    return False

  aol_rising_edge = always_on_lateral_enabled and not enabled and not previous_lateral_active
  return not (aol_rising_edge and steering_pressed)


def curv_from_psis(psi_target, psi_rate, vego, action_t):
  vego = np.clip(vego, MIN_SPEED, np.inf)
  curv_from_psi = psi_target / (vego * action_t)
  return 2*curv_from_psi - psi_rate / vego

def get_curvature_from_plan(yaws, yaw_rates, t_idxs, vego, action_t):
  psi_target = np.interp(action_t, t_idxs, yaws)
  psi_rate = yaw_rates[0]
  return curv_from_psis(psi_target, psi_rate, vego, action_t)
