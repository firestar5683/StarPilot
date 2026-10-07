"""Default Silverado acceleration filtering and integral recovery."""

import numpy as np

from opendbc.car import DT_CTRL
from opendbc.car.gm.longitudinal import GMOrdinaryLongitudinalPolicy


class GMTruckLongitudinalPolicy(GMOrdinaryLongitudinalPolicy):
  kp = ((0.0, 5.0, 15.0, 35.0), (0.02, 0.03, 0.028, 0.022))

  def __init__(self):
    self.kp = (self.kp[0], tuple(float(np.float32(value)) for value in self.kp[1]))
    self.reset()

  def reset(self):
    self.filtered_target = None

  def target(self, target: float, speed: float, should_stop: bool) -> float:
    if (self.filtered_target is None or speed < 12.0 or should_stop or target <= -0.65 or
        target < self.filtered_target - 0.45):
      self.filtered_target = float(target)
    else:
      tau = 0.14 if target < self.filtered_target else 0.20
      self.filtered_target += DT_CTRL / (tau + DT_CTRL) * (float(target) - self.filtered_target)
    return self.filtered_target

  def prepare_pid(self, pid, target, error, speed, last_output, accel_limits, *, should_stop=False, has_lead=None):
    super().prepare_pid(pid, target, error, speed, last_output, accel_limits,
                        should_stop=should_stop, has_lead=has_lead)

    light_target = float(np.interp(speed, (8.0, 15.0, 25.0), (0.03, 0.06, 0.10)))
    if (pid.i > 0.0 and last_output > 0.10 and target <= light_target and
        not (speed <= 0.35 and target > -0.40) and
        (last_output - max(target, 0.0) > 0.08 or error <= -0.08)):
      factor = float(np.interp(target, (-0.30, -0.10, -0.02, light_target), (0.20, 0.35, 0.60, 0.98)))
      if error < -0.20:
        factor *= 0.75
      pid.i *= factor

    if pid.i < -0.02 and speed >= 12.0 and target > -0.85 and error > 0.04:
      mismatch = float(target) - float(last_output)
      if mismatch > 0.10:
        release = float(np.interp(max(mismatch, error), (0.10, 0.25, 0.50), (0.0008, 0.0020, 0.0040)))
        pid.i = min(0.0, pid.i + release)
    return False


TRUCK_FRICTION_BRAKE_ENGAGE = 40
TRUCK_FRICTION_BRAKE_RELEASE = 8
TRUCK_FRICTION_BRAKE_IMMEDIATE_ACCEL = -0.85
TRUCK_FOLLOW_MICRO_ACCEL_MAX = 0.55
TRUCK_FOLLOW_MICRO_ACCEL_MIN = -0.10
TRUCK_FOLLOW_MICRO_ACCEL_SLEW = 1.5


def truck_tuning_supported(cp):
  from opendbc.car.gm.values import CAR, is_ordinary_camera_profile
  from opendbc.car.structs import CarParams
  try:
    return (cp.carFingerprint == CAR.CHEVROLET_SILVERADO and
            cp.transmissionType == CarParams.TransmissionType.automatic and
            is_ordinary_camera_profile(cp, longitudinal=True))
  except (AttributeError, TypeError, ValueError):
    return False


class TruckTuning:
  def __init__(self):
    self.enabled = False
    self.follow_accel = 0.0
    self.friction_active = False


def shape_truck_positive_accel(accel: float, v_ego: float, enabled: bool,
                               lead_visible: bool = False, set_speed_error: float = 0.0) -> float:
  if not enabled or accel <= 0.0 or v_ego < 12.0:
    return accel

  low_scale = float(np.interp(v_ego, [12.0, 18.0, 25.0, 35.0], [0.93, 0.84, 0.76, 0.76]))
  mid_scale = float(np.interp(v_ego, [12.0, 18.0, 25.0, 35.0], [0.97, 0.91, 0.85, 0.85]))

  if lead_visible and set_speed_error > 0.0:
    follow_relief = float(np.interp(set_speed_error, [0.0, 1.0, 2.5, 4.0, 6.0], [0.0, 0.04, 0.10, 0.24, 0.42]))
    low_scale += (1.0 - low_scale) * follow_relief
    mid_scale += (1.0 - mid_scale) * follow_relief

  if accel <= 0.12:
    return accel * low_scale
  if accel <= 0.35:
    return float(np.interp(accel, [0.12, 0.35], [0.12 * low_scale, 0.35 * mid_scale]))
  if accel <= 0.65:
    return float(np.interp(accel, [0.35, 0.65], [0.35 * mid_scale, 0.65]))
  return accel

def smooth_truck_follow_accel(accel: float, previous_accel: float, v_ego: float,
                              enabled: bool, lead_visible: bool, stopping: bool) -> float:
  if (
    not enabled or not lead_visible or stopping or v_ego < 25.0 or
    accel > TRUCK_FOLLOW_MICRO_ACCEL_MAX or accel < TRUCK_FOLLOW_MICRO_ACCEL_MIN or
    previous_accel > TRUCK_FOLLOW_MICRO_ACCEL_MAX or previous_accel < TRUCK_FOLLOW_MICRO_ACCEL_MIN
  ):
    return accel

  max_delta = TRUCK_FOLLOW_MICRO_ACCEL_SLEW * DT_CTRL * 4
  return previous_accel + float(np.clip(accel - previous_accel, -max_delta, max_delta))

def shape_truck_pitch_accel(pitch_accel: float, v_ego: float, enabled: bool) -> float:
  if not enabled:
    return pitch_accel

  scale = float(np.interp(v_ego, [8.0, 15.0, 25.0, 35.0], [0.60, 0.45, 0.30, 0.25]))
  return pitch_accel * scale

def shape_truck_friction_brake(apply_brake: int, accel_cmd: float, stopping: bool, active: bool) -> tuple[int, bool]:
  if apply_brake <= 0:
    return 0, False

  # Preserve full brake response for stop control and meaningful deceleration.
  if stopping or accel_cmd <= TRUCK_FRICTION_BRAKE_IMMEDIATE_ACCEL:
    return apply_brake, True

  if active:
    if apply_brake <= TRUCK_FRICTION_BRAKE_RELEASE:
      return 0, False
    return apply_brake, True

  if apply_brake >= TRUCK_FRICTION_BRAKE_ENGAGE:
    return apply_brake, True

  # Keep tiny corrections in the continuous gas/regen torque path. Switching
  # to friction also forces max regen, which makes a small request perceptible.
  return 0, False
