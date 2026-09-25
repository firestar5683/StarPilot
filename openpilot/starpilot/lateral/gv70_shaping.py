"""Exact default first-generation Electrified GV70 shaping from Dom385428f6.

Only default source formulas; learned torque calibration remains caller-owned.
See the repository's retained StarPilot attribution and licenses.
"""
from openpilot.common.constants import CV
from openpilot.starpilot.lateral.torque_shaping import sigmoid as _sigmoid


def get_hkg_canfd_base_friction_threshold(v_ego):
  # Dom's default GM schedule tops out at0.27, below HKG's0.39 floor.
  return 0.39

GENESIS_GV70_FRICTION_THRESHOLD_GAIN = 0.12

GENESIS_GV70_FRICTION_SPEED_ONSET = 8.0 * CV.MPH_TO_MS

GENESIS_GV70_FRICTION_SPEED_ONSET_WIDTH = 4.0 * CV.MPH_TO_MS

GENESIS_GV70_FRICTION_SPEED_CUTOFF = 60.0 * CV.MPH_TO_MS

GENESIS_GV70_FRICTION_SPEED_CUTOFF_WIDTH = 10.0 * CV.MPH_TO_MS

GENESIS_GV70_FRICTION_CENTER_LAT = 0.28

GENESIS_GV70_FRICTION_CENTER_LAT_WIDTH = 0.12

GENESIS_GV70_FRICTION_CALM_JERK = 0.35

GENESIS_GV70_FRICTION_CALM_JERK_WIDTH = 0.10

GENESIS_GV70_FRICTION_JERK_DEADZONE_MAX = 0.55

GENESIS_GV70_FRICTION_JERK_DEADZONE_LAT = 0.30

GENESIS_GV70_FRICTION_JERK_DEADZONE_LAT_WIDTH = 0.08

GENESIS_GV70_FRICTION_JERK_DEADZONE_SPEED = 12.0 * CV.MPH_TO_MS

GENESIS_GV70_FRICTION_JERK_DEADZONE_SPEED_WIDTH = 3.5 * CV.MPH_TO_MS

GENESIS_GV70_CENTER_OUTPUT_TAPER_MAX = 0.20

GENESIS_GV70_CENTER_OUTPUT_TAPER_LAT = 0.30

GENESIS_GV70_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.10

GENESIS_GV70_CENTER_OUTPUT_TAPER_SPEED = 22.0 * CV.MPH_TO_MS

GENESIS_GV70_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 3.0 * CV.MPH_TO_MS

GENESIS_GV70_UNWIND_FF_REDUCTION_MAX = 0.35

GENESIS_GV70_UNWIND_FF_OVERSHOOT = 0.15

GENESIS_GV70_UNWIND_FF_OVERSHOOT_WIDTH = 0.18

GENESIS_GV70_UNWIND_FF_JERK = 0.10

GENESIS_GV70_UNWIND_FF_JERK_WIDTH = 0.10

GENESIS_GV70_UNWIND_FF_SPEED = 10.0 * CV.MPH_TO_MS

GENESIS_GV70_UNWIND_FF_SPEED_WIDTH = 4.0 * CV.MPH_TO_MS

GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_MAX = 0.20

GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_SPEED = 50.0 * CV.MPH_TO_MS

GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_SPEED_WIDTH = 8.0 * CV.MPH_TO_MS

GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_ERROR = 0.18

GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_ERROR_WIDTH = 0.15

GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_JERK = 0.15

GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_JERK_WIDTH = 0.10

GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_MAX = 0.28

GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_SPEED = 25.0 * CV.MPH_TO_MS

GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_SPEED_WIDTH = 5.0 * CV.MPH_TO_MS

GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_ERROR = 0.30

GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_ERROR_WIDTH = 0.16

GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_JERK = 0.20

GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_JERK_WIDTH = 0.10

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_MAX = 0.28

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED = 18.0 * CV.MPH_TO_MS

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_WIDTH = 3.5 * CV.MPH_TO_MS

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_CUTOFF = 34.0 * CV.MPH_TO_MS

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_CUTOFF_WIDTH = 4.5 * CV.MPH_TO_MS

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_CENTER_LAT = 0.22

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_CENTER_LAT_WIDTH = 0.08

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_MIN = 0.06

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_LAT = 0.12

GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_LAT_WIDTH = 0.10

GENESIS_GV70_OUTPUT_SMOOTHING_SPEED = 38.0 * CV.MPH_TO_MS

GENESIS_GV70_OUTPUT_SMOOTHING_SPEED_WIDTH = 6.0 * CV.MPH_TO_MS

GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_LAT = 0.60

GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_LAT_WIDTH = 0.16

GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_RC = 0.42

GENESIS_GV70_OUTPUT_SMOOTHING_CURVE_RC = 0.14

GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_RC = 0.12

GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_PHASE = 0.04

GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_PHASE_WIDTH = 0.08

GENESIS_GV70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_LAT = 0.55

GENESIS_GV70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_RC = 0.065

GENESIS_GV70_MEASUREMENT_DAMPING_SPEED_BP = [10.0 * CV.MPH_TO_MS, 35.0 * CV.MPH_TO_MS, 60.0 * CV.MPH_TO_MS]

GENESIS_GV70_MEASUREMENT_DAMPING_V = [0.0, 0.08, 0.12]

def get_genesis_gv70_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0,
                                        desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_hkg_canfd_base_friction_threshold(v_ego)
  speed_onset = _sigmoid((v_ego - GENESIS_GV70_FRICTION_SPEED_ONSET) / GENESIS_GV70_FRICTION_SPEED_ONSET_WIDTH)
  speed_cutoff = _sigmoid((GENESIS_GV70_FRICTION_SPEED_CUTOFF - v_ego) / GENESIS_GV70_FRICTION_SPEED_CUTOFF_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_FRICTION_CENTER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_GV70_FRICTION_CENTER_LAT_WIDTH)
  calm_jerk_weight = _sigmoid((GENESIS_GV70_FRICTION_CALM_JERK - abs(desired_lateral_jerk)) /
                              GENESIS_GV70_FRICTION_CALM_JERK_WIDTH)
  gain = (GENESIS_GV70_FRICTION_THRESHOLD_GAIN * speed_onset * speed_cutoff *
          center_weight * calm_jerk_weight)
  return base_threshold * (1.0 + gain)

def get_genesis_gv70_friction_jerk_deadzone(v_ego: float, desired_lateral_accel: float) -> float:
  """Suppress small jerk-driven friction flips around the GV70 lane center."""
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_FRICTION_JERK_DEADZONE_SPEED) /
                          GENESIS_GV70_FRICTION_JERK_DEADZONE_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_FRICTION_JERK_DEADZONE_LAT - abs(desired_lateral_accel)) /
                           GENESIS_GV70_FRICTION_JERK_DEADZONE_LAT_WIDTH)
  return GENESIS_GV70_FRICTION_JERK_DEADZONE_MAX * speed_weight * center_weight

def get_genesis_gv70_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  """Dampen high-speed center corrections without reducing turn authority."""
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_CENTER_OUTPUT_TAPER_SPEED) /
                          GENESIS_GV70_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_GV70_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  return 1.0 - (GENESIS_GV70_CENTER_OUTPUT_TAPER_MAX * speed_weight * center_weight)

def get_genesis_gv70_unwind_ff_scale(setpoint: float, measured_lateral_accel: float,
                                     desired_lateral_jerk: float, v_ego: float) -> float:
  """Remove old-turn feedforward when the GV70 has already over-rotated."""
  if setpoint * desired_lateral_jerk >= 0.0 or setpoint * measured_lateral_accel <= 0.0:
    return 1.0

  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  overshoot_weight = _sigmoid((overshoot - GENESIS_GV70_UNWIND_FF_OVERSHOOT) /
                              GENESIS_GV70_UNWIND_FF_OVERSHOOT_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_GV70_UNWIND_FF_JERK) /
                         GENESIS_GV70_UNWIND_FF_JERK_WIDTH)
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_UNWIND_FF_SPEED) /
                          GENESIS_GV70_UNWIND_FF_SPEED_WIDTH)
  return 1.0 - GENESIS_GV70_UNWIND_FF_REDUCTION_MAX * overshoot_weight * jerk_weight * speed_weight

def get_genesis_gv70_high_speed_error_scale(setpoint: float, measured_lateral_accel: float,
                                             desired_lateral_jerk: float, v_ego: float) -> float:
  tracking_error = abs(measured_lateral_accel - setpoint)
  if tracking_error <= 0.0:
    return 1.0
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_SPEED) /
                          GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_SPEED_WIDTH)
  error_weight = _sigmoid((tracking_error - GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_ERROR) /
                          GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_ERROR_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_JERK) /
                         GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_JERK_WIDTH)
  phase_weight = 1.0 if setpoint * desired_lateral_jerk < 0.0 else 0.45
  reduction = (GENESIS_GV70_HIGH_SPEED_ERROR_DAMPING_MAX * speed_weight * error_weight *
               (0.35 + (0.65 * jerk_weight)) * phase_weight)
  return 1.0 - reduction

def get_genesis_gv70_reversal_output_scale(setpoint: float, measured_lateral_accel: float,
                                           desired_lateral_jerk: float, v_ego: float) -> float:
  commanded_unwind = setpoint * desired_lateral_jerk < 0.0
  measured_reversal = setpoint * measured_lateral_accel < 0.0
  if not commanded_unwind and not measured_reversal:
    return 1.0

  tracking_error = abs(measured_lateral_accel - setpoint)
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_SPEED) /
                          GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_SPEED_WIDTH)
  error_weight = _sigmoid((tracking_error - GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_ERROR) /
                          GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_ERROR_WIDTH)
  jerk_weight = _sigmoid((abs(desired_lateral_jerk) - GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_JERK) /
                         GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_JERK_WIDTH)
  reduction = (GENESIS_GV70_REVERSAL_OUTPUT_DAMPING_MAX * speed_weight * error_weight * jerk_weight)
  return 1.0 - reduction

def get_genesis_gv70_low_speed_center_overshoot_scale(setpoint: float, measured_lateral_accel: float,
                                                      v_ego: float) -> float:
  if abs(setpoint) > 0.08 and setpoint * measured_lateral_accel < 0.0:
    return 1.0
  overshoot = max(abs(measured_lateral_accel) - abs(setpoint), 0.0)
  if overshoot < GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_MIN:
    return 1.0
  overshoot_weight = _sigmoid((overshoot - GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_LAT) /
                              GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_LAT_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_CENTER_LAT - abs(setpoint)) /
                           GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_CENTER_LAT_WIDTH)
  speed_weight = _sigmoid((v_ego - GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED) /
                          GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_WIDTH)
  speed_cutoff = _sigmoid((GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_CUTOFF - v_ego) /
                          GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_SPEED_CUTOFF_WIDTH)
  return 1.0 - (GENESIS_GV70_LOW_SPEED_CENTER_OVERSHOOT_MAX * overshoot_weight * center_weight *
                speed_weight * speed_cutoff)

def get_genesis_gv70_stabilized_output(output_torque: float, prev_output_torque: float,
                                        desired_lateral_accel: float, desired_lateral_jerk: float,
                                        v_ego: float, dt: float) -> float:
  speed_weight = _sigmoid((max(v_ego, 0.0) - GENESIS_GV70_OUTPUT_SMOOTHING_SPEED) /
                          GENESIS_GV70_OUTPUT_SMOOTHING_SPEED_WIDTH)
  center_weight = _sigmoid((GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_LAT - abs(desired_lateral_accel)) /
                           GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_LAT_WIDTH)
  curve_weight = 1.0 - center_weight
  response_time = (GENESIS_GV70_OUTPUT_SMOOTHING_CURVE_RC * curve_weight +
                   GENESIS_GV70_OUTPUT_SMOOTHING_CENTER_RC * center_weight)

  unwind_phase = -desired_lateral_accel * desired_lateral_jerk
  unwind_weight = _sigmoid((unwind_phase - GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_PHASE) /
                           GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_PHASE_WIDTH)
  response_time += GENESIS_GV70_OUTPUT_SMOOTHING_UNWIND_RC * curve_weight * unwind_weight

  changing_direction = (abs(desired_lateral_accel) >= GENESIS_GV70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_LAT and
                        prev_output_torque * desired_lateral_accel <= 0.0)
  if changing_direction:
    response_time = min(response_time, GENESIS_GV70_OUTPUT_SMOOTHING_DIRECTION_CHANGE_RC)

  output_alpha = dt / (max(response_time, 0.0) + dt)
  smoothed_output = prev_output_torque + output_alpha * (output_torque - prev_output_torque)
  return float(output_torque + speed_weight * (smoothed_output - output_torque))
