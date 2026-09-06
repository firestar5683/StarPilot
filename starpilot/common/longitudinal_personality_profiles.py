#!/usr/bin/env python3
"""Versioned, fail-closed longitudinal acceleration/braking profiles."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import numbers

PERSONALITY_PROFILES_PARAM = "LongitudinalPersonalityProfiles"
PROFILE_SCHEMA_VERSION = 2
PERSONALITY_IDS = ("traffic", "aggressive", "standard", "relaxed")
TRUCK_FINGERPRINT_TOKENS = (
  " RAM 1500 ",
  " RAM HD ",
  " F 150 ",
  " MAVERICK ",
  " RANGER ",
  " SILVERADO ",
  " RIDGELINE ",
  " SANTA CRUZ ",
)

ACCELERATION_SPEEDS_MPH = tuple(range(0, 91, 10))
BRAKING_SPEEDS_MPH = ACCELERATION_SPEEDS_MPH
FOLLOWING_SPEEDS_MPH = ACCELERATION_SPEEDS_MPH
_NATIVE_ACCELERATION_SPEEDS_MS = (0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 40.0)
_V1_ACCELERATION_SPEEDS_MPH = (0.0, 11.184681, 22.369363, 33.554044, 44.738726, 55.923407, 89.477452)


def is_truck_fingerprint(fingerprint: object) -> bool:
  if not isinstance(fingerprint, str) or not fingerprint.strip():
    return False
  normalized = f" {fingerprint.strip().upper().replace('_', ' ').replace('-', ' ')} "
  return any(token in normalized for token in TRUCK_FINGERPRINT_TOKENS)

ACCELERATION_PRESETS = ("dom_default", "standard", "eco", "sport", "sport_plus", "custom")
BRAKING_PRESETS = ("dom_default", "standard", "eco", "sport", "custom")
FOLLOWING_PRESETS = ("dom_default", "close", "medium", "far", "custom")
# Authoring limits are not the persisted schema contract.
CURVE_BOUNDS = {
  "acceleration": (0.0, 3.5),
  "braking": (0.5, 2.0),
  "following": (0.75, 3.0),
}
_V2_CURVE_BOUNDS = {
  "acceleration": (0.0, 6.0),
  "braking": (0.5, 2.0),
  "following": (0.75, 3.0),
}
_V1_CURVE_BOUNDS = dict(_V2_CURVE_BOUNDS)
PERSONALITY_ADVANCED_PARAM_KEYS = frozenset(
  f"{profile}{suffix}"
  for profile in ("Traffic", "Aggressive", "Standard", "Relaxed")
  for suffix in ("JerkAcceleration", "JerkDeceleration", "JerkDanger", "JerkSpeedDecrease", "JerkSpeed")
)
PERSONALITY_FOLLOW_PARAM_KEYS = frozenset({
  "TrafficFollow",
  "AggressiveFollow", "AggressiveFollowHigh",
  "StandardFollow", "StandardFollowHigh",
  "RelaxedFollow", "RelaxedFollowHigh",
})
PERSONALITY_PROFILE_ENABLE_RUNTIME_KEYS = (
  ("traffic_personality_profile", "TrafficPersonalityProfile"),
  ("aggressive_personality_profile", "AggressivePersonalityProfile"),
  ("standard_personality_profile", "StandardPersonalityProfile"),
  ("relaxed_personality_profile", "RelaxedPersonalityProfile"),
)
PERSONALITY_PROFILE_ENABLE_PARAM_KEYS = frozenset(
  param_key for _runtime_key, param_key in PERSONALITY_PROFILE_ENABLE_RUNTIME_KEYS
)
PERSONALITY_PARKED_PARAM_KEYS = (
  PERSONALITY_ADVANCED_PARAM_KEYS
  | PERSONALITY_FOLLOW_PARAM_KEYS
  | PERSONALITY_PROFILE_ENABLE_PARAM_KEYS
  | {"CustomPersonalities"}
)


def load_personality_profile_enable_values(get_value) -> dict[str, bool]:
  return {
    runtime_key: get_value(param_key)
    for runtime_key, param_key in PERSONALITY_PROFILE_ENABLE_RUNTIME_KEYS
  }


def validate_personality_follow_value(raw_value) -> float:
  if not isinstance(raw_value, numbers.Real) or isinstance(raw_value, bool):
    raise ValueError("Following values must be JSON numbers.")
  value = float(raw_value)
  if not math.isfinite(value) or value < 0.5 or value > 3.0:
    raise ValueError("Following values must be between 0.5 and 3.0.")
  return round(value, 4)


def validate_personality_advanced_value(raw_value) -> float:
  if not isinstance(raw_value, numbers.Real) or isinstance(raw_value, bool):
    raise ValueError("Advanced personality values must be JSON numbers.")
  value = float(raw_value)
  if not math.isfinite(value) or value < 25.0 or value > 200.0:
    raise ValueError("Advanced personality values must be between 25 and 200.")
  return round(value, 4)


_CATEGORY_SPECS = {
  "acceleration": (ACCELERATION_PRESETS, len(ACCELERATION_SPEEDS_MPH)),
  "braking": (BRAKING_PRESETS, len(BRAKING_SPEEDS_MPH)),
  "following": (FOLLOWING_PRESETS, len(FOLLOWING_SPEEDS_MPH)),
}

_BRAKING_PRESET_CURVES = {
  "eco": (0.5,) * len(BRAKING_SPEEDS_MPH),
  "standard": (1.0,) * len(BRAKING_SPEEDS_MPH),
  "sport": (2.0,) * len(BRAKING_SPEEDS_MPH),
}
FOLLOWING_PRESET_CURVES = {
  "close": (1.25,) * len(FOLLOWING_SPEEDS_MPH),
  "medium": (1.45,) * len(FOLLOWING_SPEEDS_MPH),
  "far": (1.75,) * len(FOLLOWING_SPEEDS_MPH),
}
PROFILE_AXES = {
  "acceleration": {
    "speed": {"unit": "mph", "values": list(ACCELERATION_SPEEDS_MPH)},
    "value": {"unit": "m/s^2", "meaning": "maximum_requested_acceleration"},
  },
  "braking": {
    "speed": {"unit": "mph", "values": list(BRAKING_SPEEDS_MPH)},
    "value": {"unit": "m/s^2", "meaning": "cruise_slc_deceleration_magnitude"},
  },
  "following": {
    "speed": {"unit": "mph", "values": list(FOLLOWING_SPEEDS_MPH)},
    "value": {"unit": "s", "meaning": "base_time_headway"},
  },
}
_CATEGORY_SPEEDS_MPH = {
  "acceleration": ACCELERATION_SPEEDS_MPH,
  "braking": BRAKING_SPEEDS_MPH,
  "following": FOLLOWING_SPEEDS_MPH,
}

_ACCELERATION_PROFILE_IDS = {
  "standard": 0,
  "eco": 1,
  "sport": 2,
  "sport_plus": 3,
}

_PERSONALITY_REFERENCE_PRESETS = {
  "traffic": {"acceleration": "eco", "braking": "standard", "following": "close"},
  "aggressive": {"acceleration": "sport_plus", "braking": "sport", "following": "close"},
  "standard": {"acceleration": "standard", "braking": "standard", "following": "medium"},
  "relaxed": {"acceleration": "eco", "braking": "eco", "following": "far"},
}

_V1_PROFILE_AXES = {
  "acceleration": {
    "speed": {"unit": "mph", "values": list(_V1_ACCELERATION_SPEEDS_MPH)},
    "value": {"unit": "m/s^2", "meaning": "maximum_requested_acceleration"},
  },
  "braking": {
    "speed": {"unit": "mph", "values": list(_V1_ACCELERATION_SPEEDS_MPH)},
    "value": {"unit": "m/s^2", "meaning": "cruise_slc_deceleration_magnitude"},
  },
  "following": {
    "speed": {"unit": "mph", "values": list(FOLLOWING_SPEEDS_MPH)},
    "value": {"unit": "s", "meaning": "base_time_headway"},
  },
}


def _acceleration_preset_curve(preset: str, ev_tuning: bool, truck_tuning: bool) -> list[float]:
  # Import lazily so persisted-schema parsing remains independent of controls/runtime modules.
  from openpilot.starpilot.common.accel_profile import get_accel_profile_curve_values

  # Profile customisation resolves an impossible dual flag deterministically in favour of EV.
  return get_accel_profile_curve_values(
    _ACCELERATION_PROFILE_IDS[preset], bool(ev_tuning), bool(truck_tuning) and not bool(ev_tuning)
  )


def default_personality_profiles(ev_tuning: bool, truck_tuning: bool = False) -> dict[str, dict]:
  del ev_tuning, truck_tuning
  return {
    personality: {
      "acceleration": {"preset": "standard", "curve": []},
      "braking": {"preset": "standard", "curve": []},
      "following": {"preset": "medium", "curve": []},
    }
    for personality in PERSONALITY_IDS
  }


def profile_document(profiles: dict[str, dict], *, enabled: bool) -> dict:
  if type(enabled) is not bool:
    raise ValueError("enabled must be a JSON boolean")
  return {
    "schemaVersion": PROFILE_SCHEMA_VERSION,
    "enabled": enabled,
    "axes": deepcopy(PROFILE_AXES),
    "profiles": deepcopy(profiles),
  }


def _decode_json(raw):
  if isinstance(raw, bytes):
    try:
      raw = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
      return None
  if isinstance(raw, str):
    try:
      raw = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
      return None
  return raw


def _validated_category_with_length(
  category: str,
  raw_category,
  expected_length: int,
  curve_bounds: dict[str, tuple[float, float]],
  legacy_curve_bounds: dict[str, tuple[float, float]] | None = None,
) -> dict | None:
  if category not in _CATEGORY_SPECS or not isinstance(raw_category, dict):
    return None
  keys = set(raw_category)
  has_legacy_curve = "legacyCurve" in keys
  if keys != ({"preset", "curve", "legacyCurve"} if has_legacy_curve else {"preset", "curve"}):
    return None
  presets, _ = _CATEGORY_SPECS[category]
  preset = raw_category.get("preset")
  curve = raw_category.get("curve")
  if not isinstance(preset, str) or preset not in presets or not isinstance(curve, list):
    return None
  if preset != "custom":
    return {"preset": preset, "curve": []} if not curve and not has_legacy_curve else None
  if len(curve) != expected_length:
    return None

  minimum, maximum = curve_bounds[category]
  values = []
  for raw_value in curve:
    if isinstance(raw_value, bool) or not isinstance(raw_value, numbers.Real):
      return None
    value = float(raw_value)
    if not math.isfinite(value) or not minimum <= value <= maximum:
      return None
    values.append(round(value, 4))
  validated = {"preset": preset, "curve": values}
  if has_legacy_curve:
    legacy_curve = raw_category.get("legacyCurve")
    if category not in ("acceleration", "braking") or expected_length != len(ACCELERATION_SPEEDS_MPH) or not isinstance(legacy_curve, list):
      return None
    if len(legacy_curve) != len(_V1_ACCELERATION_SPEEDS_MPH):
      return None
    legacy_minimum, legacy_maximum = (legacy_curve_bounds or curve_bounds)[category]
    legacy_values = []
    for raw_value in legacy_curve:
      if isinstance(raw_value, bool) or not isinstance(raw_value, numbers.Real):
        return None
      value = float(raw_value)
      if not math.isfinite(value) or not legacy_minimum <= value <= legacy_maximum:
        return None
      legacy_values.append(round(value, 4))
    validated["legacyCurve"] = legacy_values
  return validated


def _validated_category(category: str, raw_category) -> dict | None:
  expected_length = _CATEGORY_SPECS.get(category, ((), 0))[1]
  return _validated_category_with_length(category, raw_category, expected_length, _V2_CURVE_BOUNDS, _V1_CURVE_BOUNDS)


def _schema_values_equal(actual, expected) -> bool:
  if type(actual) is not type(expected):
    return False
  if isinstance(expected, dict):
    return set(actual) == set(expected) and all(_schema_values_equal(actual[key], expected[key]) for key in expected)
  if isinstance(expected, list):
    return len(actual) == len(expected) and all(_schema_values_equal(value, reference) for value, reference in zip(actual, expected, strict=True))
  return actual == expected


def _strict_document(
  raw_document,
  schema_version: int,
  axes: dict,
  category_lengths: dict[str, int],
  curve_bounds: dict[str, tuple[float, float]],
  legacy_curve_bounds: dict[str, tuple[float, float]] | None = None,
) -> dict | None:
  decoded = _decode_json(raw_document)
  if not isinstance(decoded, dict) or set(decoded) != {"schemaVersion", "enabled", "axes", "profiles"}:
    return None
  if type(decoded["schemaVersion"]) is not int or decoded["schemaVersion"] != schema_version:
    return None
  if type(decoded["enabled"]) is not bool or not _schema_values_equal(decoded["axes"], axes):
    return None

  raw_profiles = decoded["profiles"]
  if not isinstance(raw_profiles, dict) or set(raw_profiles) != set(PERSONALITY_IDS):
    return None
  profiles = {}
  for personality in PERSONALITY_IDS:
    raw_profile = raw_profiles.get(personality)
    if not isinstance(raw_profile, dict) or set(raw_profile) != set(_CATEGORY_SPECS):
      return None
    profile = {}
    for category in _CATEGORY_SPECS:
      validated = _validated_category_with_length(
        category, raw_profile.get(category), category_lengths[category], curve_bounds, legacy_curve_bounds,
      )
      if validated is None:
        return None
      profile[category] = validated
    profiles[personality] = profile
  return {
    "schemaVersion": schema_version,
    "enabled": decoded["enabled"],
    "axes": deepcopy(axes),
    "profiles": profiles,
  }


def strict_profile_document(raw_document) -> dict | None:
  return _strict_document(
    raw_document,
    PROFILE_SCHEMA_VERSION,
    PROFILE_AXES,
    {category: expected_length for category, (_, expected_length) in _CATEGORY_SPECS.items()},
    _V2_CURVE_BOUNDS,
    _V1_CURVE_BOUNDS,
  )


def migrate_profile_document(raw_document) -> dict | None:
  current = strict_profile_document(raw_document)
  if current is not None:
    return current

  legacy = _strict_document(
    raw_document,
    1,
    _V1_PROFILE_AXES,
    {"acceleration": len(_V1_ACCELERATION_SPEEDS_MPH), "braking": len(_V1_ACCELERATION_SPEEDS_MPH), "following": len(FOLLOWING_SPEEDS_MPH)},
    _V1_CURVE_BOUNDS,
  )
  if legacy is None:
    return None

  migrated_profiles = deepcopy(legacy["profiles"])
  for profile in migrated_profiles.values():
    for category in ("acceleration", "braking"):
      config = profile[category]
      if config["preset"] != "custom":
        continue
      legacy_curve = list(config["curve"])
      minimum, maximum = CURVE_BOUNDS[category]
      config["curve"] = [
        round(min(max(_linear_interp(float(speed_mph), _V1_ACCELERATION_SPEEDS_MPH, config["curve"]), minimum), maximum), 4)
        for speed_mph in ACCELERATION_SPEEDS_MPH
      ]
      config["legacyCurve"] = legacy_curve
  return strict_profile_document(profile_document(migrated_profiles, enabled=legacy["enabled"]))


def synchronise_profile_document_enabled(
  raw_document, enabled: bool, ev_tuning: bool, truck_tuning: bool = False,
) -> dict | None:
  if type(enabled) is not bool:
    raise ValueError("enabled must be a JSON boolean")
  document = migrate_profile_document(raw_document)
  if document is None:
    if raw_document is not None or not enabled:
      return None
    return profile_document(default_personality_profiles(ev_tuning, truck_tuning), enabled=True)
  document["enabled"] = enabled
  return strict_profile_document(document)


def strict_personality_profiles(raw_document) -> dict[str, dict] | None:
  document = migrate_profile_document(raw_document)
  if document is None or not document["enabled"]:
    return None
  return deepcopy(document["profiles"])


def load_personality_profiles(raw_document, ev_tuning: bool, truck_tuning: bool = False) -> dict[str, dict]:
  document = migrate_profile_document(raw_document)
  return deepcopy(document["profiles"]) if document is not None else default_personality_profiles(ev_tuning, truck_tuning)


def serialize_personality_profiles(profiles, ev_tuning: bool, truck_tuning: bool = False, *, enabled: bool) -> str:
  del ev_tuning, truck_tuning
  document = profile_document(profiles, enabled=enabled)
  canonical = strict_profile_document(document)
  if canonical is None:
    raise ValueError("Longitudinal personality profiles must be complete and valid.")
  return json.dumps(canonical, separators=(",", ":"), sort_keys=True, allow_nan=False)


def update_personality_profile(
  profiles, personality: str, category: str, preset: str, curve, ev_tuning: bool, truck_tuning: bool = False,
) -> dict[str, dict]:
  if personality not in PERSONALITY_IDS:
    raise ValueError(f"Unknown personality: {personality}")
  if category not in _CATEGORY_SPECS:
    raise ValueError(f"Unknown profile category: {category}")
  base_document = profile_document(profiles, enabled=True)
  canonical = strict_profile_document(base_document)
  validated = _validated_category(category, {"preset": preset, "curve": curve})
  if validated is not None and preset == "custom":
    minimum, maximum = CURVE_BOUNDS[category]
    previous = canonical["profiles"][personality][category] if canonical is not None else None
    # Only the same point in a fully valid saved Custom curve is grandfathered.
    # Compare before rounding so a small out-of-range edit cannot masquerade as a no-op.
    for index, value in enumerate(curve):
      if not minimum <= value <= maximum and (
        previous is None or previous["preset"] != "custom" or value != previous["curve"][index]
      ):
        validated = None
        break
  if validated is None:
    minimum, maximum = CURVE_BOUNDS[category]
    presets, expected_length = _CATEGORY_SPECS[category]
    message = f"Invalid {category} profile: preset must be one of {', '.join(presets)} and curve must contain "
    message += f"{expected_length} finite numeric values between {minimum} and {maximum}."
    raise ValueError(message)

  if canonical is None:
    base = default_personality_profiles(ev_tuning, truck_tuning)
  else:
    base = canonical["profiles"]
  updated = deepcopy(base)
  previous = updated[personality][category]
  if preset == "custom" and previous["preset"] == "custom" and validated["curve"] == previous["curve"]:
    # A no-op submission is not consent to retire a preserved v1 runtime curve.
    return updated
  updated[personality][category] = validated
  return updated


def active_personality_id(traffic_mode: bool, personality) -> str | None:
  if type(traffic_mode) is not bool:
    return None
  if traffic_mode:
    return "traffic"
  if isinstance(personality, bool):
    return None
  raw = getattr(personality, "raw", personality)
  if isinstance(raw, bool) or not isinstance(raw, numbers.Integral):
    return None
  return {0: "aggressive", 1: "standard", 2: "relaxed"}.get(int(raw))


def resolve_personality_profile(raw_document, traffic_mode: bool, personality) -> dict | None:
  profiles = strict_personality_profiles(raw_document)
  personality_id = active_personality_id(traffic_mode, personality)
  if profiles is None or personality_id is None:
    return None
  return deepcopy(profiles[personality_id])


def resolve_personality_category(raw_document, traffic_mode: bool, personality, category: str) -> dict | None:
  profile = resolve_personality_profile(raw_document, traffic_mode, personality)
  if profile is None or category not in _CATEGORY_SPECS:
    return None
  config = profile[category]
  return None if config["preset"] == "dom_default" else deepcopy(config)


def category_curve(category: str, config: dict, ev_tuning: bool, truck_tuning: bool = False) -> list[float]:
  validated = _validated_category(category, config)
  if validated is None:
    raise ValueError(f"Invalid {category} profile configuration.")
  preset = validated["preset"]
  if preset == "dom_default":
    raise ValueError("Dom default resolves through the legacy controller path")
  if preset == "custom":
    return list(validated["curve"])
  if category == "acceleration":
    return _acceleration_preset_curve(preset, ev_tuning, truck_tuning)
  if category == "braking":
    return list(_BRAKING_PRESET_CURVES[preset])
  return list(FOLLOWING_PRESET_CURVES[preset])


def _sample_config_on_custom_axis(
  category: str, config: dict, ev_tuning: bool, truck_tuning: bool,
) -> list[float]:
  return [
    round(interpolate_category_curve(category, speed_mph * 0.44704, config, ev_tuning, truck_tuning), 4)
    for speed_mph in _CATEGORY_SPEEDS_MPH[category]
  ]


def personality_reference_curves(ev_tuning: bool, truck_tuning: bool = False) -> dict[str, dict[str, list[float]]]:
  return {
    personality: {
      category: _sample_config_on_custom_axis(
        category,
        {"preset": preset, "curve": []},
        ev_tuning,
        truck_tuning,
      )
      for category, preset in presets.items()
    }
    for personality, presets in _PERSONALITY_REFERENCE_PRESETS.items()
  }


def initial_custom_curve(
  category: str,
  current_config: dict,
  ev_tuning: bool,
  truck_tuning: bool,
  *,
  legacy_curve: list[float] | None = None,
) -> list[float]:
  if category not in _CATEGORY_SPECS or not isinstance(current_config, dict):
    raise ValueError("Unknown or malformed profile category")
  preset = current_config.get("preset")
  if preset == "dom_default":
    candidate = legacy_curve
    if category in ("acceleration", "braking") and isinstance(candidate, list) and len(candidate) == len(_V1_ACCELERATION_SPEEDS_MPH):
      candidate = [
        round(_linear_interp(float(speed_mph), _V1_ACCELERATION_SPEEDS_MPH, candidate), 4)
        for speed_mph in _CATEGORY_SPEEDS_MPH[category]
      ]
  elif preset == "custom":
    candidate = current_config.get("curve")
  elif isinstance(preset, str):
    candidate = _sample_config_on_custom_axis(category, {"preset": preset, "curve": []}, ev_tuning, truck_tuning)
    minimum, maximum = CURVE_BOUNDS[category]
    candidate = [round(min(max(value, minimum), maximum), 4) for value in candidate]
  else:
    candidate = None
  validated = _validated_category(category, {"preset": "custom", "curve": candidate})
  if validated is None:
    raise ValueError(f"Cannot initialize Custom {category} from the current selection")
  return validated["curve"]


def _linear_interp(value: float, breakpoints: tuple[float, ...], values: list[float]) -> float:
  if value <= breakpoints[0]:
    return float(values[0])
  if value >= breakpoints[-1]:
    return float(values[-1])
  index = next(index for index, point in enumerate(breakpoints[1:], start=1) if point >= value) - 1
  t = (value - breakpoints[index]) / float(breakpoints[index + 1] - breakpoints[index])
  return float(values[index] + t * (values[index + 1] - values[index]))


def interpolate_category_curve(
  category: str, v_ego: float, config: dict, ev_tuning: bool, truck_tuning: bool = False,
) -> float:
  if not isinstance(v_ego, numbers.Real) or isinstance(v_ego, bool) or not math.isfinite(float(v_ego)):
    raise ValueError("Vehicle speed must be finite")
  validated = _validated_category(category, config)
  if validated is None:
    raise ValueError(f"Invalid {category} profile configuration.")
  values = category_curve(category, validated, ev_tuning, truck_tuning)
  if "legacyCurve" in validated:
    return _linear_interp(float(v_ego), _NATIVE_ACCELERATION_SPEEDS_MS, validated["legacyCurve"])
  if category == "acceleration":
    from openpilot.starpilot.common.accel_profile import interpolate_accel_profile
    breakpoints = _NATIVE_ACCELERATION_SPEEDS_MS if validated["preset"] != "custom" else tuple(
      speed * 0.44704 for speed in ACCELERATION_SPEEDS_MPH
    )
    return interpolate_accel_profile(float(v_ego), values, breakpoints)
  return _linear_interp(float(v_ego) / 0.44704, _CATEGORY_SPEEDS_MPH[category], values)
