import math

from cereal import log
from opendbc.car.subaru.values import CAR as SUBARU_CAR
from openpilot.selfdrive.controls.lib.latcontrol import LatControl

# TODO This is speed dependent
STEER_ANGLE_SATURATION_THRESHOLD = 2.5  # Degrees

_ASCENT_ANGLE_TRACKING_GAIN = 0.25
_ASCENT_ANGLE_TRACKING_MAX_CORRECTION = 8.0
_ASCENT_ANGLE_TRACKING_MIN_SPEED = 5.0


def _ascent_angle_tracking_target(target_angle: float, steering_angle: float,
                                  v_ego: float, steering_pressed: bool) -> float:
  if steering_pressed or v_ego < _ASCENT_ANGLE_TRACKING_MIN_SPEED:
    return target_angle

  correction = (target_angle - steering_angle) * _ASCENT_ANGLE_TRACKING_GAIN
  correction = max(-_ASCENT_ANGLE_TRACKING_MAX_CORRECTION,
                   min(_ASCENT_ANGLE_TRACKING_MAX_CORRECTION, correction))
  return target_angle + correction


class LatControlAngle(LatControl):
  def __init__(self, CP, CI, dt):
    super().__init__(CP, CI, dt)
    self.sat_check_min_speed = 5.
    self.use_steer_limited_by_safety = CP.brand in ("tesla", "hyundai")
    self.is_ascent = CP.carFingerprint == SUBARU_CAR.SUBARU_ASCENT_2023

  def update(self, active, CS, VM, params, steer_limited_by_safety, desired_curvature, curvature_limited, lat_delay, calibrated_pose, model_data, starpilot_toggles):
    angle_log = log.ControlsState.LateralAngleState.new_message()

    if not active:
      angle_log.active = False
      angle_steers_des = float(CS.steeringAngleDeg)
    else:
      angle_log.active = True
      angle_steers_des = math.degrees(VM.get_steer_from_curvature(-desired_curvature, CS.vEgo, params.roll))
      angle_steers_des += params.angleOffsetDeg

      if self.is_ascent:
        angle_steers_des = _ascent_angle_tracking_target(
          angle_steers_des,
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
