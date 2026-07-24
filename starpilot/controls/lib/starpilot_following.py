#!/usr/bin/env python3
import numpy as np

from openpilot.common.constants import CV
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import LEAD_DANGER_FACTOR, desired_follow_distance, get_jerk_factor, get_T_FOLLOW

from openpilot.starpilot.common.starpilot_variables import CITY_SPEED_LIMIT, MAX_T_FOLLOW

TRAFFIC_MODE_BP = [0., CITY_SPEED_LIMIT]
PERSONALITY_BP = [45. * CV.MPH_TO_MS, 70. * CV.MPH_TO_MS]


def get_longitudinal_personality(sm):
  return sm["selfdriveState"].personality

class StarPilotFollowing:
  def __init__(self, StarPilotPlanner):
    self.starpilot_planner = StarPilotPlanner

    self.acceleration_jerk = 0
    self.danger_jerk = 0
    self.desired_follow_distance = 0
    self.speed_jerk = 0
    self.t_follow = 0

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

    if self.starpilot_planner.starpilot_weather.weather_id != 0:
      self.t_follow = min(self.t_follow + self.starpilot_planner.starpilot_weather.increase_following_distance, MAX_T_FOLLOW)

    if long_control_active and self.starpilot_planner.tracking_lead:
      self.desired_follow_distance = int(desired_follow_distance(v_ego, self.starpilot_planner.lead_one.vLead, self.t_follow))
    else:
      self.desired_follow_distance = 0
