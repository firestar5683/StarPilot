#!/usr/bin/env python3
import math

import numpy as np

from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.selfdrive.car.cruise import V_CRUISE_MAX, V_CRUISE_UNSET
from openpilot.selfdrive.controls.lib.longitudinal_planner import A_CRUISE_MIN, get_max_accel

from openpilot.starpilot.common.accel_profile import (
  ACCELERATION_PROFILES,
  A_CRUISE_MAX_BP_CUSTOM,
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
PULSE_GLIDE_MIN_TARGET_SPEED = 5.0
PULSE_GLIDE_MIN_LOWER_SPEED = 3.0
PULSE_GLIDE_HYSTERESIS = 0.25
PULSE_GLIDE_COAST_MIN_ACCEL = -0.03
PULSE_GLIDE_HILL_ENTER_PITCH = math.radians(3.0)
PULSE_GLIDE_HILL_EXIT_PITCH = math.radians(2.5)

# Drive mode -> profile mapping used by the map_acceleration / map_deceleration toggles.
GEAR_STATE_PROFILES = {
  "eco": (ACCELERATION_PROFILES["ECO"], DECELERATION_PROFILES["ECO"]),
  "sport": (ACCELERATION_PROFILES["SPORT_PLUS"], DECELERATION_PROFILES["SPORT"]),
  "normal": (ACCELERATION_PROFILES["STANDARD"], DECELERATION_PROFILES["STANDARD"]),
}

def get_max_accel_eco(v_ego, ev_tuning=True, truck_tuning=False):
  return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["ECO"], ev_tuning, truck_tuning))

def get_max_accel_sport(v_ego, ev_tuning=True, truck_tuning=False):
  return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["SPORT"], ev_tuning, truck_tuning))

def get_max_accel_standard(v_ego, ev_tuning=True, truck_tuning=False):
  return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["STANDARD"], ev_tuning, truck_tuning))

def get_max_accel_traffic(v_ego):
  return interpolate_accel_profile(v_ego, A_CRUISE_MAX_VALS_TRAFFIC_ALL)

def get_max_accel_custom(v_ego, custom_curve, acceleration_profile, ev_tuning=True, truck_tuning=False, custom_breakpoints=None):
  curve_breakpoints = A_CRUISE_MAX_BP_CUSTOM if custom_breakpoints is None else custom_breakpoints
  curve_values = coerce_custom_accel_profile_values(
    custom_curve,
    acceleration_profile,
    ev_tuning,
    truck_tuning,
    point_count=len(curve_breakpoints),
  )
  return interpolate_accel_profile(v_ego, curve_values, curve_breakpoints)

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
    self.params_memory = Params(memory=True)

    self.max_accel = 0
    self.min_accel = 0

    self.last_gear_state = "init"
    self.pulse_glide_coasting = False
    self.pulse_glide_target = None
    self.pulse_glide_hill_paused = False

  def _update_pulse_glide_hill_pause(self, sm):
    try:
      orientation_ned = sm["carControl"].orientationNED
      if len(orientation_ned) < 2:
        return self.pulse_glide_hill_paused
      abs_pitch = abs(float(orientation_ned[1]))
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
      return self.pulse_glide_hill_paused

    if not math.isfinite(abs_pitch):
      return self.pulse_glide_hill_paused

    if self.pulse_glide_hill_paused:
      if abs_pitch <= PULSE_GLIDE_HILL_EXIT_PITCH:
        self.pulse_glide_hill_paused = False
    elif abs_pitch >= PULSE_GLIDE_HILL_ENTER_PITCH:
      self.pulse_glide_hill_paused = True

    return self.pulse_glide_hill_paused

  def _update_pulse_glide(self, v_ego, sm, starpilot_toggles):
    self.pulse_glide_target = None
    pulse_glide_enabled = bool(getattr(sm["starpilotCarState"], "pulseAndGlide", False))
    if not pulse_glide_enabled:
      self.pulse_glide_coasting = False
      self.pulse_glide_hill_paused = False
      return False

    if self._update_pulse_glide_hill_pause(sm):
      self.pulse_glide_coasting = False
      return False

    raw_v_cruise_kph = 0.0 if sm["carState"].vCruise == V_CRUISE_UNSET else min(sm["carState"].vCruise, V_CRUISE_MAX)
    if 0 < raw_v_cruise_kph < V_CRUISE_UNSET and getattr(starpilot_toggles, "set_speed_offset", 0) > 0:
      raw_v_cruise_kph += starpilot_toggles.set_speed_offset
    raw_v_cruise = raw_v_cruise_kph * CV.KPH_TO_MS
    if raw_v_cruise <= 0.0:
      self.pulse_glide_coasting = False
      return False

    effective_slc_target = get_active_slc_control_target(
      getattr(starpilot_toggles, "speed_limit_controller", False),
      getattr(starpilot_toggles, "set_speed_limit", False),
      getattr(self.starpilot_planner.starpilot_vcruise, "slc_target", 0.0),
      getattr(self.starpilot_planner.starpilot_vcruise, "slc_offset", 0.0),
      getattr(getattr(self.starpilot_planner.starpilot_vcruise, "slc", None), "overridden_speed", 0.0),
      max(float(getattr(sm["carState"], "vEgoCluster", v_ego) or v_ego), v_ego) - v_ego,
      allow_lower_override=(getattr(starpilot_toggles, "redneck_cruise", False) and
                            getattr(starpilot_toggles, "speed_limit_controller_override_set_speed", False)),
    )
    v_target = float(self.starpilot_planner.v_cruise or raw_v_cruise)
    if effective_slc_target > 0.0:
      v_target = min(v_target, effective_slc_target)

    delta = max(0.0, float(getattr(starpilot_toggles, "pulse_glide_speed_delta", 0.0)))
    lower_target = v_target - delta
    if (delta <= 0.0 or
        v_target <= PULSE_GLIDE_MIN_TARGET_SPEED or
        lower_target < PULSE_GLIDE_MIN_LOWER_SPEED):
      self.pulse_glide_coasting = False
      return False

    has_relevant_lead = any(lead_is_braking_relevant(lead, v_ego) for lead in (sm["radarState"].leadOne, sm["radarState"].leadTwo))
    stop_context = (
      sm["carState"].standstill or
      getattr(sm["controlsState"], "forceDecel", False) or
      getattr(self.starpilot_planner.starpilot_cem, "stop_light_detected", False) or
      getattr(self.starpilot_planner.starpilot_vcruise, "forcing_stop", False) or
      getattr(self.starpilot_planner.starpilot_following, "disable_throttle", False)
    )
    if has_relevant_lead or stop_context:
      self.pulse_glide_coasting = False
      return False

    if self.pulse_glide_coasting:
      if v_ego <= lower_target + PULSE_GLIDE_HYSTERESIS:
        self.pulse_glide_coasting = False
    elif v_ego >= v_target - PULSE_GLIDE_HYSTERESIS:
      self.pulse_glide_coasting = True

    if self.pulse_glide_coasting:
      self.pulse_glide_target = lower_target

    return self.pulse_glide_coasting

  def update(self, v_ego, sm, starpilot_toggles):
    eco_gear = sm["starpilotCarState"].ecoGear
    sport_gear = sm["starpilotCarState"].sportGear
    ev_tuning = getattr(starpilot_toggles, "ev_tuning", True)
    truck_tuning = getattr(starpilot_toggles, "truck_tuning", False)
    custom_accel_profile = getattr(starpilot_toggles, "custom_accel_profile", False)
    custom_accel_profile_values = getattr(starpilot_toggles, "custom_accel_profile_values", [])
    custom_accel_profile_breakpoints = getattr(starpilot_toggles, "custom_accel_profile_breakpoints", A_CRUISE_MAX_BP_CUSTOM)
    deceleration_profile = normalize_deceleration_profile(
      getattr(starpilot_toggles, "deceleration_profile", DECELERATION_PROFILES["STANDARD"])
    )
    if sm["starpilotCarState"].trafficModeEnabled:
      self.max_accel = get_max_accel_traffic(v_ego)
    elif custom_accel_profile:
      self.max_accel = get_max_accel_custom(
        v_ego,
        custom_accel_profile_values,
        starpilot_toggles.acceleration_profile,
        ev_tuning,
        truck_tuning,
        custom_accel_profile_breakpoints,
      )
    elif starpilot_toggles.map_acceleration:
      # Drive mode is authoritative while mapping is on, normal gear included. Letting
      # normal fall through to the profile param instead leaves the car on a stale eco
      # or sport curve for the rest of the ignition cycle once the driver selects it
      # again, because the param resync below cannot be observed any sooner.
      if eco_gear:
        self.max_accel = get_max_accel_eco(v_ego, ev_tuning, truck_tuning)
      elif sport_gear:
        self.max_accel = get_max_allowed_accel(v_ego, ev_tuning, truck_tuning)
      else:
        self.max_accel = get_max_accel_standard(v_ego, ev_tuning, truck_tuning)
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

    pulse_glide_coasting = self._update_pulse_glide(v_ego, sm, starpilot_toggles)
    if sm["starpilotCarState"].forceCoast:
      self.min_accel = A_CRUISE_MIN_ECO
    elif pulse_glide_coasting:
      self.min_accel = PULSE_GLIDE_COAST_MIN_ACCEL
    elif sm["starpilotCarState"].trafficModeEnabled:
      self.min_accel = A_CRUISE_MIN_TRAFFIC
    elif starpilot_toggles.map_deceleration and (eco_gear or sport_gear):
      if eco_gear:
        self.min_accel = A_CRUISE_MIN_ECO
      else:
        self.min_accel = A_CRUISE_MIN_SPORT
    else:
      if starpilot_toggles.map_deceleration:
        # Same reasoning as the acceleration side, but resolved through the profile so
        # normal gear keeps the SLC-shaped floor below.
        deceleration_profile = DECELERATION_PROFILES["STANDARD"]
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
        allow_lower_override=(getattr(starpilot_toggles, "redneck_cruise", False) and
                              getattr(starpilot_toggles, "speed_limit_controller_override_set_speed", False)),
      )
      v_target = float(self.starpilot_planner.v_cruise or raw_v_cruise)
      if effective_slc_target > 0.0:
        v_target = min(v_target, effective_slc_target)
      slc_limited = effective_slc_target > 0.0 and abs(v_target - effective_slc_target) <= SLC_TARGET_EPS and effective_slc_target < raw_v_cruise - SLC_TARGET_EPS
      has_relevant_lead = any(lead_is_braking_relevant(lead, v_ego) for lead in (sm["radarState"].leadOne, sm["radarState"].leadTwo))
      stop_context = (
        sm["carState"].standstill or
        getattr(sm["controlsState"], "forceDecel", False) or
        getattr(self.starpilot_planner.starpilot_cem, "stop_light_detected", False) or
        getattr(self.starpilot_planner.starpilot_vcruise, "forcing_stop", False) or
        getattr(self.starpilot_planner.starpilot_following, "disable_throttle", False)
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
    mapping_enabled = starpilot_toggles.map_acceleration or starpilot_toggles.map_deceleration
    # Latch only once a mapping is actually enabled. Consuming the transition while both
    # toggles are still off would skip the resync for the life of the process, since gear
    # state never changes again on a drive that stays in one mode.
    if gear_state != self.last_gear_state and mapping_enabled:
      self.last_gear_state = gear_state
      mapped_acceleration_profile, mapped_deceleration_profile = GEAR_STATE_PROFILES[gear_state]
      if starpilot_toggles.map_acceleration:
        self.params.put_nonblocking("AccelerationProfile", mapped_acceleration_profile)
      if starpilot_toggles.map_deceleration:
        self.params.put_nonblocking("DecelerationProfile", mapped_deceleration_profile)
      # The planner reads the toggles blob rather than these params, and that blob is only
      # rebuilt when this flag is set. Without it the write stays invisible until the next
      # ignition cycle and the UI disagrees with what the planner is actually running.
      self.params_memory.put_bool("StarPilotTogglesUpdated", True)
