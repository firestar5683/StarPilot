#!/usr/bin/env python3
import numpy as np

from openpilot.common.constants import CV
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import COMFORT_BRAKE, LEAD_DANGER_FACTOR, STOP_DISTANCE, desired_follow_distance, get_jerk_factor, get_T_FOLLOW

from openpilot.frogpilot.common.frogpilot_variables import CITY_SPEED_LIMIT, MAX_T_FOLLOW

TRAFFIC_MODE_BP = [0., CITY_SPEED_LIMIT]
PERSONALITY_BP = [45. * CV.MPH_TO_MS, 70. * CV.MPH_TO_MS]
HIGHWAY_DISABLE_THROTTLE_MIN_SPEED = 45. * CV.MPH_TO_MS

class FrogPilotFollowing:
  def __init__(self, FrogPilotPlanner):
    self.frogpilot_planner = FrogPilotPlanner

    self.disable_throttle = False
    self.following_lead = False
    self.slower_lead = False

    self.acceleration_jerk = 0
    self.danger_jerk = 0
    self.desired_follow_distance = 0
    self.speed_jerk = 0
    self.t_follow = 0

  def update(self, long_control_active, v_ego, sm, frogpilot_toggles):
    stop_distance = max(float(getattr(frogpilot_toggles, "stop_distance", STOP_DISTANCE)), 4.0)

    if long_control_active and sm["frogpilotCarState"].trafficModeEnabled:
      if sm["carState"].aEgo >= 0:
        self.base_acceleration_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, frogpilot_toggles.traffic_mode_jerk_acceleration)
        self.base_speed_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, frogpilot_toggles.traffic_mode_jerk_speed)
      else:
        self.base_acceleration_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, frogpilot_toggles.traffic_mode_jerk_deceleration)
        self.base_speed_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, frogpilot_toggles.traffic_mode_jerk_speed_decrease)

      self.base_danger_jerk = np.interp(v_ego, TRAFFIC_MODE_BP, frogpilot_toggles.traffic_mode_jerk_danger)
      self.t_follow = np.interp(v_ego, TRAFFIC_MODE_BP, frogpilot_toggles.traffic_mode_follow)
    elif long_control_active:
      if sm["carState"].aEgo >= 0:
        self.base_acceleration_jerk, self.base_danger_jerk, self.base_speed_jerk = get_jerk_factor(
          frogpilot_toggles.aggressive_jerk_acceleration, frogpilot_toggles.aggressive_jerk_danger, frogpilot_toggles.aggressive_jerk_speed,
          frogpilot_toggles.standard_jerk_acceleration, frogpilot_toggles.standard_jerk_danger, frogpilot_toggles.standard_jerk_speed,
          frogpilot_toggles.relaxed_jerk_acceleration, frogpilot_toggles.relaxed_jerk_danger, frogpilot_toggles.relaxed_jerk_speed,
          frogpilot_toggles.custom_personalities, sm["selfdriveState"].personality
        )
      else:
        self.base_acceleration_jerk, self.base_danger_jerk, self.base_speed_jerk = get_jerk_factor(
          frogpilot_toggles.aggressive_jerk_deceleration, frogpilot_toggles.aggressive_jerk_danger, frogpilot_toggles.aggressive_jerk_speed_decrease,
          frogpilot_toggles.standard_jerk_deceleration, frogpilot_toggles.standard_jerk_danger, frogpilot_toggles.standard_jerk_speed_decrease,
          frogpilot_toggles.relaxed_jerk_deceleration, frogpilot_toggles.relaxed_jerk_danger, frogpilot_toggles.relaxed_jerk_speed_decrease,
          frogpilot_toggles.custom_personalities, sm["selfdriveState"].personality
        )

      self.t_follow = get_T_FOLLOW(
        frogpilot_toggles.aggressive_follow,
        frogpilot_toggles.standard_follow,
        frogpilot_toggles.relaxed_follow,
        frogpilot_toggles.custom_personalities, sm["selfdriveState"].personality
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

    self.following_lead = self.frogpilot_planner.tracking_lead and self.frogpilot_planner.lead_one.dRel < (self.t_follow * 2) * v_ego
    self.slower_lead = False

    if self.frogpilot_planner.frogpilot_weather.weather_id != 0:
      self.t_follow = min(self.t_follow + self.frogpilot_planner.frogpilot_weather.increase_following_distance, MAX_T_FOLLOW)

    self.disable_throttle = False
    if self.frogpilot_planner.tracking_lead and self.frogpilot_planner.lead_one.status:
      lead_distance = self.frogpilot_planner.lead_one.dRel
      v_lead = self.frogpilot_planner.lead_one.vLead
      closing_speed = max(0.0, v_ego - v_lead)
      desired_gap = float(desired_follow_distance(v_ego, v_lead, self.t_follow, stop_distance))
      ttc = lead_distance / max(closing_speed, 1e-3) if closing_speed > 0.1 else 1e6

      coast_window_open = lead_distance > desired_gap + max(4.0, 0.2 * v_ego)
      coast_window_far = lead_distance < desired_gap + max(25.0, 1.2 * v_ego)
      gentle_closing = closing_speed < max(2.0, 0.12 * v_ego)
      self.disable_throttle = (not self.following_lead and v_ego > HIGHWAY_DISABLE_THROTTLE_MIN_SPEED and coast_window_open and
                               coast_window_far and gentle_closing)
      self.disable_throttle &= ttc > 6.0 and lead_distance > desired_gap + 6.0

    if long_control_active and self.frogpilot_planner.tracking_lead:
      if not sm["frogpilotCarState"].trafficModeEnabled:
        self.update_follow_values(self.frogpilot_planner.lead_one.dRel, v_ego, self.frogpilot_planner.lead_one.vLead, frogpilot_toggles)
      self.desired_follow_distance = int(desired_follow_distance(v_ego, self.frogpilot_planner.lead_one.vLead, self.t_follow, stop_distance))
    else:
      self.desired_follow_distance = 0

  def update_follow_values(self, lead_distance, v_ego, v_lead, frogpilot_toggles):
    stop_distance = max(float(getattr(frogpilot_toggles, "stop_distance", STOP_DISTANCE)), 4.0)

    # Offset by FrogAi for FrogPilot for a more natural approach to a faster lead
    if frogpilot_toggles.human_following and v_lead > v_ego:
      distance_factor = max(lead_distance - (v_ego * self.t_follow), 1)
      acceleration_offset = np.clip(stop_distance - v_ego, 1, distance_factor)
      self.acceleration_jerk /= acceleration_offset
      self.speed_jerk /= acceleration_offset
      self.t_follow /= acceleration_offset

    # Offset by FrogAi for FrogPilot for a more natural approach to a slower lead
    if (frogpilot_toggles.conditional_slower_lead or frogpilot_toggles.human_following) and v_lead < v_ego:
      distance_factor = max(lead_distance - (v_lead * self.t_follow), 1)
      braking_offset = np.clip(min(v_ego - v_lead, v_lead) - COMFORT_BRAKE, 1, distance_factor)

      if frogpilot_toggles.human_following:
        far_lead_offset = max(lead_distance - (v_ego * self.t_follow) - stop_distance, 0)
        self.t_follow /= braking_offset + far_lead_offset
      else:
        self.t_follow /= braking_offset

      self.slower_lead = braking_offset > 1
