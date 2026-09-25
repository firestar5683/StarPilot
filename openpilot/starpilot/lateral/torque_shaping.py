"""Shared default torque-shaping calibration and pure math.

Vehicle admission, calibration overrides, state and output remain in each policy.
Defaults derive from the frozen StarPilot torque controller tune.
"""

import math

import numpy as np


def sigmoid(x: float) -> float:
  if x >= 0.0:
    z = math.exp(-x)
    return 1.0 / (1.0 + z)
  z = math.exp(x)
  return z / (1.0 + z)


KP = 0.6
KI = 0.35
INTERP_SPEEDS = [1, 1.5, 2.0, 3.0, 5, 7.5, 10, 15, 30]
KP_INTERP = [250, 120, 65, 30, 11.5, 5.5, 3.5, 2.0, KP]
LOW_SPEED_X = [0, 10, 20, 30]
LOW_SPEED_Y = [12, 10.5, 8, 5]
MAX_LAT_JERK_UP = 2.5
LP_FILTER_CUTOFF_HZ = 1.2
JERK_GAIN = 0.22
LAT_ACCEL_REQUEST_BUFFER_SECONDS = 1.0
MIN_SPEED = 1.0
UNWIND_D_DES_THRESHOLD = -1.0
UNWIND_LAT_ACCEL_NEAR_ZERO = 0.3
FF_ROLL_OFFSET_FADE_BP = [0.5, 2.5]
FF_ROLL_OFFSET_FADE_V = [0.0, 1.0]
CENTER_CHATTER_JERK_DEADZONE_SPEED_BP = [0.0, 5.0, 12.0, 25.0]
CENTER_CHATTER_JERK_DEADZONE_SPEED_V = [0.08, 0.12, 0.18, 0.18]
CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_BP = [0.0, 0.18, 0.35]
CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_V = [1.0, 1.0, 0.0]


def center_chatter_friction_jerk_deadzone(v_ego: float, setpoint: float, vehicle_deadzone: float) -> float:
  speed_deadzone = np.interp(max(v_ego, 0.0), CENTER_CHATTER_JERK_DEADZONE_SPEED_BP,
                             CENTER_CHATTER_JERK_DEADZONE_SPEED_V)
  center_weight = np.interp(abs(setpoint), CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_BP,
                            CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_V)
  return max(vehicle_deadzone, float(speed_deadzone * center_weight))


def get_standard_friction_threshold(v_ego):
  return 0.30
