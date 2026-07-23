import numpy as np
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


def get_lateral_active(enabled: bool, active: bool, always_on_lateral_enabled: bool,
                       steer_fault_temporary: bool, steer_fault_permanent: bool,
                       standstill: bool, steer_at_standstill: bool, lateral_check: bool) -> bool:
  lateral_allowed = (enabled and active) or always_on_lateral_enabled
  return lateral_allowed and not steer_fault_temporary and not steer_fault_permanent and \
         (not standstill or steer_at_standstill) and lateral_check

def curv_from_psis(psi_target, psi_rate, vego, action_t):
  vego = np.clip(vego, MIN_SPEED, np.inf)
  curv_from_psi = psi_target / (vego * action_t)
  return 2*curv_from_psi - psi_rate / vego

def get_curvature_from_plan(yaws, yaw_rates, t_idxs, vego, action_t):
  psi_target = np.interp(action_t, t_idxs, yaws)
  psi_rate = yaw_rates[0]
  return curv_from_psis(psi_target, psi_rate, vego, action_t)


_LC_MIN_V_EGO = 5.0
_LC_MIN_PROB = 0.6
_LC_MAX_STD = 0.3
_LC_MIN_WIDTH = 2.6
_LC_MAX_WIDTH = 4.8
_LC_MAX_CORR = 0.004
_LC_MAX_GAIN = 0.30
_LC_SMOOTH_TAU = 0.4


class LaneCenteringController:
  def __init__(self):
    self._correction = 0.0

  def reset(self):
    self._correction = 0.0

  def update(self, model_curvature, model_v2, v_ego, enabled, offset, lat_active, model_valid) -> float:
    model_curvature = float(model_curvature)

    if not model_valid:
      self.reset()
      return model_curvature

    try:
      offset_f = float(offset)
    except (TypeError, ValueError):
      self.reset()
      return model_curvature
    if not np.isfinite(offset_f):
      # Non-finite offset is an untrusted config boundary: hard-reset so NaN
      # never reaches smooth_value.
      self.reset()
      return model_curvature

    if not enabled or not lat_active or v_ego < _LC_MIN_V_EGO:
      self.reset()
      return model_curvature

    try:
      if int(model_v2.meta.laneChangeState) != 0:
        # Lane change in progress: hard-reset to drop any 0.4s filtered residual
        # instead of smearing the pre-change correction into the lane change.
        self.reset()
        return model_curvature
    except (AttributeError, TypeError, ValueError):
      pass

    valid, raw = self._raw_correction(model_v2, v_ego, offset_f)
    target = float(np.clip(raw, -_LC_MAX_CORR, _LC_MAX_CORR)) * _LC_MAX_GAIN if valid else 0.0
    self._correction = float(smooth_value(target, self._correction, _LC_SMOOTH_TAU, dt=DT_CTRL))
    return model_curvature + self._correction

  def _raw_correction(self, model_v2, v_ego, offset) -> tuple[bool, float]:
    try:
      lane_lines = model_v2.laneLines
      probs = model_v2.laneLineProbs
      stds = model_v2.laneLineStds
      if len(lane_lines) < 3 or len(probs) < 3 or len(stds) < 3:
        return False, 0.0
      if int(model_v2.meta.laneChangeState) != 0:
        return False, 0.0
      if probs[1] < _LC_MIN_PROB or probs[2] < _LC_MIN_PROB:
        return False, 0.0
      if stds[1] > _LC_MAX_STD or stds[2] > _LC_MAX_STD:
        return False, 0.0

      left_x = np.asarray(lane_lines[1].x, dtype=float)
      left_y = np.asarray(lane_lines[1].y, dtype=float)
      right_x = np.asarray(lane_lines[2].x, dtype=float)
      right_y = np.asarray(lane_lines[2].y, dtype=float)
      if (left_x.size < 2 or left_x.size != left_y.size or
          right_x.size < 2 or right_x.size != right_y.size):
        return False, 0.0
      if not (np.isfinite(left_x).all() and np.isfinite(left_y).all() and
              np.isfinite(right_x).all() and np.isfinite(right_y).all()):
        return False, 0.0
      if not (np.all(np.diff(left_x) > 0) and np.all(np.diff(right_x) > 0)):
        return False, 0.0

      lookahead = float(np.clip(v_ego * 1.0, 8.0, 35.0))
      left = float(np.interp(lookahead, left_x, left_y))
      right = float(np.interp(lookahead, right_x, right_y))
      width = right - left
      if width < _LC_MIN_WIDTH or width > _LC_MAX_WIDTH:
        return False, 0.0

      center_y = 0.5 * (left + right)

      pos_x = np.asarray(model_v2.position.x, dtype=float)
      pos_y = np.asarray(model_v2.position.y, dtype=float)
      if pos_x.size < 2 or pos_x.size != pos_y.size:
        return False, 0.0
      if not (np.isfinite(pos_x).all() and np.isfinite(pos_y).all() and np.all(np.diff(pos_x) > 0)):
        return False, 0.0
      model_y = float(np.interp(lookahead, pos_x, pos_y))
      error = (center_y + offset) - model_y
      raw = 2.0 * error / (lookahead ** 2)
      return True, float(raw)
    except (AttributeError, IndexError, TypeError, ValueError):
      return False, 0.0
