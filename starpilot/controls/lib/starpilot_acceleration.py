#!/usr/bin/env python3
import numpy as np

from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.selfdrive.car.cruise import V_CRUISE_MAX, V_CRUISE_UNSET
from openpilot.selfdrive.controls.lib.longitudinal_planner import A_CRUISE_MIN, get_max_accel

from openpilot.starpilot.common.accel_profile import (
  ACCELERATION_PROFILES,
  A_CRUISE_MAX_VALS_TRAFFIC_ALL,
  DECELERATION_PROFILES,
  coerce_custom_accel_profile_values,
  get_accel_profile_curve_values,
  get_max_allowed_accel as get_profile_max_allowed_accel,
  interpolate_accel_profile,
  normalize_deceleration_profile,
)
from openpilot.starpilot.controls.lib.starpilot_vcruise import get_active_slc_control_target

def cubic_interp(x, xp, fp):
     """Cubic interpolation using NumPy's native operations for speed."""
     # Boundary conditions
     if x <= xp[0]:
         return fp[0]
     elif x >= xp[-1]:
         return fp[-1]

     # Find interval
     i = np.searchsorted(xp, x) - 1
     i = max(0, min(i, len(xp)-2))  # clamp the index

     # Normalized position
     t = (x - xp[i]) / float(xp[i+1] - xp[i])

     # Hermite cubic formula
     return fp[i]*(1 - 3*t**2 + 2*t**3) + fp[i+1]*(3*t**2 - 2*t**3)

def akima_interp(x, xp, fp):
     """Akima-inspired interpolation with reduced overshoot characteristics."""
     if x <= xp[0]:
         return fp[0]
     elif x >= xp[-1]:
         return fp[-1]

     i = np.searchsorted(xp, x) - 1
     i = max(0, min(i, len(xp)-2))  # clamp the index

     t = (x - xp[i]) / float(xp[i+1] - xp[i])

     # Quintic polynomial to reduce overshoot
     t2 = t*t
     t4 = t2*t2
     t3 = t2*t
     return (fp[i]*(1 - 10*t3 + 15*t4 - 6*t3*t2)
             + fp[i+1]*(10*t3 - 15*t4 + 6*t3*t2))

A_CRUISE_MIN_ECO = A_CRUISE_MIN / 2
A_CRUISE_MIN_SPORT = A_CRUISE_MIN * 2
A_CRUISE_MIN_TRAFFIC = A_CRUISE_MIN * 0.35  # cruise-decel floor only; MPC lead braking keeps full ACCEL_MIN authority
SLC_COAST_WINDOW_BP = [0.0, 10.0, 20.0, 35.0]
SLC_COAST_WINDOW_BASE = [0.20, 0.40, 0.65, 1.10]
SLC_EXCESS_SCALE_BP = [0.0, 10.0, 20.0, 35.0]
SLC_EXCESS_SCALE_V = [0.8, 1.8, 3.5, 5.5]
SLC_COAST_WINDOW_MULTIPLIER = {
  DECELERATION_PROFILES["ECO"]: 1.20,
  DECELERATION_PROFILES["STANDARD"]: 1.00,
  DECELERATION_PROFILES["SPORT"]: 0.75,
}
SLC_COAST_FLOOR = {
  DECELERATION_PROFILES["ECO"]: -0.02,
  DECELERATION_PROFILES["STANDARD"]: -0.03,
  DECELERATION_PROFILES["SPORT"]: -0.04,
}
SLC_COAST_MIN_SPEED = 4.0
SLC_TARGET_EPS = 0.15
RELEVANT_LEAD_MIN_CLOSING_SPEED = 0.5
RELEVANT_LEAD_MIN_BRAKE = -0.4

def get_max_accel_eco(v_ego, ev_tuning=True, truck_tuning=False):
  return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["ECO"], ev_tuning, truck_tuning))

def get_max_accel_sport(v_ego, ev_tuning=True, truck_tuning=False):
  return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["SPORT"], ev_tuning, truck_tuning))

def get_max_accel_standard(v_ego, ev_tuning=True, truck_tuning=False):
  return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["STANDARD"], ev_tuning, truck_tuning))

def get_max_accel_traffic(v_ego):
  return interpolate_accel_profile(v_ego, A_CRUISE_MAX_VALS_TRAFFIC_ALL)

def get_max_accel_custom(v_ego, custom_curve, acceleration_profile, ev_tuning=True, truck_tuning=False):
  curve_values = coerce_custom_accel_profile_values(custom_curve, acceleration_profile, ev_tuning, truck_tuning)
  return interpolate_accel_profile(v_ego, curve_values)

def get_max_allowed_accel(v_ego, ev_tuning=True, truck_tuning=False):
  return float(get_profile_max_allowed_accel(v_ego, ev_tuning, truck_tuning))

def get_profile_min_accel_floor(deceleration_profile):
  if deceleration_profile == DECELERATION_PROFILES["ECO"]:
    return A_CRUISE_MIN_ECO
  if deceleration_profile == DECELERATION_PROFILES["SPORT"]:
    return A_CRUISE_MIN_SPORT
  return A_CRUISE_MIN

def lead_is_braking_relevant(lead, v_ego):
  if lead is None or not getattr(lead, "status", False):
    return False

  closing_speed = float(v_ego - getattr(lead, "vLead", 0.0))
  if closing_speed > RELEVANT_LEAD_MIN_CLOSING_SPEED:
    return True

  if float(getattr(lead, "aLeadK", 0.0)) < RELEVANT_LEAD_MIN_BRAKE:
    return True

  return float(getattr(lead, "dRel", 1e6)) < max(18.0, 2.0 * float(v_ego))

def get_slc_shaped_min_accel(v_ego, v_target, deceleration_profile, full_brake_floor):
  profile = DECELERATION_PROFILES["STANDARD"] if deceleration_profile is None else deceleration_profile
  coast_floor = SLC_COAST_FLOOR.get(profile, SLC_COAST_FLOOR[DECELERATION_PROFILES["STANDARD"]])
  coast_window = float(akima_interp(v_ego, SLC_COAST_WINDOW_BP, SLC_COAST_WINDOW_BASE))
  coast_window *= SLC_COAST_WINDOW_MULTIPLIER.get(profile, 1.0)
  excess_scale = float(akima_interp(v_ego, SLC_EXCESS_SCALE_BP, SLC_EXCESS_SCALE_V))
  excess_scale = max(excess_scale, coast_window + 0.1)

  excess = max(0.0, float(v_ego) - float(v_target))
  if excess <= coast_window:
    return coast_floor

  t = float(np.clip((excess - coast_window) / (excess_scale - coast_window), 0.0, 1.0)) ** 2
  return coast_floor + t * (full_brake_floor - coast_floor)

class StarPilotAcceleration:
  def __init__(self, StarPilotPlanner):
    self.starpilot_planner = StarPilotPlanner
    self.params = Params()

    self.max_accel = 0
    self.min_accel = 0

    self.last_gear_state = "init"

  def update(self, v_ego, sm, starpilot_toggles):
    eco_gear = sm["starpilotCarState"].ecoGear
    sport_gear = sm["starpilotCarState"].sportGear
    ev_tuning = getattr(starpilot_toggles, "ev_tuning", True)
    truck_tuning = getattr(starpilot_toggles, "truck_tuning", False)
    custom_accel_profile = getattr(starpilot_toggles, "custom_accel_profile", False)
    custom_accel_profile_values = getattr(starpilot_toggles, "custom_accel_profile_values", [])
    deceleration_profile = normalize_deceleration_profile(
      getattr(starpilot_toggles, "deceleration_profile", DECELERATION_PROFILES["STANDARD"])
    )

    if sm["starpilotCarState"].trafficModeEnabled:
      self.max_accel = get_max_accel_traffic(v_ego)
    elif custom_accel_profile:
      self.max_accel = get_max_accel_custom(v_ego, custom_accel_profile_values, starpilot_toggles.acceleration_profile, ev_tuning, truck_tuning)
    elif starpilot_toggles.map_acceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.max_accel = get_max_accel_eco(v_ego, ev_tuning, truck_tuning)
      else:
        self.max_accel = get_max_allowed_accel(v_ego, ev_tuning, truck_tuning)
    else:
      if starpilot_toggles.acceleration_profile == ACCELERATION_PROFILES["ECO"]:
        self.max_accel = get_max_accel_eco(v_ego, ev_tuning, truck_tuning)
      elif starpilot_toggles.acceleration_profile == ACCELERATION_PROFILES["SPORT"]:
        self.max_accel = get_max_accel_sport(v_ego, ev_tuning, truck_tuning)
      elif starpilot_toggles.acceleration_profile == ACCELERATION_PROFILES["SPORT_PLUS"]:
        self.max_accel = get_max_allowed_accel(v_ego, ev_tuning, truck_tuning)
      else:
        self.max_accel = get_max_accel_standard(v_ego, ev_tuning, truck_tuning)

    if self.starpilot_planner.starpilot_weather.weather_id != 0:
      self.max_accel -= self.max_accel * self.starpilot_planner.starpilot_weather.reduce_acceleration

    if sm["starpilotCarState"].forceCoast:
      self.min_accel = A_CRUISE_MIN_ECO
    elif sm["starpilotCarState"].trafficModeEnabled:
      self.min_accel = A_CRUISE_MIN_TRAFFIC
    elif starpilot_toggles.map_deceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.min_accel = A_CRUISE_MIN_ECO
      else:
        self.min_accel = A_CRUISE_MIN_SPORT
    else:
      self.min_accel = get_profile_min_accel_floor(deceleration_profile)

      raw_v_cruise_kph = 0.0 if sm["carState"].vCruise == V_CRUISE_UNSET else min(sm["carState"].vCruise, V_CRUISE_MAX)
      if 0 < raw_v_cruise_kph < V_CRUISE_UNSET and getattr(starpilot_toggles, "set_speed_offset", 0) > 0:
        raw_v_cruise_kph += starpilot_toggles.set_speed_offset
      raw_v_cruise = raw_v_cruise_kph * CV.KPH_TO_MS

      v_ego_cluster = getattr(sm["carState"], "vEgoCluster", v_ego)
      if v_ego_cluster is None:
        v_ego_cluster = v_ego
      v_ego_cluster = max(v_ego_cluster, v_ego)
      v_ego_diff = v_ego_cluster - v_ego
      effective_slc_target = get_active_slc_control_target(
        getattr(starpilot_toggles, "speed_limit_controller", False),
        getattr(starpilot_toggles, "set_speed_limit", False),
        getattr(self.starpilot_planner.starpilot_vcruise, "slc_target", 0.0),
        getattr(self.starpilot_planner.starpilot_vcruise, "slc_offset", 0.0),
        getattr(getattr(self.starpilot_planner.starpilot_vcruise, "slc", None), "overridden_speed", 0.0),
        v_ego_diff,
      )
      v_target = float(self.starpilot_planner.v_cruise or raw_v_cruise)
      if effective_slc_target > 0.0:
        v_target = min(v_target, effective_slc_target)
      slc_limited = effective_slc_target > 0.0 and abs(v_target - effective_slc_target) <= SLC_TARGET_EPS and effective_slc_target < raw_v_cruise - SLC_TARGET_EPS
      has_relevant_lead = any(lead_is_braking_relevant(lead, v_ego) for lead in (sm["radarState"].leadOne, sm["radarState"].leadTwo))
      stop_context = (
        sm["carState"].standstill or
        getattr(sm["controlsState"], "forceDecel", False) or
        self.starpilot_planner.longitudinal_intent.stop_detected or
        getattr(self.starpilot_planner.starpilot_vcruise, "forcing_stop", False)
      )
      if (getattr(starpilot_toggles, "speed_limit_controller", False) and
          v_ego > SLC_COAST_MIN_SPEED and
          v_ego > v_target + 0.05 and
          slc_limited and
          not has_relevant_lead and
          not stop_context):
        self.min_accel = get_slc_shaped_min_accel(v_ego, v_target, deceleration_profile, self.min_accel)

    # Sync AccelerationProfile and DecelerationProfile params so the UI reflects the active drive mode
    # Eco → Eco, Normal → Standard, Sport → Sport+
    gear_state = "eco" if eco_gear else ("sport" if sport_gear else "normal")
    if gear_state != self.last_gear_state:
      self.last_gear_state = gear_state
      if gear_state == "eco":
        if starpilot_toggles.map_acceleration:
          self.params.put_nonblocking("AccelerationProfile", ACCELERATION_PROFILES["ECO"])
        if starpilot_toggles.map_deceleration:
          self.params.put_nonblocking("DecelerationProfile", DECELERATION_PROFILES["ECO"])
      elif gear_state == "sport":
        if starpilot_toggles.map_acceleration:
          self.params.put_nonblocking("AccelerationProfile", ACCELERATION_PROFILES["SPORT_PLUS"])
        if starpilot_toggles.map_deceleration:
          self.params.put_nonblocking("DecelerationProfile", DECELERATION_PROFILES["SPORT"])
      else:
        if starpilot_toggles.map_acceleration:
          self.params.put_nonblocking("AccelerationProfile", ACCELERATION_PROFILES["STANDARD"])
        if starpilot_toggles.map_deceleration:
          self.params.put_nonblocking("DecelerationProfile", DECELERATION_PROFILES["STANDARD"])
