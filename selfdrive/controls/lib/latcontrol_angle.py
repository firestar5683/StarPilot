import math

from cereal import log
from opendbc.car.subaru.values import CAR as SUBARU_CAR
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.selfdrive.controls.lib.steering_saturation import STEER_ANGLE_SATURATION_THRESHOLD

_ASCENT_ANGLE_TRACKING_GAIN = 0.25
_ASCENT_ANGLE_TRACKING_MAX_CORRECTION = 8.0
_ASCENT_ANGLE_TRACKING_MIN_SPEED = 9.0
_ASCENT_ANGLE_TRACKING_FULL_SPEED = 15.0
_ASCENT_ANGLE_TRACKING_TURN_START = 15.0
_ASCENT_ANGLE_TRACKING_TURN_FULL = 35.0
_ASCENT_LOW_SPEED_FILTER_MAX_SPEED = 10.0
_ASCENT_LOW_SPEED_FILTER_CENTER_ANGLE = 35.0
_ASCENT_LOW_SPEED_FILTER_TIME_CONSTANT = 0.18


def _clipped_weight(value: float, start: float, end: float) -> float:
  return max(0.0, min(1.0, (value - start) / (end - start)))


def _ascent_angle_tracking_target(target_angle: float, steering_angle: float,
                                  v_ego: float, steering_pressed: bool) -> float:
  if steering_pressed:
    return target_angle

  speed_weight = _clipped_weight(v_ego, _ASCENT_ANGLE_TRACKING_MIN_SPEED, _ASCENT_ANGLE_TRACKING_FULL_SPEED)
  turn_weight = _clipped_weight(abs(target_angle), _ASCENT_ANGLE_TRACKING_TURN_START, _ASCENT_ANGLE_TRACKING_TURN_FULL)
  correction = (target_angle - steering_angle) * _ASCENT_ANGLE_TRACKING_GAIN * max(speed_weight, turn_weight)
  correction = max(-_ASCENT_ANGLE_TRACKING_MAX_CORRECTION,
                   min(_ASCENT_ANGLE_TRACKING_MAX_CORRECTION, correction))
  return target_angle + correction


def _ascent_low_speed_angle_target(target_angle: float, previous_target: float,
                                   v_ego: float, steering_pressed: bool, dt: float) -> float:
  if steering_pressed:
    return target_angle

  speed_weight = 1.0 - _clipped_weight(v_ego, 0.0, _ASCENT_LOW_SPEED_FILTER_MAX_SPEED)
  center_weight = 1.0 - _clipped_weight(abs(target_angle), 0.0, _ASCENT_LOW_SPEED_FILTER_CENTER_ANGLE)
  time_constant = _ASCENT_LOW_SPEED_FILTER_TIME_CONSTANT * speed_weight * center_weight
  if time_constant <= 0.0:
    return target_angle

  alpha = dt / (time_constant + dt)
  return previous_target + alpha * (target_angle - previous_target)


class LatControlAngle(LatControl):
  def __init__(self, CP, CI, dt):
    super().__init__(CP, CI, dt)
    self.sat_check_min_speed = 5.
    self.use_steer_limited_by_safety = CP.brand in ("tesla", "hyundai")
    self.is_ascent = CP.carFingerprint == SUBARU_CAR.SUBARU_ASCENT_2023
    self.ascent_angle_target = None

  def update(self, active, CS, VM, params, steer_limited_by_safety, desired_curvature, curvature_limited, lat_delay, calibrated_pose, model_data, starpilot_toggles):
    angle_log = log.ControlsState.LateralAngleState.new_message()

    if not active:
      angle_log.active = False
      angle_steers_des = float(CS.steeringAngleDeg)
      self.ascent_angle_target = angle_steers_des
    else:
      angle_log.active = True
      angle_steers_des = math.degrees(VM.get_steer_from_curvature(-desired_curvature, CS.vEgo, params.roll))
      angle_steers_des += params.angleOffsetDeg

      if self.is_ascent:
        if self.ascent_angle_target is None:
          self.ascent_angle_target = float(CS.steeringAngleDeg)
        self.ascent_angle_target = _ascent_low_speed_angle_target(
          angle_steers_des,
          self.ascent_angle_target,
          CS.vEgo,
          bool(getattr(CS, "steeringPressed", False)),
          self.dt,
        )
        angle_steers_des = _ascent_angle_tracking_target(
          self.ascent_angle_target,
          CS.steeringAngleDeg,
          CS.vEgo,
          bool(getattr(CS, "steeringPressed", False)),
        )

    if self.use_steer_limited_by_safety:
      # these cars' carcontrollers calculate max lateral accel and jerk, so we can rely on carOutput for saturation
      angle_control_saturated = steer_limited_by_safety
    else:
      # for cars which use a method of limiting torque such as a torque signal (Nissan and Toyota)
      # or relying on EPS (Ford Q3), carOutput does not capture maxing out torque  # TODO: this can be improved
      angle_error = angle_steers_des - CS.steeringAngleDeg
      angle_control_saturated = abs(angle_error) > STEER_ANGLE_SATURATION_THRESHOLD
    angle_log.saturated = bool(self._check_saturation(angle_control_saturated, CS, False, curvature_limited))
    angle_log.steeringAngleDeg = float(CS.steeringAngleDeg)
    angle_log.steeringAngleDesiredDeg = angle_steers_des
    return 0, float(angle_steers_des), angle_log
