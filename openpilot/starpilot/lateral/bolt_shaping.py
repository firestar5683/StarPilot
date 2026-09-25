'Default generation-specific Bolt torque shaping.'

import math

import numpy as np


from opendbc.car.common.conversions import Conversions as CV
from openpilot.starpilot.lateral.torque_shaping import sigmoid

BOLT_2017_STEER_RATIO_ONSET_SPEED = 20.0 * CV.MPH_TO_MS
BOLT_2017_STEER_RATIO_ONSET_WIDTH = 4.0 * CV.MPH_TO_MS
BOLT_2017_CENTER_TAPER_LAT = 0.1
BOLT_2017_CENTER_TAPER_WIDTH = 0.03
BOLT_2017_CENTER_TAPER_GAIN = 0.055
BOLT_2017_TORQUE_SCALE_BP = [0.0, 0.2, 0.5, 1.0, 1.5, 2.5]
BOLT_2017_TORQUE_SCALE_LEFT = [1.0, 1.0, 1.065, 1.06, 1.055, 1.045]
BOLT_2017_TORQUE_SCALE_RIGHT = [1.0, 1.0, 1.035, 1.02, 0.995, 0.985]
BOLT_2017_TRANSITION_SPEED = 10.0
BOLT_2017_PHASE_SCALE = 0.12
BOLT_2017_TURN_IN_BOOST_LEFT = 0.28
BOLT_2017_TURN_IN_BOOST_RIGHT = 0.18
BOLT_2017_UNWIND_TAPER_LEFT = 0.08
BOLT_2017_UNWIND_TAPER_RIGHT = 0.28
BOLT_2018_2021_TORQUE_GAIN_LEFT = 0.09
BOLT_2018_2021_TORQUE_GAIN_RIGHT = 0.05
BOLT_2018_2021_TORQUE_ONSET = 0.18
BOLT_2018_2021_TORQUE_ONSET_WIDTH = 0.08
BOLT_2018_2021_TORQUE_CUTOFF = 1.05
BOLT_2018_2021_TORQUE_CUTOFF_WIDTH = 0.24
BOLT_2018_2021_JERK_TAPER_CUTOFF = 0.42
BOLT_2018_2021_CENTER_TAPER_LAT = 0.12
BOLT_2018_2021_CENTER_TAPER_WIDTH = 0.04
BOLT_2018_2021_CENTER_TAPER_GAIN = 0.35
BOLT_2018_2021_TRANSITION_SPEED = 8.5
BOLT_2018_2021_PHASE_SCALE = 0.1
BOLT_2018_2021_TURN_IN_BOOST_LEFT = 0.22
BOLT_2018_2021_TURN_IN_BOOST_RIGHT = 0.12
BOLT_2018_2021_UNWIND_TAPER_GAIN_LEFT = 0.8
BOLT_2018_2021_UNWIND_TAPER_GAIN_RIGHT = 1.04
BOLT_2018_2021_FRICTION_MULT = 1.01
BOLT_2018_2021_FRICTION_LAT_RISE = 0.24
BOLT_2018_2021_FRICTION_JERK_RISE = 0.28
BOLT_2018_2021_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.16
BOLT_2018_2021_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.16
BOLT_2018_2021_UNWIND_THRESHOLD_INCREASE_LEFT = 0.15
BOLT_2018_2021_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.25
BOLT_2018_2021_TURN_IN_FRICTION_BOOST_LEFT = 0.08
BOLT_2018_2021_TURN_IN_FRICTION_BOOST_RIGHT = 0.08
BOLT_2018_2021_UNWIND_FRICTION_REDUCTION_LEFT = 0.17
BOLT_2018_2021_UNWIND_FRICTION_REDUCTION_RIGHT = 0.27
BOLT_2022_2023_FF_GAIN_LEFT = 0.11
BOLT_2022_2023_FF_GAIN_RIGHT = 0.06
BOLT_2022_2023_FF_ONSET = 0.12
BOLT_2022_2023_FF_ONSET_WIDTH = 0.07
BOLT_2022_2023_FF_CUTOFF = 1.35
BOLT_2022_2023_FF_CUTOFF_WIDTH = 0.28
BOLT_2022_2023_TRANSITION_SPEED = 9.0
BOLT_2022_2023_PHASE_SCALE = 0.12
BOLT_2022_2023_TURN_IN_BOOST_LEFT = 0.18
BOLT_2022_2023_TURN_IN_BOOST_RIGHT = 0.13
BOLT_2022_2023_UNWIND_TAPER_LEFT = 0.38
BOLT_2022_2023_UNWIND_TAPER_RIGHT = 0.4
BOLT_2022_2023_FRICTION_MULT = 1.09
BOLT_2022_2023_FRICTION_LAT_RISE = 0.22
BOLT_2022_2023_FRICTION_JERK_RISE = 0.26
BOLT_2022_2023_CENTER_TAPER_MAX = 0.11
BOLT_2022_2023_CENTER_TAPER_LAT = 0.18
BOLT_2022_2023_CENTER_TAPER_LAT_WIDTH = 0.03
BOLT_2022_2023_CENTER_TAPER_SPEED = 25.0
BOLT_2022_2023_CENTER_TAPER_SPEED_WIDTH = 2.5
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_MAX = 0.12
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_LAT = 0.14
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_LAT_WIDTH = 0.04
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED = 4.0
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH = 1.5
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_FLOOR = 2.0
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_FLOOR_WIDTH = 0.7
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_MAX = 16.5
BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_MAX_WIDTH = 2.0
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LIMIT = 0.38
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT = 0.17
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT_WIDTH = 0.04
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED = 2.5
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_WIDTH = 0.7
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX = 8.2
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX_WIDTH = 0.6
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SCALE_MIN = 0.62
BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_ALPHA_MIN = 0.28
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_BUMP = 0.08
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_LAT = 0.18
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_LAT_WIDTH = 0.06
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_SPEED = 6.7
BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH = 1.5
BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_LEFT = 0.16
BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_RIGHT = 0.12
BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_LEFT = 0.26
BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_RIGHT = 0.28
BOLT_2022_2023_TURN_IN_FRICTION_BOOST_LEFT = 0.1
BOLT_2022_2023_TURN_IN_FRICTION_BOOST_RIGHT = 0.07
BOLT_2022_2023_UNWIND_FRICTION_REDUCTION_LEFT = 0.27
BOLT_2022_2023_UNWIND_FRICTION_REDUCTION_RIGHT = 0.28


def get_gm_base_friction_threshold(v_ego: float) -> float:
  return float(np.interp(v_ego, [1 * CV.MPH_TO_MS, 20 * CV.MPH_TO_MS, 75 * CV.MPH_TO_MS], [0.16, 0.19, 0.27]))


def _bolt_2017_high_speed_factor(v_ego: float) -> float:
  return sigmoid((max(v_ego, 0.0) - BOLT_2017_STEER_RATIO_ONSET_SPEED) / BOLT_2017_STEER_RATIO_ONSET_WIDTH)


def get_bolt_2017_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  center_window = sigmoid((BOLT_2017_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / BOLT_2017_CENTER_TAPER_WIDTH)
  return 1.0 - BOLT_2017_CENTER_TAPER_GAIN * _bolt_2017_high_speed_factor(v_ego) * center_window


def _bolt_2017_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / BOLT_2017_TRANSITION_SPEED) ** 2)


def _bolt_2017_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh(desired_lateral_accel * desired_lateral_jerk / BOLT_2017_PHASE_SCALE)


def _bolt_2017_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def get_bolt_2017_base_torque_scale(desired_lateral_accel: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0
  scale_values = BOLT_2017_TORQUE_SCALE_LEFT if desired_lateral_accel > 0.0 else BOLT_2017_TORQUE_SCALE_RIGHT
  return float(np.interp(abs(desired_lateral_accel), BOLT_2017_TORQUE_SCALE_BP, scale_values))


def get_bolt_2017_torque_scale(desired_lateral_accel: float, desired_lateral_jerk: float = 0.0, v_ego: float = 30.0) -> float:
  base_scale = get_bolt_2017_base_torque_scale(desired_lateral_accel)
  scale = base_scale
  if base_scale > 1.0 and desired_lateral_jerk != 0.0:
    low_speed_factor = _bolt_2017_low_speed_factor(v_ego)
    phase = _bolt_2017_transition_phase(desired_lateral_accel, desired_lateral_jerk)
    turn_in_weight = max(phase, 0.0)
    unwind_weight = max(-phase, 0.0)
    turn_in_boost = 1.0 + _bolt_2017_side_value(desired_lateral_accel, BOLT_2017_TURN_IN_BOOST_LEFT, BOLT_2017_TURN_IN_BOOST_RIGHT) * turn_in_weight * (
      0.35 + 0.65 * low_speed_factor
    )
    unwind_taper = 1.0 - _bolt_2017_side_value(desired_lateral_accel, BOLT_2017_UNWIND_TAPER_LEFT, BOLT_2017_UNWIND_TAPER_RIGHT) * unwind_weight * (
      0.45 + 0.55 * low_speed_factor
    )
    scale = 1.0 + (base_scale - 1.0) * turn_in_boost * max(unwind_taper, 0.0)
  return scale * get_bolt_2017_center_taper_scale(desired_lateral_accel, v_ego)


def _bolt_2018_2021_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / BOLT_2018_2021_TRANSITION_SPEED) ** 2)


def _bolt_2018_2021_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh(desired_lateral_accel * desired_lateral_jerk / BOLT_2018_2021_PHASE_SCALE)


def _bolt_2018_2021_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _bolt_2018_2021_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / BOLT_2018_2021_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / BOLT_2018_2021_FRICTION_JERK_RISE)
  return _bolt_2018_2021_low_speed_factor(v_ego) * lat_factor * jerk_factor


def get_bolt_2018_2021_torque_scale(desired_lateral_accel: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0
  gain = BOLT_2018_2021_TORQUE_GAIN_LEFT if desired_lateral_accel > 0.0 else BOLT_2018_2021_TORQUE_GAIN_RIGHT
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = sigmoid((abs_lateral_accel - BOLT_2018_2021_TORQUE_ONSET) / BOLT_2018_2021_TORQUE_ONSET_WIDTH)
  cutoff = sigmoid((BOLT_2018_2021_TORQUE_CUTOFF - abs_lateral_accel) / BOLT_2018_2021_TORQUE_CUTOFF_WIDTH)
  return 1.0 + gain * onset * cutoff


def get_bolt_2018_2021_dynamic_torque_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  base_scale = get_bolt_2018_2021_torque_scale(desired_lateral_accel)
  extra_scale = max(base_scale - 1.0, 0.0)
  abs_lateral_accel = abs(desired_lateral_accel)
  low_speed_factor = _bolt_2018_2021_low_speed_factor(v_ego)
  high_speed_factor = 1.0 - low_speed_factor
  center_window = sigmoid((BOLT_2018_2021_CENTER_TAPER_LAT - abs_lateral_accel) / BOLT_2018_2021_CENTER_TAPER_WIDTH)
  center_taper = 1.0 - BOLT_2018_2021_CENTER_TAPER_GAIN * high_speed_factor * center_window
  phase = _bolt_2018_2021_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  jerk_taper = 1.0 / (1.0 + (abs(desired_lateral_jerk) / BOLT_2018_2021_JERK_TAPER_CUTOFF) ** 2)
  turn_in_boost = (
    1.0
    + _bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_TURN_IN_BOOST_LEFT, BOLT_2018_2021_TURN_IN_BOOST_RIGHT)
    * turn_in_weight
    * low_speed_factor
  )
  unwind_weight = max(-phase, 0.0)
  unwind_taper = 1.0 - _bolt_2018_2021_side_value(
    desired_lateral_accel, BOLT_2018_2021_UNWIND_TAPER_GAIN_LEFT, BOLT_2018_2021_UNWIND_TAPER_GAIN_RIGHT
  ) * unwind_weight * (0.55 + 0.45 * low_speed_factor)
  return 1.0 + extra_scale * center_taper * jerk_taper * turn_in_boost * max(unwind_taper, 0.0)


def get_bolt_2018_2021_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  transition_envelope = _bolt_2018_2021_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2018_2021_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  threshold_scale = (
    1.0
    - _bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_TURN_IN_THRESHOLD_REDUCTION_LEFT, BOLT_2018_2021_TURN_IN_THRESHOLD_REDUCTION_RIGHT)
    * transition_envelope
    * turn_in_weight
  )
  threshold_scale += (
    _bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_UNWIND_THRESHOLD_INCREASE_LEFT, BOLT_2018_2021_UNWIND_THRESHOLD_INCREASE_RIGHT)
    * transition_envelope
    * unwind_weight
  )
  return base_threshold * min(max(threshold_scale, 0.82), 1.12)


def get_bolt_2018_2021_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _bolt_2018_2021_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2018_2021_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  friction_scale = BOLT_2018_2021_FRICTION_MULT
  friction_scale += (
    _bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_TURN_IN_FRICTION_BOOST_LEFT, BOLT_2018_2021_TURN_IN_FRICTION_BOOST_RIGHT)
    * transition_envelope
    * turn_in_weight
  )
  friction_scale -= (
    _bolt_2018_2021_side_value(desired_lateral_accel, BOLT_2018_2021_UNWIND_FRICTION_REDUCTION_LEFT, BOLT_2018_2021_UNWIND_FRICTION_REDUCTION_RIGHT)
    * transition_envelope
    * unwind_weight
  )
  return min(max(friction_scale, 0.88), 1.1)


def _bolt_2022_2023_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / BOLT_2022_2023_TRANSITION_SPEED) ** 2)


def _bolt_2022_2023_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh(desired_lateral_accel * desired_lateral_jerk / BOLT_2022_2023_PHASE_SCALE)


def _bolt_2022_2023_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value


def _bolt_2022_2023_transition_envelope(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  lat_factor = 1.0 - math.exp(-abs(desired_lateral_accel) / BOLT_2022_2023_FRICTION_LAT_RISE)
  jerk_factor = 1.0 - math.exp(-abs(desired_lateral_jerk) / BOLT_2022_2023_FRICTION_JERK_RISE)
  return _bolt_2022_2023_low_speed_factor(v_ego) * lat_factor * jerk_factor


def get_bolt_2022_2023_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0
  gain = _bolt_2022_2023_side_value(desired_lateral_accel, BOLT_2022_2023_FF_GAIN_LEFT, BOLT_2022_2023_FF_GAIN_RIGHT)
  abs_lateral_accel = abs(desired_lateral_accel)
  onset = sigmoid((abs_lateral_accel - BOLT_2022_2023_FF_ONSET) / BOLT_2022_2023_FF_ONSET_WIDTH)
  cutoff = sigmoid((BOLT_2022_2023_FF_CUTOFF - abs_lateral_accel) / BOLT_2022_2023_FF_CUTOFF_WIDTH)
  extra_scale = gain * onset * cutoff
  speed_weight = sigmoid((v_ego - BOLT_2022_2023_CENTER_TAPER_SPEED) / BOLT_2022_2023_CENTER_TAPER_SPEED_WIDTH)
  center_weight = sigmoid((BOLT_2022_2023_CENTER_TAPER_LAT - abs_lateral_accel) / BOLT_2022_2023_CENTER_TAPER_LAT_WIDTH)
  center_taper = 1.0 - BOLT_2022_2023_CENTER_TAPER_MAX * speed_weight * center_weight
  low_speed_factor = _bolt_2022_2023_low_speed_factor(v_ego)
  transition_envelope = _bolt_2022_2023_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2022_2023_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  turn_in_boost = (
    1.0
    + _bolt_2022_2023_side_value(desired_lateral_accel, BOLT_2022_2023_TURN_IN_BOOST_LEFT, BOLT_2022_2023_TURN_IN_BOOST_RIGHT)
    * turn_in_weight
    * low_speed_factor
  )
  unwind_envelope = (0.25 + 0.75 * low_speed_factor) * (1.0 + 0.45 * transition_envelope)
  unwind_taper = (
    1.0
    - _bolt_2022_2023_side_value(desired_lateral_accel, BOLT_2022_2023_UNWIND_TAPER_LEFT, BOLT_2022_2023_UNWIND_TAPER_RIGHT) * unwind_weight * unwind_envelope
  )
  return 1.0 + extra_scale * center_taper * turn_in_boost * max(unwind_taper, 0.0)


def get_bolt_2022_2023_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  highway_speed_weight = sigmoid((v_ego - BOLT_2022_2023_CENTER_TAPER_SPEED) / BOLT_2022_2023_CENTER_TAPER_SPEED_WIDTH)
  highway_center_weight = sigmoid((BOLT_2022_2023_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / BOLT_2022_2023_CENTER_TAPER_LAT_WIDTH)
  low_speed_onset = sigmoid((v_ego - BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED) / BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH)
  low_speed_cutoff = sigmoid((BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_MAX - v_ego) / BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_SPEED_MAX_WIDTH)
  low_speed_center_weight = sigmoid((BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_LAT_WIDTH)
  low_speed_floor = sigmoid((v_ego - BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_FLOOR) / BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_FLOOR_WIDTH)
  highway_reduction = BOLT_2022_2023_CENTER_TAPER_MAX * highway_speed_weight * highway_center_weight
  low_speed_reduction = BOLT_2022_2023_LOW_SPEED_CENTER_TAPER_MAX * low_speed_onset * low_speed_cutoff * low_speed_center_weight * low_speed_floor
  return 1.0 - min(highway_reduction + low_speed_reduction, 0.95)


def get_bolt_2022_2023_low_speed_center_output_limit(desired_lateral_accel: float, v_ego: float) -> float:
  """Limit small-signal output while the Bolt is in its low-speed chatter band."""
  speed_onset = sigmoid((v_ego - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED) / BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_WIDTH)
  speed_cutoff = sigmoid((BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX - v_ego) / BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX_WIDTH)
  center_weight = sigmoid((BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT - abs(desired_lateral_accel)) / BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT_WIDTH)
  speed_weight = speed_onset * speed_cutoff
  reduction = (1.0 - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LIMIT) * speed_weight * center_weight
  return 1.0 - reduction


def get_bolt_2022_2023_low_speed_center_output(output_torque: float, prev_output_torque: float, desired_lateral_accel: float, v_ego: float) -> float:
  """Damp low-speed center reversals without reducing real turn authority."""
  speed_weight = sigmoid((v_ego - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED) / BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_WIDTH) * sigmoid(
    (BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX - v_ego) / BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SPEED_MAX_WIDTH
  )
  center_weight = sigmoid((BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT - abs(desired_lateral_accel)) / BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_LAT_WIDTH)
  envelope = speed_weight * center_weight
  output_scale = 1.0 - (1.0 - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_SCALE_MIN) * envelope
  output_alpha = 1.0 - (1.0 - BOLT_2022_2023_LOW_SPEED_CENTER_OUTPUT_ALPHA_MIN) * envelope
  limited_output = output_torque * output_scale
  return float(prev_output_torque + output_alpha * (limited_output - prev_output_torque))


def get_bolt_2022_2023_friction_threshold(v_ego: float, desired_lateral_accel: float = 0.0, desired_lateral_jerk: float = 0.0) -> float:
  base_threshold = get_gm_base_friction_threshold(v_ego)
  center_weight = sigmoid((BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_LAT - abs(desired_lateral_accel)) / BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_LAT_WIDTH)
  low_speed_weight = sigmoid((BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_SPEED - v_ego) / BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_SPEED_WIDTH)
  base_threshold += BOLT_2022_2023_CENTER_FRICTION_THRESHOLD_BUMP * center_weight * low_speed_weight
  transition_envelope = _bolt_2022_2023_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2022_2023_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  threshold_scale = (
    1.0
    - _bolt_2022_2023_side_value(desired_lateral_accel, BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_LEFT, BOLT_2022_2023_TURN_IN_THRESHOLD_REDUCTION_RIGHT)
    * transition_envelope
    * turn_in_weight
  )
  threshold_scale += (
    _bolt_2022_2023_side_value(desired_lateral_accel, BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_LEFT, BOLT_2022_2023_UNWIND_THRESHOLD_INCREASE_RIGHT)
    * transition_envelope
    * unwind_weight
  )
  return base_threshold * min(max(threshold_scale, 0.84), 1.14)


def get_bolt_2022_2023_friction_scale(v_ego: float, desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  transition_envelope = _bolt_2022_2023_transition_envelope(v_ego, desired_lateral_accel, desired_lateral_jerk)
  phase = _bolt_2022_2023_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  friction_scale = BOLT_2022_2023_FRICTION_MULT
  friction_scale += (
    _bolt_2022_2023_side_value(desired_lateral_accel, BOLT_2022_2023_TURN_IN_FRICTION_BOOST_LEFT, BOLT_2022_2023_TURN_IN_FRICTION_BOOST_RIGHT)
    * transition_envelope
    * turn_in_weight
  )
  friction_scale -= (
    _bolt_2022_2023_side_value(desired_lateral_accel, BOLT_2022_2023_UNWIND_FRICTION_REDUCTION_LEFT, BOLT_2022_2023_UNWIND_FRICTION_REDUCTION_RIGHT)
    * transition_envelope
    * unwind_weight
  )
  return min(max(friction_scale, 0.92), 1.22)
