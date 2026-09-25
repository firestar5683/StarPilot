"""Frozen named acceleration curves used by versioned longitudinal profiles."""
from __future__ import annotations

ACCELERATION_PROFILES = {"STANDARD": 0, "ECO": 1, "SPORT": 2, "SPORT_PLUS": 3}
DECELERATION_PROFILES = {"STANDARD": 0, "ECO": 1, "SPORT": 2}
A_CRUISE_MAX_BP_CUSTOM = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 40.0]
CUSTOM_ACCEL_PROFILE_MIN_POINTS = 2

A_CRUISE_MAX_VALS_ECO_EV =        [1.50, 1.34, 1.18, 1.02, 0.90, 0.74, 0.58]
A_CRUISE_MAX_VALS_STANDARD_EV =   [2.00, 1.84, 1.64, 1.44, 1.24, 1.08, 0.84]
A_CRUISE_MAX_VALS_SPORT_EV =      [2.50, 2.30, 2.06, 1.78, 1.54, 1.34, 1.10]
A_CRUISE_MAX_VALS_SPORT_PLUS_EV = [3.50, 3.26, 2.94, 2.58, 2.22, 1.94, 1.62]

A_CRUISE_MAX_VALS_ECO_GAS =        [1.50, 1.30, 1.10, 0.90, 0.75, 0.55, 0.35]
A_CRUISE_MAX_VALS_STANDARD_GAS =   [2.00, 1.80, 1.55, 1.30, 1.05, 0.85, 0.55]
A_CRUISE_MAX_VALS_SPORT_GAS =      [2.50, 2.25, 1.95, 1.60, 1.30, 1.05, 0.75]
A_CRUISE_MAX_VALS_SPORT_PLUS_GAS = [3.50, 3.20, 2.80, 2.35, 1.90, 1.55, 1.15]

# Traffic Mode: bumper-to-bumper stop-and-go, softer than Eco at every breakpoint.
# Single curve for all vehicle types, derived from manual stop-and-go driving logs.
A_CRUISE_MAX_VALS_TRAFFIC_ALL = [1.10, 0.87, 0.67, 0.53, 0.44, 0.34, 0.23]

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
    return list(A_CRUISE_MAX_VALS_SPORT_PLUS_GAS)

  if ev_tuning:
    return list(A_CRUISE_MAX_VALS_STANDARD_EV)
  if truck_tuning:
    return list(A_CRUISE_MAX_VALS_STANDARD_TRUCK)
  return list(A_CRUISE_MAX_VALS_STANDARD_GAS)


def interpolate_accel_profile(v_ego, curve_values, breakpoints=None):
  curve_breakpoints = A_CRUISE_MAX_BP_CUSTOM if breakpoints is None else breakpoints
  if len(curve_breakpoints) != len(curve_values) or len(curve_breakpoints) < CUSTOM_ACCEL_PROFILE_MIN_POINTS:
    raise ValueError("Acceleration profile requires matching breakpoint and value arrays")
  return float(akima_interp(v_ego, curve_breakpoints, curve_values))


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
