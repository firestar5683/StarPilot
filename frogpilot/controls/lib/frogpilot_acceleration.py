#!/usr/bin/env python3
import numpy as np


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
     t2 = t*t
     t3 = t2*t

     return fp[i]*(1 - 3*t2 + 2*t3) + fp[i+1]*(3*t2 - 2*t3)

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
     t3 = t2*t
     t4 = t2*t2
     t5 = t3*t2

     return (fp[i]*(1 - 10*t3 + 15*t4 - 6*t5) + fp[i+1]*(10*t3 - 15*t4 + 6*t5))


from openpilot.selfdrive.controls.lib.longitudinal_planner import A_CRUISE_MIN, get_max_accel

from openpilot.frogpilot.common.frogpilot_variables import CITY_SPEED_LIMIT

A_CRUISE_MIN_ECO =   A_CRUISE_MIN / 2
A_CRUISE_MIN_SPORT = A_CRUISE_MIN * 2

                       # MPH = [0.0,  11,  22,  34,  45,  56,  89]
A_CRUISE_MAX_BP_CUSTOM =       [0.0,  5., 10., 15., 20., 25., 40.]
A_CRUISE_MAX_VALS_ECO_EV =     [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
A_CRUISE_MAX_VALS_SPORT_EV =   [1.25, 1.25, 1.25, 1.25, 1.5, 1.5, 2.0]
A_CRUISE_MAX_VALS_ECO_GAS =    [6.0, 1.40, 0.90, 0.65, 0.60, 0.55, 0.42]
A_CRUISE_MAX_VALS_SPORT_GAS =  [6.0, 1.50, 1.00, 0.72, 0.65, 0.60, 0.45]

def get_max_accel_eco(v_ego, ev_tuning=True):
  cruise_vals = A_CRUISE_MAX_VALS_ECO_EV if ev_tuning else A_CRUISE_MAX_VALS_ECO_GAS
  return float(akima_interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, cruise_vals))

def get_max_accel_sport(v_ego, ev_tuning=True):
  cruise_vals = A_CRUISE_MAX_VALS_SPORT_EV if ev_tuning else A_CRUISE_MAX_VALS_SPORT_GAS
  return float(akima_interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, cruise_vals))

def get_max_accel_low_speeds(max_accel, v_cruise):
  return float(akima_interp(v_cruise, [0., CITY_SPEED_LIMIT / 2, CITY_SPEED_LIMIT], [max_accel / 4, max_accel / 2, max_accel]))

def get_max_accel_ramp_off(max_accel, v_cruise, v_ego):
  return float(akima_interp(v_cruise - v_ego, [0., 1., 5., 10.], [0., 0.5, 1.0, max_accel]))

def get_max_allowed_accel(v_ego):
  return float(akima_interp(v_ego, [0., 5., 20.], [4.0, 4.0, 2.0]))  # ISO 15622:2018

class FrogPilotAcceleration:
  def __init__(self, FrogPilotPlanner):
    self.frogpilot_planner = FrogPilotPlanner

    self.max_accel = 0
    self.min_accel = 0

  def update(self, v_ego, sm, frogpilot_toggles):
    eco_gear = sm["frogpilotCarState"].ecoGear
    sport_gear = sm["frogpilotCarState"].sportGear
    ev_tuning = frogpilot_toggles.ev_tuning

    if sm["frogpilotCarState"].trafficModeEnabled:
      self.max_accel = get_max_accel(v_ego)
    elif frogpilot_toggles.map_acceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.max_accel = get_max_accel_eco(v_ego, ev_tuning)
      else:
        if frogpilot_toggles.acceleration_profile == 2:
          self.max_accel = get_max_accel_sport(v_ego, ev_tuning)
        else:
          self.max_accel = get_max_allowed_accel(v_ego)
    else:
      if frogpilot_toggles.acceleration_profile == 1:
        self.max_accel = get_max_accel_eco(v_ego, ev_tuning)
      elif frogpilot_toggles.acceleration_profile == 2:
        self.max_accel = get_max_accel_sport(v_ego, ev_tuning)
      elif frogpilot_toggles.acceleration_profile == 3:
        self.max_accel = get_max_allowed_accel(v_ego)
      else:
        self.max_accel = get_max_accel(v_ego)

    if frogpilot_toggles.human_acceleration:
      self.max_accel = min(get_max_accel_low_speeds(self.max_accel, self.frogpilot_planner.v_cruise), self.max_accel)
      self.max_accel = min(get_max_accel_ramp_off(self.max_accel, self.frogpilot_planner.v_cruise, v_ego), self.max_accel)

    if sm["frogpilotCarState"].forceCoast:
      self.min_accel = A_CRUISE_MIN_ECO
    elif frogpilot_toggles.map_deceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.min_accel = A_CRUISE_MIN_ECO
      else:
        self.min_accel = A_CRUISE_MIN_SPORT
    else:
      if frogpilot_toggles.deceleration_profile == 1:
        self.min_accel = A_CRUISE_MIN_ECO
      elif frogpilot_toggles.deceleration_profile == 2:
        self.min_accel = A_CRUISE_MIN_SPORT
      else:
        self.min_accel = A_CRUISE_MIN
