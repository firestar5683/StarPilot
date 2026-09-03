import math

from cereal import log
from opendbc.car.honda.carcontroller import get_civic_bosch_modified_steering_pressed
from opendbc.car.honda.values import CAR as HONDA, HondaFlags
from openpilot.starpilot.common.testing_grounds import testing_ground
from openpilot.selfdrive.controls.lib.latcontrol import LatControl
from openpilot.selfdrive.controls.lib.latcontrol_vehicle_tunes import (
  RAV4_TSS2_CARS,
  SUBARU_IMPREZA_CARS,
  get_honda_crv_5g_pid_output,
  get_rav4_tss2_pid_output,
  get_subaru_impreza_pid_output_scale,
)
from openpilot.common.pid import PIDController

HONDA_PID_GAIN_SCALE_MIN = 0.1
HONDA_PID_GAIN_SCALE_MAX = 4.0


def civic_bosch_modified_lateral_testing_ground_active() -> bool:
  return testing_ground.use("8", "B")


def get_honda_lateral_pid_gain_scale(value) -> float:
  try:
    scale = float(value)
  except (TypeError, ValueError):
    return 1.0
  if not math.isfinite(scale):
    return 1.0
  return min(max(scale, HONDA_PID_GAIN_SCALE_MIN), HONDA_PID_GAIN_SCALE_MAX)


def scale_lateral_pid_gain_values(values, scale: float) -> list[float]:
  return [float(value) * scale for value in values]


def get_civic_bosch_modified_pid_output_scale(desired_angle_deg: float, desired_angle_delta_deg: float, v_ego: float) -> float:
  abs_angle = abs(desired_angle_deg)
  speed_weight = min(max((v_ego - 4.0) / 10.0, 0.0), 1.0)
  center_speed_weight = 0.70 + (0.30 * speed_weight)
  center_weight = min(max((18.0 - abs_angle) / 18.0, 0.0), 1.0)
  mid_turn_weight = min(max((abs_angle - 10.0) / 10.0, 0.0), 1.0)
  angle_weight = min(max((abs_angle - 18.0) / 10.0, 0.0), 1.0)
  phase = desired_angle_deg * desired_angle_delta_deg

  is_left = desired_angle_deg > 0.0
  center_taper = 0.32
  mid_turn_scale = 0.12 if is_left else -0.10
  mid_turn_turn_in_scale = 0.08 if is_left else -0.08
  mid_turn_unwind_scale = -0.05 if is_left else -0.08
  base_scale = 0.12 if is_left else 0.10
  turn_in_scale = 0.12 if is_left else 0.12
  unwind_scale = 0.14 if is_left else 0.18

  scale = 1.0 - (center_speed_weight * center_weight * center_taper)
  scale += speed_weight * mid_turn_weight * mid_turn_scale
  scale += speed_weight * angle_weight * base_scale
  if phase > 0.2:
    scale += speed_weight * mid_turn_weight * mid_turn_turn_in_scale
    scale += speed_weight * angle_weight * turn_in_scale
  elif phase < -0.2:
    scale += speed_weight * mid_turn_weight * mid_turn_unwind_scale
    scale -= speed_weight * angle_weight * unwind_scale

  return max(scale, 0.70)


def get_civic_bosch_modified_pid_output_alpha(desired_angle_deg: float, desired_angle_delta_deg: float,
                                              v_ego: float, output_torque: float, prev_output_torque: float) -> float:
  abs_angle = abs(desired_angle_deg)
  if abs_angle < 0.75 or abs_angle > 22.0:
    return 1.0

  speed_weight = min(max((v_ego - 4.0) / 10.0, 0.0), 1.0)
  onset = min(max((abs_angle - 0.75) / 5.25, 0.0), 1.0)
  cutoff = min(max((22.0 - abs_angle) / 8.0, 0.0), 1.0)
  band_weight = onset * cutoff
  small_curve_weight = min(max((12.0 - abs_angle) / 6.0, 0.0), 1.0)
  large_turn_weight = min(max((abs_angle - 16.0) / 6.0, 0.0), 1.0)
  transition_weight = min(abs(desired_angle_delta_deg) / 0.35, 1.0)
  sign_change_weight = 1.0 if (output_torque * prev_output_torque) < 0.0 else 0.0

  smoothing = band_weight * (0.36 + (0.22 * speed_weight) + (0.12 * transition_weight) + (0.12 * sign_change_weight))
  smoothing *= 1.0 + (0.35 * small_curve_weight)
  smoothing *= 1.0 - (0.50 * large_turn_weight)
  return min(max(1.0 - smoothing, 0.14), 1.0)


class LatControlPID(LatControl):
  def __init__(self, CP, CI, dt):
    super().__init__(CP, CI, dt)
    self.base_kp_bp = [float(value) for value in CP.lateralTuning.pid.kpBP]
    self.base_kp_v = [float(value) for value in CP.lateralTuning.pid.kpV]
    self.base_ki_bp = [float(value) for value in CP.lateralTuning.pid.kiBP]
    self.base_ki_v = [float(value) for value in CP.lateralTuning.pid.kiV]
    self.pid = PIDController((self.base_kp_bp, self.base_kp_v),
                             (self.base_ki_bp, self.base_ki_v),
                             pos_limit=self.steer_max, neg_limit=-self.steer_max)
    self.ff_factor = CP.lateralTuning.pid.kf
    self.get_steer_feedforward = CI.get_steer_feedforward_function()
    self.is_honda_pid_lateral = CP.brand == "honda"
    self.is_honda_accord_11g = self.is_honda_pid_lateral and CP.carFingerprint == HONDA.HONDA_ACCORD_11G
    self.honda_lateral_pid_kp_scale = 1.0
    self.honda_lateral_pid_ki_scale = 1.0
    self.is_civic_bosch_modified = CP.carFingerprint == HONDA.HONDA_CIVIC_BOSCH and bool(CP.flags & HondaFlags.EPS_MODIFIED)
    self.is_honda_crv_5g = CP.carFingerprint == HONDA.HONDA_CRV_5G
    self.is_subaru_impreza = CP.carFingerprint in SUBARU_IMPREZA_CARS
    self.is_rav4_tss2 = CP.carFingerprint in RAV4_TSS2_CARS
    self.prev_angle_steers_des_no_offset = 0.0
    self.modified_civic_steering_pressed_filter_s = 0.0
    self.modified_civic_steering_pressed_prev = False
    self.prev_output_torque = 0.0

  def update_honda_lateral_pid_gain_scale(self, starpilot_toggles):
    if not self.is_honda_pid_lateral or self.is_honda_accord_11g:
      return

    kp_scale = get_honda_lateral_pid_gain_scale(getattr(starpilot_toggles, "honda_lateral_pid_kp_scale", 1.0))
    ki_scale = get_honda_lateral_pid_gain_scale(getattr(starpilot_toggles, "honda_lateral_pid_ki_scale", 1.0))
    if math.isclose(kp_scale, self.honda_lateral_pid_kp_scale) and math.isclose(ki_scale, self.honda_lateral_pid_ki_scale):
      return

    self.honda_lateral_pid_kp_scale = kp_scale
    self.honda_lateral_pid_ki_scale = ki_scale
    self.pid._k_p = [self.base_kp_bp, scale_lateral_pid_gain_values(self.base_kp_v, kp_scale)]
    self.pid._k_i = [self.base_ki_bp, scale_lateral_pid_gain_values(self.base_ki_v, ki_scale)]

  def update(self, active, CS, VM, params, steer_limited_by_safety, desired_curvature, curvature_limited, lat_delay, calibrated_pose, model_data, starpilot_toggles):
    self.update_honda_lateral_pid_gain_scale(starpilot_toggles)

    pid_log = log.ControlsState.LateralPIDState.new_message()
    pid_log.steeringAngleDeg = float(CS.steeringAngleDeg)
    pid_log.steeringRateDeg = float(CS.steeringRateDeg)

    angle_steers_des_no_offset = math.degrees(VM.get_steer_from_curvature(-desired_curvature, CS.vEgo, params.roll))
    angle_steers_des = angle_steers_des_no_offset + params.angleOffsetDeg
    error = angle_steers_des - CS.steeringAngleDeg

    pid_log.steeringAngleDesiredDeg = angle_steers_des
    pid_log.angleError = error
    if not active:
      output_torque = 0.0
      pid_log.active = False
      self.prev_angle_steers_des_no_offset = angle_steers_des_no_offset
      self.modified_civic_steering_pressed_filter_s = 0.0
      self.modified_civic_steering_pressed_prev = False
      self.prev_output_torque = 0.0

    else:
      # offset does not contribute to resistive torque
      ff = self.ff_factor * self.get_steer_feedforward(angle_steers_des_no_offset, CS.vEgo)
      steering_pressed = CS.steeringPressed
      if self.is_civic_bosch_modified:
        self.modified_civic_steering_pressed_filter_s, steering_pressed = get_civic_bosch_modified_steering_pressed(
          bool(CS.steeringPressed),
          float(getattr(CS, "steeringTorque", 0.0)),
          float(self.prev_output_torque),
          self.modified_civic_steering_pressed_filter_s,
          self.modified_civic_steering_pressed_prev,
        )
        self.modified_civic_steering_pressed_prev = steering_pressed

      freeze_integrator = steer_limited_by_safety or steering_pressed or CS.vEgo < 5

      output_torque = self.pid.update(error,
                                feedforward=ff,
                                speed=CS.vEgo,
                                freeze_integrator=freeze_integrator)

      if self.is_subaru_impreza:
        raw_output_torque = self.pid.p + self.pid.i + self.pid.d + self.pid.f
        output_torque = raw_output_torque * get_subaru_impreza_pid_output_scale(error)
        output_torque = float(max(min(output_torque, self.steer_max), -self.steer_max))

      if self.is_honda_crv_5g:
        output_torque = get_honda_crv_5g_pid_output(
          output_torque, self.prev_output_torque, angle_steers_des_no_offset, CS.vEgo,
        )
        output_torque = float(max(min(output_torque, self.steer_max), -self.steer_max))

      if self.is_rav4_tss2:
        output_torque = get_rav4_tss2_pid_output(output_torque, self.prev_output_torque,
                                                angle_steers_des_no_offset, CS.vEgo)
        output_torque = float(max(min(output_torque, self.steer_max), -self.steer_max))

      if self.is_civic_bosch_modified and civic_bosch_modified_lateral_testing_ground_active():
        desired_angle_delta = angle_steers_des_no_offset - self.prev_angle_steers_des_no_offset
        output_torque *= get_civic_bosch_modified_pid_output_scale(angle_steers_des_no_offset, desired_angle_delta, CS.vEgo)
        output_alpha = get_civic_bosch_modified_pid_output_alpha(angle_steers_des_no_offset, desired_angle_delta, CS.vEgo,
                                                                 output_torque, self.prev_output_torque)
        output_torque = self.prev_output_torque + (output_alpha * (output_torque - self.prev_output_torque))
        output_torque = float(max(min(output_torque, self.steer_max), -self.steer_max))

      pid_log.active = True
      pid_log.p = float(self.pid.p)
      pid_log.i = float(self.pid.i)
      pid_log.f = float(self.pid.f)
      pid_log.output = float(output_torque)
      pid_log.saturated = bool(self._check_saturation(self.steer_max - abs(output_torque) < 1e-3, CS, steer_limited_by_safety, curvature_limited))
      self.prev_angle_steers_des_no_offset = angle_steers_des_no_offset
      self.prev_output_torque = float(output_torque)

    return output_torque, angle_steers_des, pid_log
