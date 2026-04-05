#!/usr/bin/env python3
from __future__ import annotations

import math

from openpilot.selfdrive.controls.lib.longitudinal_planner import get_max_accel

ACCELERATION_PROFILES = {
  "STANDARD": 0,
  "ECO": 1,
  "SPORT": 2,
  "SPORT_PLUS": 3,
}

DECELERATION_PROFILES = {
  "STANDARD": 0,
  "ECO": 1,
  "SPORT": 2,
}

# MPH = [0.0, 11, 22, 34, 45, 56, 89]
A_CRUISE_MAX_BP_CUSTOM = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 40.0]

CUSTOM_ACCEL_PROFILE_PARAM_SPECS = [
  ("CustomAccelProfile0MPH", 0),
  ("CustomAccelProfile11MPH", 11),
  ("CustomAccelProfile22MPH", 22),
  ("CustomAccelProfile34MPH", 34),
  ("CustomAccelProfile45MPH", 45),
  ("CustomAccelProfile56MPH", 56),
  ("CustomAccelProfile89MPH", 89),
]
CUSTOM_ACCEL_PROFILE_PARAM_KEYS = [key for key, _ in CUSTOM_ACCEL_PROFILE_PARAM_SPECS]
CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY = "CustomAccelProfileInitialized"
CUSTOM_ACCEL_PROFILE_VALUE_MIN = 0.0
CUSTOM_ACCEL_PROFILE_VALUE_MAX = 6.0

A_CRUISE_MAX_VALS_ECO_EV = [1.25, 1.25, 1.25, 1.25, 1.45, 1.50, 2.00]
A_CRUISE_MAX_VALS_STANDARD_EV = [1.35, 1.35, 1.35, 1.35, 1.60, 1.60, 2.10]
A_CRUISE_MAX_VALS_SPORT_EV = [1.55, 1.55, 1.55, 1.55, 1.84, 1.84, 2.42]
A_CRUISE_MAX_VALS_SPORT_PLUS_EV = [1.7825, 1.7825, 1.7825, 1.7825, 2.116, 2.116, 2.783]
A_CRUISE_MAX_VALS_ECO_GAS = [2.0, 1.5, 1.0, 0.8, 0.6, 0.4, 0.2]
A_CRUISE_MAX_VALS_SPORT_GAS = [3.0, 2.5, 2.0, 1.5, 1.0, 0.8, 0.6]
A_CRUISE_MAX_VALS_ECO_TRUCK = [3.00, 1.05, 0.60, 0.50, 0.50, 0.45, 0.35]
A_CRUISE_MAX_VALS_STANDARD_TRUCK = [6.00, 1.10, 0.70, 0.60, 0.55, 0.45, 0.35]
A_CRUISE_MAX_VALS_SPORT_TRUCK = [6.00, 1.15, 0.75, 0.70, 0.60, 0.50, 0.40]
A_CRUISE_MAX_VALS_SPORT_PLUS_TRUCK = [6.00, 1.30, 0.90, 0.80, 0.70, 0.60, 0.45]


def akima_interp(x, xp, fp):
  if x <= xp[0]:
    return fp[0]
  if x >= xp[-1]:
    return fp[-1]

  i = max(0, min(len(xp) - 2, int(next(idx for idx, bp in enumerate(xp[1:], start=1) if bp >= x) - 1)))
  t = (x - xp[i]) / float(xp[i + 1] - xp[i])
  t2 = t * t
  t3 = t2 * t
  t4 = t2 * t2
  return (fp[i] * (1 - 10 * t3 + 15 * t4 - 6 * t3 * t2)
          + fp[i + 1] * (10 * t3 - 15 * t4 + 6 * t3 * t2))


def normalize_acceleration_profile(value):
  return _normalize_profile(value, ACCELERATION_PROFILES, ACCELERATION_PROFILES["STANDARD"])


def normalize_deceleration_profile(value):
  return _normalize_profile(value, DECELERATION_PROFILES, DECELERATION_PROFILES["STANDARD"])


def get_accel_profile_curve_values(acceleration_profile, ev_tuning=True, truck_tuning=False):
  profile = normalize_acceleration_profile(acceleration_profile)
  if truck_tuning:
    ev_tuning = False

  if profile == ACCELERATION_PROFILES["ECO"]:
    if ev_tuning:
      return list(A_CRUISE_MAX_VALS_ECO_EV)
    if truck_tuning:
      return list(A_CRUISE_MAX_VALS_ECO_TRUCK)
    return list(A_CRUISE_MAX_VALS_ECO_GAS)

  if profile == ACCELERATION_PROFILES["SPORT"]:
    if ev_tuning:
      return list(A_CRUISE_MAX_VALS_SPORT_EV)
    if truck_tuning:
      return list(A_CRUISE_MAX_VALS_SPORT_TRUCK)
    return list(A_CRUISE_MAX_VALS_SPORT_GAS)

  if profile == ACCELERATION_PROFILES["SPORT_PLUS"]:
    if ev_tuning:
      return list(A_CRUISE_MAX_VALS_SPORT_PLUS_EV)
    if truck_tuning:
      return list(A_CRUISE_MAX_VALS_SPORT_PLUS_TRUCK)
    return [float(akima_interp(v_ego, [0.0, 5.0, 20.0], [4.0, 4.0, 2.0])) for v_ego in A_CRUISE_MAX_BP_CUSTOM]

  if ev_tuning:
    return list(A_CRUISE_MAX_VALS_STANDARD_EV)
  if truck_tuning:
    return list(A_CRUISE_MAX_VALS_STANDARD_TRUCK)
  return [float(get_max_accel(v_ego)) for v_ego in A_CRUISE_MAX_BP_CUSTOM]


def interpolate_accel_profile(v_ego, curve_values):
  return float(akima_interp(v_ego, A_CRUISE_MAX_BP_CUSTOM, curve_values))


def get_max_allowed_accel(v_ego, ev_tuning=True, truck_tuning=False):
  return interpolate_accel_profile(v_ego, get_accel_profile_curve_values(ACCELERATION_PROFILES["SPORT_PLUS"], ev_tuning, truck_tuning))


def build_custom_accel_profile_defaults(acceleration_profile, ev_tuning=True, truck_tuning=False):
  curve_values = get_accel_profile_curve_values(acceleration_profile, ev_tuning, truck_tuning)
  return {
    key: float(curve_values[idx])
    for idx, key in enumerate(CUSTOM_ACCEL_PROFILE_PARAM_KEYS)
  }


CUSTOM_ACCEL_PROFILE_STATIC_DEFAULTS = {
  key: float(A_CRUISE_MAX_VALS_SPORT_GAS[idx])
  for idx, key in enumerate(CUSTOM_ACCEL_PROFILE_PARAM_KEYS)
}


def custom_accel_profile_is_initialized(initialized_flag, raw_values_by_key):
  if _coerce_bool(initialized_flag):
    return True

  if not isinstance(raw_values_by_key, dict):
    return False

  for key in CUSTOM_ACCEL_PROFILE_PARAM_KEYS:
    raw_value = raw_values_by_key.get(key)
    if raw_value is None:
      return False

    try:
      value = float(raw_value.decode("utf-8", errors="replace") if isinstance(raw_value, bytes) else raw_value)
    except (TypeError, ValueError):
      return False

    if not math.isclose(value, CUSTOM_ACCEL_PROFILE_STATIC_DEFAULTS[key], abs_tol=1e-6):
      return True

  return False


def coerce_custom_accel_profile_values(raw_values, acceleration_profile, ev_tuning=True, truck_tuning=False):
  defaults = get_accel_profile_curve_values(acceleration_profile, ev_tuning, truck_tuning)
  values = []
  for idx, default in enumerate(defaults):
    try:
      value = float(raw_values[idx])
    except (IndexError, TypeError, ValueError):
      value = default
    values.append(min(CUSTOM_ACCEL_PROFILE_VALUE_MAX, max(CUSTOM_ACCEL_PROFILE_VALUE_MIN, value)))
  return values


def _normalize_profile(value, profile_map, fallback):
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")

  if isinstance(value, str):
    normalized = value.strip().upper().replace("+", "_PLUS").replace(" ", "_")
    if normalized in profile_map:
      return profile_map[normalized]

  try:
    return int(float(value))
  except (TypeError, ValueError):
    return fallback


def _coerce_bool(value):
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="replace")

  if isinstance(value, str):
    return value.strip() in ("1", "true", "True")

  return bool(value)
