#!/usr/bin/env python3
import math
import numpy as np
import time
import cereal.messaging as messaging
from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.starpilot.common.model_versions import is_tinygrad_model_version
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import LongitudinalMpc
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import desired_follow_distance
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import should_trigger_planner_fcw
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import STOP_DISTANCE
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import T_IDXS as T_IDXS_MPC
from openpilot.selfdrive.controls.lib.lead_behavior import is_radarless_matched_follow_window
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N
from openpilot.selfdrive.car.cruise import V_CRUISE_UNSET
from openpilot.common.swaglog import cloudlog

LON_MPC_STEP = 0.2  # first step is 0.2s
A_CRUISE_MIN = -1.0
A_CRUISE_MAX_BP = [0.0, 5., 10., 15., 20., 25., 40.]
A_CRUISE_MAX_VALS = [1.125, 1.125, 1.125, 1.125, 1.25, 1.25, 1.5]
CONTROL_N_T_IDX = ModelConstants.T_IDXS[:CONTROL_N]
ALLOW_THROTTLE_THRESHOLD = 0.4
ALLOW_THROTTLE_HYSTERESIS = 0.05
ALLOW_THROTTLE_ENABLE_THRESHOLD = ALLOW_THROTTLE_THRESHOLD + ALLOW_THROTTLE_HYSTERESIS
ALLOW_THROTTLE_DISABLE_THRESHOLD = ALLOW_THROTTLE_THRESHOLD - ALLOW_THROTTLE_HYSTERESIS
MIN_ALLOW_THROTTLE_SPEED = 5.0
RAW_LEAD_SAFETY_MIN_CLOSING_SPEED = 0.5
RAW_LEAD_SAFETY_TTC = 7.0
RAW_LEAD_SAFETY_DISTANCE = 40.0
STANDSTILL_LEAD_NUDGE_ACCEL = 0.05
STANDSTILL_LEAD_NUDGE_MIN_SPEED = 0.0
STANDSTILL_LEAD_DEPART_MIN_ACCEL = 0.35
STANDSTILL_LEAD_DEPART_MAX_EGO_SPEED = 1.5
STANDSTILL_LEAD_DEPART_MIN_LEAD_SPEED = 0.6
STANDSTILL_LEAD_DEPART_MIN_GAP_MARGIN = 0.8
STANDSTILL_LEAD_DEPART_MIN_MODEL_ACCEL = 0.08
LEAD_DEPART_CONFIDENT_MIN_GAP = 3.75
LEAD_DEPART_CONFIDENT_MAX_GAP = 5.25
LEAD_DEPART_CONFIDENT_MIN_LEAD_SPEED = 0.3
LEAD_DEPART_CONFIDENT_MIN_LEAD_DELTA = 0.25
LEAD_DEPART_CONFIDENT_MIN_LEAD_ACCEL = 0.2
LEAD_DEPART_CONFIDENT_CONFIRM_TIME = 0.35
RADAR_DEPART_CONFLICT_MAX_EGO_SPEED = 1.6
RADAR_DEPART_CONFLICT_MIN_RADAR_LATERAL = 1.5
RADAR_DEPART_CONFLICT_MAX_RADAR_DISTANCE = 18.0
RADAR_DEPART_CONFLICT_MIN_MODEL_PROB = 0.95
RADAR_DEPART_CONFLICT_MAX_MODEL_DISTANCE = 18.0
RADAR_DEPART_CONFLICT_MAX_MODEL_LATERAL = 0.9
RADAR_DEPART_CONFLICT_MAX_MODEL_LEAD_SPEED = 2.0
RADAR_DEPART_CONFLICT_MAX_DISTANCE_MISMATCH = 4.0
LEAD_DEPART_ACCEL_HOLD_TIME = 1.2
LEAD_DEPART_ACCEL_HOLD_MAX_EGO_SPEED = 1.5
LEAD_DEPART_ACCEL_HOLD_MIN_LEAD_SPEED = 0.6
LEAD_DEPART_ACCEL_HOLD_MIN_LEAD_DELTA = 0.5
LEAD_DEPART_ACCEL_HOLD_MIN_GAP = 3.5
LEAD_DEPART_ACCEL_HOLD_FULL_GAP = 6.0
LEAD_DEPART_ACCEL_HOLD_FULL_LEAD_SPEED = 2.2
LEAD_DEPART_ACCEL_HOLD_MIN_MODEL_PROB = 0.85
LEAD_DEPART_ACCEL_HOLD_MIN_MODEL_ACCEL = 0.12
LEAD_DEPART_ACCEL_HOLD_MAX_LEAD_BRAKE = 0.2
LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL = 0.25
LEAD_DEPART_ACCEL_HOLD_MAX_ACCEL = 0.45
CLOSE_LEAD_BRAKE_CAP_MAX_TTC = 25.0
VISION_LEAD_APPROACH_MIN_CLOSING_SPEED = 2.0
VISION_LEAD_APPROACH_TRIGGER_TIME = 4.5
VISION_LEAD_APPROACH_FULL_TIME = 1.0
VISION_LEAD_APPROACH_TIGHT_BUFFER = 2.0
VISION_LEAD_APPROACH_MAX_DECEL = 0.80
VISION_LEAD_APPROACH_MIN_DECEL = 0.15
VISION_LEAD_APPROACH_MIN_MODEL_PROB = 0.85
VISION_LEAD_APPROACH_FULL_MODEL_PROB = 0.98
VISION_LEAD_APPROACH_DEFICIT_MAX_DECEL = 1.30
VISION_LEAD_APPROACH_DEFICIT_BUFFER_MIN = 3.0
VISION_LEAD_APPROACH_DEFICIT_BUFFER_GAIN = 0.20
VISION_LEAD_APPROACH_BRAKING_DEFICIT_MIN = 0.75
VISION_LEAD_APPROACH_BRAKING_MIN_LEAD_BRAKE = 0.45
VISION_LEAD_APPROACH_BRAKING_FULL_LEAD_BRAKE = 1.20
VISION_LEAD_APPROACH_BRAKING_FLOOR_MIN_DECEL = 1.30
VISION_LEAD_APPROACH_BRAKING_FLOOR_MAX_DECEL = 1.75
VISION_LEAD_APPROACH_CONFIRM_TIME = 0.25
VISION_LEAD_APPROACH_CONFIRM_BYPASS_DECEL = 1.0
VISION_LEAD_APPROACH_CONFIRM_BYPASS_CLOSING_SPEED = 4.0
VISION_LEAD_APPROACH_CONFIRM_BYPASS_LEAD_BRAKE = 0.20
VISION_LEAD_APPROACH_CONFIRM_BYPASS_DISTANCE_MIN = 28.0
VISION_LEAD_APPROACH_CONFIRM_BYPASS_DISTANCE_TIME = 0.85
VISION_UNTRACKED_SLOW_LEAD_MIN_MODEL_PROB = 0.9
VISION_UNTRACKED_SLOW_LEAD_FULL_MODEL_PROB = 0.97
VISION_UNTRACKED_SLOW_LEAD_MIN_CLOSING_SPEED = 3.0
VISION_UNTRACKED_SLOW_LEAD_MIN_CLOSING_RATIO = 0.16
VISION_UNTRACKED_SLOW_LEAD_FULL_CLOSING_RATIO = 0.24
VISION_UNTRACKED_SLOW_LEAD_TRIGGER_TTC = 16.0
VISION_UNTRACKED_SLOW_LEAD_FULL_TTC = 8.0
VISION_UNTRACKED_SLOW_LEAD_MAX_DISTANCE_TIME = 4.4
VISION_UNTRACKED_SLOW_LEAD_MIN_DISTANCE = 80.0
VISION_UNTRACKED_SLOW_LEAD_MAX_DISTANCE = 120.0
VISION_UNTRACKED_SLOW_LEAD_RELAXED_MAX_DISTANCE_TIME = 5.7
VISION_UNTRACKED_SLOW_LEAD_MAX_DECEL = 0.85
VISION_UNTRACKED_SLOW_LEAD_MIN_DECEL = 0.1
VISION_UNTRACKED_SLOW_LEAD_RELAXED_MODEL_PROB = 0.68
VISION_UNTRACKED_SLOW_LEAD_RELAXED_MAX_LEAD_SPEED = 8.0
VISION_UNTRACKED_SLOW_LEAD_RELAXED_MAX_TTC = 10.0
VISION_UNTRACKED_SLOW_LEAD_RELAXED_MIN_CLOSING_SPEED = 10.0
VISION_UNTRACKED_SLOW_LEAD_RELAXED_FULL_CLOSING_SPEED = 16.0
VISION_UNTRACKED_SLOW_LEAD_CONFIRM_TIME = 0.30
VISION_UNTRACKED_SLOW_LEAD_IMMEDIATE_DECEL = 0.55
VISION_UNTRACKED_SLOW_LEAD_IMMEDIATE_DISTANCE = 45.0
VISION_UNTRACKED_SLOW_LEAD_IMMEDIATE_LEAD_BRAKE = 0.10
VISION_SLOW_LEAD_MAX_SPEED = 5.0
VISION_SLOW_LEAD_MIN_CLOSING_SPEED = 1.5
VISION_SLOW_LEAD_TRIGGER_TTC = 4.5
VISION_SLOW_LEAD_FULL_TTC = 2.0
VISION_SLOW_LEAD_MAX_DECEL = 1.2
VISION_SLOW_LEAD_MIN_DECEL = 0.18
VISION_SLOW_LEAD_MIN_MODEL_PROB = 0.9
LEAD_APPROACH_TFOLLOW_TRIGGER_TIME = 4.5
LEAD_APPROACH_TFOLLOW_FULL_TIME = 1.5
LEAD_APPROACH_TFOLLOW_MAX_DELTA = 0.18
LEAD_APPROACH_TFOLLOW_MAX_CLOSING_SPEED = 6.0
LEAD_APPROACH_TFOLLOW_MAX_LEAD_BRAKE = 2.5
LEAD_APPROACH_TFOLLOW_MIN_CLOSING_SPEED = 0.75
LEAD_APPROACH_TFOLLOW_MIN_LEAD_BRAKE = 0.2
LEAD_APPROACH_TFOLLOW_WINDOW_MIN = 6.0
LEAD_APPROACH_TFOLLOW_WINDOW_GAIN = 0.35
LEAD_APPROACH_TFOLLOW_RATE_UP = 1.0
LEAD_APPROACH_TFOLLOW_RATE_DOWN = 0.60
VISION_LEAD_TFOLLOW_MAX_EXTRA_DELTA = 0.24
VISION_LEAD_TFOLLOW_SLOW_LEAD_SPEED = 20.0
VISION_LEAD_TFOLLOW_GAP_BUFFER_MIN = 8.0
VISION_LEAD_TFOLLOW_GAP_BUFFER_GAIN = 0.35
VISION_LOW_SPEED_STOP_BUFFER_MAX_EGO_SPEED = 6.5
VISION_LOW_SPEED_STOP_BUFFER_MAX_LEAD_SPEED = 3.25
VISION_LOW_SPEED_STOP_BUFFER_HOLD_MAX_LEAD_SPEED = 4.0
VISION_LOW_SPEED_STOP_BUFFER_MIN_MODEL_PROB = 0.9
VISION_LOW_SPEED_STOP_BUFFER_MIN_CLOSING_SPEED = 0.35
VISION_LOW_SPEED_STOP_BUFFER_MIN_HOLD_REL_SPEED = -0.2
VISION_LOW_SPEED_STOP_BUFFER_BASE = 3.8
VISION_LOW_SPEED_STOP_BUFFER_EGO_GAIN = 0.80
VISION_LOW_SPEED_STOP_BUFFER_LEAD_GAIN = 0.25
VISION_LOW_SPEED_STOP_BUFFER_RELEASE_MARGIN = 0.9
VISION_LOW_SPEED_STOP_BUFFER_HOLD_TIME = 0.8
VISION_LOW_SPEED_STOP_BUFFER_MIN_BRAKE = 1.25
VISION_LOW_SPEED_STOP_BUFFER_BRAKE_GAIN = 0.25
VISION_CLOSE_STOP_HOLD_MAX_EGO_SPEED = 0.75
VISION_CLOSE_STOP_HOLD_MAX_LEAD_SPEED = 0.8
VISION_CLOSE_STOP_HOLD_MAX_DISTANCE = 3.5
VISION_CLOSE_STOP_HOLD_MIN_MODEL_PROB = 0.95
VISION_CLOSE_STOP_HOLD_MIN_BRAKE = 0.20
VISION_CLOSE_STOP_HOLD_MAX_BRAKE = 0.36
VISION_CLOSE_SETTLE_MAX_EGO_SPEED = 0.75
VISION_CLOSE_SETTLE_MAX_LEAD_SPEED = 2.75
VISION_CLOSE_SETTLE_MAX_DISTANCE = 4.2
VISION_CLOSE_SETTLE_MAX_LEAD_DELTA = 2.6
VISION_CLOSE_SETTLE_MIN_BRAKE = 0.16
VISION_CLOSE_SETTLE_MAX_BRAKE = 0.30
VISION_CLOSE_FINAL_GUARD_MAX_EGO_SPEED = 0.5
VISION_CLOSE_FINAL_GUARD_MAX_LEAD_SPEED = 2.75
VISION_CLOSE_FINAL_GUARD_MAX_DISTANCE = 4.5
VISION_CLOSE_FINAL_GUARD_MIN_BRAKE = 0.18
VISION_CLOSE_FINAL_GUARD_MAX_BRAKE = 0.28
VISION_CLOSE_RELEASE_HOLD_MAX_EGO_SPEED = 2.5
VISION_CLOSE_RELEASE_HOLD_MAX_LEAD_SPEED = 3.5
VISION_CLOSE_RELEASE_HOLD_MAX_DISTANCE = 4.2
VISION_CLOSE_RELEASE_HOLD_MIN_MODEL_PROB = 0.98
VISION_CLOSE_RELEASE_HOLD_MIN_LEAD_DELTA = -0.1
VISION_CLOSE_RELEASE_HOLD_MAX_LEAD_DELTA = 1.5
VISION_CLOSE_RELEASE_HOLD_MIN_BRAKE = 0.18
VISION_CLOSE_RELEASE_HOLD_MAX_BRAKE = 0.40
MANUAL_STOP_RESUME_OVERRIDE_TIME = 3.0
MANUAL_STOP_RESUME_OVERRIDE_MAX_SPEED = 2.0
MANUAL_STOP_RESUME_OVERRIDE_MIN_ACCEL = 0.2
FORCE_STOP_HANDOFF_MAX_VCRUISE = 0.5
LEAD_CATCHUP_ACCEL_MIN_EGO = 8.0
LEAD_CATCHUP_ACCEL_MIN_LEAD_DELTA = -0.5
LEAD_CATCHUP_ACCEL_MAX_GAP_BUFFER_MIN = 4.0
LEAD_CATCHUP_ACCEL_MAX_GAP_BUFFER_GAIN = 0.15
LOW_SPEED_FOLLOW_ACCEL_CAP_MAX_SPEED = 12.0
LOW_SPEED_FOLLOW_ACCEL_CAP_MIN_MODEL_PROB = 0.85
LOW_SPEED_FOLLOW_ACCEL_CAP_MAX_LEAD_BRAKE = 0.20
LOW_SPEED_FOLLOW_ACCEL_CAP_MIN_LEAD_DELTA = -1.2
LOW_SPEED_FOLLOW_ACCEL_CAP_MAX_GAP_BUFFER_MIN = 6.0
LOW_SPEED_FOLLOW_ACCEL_CAP_MAX_GAP_BUFFER_GAIN = 0.35
LOW_SPEED_FOLLOW_TRANSITION_MIN_SPEED = 3.0
LOW_SPEED_FOLLOW_TRANSITION_MAX_SPEED = 12.0
LOW_SPEED_FOLLOW_TRANSITION_MIN_MODEL_PROB = 0.85
LOW_SPEED_FOLLOW_TRANSITION_MAX_LEAD_BRAKE = 0.20
LOW_SPEED_FOLLOW_TRANSITION_MIN_GAP_MARGIN = 1.0
LOW_SPEED_FOLLOW_TRANSITION_MAX_CLOSING_SPEED = 0.6
LOW_SPEED_FOLLOW_TRANSITION_PREV_ACCEL_MIN = 0.18
LOW_SPEED_FOLLOW_TRANSITION_TARGET_BRAKE_MIN = -0.18
LOW_SPEED_FOLLOW_TRANSITION_MAX_BRAKE = 0.14
LOW_SPEED_FOLLOW_TRANSITION_MIN_BRAKE = 0.08
CRUISE_TRACKED_LEAD_ACCEL_CAP_MIN_SPEED = 10.0
CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_SPEED = 20.0
CRUISE_TRACKED_LEAD_ACCEL_CAP_MIN_MODEL_PROB = 0.85
CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_LEAD_BRAKE = 0.25
CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_PULLAWAY_SPEED = 1.0
CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_GAP_BUFFER_MIN = 12.0
CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_GAP_BUFFER_GAIN = 0.9
CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_LATERAL_OFFSET = 1.15
CRUISE_TRACKED_LEAD_ACCEL_CAP_UNRESOLVED_MIN_CLOSING_SPEED = 1.5
CRUISE_TRACKED_LEAD_ACCEL_CAP_UNRESOLVED_MAX_LEAD_DELTA = 0.25
CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_ACCEL = 0.18
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MIN_SPEED = 12.0
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_SPEED = 22.0
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MIN_MODEL_PROB = 0.9
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_LEAD_BRAKE = 0.35
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_LATERAL_OFFSET = 1.15
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_PULLAWAY_SPEED = 2.25
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_HEADWAY_ABOVE_TARGET = 0.95
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MIN_DELTA_A = 0.18
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MIN_STEP = 0.06
CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_STEP = 0.18

# Uncertainty-based filter disable thresholds
UNCERT_SLOPE_TRIG = 0.12  # per second
UNCERT_MAG_TRIG = 0.50
UNCERT_PANIC_MIN_CLOSING_SPEED = 2.0
UNCERT_PANIC_MIN_CLOSING_SPEED_GAIN = 0.08
UNCERT_PANIC_MAX_GAP_BUFFER_MIN = 8.0
UNCERT_PANIC_MAX_GAP_BUFFER_GAIN = 0.35
STEADY_FOLLOW_SMOOTHING_MIN_SPEED = 22.0
STEADY_FOLLOW_SMOOTHING_MIN_CLOSING_SPEED = 0.15
STEADY_FOLLOW_SMOOTHING_MAX_CLOSING_SPEED = 1.8
STEADY_FOLLOW_SMOOTHING_MIN_HEADWAY = 0.95
STEADY_FOLLOW_SMOOTHING_HEADWAY_BELOW_TARGET = 0.35
STEADY_FOLLOW_SMOOTHING_HEADWAY_ABOVE_TARGET = 0.90
STEADY_FOLLOW_SMOOTHING_MAX_LEAD_BRAKE = 0.35
STEADY_FOLLOW_SMOOTHING_MIN_MODEL_PROB = 0.7
STEADY_FOLLOW_SMOOTHING_FILTER_FACTOR_FLOOR = 0.24
STEADY_FOLLOW_BRAKE_CAP_MIN_HEADWAY = 1.05
STEADY_FOLLOW_BRAKE_CAP_MAX_HEADWAY_ABOVE_TARGET = 0.90
STEADY_FOLLOW_BRAKE_CAP_MIN_REL_SPEED = -1.2
STEADY_FOLLOW_BRAKE_CAP_MAX_CLOSING_SPEED = 2.2
STEADY_FOLLOW_BRAKE_CAP_ZERO_REL_SPEED_DECEL = 0.12
STEADY_FOLLOW_BRAKE_CAP_OPENING_DECEL = 0.08
STEADY_FOLLOW_BRAKE_CAP_MIN_DECEL = 0.18
STEADY_FOLLOW_BRAKE_CAP_MAX_DECEL = 0.32
STEADY_FOLLOW_BRAKE_CAP_SPACIOUS_HEADWAY_MARGIN = 0.45
STEADY_FOLLOW_BRAKE_CAP_SPACIOUS_MIN_HEADWAY = 1.80
STEADY_FOLLOW_BRAKE_CAP_SPACIOUS_MAX_LEAD_BRAKE = 0.15
FAR_LEAD_COMFORT_BRAKE_CAP_MIN_DISTANCE = 80.0
FAR_LEAD_COMFORT_BRAKE_CAP_MIN_CLOSING_SPEED = 0.1
FAR_LEAD_COMFORT_BRAKE_CAP_MAX_CLOSING_SPEED = 2.0
FAR_LEAD_COMFORT_BRAKE_CAP_MIN_MODEL_PROB = 0.95
FAR_LEAD_COMFORT_BRAKE_CAP_MAX_LEAD_BRAKE = 0.12
FAR_LEAD_COMFORT_BRAKE_CAP_MIN_TTC = 7.5
FAR_LEAD_COMFORT_BRAKE_CAP_MIN_HEADWAY_MARGIN = 0.55
FAR_LEAD_COMFORT_BRAKE_CAP_FULL_HEADWAY_MARGIN = 1.00
FAR_LEAD_COMFORT_BRAKE_CAP_MIN_DECEL = 0.05
FAR_LEAD_COMFORT_BRAKE_CAP_MAX_DECEL = 0.18
FAR_LEAD_COMFORT_BRAKE_CAP_FULL_RELAX_DECEL = 0.05
MATCHED_FOLLOW_TRANSITION_MIN_SPEED = 20.0
MATCHED_FOLLOW_TRANSITION_MIN_HEADWAY_MARGIN = 0.25
MATCHED_FOLLOW_TRANSITION_FULL_HEADWAY_MARGIN = 0.75
MATCHED_FOLLOW_TRANSITION_MIN_MODEL_PROB = 0.9
MATCHED_FOLLOW_TRANSITION_MAX_LEAD_BRAKE = 0.18
MATCHED_FOLLOW_TRANSITION_MAX_CLOSING_SPEED = 1.75
MATCHED_FOLLOW_TRANSITION_MIN_TTC = 12.0
MATCHED_FOLLOW_TRANSITION_MIN_POSITIVE_STEP = 0.08
MATCHED_FOLLOW_TRANSITION_MAX_POSITIVE_STEP = 0.18
MATCHED_FOLLOW_TRANSITION_MIN_NEGATIVE_STEP = 0.08
MATCHED_FOLLOW_TRANSITION_MAX_NEGATIVE_STEP = 0.16
MATCHED_FOLLOW_TRANSITION_SIGN_CROSS_STEP = 0.10
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_SPEED = 10.0
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_SPEED = MATCHED_FOLLOW_TRANSITION_MIN_SPEED
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_HEADWAY_MARGIN = 0.45
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_FULL_HEADWAY_MARGIN = 1.00
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_MODEL_PROB = 0.98
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_LEAD_BRAKE = 0.08
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_CLOSING_SPEED = 1.25
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_TTC = 18.0
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_POSITIVE_STEP = 0.06
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_POSITIVE_STEP = 0.10
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_NEGATIVE_STEP = 0.05
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_NEGATIVE_STEP = 0.08
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_SIGN_CROSS_STEP = 0.06
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_TARGET = -0.12
LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_DELTA_A = 0.12
NEAR_DUPLICATE_LEAD_TRANSITION_MIN_SPEED = 20.0
NEAR_DUPLICATE_LEAD_TRANSITION_MIN_MODEL_PROB = 0.95
NEAR_DUPLICATE_LEAD_TRANSITION_MAX_LEAD_BRAKE = 0.35
NEAR_DUPLICATE_LEAD_TRANSITION_MAX_CLOSING_SPEED = 3.5
NEAR_DUPLICATE_LEAD_TRANSITION_MIN_TTC = 8.0
NEAR_DUPLICATE_LEAD_TRANSITION_MIN_HEADWAY_BELOW_TARGET = 0.45
NEAR_DUPLICATE_LEAD_TRANSITION_MAX_HEADWAY_ABOVE_TARGET = 0.85
NEAR_DUPLICATE_LEAD_TRANSITION_MIN_DELTA_A = 0.35
NEAR_DUPLICATE_LEAD_TRANSITION_POSITIVE_STEP = 0.22
NEAR_DUPLICATE_LEAD_TRANSITION_NEGATIVE_STEP = 0.32
NEAR_DUPLICATE_LEAD_TRANSITION_SIGN_CROSS_STEP = 0.18
TRACKED_VISION_MODEL_FLOOR_MIN_SPEED = 10.0
TRACKED_VISION_MODEL_FLOOR_MIN_MODEL_PROB = 0.95
TRACKED_VISION_MODEL_FLOOR_MIN_MODEL_DECEL = 0.80
TRACKED_VISION_MODEL_FLOOR_MIN_CLOSING_SPEED = 1.0
TRACKED_VISION_MODEL_FLOOR_MAX_TTC = 22.0
TRACKED_VISION_MODEL_FLOOR_MIN_GAP_MARGIN = -2.0
TRACKED_VISION_MODEL_FLOOR_MAX_GAP_BUFFER_MIN = 4.0
TRACKED_VISION_MODEL_FLOOR_MAX_GAP_BUFFER_GAIN = 0.25
TRACKED_VISION_MODEL_FLOOR_MIN_DECEL = 0.35
TRACKED_VISION_MODEL_FLOOR_MAX_DECEL = 1.10
TRACKED_VISION_MODEL_FLOOR_LEAD_BRAKE_MAX = 0.18
TRACKED_VISION_MODEL_CAP_MIN_SPEED = 14.0
TRACKED_VISION_MODEL_CAP_MAX_SPEED = 32.0
TRACKED_VISION_MODEL_CAP_MIN_MODEL_PROB = 0.95
TRACKED_VISION_MODEL_CAP_MAX_MODEL_DECEL = 0.75
TRACKED_VISION_MODEL_CAP_MIN_CLOSING_SPEED = 0.75
TRACKED_VISION_MODEL_CAP_MAX_CLOSING_SPEED = 4.0
TRACKED_VISION_MODEL_CAP_MAX_LEAD_BRAKE = 0.55
TRACKED_VISION_MODEL_CAP_MIN_TTC = 7.0
TRACKED_VISION_MODEL_CAP_MIN_GAP_MARGIN = -1.5
TRACKED_VISION_MODEL_CAP_MAX_GAP_BUFFER_MIN = 4.0
TRACKED_VISION_MODEL_CAP_MAX_GAP_BUFFER_GAIN = 0.25
TRACKED_VISION_MODEL_CAP_MIN_DECEL = 0.45
TRACKED_VISION_MODEL_CAP_MAX_DECEL = 1.10

# Lookup table for turns
_A_TOTAL_MAX_V = [3.5, 3.5, 3.2]
_A_TOTAL_MAX_BP = [0., 20., 40.]

_preap_follow_cache = None


def get_preap_follow_limit(v_ego):
  global _preap_follow_cache
  if _preap_follow_cache is None:
    try:
      from opendbc.car.tesla.preap.constants import ACCEL_PREAP_BP, ACCEL_PREAP_FOLLOW
      _preap_follow_cache = (ACCEL_PREAP_BP, ACCEL_PREAP_FOLLOW)
    except ImportError:
      _preap_follow_cache = (None, None)
  bp, values = _preap_follow_cache
  if bp is None:
    return None
  return float(np.interp(v_ego, bp, values))


def get_longitudinal_personality(sm):
  return sm['selfdriveState'].personality


def get_max_accel(v_ego):
  return np.interp(v_ego, A_CRUISE_MAX_BP, A_CRUISE_MAX_VALS)

def get_coast_accel(pitch):
  return np.sin(pitch) * -5.65 - 0.3  # fitted from data using xx/projects/allow_throttle/compute_coast_accel.py


def limit_accel_in_turns(v_ego, angle_steers, a_target, CP):
  """
  This function returns a limited long acceleration allowed, depending on the existing lateral acceleration
  this should avoid accelerating when losing the target in turns
  """
  # FIXME: This function to calculate lateral accel is incorrect and should use the VehicleModel
  # The lookup table for turns should also be updated if we do this
  a_total_max = np.interp(v_ego, _A_TOTAL_MAX_BP, _A_TOTAL_MAX_V)
  a_y = v_ego ** 2 * angle_steers * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
  a_x_allowed = math.sqrt(max(a_total_max ** 2 - a_y ** 2, 0.))

  return [a_target[0], min(a_target[1], a_x_allowed)]


def should_publish_planner_fcw(crash_cnt: int, car_state, radar_state) -> bool:
  return (
    crash_cnt > 2 and
    not car_state.standstill and
    should_trigger_planner_fcw(radar_state.leadOne, float(car_state.vEgo))
  )


def get_vehicle_min_accel(CP, v_ego):
  # Planner-side physical decel capability estimate for GM pedal-long paths.
  if getattr(CP, "carName", "") == "gm" and getattr(CP, "enableGasInterceptorDEPRECATED", False):
    try:
      from opendbc.car.gm.values import GMFlags, CAR
      if bool(CP.flags & GMFlags.PEDAL_LONG.value):
        bolt_pedal_long_cars = {
          CAR.CHEVROLET_BOLT_CC_2017,
          CAR.CHEVROLET_BOLT_CC_2018_2021,
          CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL,
          CAR.CHEVROLET_BOLT_CC_2022_2023,
          CAR.CHEVROLET_MALIBU_HYBRID_CC,
        }
        if CP.carFingerprint in bolt_pedal_long_cars:
          return float(np.interp(v_ego, [0.0, 1.5, 4.0, 8.0, 15.0, 30.0],
                                 [-0.93, -1.28, -1.98, -2.58, -2.86, -2.95]))
        return float(np.interp(v_ego, [0.0, 1.5, 4.0, 8.0, 15.0, 30.0],
                               [-0.95, -1.3, -1.85, -2.3, -2.6, -2.8]))
    except Exception:
      pass
  return float(ACCEL_MIN)


def get_planner_v_ego(CP, car_state):
  v_ego = max(car_state.vEgo, car_state.vEgoCluster)

  is_gm = getattr(CP, "carName", "") == "gm" or getattr(CP, "brand", "") == "gm"
  if is_gm and getattr(CP, "enableGasInterceptorDEPRECATED", False):
    try:
      from opendbc.car.gm.values import GMFlags
      is_gm_pedal_long = bool(CP.flags & GMFlags.PEDAL_LONG.value)
      if is_gm_pedal_long:
        return float(car_state.vEgo)
    except Exception:
      pass

  return float(v_ego)


def get_accel_from_plan_classic(CP, speeds, accels, vEgoStopping):
  if len(speeds) == CONTROL_N:
    v_target_now = np.interp(DT_MDL, CONTROL_N_T_IDX, speeds)
    a_target_now = np.interp(DT_MDL, CONTROL_N_T_IDX, accels)

    v_target = np.interp(CP.longitudinalActuatorDelay + DT_MDL, CONTROL_N_T_IDX, speeds)
    if v_target != v_target_now:
      a_target = 2 * (v_target - v_target_now) / CP.longitudinalActuatorDelay - a_target_now
    else:
      a_target = a_target_now

    v_target_1sec = np.interp(CP.longitudinalActuatorDelay + DT_MDL + 1.0, CONTROL_N_T_IDX, speeds)
  else:
    v_target = 0.0
    v_target_1sec = 0.0
    a_target = 0.0
  should_stop = (v_target < vEgoStopping and
                 v_target_1sec < vEgoStopping)
  return a_target, should_stop


def get_accel_from_plan(speeds, accels, action_t=DT_MDL, vEgoStopping=0.05):
  if len(speeds) == CONTROL_N:
    v_now = speeds[0]
    a_now = accels[0]

    v_target = np.interp(action_t, CONTROL_N_T_IDX, speeds)
    a_target = 2 * (v_target - v_now) / (action_t) - a_now
    v_target_1sec = np.interp(action_t + 1.0, CONTROL_N_T_IDX, speeds)
  else:
    v_target = 0.0
    v_target_1sec = 0.0
    a_target = 0.0
  should_stop = (v_target < vEgoStopping and
                 v_target_1sec < vEgoStopping)
  return a_target, should_stop


class LongitudinalPlanner:
  def __init__(self, CP, init_v=0.0, init_a=0.0, dt=DT_MDL):
    self.CP = CP
    self.mpc = LongitudinalMpc(dt=dt)
    self.fcw = False
    self.dt = dt
    self.model_allow_throttle = True
    self.allow_throttle = True
    self.mode = 'acc'
    self.is_preap = (
      CP.brand == "tesla" and CP.carFingerprint == "TESLA_MODEL_S_PREAP" and
      CP.openpilotLongitudinalControl and not CP.pcmCruise
    )
    self.nap_adaptive_accel = False
    self._preap_params = None
    self._preap_param_frame = 0

    self.generation = None

    self.a_desired = init_a
    self.v_desired_filter = FirstOrderFilter(init_v, 2.0, self.dt)
    self.v_model_error = 0.0
    self.output_a_target = 0.0
    self.output_should_stop = False
    self.confident_lead_depart_elapsed = 0.0

    self.v_desired_trajectory = np.zeros(CONTROL_N)
    self.a_desired_trajectory = np.zeros(CONTROL_N)
    self.j_desired_trajectory = np.zeros(CONTROL_N)
    self.solverExecutionTime = 0.0

    # ---- Rubberband mitigation state ----
    # Two uncertainty tracks (slow/fast) for asymmetric gating
    self.uncert_slow = FirstOrderFilter(0.0, 1.6, self.dt)  # ~lam=0.6
    self.uncert_fast = FirstOrderFilter(0.0, 0.9, self.dt)  # faster cool-down for accel decisions
    # Lead stability tracking
    self.prev_lead_dist = None
    self.last_big_brake_t = 0.0
    self.stable_lead = False
    # Smoothed lead distance
    self.lead_dist_f = None

    # Uncertainty slope tracking
    self._uncert_last = 0.0
    self._uncert_last_t = None
    self._panic_bypass_log_t = 0.0
    self.effective_t_follow = None
    self.vision_low_speed_stop_hold_until = 0.0
    self.vision_lead_approach_confirm_t = 0.0
    self.untracked_slow_lead_confirm_t = 0.0
    self.manual_stop_resume_override_until = 0.0
    self.lead_depart_accel_hold_until = 0.0

    if self.is_preap:
      try:
        from openpilot.common.params import Params
        self._preap_params = Params()
        self.nap_adaptive_accel = self._preap_params.get_bool("NAPAdaptiveAccel")
      except Exception:
        self._preap_params = None
        self.nap_adaptive_accel = False

  @property
  def mlsim(self):
    return is_tinygrad_model_version(self.generation)

  def get_mpc_mode(self) -> str:
    if not self.mlsim:
      return self.mode
    return getattr(self.mpc, 'mode', 'acc')

  @staticmethod
  def get_model_speed_error(model_msg, v_ego):
    try:
      if len(model_msg.temporalPose.trans):
        return float(np.clip(model_msg.temporalPose.trans[0] - v_ego, -5.0, 5.0))
    except AttributeError:
      pass
    return 0.0

  @staticmethod
  def parse_model(model_msg, model_error, v_ego, starpilot_toggles):
    if (len(model_msg.position.x) == ModelConstants.IDX_N and
      len(model_msg.velocity.x) == ModelConstants.IDX_N and
      len(model_msg.acceleration.x) == ModelConstants.IDX_N):
      x = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.position.x) - model_error * T_IDXS_MPC
      v = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.velocity.x) - model_error
      a = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.acceleration.x)
      j = np.zeros(len(T_IDXS_MPC))
    else:
      x = np.zeros(len(T_IDXS_MPC))
      v = np.zeros(len(T_IDXS_MPC))
      a = np.zeros(len(T_IDXS_MPC))
      j = np.zeros(len(T_IDXS_MPC))

    if starpilot_toggles.taco_tune:
      max_lat_accel = np.interp(v_ego, [5, 10, 20], [1.5, 2.0, 3.0])
      curvatures = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS, model_msg.orientationRate.z) / np.clip(v, 0.3, 100.0)
      max_v = np.sqrt(max_lat_accel / (np.abs(curvatures) + 1e-3)) - 2.0
      v = np.minimum(max_v, v)

    if len(model_msg.meta.disengagePredictions.gasPressProbs) > 1:
      throttle_prob = model_msg.meta.disengagePredictions.gasPressProbs[1]
    else:
      throttle_prob = 1.0
    return x, v, a, j, throttle_prob

  def get_close_lead_brake_cap(self, lead, v_ego, accel_min):
    if lead is None or not lead.status:
      return None

    lead_brake = max(0.0, -float(lead.aLeadK))
    reaction_t = max(self.CP.longitudinalActuatorDelay, self.dt)
    closing_speed = max(0.0, v_ego - lead.vLead)
    projected_closing_speed = closing_speed + lead_brake * reaction_t
    if projected_closing_speed < 0.1 and lead_brake < 0.5:
      return None

    target_gap = float(np.clip(2.0 + 0.2 * v_ego, 2.0, 6.0))
    delay_buffer = projected_closing_speed * reaction_t
    available_gap = max(float(lead.dRel) - target_gap - delay_buffer, 0.5)
    projected_ttc = available_gap / max(projected_closing_speed, 0.1)
    if projected_ttc > CLOSE_LEAD_BRAKE_CAP_MAX_TTC:
      return None
    required_decel = (projected_closing_speed ** 2) / (2.0 * available_gap) + 0.7 * lead_brake
    if required_decel < 0.2:
      return None

    return max(accel_min, -required_decel)

  def get_vision_lead_approach_cap(self, lead, v_ego, accel_min, t_follow):
    if lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < VISION_LEAD_APPROACH_MIN_MODEL_PROB:
      return None

    lead_brake = max(0.0, -float(lead.aLeadK))
    reaction_t = max(self.CP.longitudinalActuatorDelay, self.dt)
    closing_speed = max(0.0, v_ego - lead.vLead)
    projected_closing_speed = closing_speed + lead_brake * reaction_t
    if projected_closing_speed < VISION_LEAD_APPROACH_MIN_CLOSING_SPEED:
      return None

    tight_follow_gap = float(t_follow * v_ego + VISION_LEAD_APPROACH_TIGHT_BUFFER)
    gap_to_tight_follow = float(lead.dRel) - tight_follow_gap
    time_to_tight_follow = gap_to_tight_follow / max(projected_closing_speed, 0.1)
    if time_to_tight_follow > VISION_LEAD_APPROACH_TRIGGER_TIME:
      return None

    desired_gap = float(desired_follow_distance(v_ego, lead.vLead, t_follow))
    if float(lead.dRel) > desired_gap + VISION_LEAD_APPROACH_TIGHT_BUFFER:
      return None

    time_factor = float(np.clip((VISION_LEAD_APPROACH_TRIGGER_TIME - time_to_tight_follow) /
                                (VISION_LEAD_APPROACH_TRIGGER_TIME - VISION_LEAD_APPROACH_FULL_TIME), 0.0, 1.0))
    prob_factor = float(np.clip((lead_prob - VISION_LEAD_APPROACH_MIN_MODEL_PROB) /
                                (VISION_LEAD_APPROACH_FULL_MODEL_PROB - VISION_LEAD_APPROACH_MIN_MODEL_PROB), 0.0, 1.0))
    closing_factor = float(np.clip(projected_closing_speed / (VISION_LEAD_APPROACH_MIN_CLOSING_SPEED + 2.5), 0.0, 1.0))
    tight_follow_deficit = max(tight_follow_gap - float(lead.dRel), 0.0)
    tight_follow_buffer = max(VISION_LEAD_APPROACH_DEFICIT_BUFFER_MIN,
                              VISION_LEAD_APPROACH_DEFICIT_BUFFER_GAIN * float(v_ego) + 1.0)
    deficit_factor = float(np.clip(tight_follow_deficit / tight_follow_buffer, 0.0, 1.0))

    approach_decel = VISION_LEAD_APPROACH_MAX_DECEL * time_factor * (0.45 + 0.55 * prob_factor)
    approach_decel *= 0.6 + 0.4 * closing_factor
    deficit_decel = VISION_LEAD_APPROACH_DEFICIT_MAX_DECEL * deficit_factor * prob_factor
    deficit_decel *= 0.5 + 0.5 * closing_factor
    approach_decel = max(approach_decel, deficit_decel)

    # If a tracked vision lead is already far inside the tight-follow window and
    # it is actively braking, don't stay stuck at the softer comfort cap.
    if deficit_factor >= VISION_LEAD_APPROACH_BRAKING_DEFICIT_MIN and lead_brake >= VISION_LEAD_APPROACH_BRAKING_MIN_LEAD_BRAKE:
      braking_floor = float(np.interp(
        lead_brake,
        [VISION_LEAD_APPROACH_BRAKING_MIN_LEAD_BRAKE, VISION_LEAD_APPROACH_BRAKING_FULL_LEAD_BRAKE],
        [VISION_LEAD_APPROACH_BRAKING_FLOOR_MIN_DECEL, VISION_LEAD_APPROACH_BRAKING_FLOOR_MAX_DECEL],
      ))
      braking_floor *= 0.85 + 0.15 * max(closing_factor, prob_factor)
      approach_decel = max(approach_decel, braking_floor)

    if approach_decel < VISION_LEAD_APPROACH_MIN_DECEL:
      return None

    return max(accel_min, -approach_decel)

  def get_vision_untracked_slow_lead_cap(self, lead, v_ego, accel_min):
    if lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))

    lead_brake = max(0.0, -float(lead.aLeadK))
    reaction_t = max(self.CP.longitudinalActuatorDelay, self.dt)
    closing_speed = max(0.0, v_ego - lead.vLead)
    projected_closing_speed = closing_speed + lead_brake * reaction_t
    if projected_closing_speed < VISION_UNTRACKED_SLOW_LEAD_MIN_CLOSING_SPEED:
      return None

    closing_ratio = projected_closing_speed / max(float(v_ego), 0.1)
    if closing_ratio < VISION_UNTRACKED_SLOW_LEAD_MIN_CLOSING_RATIO:
      return None

    projected_ttc = float(lead.dRel) / max(projected_closing_speed, 0.1)
    if projected_ttc > VISION_UNTRACKED_SLOW_LEAD_TRIGGER_TTC:
      return None

    min_model_prob = VISION_UNTRACKED_SLOW_LEAD_MIN_MODEL_PROB
    max_distance_time = VISION_UNTRACKED_SLOW_LEAD_MAX_DISTANCE_TIME
    if float(lead.vLead) <= VISION_UNTRACKED_SLOW_LEAD_RELAXED_MAX_LEAD_SPEED and \
        projected_ttc <= VISION_UNTRACKED_SLOW_LEAD_RELAXED_MAX_TTC:
      closing_relax = float(np.clip((projected_closing_speed - VISION_UNTRACKED_SLOW_LEAD_RELAXED_MIN_CLOSING_SPEED) /
                                    (VISION_UNTRACKED_SLOW_LEAD_RELAXED_FULL_CLOSING_SPEED -
                                     VISION_UNTRACKED_SLOW_LEAD_RELAXED_MIN_CLOSING_SPEED), 0.0, 1.0))
      ttc_relax = float(np.clip((VISION_UNTRACKED_SLOW_LEAD_RELAXED_MAX_TTC - projected_ttc) /
                                (VISION_UNTRACKED_SLOW_LEAD_RELAXED_MAX_TTC -
                                 VISION_UNTRACKED_SLOW_LEAD_FULL_TTC), 0.0, 1.0))
      relax_factor = closing_relax * ttc_relax
      min_model_prob = float(np.interp(relax_factor, [0.0, 1.0],
                                       [VISION_UNTRACKED_SLOW_LEAD_MIN_MODEL_PROB,
                                        VISION_UNTRACKED_SLOW_LEAD_RELAXED_MODEL_PROB]))
      max_distance_time = float(np.interp(relax_factor, [0.0, 1.0],
                                          [VISION_UNTRACKED_SLOW_LEAD_MAX_DISTANCE_TIME,
                                           VISION_UNTRACKED_SLOW_LEAD_RELAXED_MAX_DISTANCE_TIME]))

    max_distance = float(np.clip(max_distance_time * v_ego,
                                 VISION_UNTRACKED_SLOW_LEAD_MIN_DISTANCE,
                                 VISION_UNTRACKED_SLOW_LEAD_MAX_DISTANCE))
    if float(lead.dRel) > max_distance:
      return None

    if lead_prob < min_model_prob:
      return None

    time_factor = float(np.clip((VISION_UNTRACKED_SLOW_LEAD_TRIGGER_TTC - projected_ttc) /
                                (VISION_UNTRACKED_SLOW_LEAD_TRIGGER_TTC - VISION_UNTRACKED_SLOW_LEAD_FULL_TTC),
                                0.0, 1.0))
    prob_factor = float(np.clip((lead_prob - min_model_prob) /
                                (VISION_UNTRACKED_SLOW_LEAD_FULL_MODEL_PROB - min_model_prob),
                                0.0, 1.0))
    closing_factor = float(np.clip((closing_ratio - VISION_UNTRACKED_SLOW_LEAD_MIN_CLOSING_RATIO) /
                                   (VISION_UNTRACKED_SLOW_LEAD_FULL_CLOSING_RATIO - VISION_UNTRACKED_SLOW_LEAD_MIN_CLOSING_RATIO),
                                   0.0, 1.0))
    approach_decel = VISION_UNTRACKED_SLOW_LEAD_MAX_DECEL * np.clip(
      0.5 * time_factor + 0.3 * prob_factor + 0.2 * closing_factor, 0.0, 1.0)
    if approach_decel < VISION_UNTRACKED_SLOW_LEAD_MIN_DECEL:
      return None

    return max(accel_min, -approach_decel)

  def get_vision_slow_stopped_lead_cap(self, lead, v_ego, accel_min, t_follow):
    if lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < VISION_SLOW_LEAD_MIN_MODEL_PROB or float(lead.vLead) > VISION_SLOW_LEAD_MAX_SPEED:
      return None

    lead_brake = max(0.0, -float(lead.aLeadK))
    reaction_t = max(self.CP.longitudinalActuatorDelay, self.dt)
    closing_speed = max(0.0, v_ego - lead.vLead)
    projected_closing_speed = closing_speed + lead_brake * reaction_t
    if projected_closing_speed < VISION_SLOW_LEAD_MIN_CLOSING_SPEED:
      return None

    stop_gap = float(max(STOP_DISTANCE + 1.0, 2.5 + 0.15 * max(float(lead.vLead), 0.0)))
    delay_buffer = projected_closing_speed * reaction_t
    available_gap = max(float(lead.dRel) - stop_gap - delay_buffer, 0.5)
    projected_ttc = available_gap / max(projected_closing_speed, 0.1)
    if projected_ttc > VISION_SLOW_LEAD_TRIGGER_TTC:
      return None

    time_factor = float(np.clip((VISION_SLOW_LEAD_TRIGGER_TTC - projected_ttc) /
                                (VISION_SLOW_LEAD_TRIGGER_TTC - VISION_SLOW_LEAD_FULL_TTC), 0.0, 1.0))
    prob_factor = float(np.clip((lead_prob - VISION_SLOW_LEAD_MIN_MODEL_PROB) /
                                (VISION_LEAD_APPROACH_FULL_MODEL_PROB - VISION_SLOW_LEAD_MIN_MODEL_PROB), 0.0, 1.0))
    speed_factor = float(np.clip((VISION_SLOW_LEAD_MAX_SPEED - max(float(lead.vLead), 0.0)) /
                                 VISION_SLOW_LEAD_MAX_SPEED, 0.0, 1.0))
    required_decel = (projected_closing_speed ** 2) / (2.0 * available_gap)
    decel_scale = 0.45 + 0.35 * time_factor + 0.20 * speed_factor
    approach_decel = min(VISION_SLOW_LEAD_MAX_DECEL, required_decel * decel_scale)
    approach_decel *= 0.65 + 0.35 * prob_factor
    if approach_decel < VISION_SLOW_LEAD_MIN_DECEL:
      return None

    return max(accel_min, -approach_decel)

  def tracked_vision_lead_approach_needs_immediate_brake(self, lead, v_ego, approach_cap):
    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    reaction_t = max(self.CP.longitudinalActuatorDelay, self.dt)
    projected_closing_speed = max(0.0, v_ego - float(lead.vLead)) + lead_brake * reaction_t
    bypass_distance = max(VISION_LEAD_APPROACH_CONFIRM_BYPASS_DISTANCE_MIN,
                          VISION_LEAD_APPROACH_CONFIRM_BYPASS_DISTANCE_TIME * float(v_ego))
    return (
      approach_cap <= -VISION_LEAD_APPROACH_CONFIRM_BYPASS_DECEL or
      projected_closing_speed >= VISION_LEAD_APPROACH_CONFIRM_BYPASS_CLOSING_SPEED or
      lead_brake >= VISION_LEAD_APPROACH_CONFIRM_BYPASS_LEAD_BRAKE or
      float(lead.dRel) <= bypass_distance
    )

  def get_dynamic_t_follow(self, base_t_follow, lead, v_ego):
    base_t_follow = float(base_t_follow)
    target_t_follow = base_t_follow

    if lead is not None and lead.status:
      lead_prob = float(getattr(lead, "modelProb", 1.0 if bool(getattr(lead, "radar", False)) else 0.0))
      if bool(getattr(lead, "radar", False)) or lead_prob >= VISION_LEAD_APPROACH_MIN_MODEL_PROB:
        lead_brake = max(0.0, -float(lead.aLeadK))
        closing_speed = max(0.0, v_ego - lead.vLead)
        if closing_speed >= LEAD_APPROACH_TFOLLOW_MIN_CLOSING_SPEED or lead_brake >= LEAD_APPROACH_TFOLLOW_MIN_LEAD_BRAKE:
          desired_gap = float(desired_follow_distance(v_ego, lead.vLead, base_t_follow))
          approach_window = max(LEAD_APPROACH_TFOLLOW_WINDOW_MIN, LEAD_APPROACH_TFOLLOW_WINDOW_GAIN * float(v_ego))
          if float(lead.dRel) <= desired_gap + approach_window:
            reaction_t = max(self.CP.longitudinalActuatorDelay, self.dt)
            projected_closing_speed = closing_speed + 0.5 * lead_brake * reaction_t
            gap_to_follow = max(float(lead.dRel) - desired_gap, 0.0)
            time_to_follow = gap_to_follow / max(projected_closing_speed, 0.1)
            time_factor = float(np.clip((LEAD_APPROACH_TFOLLOW_TRIGGER_TIME - time_to_follow) /
                                        (LEAD_APPROACH_TFOLLOW_TRIGGER_TIME - LEAD_APPROACH_TFOLLOW_FULL_TIME), 0.0, 1.0))
            closing_factor = float(np.clip(closing_speed / LEAD_APPROACH_TFOLLOW_MAX_CLOSING_SPEED, 0.0, 1.0))
            brake_factor = float(np.clip(lead_brake / LEAD_APPROACH_TFOLLOW_MAX_LEAD_BRAKE, 0.0, 1.0))
            target_delta = LEAD_APPROACH_TFOLLOW_MAX_DELTA * np.clip(
              0.55 * time_factor + 0.25 * closing_factor + 0.20 * brake_factor, 0.0, 1.0)
            if not bool(getattr(lead, "radar", False)):
              gap_deficit = max(desired_gap - float(lead.dRel), 0.0)
              gap_buffer = max(VISION_LEAD_TFOLLOW_GAP_BUFFER_MIN,
                               VISION_LEAD_TFOLLOW_GAP_BUFFER_GAIN * float(v_ego))
              gap_factor = float(np.clip(gap_deficit / gap_buffer, 0.0, 1.0))
              slow_lead_factor = float(np.clip((VISION_LEAD_TFOLLOW_SLOW_LEAD_SPEED - float(lead.vLead)) /
                                               VISION_LEAD_TFOLLOW_SLOW_LEAD_SPEED, 0.0, 1.0))
              vision_extra = VISION_LEAD_TFOLLOW_MAX_EXTRA_DELTA * np.clip(
                0.40 * time_factor + 0.30 * gap_factor + 0.20 * slow_lead_factor + 0.10 * closing_factor,
                0.0, 1.0)
              target_delta += vision_extra
            target_t_follow = base_t_follow + float(target_delta)

    if self.effective_t_follow is None:
      self.effective_t_follow = base_t_follow

    rate = LEAD_APPROACH_TFOLLOW_RATE_UP if target_t_follow > self.effective_t_follow else LEAD_APPROACH_TFOLLOW_RATE_DOWN
    step = rate * self.dt
    self.effective_t_follow = float(np.clip(target_t_follow, self.effective_t_follow - step, self.effective_t_follow + step))
    self.effective_t_follow = max(base_t_follow, self.effective_t_follow)
    return self.effective_t_follow

  def get_vision_low_speed_stop_buffer_cap(self, lead, v_ego, accel_min):
    if lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None, False

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < VISION_LOW_SPEED_STOP_BUFFER_MIN_MODEL_PROB:
      return None, False

    lead_speed = max(float(lead.vLead), 0.0)
    relative_speed = float(v_ego) - lead_speed
    closing_speed = max(0.0, v_ego - lead_speed)
    entry_context = (
      v_ego <= VISION_LOW_SPEED_STOP_BUFFER_MAX_EGO_SPEED and
      lead_speed <= VISION_LOW_SPEED_STOP_BUFFER_MAX_LEAD_SPEED and
      closing_speed >= VISION_LOW_SPEED_STOP_BUFFER_MIN_CLOSING_SPEED
    )
    hold_context = (
      v_ego <= VISION_LOW_SPEED_STOP_BUFFER_MAX_EGO_SPEED and
      lead_speed <= VISION_LOW_SPEED_STOP_BUFFER_HOLD_MAX_LEAD_SPEED and
      relative_speed >= VISION_LOW_SPEED_STOP_BUFFER_MIN_HOLD_REL_SPEED
    )

    now_t = time.monotonic()
    entry_buffer = max(3.2, VISION_LOW_SPEED_STOP_BUFFER_BASE +
                       VISION_LOW_SPEED_STOP_BUFFER_EGO_GAIN * float(v_ego) +
                       VISION_LOW_SPEED_STOP_BUFFER_LEAD_GAIN * lead_speed)
    release_buffer = entry_buffer + VISION_LOW_SPEED_STOP_BUFFER_RELEASE_MARGIN
    if entry_context and float(lead.dRel) <= entry_buffer:
      self.vision_low_speed_stop_hold_until = now_t + VISION_LOW_SPEED_STOP_BUFFER_HOLD_TIME

    latched = now_t < self.vision_low_speed_stop_hold_until
    active = bool(
      (entry_context and float(lead.dRel) <= entry_buffer) or
      (latched and hold_context and float(lead.dRel) <= release_buffer)
    )
    if not active:
      return None, False

    min_stop_brake = VISION_LOW_SPEED_STOP_BUFFER_MIN_BRAKE + VISION_LOW_SPEED_STOP_BUFFER_BRAKE_GAIN * float(v_ego)
    return max(accel_min, -min_stop_brake), True

  def get_vision_close_stop_hold_cap(self, lead, v_ego, accel_min, should_stop):
    if not should_stop or lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < VISION_CLOSE_STOP_HOLD_MIN_MODEL_PROB:
      return None

    lead_speed = max(float(lead.vLead), 0.0)
    near_standstill_settle = bool(
      float(v_ego) <= VISION_CLOSE_SETTLE_MAX_EGO_SPEED and
      lead_speed <= VISION_CLOSE_SETTLE_MAX_LEAD_SPEED and
      float(lead.dRel) <= VISION_CLOSE_SETTLE_MAX_DISTANCE
    )
    max_lead_speed = VISION_CLOSE_SETTLE_MAX_LEAD_SPEED if near_standstill_settle else VISION_CLOSE_STOP_HOLD_MAX_LEAD_SPEED
    max_distance = VISION_CLOSE_SETTLE_MAX_DISTANCE if near_standstill_settle else VISION_CLOSE_STOP_HOLD_MAX_DISTANCE
    if (
      float(v_ego) > VISION_CLOSE_STOP_HOLD_MAX_EGO_SPEED or
      lead_speed > max_lead_speed or
      float(lead.dRel) > max_distance
    ):
      return None

    distance_factor = float(np.clip((max_distance - float(lead.dRel)) /
                                    max(max_distance - 1.8, 0.1), 0.0, 1.0))
    speed_factor = float(np.clip(float(v_ego) / max(VISION_CLOSE_STOP_HOLD_MAX_EGO_SPEED, 0.1), 0.0, 1.0))
    hold_brake = VISION_CLOSE_STOP_HOLD_MIN_BRAKE + 0.08 * distance_factor + 0.08 * speed_factor
    if near_standstill_settle:
      settle_brake = VISION_CLOSE_SETTLE_MIN_BRAKE + 0.10 * distance_factor + 0.04 * speed_factor
      hold_brake = max(hold_brake, settle_brake)
    hold_brake = float(np.clip(hold_brake, VISION_CLOSE_STOP_HOLD_MIN_BRAKE, VISION_CLOSE_STOP_HOLD_MAX_BRAKE))
    brake_floor = -hold_brake
    return brake_floor if accel_min >= 0.0 else max(accel_min, brake_floor)

  def get_vision_close_release_hold_cap(self, lead, v_ego, accel_min, should_stop):
    if should_stop or lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < VISION_CLOSE_RELEASE_HOLD_MIN_MODEL_PROB:
      return None

    lead_speed = max(float(lead.vLead), 0.0)
    lead_delta = lead_speed - float(v_ego)
    near_standstill_settle = bool(
      float(v_ego) <= VISION_CLOSE_SETTLE_MAX_EGO_SPEED and
      lead_speed <= VISION_CLOSE_SETTLE_MAX_LEAD_SPEED and
      float(lead.dRel) <= VISION_CLOSE_SETTLE_MAX_DISTANCE and
      lead_delta <= VISION_CLOSE_SETTLE_MAX_LEAD_DELTA
    )
    max_lead_speed = VISION_CLOSE_SETTLE_MAX_LEAD_SPEED if near_standstill_settle else VISION_CLOSE_RELEASE_HOLD_MAX_LEAD_SPEED
    max_distance = VISION_CLOSE_SETTLE_MAX_DISTANCE if near_standstill_settle else VISION_CLOSE_RELEASE_HOLD_MAX_DISTANCE
    max_lead_delta = VISION_CLOSE_SETTLE_MAX_LEAD_DELTA if near_standstill_settle else VISION_CLOSE_RELEASE_HOLD_MAX_LEAD_DELTA
    if (
      float(v_ego) > VISION_CLOSE_RELEASE_HOLD_MAX_EGO_SPEED or
      lead_speed > max_lead_speed or
      float(lead.dRel) > max_distance or
      lead_delta < VISION_CLOSE_RELEASE_HOLD_MIN_LEAD_DELTA or
      lead_delta > max_lead_delta
    ):
      return None

    distance_factor = float(np.clip((max_distance - float(lead.dRel)) /
                                    max(max_distance - 2.8, 0.1), 0.0, 1.0))
    speed_factor = float(np.clip(float(v_ego) / max(VISION_CLOSE_RELEASE_HOLD_MAX_EGO_SPEED, 0.1), 0.0, 1.0))
    delta_factor = float(np.clip((max_lead_delta - lead_delta) /
                                 max(max_lead_delta - VISION_CLOSE_RELEASE_HOLD_MIN_LEAD_DELTA, 0.1),
                                 0.0, 1.0))
    hold_brake = VISION_CLOSE_RELEASE_HOLD_MIN_BRAKE + 0.12 * distance_factor + 0.06 * speed_factor + 0.04 * delta_factor
    if near_standstill_settle:
      settle_brake = VISION_CLOSE_SETTLE_MIN_BRAKE + 0.08 * distance_factor + 0.02 * delta_factor
      hold_brake = max(hold_brake, settle_brake)
    hold_brake = float(np.clip(hold_brake, VISION_CLOSE_RELEASE_HOLD_MIN_BRAKE, VISION_CLOSE_RELEASE_HOLD_MAX_BRAKE))
    brake_floor = -hold_brake
    return brake_floor if accel_min >= 0.0 else max(accel_min, brake_floor)

  def get_vision_close_settle_cap(self, lead, v_ego, accel_min, stop_guard_active):
    if lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < VISION_CLOSE_STOP_HOLD_MIN_MODEL_PROB:
      return None

    lead_speed = max(float(lead.vLead), 0.0)
    lead_delta = lead_speed - float(v_ego)
    if (
      float(v_ego) > VISION_CLOSE_SETTLE_MAX_EGO_SPEED or
      lead_speed > VISION_CLOSE_SETTLE_MAX_LEAD_SPEED or
      float(lead.dRel) > VISION_CLOSE_SETTLE_MAX_DISTANCE or
      lead_delta > VISION_CLOSE_SETTLE_MAX_LEAD_DELTA
    ):
      return None

    if not stop_guard_active and lead_delta < 0.0:
      return None

    distance_factor = float(np.clip((VISION_CLOSE_SETTLE_MAX_DISTANCE - float(lead.dRel)) /
                                    max(VISION_CLOSE_SETTLE_MAX_DISTANCE - 2.8, 0.1), 0.0, 1.0))
    delta_factor = float(np.clip((VISION_CLOSE_SETTLE_MAX_LEAD_DELTA - lead_delta) /
                                 max(VISION_CLOSE_SETTLE_MAX_LEAD_DELTA, 0.1), 0.0, 1.0))
    hold_brake = VISION_CLOSE_SETTLE_MIN_BRAKE + 0.10 * distance_factor + 0.04 * delta_factor
    hold_brake = float(np.clip(hold_brake, VISION_CLOSE_SETTLE_MIN_BRAKE, VISION_CLOSE_SETTLE_MAX_BRAKE))
    brake_floor = -hold_brake
    return brake_floor if accel_min >= 0.0 else max(accel_min, brake_floor)

  def get_vision_close_final_guard_cap(self, lead, v_ego, accel_min):
    if lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    lead_speed = max(float(lead.vLead), 0.0)
    if (
      lead_prob < VISION_CLOSE_STOP_HOLD_MIN_MODEL_PROB or
      float(v_ego) > VISION_CLOSE_FINAL_GUARD_MAX_EGO_SPEED or
      lead_speed > VISION_CLOSE_FINAL_GUARD_MAX_LEAD_SPEED or
      float(lead.dRel) > VISION_CLOSE_FINAL_GUARD_MAX_DISTANCE
    ):
      return None

    distance_factor = float(np.clip((VISION_CLOSE_FINAL_GUARD_MAX_DISTANCE - float(lead.dRel)) /
                                    max(VISION_CLOSE_FINAL_GUARD_MAX_DISTANCE - 2.8, 0.1), 0.0, 1.0))
    hold_brake = VISION_CLOSE_FINAL_GUARD_MIN_BRAKE + 0.10 * distance_factor
    hold_brake = float(np.clip(hold_brake, VISION_CLOSE_FINAL_GUARD_MIN_BRAKE, VISION_CLOSE_FINAL_GUARD_MAX_BRAKE))
    brake_floor = -hold_brake
    return brake_floor if accel_min >= 0.0 else max(accel_min, brake_floor)

  def _update_manual_stop_resume_override(self, sm):
    now_t = time.monotonic()
    lead = sm["radarState"].leadOne
    no_lead = not bool(getattr(lead, "status", False))
    try:
      starpilot_car_state = sm["starpilotCarState"]
    except KeyError:
      starpilot_car_state = None
    accel_pressed = bool(getattr(starpilot_car_state, "accelPressed", False))
    model_should_stop = bool(getattr(sm["modelV2"].action, "shouldStop", False))
    standstill = bool(getattr(sm["carState"], "standstill", False))
    forcing_stop = bool(getattr(sm["starpilotPlan"], "forcingStop", False))
    red_light = bool(getattr(sm["starpilotPlan"], "redLight", False))

    if standstill and no_lead and accel_pressed and (forcing_stop or red_light or model_should_stop):
      self.manual_stop_resume_override_until = now_t + MANUAL_STOP_RESUME_OVERRIDE_TIME

    return bool(
      no_lead and
      float(getattr(sm["carState"], "vEgo", 0.0)) < MANUAL_STOP_RESUME_OVERRIDE_MAX_SPEED and
      now_t < self.manual_stop_resume_override_until
    )

  def is_confident_lead_depart(self, lead, v_ego):
    if lead is None or not lead.status:
      return False

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and lead_prob < LEAD_DEPART_ACCEL_HOLD_MIN_MODEL_PROB:
      return False

    lead_speed = max(float(lead.vLead), 0.0)
    lead_delta = lead_speed - float(v_ego)
    lead_accel = float(getattr(lead, "aLeadK", 0.0))
    return bool(
      float(lead.dRel) >= LEAD_DEPART_CONFIDENT_MIN_GAP and
      float(lead.dRel) <= LEAD_DEPART_CONFIDENT_MAX_GAP and
      lead_speed >= LEAD_DEPART_CONFIDENT_MIN_LEAD_SPEED and
      lead_delta >= LEAD_DEPART_CONFIDENT_MIN_LEAD_DELTA and
      lead_accel >= LEAD_DEPART_CONFIDENT_MIN_LEAD_ACCEL
    )

  @staticmethod
  def get_centered_model_lead(model_data):
    try:
      leads = model_data.leadsV3
    except Exception:
      return None

    best_candidate = None
    for i in range(3):
      try:
        lead = leads[i]
        prob = float(lead.prob)
        x = float(lead.x[0])
        y = float(lead.y[0])
        v = float(lead.v[0])
      except Exception:
        continue

      if (
        prob < RADAR_DEPART_CONFLICT_MIN_MODEL_PROB or
        x <= 0.0 or
        x > RADAR_DEPART_CONFLICT_MAX_MODEL_DISTANCE or
        abs(y) > RADAR_DEPART_CONFLICT_MAX_MODEL_LATERAL or
        max(v, 0.0) > RADAR_DEPART_CONFLICT_MAX_MODEL_LEAD_SPEED
      ):
        continue

      if best_candidate is None or x < best_candidate[0]:
        best_candidate = (x, y, v, prob)

    return best_candidate

  def has_offcenter_radar_depart_conflict(self, sm):
    if float(getattr(sm["carState"], "vEgo", 0.0)) > RADAR_DEPART_CONFLICT_MAX_EGO_SPEED:
      return False

    centered_model_lead = self.get_centered_model_lead(sm["modelV2"])
    if centered_model_lead is None:
      return False

    centered_model_dist = float(centered_model_lead[0])
    for lead in (self.lead_one, self.lead_two):
      if not lead.status or not bool(getattr(lead, "radar", False)):
        continue

      lead_dist = float(getattr(lead, "dRel", 0.0))
      if lead_dist <= 0.0 or lead_dist > RADAR_DEPART_CONFLICT_MAX_RADAR_DISTANCE:
        continue
      if abs(float(getattr(lead, "yRel", 0.0))) < RADAR_DEPART_CONFLICT_MIN_RADAR_LATERAL:
        continue
      if abs(lead_dist - centered_model_dist) > RADAR_DEPART_CONFLICT_MAX_DISTANCE_MISMATCH:
        continue

      return True

    return False

  def get_lead_depart_accel_floor(self, lead, v_ego, model_desired_accel):
    if lead is None or not lead.status:
      return None

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and lead_prob < LEAD_DEPART_ACCEL_HOLD_MIN_MODEL_PROB:
      return None

    lead_speed = max(float(lead.vLead), 0.0)
    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    lead_delta = lead_speed - float(v_ego)
    confident_depart = self.is_confident_lead_depart(lead, v_ego)
    min_lead_speed = LEAD_DEPART_CONFIDENT_MIN_LEAD_SPEED if confident_depart else LEAD_DEPART_ACCEL_HOLD_MIN_LEAD_SPEED
    min_lead_delta = LEAD_DEPART_CONFIDENT_MIN_LEAD_DELTA if confident_depart else LEAD_DEPART_ACCEL_HOLD_MIN_LEAD_DELTA
    min_gap = LEAD_DEPART_CONFIDENT_MIN_GAP if confident_depart else LEAD_DEPART_ACCEL_HOLD_MIN_GAP
    min_model_accel = 0.0 if confident_depart else LEAD_DEPART_ACCEL_HOLD_MIN_MODEL_ACCEL
    if (
      float(v_ego) > LEAD_DEPART_ACCEL_HOLD_MAX_EGO_SPEED or
      lead_speed < min_lead_speed or
      lead_delta < min_lead_delta or
      float(lead.dRel) < min_gap or
      lead_brake > LEAD_DEPART_ACCEL_HOLD_MAX_LEAD_BRAKE or
      float(model_desired_accel) < min_model_accel
    ):
      return None

    gap_factor = float(np.clip((float(lead.dRel) - LEAD_DEPART_ACCEL_HOLD_MIN_GAP) /
                               max(LEAD_DEPART_ACCEL_HOLD_FULL_GAP - LEAD_DEPART_ACCEL_HOLD_MIN_GAP, 0.1), 0.0, 1.0))
    lead_factor = float(np.clip((lead_speed - LEAD_DEPART_ACCEL_HOLD_MIN_LEAD_SPEED) /
                                max(LEAD_DEPART_ACCEL_HOLD_FULL_LEAD_SPEED - LEAD_DEPART_ACCEL_HOLD_MIN_LEAD_SPEED, 0.1), 0.0, 1.0))
    accel_cap = LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL + (LEAD_DEPART_ACCEL_HOLD_MAX_ACCEL - LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL) * np.clip(
      0.55 * lead_factor + 0.45 * gap_factor, 0.0, 1.0)
    return min(accel_cap, max(float(model_desired_accel), LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL))

  def get_lead_catchup_accel_cap(self, lead, v_ego, t_follow):
    if lead is None or not lead.status:
      return None

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    low_speed_follow_window = (
      not lead_radar and
      v_ego <= LOW_SPEED_FOLLOW_ACCEL_CAP_MAX_SPEED and
      lead_prob >= LOW_SPEED_FOLLOW_ACCEL_CAP_MIN_MODEL_PROB and
      lead_brake <= LOW_SPEED_FOLLOW_ACCEL_CAP_MAX_LEAD_BRAKE
    )
    if v_ego < LEAD_CATCHUP_ACCEL_MIN_EGO and not low_speed_follow_window:
      return None

    lead_delta = float(lead.vLead) - float(v_ego)
    min_lead_delta = LOW_SPEED_FOLLOW_ACCEL_CAP_MIN_LEAD_DELTA if low_speed_follow_window else LEAD_CATCHUP_ACCEL_MIN_LEAD_DELTA
    if lead_delta < min_lead_delta:
      return None

    desired_gap = float(desired_follow_distance(v_ego, lead.vLead, t_follow))
    if low_speed_follow_window:
      gap_buffer = max(LOW_SPEED_FOLLOW_ACCEL_CAP_MAX_GAP_BUFFER_MIN,
                       LOW_SPEED_FOLLOW_ACCEL_CAP_MAX_GAP_BUFFER_GAIN * float(v_ego))
    else:
      gap_buffer = max(LEAD_CATCHUP_ACCEL_MAX_GAP_BUFFER_MIN,
                       LEAD_CATCHUP_ACCEL_MAX_GAP_BUFFER_GAIN * float(v_ego))
    gap_error = float(lead.dRel) - desired_gap
    if gap_error > gap_buffer:
      return None

    # If the lead is already pace-matched or pulling away, keep any catch-up
    # accel very small while we're near the follow target so we don't surge into
    # the lead and immediately ask for brake again.
    if low_speed_follow_window:
      edge_cap = float(np.interp(lead_delta, [min_lead_delta, 0.0, 1.0, 2.0], [0.20, 0.24, 0.38, 0.55]))
      near_cap = min(edge_cap, 0.16)
    else:
      edge_cap = float(np.interp(lead_delta, [-0.5, 0.0, 1.0], [0.16, 0.08, 0.02]))
      near_cap = min(edge_cap, 0.03)
    gap_factor = float(np.clip(max(gap_error, 0.0) / max(gap_buffer, 0.1), 0.0, 1.0))
    return float(np.interp(gap_factor, [0.0, 1.0], [near_cap, edge_cap]))

  def get_low_speed_follow_transition_brake_cap(self, lead, v_ego, t_follow, prev_output_a_target, output_a_target):
    if lead is None or not lead.status:
      return None
    if bool(getattr(lead, "radar", False)):
      return None
    if not (LOW_SPEED_FOLLOW_TRANSITION_MIN_SPEED <= float(v_ego) <= LOW_SPEED_FOLLOW_TRANSITION_MAX_SPEED):
      return None
    if prev_output_a_target <= LOW_SPEED_FOLLOW_TRANSITION_PREV_ACCEL_MIN:
      return None
    if output_a_target >= LOW_SPEED_FOLLOW_TRANSITION_TARGET_BRAKE_MIN:
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < LOW_SPEED_FOLLOW_TRANSITION_MIN_MODEL_PROB:
      return None

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > LOW_SPEED_FOLLOW_TRANSITION_MAX_LEAD_BRAKE:
      return None

    closing_speed = max(0.0, float(v_ego) - float(lead.vLead))
    if closing_speed > LOW_SPEED_FOLLOW_TRANSITION_MAX_CLOSING_SPEED:
      return None

    desired_gap = float(desired_follow_distance(v_ego, lead.vLead, t_follow))
    if float(lead.dRel) < desired_gap + LOW_SPEED_FOLLOW_TRANSITION_MIN_GAP_MARGIN:
      return None

    cap_decel = float(np.interp(
      closing_speed,
      [0.0, LOW_SPEED_FOLLOW_TRANSITION_MAX_CLOSING_SPEED],
      [LOW_SPEED_FOLLOW_TRANSITION_MIN_BRAKE, LOW_SPEED_FOLLOW_TRANSITION_MAX_BRAKE],
    ))
    return -cap_decel

  def get_cruise_tracking_lead_accel_cap(self, lead, v_ego, t_follow, current_source, tracking_lead_active):
    if lead is None or not lead.status or current_source != "cruise":
      return None
    if not (CRUISE_TRACKED_LEAD_ACCEL_CAP_MIN_SPEED <= float(v_ego) <= CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_SPEED):
      return None

    lead_prob = float(getattr(lead, "modelProb", 1.0 if bool(getattr(lead, "radar", False)) else 0.0))
    if not bool(getattr(lead, "radar", False)) and lead_prob < CRUISE_TRACKED_LEAD_ACCEL_CAP_MIN_MODEL_PROB:
      return None

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_LEAD_BRAKE:
      return None

    if abs(float(getattr(lead, "yRel", 0.0))) > CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_LATERAL_OFFSET:
      return None

    lead_delta = float(lead.vLead) - float(v_ego)
    if lead_delta > CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_PULLAWAY_SPEED:
      return None

    closing_speed = max(float(v_ego) - float(lead.vLead), 0.0)
    raw_close_lead = self.raw_close_lead_needs_control(lead, v_ego)
    unresolved_slow_lead = (
      closing_speed >= CRUISE_TRACKED_LEAD_ACCEL_CAP_UNRESOLVED_MIN_CLOSING_SPEED and
      lead_delta <= CRUISE_TRACKED_LEAD_ACCEL_CAP_UNRESOLVED_MAX_LEAD_DELTA
    )
    if not tracking_lead_active and not raw_close_lead and not unresolved_slow_lead:
      return None

    desired_gap = float(desired_follow_distance(v_ego, lead.vLead, t_follow))
    gap_error = float(lead.dRel) - desired_gap
    gap_buffer = max(CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_GAP_BUFFER_MIN,
                     CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_GAP_BUFFER_GAIN * float(v_ego))
    if gap_error > gap_buffer:
      return None

    base_cap = float(np.interp(
      lead_delta,
      [-1.5, -0.5, 0.0, 0.5, CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_PULLAWAY_SPEED],
      [0.0, 0.04, 0.08, 0.12, 0.16],
    ))

    if raw_close_lead:
      base_cap = min(base_cap, float(np.interp(closing_speed, [0.5, 1.5, 3.5], [0.10, 0.05, 0.0])))
    else:
      base_cap = min(base_cap, float(np.interp(closing_speed, [0.0, 1.0, 2.0], [0.18, 0.12, 0.06])))

    if gap_error <= 0.0:
      return max(0.0, base_cap)

    gap_factor = float(np.clip(gap_error / max(gap_buffer, 0.1), 0.0, 1.0))
    cap = min(CRUISE_TRACKED_LEAD_ACCEL_CAP_MAX_ACCEL, base_cap + 0.06 * gap_factor)
    return max(0.0, cap)

  def get_cruise_tracking_lead_accel_transition_target(self, lead, v_ego, t_follow,
                                                       prev_output_a_target, output_a_target,
                                                       current_source):
    if lead is None or not lead.status or current_source != "cruise":
      return None
    if not (CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MIN_SPEED <= float(v_ego) <= CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_SPEED):
      return None

    target_delta = float(output_a_target) - float(prev_output_a_target)
    if target_delta < CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MIN_DELTA_A:
      return None

    lead_prob = float(getattr(lead, "modelProb", 1.0 if bool(getattr(lead, "radar", False)) else 0.0))
    if not bool(getattr(lead, "radar", False)) and lead_prob < CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MIN_MODEL_PROB:
      return None

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_LEAD_BRAKE:
      return None

    if abs(float(getattr(lead, "yRel", 0.0))) > CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_LATERAL_OFFSET:
      return None

    lead_delta = float(lead.vLead) - float(v_ego)
    if lead_delta > CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_PULLAWAY_SPEED:
      return None

    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
    headway_margin = actual_headway - float(t_follow)
    if headway_margin > CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_HEADWAY_ABOVE_TARGET:
      return None

    positive_step = float(np.interp(
      lead_delta,
      [-1.0, 0.0, 1.0, CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_PULLAWAY_SPEED],
      [CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MIN_STEP,
       0.08,
       0.12,
       CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_STEP],
    ))
    if headway_margin > 0.0:
      headway_factor = float(np.clip(
        headway_margin / max(CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_HEADWAY_ABOVE_TARGET, 1e-3),
        0.0,
        1.0,
      ))
      positive_step = float(np.interp(
        headway_factor,
        [0.0, 1.0],
        [positive_step, CRUISE_TRACKED_LEAD_ACCEL_TRANSITION_MAX_STEP],
      ))

    upper = float(prev_output_a_target) + positive_step
    smoothed_target = float(min(output_a_target, upper))
    return smoothed_target if smoothed_target < float(output_a_target) - 1e-6 else None

  def lead_is_matched_follow_window(self, lead, v_ego, base_t_follow):
    if lead is None or not lead.status or v_ego < STEADY_FOLLOW_SMOOTHING_MIN_SPEED:
      return False

    relative_speed = float(v_ego) - float(lead.vLead)
    if not (STEADY_FOLLOW_BRAKE_CAP_MIN_REL_SPEED <= relative_speed <= STEADY_FOLLOW_SMOOTHING_MAX_CLOSING_SPEED):
      return False

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > STEADY_FOLLOW_SMOOTHING_MAX_LEAD_BRAKE:
      return False

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and not is_radarless_matched_follow_window(
      v_ego,
      lead.dRel,
      lead.vLead,
      base_t_follow,
      radar=lead_radar,
      lead_brake=lead_brake,
      lead_prob=lead_prob,
    ):
      return False

    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
    if actual_headway < max(STEADY_FOLLOW_BRAKE_CAP_MIN_HEADWAY, float(base_t_follow) - STEADY_FOLLOW_SMOOTHING_HEADWAY_BELOW_TARGET):
      return False
    if actual_headway > float(base_t_follow) + STEADY_FOLLOW_BRAKE_CAP_MAX_HEADWAY_ABOVE_TARGET:
      return False
    return True

  def get_matched_follow_control_lead(self, v_ego, t_follow):
    if self.mpc.source == 'lead1' and self.lead_is_matched_follow_window(self.lead_two, v_ego, t_follow):
      return self.lead_two
    if self.lead_is_matched_follow_window(self.lead_one, v_ego, t_follow):
      return self.lead_one
    if self.lead_is_matched_follow_window(self.lead_two, v_ego, t_follow):
      return self.lead_two
    return None

  def get_follow_control_lead(self, lead_control_active, v_ego, t_follow, *, allow_optional_far_lead_logic=True):
    if allow_optional_far_lead_logic:
      matched_follow_lead = self.get_matched_follow_control_lead(v_ego, t_follow)
      if matched_follow_lead is not None:
        return matched_follow_lead

    if not lead_control_active:
      return None

    if self.lead_one.status:
      return self.lead_one
    if self.lead_two.status:
      return self.lead_two
    return None

  def lead_is_spacious_brake_cap_window(self, lead, v_ego, base_t_follow):
    if lead is None or not lead.status or v_ego < STEADY_FOLLOW_SMOOTHING_MIN_SPEED:
      return False

    relative_speed = float(v_ego) - float(lead.vLead)
    if not (STEADY_FOLLOW_BRAKE_CAP_MIN_REL_SPEED <= relative_speed <= STEADY_FOLLOW_BRAKE_CAP_MAX_CLOSING_SPEED):
      return False

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > STEADY_FOLLOW_BRAKE_CAP_SPACIOUS_MAX_LEAD_BRAKE:
      return False

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and lead_prob < STEADY_FOLLOW_SMOOTHING_MIN_MODEL_PROB:
      return False

    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
    if actual_headway < max(float(base_t_follow) + STEADY_FOLLOW_BRAKE_CAP_SPACIOUS_HEADWAY_MARGIN,
                            STEADY_FOLLOW_BRAKE_CAP_SPACIOUS_MIN_HEADWAY):
      return False
    if actual_headway > float(base_t_follow) + STEADY_FOLLOW_BRAKE_CAP_MAX_HEADWAY_ABOVE_TARGET:
      return False
    return True

  def get_matched_follow_brake_cap(self, lead, v_ego, base_t_follow):
    if not (
      self.lead_is_matched_follow_window(lead, v_ego, base_t_follow) or
      self.lead_is_spacious_brake_cap_window(lead, v_ego, base_t_follow)
    ):
      return None

    relative_speed = float(v_ego) - float(lead.vLead)
    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
    cap_decel = float(np.interp(
      relative_speed,
      [STEADY_FOLLOW_BRAKE_CAP_MIN_REL_SPEED, 0.0, STEADY_FOLLOW_BRAKE_CAP_MAX_CLOSING_SPEED],
      [STEADY_FOLLOW_BRAKE_CAP_OPENING_DECEL,
       STEADY_FOLLOW_BRAKE_CAP_ZERO_REL_SPEED_DECEL,
       STEADY_FOLLOW_BRAKE_CAP_MAX_DECEL],
    ))
    headway_deficit = float(np.clip((float(base_t_follow) - actual_headway) / STEADY_FOLLOW_SMOOTHING_HEADWAY_BELOW_TARGET, 0.0, 1.0))
    cap_decel = min(STEADY_FOLLOW_BRAKE_CAP_MAX_DECEL, cap_decel + 0.05 * headway_deficit)
    return -cap_decel

  def get_far_lead_brake_cap(self, lead, v_ego, base_t_follow):
    if lead is None or not lead.status or v_ego < STEADY_FOLLOW_SMOOTHING_MIN_SPEED:
      return None

    if bool(getattr(lead, "radar", False)):
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < FAR_LEAD_COMFORT_BRAKE_CAP_MIN_MODEL_PROB:
      return None

    relative_speed = float(v_ego) - float(lead.vLead)
    if not (FAR_LEAD_COMFORT_BRAKE_CAP_MIN_CLOSING_SPEED <= relative_speed <= FAR_LEAD_COMFORT_BRAKE_CAP_MAX_CLOSING_SPEED):
      return None

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > FAR_LEAD_COMFORT_BRAKE_CAP_MAX_LEAD_BRAKE:
      return None

    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
    headway_margin = actual_headway - float(base_t_follow)
    if float(lead.dRel) < FAR_LEAD_COMFORT_BRAKE_CAP_MIN_DISTANCE or headway_margin < FAR_LEAD_COMFORT_BRAKE_CAP_MIN_HEADWAY_MARGIN:
      return None

    ttc = float(lead.dRel) / max(relative_speed, 1e-3)
    if ttc < FAR_LEAD_COMFORT_BRAKE_CAP_MIN_TTC:
      return None

    cap_decel = float(np.interp(
      relative_speed,
      [FAR_LEAD_COMFORT_BRAKE_CAP_MIN_CLOSING_SPEED, FAR_LEAD_COMFORT_BRAKE_CAP_MAX_CLOSING_SPEED],
      [FAR_LEAD_COMFORT_BRAKE_CAP_MIN_DECEL, FAR_LEAD_COMFORT_BRAKE_CAP_MAX_DECEL],
    ))
    relax_decel = float(np.interp(
      headway_margin,
      [FAR_LEAD_COMFORT_BRAKE_CAP_MIN_HEADWAY_MARGIN, FAR_LEAD_COMFORT_BRAKE_CAP_FULL_HEADWAY_MARGIN],
      [0.0, FAR_LEAD_COMFORT_BRAKE_CAP_FULL_RELAX_DECEL],
    ))
    return -max(0.0, cap_decel - relax_decel)

  def get_matched_follow_transition_target(self, lead, v_ego, base_t_follow, prev_output_a_target, output_a_target,
                                           current_source, tracking_lead_active):
    if lead is None or not lead.status:
      return None
    low_speed_extension_active = (
      bool(tracking_lead_active) and
      current_source == "cruise" and
      LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_SPEED <= float(v_ego) < LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_SPEED
    )
    if float(v_ego) < MATCHED_FOLLOW_TRANSITION_MIN_SPEED and not low_speed_extension_active:
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    min_model_prob = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_MODEL_PROB if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_MIN_MODEL_PROB
    if lead_prob < min_model_prob:
      return None

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    max_lead_brake = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_LEAD_BRAKE if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_MAX_LEAD_BRAKE
    if lead_brake > max_lead_brake:
      return None

    relative_speed = float(v_ego) - float(lead.vLead)
    if not (STEADY_FOLLOW_BRAKE_CAP_MIN_REL_SPEED <= relative_speed <= STEADY_FOLLOW_SMOOTHING_MAX_CLOSING_SPEED):
      return None

    closing_speed = max(0.0, relative_speed)
    max_closing_speed = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_CLOSING_SPEED if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_MAX_CLOSING_SPEED
    if closing_speed > max_closing_speed:
      return None

    ttc = float(lead.dRel) / max(closing_speed, 0.1) if closing_speed > 0.1 else float("inf")
    min_ttc = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_TTC if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_MIN_TTC
    if ttc < min_ttc:
      return None

    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
    headway_margin = actual_headway - float(base_t_follow)
    min_headway_margin = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_HEADWAY_MARGIN if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_MIN_HEADWAY_MARGIN
    full_headway_margin = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_FULL_HEADWAY_MARGIN if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_FULL_HEADWAY_MARGIN
    if headway_margin < min_headway_margin:
      return None
    if actual_headway > float(base_t_follow) + STEADY_FOLLOW_BRAKE_CAP_MAX_HEADWAY_ABOVE_TARGET:
      return None

    target_delta = float(output_a_target) - float(prev_output_a_target)
    if low_speed_extension_active:
      if float(prev_output_a_target) < LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_TARGET:
        return None
      if float(output_a_target) < LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_TARGET:
        return None
      if abs(target_delta) < LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_DELTA_A:
        return None
    elif abs(target_delta) < 1e-3:
      return None

    headway_factor = float(np.clip(
      (headway_margin - min_headway_margin) /
      max(full_headway_margin - min_headway_margin, 1e-3),
      0.0,
      1.0,
    ))

    min_positive_step = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_POSITIVE_STEP if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_MIN_POSITIVE_STEP
    max_positive_step = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_POSITIVE_STEP if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_MAX_POSITIVE_STEP
    positive_step = float(np.interp(
      max(float(lead.vLead) - float(v_ego), 0.0),
      [0.0, 1.0],
      [min_positive_step, max_positive_step],
    ))
    min_negative_step = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MIN_NEGATIVE_STEP if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_MIN_NEGATIVE_STEP
    max_negative_step = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_MAX_NEGATIVE_STEP if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_MAX_NEGATIVE_STEP
    negative_step = float(np.interp(
      closing_speed,
      [0.0, max_closing_speed],
      [min_negative_step, max_negative_step],
    ))

    # The more space we still have, the less abrupt the comfort path should be.
    positive_step = float(np.interp(headway_factor, [0.0, 1.0], [positive_step, min_positive_step]))
    negative_step = float(np.interp(headway_factor, [0.0, 1.0], [negative_step, min_negative_step]))

    if float(prev_output_a_target) * float(output_a_target) < 0.0:
      sign_cross_step = LOW_SPEED_MATCHED_FOLLOW_TRANSITION_SIGN_CROSS_STEP if low_speed_extension_active else MATCHED_FOLLOW_TRANSITION_SIGN_CROSS_STEP
      positive_step = min(positive_step, sign_cross_step)
      negative_step = min(negative_step, sign_cross_step)

    lower = float(prev_output_a_target) - negative_step
    upper = float(prev_output_a_target) + positive_step
    smoothed_target = float(np.clip(output_a_target, lower, upper))
    return smoothed_target if abs(smoothed_target - float(output_a_target)) > 1e-6 else None

  def get_near_duplicate_lead_transition_target(self, lead, v_ego, base_t_follow,
                                                prev_output_a_target, output_a_target,
                                                current_source, tracking_lead_active):
    if lead is None or not lead.status:
      return None
    if current_source not in ("lead0", "lead1") and not tracking_lead_active:
      return None
    if not (self.lead_one.status and self.lead_two.status):
      return None
    if not self.mpc.leads_are_near_duplicates(self.lead_one, self.lead_two, v_ego):
      return None
    if float(v_ego) < NEAR_DUPLICATE_LEAD_TRANSITION_MIN_SPEED:
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if bool(getattr(lead, "radar", False)) or lead_prob < NEAR_DUPLICATE_LEAD_TRANSITION_MIN_MODEL_PROB:
      return None

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > NEAR_DUPLICATE_LEAD_TRANSITION_MAX_LEAD_BRAKE:
      return None

    relative_speed = float(v_ego) - float(lead.vLead)
    closing_speed = max(0.0, relative_speed)
    if closing_speed > NEAR_DUPLICATE_LEAD_TRANSITION_MAX_CLOSING_SPEED:
      return None

    ttc = float(lead.dRel) / max(closing_speed, 0.1) if closing_speed > 0.1 else float("inf")
    if ttc < NEAR_DUPLICATE_LEAD_TRANSITION_MIN_TTC:
      return None

    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
    if actual_headway < max(0.0, float(base_t_follow) - NEAR_DUPLICATE_LEAD_TRANSITION_MIN_HEADWAY_BELOW_TARGET):
      return None
    if actual_headway > float(base_t_follow) + NEAR_DUPLICATE_LEAD_TRANSITION_MAX_HEADWAY_ABOVE_TARGET:
      return None

    target_delta = float(output_a_target) - float(prev_output_a_target)
    if abs(target_delta) < NEAR_DUPLICATE_LEAD_TRANSITION_MIN_DELTA_A:
      return None

    positive_step = NEAR_DUPLICATE_LEAD_TRANSITION_POSITIVE_STEP
    negative_step = NEAR_DUPLICATE_LEAD_TRANSITION_NEGATIVE_STEP
    if float(prev_output_a_target) * float(output_a_target) < 0.0:
      positive_step = min(positive_step, NEAR_DUPLICATE_LEAD_TRANSITION_SIGN_CROSS_STEP)
      negative_step = min(negative_step, NEAR_DUPLICATE_LEAD_TRANSITION_SIGN_CROSS_STEP)

    lower = float(prev_output_a_target) - negative_step
    upper = float(prev_output_a_target) + positive_step
    smoothed_target = float(np.clip(output_a_target, lower, upper))
    return smoothed_target if abs(smoothed_target - float(output_a_target)) > 1e-6 else None

  def get_tracked_vision_model_brake_floor(self, lead, v_ego, accel_min, t_follow, model_desired):
    if lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None
    if float(v_ego) < TRACKED_VISION_MODEL_FLOOR_MIN_SPEED:
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < TRACKED_VISION_MODEL_FLOOR_MIN_MODEL_PROB:
      return None

    model_brake = max(0.0, -float(model_desired))
    if model_brake < TRACKED_VISION_MODEL_FLOOR_MIN_MODEL_DECEL:
      return None

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    reaction_t = max(self.CP.longitudinalActuatorDelay, self.dt)
    projected_closing_speed = max(0.0, float(v_ego) - float(lead.vLead)) + lead_brake * reaction_t
    if projected_closing_speed < TRACKED_VISION_MODEL_FLOOR_MIN_CLOSING_SPEED:
      return None

    desired_gap = float(desired_follow_distance(v_ego, lead.vLead, t_follow))
    gap_margin = float(lead.dRel) - desired_gap
    max_gap_margin = max(TRACKED_VISION_MODEL_FLOOR_MAX_GAP_BUFFER_MIN,
                         TRACKED_VISION_MODEL_FLOOR_MAX_GAP_BUFFER_GAIN * float(v_ego))
    if gap_margin < TRACKED_VISION_MODEL_FLOOR_MIN_GAP_MARGIN or gap_margin > max_gap_margin:
      return None

    projected_ttc = float(lead.dRel) / max(projected_closing_speed, 0.1)
    if projected_ttc > TRACKED_VISION_MODEL_FLOOR_MAX_TTC:
      return None

    floor_decel = float(np.interp(
      model_brake,
      [TRACKED_VISION_MODEL_FLOOR_MIN_MODEL_DECEL, 1.6],
      [TRACKED_VISION_MODEL_FLOOR_MIN_DECEL, TRACKED_VISION_MODEL_FLOOR_MAX_DECEL],
    ))
    floor_decel += float(np.interp(lead_brake, [0.0, 0.8], [0.0, TRACKED_VISION_MODEL_FLOOR_LEAD_BRAKE_MAX]))
    return max(accel_min, -min(TRACKED_VISION_MODEL_FLOOR_MAX_DECEL, floor_decel))

  def get_tracked_vision_model_brake_cap(self, lead, v_ego, t_follow, model_desired):
    if lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None
    if not (TRACKED_VISION_MODEL_CAP_MIN_SPEED <= float(v_ego) <= TRACKED_VISION_MODEL_CAP_MAX_SPEED):
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < TRACKED_VISION_MODEL_CAP_MIN_MODEL_PROB:
      return None

    model_brake = max(0.0, -float(model_desired))
    if model_brake > TRACKED_VISION_MODEL_CAP_MAX_MODEL_DECEL:
      return None

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > TRACKED_VISION_MODEL_CAP_MAX_LEAD_BRAKE:
      return None

    reaction_t = max(self.CP.longitudinalActuatorDelay, self.dt)
    projected_closing_speed = max(0.0, float(v_ego) - float(lead.vLead)) + lead_brake * reaction_t
    if not (TRACKED_VISION_MODEL_CAP_MIN_CLOSING_SPEED <= projected_closing_speed <= TRACKED_VISION_MODEL_CAP_MAX_CLOSING_SPEED):
      return None

    desired_gap = float(desired_follow_distance(v_ego, lead.vLead, t_follow))
    gap_margin = float(lead.dRel) - desired_gap
    max_gap_margin = max(TRACKED_VISION_MODEL_CAP_MAX_GAP_BUFFER_MIN,
                         TRACKED_VISION_MODEL_CAP_MAX_GAP_BUFFER_GAIN * float(v_ego))
    if gap_margin < TRACKED_VISION_MODEL_CAP_MIN_GAP_MARGIN or gap_margin > max_gap_margin:
      return None

    projected_ttc = float(lead.dRel) / max(projected_closing_speed, 0.1)
    if projected_ttc < TRACKED_VISION_MODEL_CAP_MIN_TTC:
      return None

    cap_decel = float(np.interp(
      model_brake,
      [0.0, TRACKED_VISION_MODEL_CAP_MAX_MODEL_DECEL],
      [TRACKED_VISION_MODEL_CAP_MIN_DECEL, TRACKED_VISION_MODEL_CAP_MAX_DECEL],
    ))
    cap_decel += float(np.interp(
      projected_closing_speed,
      [TRACKED_VISION_MODEL_CAP_MIN_CLOSING_SPEED, TRACKED_VISION_MODEL_CAP_MAX_CLOSING_SPEED],
      [0.0, 0.08],
    ))
    return -min(TRACKED_VISION_MODEL_CAP_MAX_DECEL, cap_decel)

  @staticmethod
  def raw_close_lead_needs_control(lead, v_ego):
    if lead is None or not lead.status:
      return False

    closing_speed = float(v_ego - lead.vLead)
    lead_braking = float(lead.aLeadK) < -0.5
    if closing_speed <= RAW_LEAD_SAFETY_MIN_CLOSING_SPEED and not lead_braking:
      return False

    d_rel = max(float(lead.dRel), 0.0)
    dynamic_distance = max(RAW_LEAD_SAFETY_DISTANCE, 3.0 * float(v_ego))
    ttc = d_rel / max(closing_speed, 0.1) if closing_speed > 0.1 else float("inf")
    return d_rel < dynamic_distance and (ttc < RAW_LEAD_SAFETY_TTC or lead_braking)

  def update(self, sm, starpilot_toggles):
    if self.is_preap:
      self._preap_param_frame += 1
      if self._preap_params is not None and (self._preap_param_frame % 20) == 0:
        self.nap_adaptive_accel = self._preap_params.get_bool("NAPAdaptiveAccel")

    self.generation = getattr(starpilot_toggles, "model_version", None)
    self.mode = 'blended' if sm['selfdriveState'].experimentalMode else 'acc'
    self.mpc.mode = 'acc'
    if not self.mlsim:
      self.mpc.mode = self.mode

    if len(sm['carControl'].orientationNED) == 3:
      accel_coast = get_coast_accel(sm['carControl'].orientationNED[1])
    else:
      accel_coast = ACCEL_MAX

    v_ego = get_planner_v_ego(self.CP, sm['carState'])
    scene_v_ego = float(sm['carState'].vEgo)
    v_cruise = sm['starpilotPlan'].vCruise
    if not np.isfinite(v_cruise):
      cloudlog.error(f"Longitudinal planner received non-finite vCruise={v_cruise}, falling back to v_ego={v_ego:.2f}")
      v_cruise = max(v_ego, 0.0)
    v_cruise_initialized = sm['carState'].vCruise != V_CRUISE_UNSET

    long_control_off = sm['controlsState'].longControlState == LongCtrlState.off
    force_slow_decel = sm['controlsState'].forceDecel

    # Reset current state when not engaged, or user is controlling the speed
    reset_state = long_control_off if self.CP.openpilotLongitudinalControl else not sm['selfdriveState'].enabled
    # PCM cruise speed may be updated a few cycles later, check if initialized
    reset_state = reset_state or not v_cruise_initialized

    # No change cost when user is controlling the speed, or when standstill
    prev_accel_constraint = not (reset_state or sm['carState'].standstill)

    if self.mpc.mode == 'acc':
      accel_limits = [sm['starpilotPlan'].minAcceleration, sm['starpilotPlan'].maxAcceleration]
      steer_angle_without_offset = sm['carState'].steeringAngleDeg - sm['liveParameters'].angleOffsetDeg
      accel_limits_turns = limit_accel_in_turns(v_ego, steer_angle_without_offset, accel_limits, self.CP)
      accel_limits_turns[0] = max(get_vehicle_min_accel(self.CP, v_ego), accel_limits_turns[0])
    else:
      accel_limits = [ACCEL_MIN, ACCEL_MAX]
      accel_limits_turns = [ACCEL_MIN, ACCEL_MAX]

    if reset_state:
      self.v_desired_filter.x = v_ego
      # Clip aEgo to cruise limits to prevent large accelerations when becoming active
      self.a_desired = np.clip(sm['carState'].aEgo, accel_limits[0], accel_limits[1])
      self.model_allow_throttle = True

    # Prevent divergence, smooth in current v_ego
    self.v_desired_filter.x = max(0.0, self.v_desired_filter.update(v_ego))
    # Compute model v_ego error
    self.v_model_error = self.get_model_speed_error(sm['modelV2'], v_ego)
    x, v, a, j, throttle_prob = self.parse_model(sm['modelV2'], self.v_model_error, v_ego, starpilot_toggles)
    # Don't clip at low speeds since throttle_prob doesn't account for creep. Use
    # hysteresis here because raw gasPressProb noise can chatter the throttle gate.
    if v_ego <= MIN_ALLOW_THROTTLE_SPEED:
      self.model_allow_throttle = True
    elif self.model_allow_throttle:
      self.model_allow_throttle = throttle_prob > ALLOW_THROTTLE_DISABLE_THRESHOLD
    else:
      self.model_allow_throttle = throttle_prob > ALLOW_THROTTLE_ENABLE_THRESHOLD
    self.allow_throttle = self.model_allow_throttle and not sm['starpilotPlan'].disableThrottle

    if not self.allow_throttle:
      clipped_accel_coast = max(accel_coast, accel_limits_turns[0])
      # Hold the output cap to the physical coasting limit until throttle is
      # allowed again. Relaxing back toward positive accel while the gate is
      # still closed can stall downhill coastdown well above the target speed.
      accel_limits_turns[1] = min(accel_limits_turns[1], clipped_accel_coast)
    no_throttle_output_max = accel_limits_turns[1]

    if force_slow_decel:
      v_cruise = 0.0
    # clip limits, cannot init MPC outside of bounds
    accel_limits_turns[0] = min(accel_limits_turns[0], self.a_desired + 0.05)
    accel_limits_turns[1] = max(accel_limits_turns[1], self.a_desired - 0.05)

    tracking_lead = bool(sm['starpilotPlan'].trackingLead)
    self.lead_one = sm['radarState'].leadOne
    self.lead_two = sm['radarState'].leadTwo
    raw_close_lead_control = any(self.raw_close_lead_needs_control(lead, scene_v_ego) for lead in (self.lead_one, self.lead_two))
    # StarPilot trackingLead is debounce/model-length based. Keep a raw close-lead
    # safety path so ACC/chill does not ignore a visible lead during that debounce.
    lead_control_active = tracking_lead or raw_close_lead_control
    lead_one_active = bool(self.lead_one.status and lead_control_active)
    effective_t_follow = self.get_dynamic_t_follow(sm['starpilotPlan'].tFollow, self.lead_one if lead_one_active else None, v_ego)

    if self.is_preap and self.nap_adaptive_accel and lead_one_active:
      follow_limit = get_preap_follow_limit(v_ego)
      if follow_limit is not None:
        safe_dist = get_safe_obstacle_distance(v_ego, effective_t_follow)
        lead_dist_ratio = float(self.lead_one.dRel) / max(safe_dist, 1.0)
        cap_strength = float(np.clip(1.0 - (lead_dist_ratio - 1.2) / 0.3, 0.0, 1.0))
        if cap_strength > 0.0:
          accel_limits_turns[1] = min(
            accel_limits_turns[1],
            accel_limits_turns[1] * (1.0 - cap_strength) + follow_limit * cap_strength,
          )

    lead_dist = self.lead_one.dRel if lead_one_active else 50.0

    # Smooth lead distance (EMA) to avoid chatter in thresholds
    alpha = max(0.02, min(0.15, 0.05 + 0.002 * v_ego))
    if self.lead_dist_f is None:
      self.lead_dist_f = float(lead_dist)
    else:
      self.lead_dist_f += alpha * (float(lead_dist) - self.lead_dist_f)

    # Lead stability estimation and recent-brake timer
    now_t = time.monotonic()
    # relative speed (ego - lead) positive when closing
    v_rel = (v_ego - self.lead_one.vLead) if lead_one_active else 0.0
    if self.prev_lead_dist is None:
      d_rel_dot = 0.0
    else:
      d_rel_dot = (lead_dist - self.prev_lead_dist) / max(self.dt, 1e-3)
    self.prev_lead_dist = lead_dist

    # Remember time of last non-trivial model brake risk
    if 'raw_brake_max' in locals() and raw_brake_max is not None and raw_brake_max > 0.02:
      self.last_big_brake_t = now_t

    # Stable lead heuristic (short window, cheap to compute)
    recently_braked = (now_t - self.last_big_brake_t) < 0.7
    self.stable_lead = (
      lead_one_active and
      abs(v_rel) < 0.5 and
      abs(d_rel_dot) < 0.5 and
      not recently_braked
    )

    # Calculate scene uncertainty from model desire prediction entropy and disengage predictions
    uncertainty = 0.0
    if hasattr(sm['modelV2'], 'meta'):
      # Desire prediction entropy (maneuver uncertainty), normalized to [0, 1]
      desire_entropy = 0.0
      if hasattr(sm['modelV2'].meta, 'desirePrediction'):
        desire_probs = sm['modelV2'].meta.desirePrediction
        if len(desire_probs) > 1:
          probs = np.asarray(desire_probs, dtype=float)
          total = float(np.sum(probs))
          if total > 1e-6:
            p = probs / total
            entropy = -np.sum(p * np.log(p + 1e-10))
            max_entropy = np.log(len(p))
            desire_entropy = float(entropy / max(max_entropy, 1e-6))  # normalized entropy in [0,1]
          else:
            desire_entropy = 0.0  # guard against all-zero vector

      # Disengage prediction risk (intervention likelihood)
      disengage_risk = 0.0
      raw_brake_max = -1.0
      lam = -1.0
      if hasattr(sm['modelV2'].meta, 'disengagePredictions'):
        # Use brake press probabilities as primary risk indicator
        brake_probs = sm['modelV2'].meta.disengagePredictions.brakePressProbs
        if len(brake_probs) > 0:
          # Exponentially decayed max over the full horizon
          probs = np.asarray(brake_probs, dtype=float)
          # Clip tiny brake blips so they don't inflate uncertainty
          if float(np.max(probs)) < 0.015:
            probs = probs * 0.5
          raw_brake_max = float(np.max(probs))
          # Time vector assuming model horizon step = DT_MDL
          t = np.arange(len(probs), dtype=float) * DT_MDL
          lam = 0.6  # decay rate per second (tunable: 0.5–0.9 typical)
          weights = np.exp(-lam * t)
          disengage_risk = float(np.max(probs * weights))

      # Combined uncertainty metric (range roughly 0..2), with dual-track filtering
      raw_uncertainty = desire_entropy + disengage_risk
      # Update filters
      self.uncert_slow.update(raw_uncertainty)
      self.uncert_fast.update(raw_uncertainty)
      # Use a more permissive track for accel decisions
      uncertainty = self.uncert_slow.x
    uncertainty_accel = min(self.uncert_slow.x, self.uncert_fast.x)

    # --- Slope-based panic bypass ---
    if self._uncert_last_t is None:
      uncert_slope = 0.0
    else:
      dt_u = max(1e-3, now_t - self._uncert_last_t)
      uncert_slope = (uncertainty - self._uncert_last) / dt_u
    self._uncert_last = uncertainty
    self._uncert_last_t = now_t

    panic_close_window = False
    closing_fast = False
    desired_gap = None
    closing_speed = 0.0
    if lead_one_active:
      desired_gap = float(desired_follow_distance(v_ego, self.lead_one.vLead, effective_t_follow))
      scene_desired_gap = float(desired_follow_distance(scene_v_ego, self.lead_one.vLead, effective_t_follow))
      close_gap_window = max(UNCERT_PANIC_MAX_GAP_BUFFER_MIN,
                             UNCERT_PANIC_MAX_GAP_BUFFER_GAIN * float(v_ego))
      panic_close_window = float(self.lead_one.dRel) <= scene_desired_gap + close_gap_window
      closing_speed = max(0.0, scene_v_ego - self.lead_one.vLead)
      closing_fast = closing_speed >= max(
        UNCERT_PANIC_MIN_CLOSING_SPEED,
        UNCERT_PANIC_MIN_CLOSING_SPEED_GAIN * float(scene_v_ego),
      )

    # Only bypass lead smoothing when we're closing meaningfully and already
    # near the follow window. Far or nearly pace-matched leads should stay on
    # the smoothed path so the planner doesn't flip-flop between accel and brake.
    panic_bypass = panic_close_window and closing_fast and (
      uncert_slope > UNCERT_SLOPE_TRIG or uncertainty >= UNCERT_MAG_TRIG
    )

    steady_follow_filter_floor = 0.0
    if lead_one_active and desired_gap is not None and not panic_bypass:
      lead_brake = max(0.0, -float(getattr(self.lead_one, "aLeadK", 0.0)))
      lead_radar = bool(getattr(self.lead_one, "radar", False))
      lead_prob = float(getattr(self.lead_one, "modelProb", 1.0 if lead_radar else 0.0))
      actual_headway = float(self.lead_one.dRel) / max(scene_v_ego, 1e-3)
      matched_follow_window = (
        is_radarless_matched_follow_window(
          scene_v_ego,
          self.lead_one.dRel,
          self.lead_one.vLead,
          effective_t_follow,
          radar=lead_radar,
          lead_brake=lead_brake,
          lead_prob=lead_prob,
        ) or (
          lead_radar and
          scene_v_ego >= STEADY_FOLLOW_SMOOTHING_MIN_SPEED and
          STEADY_FOLLOW_SMOOTHING_MIN_CLOSING_SPEED <= closing_speed <= STEADY_FOLLOW_SMOOTHING_MAX_CLOSING_SPEED and
          actual_headway >= max(STEADY_FOLLOW_SMOOTHING_MIN_HEADWAY,
                                effective_t_follow - STEADY_FOLLOW_SMOOTHING_HEADWAY_BELOW_TARGET) and
          actual_headway <= effective_t_follow + STEADY_FOLLOW_SMOOTHING_HEADWAY_ABOVE_TARGET and
          lead_brake <= STEADY_FOLLOW_SMOOTHING_MAX_LEAD_BRAKE
        )
      )
      if matched_follow_window:
        steady_follow_filter_floor = STEADY_FOLLOW_SMOOTHING_FILTER_FACTOR_FLOOR

    if panic_bypass:
      if now_t - self._panic_bypass_log_t > 5.0:
        self._panic_bypass_log_t = now_t
        try:
          cloudlog.warning(
            "LON_SLOPE close bypass: "
            f"slope={uncert_slope:.3f}/s uncertainty={uncertainty:.3f} "
            f"v_ego={v_ego:.2f} v_rel={(v_ego - self.lead_one.vLead) if lead_one_active else 0.0:.2f} "
            f"lead_dist={self.lead_dist_f if self.lead_dist_f is not None else -1:.2f}"
          )
        except Exception:
          pass

    personality = get_longitudinal_personality(sm)

    self.mpc.set_weights(sm['starpilotPlan'].accelerationJerk,
                         sm['starpilotPlan'].dangerJerk,
                         sm['starpilotPlan'].speedJerk,
                         prev_accel_constraint,
                         personality=personality,
                         v_ego=v_ego,
                         lead_dist=self.lead_dist_f if lead_one_active and self.lead_dist_f is not None else 50.0,
                         uncertainty=uncertainty,
                         panic_bypass=panic_bypass,
                         filter_time_factor_floor=steady_follow_filter_floor)
    self.mpc.set_accel_limits(accel_limits_turns[0], accel_limits_turns[1])
    self.mpc.set_cur_state(self.v_desired_filter.x, self.a_desired)
    # After deciding the MPC mode via get_mpc_mode(), ensure MPC uses that mode when not mlsim
    dec_mpc_mode = self.get_mpc_mode()
    if not self.mlsim:
      self.mpc.mode = dec_mpc_mode
    optional_far_lead_comfort = getattr(starpilot_toggles, "coast_up_to_leads", True)
    self.mpc.update(sm['radarState'], v_cruise, x, v, a, j,
                    sm['starpilotPlan'].dangerFactor, effective_t_follow,
                    personality=personality, tracking_lead=lead_control_active,
                    optional_far_lead_comfort=optional_far_lead_comfort)

    self.a_desired_trajectory_full = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.a_solution)
    self.v_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.v_solution)
    self.a_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC, self.mpc.a_solution)
    self.j_desired_trajectory = np.interp(CONTROL_N_T_IDX, T_IDXS_MPC[:-1], self.mpc.j_solution)

    # TODO counter is only needed because radar is glitchy, remove once radar is gone
    self.fcw = should_publish_planner_fcw(self.mpc.crash_cnt, sm['carState'], sm['radarState'])
    if self.fcw:
      cloudlog.info("FCW triggered")

    # Safety checks for rubber-banding mitigation
    max_jerk = np.max(np.abs(self.mpc.j_solution))
    max_accel_change = np.max(np.abs(np.diff(self.mpc.a_solution)))
    if max_jerk > 5.0:  # m/s^3
      cloudlog.warning(f"High jerk detected: {max_jerk:.2f} m/s^3")
    if max_accel_change > 2.0:  # m/s^2
      cloudlog.warning(f"High acceleration change: {max_accel_change:.2f} m/s^2")

    # Interpolate 0.05 seconds and save as starting point for next iteration
    a_prev = self.a_desired
    self.a_desired = float(np.interp(self.dt, CONTROL_N_T_IDX, self.a_desired_trajectory))
    self.v_desired_filter.x = self.v_desired_filter.x + self.dt * (self.a_desired + a_prev) / 2.0

    # Anticipatory pre-brake to avoid "coming in hot" when closing on a lead
    if lead_one_active:
      rel_v = max(0.0, v_ego - self.lead_one.vLead)
      # dynamic time headway adds a small buffer when uncertainty is elevated
      base_th = max(1.6, effective_t_follow)
      th = base_th + 0.6 * max(0.0, uncertainty - 0.42)
      desired_gap = th * v_ego
      if (self.lead_dist_f is not None and self.lead_dist_f < desired_gap and rel_v > 0.5):
        k_rel, k_unc = 0.04, 0.20
        pre_brake = k_rel * rel_v + k_unc * max(0.0, uncertainty - 0.42)
        pre_brake = min(pre_brake, 0.06)
        self.a_desired = float(self.a_desired - pre_brake)

    # Small deadzone around zero accel to kill micro-dithers
    if -0.05 < self.a_desired < 0.05:
      self.a_desired = 0.0

    classic_model = bool(getattr(starpilot_toggles, "classic_model", False))
    tinygrad_model = bool(getattr(starpilot_toggles, "tinygrad_model", False))
    experimental_mlsim = bool(tinygrad_model and self.mlsim and self.mode != 'acc')
    action_t = self.CP.longitudinalActuatorDelay + DT_MDL
    prev_output_a_target = float(self.output_a_target)

    if classic_model:
      output_a_target, output_should_stop = get_accel_from_plan_classic(
        self.CP, self.v_desired_trajectory, self.a_desired_trajectory, starpilot_toggles.vEgoStopping)
    elif tinygrad_model:
      output_a_target_mpc, output_should_stop_mpc = get_accel_from_plan(
        self.v_desired_trajectory, self.a_desired_trajectory,
        action_t=action_t, vEgoStopping=starpilot_toggles.vEgoStopping)
      output_a_target_e2e = sm['modelV2'].action.desiredAcceleration
      output_should_stop_e2e = sm['modelV2'].action.shouldStop

      if self.mode == 'acc' or self.generation == 'v9':
        output_a_target = output_a_target_mpc
        output_should_stop = output_should_stop_mpc
      else:
        output_a_target = min(output_a_target_mpc, output_a_target_e2e)
        output_should_stop = output_should_stop_e2e or output_should_stop_mpc
    else:
      output_a_target, output_should_stop = get_accel_from_plan(
        self.v_desired_trajectory, self.a_desired_trajectory,
        action_t=action_t, vEgoStopping=starpilot_toggles.vEgoStopping)

    comfort_output_accel_min = get_vehicle_min_accel(self.CP, v_ego) if experimental_mlsim else accel_limits_turns[0]
    vision_cap_accel_min = min(comfort_output_accel_min, get_vehicle_min_accel(self.CP, v_ego))
    output_accel_min = comfort_output_accel_min
    model_desired_accel = float(sm['modelV2'].action.desiredAcceleration)

    if not tracking_lead:
      pretracking_vision_caps = []
      for lead in (self.lead_one, self.lead_two):
        if lead.status and not bool(getattr(lead, "radar", False)):
          pretracking_cap = self.get_vision_untracked_slow_lead_cap(lead, v_ego, vision_cap_accel_min)
          if pretracking_cap is not None:
            pretracking_vision_caps.append((pretracking_cap, lead))

      if pretracking_vision_caps:
        pretracking_vision_cap, pretracking_vision_lead = min(pretracking_vision_caps, key=lambda cap_and_lead: cap_and_lead[0])
        lead_brake = max(0.0, -float(getattr(pretracking_vision_lead, "aLeadK", 0.0)))
        immediate_pretracking_cap = (
          pretracking_vision_cap <= -VISION_UNTRACKED_SLOW_LEAD_IMMEDIATE_DECEL or
          float(getattr(pretracking_vision_lead, "dRel", float("inf"))) <= VISION_UNTRACKED_SLOW_LEAD_IMMEDIATE_DISTANCE or
          lead_brake >= VISION_UNTRACKED_SLOW_LEAD_IMMEDIATE_LEAD_BRAKE or
          float(getattr(pretracking_vision_lead, "vLead", float("inf"))) <= VISION_UNTRACKED_SLOW_LEAD_RELAXED_MAX_LEAD_SPEED
        )

        if immediate_pretracking_cap:
          self.untracked_slow_lead_confirm_t = VISION_UNTRACKED_SLOW_LEAD_CONFIRM_TIME
        else:
          self.untracked_slow_lead_confirm_t = min(
            self.untracked_slow_lead_confirm_t + self.dt,
            VISION_UNTRACKED_SLOW_LEAD_CONFIRM_TIME,
          )

        if self.untracked_slow_lead_confirm_t >= VISION_UNTRACKED_SLOW_LEAD_CONFIRM_TIME:
          self.a_desired = min(self.a_desired, pretracking_vision_cap)
          output_a_target = min(output_a_target, pretracking_vision_cap)
      else:
        self.untracked_slow_lead_confirm_t = 0.0
    else:
      self.untracked_slow_lead_confirm_t = 0.0

    close_lead_caps = []
    tracked_vision_approach_caps = []
    vision_low_speed_stop_active = False
    vision_brake_cap_active = False
    if lead_control_active:
      for lead in (self.lead_one, self.lead_two):
        cap = self.get_close_lead_brake_cap(lead, v_ego, output_accel_min)
        if cap is not None:
          close_lead_caps.append(cap)
        slow_stop_cap = self.get_vision_slow_stopped_lead_cap(lead, v_ego, vision_cap_accel_min, effective_t_follow)
        if slow_stop_cap is not None:
          close_lead_caps.append(slow_stop_cap)
          vision_brake_cap_active = True
        approach_cap = self.get_vision_lead_approach_cap(lead, v_ego, vision_cap_accel_min, effective_t_follow)
        if approach_cap is not None:
          tracked_vision_approach_caps.append((
            approach_cap,
            self.tracked_vision_lead_approach_needs_immediate_brake(lead, v_ego, approach_cap),
          ))
        low_speed_stop_cap, low_speed_stop_active = self.get_vision_low_speed_stop_buffer_cap(lead, v_ego, vision_cap_accel_min)
        if low_speed_stop_cap is not None:
          close_lead_caps.append(low_speed_stop_cap)
          vision_brake_cap_active = True
        vision_low_speed_stop_active |= low_speed_stop_active
    if tracked_vision_approach_caps:
      if any(immediate for _, immediate in tracked_vision_approach_caps):
        self.vision_lead_approach_confirm_t = VISION_LEAD_APPROACH_CONFIRM_TIME
      else:
        self.vision_lead_approach_confirm_t = min(
          self.vision_lead_approach_confirm_t + self.dt,
          VISION_LEAD_APPROACH_CONFIRM_TIME,
        )

      if self.vision_lead_approach_confirm_t >= VISION_LEAD_APPROACH_CONFIRM_TIME:
        close_lead_caps.append(min(cap for cap, _ in tracked_vision_approach_caps))
        vision_brake_cap_active = True
    else:
      self.vision_lead_approach_confirm_t = 0.0
    if close_lead_caps:
      close_lead_brake_cap = min(close_lead_caps)
      self.a_desired = min(self.a_desired, close_lead_brake_cap)
      output_a_target = min(output_a_target, close_lead_brake_cap)

    standstill_nudge_gap = max(float(getattr(starpilot_toggles, "stop_distance", STOP_DISTANCE)), STOP_DISTANCE) - 0.5
    moving_leads = [lead for lead in (self.lead_one, self.lead_two)
                    if lead.status and
                    lead.vLead > STANDSTILL_LEAD_NUDGE_MIN_SPEED and lead.dRel >= standstill_nudge_gap]
    confident_depart_detected = any(self.is_confident_lead_depart(lead, float(sm['carState'].vEgo))
                                    for lead in (self.lead_one, self.lead_two))
    lead_depart_ready = any(
      lead.status and
      lead.vLead >= STANDSTILL_LEAD_DEPART_MIN_LEAD_SPEED and
      lead.dRel >= standstill_nudge_gap + STANDSTILL_LEAD_DEPART_MIN_GAP_MARGIN
      for lead in (self.lead_one, self.lead_two)
    )
    depart_safety_veto = (not bool(getattr(starpilot_toggles, "radar_takeoffs", False))
                          and self.has_offcenter_radar_depart_conflict(sm))
    if (
      lead_control_active and
      sm['carState'].standstill and
      not depart_safety_veto and
      not bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) and
      not bool(getattr(sm['starpilotPlan'], 'redLight', False)) and
      confident_depart_detected
    ):
      self.confident_lead_depart_elapsed = min(
        LEAD_DEPART_CONFIDENT_CONFIRM_TIME,
        self.confident_lead_depart_elapsed + self.dt,
      )
    else:
      self.confident_lead_depart_elapsed = 0.0
    confident_depart_ready = (
      confident_depart_detected and
      self.confident_lead_depart_elapsed >= LEAD_DEPART_CONFIDENT_CONFIRM_TIME
    )

    if lead_control_active and sm['carState'].standstill and moving_leads and not depart_safety_veto:
      output_a_target = max(output_a_target, STANDSTILL_LEAD_NUDGE_ACCEL)

    if (
      lead_control_active and
      sm['carState'].standstill and
      (confident_depart_ready or lead_depart_ready) and
      not depart_safety_veto and
      not bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) and
      not bool(getattr(sm['starpilotPlan'], 'redLight', False)) and
      (confident_depart_ready or model_desired_accel >= STANDSTILL_LEAD_DEPART_MIN_MODEL_ACCEL)
    ):
      vision_low_speed_stop_active = False
      output_should_stop = False
      output_a_target = max(output_a_target, STANDSTILL_LEAD_DEPART_MIN_ACCEL)

    if lead_control_active and lead_depart_ready and not depart_safety_veto and not output_should_stop and float(sm['carState'].vEgo) <= STANDSTILL_LEAD_DEPART_MAX_EGO_SPEED:
      output_a_target = max(output_a_target, STANDSTILL_LEAD_DEPART_MIN_ACCEL)

    if depart_safety_veto or output_should_stop or bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) or bool(getattr(sm['starpilotPlan'], 'redLight', False)):
      self.lead_depart_accel_hold_until = 0.0

    lead_depart_accel_floor = None
    if lead_control_active and not output_should_stop and not depart_safety_veto:
      lead_depart_accel_floors = [
        floor for floor in (
          self.get_lead_depart_accel_floor(self.lead_one, scene_v_ego, model_desired_accel),
          self.get_lead_depart_accel_floor(self.lead_two, scene_v_ego, model_desired_accel),
        ) if floor is not None
      ]
      if lead_depart_accel_floors:
        lead_depart_accel_floor = max(lead_depart_accel_floors)
        if sm['carState'].standstill:
          self.lead_depart_accel_hold_until = now_t + LEAD_DEPART_ACCEL_HOLD_TIME

    lead_depart_accel_hold_active = (
      lead_depart_accel_floor is not None and
      now_t < self.lead_depart_accel_hold_until and
      float(sm['carState'].vEgo) <= LEAD_DEPART_ACCEL_HOLD_MAX_EGO_SPEED
    )

    close_stop_active = bool(output_should_stop or vision_low_speed_stop_active)

    close_stop_hold_cap = None
    if lead_control_active and close_stop_active:
      close_stop_hold_caps = [
        cap for cap in (
          self.get_vision_close_stop_hold_cap(self.lead_one, v_ego, output_accel_min, close_stop_active),
          self.get_vision_close_stop_hold_cap(self.lead_two, v_ego, output_accel_min, close_stop_active),
        ) if cap is not None
      ]
      if close_stop_hold_caps:
        close_stop_hold_cap = min(close_stop_hold_caps)

    close_release_hold_cap = None
    if lead_control_active and not close_stop_active:
      close_release_hold_caps = [
        cap for cap in (
          self.get_vision_close_release_hold_cap(self.lead_one, v_ego, vision_cap_accel_min, close_stop_active),
          self.get_vision_close_release_hold_cap(self.lead_two, v_ego, vision_cap_accel_min, close_stop_active),
        ) if cap is not None
      ]
      if close_release_hold_caps:
        close_release_hold_cap = min(close_release_hold_caps)

    close_settle_guard_active = bool(
      output_should_stop or
      vision_low_speed_stop_active or
      sm['controlsState'].longControlState == LongCtrlState.stopping
    )
    close_settle_cap = None
    if lead_control_active:
      close_settle_caps = [
        cap for cap in (
          self.get_vision_close_settle_cap(self.lead_one, v_ego, output_accel_min, close_settle_guard_active),
          self.get_vision_close_settle_cap(self.lead_two, v_ego, output_accel_min, close_settle_guard_active),
        ) if cap is not None
      ]
      if close_settle_caps:
        close_settle_cap = min(close_settle_caps)

    close_final_guard_cap = None
    if lead_control_active:
      close_final_guard_caps = [
        cap for cap in (
          self.get_vision_close_final_guard_cap(self.lead_one, v_ego, output_accel_min),
          self.get_vision_close_final_guard_cap(self.lead_two, v_ego, output_accel_min),
        ) if cap is not None
      ]
      if close_final_guard_caps:
        close_final_guard_cap = min(close_final_guard_caps)

    if lead_one_active:
      lead_catchup_accel_cap = self.get_lead_catchup_accel_cap(self.lead_one, scene_v_ego, effective_t_follow)
      if lead_catchup_accel_cap is not None:
        self.a_desired = min(self.a_desired, lead_catchup_accel_cap)
        output_a_target = min(output_a_target, lead_catchup_accel_cap)

    if lead_control_active and np.isfinite(v_cruise) and any(lead.status for lead in (self.lead_one, self.lead_two)):
      # Keep follow/catchup behavior from pulling past the cruise target. Using the
      # same action horizon as the planner preserves normal accel farther below set speed.
      cruise_accel_cap = (v_cruise - v_ego + 0.01) / max(action_t, self.dt)
      output_a_target = min(output_a_target, cruise_accel_cap)

    if vision_brake_cap_active:
      output_accel_min = min(output_accel_min, vision_cap_accel_min)

    follow_control_lead = self.get_follow_control_lead(
      lead_control_active,
      scene_v_ego,
      effective_t_follow,
      allow_optional_far_lead_logic=optional_far_lead_comfort,
    )
    if follow_control_lead is not None and not panic_bypass:
      if not output_should_stop and not vision_low_speed_stop_active:
        tracked_vision_model_brake_floor = self.get_tracked_vision_model_brake_floor(
          follow_control_lead,
          scene_v_ego,
          output_accel_min,
          effective_t_follow,
          model_desired_accel,
        )
        if tracked_vision_model_brake_floor is not None:
          self.a_desired = min(self.a_desired, tracked_vision_model_brake_floor)
          output_a_target = min(output_a_target, tracked_vision_model_brake_floor)

      if optional_far_lead_comfort:
        matched_follow_brake_cap = self.get_matched_follow_brake_cap(follow_control_lead, scene_v_ego, effective_t_follow)
        if matched_follow_brake_cap is not None:
          self.a_desired = max(self.a_desired, matched_follow_brake_cap)
          output_a_target = max(output_a_target, matched_follow_brake_cap)

      if not close_lead_caps and not output_should_stop and not vision_low_speed_stop_active:
        low_speed_transition_brake_cap = self.get_low_speed_follow_transition_brake_cap(
          follow_control_lead,
          scene_v_ego,
          effective_t_follow,
          prev_output_a_target,
          output_a_target,
        )
        if low_speed_transition_brake_cap is not None:
          self.a_desired = max(self.a_desired, low_speed_transition_brake_cap)
          output_a_target = max(output_a_target, low_speed_transition_brake_cap)

    comfort_lead = self.lead_two if self.mpc.source == 'lead1' and self.lead_two.status else self.lead_one
    if optional_far_lead_comfort and comfort_lead is not None and not panic_bypass:
      far_lead_brake_cap = self.get_far_lead_brake_cap(comfort_lead, scene_v_ego, effective_t_follow)
      if far_lead_brake_cap is not None:
        self.a_desired = max(self.a_desired, far_lead_brake_cap)
        output_a_target = max(output_a_target, far_lead_brake_cap)

    if follow_control_lead is not None and not panic_bypass and not output_should_stop and not vision_low_speed_stop_active:
      tracked_vision_model_brake_cap = self.get_tracked_vision_model_brake_cap(
        follow_control_lead,
        scene_v_ego,
        effective_t_follow,
        model_desired_accel,
      )
      if tracked_vision_model_brake_cap is not None:
        self.a_desired = max(self.a_desired, tracked_vision_model_brake_cap)
        output_a_target = max(output_a_target, tracked_vision_model_brake_cap)

    if optional_far_lead_comfort and follow_control_lead is not None and not panic_bypass and not output_should_stop and not vision_low_speed_stop_active:
      matched_follow_transition_target = self.get_matched_follow_transition_target(
        follow_control_lead,
        scene_v_ego,
        effective_t_follow,
        prev_output_a_target,
        output_a_target,
        self.mpc.source,
        bool(getattr(sm["starpilotPlan"], "trackingLead", False)),
      )
      if matched_follow_transition_target is not None:
        if matched_follow_transition_target < output_a_target:
          self.a_desired = min(self.a_desired, matched_follow_transition_target)
        else:
          self.a_desired = max(self.a_desired, matched_follow_transition_target)
        output_a_target = matched_follow_transition_target

    if optional_far_lead_comfort and comfort_lead is not None and not panic_bypass and not output_should_stop and not vision_low_speed_stop_active:
      near_duplicate_transition_target = self.get_near_duplicate_lead_transition_target(
        comfort_lead,
        scene_v_ego,
        effective_t_follow,
        prev_output_a_target,
        output_a_target,
        self.mpc.source,
        bool(getattr(sm["starpilotPlan"], "trackingLead", False)),
      )
      if near_duplicate_transition_target is not None:
        if near_duplicate_transition_target < output_a_target:
          self.a_desired = min(self.a_desired, near_duplicate_transition_target)
        else:
          self.a_desired = max(self.a_desired, near_duplicate_transition_target)
        output_a_target = near_duplicate_transition_target

    if follow_control_lead is not None and not panic_bypass and not output_should_stop and not vision_low_speed_stop_active:
      cruise_tracking_lead_accel_cap = self.get_cruise_tracking_lead_accel_cap(
        follow_control_lead,
        scene_v_ego,
        effective_t_follow,
        self.mpc.source,
        tracking_lead,
      )
      if cruise_tracking_lead_accel_cap is not None:
        self.a_desired = min(self.a_desired, cruise_tracking_lead_accel_cap)
        output_a_target = min(output_a_target, cruise_tracking_lead_accel_cap)

      cruise_tracking_lead_transition_target = self.get_cruise_tracking_lead_accel_transition_target(
        follow_control_lead,
        scene_v_ego,
        effective_t_follow,
        prev_output_a_target,
        output_a_target,
        self.mpc.source,
      )
      if cruise_tracking_lead_transition_target is not None:
        self.a_desired = min(self.a_desired, cruise_tracking_lead_transition_target)
        output_a_target = min(output_a_target, cruise_tracking_lead_transition_target)

    output_accel_max = no_throttle_output_max if not self.allow_throttle else accel_limits_turns[1]
    output_a_target = float(np.clip(output_a_target, output_accel_min, output_accel_max))

    if close_stop_hold_cap is not None:
      self.a_desired = min(self.a_desired, close_stop_hold_cap)
      output_a_target = min(output_a_target, close_stop_hold_cap)

    if close_settle_cap is not None:
      self.a_desired = min(self.a_desired, close_settle_cap)
      output_a_target = min(output_a_target, close_settle_cap)

    if close_final_guard_cap is not None:
      self.a_desired = min(self.a_desired, close_final_guard_cap)
      output_a_target = min(output_a_target, close_final_guard_cap)

    if close_release_hold_cap is not None:
      self.a_desired = min(self.a_desired, close_release_hold_cap)
      output_a_target = min(output_a_target, close_release_hold_cap)

    if depart_safety_veto:
      self.a_desired = min(self.a_desired, 0.0)
      output_a_target = min(output_a_target, 0.0)
      if sm['carState'].standstill:
        output_should_stop = True

    if lead_depart_accel_hold_active:
      output_a_target = max(output_a_target, lead_depart_accel_floor)

    force_stop_handoff = bool(
      getattr(sm['starpilotPlan'], 'forcingStop', False) and
      not lead_control_active and
      (
        float(getattr(sm['starpilotPlan'], 'forcingStopLength', float('inf'))) < 1.0 or
        float(getattr(sm['starpilotPlan'], 'vCruise', float('inf'))) <= FORCE_STOP_HANDOFF_MAX_VCRUISE
      )
    )

    if force_stop_handoff:
      output_should_stop = True

    manual_stop_resume_override = self._update_manual_stop_resume_override(sm)
    if manual_stop_resume_override:
      output_a_target = max(output_a_target, MANUAL_STOP_RESUME_OVERRIDE_MIN_ACCEL)
      output_should_stop = False

    self.output_a_target = output_a_target
    self.output_should_stop = bool(output_should_stop or vision_low_speed_stop_active)

  def publish(self, sm, pm):
    plan_send = messaging.new_message('longitudinalPlan')

    plan_send.valid = sm.all_checks(service_list=['carState', 'controlsState', 'selfdriveState', 'radarState'])

    longitudinalPlan = plan_send.longitudinalPlan
    longitudinalPlan.modelMonoTime = sm.logMonoTime['modelV2']
    longitudinalPlan.processingDelay = (plan_send.logMonoTime / 1e9) - sm.logMonoTime['modelV2']
    longitudinalPlan.solverExecutionTime = self.mpc.solve_time

    longitudinalPlan.speeds = self.v_desired_trajectory.tolist()
    longitudinalPlan.accels = self.a_desired_trajectory.tolist()
    longitudinalPlan.jerks = self.j_desired_trajectory.tolist()

    longitudinalPlan.hasLead = sm['radarState'].leadOne.status
    longitudinalPlan.longitudinalPlanSource = self.mpc.source
    longitudinalPlan.fcw = self.fcw

    longitudinalPlan.aTarget = float(self.output_a_target)
    force_stop_handoff = bool(
      sm['starpilotPlan'].forcingStop and (
        sm['starpilotPlan'].forcingStopLength < 1.0 or
        sm['starpilotPlan'].vCruise <= FORCE_STOP_HANDOFF_MAX_VCRUISE
      )
    )
    longitudinalPlan.shouldStop = bool(self.output_should_stop) or force_stop_handoff
    longitudinalPlan.allowBrake = True
    longitudinalPlan.allowThrottle = bool(self.allow_throttle)

    pm.send('longitudinalPlan', plan_send)
