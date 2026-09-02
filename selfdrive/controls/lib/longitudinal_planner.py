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
from openpilot.starpilot.controls.lib.starpilot_vcruise import FT_TO_M, OFFSET_FT_MAX, OFFSET_FT_MIN
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import LongitudinalMpc, get_safe_obstacle_distance
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import desired_follow_distance
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import should_trigger_planner_fcw
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import STOP_DISTANCE
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import T_IDXS as T_IDXS_MPC
from openpilot.selfdrive.controls.lib.lead_behavior import is_radarless_matched_follow_window
from openpilot.selfdrive.controls.lib.lead_follow_policy import apply as apply_follow_policy
from openpilot.selfdrive.controls.lib.lead_follow_policy import is_nonurgent_duplicate_vision_follow
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import (
  get_far_follow_output_slew_rates,
  get_follow_prebrake_min_headway,
  get_honda_accord_lead_departure_tune,
  get_honda_accord_stop_go_accel_cap,
  get_honda_accord_stop_go_accel_rise_rate,
  get_toyota_rav4_tss2_lead_departure_tune,
  get_toyota_rav4_tss2_lead_creep_tune,
  get_force_stop_distance_bias,
  get_force_stop_handoff_distance,
  get_stop_sign_low_speed_hold,
  allow_radar_standstill_gap_settle,
  is_gm_silverado_early_follow_lead,
  is_toyota_rav4_tss2_post_departure_tune,
  get_toyota_rav4_tss2_early_lead_cap,
  is_toyota_rav4_tss2_radar_follow_lead,
  get_toyota_sienna_post_departure_restop_cap,
  get_untracked_slow_lead_decel_scale,
  get_toyota_prius_stopped_lead_obstacle_bias,
  get_honda_crv_5g_stopped_lead_obstacle_bias,
  get_honda_crv_5g_low_speed_stopped_lead_cap,
  allow_honda_crv_5g_vision_gap_settle,
  get_honda_crv_5g_early_radar_follow_cap,
  get_standstill_gap_settle_max_extra_gap,
  get_standstill_stopped_lead_guard_distance_margin,
  get_standstill_stopped_lead_guard_max_lead_speed,
  is_ford_f150_lightning_stopped_radar_follow_lead,
  get_tracked_lead_catchup_bias_gain,
  get_tracked_lead_catchup_bias_cap,
  get_tracked_lead_catchup_speed_range,
  get_tracked_lead_catchup_fade_margins,
  get_tracked_lead_catchup_cruise_error_full,
  get_tracked_lead_catchup_headway_margins,
)
from openpilot.selfdrive.controls.lib.drive_helpers import CONTROL_N
from openpilot.selfdrive.car.cruise import V_CRUISE_UNSET
from openpilot.common.swaglog import cloudlog
from cereal import log

LaneChangeState = log.LaneChangeState
LaneChangeDirection = log.LaneChangeDirection

# Lane-change merge assist: cap braking for a lead we're leaving and add a mild push.
LC_MERGE_STATES = (
  LaneChangeState.preLaneChange,
  LaneChangeState.laneChangeStarting,
  LaneChangeState.laneChangeFinishing,
)
LC_MERGE_CLOSING_MIN = 0.5
LC_MERGE_TTC_MIN = 4.0
LC_MERGE_MIN_DIST = 30.0
LC_MERGE_BRAKE_FLOOR = -0.4
LC_MERGE_TTC_ACCEL = 6.0
LC_MERGE_ACCEL_MIN_DIST = 30.0
LC_MERGE_HEADROOM_MIN = 2.0
LC_MERGE_ACCEL_BIAS = 0.55

A_CRUISE_MAX_BP = [0.0, 5., 10., 15., 20., 25., 40.]
A_CRUISE_MAX_VALS = [1.125, 1.125, 1.125, 1.125, 1.25, 1.25, 1.5]
CONTROL_N_T_IDX = ModelConstants.T_IDXS[:CONTROL_N]
ALLOW_THROTTLE_THRESHOLD = 0.4
ALLOW_THROTTLE_HYSTERESIS = 0.05
ALLOW_THROTTLE_ENABLE_THRESHOLD = ALLOW_THROTTLE_THRESHOLD + ALLOW_THROTTLE_HYSTERESIS
ALLOW_THROTTLE_DISABLE_THRESHOLD = ALLOW_THROTTLE_THRESHOLD - ALLOW_THROTTLE_HYSTERESIS
ALLOW_THROTTLE_TRANSITION_CONFIRM_TIME = 0.25
MIN_ALLOW_THROTTLE_SPEED = 5.0
FORCE_DECEL_MIN_ACCEL = -0.05
MODEL_LAUNCH_DISARM_SPEED = 2.0
MODEL_LAUNCH_COMMIT_TIME = 3.5
MODEL_LAUNCH_MOVING_SPEED = 1.2
MODEL_LAUNCH_MAX_ACCEL = 1.5
RAW_LEAD_SAFETY_MIN_CLOSING_SPEED = 0.5
RAW_LEAD_SAFETY_TTC = 7.0
RAW_LEAD_SAFETY_DISTANCE = 40.0
RAW_RADAR_STOPPED_LEAD_MAX_SPEED = 1.0
RAW_RADAR_STOPPED_LEAD_MAX_DISTANCE = 120.0
RAW_LEAD_LOW_SPEED_HOLD_MAX_EGO_SPEED = 4.5
RAW_LEAD_LOW_SPEED_HOLD_MAX_LEAD_SPEED = 3.5
RAW_LEAD_LOW_SPEED_HOLD_MAX_DISTANCE = 10.0
RAW_LEAD_LOW_SPEED_HOLD_MAX_LATERAL_OFFSET = 1.75
RAW_LEAD_LOW_SPEED_HOLD_MIN_CLOSING_SPEED = 0.15
STANDSTILL_LEAD_NUDGE_ACCEL = 0.05
STANDSTILL_LEAD_NUDGE_MIN_SPEED = 0.0
STANDSTILL_LEAD_NUDGE_MIN_LEAD_ACCEL = 0.2
STANDSTILL_LEAD_DEPART_MIN_ACCEL = 0.35
STANDSTILL_LEAD_DEPART_MAX_EGO_SPEED = 1.5
STANDSTILL_LEAD_DEPART_MIN_LEAD_SPEED = 0.6
STANDSTILL_LEAD_DEPART_MIN_GAP_MARGIN = 0.8
STANDSTILL_LEAD_DEPART_MIN_MODEL_ACCEL = 0.08
STANDSTILL_LEAD_CREEP_RELEASE_MIN_ACCEL = 0.18
STANDSTILL_LEAD_CREEP_RELEASE_CONFIRM_TIME = 0.30
RADAR_STANDSTILL_GAP_SETTLE_ACCEL = 0.18
LEAD_DEPART_CONFIDENT_CONFIRM_TIME = 0.35
LEAD_DEPART_RELEASE_HOLD_TIME = 1.5
LEAD_DEPART_RELEASE_HOLD_CONFIRM_TIME = 0.15
STANDSTILL_STOPPED_LEAD_GUARD_MAX_EGO_SPEED = 0.5
STANDSTILL_STOPPED_LEAD_GUARD_MAX_LEAD_SPEED = 0.45
STANDSTILL_STOPPED_LEAD_GUARD_MAX_LEAD_DELTA = 0.50
STANDSTILL_STOPPED_LEAD_GUARD_MIN_MODEL_PROB = 0.95
STANDSTILL_STOPPED_LEAD_GUARD_MAX_LATERAL_OFFSET = 1.75
STANDSTILL_STOPPED_LEAD_GUARD_MIN_DISTANCE = 3.0
STANDSTILL_STOPPED_LEAD_GUARD_DISTANCE_MARGIN = 3.0
STANDSTILL_STOPPED_LEAD_GUARD_MIN_BRAKE = 0.16
STANDSTILL_STOPPED_LEAD_GUARD_MAX_BRAKE = 0.26
LEAD_DEPART_ACCEL_HOLD_TIME = 1.2
LEAD_DEPART_ACCEL_HOLD_MAX_EGO_SPEED = 2.0
CLOSE_LEAD_BRAKE_CAP_MAX_TTC = 25.0
INSIDE_GAP_CLOSING_MIN_EGO_SPEED = 8.0
INSIDE_GAP_CLOSING_MIN_LEAD_SPEED = 5.0
INSIDE_GAP_CLOSING_MIN_SPEED = 0.5
INSIDE_GAP_CLOSING_FULL_SPEED = 2.5
INSIDE_GAP_CLOSING_MIN_DEFICIT = 3.0
INSIDE_GAP_CLOSING_DEFICIT_RATIO = 0.15
INSIDE_GAP_CLOSING_BRAKE_DEFICIT_RATIO = 0.25
INSIDE_GAP_CLOSING_BRAKE_MIN_SPEED = 1.0
INSIDE_GAP_CLOSING_MAX_DECEL = 0.65
INSIDE_GAP_CLOSING_MAX_LATERAL_OFFSET = 1.75
INSIDE_GAP_CLOSING_VISION_MIN_MODEL_PROB = 0.95
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
PLANNER_SAFETY_WARNING_INTERVAL = 5.0
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
VISION_UNTRACKED_SLOW_LEAD_EARLY_MIN_MODEL_PROB = 0.95
VISION_UNTRACKED_SLOW_LEAD_EARLY_MIN_CLOSING_SPEED = 2.0
VISION_UNTRACKED_SLOW_LEAD_EARLY_MIN_CLOSING_RATIO = 0.12
VISION_UNTRACKED_SLOW_LEAD_EARLY_TRIGGER_TTC = 24.0
VISION_UNTRACKED_SLOW_LEAD_NEAR_MAX_DISTANCE = 45.0
VISION_UNTRACKED_SLOW_LEAD_NEAR_MIN_MODEL_PROB = 0.90
VISION_UNTRACKED_SLOW_LEAD_NEAR_MIN_CLOSING_RATIO = 0.09
VISION_UNTRACKED_SLOW_LEAD_RELAXED_ENTRY_MAX_LATERAL_OFFSET = 1.2
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
VISION_UNTRACKED_APPROACH_LIFT_MIN_EGO_SPEED = 18.0
VISION_UNTRACKED_APPROACH_LIFT_MIN_MODEL_PROB = 0.95
VISION_UNTRACKED_APPROACH_LIFT_MAX_LATERAL_OFFSET = 1.2
VISION_UNTRACKED_APPROACH_LIFT_MIN_CLOSING_SPEED = 0.75
VISION_UNTRACKED_APPROACH_LIFT_MAX_DISTANCE = 130.0
VISION_UNTRACKED_APPROACH_LIFT_MIN_GAP_EXCESS = 6.0
VISION_UNTRACKED_APPROACH_LIFT_TRIGGER_TIME = 20.0
VISION_UNTRACKED_APPROACH_LIFT_FULL_TIME = 6.0
VISION_UNTRACKED_APPROACH_LIFT_MAX_ACCEL = 0.22
VISION_UNTRACKED_APPROACH_LIFT_CONFIRM_TIME = 0.30
VISION_UNTRACKED_APPROACH_LIFT_HOLD_TIME = 0.75
VISION_UNTRACKED_APPROACH_LIFT_RATE_DOWN = 0.35
VISION_UNTRACKED_APPROACH_LIFT_RATE_UP = 0.25
VISION_SLOW_LEAD_MAX_SPEED = 5.0
VISION_SLOW_LEAD_MIN_CLOSING_SPEED = 1.5
VISION_SLOW_LEAD_TRIGGER_TTC = 4.5
VISION_SLOW_LEAD_FULL_TTC = 2.0
VISION_SLOW_LEAD_MAX_DECEL = 1.2
VISION_SLOW_LEAD_MIN_DECEL = 0.18
VISION_SLOW_LEAD_MIN_MODEL_PROB = 0.9
LEAD_APPROACH_TFOLLOW_TRIGGER_TIME = 4.5
LEAD_APPROACH_TFOLLOW_FULL_TIME = 1.5
LEAD_APPROACH_TFOLLOW_MAX_DELTA = 0.162
LEAD_APPROACH_TFOLLOW_MAX_CLOSING_SPEED = 6.0
LEAD_APPROACH_TFOLLOW_MAX_LEAD_BRAKE = 2.5
LEAD_APPROACH_TFOLLOW_MIN_CLOSING_SPEED = 0.75
LEAD_APPROACH_TFOLLOW_MIN_LEAD_BRAKE = 0.2
LEAD_APPROACH_TFOLLOW_WINDOW_MIN = 6.0
LEAD_APPROACH_TFOLLOW_WINDOW_GAIN = 0.35
LEAD_APPROACH_TFOLLOW_RATE_UP = 1.0
LEAD_APPROACH_TFOLLOW_RATE_DOWN = 0.60
VISION_LEAD_TFOLLOW_MAX_EXTRA_DELTA = 0.216
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
VISION_CLOSE_SETTLE_MAX_EGO_SPEED = 0.75
VISION_CLOSE_SETTLE_MAX_LEAD_SPEED = 2.75
VISION_CLOSE_SETTLE_MAX_DISTANCE = 4.2
MANUAL_STOP_RESUME_OVERRIDE_MIN_ACCEL = 0.2
FORCE_STOP_HANDOFF_MAX_VCRUISE = 0.5
POST_DEPARTURE_FOLLOW_SETTLE_LATCH_TIME = 75.0
POST_DEPARTURE_FOLLOW_SETTLE_MIN_SPEED = 8.0
POST_DEPARTURE_FOLLOW_SETTLE_MAX_ARM_SPEED = 16.0
POST_DEPARTURE_FOLLOW_SETTLE_MIN_MODEL_PROB = 0.9
POST_DEPARTURE_FOLLOW_SETTLE_MAX_LATERAL_OFFSET = 1.15
POST_DEPARTURE_FOLLOW_SETTLE_MAX_CLOSING_SPEED = 0.8
POST_DEPARTURE_FOLLOW_SETTLE_MAX_LEAD_BRAKE = 0.10
POST_DEPARTURE_FOLLOW_SETTLE_ARM_MIN_LEAD_DELTA = -0.10
POST_DEPARTURE_FOLLOW_SETTLE_ARM_MIN_LEAD_ACCEL = 0.20
POST_DEPARTURE_FOLLOW_SETTLE_ARM_MIN_HEADWAY_MARGIN = 0.08
POST_DEPARTURE_FOLLOW_SETTLE_COMPLETE_HEADWAY_MARGIN = 0.05

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
STEADY_FOLLOW_SMOOTHING_FILTER_FACTOR_FLOOR = 0.24
EXPERIMENTAL_RELEASE_ACCEL_HOLD_TIME = 0.75
# At low speed, preserve the existing handoff slew long enough to bridge a
# brief slow-lead CEM dropout without extending high-speed release behavior.
EXPERIMENTAL_RELEASE_ACCEL_LOW_SPEED_HOLD_TIME = 3.0
EXPERIMENTAL_RELEASE_ACCEL_LOW_SPEED_THRESHOLD = 12.0
EXPERIMENTAL_RELEASE_ACCEL_MIN_SPEED = 2.5
EXPERIMENTAL_RELEASE_ACCEL_MIN_LEAD_SPEED = 5.0
EXPERIMENTAL_RELEASE_ACCEL_MIN_LEAD_DELTA = -1.0
EXPERIMENTAL_RELEASE_ACCEL_MAX_LEAD_BRAKE = 0.2
EXPERIMENTAL_RELEASE_ACCEL_MIN_DELTA_A = 0.12
EXPERIMENTAL_RELEASE_ACCEL_STEP = 0.06
# Last few mph below CESpeed/CESpeedLead: mix MPC back in so experimental
# cannot crawl into the breakpoint and then snap to ACC.
EXPERIMENTAL_SPEED_HANDOFF_BAND = 5.0 * CV.MPH_TO_MS
EXPERIMENTAL_HANDOFF_KEEP_E2E_BRAKE = -0.15
MATCHED_FOLLOW_TRANSITION_MIN_SPEED = 20.0
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
  is_gm = getattr(CP, "carName", "") == "gm" or getattr(CP, "brand", "") == "gm"
  if is_gm and getattr(CP, "enableGasInterceptorDEPRECATED", False):
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


# Restored planner constants retained by CEM, stop, and departure paths.
A_CRUISE_MIN = -1.0
# The stop distance runs ~9 m long through the mid-approach, which leaves the obstacle slack
# so it stays silent and deceleration sags. Multiplicative so the trim scales with what is
# left. Note the car parks where the obstacle sits, so this is also a placement bias — 0.85
# stopped ~4.6 m short, 0.93 ~1.6 m.
FORCE_STOP_OBSTACLE_TRIM = 0.93
STANDSTILL_LEAD_CREEP_RELEASE_MIN_LEAD_SPEED = 0.25
STANDSTILL_LEAD_CREEP_RELEASE_MIN_LEAD_ACCEL = 0.08
STANDSTILL_LEAD_CREEP_RELEASE_MIN_GAP_MARGIN = 0.1
RADAR_STANDSTILL_GAP_SETTLE_CONFIRM_TIME = 0.50
RADAR_STANDSTILL_GAP_SETTLE_ENTRY_MARGIN = 0.60
RADAR_STANDSTILL_GAP_SETTLE_EXIT_MARGIN = 0.15
RADAR_STANDSTILL_GAP_SETTLE_MAX_EXTRA_GAP = 1.5
RADAR_STANDSTILL_GAP_SETTLE_MAX_EGO_SPEED = 0.45
RADAR_STANDSTILL_GAP_SETTLE_MAX_LEAD_SPEED = 0.15
RADAR_STANDSTILL_GAP_SETTLE_MAX_LATERAL_OFFSET = 1.0
LEAD_DEPART_CONFIDENT_MIN_GAP = 3.75
LEAD_DEPART_CONFIDENT_MAX_GAP = 5.25
LEAD_DEPART_CONFIDENT_MIN_LEAD_SPEED = 0.3
LEAD_DEPART_CONFIDENT_MIN_LEAD_DELTA = 0.25
LEAD_DEPART_CONFIDENT_MIN_LEAD_ACCEL = 0.2
LEAD_DEPART_RELEASE_HOLD_MIN_DISTANCE = 3.0
LEAD_DEPART_RELEASE_HOLD_MIN_LEAD_SPEED = 0.55
LEAD_DEPART_RELEASE_HOLD_MIN_LEAD_DELTA = 0.25
LEAD_DEPART_RELEASE_HOLD_MAX_LEAD_BRAKE = 0.15
LEAD_DEPART_RELEASE_HOLD_MIN_MODEL_PROB = 0.95
LEAD_DEPART_RELEASE_HOLD_MAX_LATERAL_OFFSET = 1.0
LEAD_DEPART_RELEASE_HOLD_CONFLICT_SPEED = 0.25
LEAD_DEPART_RELEASE_HOLD_CONFLICT_DISTANCE_MARGIN = 3.0
VEHICLE_FAR_FOLLOW_SLEW_MIN_SPEED = 10.0
VEHICLE_FAR_FOLLOW_SLEW_MIN_DISTANCE = 25.0
VEHICLE_FAR_FOLLOW_SLEW_MIN_DISTANCE_TIME = 1.35
VEHICLE_FAR_FOLLOW_SLEW_MIN_HEADWAY = 1.35
VEHICLE_FAR_FOLLOW_SLEW_MIN_TTC = 8.0
VEHICLE_FAR_FOLLOW_SLEW_MAX_LATERAL_OFFSET = 1.5
RADAR_DEPART_CONFLICT_MAX_EGO_SPEED = 1.6
RADAR_DEPART_CONFLICT_MIN_RADAR_LATERAL = 1.5
RADAR_DEPART_CONFLICT_MAX_RADAR_DISTANCE = 18.0
RADAR_DEPART_CONFLICT_MIN_MODEL_PROB = 0.95
RADAR_DEPART_CONFLICT_MAX_MODEL_DISTANCE = 18.0
RADAR_DEPART_CONFLICT_MAX_MODEL_LATERAL = 0.9
RADAR_DEPART_CONFLICT_MAX_MODEL_LEAD_SPEED = 2.0
RADAR_DEPART_CONFLICT_MAX_DISTANCE_MISMATCH = 4.0
LEAD_DEPART_ACCEL_HOLD_MIN_LEAD_SPEED = 0.6
LEAD_DEPART_ACCEL_HOLD_MIN_LEAD_DELTA = 0.5
LEAD_DEPART_ACCEL_HOLD_MIN_GAP = 3.5
LEAD_DEPART_ACCEL_HOLD_FULL_GAP = 6.0
LEAD_DEPART_ACCEL_HOLD_FULL_LEAD_SPEED = 2.2
LEAD_DEPART_ACCEL_HOLD_MIN_MODEL_PROB = 0.85
LEAD_DEPART_ACCEL_HOLD_MIN_MODEL_ACCEL = 0.12
LEAD_DEPART_ACCEL_HOLD_MAX_LEAD_BRAKE = 0.2
LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL = 0.25
LEAD_DEPART_ACCEL_HOLD_MAX_ACCEL = 0.55
LEAD_DEPART_ACCEL_ASSIST = 0.10
LEAD_DEPART_ACCEL_HOLD_REUSE_MIN_GAP = 3.75
LEAD_DEPART_ACCEL_HOLD_REUSE_MAX_CLOSING_SPEED = 0.45
LEAD_DEPART_ACCEL_HOLD_REUSE_MAX_LEAD_BRAKE = 0.2
LEAD_DEPART_ACCEL_HOLD_REUSE_MIN_HEADWAY_MARGIN = 0.10
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_EGO_SPEED = 4.5
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_DISTANCE = 4.0
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_DISTANCE = 18.0
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LEAD_SPEED = 4.0
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LATERAL_OFFSET = 1.75
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_MODEL_PROB = 0.9
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_LEAD_DELTA = -0.5
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LEAD_DELTA = 0.75
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_LEAD_ACCEL = -0.4
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LEAD_ACCEL = 0.25
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_ACCEL = 0.08
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_ACCEL = 0.22
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MAX_EGO_SPEED = 1.25
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MIN_GAP = 4.0
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MIN_LEAD_SPEED = 1.2
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MIN_LEAD_DELTA = 0.8
LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MIN_LEAD_ACCEL = 0.5
VISION_CLOSE_STOP_HOLD_MIN_BRAKE = 0.20
VISION_CLOSE_STOP_HOLD_MAX_BRAKE = 0.36
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
# Give a driver-initiated launch enough time to clear a stale model stop/light
# prediction before the stop request is allowed to reassert.
MANUAL_STOP_RESUME_OVERRIDE_TIME = 6.0
MANUAL_STOP_RESUME_OVERRIDE_MAX_SPEED = 2.0

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
    self.model_allow_throttle_transition_t = 0.0
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
    self.far_follow_brake_slew_rate, self.far_follow_release_slew_rate = get_far_follow_output_slew_rates(CP)
    self.untracked_slow_lead_decel_scale = get_untracked_slow_lead_decel_scale(CP)
    self.tracked_lead_catchup_headway_margins = get_tracked_lead_catchup_headway_margins(CP)
    self.far_follow_output_slew_active = False
    self.model_launch_armed = False
    self.model_launch_stop_seen = False
    self.confident_lead_depart_elapsed = 0.0
    self.slow_creep_lead_depart_elapsed = 0.0
    self.lead_depart_release_candidate_elapsed = 0.0
    self.lead_depart_release_pending = False
    self.lead_depart_release_hold_remaining = 0.0
    self.radar_standstill_gap_settle_elapsed = 0.0
    self.radar_standstill_gap_settle_active = False
    self.tracked_lead_catchup_bias_gain = get_tracked_lead_catchup_bias_gain(CP)
    self.tracked_lead_catchup_bias_cap = get_tracked_lead_catchup_bias_cap(CP)
    self.tracked_lead_catchup_speed_range = get_tracked_lead_catchup_speed_range(CP)
    self.tracked_lead_catchup_fade_margins = get_tracked_lead_catchup_fade_margins(CP)
    self.tracked_lead_catchup_cruise_error_full = get_tracked_lead_catchup_cruise_error_full(CP)

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
    self._safety_warning_log_t = 0.0
    self.effective_t_follow = None
    self.vision_low_speed_stop_hold_until = 0.0
    self.vision_lead_approach_confirm_t = 0.0
    self.untracked_slow_lead_confirm_t = 0.0
    self.untracked_vision_approach_lift_confirm_t = 0.0
    self.untracked_vision_approach_lift_cap = None
    self.untracked_vision_approach_lift_target = None
    self.untracked_vision_approach_lift_hold_until = 0.0
    self.manual_stop_resume_override_until = 0.0
    self.lead_depart_accel_hold_until = 0.0
    self.lead_depart_accel_hold_floor = None
    self.post_departure_follow_settle_until = 0.0
    self.duplicate_vision_comfort_lead_source = None
    self.prev_experimental_mode = None
    self.experimental_release_accel_until = 0.0

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
      temporal_pose = model_msg.temporalPoseDEPRECATED
    except AttributeError:
      try:
        temporal_pose = model_msg.temporalPose
      except AttributeError:
        return 0.0
    if len(temporal_pose.trans):
      return float(np.clip(temporal_pose.trans[0] - v_ego, -5.0, 5.0))
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

  @staticmethod
  def get_model_launch_accel(model_v, model_a, action_t, v_ego):
    if len(model_v) != len(T_IDXS_MPC) or len(model_a) != len(T_IDXS_MPC):
      return None
    if float(np.interp(MODEL_LAUNCH_COMMIT_TIME, T_IDXS_MPC, model_v)) <= MODEL_LAUNCH_DISARM_SPEED:
      return None

    moving_idxs = np.flatnonzero(np.asarray(model_v) > MODEL_LAUNCH_MOVING_SPEED)
    if len(moving_idxs) == 0:
      return None

    t_cut = min(float(T_IDXS_MPC[int(moving_idxs[0])]), MODEL_LAUNCH_COMMIT_TIME)
    shifted_t = T_IDXS_MPC + t_cut
    shifted_v = np.interp(shifted_t, T_IDXS_MPC, model_v)
    shifted_a = np.interp(shifted_t, T_IDXS_MPC, model_a)
    safe_action_t = max(float(action_t), 1e-3)
    v_target = float(np.interp(safe_action_t, T_IDXS_MPC, shifted_v))
    a_launch = 2.0 * (v_target - float(shifted_v[0])) / safe_action_t - float(shifted_a[0])
    accel_cap = float(np.interp(
      float(v_ego),
      [MODEL_LAUNCH_MOVING_SPEED, MODEL_LAUNCH_DISARM_SPEED],
      [MODEL_LAUNCH_MAX_ACCEL, 0.0],
    ))
    return float(np.clip(a_launch, 0.0, accel_cap))

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

  @staticmethod
  def get_inside_gap_closing_lead_accel_cap(lead, v_ego, accel_min, t_follow):
    if lead is None or not lead.status:
      return None

    ego_speed = float(v_ego)
    lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
    if ego_speed < INSIDE_GAP_CLOSING_MIN_EGO_SPEED or lead_speed < INSIDE_GAP_CLOSING_MIN_LEAD_SPEED:
      return None
    if abs(float(getattr(lead, "yRel", 0.0))) > INSIDE_GAP_CLOSING_MAX_LATERAL_OFFSET:
      return None

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and lead_prob < INSIDE_GAP_CLOSING_VISION_MIN_MODEL_PROB:
      return None

    closing_speed = ego_speed - lead_speed
    if closing_speed < INSIDE_GAP_CLOSING_MIN_SPEED:
      return None

    desired_gap = float(desired_follow_distance(ego_speed, lead_speed, float(t_follow)))
    gap_deficit = desired_gap - float(lead.dRel)
    trigger_deficit = max(INSIDE_GAP_CLOSING_MIN_DEFICIT,
                          INSIDE_GAP_CLOSING_DEFICIT_RATIO * desired_gap)
    if gap_deficit <= trigger_deficit:
      return None

    brake_deficit = INSIDE_GAP_CLOSING_BRAKE_DEFICIT_RATIO * desired_gap
    deficit_factor = float(np.clip(
      (gap_deficit - brake_deficit) / max(brake_deficit, 1.0),
      0.0,
      1.0,
    ))
    closing_factor = float(np.clip(
      (closing_speed - INSIDE_GAP_CLOSING_BRAKE_MIN_SPEED) /
      (INSIDE_GAP_CLOSING_FULL_SPEED - INSIDE_GAP_CLOSING_BRAKE_MIN_SPEED),
      0.0,
      1.0,
    ))
    required_decel = 0.45 * deficit_factor + 0.20 * closing_factor
    required_decel = min(required_decel, INSIDE_GAP_CLOSING_MAX_DECEL)
    return max(float(accel_min), -required_decel)

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
    closing_ratio = projected_closing_speed / max(float(v_ego), 0.1)
    projected_ttc = float(lead.dRel) / max(projected_closing_speed, 0.1)

    standard_entry = bool(
      projected_closing_speed >= VISION_UNTRACKED_SLOW_LEAD_MIN_CLOSING_SPEED and
      closing_ratio >= VISION_UNTRACKED_SLOW_LEAD_MIN_CLOSING_RATIO and
      projected_ttc <= VISION_UNTRACKED_SLOW_LEAD_TRIGGER_TTC
    )
    centered_relaxed_entry = (
      abs(float(getattr(lead, "yRel", 0.0))) <= VISION_UNTRACKED_SLOW_LEAD_RELAXED_ENTRY_MAX_LATERAL_OFFSET
    )
    high_confidence_early_entry = bool(
      centered_relaxed_entry and
      lead_prob + 1e-6 >= VISION_UNTRACKED_SLOW_LEAD_EARLY_MIN_MODEL_PROB and
      projected_closing_speed >= VISION_UNTRACKED_SLOW_LEAD_EARLY_MIN_CLOSING_SPEED and
      closing_ratio >= VISION_UNTRACKED_SLOW_LEAD_EARLY_MIN_CLOSING_RATIO and
      projected_ttc <= VISION_UNTRACKED_SLOW_LEAD_EARLY_TRIGGER_TTC
    )
    near_early_entry = bool(
      centered_relaxed_entry and
      float(lead.dRel) <= VISION_UNTRACKED_SLOW_LEAD_NEAR_MAX_DISTANCE and
      lead_prob + 1e-6 >= VISION_UNTRACKED_SLOW_LEAD_NEAR_MIN_MODEL_PROB and
      projected_closing_speed >= VISION_UNTRACKED_SLOW_LEAD_EARLY_MIN_CLOSING_SPEED and
      closing_ratio >= VISION_UNTRACKED_SLOW_LEAD_NEAR_MIN_CLOSING_RATIO and
      projected_ttc <= VISION_UNTRACKED_SLOW_LEAD_EARLY_TRIGGER_TTC
    )
    if not (standard_entry or high_confidence_early_entry or near_early_entry):
      return None

    trigger_ttc = VISION_UNTRACKED_SLOW_LEAD_TRIGGER_TTC
    min_closing_ratio = VISION_UNTRACKED_SLOW_LEAD_MIN_CLOSING_RATIO
    if high_confidence_early_entry:
      trigger_ttc = VISION_UNTRACKED_SLOW_LEAD_EARLY_TRIGGER_TTC
      min_closing_ratio = VISION_UNTRACKED_SLOW_LEAD_EARLY_MIN_CLOSING_RATIO
    if near_early_entry:
      trigger_ttc = VISION_UNTRACKED_SLOW_LEAD_EARLY_TRIGGER_TTC
      min_closing_ratio = VISION_UNTRACKED_SLOW_LEAD_NEAR_MIN_CLOSING_RATIO

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

    if lead_prob + 1e-6 < min_model_prob:
      return None

    time_factor = float(np.clip((trigger_ttc - projected_ttc) /
                                (trigger_ttc - VISION_UNTRACKED_SLOW_LEAD_FULL_TTC),
                                0.0, 1.0))
    prob_factor = float(np.clip((lead_prob - min_model_prob) /
                                (VISION_UNTRACKED_SLOW_LEAD_FULL_MODEL_PROB - min_model_prob),
                                0.0, 1.0))
    closing_factor = float(np.clip((closing_ratio - min_closing_ratio) /
                                   (VISION_UNTRACKED_SLOW_LEAD_FULL_CLOSING_RATIO - min_closing_ratio),
                                   0.0, 1.0))
    approach_decel = VISION_UNTRACKED_SLOW_LEAD_MAX_DECEL * self.untracked_slow_lead_decel_scale * np.clip(
      0.5 * time_factor + 0.3 * prob_factor + 0.2 * closing_factor, 0.0, 1.0)
    if approach_decel < VISION_UNTRACKED_SLOW_LEAD_MIN_DECEL:
      return None

    return max(accel_min, -approach_decel)

  @staticmethod
  def get_vision_untracked_approach_lift_cap(lead, v_ego, t_follow):
    """Trim throttle before a confident vision lead reaches the tracking window."""
    if lead is None or not lead.status or bool(getattr(lead, "radar", False)):
      return None
    if float(v_ego) < VISION_UNTRACKED_APPROACH_LIFT_MIN_EGO_SPEED:
      return None

    lead_prob = float(getattr(lead, "modelProb", 0.0))
    if lead_prob < VISION_UNTRACKED_APPROACH_LIFT_MIN_MODEL_PROB:
      return None
    if abs(float(getattr(lead, "yRel", 0.0))) > VISION_UNTRACKED_APPROACH_LIFT_MAX_LATERAL_OFFSET:
      return None
    if float(lead.dRel) > VISION_UNTRACKED_APPROACH_LIFT_MAX_DISTANCE:
      return None

    closing_speed = float(v_ego) - float(lead.vLead)
    if closing_speed < VISION_UNTRACKED_APPROACH_LIFT_MIN_CLOSING_SPEED:
      return None

    desired_gap = float(desired_follow_distance(v_ego, lead.vLead, t_follow))
    gap_excess = float(lead.dRel) - desired_gap
    if gap_excess < VISION_UNTRACKED_APPROACH_LIFT_MIN_GAP_EXCESS:
      return 0.0

    time_to_desired_gap = gap_excess / max(closing_speed, 0.1)
    if time_to_desired_gap > VISION_UNTRACKED_APPROACH_LIFT_TRIGGER_TIME:
      return None

    # This path only removes positive acceleration. Braking remains exclusively
    # owned by lead tracking and the existing close-lead safety caps.
    return float(np.interp(
      time_to_desired_gap,
      [VISION_UNTRACKED_APPROACH_LIFT_FULL_TIME, VISION_UNTRACKED_APPROACH_LIFT_TRIGGER_TIME],
      [0.0, VISION_UNTRACKED_APPROACH_LIFT_MAX_ACCEL],
    ))

  def update_vision_untracked_approach_lift_cap(self, raw_cap, output_a_target, prev_output_a_target,
                                                now_t, untracked):
    if untracked and raw_cap is not None:
      if self.untracked_vision_approach_lift_cap is None:
        self.untracked_vision_approach_lift_confirm_t = min(
          self.untracked_vision_approach_lift_confirm_t + self.dt,
          VISION_UNTRACKED_APPROACH_LIFT_CONFIRM_TIME,
        )
        if self.untracked_vision_approach_lift_confirm_t >= VISION_UNTRACKED_APPROACH_LIFT_CONFIRM_TIME:
          self.untracked_vision_approach_lift_cap = float(prev_output_a_target)
      if self.untracked_vision_approach_lift_cap is not None:
        self.untracked_vision_approach_lift_target = float(raw_cap)
        self.untracked_vision_approach_lift_hold_until = now_t + VISION_UNTRACKED_APPROACH_LIFT_HOLD_TIME
    elif self.untracked_vision_approach_lift_cap is None:
      self.untracked_vision_approach_lift_confirm_t = 0.0

    active_cap = self.untracked_vision_approach_lift_cap
    if active_cap is None:
      return None

    holding = untracked and now_t < self.untracked_vision_approach_lift_hold_until
    target = self.untracked_vision_approach_lift_target if holding else float(output_a_target)
    if target is None:
      target = float(output_a_target)

    lower = active_cap - VISION_UNTRACKED_APPROACH_LIFT_RATE_DOWN * self.dt
    upper = active_cap + VISION_UNTRACKED_APPROACH_LIFT_RATE_UP * self.dt
    active_cap = float(np.clip(target, lower, upper))
    self.untracked_vision_approach_lift_cap = active_cap

    if not holding and active_cap >= float(output_a_target) - 1e-6:
      self.untracked_vision_approach_lift_confirm_t = 0.0
      self.untracked_vision_approach_lift_cap = None
      self.untracked_vision_approach_lift_target = None
      self.untracked_vision_approach_lift_hold_until = 0.0
      return None

    return active_cap

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
    accel_pressed = bool(
      getattr(starpilot_car_state, "accelPressed", False) or
      getattr(sm["carState"], "gasPressed", False)
    )
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

  def is_slow_creep_lead_depart(self, lead, v_ego, standstill_nudge_gap):
    if lead is None or not lead.status:
      return False

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and lead_prob < STANDSTILL_STOPPED_LEAD_GUARD_MIN_MODEL_PROB:
      return False

    if abs(float(getattr(lead, "yRel", 0.0))) > STANDSTILL_STOPPED_LEAD_GUARD_MAX_LATERAL_OFFSET:
      return False

    lead_gap = float(getattr(lead, "dRel", 0.0))
    lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
    lead_accel = float(getattr(lead, "aLeadK", 0.0))
    creep_tune = get_toyota_rav4_tss2_lead_creep_tune(self.CP)
    min_lead_speed, min_lead_accel = (
      (STANDSTILL_LEAD_CREEP_RELEASE_MIN_LEAD_SPEED,
       STANDSTILL_LEAD_CREEP_RELEASE_MIN_LEAD_ACCEL)
      if creep_tune is None else creep_tune
    )
    return bool(
      float(v_ego) <= STANDSTILL_LEAD_DEPART_MAX_EGO_SPEED and
      lead_gap >= standstill_nudge_gap + STANDSTILL_LEAD_CREEP_RELEASE_MIN_GAP_MARGIN and
      lead_speed >= min_lead_speed and
      lead_accel >= min_lead_accel
    )

  def get_safe_depart_release_hold_lead(self, v_ego):
    credible_leads = [
      lead for lead in (self.lead_one, self.lead_two)
      if lead is not None and
      bool(getattr(lead, "status", False)) and
      (bool(getattr(lead, "radar", False)) or
       float(getattr(lead, "modelProb", 0.0)) >= LEAD_DEPART_RELEASE_HOLD_MIN_MODEL_PROB) and
      abs(float(getattr(lead, "yRel", 0.0))) <= LEAD_DEPART_RELEASE_HOLD_MAX_LATERAL_OFFSET
    ]
    moving_leads = [
      lead for lead in credible_leads
      if float(getattr(lead, "dRel", 0.0)) >= LEAD_DEPART_RELEASE_HOLD_MIN_DISTANCE and
      float(getattr(lead, "vLead", 0.0)) >= LEAD_DEPART_RELEASE_HOLD_MIN_LEAD_SPEED and
      float(getattr(lead, "vLead", 0.0)) - float(v_ego) >= LEAD_DEPART_RELEASE_HOLD_MIN_LEAD_DELTA and
      max(0.0, -float(getattr(lead, "aLeadK", 0.0))) <= LEAD_DEPART_RELEASE_HOLD_MAX_LEAD_BRAKE
    ]
    if not moving_leads:
      return None

    selected_lead = min(moving_leads, key=lambda lead: float(lead.dRel))
    stopped_conflict = any(
      lead is not selected_lead and
      float(getattr(lead, "dRel", float("inf"))) <= float(selected_lead.dRel) + LEAD_DEPART_RELEASE_HOLD_CONFLICT_DISTANCE_MARGIN and
      float(getattr(lead, "vLead", 0.0)) < LEAD_DEPART_RELEASE_HOLD_CONFLICT_SPEED
      for lead in credible_leads
    )
    return None if stopped_conflict else selected_lead

  def get_vehicle_far_follow_slew_target(self, v_ego, prev_target, target, output_should_stop, panic_bypass):
    if self.far_follow_brake_slew_rate <= 0.0 or self.far_follow_release_slew_rate <= 0.0 or output_should_stop or panic_bypass:
      self.far_follow_output_slew_active = False
      return target

    centered_leads = [
      lead for lead in (self.lead_one, self.lead_two)
      if bool(getattr(lead, "status", False)) and
      abs(float(getattr(lead, "yRel", 0.0))) <= VEHICLE_FAR_FOLLOW_SLEW_MAX_LATERAL_OFFSET
    ]
    safe_far_follow = bool(centered_leads and float(v_ego) >= VEHICLE_FAR_FOLLOW_SLEW_MIN_SPEED)
    for lead in centered_leads:
      distance = float(getattr(lead, "dRel", 0.0))
      closing_speed = max(0.0, float(v_ego) - float(getattr(lead, "vLead", v_ego)))
      ttc = distance / max(closing_speed, 0.1) if closing_speed > 0.1 else float("inf")
      headway = distance / max(float(v_ego), 1e-3)
      safe_far_follow &= bool(
        distance >= max(VEHICLE_FAR_FOLLOW_SLEW_MIN_DISTANCE,
                        VEHICLE_FAR_FOLLOW_SLEW_MIN_DISTANCE_TIME * float(v_ego)) and
        headway >= VEHICLE_FAR_FOLLOW_SLEW_MIN_HEADWAY and
        ttc >= VEHICLE_FAR_FOLLOW_SLEW_MIN_TTC
      )

    slew_was_active = self.far_follow_output_slew_active
    self.far_follow_output_slew_active = safe_far_follow
    if not safe_far_follow or not slew_was_active:
      return target

    return float(np.clip(
      target,
      float(prev_target) - self.far_follow_brake_slew_rate * self.dt,
      float(prev_target) + self.far_follow_release_slew_rate * self.dt,
    ))

  @staticmethod
  def is_radar_standstill_gap_settle_candidate(lead, v_ego, target_gap, active=False,
                                               allow_vision=False, max_extra_gap=RADAR_STANDSTILL_GAP_SETTLE_MAX_EXTRA_GAP):
    if lead is None or not lead.status or (not bool(getattr(lead, "radar", False)) and not allow_vision):
      return False
    if float(v_ego) > RADAR_STANDSTILL_GAP_SETTLE_MAX_EGO_SPEED:
      return False
    if abs(float(getattr(lead, "yRel", 0.0))) > RADAR_STANDSTILL_GAP_SETTLE_MAX_LATERAL_OFFSET:
      return False
    if abs(float(getattr(lead, "vLead", 0.0))) > RADAR_STANDSTILL_GAP_SETTLE_MAX_LEAD_SPEED:
      return False
    if allow_vision and (
      bool(getattr(lead, "radar", False)) or
      float(getattr(lead, "modelProb", 0.0)) < 0.99
    ):
      return False

    lead_gap = float(getattr(lead, "dRel", 0.0))
    min_margin = RADAR_STANDSTILL_GAP_SETTLE_EXIT_MARGIN if active else RADAR_STANDSTILL_GAP_SETTLE_ENTRY_MARGIN
    return bool(
      lead_gap > target_gap + min_margin and
      lead_gap <= target_gap + float(max_extra_gap)
    )

  def update_radar_standstill_gap_settle(self, sm, target_gap, allow_vision=False, max_extra_gap=None):
    vetoed = bool(
      getattr(sm["carState"], "brakePressed", False) or
      getattr(sm["carState"], "gasPressed", False) or
      getattr(sm["starpilotPlan"], "forcingStop", False) or
      getattr(sm["starpilotPlan"], "redLight", False)
    )
    candidates = [
      lead for lead in (self.lead_one, self.lead_two)
      if self.is_radar_standstill_gap_settle_candidate(
        lead,
        float(sm["carState"].vEgo),
        target_gap,
        active=self.radar_standstill_gap_settle_active,
        allow_vision=allow_vision,
        max_extra_gap=(RADAR_STANDSTILL_GAP_SETTLE_MAX_EXTRA_GAP if max_extra_gap is None else max_extra_gap),
      )
    ]

    if vetoed or not candidates:
      self.radar_standstill_gap_settle_elapsed = 0.0
      self.radar_standstill_gap_settle_active = False
      return False

    if self.radar_standstill_gap_settle_active:
      return True

    if not bool(sm["carState"].standstill):
      self.radar_standstill_gap_settle_elapsed = 0.0
      return False

    self.radar_standstill_gap_settle_elapsed = min(
      RADAR_STANDSTILL_GAP_SETTLE_CONFIRM_TIME,
      self.radar_standstill_gap_settle_elapsed + self.dt,
    )
    self.radar_standstill_gap_settle_active = (
      self.radar_standstill_gap_settle_elapsed + 1e-6 >= RADAR_STANDSTILL_GAP_SETTLE_CONFIRM_TIME
    )
    return self.radar_standstill_gap_settle_active

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
    departure_tune = get_honda_accord_lead_departure_tune(self.CP)
    if departure_tune is None:
      departure_tune = get_toyota_rav4_tss2_lead_departure_tune(self.CP)
    max_accel = LEAD_DEPART_ACCEL_HOLD_MAX_ACCEL if departure_tune is None else departure_tune[0]
    assist = LEAD_DEPART_ACCEL_ASSIST if departure_tune is None else departure_tune[1]
    accel_cap = LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL + (max_accel - LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL) * np.clip(
      0.55 * lead_factor + 0.45 * gap_factor, 0.0, 1.0)
    assisted_model_accel = float(model_desired_accel) + assist
    return min(accel_cap, max(assisted_model_accel, LEAD_DEPART_ACCEL_HOLD_MIN_ACCEL))

  def get_reusable_lead_depart_accel_floor(self, lead, v_ego, t_follow):
    if self.lead_depart_accel_hold_floor is None or lead is None or not lead.status:
      return None

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and lead_prob < LEAD_DEPART_ACCEL_HOLD_MIN_MODEL_PROB:
      return None

    if abs(float(getattr(lead, "yRel", 0.0))) > STANDSTILL_STOPPED_LEAD_GUARD_MAX_LATERAL_OFFSET:
      return None

    d_rel = float(getattr(lead, "dRel", 0.0))
    if d_rel < LEAD_DEPART_ACCEL_HOLD_REUSE_MIN_GAP:
      return None

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > LEAD_DEPART_ACCEL_HOLD_REUSE_MAX_LEAD_BRAKE:
      return None

    closing_speed = max(float(v_ego) - float(getattr(lead, "vLead", 0.0)), 0.0)
    if closing_speed > LEAD_DEPART_ACCEL_HOLD_REUSE_MAX_CLOSING_SPEED:
      return None

    actual_headway = d_rel / max(float(v_ego), 1e-3)
    headway_margin = actual_headway - float(t_follow)
    if headway_margin < LEAD_DEPART_ACCEL_HOLD_REUSE_MIN_HEADWAY_MARGIN:
      return None

    return float(self.lead_depart_accel_hold_floor)

  def get_low_speed_weak_lead_accel_cap(self, lead, v_ego):
    if lead is None or not lead.status:
      return None

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and lead_prob < LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_MODEL_PROB:
      return None

    d_rel = float(getattr(lead, "dRel", 0.0))
    lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
    lead_delta = lead_speed - float(v_ego)
    lead_accel = float(getattr(lead, "aLeadK", 0.0))
    lead_lateral = abs(float(getattr(lead, "yRel", 0.0)))
    if (
      float(v_ego) > LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_EGO_SPEED or
      d_rel > LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_DISTANCE or
      lead_speed > LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LEAD_SPEED or
      lead_lateral > LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LATERAL_OFFSET or
      lead_delta > LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LEAD_DELTA or
      lead_accel > LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LEAD_ACCEL
    ):
      return None

    if (
      float(v_ego) <= LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MAX_EGO_SPEED and
      d_rel >= LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MIN_GAP and
      lead_speed >= LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MIN_LEAD_SPEED and
      lead_delta >= LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MIN_LEAD_DELTA and
      lead_accel >= LOW_SPEED_WEAK_LEAD_ACCEL_CAP_STRONG_DEPART_MIN_LEAD_ACCEL
    ):
      return None

    distance_factor = float(np.clip(
      (d_rel - LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_DISTANCE) /
      max(LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_DISTANCE - LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_DISTANCE, 0.1),
      0.0, 1.0,
    ))
    delta_factor = float(np.clip(
      (lead_delta - LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_LEAD_DELTA) /
      max(LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LEAD_DELTA - LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_LEAD_DELTA, 0.1),
      0.0, 1.0,
    ))
    accel_factor = float(np.clip(
      (lead_accel - LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_LEAD_ACCEL) /
      max(LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_LEAD_ACCEL - LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_LEAD_ACCEL, 0.1),
      0.0, 1.0,
    ))
    cap_strength = float(np.clip(0.5 * distance_factor + 0.3 * delta_factor + 0.2 * accel_factor, 0.0, 1.0))
    return LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_ACCEL + (
      LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MAX_ACCEL - LOW_SPEED_WEAK_LEAD_ACCEL_CAP_MIN_ACCEL
    ) * cap_strength

  def get_honda_accord_stop_go_accel_target(self, lead, v_ego, previous_target, target, blocked):
    """Smooth the Accord's low-speed lead launch without touching braking targets."""
    if blocked or target <= 0.0:
      return float(target)

    cap = get_honda_accord_stop_go_accel_cap(self.CP, lead, v_ego)
    if cap is None:
      return float(target)

    limited_target = min(float(target), cap)
    if limited_target > float(previous_target):
      rise_rate = get_honda_accord_stop_go_accel_rise_rate(self.CP)
      if rise_rate > 0.0:
        limited_target = min(
          limited_target,
          max(0.0, float(previous_target) + rise_rate * self.dt),
        )
    return float(limited_target)

  def get_standstill_stopped_lead_guard_cap(self, lead, v_ego, accel_min, stop_distance,
                                            release_ready, confident_depart_ready):
    if lead is None or not lead.status or release_ready or confident_depart_ready:
      return None
    if float(v_ego) > STANDSTILL_STOPPED_LEAD_GUARD_MAX_EGO_SPEED:
      return None

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and lead_prob < STANDSTILL_STOPPED_LEAD_GUARD_MIN_MODEL_PROB:
      return None

    if abs(float(getattr(lead, "yRel", 0.0))) > STANDSTILL_STOPPED_LEAD_GUARD_MAX_LATERAL_OFFSET:
      return None

    lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
    lead_delta = lead_speed - float(v_ego)
    max_lead_speed = get_standstill_stopped_lead_guard_max_lead_speed(
      self.CP, STANDSTILL_STOPPED_LEAD_GUARD_MAX_LEAD_SPEED,
    )
    max_distance = max(
      STANDSTILL_STOPPED_LEAD_GUARD_MIN_DISTANCE,
      float(stop_distance) + get_standstill_stopped_lead_guard_distance_margin(self.CP),
    )
    if (
      float(getattr(lead, "dRel", float("inf"))) > max_distance or
      lead_speed > max_lead_speed or
      lead_delta > STANDSTILL_STOPPED_LEAD_GUARD_MAX_LEAD_DELTA
    ):
      return None

    distance_factor = float(np.clip((max_distance - float(lead.dRel)) /
                                    max(max_distance - STANDSTILL_STOPPED_LEAD_GUARD_MIN_DISTANCE, 0.1),
                                    0.0, 1.0))
    speed_factor = float(np.clip(lead_speed / max(max_lead_speed, 0.1), 0.0, 1.0))
    delta_factor = float(np.clip((STANDSTILL_STOPPED_LEAD_GUARD_MAX_LEAD_DELTA - lead_delta) /
                                 max(STANDSTILL_STOPPED_LEAD_GUARD_MAX_LEAD_DELTA, 0.1),
                                 0.0, 1.0))
    hold_brake = STANDSTILL_STOPPED_LEAD_GUARD_MIN_BRAKE + 0.06 * distance_factor + 0.02 * speed_factor + 0.02 * delta_factor
    hold_brake = float(np.clip(
      hold_brake,
      STANDSTILL_STOPPED_LEAD_GUARD_MIN_BRAKE,
      STANDSTILL_STOPPED_LEAD_GUARD_MAX_BRAKE,
    ))
    brake_floor = -hold_brake
    return brake_floor if accel_min >= 0.0 else max(accel_min, brake_floor)

  def post_departure_follow_settle_active(self, lead, v_ego, t_follow):
    if lead is None or not lead.status:
      return False
    if float(v_ego) < POST_DEPARTURE_FOLLOW_SETTLE_MIN_SPEED:
      return False

    lead_radar = bool(getattr(lead, "radar", False))
    lead_prob = float(getattr(lead, "modelProb", 1.0 if lead_radar else 0.0))
    if not lead_radar and lead_prob < POST_DEPARTURE_FOLLOW_SETTLE_MIN_MODEL_PROB:
      return False

    if abs(float(getattr(lead, "yRel", 0.0))) > POST_DEPARTURE_FOLLOW_SETTLE_MAX_LATERAL_OFFSET:
      return False

    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
    headway_margin = actual_headway - float(t_follow)
    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    closing_speed = max(float(v_ego) - float(lead.vLead), 0.0)
    now = time.monotonic()
    if now > self.post_departure_follow_settle_until:
      self.post_departure_follow_settle_until = 0.0
      lead_delta = float(lead.vLead) - float(v_ego)
      lead_accel = float(getattr(lead, "aLeadK", 0.0))
      # Rolling launches can miss the standstill release edge that normally arms
      # this latch. Confirm the same safe pull-away state from lead motion instead.
      rolling_departure = (
        float(v_ego) <= POST_DEPARTURE_FOLLOW_SETTLE_MAX_ARM_SPEED and
        lead_delta >= POST_DEPARTURE_FOLLOW_SETTLE_ARM_MIN_LEAD_DELTA and
        lead_accel >= POST_DEPARTURE_FOLLOW_SETTLE_ARM_MIN_LEAD_ACCEL and
        headway_margin >= POST_DEPARTURE_FOLLOW_SETTLE_ARM_MIN_HEADWAY_MARGIN
      )
      if not rolling_departure:
        return False
      self.post_departure_follow_settle_until = now + POST_DEPARTURE_FOLLOW_SETTLE_LATCH_TIME

    if (
      headway_margin <= POST_DEPARTURE_FOLLOW_SETTLE_COMPLETE_HEADWAY_MARGIN or
      lead_brake > POST_DEPARTURE_FOLLOW_SETTLE_MAX_LEAD_BRAKE or
      closing_speed > POST_DEPARTURE_FOLLOW_SETTLE_MAX_CLOSING_SPEED
    ):
      self.post_departure_follow_settle_until = 0.0
      return False

    return True

  def update_experimental_release_accel_state(self, experimental_mode, now_t, v_ego=None):
    if self.prev_experimental_mode is True and not experimental_mode:
      low_speed_release = v_ego is not None and float(v_ego) < EXPERIMENTAL_RELEASE_ACCEL_LOW_SPEED_THRESHOLD
      hold_time = EXPERIMENTAL_RELEASE_ACCEL_LOW_SPEED_HOLD_TIME if low_speed_release else EXPERIMENTAL_RELEASE_ACCEL_HOLD_TIME
      self.experimental_release_accel_until = now_t + hold_time
    elif experimental_mode:
      self.experimental_release_accel_until = 0.0
    self.prev_experimental_mode = bool(experimental_mode)

  def get_experimental_speed_handoff_weight(self, v_ego, experimental_mode, following_lead,
                                            starpilot_toggles, hold_experimental):
    if not experimental_mode or hold_experimental:
      return 0.0

    limit_key = "conditional_limit_lead" if following_lead else "conditional_limit"
    limit = float(getattr(starpilot_toggles, limit_key, 0.0) or 0.0)
    if limit <= 1.0:
      return 0.0

    return float(np.clip(
      (float(v_ego) - (limit - EXPERIMENTAL_SPEED_HANDOFF_BAND)) / EXPERIMENTAL_SPEED_HANDOFF_BAND,
      0.0,
      1.0,
    ))

  @staticmethod
  def is_cem_following_lead(tracking_lead, d_rel, t_follow, v_ego):
    # Same inputs as StarPilotFollowing.following_lead / CEM: published
    # trackingLead and tFollow, plus leadOne.dRel inside 2*t_follow*v_ego.
    return bool(tracking_lead and float(d_rel) < (float(t_follow) * 2.0) * float(v_ego))

  @staticmethod
  def apply_experimental_speed_handoff(output_a_target, output_a_target_mpc, output_a_target_e2e, speed_handoff):
    if speed_handoff <= 0.0:
      return output_a_target
    # Keep a real E2E brake. Only mix MPC back in when experimental is crawling
    # or matching ACC, not when it is already asking for more deceleration.
    if output_a_target_e2e < min(output_a_target_mpc, EXPERIMENTAL_HANDOFF_KEEP_E2E_BRAKE):
      return output_a_target
    return (1.0 - speed_handoff) * output_a_target + speed_handoff * output_a_target_mpc

  def get_experimental_release_accel_target(self, lead, v_ego, base_t_follow,
                                            prev_output_a_target, output_a_target,
                                            release_active):
    if not release_active or v_ego < EXPERIMENTAL_RELEASE_ACCEL_MIN_SPEED:
      return None

    # Only veto comfort slewing for a real closing/stopped/braking lead. Open-road
    # CESpeed exits and unmatched distant leads used to skip this path and floor.
    if lead is not None and bool(getattr(lead, "status", False)):
      lead_speed = float(lead.vLead)
      lead_delta = lead_speed - float(v_ego)
      lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
      if lead_speed < EXPERIMENTAL_RELEASE_ACCEL_MIN_LEAD_SPEED:
        return None
      if lead_delta < EXPERIMENTAL_RELEASE_ACCEL_MIN_LEAD_DELTA:
        return None
      if lead_brake > EXPERIMENTAL_RELEASE_ACCEL_MAX_LEAD_BRAKE:
        return None

    if float(output_a_target) - float(prev_output_a_target) < EXPERIMENTAL_RELEASE_ACCEL_MIN_DELTA_A:
      return None

    return min(float(output_a_target), float(prev_output_a_target) + EXPERIMENTAL_RELEASE_ACCEL_STEP)

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

    d_rel = max(float(lead.dRel), 0.0)
    lead_speed = max(float(getattr(lead, "vLead", 0.0)), 0.0)
    closing_speed = float(v_ego - lead.vLead)
    lead_braking = float(lead.aLeadK) < -0.5
    centered_lead = abs(float(getattr(lead, "yRel", 0.0))) <= RAW_LEAD_LOW_SPEED_HOLD_MAX_LATERAL_OFFSET
    if (
      centered_lead and
      float(v_ego) <= RAW_LEAD_LOW_SPEED_HOLD_MAX_EGO_SPEED and
      lead_speed <= RAW_LEAD_LOW_SPEED_HOLD_MAX_LEAD_SPEED and
      d_rel <= RAW_LEAD_LOW_SPEED_HOLD_MAX_DISTANCE and
      closing_speed >= RAW_LEAD_LOW_SPEED_HOLD_MIN_CLOSING_SPEED
    ):
      return True

    if closing_speed <= RAW_LEAD_SAFETY_MIN_CLOSING_SPEED and not lead_braking:
      return False

    dynamic_distance = max(RAW_LEAD_SAFETY_DISTANCE, 3.0 * float(v_ego))
    if bool(getattr(lead, "radar", False)) and lead_speed <= RAW_RADAR_STOPPED_LEAD_MAX_SPEED:
      dynamic_distance = max(
        dynamic_distance,
        min(RAW_RADAR_STOPPED_LEAD_MAX_DISTANCE, 5.0 * float(v_ego)),
      )
    ttc = d_rel / max(closing_speed, 0.1) if closing_speed > 0.1 else float("inf")
    return d_rel < dynamic_distance and (ttc < RAW_LEAD_SAFETY_TTC or lead_braking)

  def get_lane_change_merge_accel_floor(self, sm, starpilot_toggles, scene_v_ego, v_cruise, action_t, blocked):
    # Accel floor (m/s^2) to apply as max(output_a_target, floor) while merging out, else None.
    if blocked or not getattr(starpilot_toggles, "lane_change_close_gap", False):
      return None

    meta = sm['modelV2'].meta
    if meta.laneChangeState not in LC_MERGE_STATES:
      return None

    CS = sm['carState']
    if CS.standstill or bool(getattr(CS, "brakePressed", False)):
      return None
    if scene_v_ego < float(getattr(starpilot_toggles, "minimum_lane_change_speed", 0.0)):
      return None

    direction = meta.laneChangeDirection
    if (direction == LaneChangeDirection.left and CS.leftBlindspot) or \
       (direction == LaneChangeDirection.right and CS.rightBlindspot):
      return None

    # Only intervene when there's a lead we're merging around; leave curve/open-road braking alone.
    lead = self.lead_one
    if not lead.status:
      return None

    d_rel = float(lead.dRel)
    closing = scene_v_ego - float(lead.vLead)
    ttc = d_rel / closing if closing > LC_MERGE_CLOSING_MIN else float('inf')
    # A close lead (small gap or short time-to-reach) keeps full braking authority.
    if ttc < LC_MERGE_TTC_MIN or d_rel < LC_MERGE_MIN_DIST:
      return None

    floor = LC_MERGE_BRAKE_FLOOR
    if (self.allow_throttle and ttc >= LC_MERGE_TTC_ACCEL and d_rel >= LC_MERGE_ACCEL_MIN_DIST and
        np.isfinite(v_cruise) and (v_cruise - scene_v_ego) >= LC_MERGE_HEADROOM_MIN):
      cruise_cap = max(0.0, (v_cruise - scene_v_ego) / max(action_t, self.dt))
      floor = min(LC_MERGE_ACCEL_BIAS, cruise_cap)
    return floor

  def update(self, sm, starpilot_toggles):
    if self.is_preap:
      self._preap_param_frame += 1
      if self._preap_params is not None and (self._preap_param_frame % 20) == 0:
        self.nap_adaptive_accel = self._preap_params.get_bool("NAPAdaptiveAccel")

    self.generation = getattr(starpilot_toggles, "model_version", None)
    experimental_mode = bool(sm['selfdriveState'].experimentalMode)
    self.mode = 'blended' if experimental_mode else 'acc'
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
      self.model_allow_throttle_transition_t = 0.0

    # Prevent divergence, smooth in current v_ego
    self.v_desired_filter.x = max(0.0, self.v_desired_filter.update(v_ego))
    # Compute model v_ego error
    self.v_model_error = self.get_model_speed_error(sm['modelV2'], v_ego)
    x, v, a, j, throttle_prob = self.parse_model(sm['modelV2'], self.v_model_error, v_ego, starpilot_toggles)
    if bool(sm['carState'].standstill):
      self.model_launch_armed = True
      self.model_launch_stop_seen |= bool(
        sm['modelV2'].action.shouldStop or
        getattr(sm['starpilotPlan'], 'redLight', False) or
        getattr(sm['starpilotPlan'], 'forcingStop', False)
      )
    elif scene_v_ego > MODEL_LAUNCH_DISARM_SPEED:
      self.model_launch_armed = False
      self.model_launch_stop_seen = False
    model_launch_v = np.array(v, copy=True)
    model_launch_a = np.array(a, copy=True)
    # Don't clip at low speeds since throttle_prob doesn't account for creep. Raw
    # gasPressProb can cross both hysteresis thresholds for only a few model frames,
    # so confirm transitions before changing the physical coast cap.
    if v_ego <= MIN_ALLOW_THROTTLE_SPEED:
      self.model_allow_throttle = True
      self.model_allow_throttle_transition_t = 0.0
    else:
      transition_requested = (
        throttle_prob <= ALLOW_THROTTLE_DISABLE_THRESHOLD if self.model_allow_throttle
        else throttle_prob > ALLOW_THROTTLE_ENABLE_THRESHOLD
      )
      if transition_requested:
        self.model_allow_throttle_transition_t += self.dt
        if self.model_allow_throttle_transition_t + 1e-6 >= ALLOW_THROTTLE_TRANSITION_CONFIRM_TIME:
          self.model_allow_throttle = not self.model_allow_throttle
          self.model_allow_throttle_transition_t = 0.0
      else:
        self.model_allow_throttle_transition_t = 0.0
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
    early_truck_follow = (
      not experimental_mode and
      any(is_gm_silverado_early_follow_lead(self.CP, lead, scene_v_ego) for lead in (self.lead_one, self.lead_two))
    )
    rav4_radar_follow = (
      not experimental_mode and
      any(is_toyota_rav4_tss2_radar_follow_lead(self.CP, lead, scene_v_ego)
          for lead in (self.lead_one, self.lead_two))
    )
    lightning_stopped_radar_follow = (
      experimental_mode and
      not bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) and
      not bool(getattr(sm['starpilotPlan'], 'redLight', False)) and
      not bool(getattr(sm['starpilotPlan'], 'stopSignConfirmed', False)) and
      any(is_ford_f150_lightning_stopped_radar_follow_lead(self.CP, lead, scene_v_ego)
          for lead in (self.lead_one, self.lead_two))
    )
    # StarPilot trackingLead is debounce/model-length based. Keep a raw close-lead
    # safety path so ACC/chill does not ignore a visible lead during that debounce.
    lead_control_active = (
      tracking_lead or raw_close_lead_control or early_truck_follow or rav4_radar_follow or
      lightning_stopped_radar_follow
    )
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
    self.update_experimental_release_accel_state(experimental_mode, now_t, scene_v_ego)
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
    # Duplicate vision tracks can share the same noisy velocity spike. Keep the
    # comfort path unless distance, TTC, or lead braking makes the scene urgent.
    nonurgent_duplicate_vision_follow = is_nonurgent_duplicate_vision_follow(
      self.lead_one, self.lead_two, scene_v_ego, effective_t_follow, self.mpc,
    )
    if panic_bypass and nonurgent_duplicate_vision_follow:
      panic_bypass = False

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
    # Hand the forced stop to the solver as a position. The obstacle sits STOP_DISTANCE
    # beyond the line because the safe-distance term already includes it — placing it on
    # the line parks us short. Below that the existing v_cruise=0 path finishes the stop,
    # since forcingStopLength is decaying to zero and the obstacle would land behind us.
    force_stop_x = None
    force_stop_handoff_m = get_force_stop_handoff_distance(self.CP.carFingerprint)
    if sm['starpilotPlan'].forcingStop and sm['starpilotPlan'].forcingStopLength > force_stop_handoff_m:
      stop_length = float(sm['starpilotPlan'].forcingStopLength)
    else:
      # pre-commit the envelope is only a speed ceiling, which the solver tracks with a lag;
      # getattr so a stale cereal build degrades to the old behaviour instead of raising
      stop_length = float(getattr(sm['starpilotPlan'], 'approachStopLength', 0.0))
    if stop_length > force_stop_handoff_m:
      # ForceStopDistanceOffset shifts the perceived line for the v_cruise ceiling, so it has
      # to shift the obstacle too or the slider barely moves anything now that stop_x leads.
      offset_ft = max(OFFSET_FT_MIN, min(OFFSET_FT_MAX, int(getattr(starpilot_toggles, 'force_stop_distance_offset', 0) or 0)))
      force_stop_x = (
        stop_length * FORCE_STOP_OBSTACLE_TRIM + offset_ft * FT_TO_M + STOP_DISTANCE +
        get_force_stop_distance_bias(self.CP.carFingerprint)
      )

    stopped_lead_obstacle_bias = (0.0, 0.0)
    if (
      self.mode == 'acc' and
      not bool(getattr(sm['modelV2'].action, 'shouldStop', False)) and
      not bool(getattr(sm['starpilotPlan'], 'redLight', False)) and
      not bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) and
      not bool(getattr(sm['carState'], 'standstill', False))
    ):
      stopped_lead_obstacle_bias = tuple(
        max(
          get_toyota_prius_stopped_lead_obstacle_bias(self.CP, lead, scene_v_ego),
          get_honda_crv_5g_stopped_lead_obstacle_bias(self.CP, lead, scene_v_ego),
        )
        for lead in (self.lead_one, self.lead_two)
      )

    self.mpc.update(sm['radarState'], v_cruise, x, v, a, j,
                    sm['starpilotPlan'].dangerFactor, effective_t_follow,
                    personality=personality, tracking_lead=lead_control_active,
                    optional_far_lead_comfort=True,
                    smooth_duplicate_vision=nonurgent_duplicate_vision_follow and not panic_bypass,
                    stop_x=force_stop_x,
                    silverado_early_follow=early_truck_follow,
                    modelV2=sm['modelV2'],
                    lead_obstacle_bias=stopped_lead_obstacle_bias,
                    tracked_lead_catchup_headway_margins=self.tracked_lead_catchup_headway_margins,
                    tracked_lead_catchup_bias_gain=self.tracked_lead_catchup_bias_gain,
                    tracked_lead_catchup_bias_cap=self.tracked_lead_catchup_bias_cap,
                    tracked_lead_catchup_speed_range=self.tracked_lead_catchup_speed_range,
                    tracked_lead_catchup_fade_margins=self.tracked_lead_catchup_fade_margins,
                    tracked_lead_catchup_cruise_error_full=self.tracked_lead_catchup_cruise_error_full)

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
    if (max_jerk > 5.0 or max_accel_change > 2.0) and now_t - self._safety_warning_log_t >= PLANNER_SAFETY_WARNING_INTERVAL:
      cloudlog.warning(
        f"Longitudinal planner output discontinuity: jerk={max_jerk:.2f} m/s^3, "
        f"accel_change={max_accel_change:.2f} m/s^2"
      )
      self._safety_warning_log_t = now_t

    # Interpolate 0.05 seconds and save as starting point for next iteration
    a_prev = self.a_desired
    self.a_desired = float(np.interp(self.dt, CONTROL_N_T_IDX, self.a_desired_trajectory))
    self.v_desired_filter.x = self.v_desired_filter.x + self.dt * (self.a_desired + a_prev) / 2.0

    # Anticipatory pre-brake to avoid "coming in hot" when closing on a lead
    if lead_one_active:
      rel_v = max(0.0, v_ego - self.lead_one.vLead)
      # dynamic time headway adds a small buffer when uncertainty is elevated
      base_th = get_follow_prebrake_min_headway(self.CP, effective_t_follow)
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
    model_launch_accel = None
    if self.model_launch_armed and not bool(sm['modelV2'].action.shouldStop):
      model_launch_accel = self.get_model_launch_accel(model_launch_v, model_launch_a, action_t, scene_v_ego)

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
        cem_following_lead = self.is_cem_following_lead(
          tracking_lead,
          self.lead_one.dRel,
          sm['starpilotPlan'].tFollow,
          scene_v_ego,
        )
        speed_handoff = self.get_experimental_speed_handoff_weight(
          scene_v_ego,
          experimental_mode,
          cem_following_lead,
          starpilot_toggles,
          bool(
            output_should_stop_e2e or
            getattr(sm['starpilotPlan'], 'forcingStop', False) or
            getattr(sm['starpilotPlan'], 'redLight', False)
          ),
        )
        output_a_target = self.apply_experimental_speed_handoff(
          output_a_target, output_a_target_mpc, output_a_target_e2e, speed_handoff,
        )
    else:
      output_a_target, output_should_stop = get_accel_from_plan(
        self.v_desired_trajectory, self.a_desired_trajectory,
        action_t=action_t, vEgoStopping=starpilot_toggles.vEgoStopping)

    comfort_output_accel_min = get_vehicle_min_accel(self.CP, v_ego) if experimental_mlsim else accel_limits_turns[0]
    vision_cap_accel_min = min(comfort_output_accel_min, get_vehicle_min_accel(self.CP, v_ego))
    output_accel_min = comfort_output_accel_min
    model_desired_accel = float(sm['modelV2'].action.desiredAcceleration)

    raw_approach_lift_cap = None
    if not tracking_lead:
      approach_lift_caps = [
        cap for cap in (
          self.get_vision_untracked_approach_lift_cap(self.lead_one, v_ego, effective_t_follow),
          self.get_vision_untracked_approach_lift_cap(self.lead_two, v_ego, effective_t_follow),
        ) if cap is not None
      ]
      if approach_lift_caps:
        raw_approach_lift_cap = min(approach_lift_caps)

      if not experimental_mode:
        # Apply the RAV4's mild early-lead response before ordinary lead tracking
        # is admitted. This only removes throttle while a centered, confident
        # lead is already braking; the normal safety path remains authoritative.
        rav4_pretracking_caps = [
          cap for cap in (
            get_toyota_rav4_tss2_early_lead_cap(
              self.CP, self.lead_one, v_ego, vision_cap_accel_min,
            ),
            get_toyota_rav4_tss2_early_lead_cap(
              self.CP, self.lead_two, v_ego, vision_cap_accel_min,
            ),
          ) if cap is not None
        ]
        if rav4_pretracking_caps:
          rav4_pretracking_cap = min(rav4_pretracking_caps)
          self.a_desired = min(self.a_desired, rav4_pretracking_cap)
          output_a_target = min(output_a_target, rav4_pretracking_cap)

        early_radar_caps = [
          cap for cap in (
            get_honda_crv_5g_early_radar_follow_cap(
              self.CP, self.lead_one, v_ego, vision_cap_accel_min,
            ),
            get_honda_crv_5g_early_radar_follow_cap(
              self.CP, self.lead_two, v_ego, vision_cap_accel_min,
            ),
          ) if cap is not None
        ]
        if early_radar_caps:
          early_radar_cap = min(early_radar_caps)
          self.a_desired = min(self.a_desired, early_radar_cap)
          output_a_target = min(output_a_target, early_radar_cap)

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

    approach_lift_cap = self.update_vision_untracked_approach_lift_cap(
      raw_approach_lift_cap,
      output_a_target,
      prev_output_a_target,
      now_t,
      not tracking_lead,
    )
    if approach_lift_cap is not None:
      self.a_desired = min(self.a_desired, approach_lift_cap)
      output_a_target = min(output_a_target, approach_lift_cap)

    close_lead_caps = []
    rav4_early_lead_caps = []
    tracked_vision_approach_caps = []
    vision_low_speed_stop_active = False
    vision_brake_cap_active = False
    if lead_control_active:
      for lead in (self.lead_one, self.lead_two):
        rav4_early_lead_cap = get_toyota_rav4_tss2_early_lead_cap(
          self.CP, lead, v_ego, output_accel_min,
        )
        if rav4_early_lead_cap is not None:
          rav4_early_lead_caps.append(rav4_early_lead_cap)
        cap = self.get_close_lead_brake_cap(lead, v_ego, output_accel_min)
        if cap is not None:
          close_lead_caps.append(cap)
        cap = get_honda_crv_5g_low_speed_stopped_lead_cap(
          self.CP, lead, v_ego, vision_cap_accel_min,
        )
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

    standstill_nudge_gap = STOP_DISTANCE - 0.5
    moving_leads = [lead for lead in (self.lead_one, self.lead_two)
                    if lead.status and
                    lead.vLead > STANDSTILL_LEAD_NUDGE_MIN_SPEED and lead.dRel >= standstill_nudge_gap]
    accelerating_nudge_lead = any(
      lead.status and
      float(getattr(lead, "vLead", 0.0)) > STANDSTILL_LEAD_NUDGE_MIN_SPEED and
      float(getattr(lead, "aLeadK", 0.0)) >= STANDSTILL_LEAD_NUDGE_MIN_LEAD_ACCEL and
      float(getattr(lead, "dRel", 0.0)) >= standstill_nudge_gap
      for lead in (self.lead_one, self.lead_two)
    )
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
    safe_depart_release_hold_lead = self.get_safe_depart_release_hold_lead(float(sm['carState'].vEgo))
    depart_release_hold_context = bool(
      lead_control_active and
      float(sm['carState'].vEgo) <= STANDSTILL_LEAD_DEPART_MAX_EGO_SPEED and
      not depart_safety_veto and
      not bool(getattr(sm['carState'], 'brakePressed', False)) and
      not bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) and
      not bool(getattr(sm['starpilotPlan'], 'redLight', False)) and
      safe_depart_release_hold_lead is not None
    )
    if depart_release_hold_context:
      self.lead_depart_release_candidate_elapsed = min(
        LEAD_DEPART_RELEASE_HOLD_CONFIRM_TIME,
        self.lead_depart_release_candidate_elapsed + self.dt,
      )
    else:
      self.lead_depart_release_candidate_elapsed = 0.0
      self.lead_depart_release_pending = False
      self.lead_depart_release_hold_remaining = 0.0

    if self.lead_depart_release_hold_remaining > 0.0:
      self.lead_depart_release_hold_remaining = max(0.0, self.lead_depart_release_hold_remaining - self.dt)
    depart_release_hold_active = bool(depart_release_hold_context and self.lead_depart_release_hold_remaining > 0.0)
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
    slow_creep_depart_detected = any(
      self.is_slow_creep_lead_depart(lead, float(sm['carState'].vEgo), standstill_nudge_gap)
      for lead in (self.lead_one, self.lead_two)
    )
    if (
      lead_control_active and
      sm['carState'].standstill and
      not depart_safety_veto and
      not bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) and
      not bool(getattr(sm['starpilotPlan'], 'redLight', False)) and
      slow_creep_depart_detected
    ):
      self.slow_creep_lead_depart_elapsed = min(
        STANDSTILL_LEAD_CREEP_RELEASE_CONFIRM_TIME,
        self.slow_creep_lead_depart_elapsed + self.dt,
      )
    else:
      self.slow_creep_lead_depart_elapsed = 0.0
    slow_creep_depart_ready = (
      slow_creep_depart_detected and
      self.slow_creep_lead_depart_elapsed >= STANDSTILL_LEAD_CREEP_RELEASE_CONFIRM_TIME
    )
    radar_gap_settle_active = False
    if allow_radar_standstill_gap_settle(self.CP) or allow_honda_crv_5g_vision_gap_settle(self.CP):
      radar_gap_settle_active = self.update_radar_standstill_gap_settle(
        sm,
        standstill_nudge_gap,
        allow_vision=allow_honda_crv_5g_vision_gap_settle(self.CP),
        max_extra_gap=get_standstill_gap_settle_max_extra_gap(self.CP),
      )
    else:
      self.radar_standstill_gap_settle_elapsed = 0.0
      self.radar_standstill_gap_settle_active = False

    standstill_stopped_lead_guard_cap = None
    standstill_guard_lead_present = any(bool(getattr(lead, "status", False)) for lead in (self.lead_one, self.lead_two))
    if standstill_guard_lead_present and (bool(sm['carState'].standstill) or float(sm['carState'].vEgo) <= STANDSTILL_STOPPED_LEAD_GUARD_MAX_EGO_SPEED):
      release_ready = bool(
        lead_depart_ready or confident_depart_ready or slow_creep_depart_ready or
        radar_gap_settle_active or depart_release_hold_active
      )
      standstill_stopped_lead_guard_caps = [
        cap for cap in (
          self.get_standstill_stopped_lead_guard_cap(
            self.lead_one,
            float(sm['carState'].vEgo),
            output_accel_min,
            standstill_nudge_gap,
            release_ready,
            confident_depart_ready,
          ),
          self.get_standstill_stopped_lead_guard_cap(
            self.lead_two,
            float(sm['carState'].vEgo),
            output_accel_min,
            standstill_nudge_gap,
            release_ready,
            confident_depart_ready,
          ),
        ) if cap is not None
      ]
      if standstill_stopped_lead_guard_caps:
        standstill_stopped_lead_guard_cap = min(standstill_stopped_lead_guard_caps)
        output_should_stop = True

    if lead_control_active and sm['carState'].standstill and moving_leads and not depart_safety_veto:
      output_a_target = max(output_a_target, STANDSTILL_LEAD_NUDGE_ACCEL)

    if (
      lead_control_active and
      sm['carState'].standstill and
      (confident_depart_ready or lead_depart_ready or slow_creep_depart_ready) and
      not depart_safety_veto and
      not bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) and
      not bool(getattr(sm['starpilotPlan'], 'redLight', False)) and
      (confident_depart_ready or slow_creep_depart_ready or model_desired_accel >= STANDSTILL_LEAD_DEPART_MIN_MODEL_ACCEL)
    ):
      vision_low_speed_stop_active = False
      output_should_stop = False
      depart_min_accel = STANDSTILL_LEAD_DEPART_MIN_ACCEL
      if slow_creep_depart_ready and not (confident_depart_ready or lead_depart_ready):
        depart_min_accel = STANDSTILL_LEAD_CREEP_RELEASE_MIN_ACCEL
      output_a_target = max(output_a_target, depart_min_accel)
      self.post_departure_follow_settle_until = now_t + POST_DEPARTURE_FOLLOW_SETTLE_LATCH_TIME

    if depart_release_hold_context and bool(self.output_should_stop) and not bool(output_should_stop):
      self.lead_depart_release_pending = True
    if (
      depart_release_hold_context and
      self.lead_depart_release_pending and
      not bool(output_should_stop) and
      self.lead_depart_release_candidate_elapsed >= LEAD_DEPART_RELEASE_HOLD_CONFIRM_TIME
    ):
      self.lead_depart_release_hold_remaining = LEAD_DEPART_RELEASE_HOLD_TIME
      self.lead_depart_release_pending = False
      depart_release_hold_active = True
    elif bool(output_should_stop) and self.lead_depart_release_hold_remaining <= 0.0:
      self.lead_depart_release_pending = False

    if depart_release_hold_active:
      vision_low_speed_stop_active = False
      output_should_stop = False
      self.post_departure_follow_settle_until = now_t + POST_DEPARTURE_FOLLOW_SETTLE_LATCH_TIME

    if lead_control_active and lead_depart_ready and not depart_safety_veto and not output_should_stop and float(sm['carState'].vEgo) <= STANDSTILL_LEAD_DEPART_MAX_EGO_SPEED:
      output_a_target = max(output_a_target, STANDSTILL_LEAD_DEPART_MIN_ACCEL)
      self.post_departure_follow_settle_until = now_t + POST_DEPARTURE_FOLLOW_SETTLE_LATCH_TIME

    if radar_gap_settle_active:
      vision_low_speed_stop_active = False
      output_should_stop = False
      output_a_target = RADAR_STANDSTILL_GAP_SETTLE_ACCEL

    lead_present = any(bool(getattr(lead, "status", False)) for lead in (self.lead_one, self.lead_two))
    confirmed_lead_release = bool(confident_depart_ready or lead_depart_ready or slow_creep_depart_ready)
    model_launch_allowed = bool(
      model_launch_accel is not None and
      not output_should_stop and
      not vision_low_speed_stop_active and
      not bool(getattr(sm['carState'], 'brakePressed', False)) and
      not bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) and
      not bool(getattr(sm['starpilotPlan'], 'redLight', False)) and
      not depart_safety_veto and
      (
        (lead_present and lead_control_active and confirmed_lead_release) or
        (not lead_present and (self.mode != 'acc' or self.model_launch_stop_seen))
      )
    )
    if model_launch_allowed:
      output_a_target = max(output_a_target, model_launch_accel)

    if depart_safety_veto or output_should_stop or bool(getattr(sm['starpilotPlan'], 'forcingStop', False)) or bool(getattr(sm['starpilotPlan'], 'redLight', False)):
      self.lead_depart_accel_hold_until = 0.0
      self.lead_depart_accel_hold_floor = None

    lead_depart_accel_floor = None
    lead_depart_accel_floor_reused = False
    if lead_control_active and not output_should_stop and not depart_safety_veto:
      lead_depart_accel_floors = [
        floor for floor in (
          self.get_lead_depart_accel_floor(self.lead_one, scene_v_ego, model_desired_accel),
          self.get_lead_depart_accel_floor(self.lead_two, scene_v_ego, model_desired_accel),
        ) if floor is not None
      ]
      if lead_depart_accel_floors:
        lead_depart_accel_floor = max(lead_depart_accel_floors)
        self.lead_depart_accel_hold_floor = lead_depart_accel_floor
        if sm['carState'].standstill:
          self.lead_depart_accel_hold_until = now_t + LEAD_DEPART_ACCEL_HOLD_TIME
      elif self.lead_depart_accel_hold_floor is not None and now_t < self.lead_depart_accel_hold_until:
        reusable_hold_floors = [
          floor for floor in (
            self.get_reusable_lead_depart_accel_floor(self.lead_one, scene_v_ego, effective_t_follow),
            self.get_reusable_lead_depart_accel_floor(self.lead_two, scene_v_ego, effective_t_follow),
          ) if floor is not None
        ]
        if reusable_hold_floors:
          lead_depart_accel_floor = max(reusable_hold_floors)
          lead_depart_accel_floor_reused = True
        else:
          self.lead_depart_accel_hold_floor = None
      elif now_t >= self.lead_depart_accel_hold_until:
        self.lead_depart_accel_hold_floor = None

    lead_depart_accel_hold_active = (
      lead_depart_accel_floor is not None and
      now_t < self.lead_depart_accel_hold_until and
      float(sm['carState'].vEgo) <= LEAD_DEPART_ACCEL_HOLD_MAX_EGO_SPEED
    )

    low_speed_weak_lead_accel_cap = None
    if not output_should_stop:
      low_speed_weak_lead_accel_caps = [
        cap for cap in (
          self.get_low_speed_weak_lead_accel_cap(self.lead_one, scene_v_ego),
          self.get_low_speed_weak_lead_accel_cap(self.lead_two, scene_v_ego),
        ) if cap is not None
      ]
      if low_speed_weak_lead_accel_caps:
        low_speed_weak_lead_accel_cap = min(low_speed_weak_lead_accel_caps)

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

    if lead_control_active and np.isfinite(v_cruise) and any(lead.status for lead in (self.lead_one, self.lead_two)):
      # This is only an acceleration cap. A negative cap would manufacture hard
      # braking on abrupt cruise-target drops instead of letting the MPC decelerate.
      cruise_accel_cap = max(0.0, (v_cruise - v_ego + 0.01) / max(action_t, self.dt))
      output_a_target = min(output_a_target, cruise_accel_cap)

    if vision_brake_cap_active:
      output_accel_min = min(output_accel_min, vision_cap_accel_min)

    policy_lead = self.lead_two if self.mpc.source == "lead1" else self.lead_one
    post_departure_active = self.post_departure_follow_settle_active(
      policy_lead, scene_v_ego, effective_t_follow,
    )
    # The RAV4's post-departure path used to bypass the ordinary follow cap for
    # the entire settle latch. When a slow lead changed lanes, that let the
    # cruise branch request full acceleration before the next lead was stable.
    # Keep the normal catch-up cap on this car; urgent braking remains outside
    # this comfort policy and is still allowed through unchanged.
    post_departure_bypass = post_departure_active and not is_toyota_rav4_tss2_post_departure_tune(self.CP)
    follow_result = apply_follow_policy(
      self.lead_one,
      self.lead_two,
      source=self.mpc.source,
      active=lead_control_active,
      v_ego=scene_v_ego,
      t_follow=effective_t_follow,
      previous_target=prev_output_a_target,
      raw_target=output_a_target,
      tracking=tracking_lead,
      post_departure=post_departure_bypass,
      blocked=bool(output_should_stop or vision_low_speed_stop_active or close_lead_caps),
      panic_bypass=panic_bypass,
    )
    comfort_follow_lead = follow_result.lead
    comfort_lead = follow_result.lead
    if follow_result.target < output_a_target:
      self.a_desired = min(self.a_desired, follow_result.target)
    else:
      self.a_desired = max(self.a_desired, follow_result.target)
    output_a_target = follow_result.target

    # Model-backed braking remains outside the ordinary follow policy. These
    # floors are safety responses, not comfort arbitration.
    if comfort_follow_lead is not None and not panic_bypass and not output_should_stop and not vision_low_speed_stop_active:
      tracked_vision_model_brake_floor = self.get_tracked_vision_model_brake_floor(
        comfort_follow_lead, scene_v_ego, output_accel_min, effective_t_follow, model_desired_accel,
      )
      if tracked_vision_model_brake_floor is not None:
        self.a_desired = min(self.a_desired, tracked_vision_model_brake_floor)
        output_a_target = min(output_a_target, tracked_vision_model_brake_floor)

    if comfort_follow_lead is not None and not panic_bypass and not output_should_stop and not vision_low_speed_stop_active:
      tracked_vision_model_brake_cap = self.get_tracked_vision_model_brake_cap(
        comfort_follow_lead, scene_v_ego, effective_t_follow, model_desired_accel,
      )
      if tracked_vision_model_brake_cap is not None:
        self.a_desired = max(self.a_desired, tracked_vision_model_brake_cap)
        output_a_target = max(output_a_target, tracked_vision_model_brake_cap)

    output_accel_max = no_throttle_output_max if not self.allow_throttle else accel_limits_turns[1]
    output_a_target = float(np.clip(output_a_target, output_accel_min, output_accel_max))

    if close_stop_hold_cap is not None:
      self.a_desired = min(self.a_desired, close_stop_hold_cap)
      output_a_target = min(output_a_target, close_stop_hold_cap)

    if standstill_stopped_lead_guard_cap is not None:
      self.a_desired = min(self.a_desired, standstill_stopped_lead_guard_cap)
      output_a_target = min(output_a_target, standstill_stopped_lead_guard_cap)

    if close_settle_cap is not None:
      self.a_desired = min(self.a_desired, close_settle_cap)
      output_a_target = min(output_a_target, close_settle_cap)

    if close_final_guard_cap is not None:
      self.a_desired = min(self.a_desired, close_final_guard_cap)
      output_a_target = min(output_a_target, close_final_guard_cap)

    if rav4_early_lead_caps:
      rav4_early_lead_cap = min(rav4_early_lead_caps)
      self.a_desired = min(self.a_desired, rav4_early_lead_cap)
      output_a_target = min(output_a_target, rav4_early_lead_cap)

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

    if low_speed_weak_lead_accel_cap is not None and not (lead_depart_accel_hold_active and lead_depart_accel_floor_reused):
      self.a_desired = min(self.a_desired, low_speed_weak_lead_accel_cap)
      output_a_target = min(output_a_target, low_speed_weak_lead_accel_cap)

    if (
      lead_control_active and
      (bool(sm['carState'].standstill) or float(sm['carState'].vEgo) <= STANDSTILL_STOPPED_LEAD_GUARD_MAX_EGO_SPEED) and
      output_should_stop and
      accelerating_nudge_lead and
      not depart_safety_veto
    ):
      output_a_target = max(output_a_target, STANDSTILL_LEAD_NUDGE_ACCEL)

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

    inside_gap_closing_cap = None
    if lead_control_active:
      inside_gap_closing_lead = self.lead_two if self.mpc.source == 'lead1' else self.lead_one
      inside_gap_closing_cap = self.get_inside_gap_closing_lead_accel_cap(
        inside_gap_closing_lead,
        scene_v_ego,
        output_accel_min,
        sm['starpilotPlan'].tFollow,
      )
    if inside_gap_closing_cap is not None:
      self.a_desired = min(self.a_desired, inside_gap_closing_cap)
      output_a_target = min(output_a_target, inside_gap_closing_cap)

    experimental_release_accel_target = self.get_experimental_release_accel_target(
      comfort_follow_lead,
      scene_v_ego,
      effective_t_follow,
      prev_output_a_target,
      output_a_target,
      bool(
        now_t < self.experimental_release_accel_until and
        not output_should_stop and
        not vision_low_speed_stop_active and
        not getattr(sm['starpilotPlan'], 'forcingStop', False) and
        not getattr(sm['starpilotPlan'], 'redLight', False)
      ),
    )
    if experimental_release_accel_target is not None:
      self.a_desired = min(self.a_desired, experimental_release_accel_target)
      output_a_target = min(output_a_target, experimental_release_accel_target)

    if depart_release_hold_active:
      output_a_target = max(output_a_target, STANDSTILL_LEAD_CREEP_RELEASE_MIN_ACCEL)

    output_a_target = self.get_vehicle_far_follow_slew_target(
      scene_v_ego,
      prev_output_a_target,
      output_a_target,
      bool(output_should_stop or vision_low_speed_stop_active),
      panic_bypass,
    )

    if radar_gap_settle_active:
      output_a_target = RADAR_STANDSTILL_GAP_SETTLE_ACCEL
      output_should_stop = False

    sienna_restop_caps = [
      cap for cap in (
        get_toyota_sienna_post_departure_restop_cap(
          self.CP, self.lead_one, scene_v_ego, output_accel_min,
          standstill_nudge_gap, now_t, self.post_departure_follow_settle_until,
        ),
        get_toyota_sienna_post_departure_restop_cap(
          self.CP, self.lead_two, scene_v_ego, output_accel_min,
          standstill_nudge_gap, now_t, self.post_departure_follow_settle_until,
        ),
      ) if cap is not None
    ]
    if sienna_restop_caps:
      sienna_restop_cap = min(sienna_restop_caps)
      self.a_desired = min(self.a_desired, sienna_restop_cap)
      output_a_target = min(output_a_target, sienna_restop_cap)
      output_should_stop = True

    lc_merge_floor = self.get_lane_change_merge_accel_floor(
      sm, starpilot_toggles, scene_v_ego, v_cruise, action_t,
      blocked=bool(
        output_should_stop or vision_low_speed_stop_active or depart_safety_veto or
        getattr(sm['starpilotPlan'], 'forcingStop', False) or
        getattr(sm['starpilotPlan'], 'redLight', False)
      ),
    )
    if lc_merge_floor is not None:
      output_a_target = float(min(max(output_a_target, lc_merge_floor), output_accel_max))
      self.a_desired = max(self.a_desired, min(lc_merge_floor, output_accel_max))

    # Force-decel is the driver-monitoring no-response path. Keep a small
    # braking floor until the vehicle is actually stopped; normal MPC tapering
    # can otherwise leave it creeping indefinitely at the maneuver-test cutoff.
    if force_slow_decel and scene_v_ego > 0.1:
      output_a_target = min(output_a_target, FORCE_DECEL_MIN_ACCEL)

    try:
      starpilot_car_state = sm['starpilotCarState']
    except KeyError:
      starpilot_car_state = None
    driver_accel_pressed = bool(
      getattr(sm['carState'], 'gasPressed', False) or
      getattr(starpilot_car_state, 'accelPressed', False)
    )
    accord_stop_go_blocked = bool(
      not lead_control_active or
      output_should_stop or
      vision_low_speed_stop_active or
      depart_safety_veto or
      radar_gap_settle_active or
      getattr(sm['starpilotPlan'], 'forcingStop', False) or
      getattr(sm['starpilotPlan'], 'redLight', False) or
      driver_accel_pressed
    )
    accord_stop_go_target = self.get_honda_accord_stop_go_accel_target(
      policy_lead, scene_v_ego, prev_output_a_target, output_a_target, accord_stop_go_blocked,
    )
    if accord_stop_go_target < output_a_target:
      self.a_desired = min(self.a_desired, accord_stop_go_target)
      output_a_target = accord_stop_go_target

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

    # LongControl needs to know about whichever lead MPC is following. Using
    # leadOne only leaves the stop-release guard blind when source=lead1.
    selected_lead = sm['radarState'].leadTwo if self.mpc.source == "lead1" else sm['radarState'].leadOne
    longitudinalPlan.hasLead = bool(selected_lead.status)
    longitudinalPlan.longitudinalPlanSource = self.mpc.source
    longitudinalPlan.fcw = self.fcw

    longitudinalPlan.leadTrajectoryX0 = self.mpc.lead_xv_0[:, 0].tolist()
    longitudinalPlan.leadTrajectoryV0 = self.mpc.lead_xv_0[:, 1].tolist()
    longitudinalPlan.leadTrajectoryX1 = self.mpc.lead_xv_1[:, 0].tolist()
    longitudinalPlan.leadTrajectoryV1 = self.mpc.lead_xv_1[:, 1].tolist()

    longitudinalPlan.aTarget = float(self.output_a_target)
    force_stop_handoff = bool(
      sm['starpilotPlan'].forcingStop and (
        sm['starpilotPlan'].forcingStopLength < 1.0 or
        sm['starpilotPlan'].vCruise <= FORCE_STOP_HANDOFF_MAX_VCRUISE
      )
    )
    stop_sign_hold_speed = get_stop_sign_low_speed_hold(self.CP)
    stop_sign_low_speed_hold = bool(
      stop_sign_hold_speed is not None and
      bool(getattr(sm['starpilotPlan'], 'stopSignConfirmed', False)) and
      float(getattr(sm['carState'], 'vEgo', 0.0)) <= stop_sign_hold_speed and
      not bool(getattr(sm['carState'], 'gasPressed', False))
    )
    longitudinalPlan.shouldStop = bool(self.output_should_stop) or force_stop_handoff or stop_sign_low_speed_hold
    longitudinalPlan.allowBrake = True
    longitudinalPlan.allowThrottle = bool(self.allow_throttle)

    pm.send('longitudinalPlan', plan_send)
