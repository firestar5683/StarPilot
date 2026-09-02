#!/usr/bin/env python3
import numpy as np

from cereal import log
from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.controls.lib.lead_behavior import should_disable_far_lead_throttle
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import COMFORT_BRAKE, LEAD_DANGER_FACTOR, desired_follow_distance, get_jerk_factor, get_T_FOLLOW

from openpilot.starpilot.common.starpilot_variables import CITY_SPEED_LIMIT, MAX_T_FOLLOW

TRAFFIC_MODE_BP = [0., CITY_SPEED_LIMIT]
PERSONALITY_BP = [45. * CV.MPH_TO_MS, 70. * CV.MPH_TO_MS]

LaneChangeState = log.LaneChangeState
LaneChangeDirection = log.LaneChangeDirection

# Lane-change close-gap transition: while signalling out of the lane, temporarily
# hold a shorter follow distance so openpilot merges out smoothly and can accelerate
# through the maneuver instead of braking behind a lead it is about to leave.
# Ramps in gradually, snaps back to the normal gap when the safety gate trips.
LANE_CHANGE_MIN_T_FOLLOW = 0.25            # hard floor on the reduced gap (s)
LANE_CHANGE_GAP_RAMP_IN_RATE = 0.6         # seconds of headway per second, toward the shorter gap
LANE_CHANGE_GAP_RAMP_OUT_RATE = 4.0        # seconds of headway per second, back to the normal gap
LANE_CHANGE_ABORT_LEAD_BRAKE = 0.8         # lead decel that aborts the reduction (m/s^2)

LANE_CHANGE_ACTIVE_STATES = (
  LaneChangeState.preLaneChange,
  LaneChangeState.laneChangeStarting,
  LaneChangeState.laneChangeFinishing,
)


def get_longitudinal_personality(sm):
  return sm["selfdriveState"].personality

class StarPilotFollowing:
  def __init__(self, StarPilotPlanner):
    self.starpilot_planner = StarPilotPlanner

    self.disable_throttle = False
    self.following_lead = False
    self.slower_lead = False

    self.acceleration_jerk = 0
    self.danger_jerk = 0
    self.desired_follow_distance = 0
    self.speed_jerk = 0
    self.t_follow = 0

    # Rate-limited lane-change follow distance (s). None until the first reduction.
    self.lane_change_t_follow = None

  def update(self, long_control_active, v_ego, sm, starpilot_toggles):
    personality = get_longitudinal_personality(sm)

    if long_control_active and sm["starpilotCarState"].trafficModeEnabled:
      if sm["carState"].aEgo >= 0:
        self.base_acceleration_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, starpilot_toggles.traffic_mode_jerk_acceleration)
        self.base_speed_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, starpilot_toggles.traffic_mode_jerk_speed)
      else:
        self.base_acceleration_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, starpilot_toggles.traffic_mode_jerk_deceleration)
        self.base_speed_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, starpilot_toggles.traffic_mode_jerk_speed_decrease)

      self.base_danger_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, starpilot_toggles.traffic_mode_jerk_danger)
      self.t_follow = np.interp(v_ego, TRAFFIC_MODE_BP, starpilot_toggles.traffic_mode_follow)
    elif long_control_active:
      if sm["carState"].aEgo >= 0:
        self.base_acceleration_jerk, self.base_danger_jerk, self.base_speed_jerk = get_jerk_factor(
          starpilot_toggles.aggressive_jerk_acceleration, starpilot_toggles.aggressive_jerk_danger, starpilot_toggles.aggressive_jerk_speed,
          starpilot_toggles.standard_jerk_acceleration, starpilot_toggles.standard_jerk_danger, starpilot_toggles.standard_jerk_speed,
          starpilot_toggles.relaxed_jerk_acceleration, starpilot_toggles.relaxed_jerk_danger, starpilot_toggles.relaxed_jerk_speed,
          starpilot_toggles.custom_personalities, personality
        )
      else:
        self.base_acceleration_jerk, self.base_danger_jerk, self.base_speed_jerk = get_jerk_factor(
          starpilot_toggles.aggressive_jerk_deceleration, starpilot_toggles.aggressive_jerk_danger, starpilot_toggles.aggressive_jerk_speed_decrease,
          starpilot_toggles.standard_jerk_deceleration, starpilot_toggles.standard_jerk_danger, starpilot_toggles.standard_jerk_speed_decrease,
          starpilot_toggles.relaxed_jerk_deceleration, starpilot_toggles.relaxed_jerk_danger, starpilot_toggles.relaxed_jerk_speed_decrease,
          starpilot_toggles.custom_personalities, personality
        )

      self.t_follow = get_T_FOLLOW(
        starpilot_toggles.aggressive_follow,
        starpilot_toggles.standard_follow,
        starpilot_toggles.relaxed_follow,
        starpilot_toggles.custom_personalities, personality
      )
      if isinstance(self.t_follow, (list, tuple)):
        self.t_follow = float(np.interp(v_ego, PERSONALITY_BP, self.t_follow))
      else:
        self.t_follow = float(self.t_follow)
    else:
      self.base_acceleration_jerk = 0
      self.base_danger_jerk = 0
      self.base_speed_jerk = 0
      self.t_follow = 0

    self.acceleration_jerk = self.base_acceleration_jerk
    self.danger_factor = LEAD_DANGER_FACTOR
    self.danger_jerk = self.base_danger_jerk
    self.speed_jerk = self.base_speed_jerk

    self.slower_lead = False

    if self.starpilot_planner.starpilot_weather.weather_id != 0:
      self.t_follow = min(self.t_follow + self.starpilot_planner.starpilot_weather.increase_following_distance, MAX_T_FOLLOW)

    self.update_lane_change_gap(long_control_active, v_ego, sm, starpilot_toggles)

    # After t_follow adjustments so CEM and the published tFollow use the same window.
    self.following_lead = self.starpilot_planner.tracking_lead and self.starpilot_planner.lead_one.dRel < (self.t_follow * 2) * v_ego

    self.disable_throttle = False
    if self.starpilot_planner.tracking_lead and self.starpilot_planner.lead_one.status:
      lead_distance = self.starpilot_planner.lead_one.dRel
      v_lead = self.starpilot_planner.lead_one.vLead
      closing_speed = max(0.0, v_ego - v_lead)
      desired_gap = float(desired_follow_distance(v_ego, v_lead, self.t_follow))
      self.disable_throttle = should_disable_far_lead_throttle(v_ego, lead_distance, desired_gap, closing_speed, self.following_lead)

    if long_control_active and self.starpilot_planner.tracking_lead:
      self.update_follow_values(self.starpilot_planner.lead_one.dRel, v_ego, self.starpilot_planner.lead_one.vLead, starpilot_toggles)
      self.desired_follow_distance = int(desired_follow_distance(v_ego, self.starpilot_planner.lead_one.vLead, self.t_follow))
    else:
      self.desired_follow_distance = 0

  def update_lane_change_gap(self, long_control_active, v_ego, sm, starpilot_toggles):
    # Hold a shorter follow distance while signalling out of the lane so openpilot
    # merges out smoothly and can accelerate through the maneuver, instead of braking
    # behind a lead it is about to leave. The target is an absolute headway that can
    # only ever shorten the current gap, never lengthen it.
    if not long_control_active:
      self.lane_change_t_follow = None
      return

    target = self.t_follow

    if getattr(starpilot_toggles, "lane_change_close_gap", False):
      meta = sm["modelV2"].meta
      lane_change_active = meta.laneChangeState in LANE_CHANGE_ACTIVE_STATES

      if lane_change_active and self.lane_change_gap_safe(v_ego, sm, meta.laneChangeDirection, starpilot_toggles):
        requested = float(np.clip(starpilot_toggles.lane_change_close_gap_seconds, LANE_CHANGE_MIN_T_FOLLOW, MAX_T_FOLLOW))
        # Absolute cap: only apply when it is actually shorter than the normal gap.
        target = min(self.t_follow, requested)

    if self.lane_change_t_follow is None:
      self.lane_change_t_follow = self.t_follow

    rate = LANE_CHANGE_GAP_RAMP_IN_RATE if target < self.lane_change_t_follow else LANE_CHANGE_GAP_RAMP_OUT_RATE
    step = rate * DT_MDL
    self.lane_change_t_follow = float(np.clip(target,
                                              self.lane_change_t_follow - step,
                                              self.lane_change_t_follow + step))

    # Never let the ramp raise the gap above what the rest of the stack asked for.
    self.t_follow = min(self.t_follow, max(self.lane_change_t_follow, LANE_CHANGE_MIN_T_FOLLOW))

  def lane_change_gap_safe(self, v_ego, sm, direction, starpilot_toggles):
    CS = sm["carState"]
    if CS.standstill or v_ego < starpilot_toggles.minimum_lane_change_speed:
      return False

    # Do not close the gap toward an occupied blindspot on the lane-change side.
    if (direction == LaneChangeDirection.left and CS.leftBlindspot) or \
       (direction == LaneChangeDirection.right and CS.rightBlindspot):
      return False

    lead = self.starpilot_planner.lead_one
    if self.starpilot_planner.tracking_lead and lead.status:
      if max(0.0, -float(lead.aLeadK)) >= LANE_CHANGE_ABORT_LEAD_BRAKE:
        return False

    return True

  def update_follow_values(self, lead_distance, v_ego, v_lead, starpilot_toggles):
    if starpilot_toggles.conditional_slower_lead and v_lead < v_ego:
      distance_factor = max(lead_distance - (v_lead * self.t_follow), 1)
      braking_offset = float(np.clip(min(v_ego - v_lead, v_lead) - COMFORT_BRAKE, 1, distance_factor))
      self.slower_lead = braking_offset > 1
