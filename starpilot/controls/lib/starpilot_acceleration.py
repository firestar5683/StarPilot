#!/usr/bin/env python3
import numpy as np

from openpilot.selfdrive.controls.lib.longitudinal_planner import A_CRUISE_MIN, get_max_accel

from openpilot.starpilot.common.accel_profile import (
  ACCELERATION_PROFILES,
  DECELERATION_PROFILES,
  coerce_custom_accel_profile_values,
  get_accel_profile_curve_values,
  get_max_allowed_accel as get_profile_max_allowed_accel,
  interpolate_accel_profile,
)
from openpilot.starpilot.common.starpilot_variables import CITY_SPEED_LIMIT

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

def get_max_accel_eco(v_ego, ev_tuning=True, truck_tuning=False):
  return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["ECO"], ev_tuning, truck_tuning))

def get_max_accel_sport(v_ego, ev_tuning=True, truck_tuning=False):
  return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["SPORT"], ev_tuning, truck_tuning))

def get_max_accel_standard(v_ego, ev_tuning=True, truck_tuning=False):
  if ev_tuning or truck_tuning:
    return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["STANDARD"], ev_tuning, truck_tuning))
  return float(get_max_accel(v_ego))

def get_max_accel_custom(v_ego, custom_curve, acceleration_profile, ev_tuning=True, truck_tuning=False):
  curve_values = coerce_custom_accel_profile_values(custom_curve, acceleration_profile, ev_tuning, truck_tuning)
  return interpolate_accel_profile(v_ego, curve_values)

def get_max_accel_low_speeds(max_accel, v_cruise):
  return float(akima_interp(v_cruise, [0., CITY_SPEED_LIMIT / 2, CITY_SPEED_LIMIT], [max_accel / 4, max_accel / 2, max_accel]))

def get_max_accel_ramp_off(max_accel, v_cruise, v_ego):
  return float(akima_interp(v_cruise - v_ego, [0., 1., 5., 10.], [0., 0.5, 1.0, max_accel]))

def get_max_allowed_accel(v_ego, ev_tuning=True, truck_tuning=False):
  return float(get_profile_max_allowed_accel(v_ego, ev_tuning, truck_tuning))

class StarPilotAcceleration:
  def __init__(self, StarPilotPlanner):
    self.starpilot_planner = StarPilotPlanner

    self.max_accel = 0
    self.min_accel = 0

  def update(self, v_ego, sm, starpilot_toggles):
    eco_gear = sm["starpilotCarState"].ecoGear
    sport_gear = sm["starpilotCarState"].sportGear
    ev_tuning = getattr(starpilot_toggles, "ev_tuning", True)
    truck_tuning = getattr(starpilot_toggles, "truck_tuning", False)
    custom_accel_profile = getattr(starpilot_toggles, "custom_accel_profile", False)
    custom_accel_profile_values = getattr(starpilot_toggles, "custom_accel_profile_values", [])

    if custom_accel_profile:
      self.max_accel = get_max_accel_custom(v_ego, custom_accel_profile_values, starpilot_toggles.acceleration_profile, ev_tuning, truck_tuning)
    elif sm["starpilotCarState"].trafficModeEnabled:
      self.max_accel = get_max_accel_standard(v_ego, ev_tuning, truck_tuning)
    elif starpilot_toggles.map_acceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.max_accel = get_max_accel_eco(v_ego, ev_tuning, truck_tuning)
      else:
        if starpilot_toggles.acceleration_profile == ACCELERATION_PROFILES["SPORT"]:
          self.max_accel = get_max_accel_sport(v_ego, ev_tuning, truck_tuning)
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

    if starpilot_toggles.human_acceleration:
      self.max_accel = min(get_max_accel_low_speeds(self.max_accel, self.starpilot_planner.v_cruise), self.max_accel)
      self.max_accel = min(get_max_accel_ramp_off(self.max_accel, self.starpilot_planner.v_cruise, v_ego), self.max_accel)

    if self.starpilot_planner.starpilot_weather.weather_id != 0:
      self.max_accel -= self.max_accel * self.starpilot_planner.starpilot_weather.reduce_acceleration

    if sm["starpilotCarState"].forceCoast:
      self.min_accel = A_CRUISE_MIN_ECO
    elif starpilot_toggles.map_deceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.min_accel = A_CRUISE_MIN_ECO
      else:
        self.min_accel = A_CRUISE_MIN_SPORT
    else:
      if starpilot_toggles.deceleration_profile == DECELERATION_PROFILES["ECO"]:
        self.min_accel = A_CRUISE_MIN_ECO
      elif starpilot_toggles.deceleration_profile == DECELERATION_PROFILES["SPORT"]:
        self.min_accel = A_CRUISE_MIN_SPORT
      else:
        self.min_accel = A_CRUISE_MIN
