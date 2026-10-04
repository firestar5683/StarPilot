import math

import numpy as np

from openpilot.starpilot.lateral.torque_shaping import get_standard_friction_threshold


SONATA_HYBRID_BASE_LAT_ACCEL_FACTOR_MULT = 1.05

SONATA_HYBRID_FF_REDUCTION_LEFT = 0.09

SONATA_HYBRID_FF_REDUCTION_RIGHT = 0.26

SONATA_HYBRID_FF_ONSET = 0.18

SONATA_HYBRID_FF_ONSET_WIDTH = 0.08

SONATA_HYBRID_FF_CUTOFF = 1.35

SONATA_HYBRID_FF_CUTOFF_WIDTH = 0.40

SONATA_HYBRID_TRANSITION_SPEED = 8.0

SONATA_HYBRID_PHASE_SCALE = 0.12

SONATA_HYBRID_TURN_IN_BOOST_LEFT = 0.12

SONATA_HYBRID_TURN_IN_BOOST_RIGHT = 0.02

SONATA_HYBRID_UNWIND_TAPER_LEFT = 0.18

SONATA_HYBRID_UNWIND_TAPER_RIGHT = 0.10

SONATA_HYBRID_CENTER_TAPER_MAX = 0.10

SONATA_HYBRID_CENTER_TAPER_LAT = 0.16

SONATA_HYBRID_CENTER_TAPER_LAT_WIDTH = 0.025

SONATA_HYBRID_CENTER_TAPER_SPEED = 22.0

SONATA_HYBRID_CENTER_TAPER_SPEED_WIDTH = 2.5

SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_MAX = 0.14

SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_LAT = 0.10

SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_LAT_WIDTH = 0.02

SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_SPEED_MAX = 7.5

SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH = 1.0

SONATA_HYBRID_CENTER_OUTPUT_TAPER_MAX = 0.14

SONATA_HYBRID_CENTER_OUTPUT_TAPER_LAT = 0.18

SONATA_HYBRID_CENTER_OUTPUT_TAPER_LAT_WIDTH = 0.05

SONATA_HYBRID_CENTER_OUTPUT_TAPER_SPEED = 12.5

SONATA_HYBRID_CENTER_OUTPUT_TAPER_SPEED_WIDTH = 2.5

SONATA_HYBRID_CHATTER_THRESHOLD_SPEED_BP = [0.0, 4.5, 7.5, 11.0, 20.0]

SONATA_HYBRID_CHATTER_THRESHOLD_BUMP = [0.02, 0.04, 0.04, 0.02, 0.0]

SONATA_HYBRID_CHATTER_THRESHOLD_CENTER = 0.20

SONATA_HYBRID_CHATTER_THRESHOLD_CENTER_WIDTH = 0.05

def _sigmoid(x: float) -> float:
  if x >= 0.0:
    z = math.exp(-x)
    return 1.0 / (1.0 + z)

  z = math.exp(x)
  return z / (1.0 + z)

def _sonata_hybrid_sigmoid(x: float) -> float:
  return _sigmoid(x)

def _sonata_hybrid_low_speed_factor(v_ego: float) -> float:
  return 1.0 / (1.0 + (max(v_ego, 0.0) / SONATA_HYBRID_TRANSITION_SPEED) ** 2)

def _sonata_hybrid_transition_phase(desired_lateral_accel: float, desired_lateral_jerk: float) -> float:
  return math.tanh((desired_lateral_accel * desired_lateral_jerk) / SONATA_HYBRID_PHASE_SCALE)

def _sonata_hybrid_side_value(desired_lateral_accel: float, left_value: float, right_value: float) -> float:
  return left_value if desired_lateral_accel >= 0.0 else right_value

def get_sonata_hybrid_ff_scale(desired_lateral_accel: float, desired_lateral_jerk: float, v_ego: float) -> float:
  if desired_lateral_accel == 0.0:
    return 1.0

  abs_lateral_accel = abs(desired_lateral_accel)
  onset = _sonata_hybrid_sigmoid((abs_lateral_accel - SONATA_HYBRID_FF_ONSET) / SONATA_HYBRID_FF_ONSET_WIDTH)
  cutoff = _sonata_hybrid_sigmoid((SONATA_HYBRID_FF_CUTOFF - abs_lateral_accel) / SONATA_HYBRID_FF_CUTOFF_WIDTH)
  base_reduction = _sonata_hybrid_side_value(desired_lateral_accel,
                                             SONATA_HYBRID_FF_REDUCTION_LEFT,
                                             SONATA_HYBRID_FF_REDUCTION_RIGHT) * onset * cutoff
  phase = _sonata_hybrid_transition_phase(desired_lateral_accel, desired_lateral_jerk)
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  low_speed_factor = _sonata_hybrid_low_speed_factor(v_ego)
  turn_in_boost = 1.0 + (_sonata_hybrid_side_value(desired_lateral_accel,
                                                    SONATA_HYBRID_TURN_IN_BOOST_LEFT,
                                                    SONATA_HYBRID_TURN_IN_BOOST_RIGHT) *
                         turn_in_weight * low_speed_factor)
  unwind_taper = 1.0 - (_sonata_hybrid_side_value(desired_lateral_accel,
                                                   SONATA_HYBRID_UNWIND_TAPER_LEFT,
                                                   SONATA_HYBRID_UNWIND_TAPER_RIGHT) *
                        unwind_weight * (0.35 + 0.65 * low_speed_factor))
  return (1.0 - base_reduction) * turn_in_boost * max(unwind_taper, 0.0)

def get_sonata_hybrid_center_taper_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sonata_hybrid_sigmoid((v_ego - SONATA_HYBRID_CENTER_TAPER_SPEED) / SONATA_HYBRID_CENTER_TAPER_SPEED_WIDTH)
  center_weight = _sonata_hybrid_sigmoid((SONATA_HYBRID_CENTER_TAPER_LAT - abs(desired_lateral_accel)) / SONATA_HYBRID_CENTER_TAPER_LAT_WIDTH)
  reduction = SONATA_HYBRID_CENTER_TAPER_MAX * speed_weight * center_weight
  low_speed_weight = _sonata_hybrid_sigmoid((SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_SPEED_MAX - v_ego) /
                                            SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_SPEED_WIDTH)
  low_speed_center_weight = _sonata_hybrid_sigmoid((SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_LAT - abs(desired_lateral_accel)) /
                                                   SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_LAT_WIDTH)
  reduction += SONATA_HYBRID_LOW_SPEED_CENTER_TAPER_MAX * low_speed_weight * low_speed_center_weight
  return 1.0 - reduction

def get_sonata_hybrid_center_output_scale(desired_lateral_accel: float, v_ego: float) -> float:
  speed_weight = _sonata_hybrid_sigmoid((v_ego - SONATA_HYBRID_CENTER_OUTPUT_TAPER_SPEED) /
                                        SONATA_HYBRID_CENTER_OUTPUT_TAPER_SPEED_WIDTH)
  center_weight = _sonata_hybrid_sigmoid((SONATA_HYBRID_CENTER_OUTPUT_TAPER_LAT - abs(desired_lateral_accel)) /
                                         SONATA_HYBRID_CENTER_OUTPUT_TAPER_LAT_WIDTH)
  return 1.0 - SONATA_HYBRID_CENTER_OUTPUT_TAPER_MAX * speed_weight * center_weight

def get_sonata_hybrid_friction_threshold(v_ego: float, desired_lateral_accel: float) -> float:
  base_threshold = get_standard_friction_threshold(v_ego)
  speed_bump = np.interp(max(v_ego, 0.0), SONATA_HYBRID_CHATTER_THRESHOLD_SPEED_BP,
                         SONATA_HYBRID_CHATTER_THRESHOLD_BUMP)
  center_weight = _sonata_hybrid_sigmoid(
    (SONATA_HYBRID_CHATTER_THRESHOLD_CENTER - abs(desired_lateral_accel)) /
    SONATA_HYBRID_CHATTER_THRESHOLD_CENTER_WIDTH
  )
  return float(base_threshold + speed_bump * center_weight)
