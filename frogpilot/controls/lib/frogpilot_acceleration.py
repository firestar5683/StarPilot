#!/usr/bin/env python3
import numpy as np

from openpilot.selfdrive.controls.lib.longitudinal_planner import A_CRUISE_MIN, get_max_accel

from openpilot.frogpilot.common.frogpilot_variables import CITY_SPEED_LIMIT

def cubic_interp(x, xp, fp):
  if x <= xp[0]:
    return fp[0]
  elif x >= xp[-1]:
    return fp[-1]

  i = np.searchsorted(xp, x) - 1
  i = max(0, min(i, len(xp) - 2))
  t = (x - xp[i]) / float(xp[i + 1] - xp[i])

  return fp[i] * (1 - 3 * t ** 2 + 2 * t ** 3) + fp[i + 1] * (3 * t ** 2 - 2 * t ** 3)

def akima_interp(x, xp, fp):
  if x <= xp[0]:
    return fp[0]
  elif x >= xp[-1]:
    return fp[-1]

  i = np.searchsorted(xp, x) - 1
  i = max(0, min(i, len(xp) - 2))
  t = (x - xp[i]) / float(xp[i + 1] - xp[i])

  t2 = t * t
  t3 = t2 * t
  t4 = t2 * t2
  return (fp[i] * (1 - 10 * t3 + 15 * t4 - 6 * t3 * t2)
          + fp[i + 1] * (10 * t3 - 15 * t4 + 6 * t3 * t2))

A_CRUISE_MIN_ECO = A_CRUISE_MIN / 2
A_CRUISE_MIN_SPORT = A_CRUISE_MIN * 2

                       # MPH = [0.0,  11,  22,  34,  45,  56,  89]
A_CRUISE_MAX_BP_CUSTOM =        [0.0,  5., 10., 15., 20., 25., 40.]
A_CRUISE_MAX_VALS_ECO_EV =      [1.15, 1.15, 1.15, 1.15, 1.30, 1.30, 1.72]
A_CRUISE_MAX_VALS_STANDARD_EV = [1.25, 1.25, 1.25, 1.25, 1.45, 1.50, 2.00]
A_CRUISE_MAX_VALS_SPORT_EV =    [1.35, 1.35, 1.35, 1.35, 1.60, 1.60, 2.10]
A_CRUISE_MAX_VALS_SPORT_PLUS_EV = [1.55, 1.55, 1.55, 1.55, 1.84, 1.84, 2.42]
A_CRUISE_MAX_VALS_ECO_GAS =       [2.0, 1.5, 1.0, 0.8, 0.6, 0.4, 0.2]
A_CRUISE_MAX_VALS_SPORT_GAS =     [3.0, 2.5, 2.0, 1.5, 1.0, 0.8, 0.6]
A_CRUISE_MAX_VALS_ECO_TRUCK =       [3.00, 1.05, 0.60, 0.50, 0.50, 0.45, 0.35]
A_CRUISE_MAX_VALS_STANDARD_TRUCK =  [6.00, 1.10, 0.70, 0.60, 0.55, 0.45, 0.35]
A_CRUISE_MAX_VALS_SPORT_TRUCK =     [6.00, 1.15, 0.75, 0.70, 0.60, 0.50, 0.40]
A_CRUISE_MAX_VALS_SPORT_PLUS_TRUCK = [6.00, 1.30, 0.90, 0.80, 0.70, 0.60, 0.45]

ACCELERATION_PROFILES = {
  "STANDARD": 0,
  "ECO": 1,
  "SPORT": 2,
  "SPORT_PLUS": 3
}

DECELERATION_PROFILES = {
  "STANDARD": 0,
  "ECO": 1,
  "SPORT": 2
}

def get_max_accel_eco(v_ego, ev_tuning=True, truck_tuning=False):
  if ev_tuning:
    cruise_vals = A_CRUISE_MAX_VALS_ECO_EV
  elif truck_tuning:
    cruise_vals = A_CRUISE_MAX_VALS_ECO_TRUCK
  else:
    cruise_vals = A_CRUISE_MAX_VALS_ECO_GAS
  return float(akima_interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, cruise_vals))

def get_max_accel_sport(v_ego, ev_tuning=True, truck_tuning=False):
  if ev_tuning:
    cruise_vals = A_CRUISE_MAX_VALS_SPORT_EV
  elif truck_tuning:
    cruise_vals = A_CRUISE_MAX_VALS_SPORT_TRUCK
  else:
    cruise_vals = A_CRUISE_MAX_VALS_SPORT_GAS
  return float(akima_interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, cruise_vals))

def get_max_accel_standard(v_ego, ev_tuning=True, truck_tuning=False):
  if ev_tuning:
    return float(akima_interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, A_CRUISE_MAX_VALS_STANDARD_EV))
  if truck_tuning:
    return float(akima_interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, A_CRUISE_MAX_VALS_STANDARD_TRUCK))
  return get_max_accel(v_ego)

def get_max_accel_low_speeds(max_accel, v_cruise):
  return float(akima_interp(v_cruise, [0., CITY_SPEED_LIMIT / 2, CITY_SPEED_LIMIT], [max_accel / 4, max_accel / 2, max_accel]))

def get_max_accel_ramp_off(max_accel, v_cruise, v_ego):
  return float(akima_interp(v_cruise - v_ego, [0., 1., 5., 10.], [0., 0.5, 1.0, max_accel]))

def get_max_allowed_accel(v_ego, ev_tuning=True, truck_tuning=False):
  if ev_tuning:
    return float(akima_interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, A_CRUISE_MAX_VALS_SPORT_PLUS_EV))
  if truck_tuning:
    return float(akima_interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, A_CRUISE_MAX_VALS_SPORT_PLUS_TRUCK))
  return float(akima_interp(v_ego, [0., 5., 20.], [4.0, 4.0, 2.0]))  # ISO 15622:2018

class FrogPilotAcceleration:
  def __init__(self, FrogPilotPlanner):
    self.frogpilot_planner = FrogPilotPlanner

    self.max_accel = 0
    self.min_accel = 0

  def update(self, v_ego, sm, frogpilot_toggles):
    eco_gear = sm["frogpilotCarState"].ecoGear
    sport_gear = sm["frogpilotCarState"].sportGear
    ev_tuning = getattr(frogpilot_toggles, "ev_tuning", True)
    truck_tuning = getattr(frogpilot_toggles, "truck_tuning", False)

    if sm["frogpilotCarState"].trafficModeEnabled:
      self.max_accel = get_max_accel_standard(v_ego, ev_tuning, truck_tuning)
    elif frogpilot_toggles.map_acceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.max_accel = get_max_accel_eco(v_ego, ev_tuning, truck_tuning)
      else:
        if frogpilot_toggles.acceleration_profile == ACCELERATION_PROFILES["SPORT"]:
          self.max_accel = get_max_accel_sport(v_ego, ev_tuning, truck_tuning)
        else:
          self.max_accel = get_max_allowed_accel(v_ego, ev_tuning, truck_tuning)
    else:
      if frogpilot_toggles.acceleration_profile == ACCELERATION_PROFILES["ECO"]:
        self.max_accel = get_max_accel_eco(v_ego, ev_tuning, truck_tuning)
      elif frogpilot_toggles.acceleration_profile == ACCELERATION_PROFILES["SPORT"]:
        self.max_accel = get_max_accel_sport(v_ego, ev_tuning, truck_tuning)
      elif frogpilot_toggles.acceleration_profile == ACCELERATION_PROFILES["SPORT_PLUS"]:
        self.max_accel = get_max_allowed_accel(v_ego, ev_tuning, truck_tuning)
      else:
        self.max_accel = get_max_accel_standard(v_ego, ev_tuning, truck_tuning)

    if frogpilot_toggles.human_acceleration:
      self.max_accel = min(get_max_accel_low_speeds(self.max_accel, self.frogpilot_planner.v_cruise), self.max_accel)
      self.max_accel = min(get_max_accel_ramp_off(self.max_accel, self.frogpilot_planner.v_cruise, v_ego), self.max_accel)

    if self.frogpilot_planner.frogpilot_weather.weather_id != 0:
      self.max_accel -= self.max_accel * self.frogpilot_planner.frogpilot_weather.reduce_acceleration

    if sm["frogpilotCarState"].forceCoast:
      self.min_accel = A_CRUISE_MIN_ECO
    elif frogpilot_toggles.map_deceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.min_accel = A_CRUISE_MIN_ECO
      else:
        self.min_accel = A_CRUISE_MIN_SPORT
    else:
      if frogpilot_toggles.deceleration_profile == DECELERATION_PROFILES["ECO"]:
        self.min_accel = A_CRUISE_MIN_ECO
      elif frogpilot_toggles.deceleration_profile == DECELERATION_PROFILES["SPORT"]:
        self.min_accel = A_CRUISE_MIN_SPORT
      else:
        self.min_accel = A_CRUISE_MIN
