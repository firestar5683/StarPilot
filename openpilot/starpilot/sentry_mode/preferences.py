"""Strict optional saved Sentry motion policy; no legacy-key adoption."""

from dataclasses import dataclass, field
import json
import math
from typing import Any

from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.sentry_mode.policy import Settings


KEY = "SentryMotionPreferences"
MAX_BYTES = 512


@dataclass(frozen=True)
class Preferences:
  enabled: bool = False
  settings: Settings = field(default_factory=Settings)


@dataclass(frozen=True)
class SavedPreferences:
  raw: bytes | None
  readable: bool
  valid: bool
  preferences: Preferences = field(default_factory=Preferences)


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
  result: dict[str, object] = {}
  for key, value in pairs:
    if key in result:
      raise ValueError("duplicate Sentry preference")
    result[key] = value
  return result


def decode(raw: bytes) -> Preferences | None:
  if len(raw) > MAX_BYTES:
    return None
  try:
    data = json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    if not isinstance(data, dict) or set(data) != {"version", "enabled", "sensitivity", "warningTimeSeconds"}:
      return None
    if type(data["version"]) is not int or data["version"] != 1 or type(data["enabled"]) is not bool:
      return None
    sensitivity, warning = data["sensitivity"], data["warningTimeSeconds"]
    if (type(sensitivity) not in (float, int) or type(warning) not in (float, int) or
        not math.isfinite(sensitivity) or not math.isfinite(warning)):
      return None
    return Preferences(data["enabled"], Settings(float(sensitivity), float(warning)))
  except (UnicodeDecodeError, ValueError, TypeError, OverflowError, RecursionError):
    return None


def encode(preferences: Preferences) -> bytes:
  if not isinstance(preferences, Preferences) or type(preferences.enabled) is not bool:
    raise ValueError("invalid Sentry preferences")
  settings = Settings(preferences.settings.sensitivity, preferences.settings.warning_time_seconds)
  data = {"version": 1, "enabled": preferences.enabled,
          "sensitivity": settings.sensitivity, "warningTimeSeconds": settings.warning_time_seconds}
  raw = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
  if len(raw) > MAX_BYTES:
    raise ValueError("oversized Sentry preferences")
  return raw


def read_preferences(params: Any) -> SavedPreferences:
  raw, readable = read_saved(params, KEY, MAX_BYTES)
  if not readable:
    return SavedPreferences(raw, False, False)
  if raw is None:
    return SavedPreferences(None, True, True)
  preferences = decode(raw)
  return SavedPreferences(raw, True, preferences is not None, preferences or Preferences())


def enabled(params: Any) -> bool:
  saved = read_preferences(params)
  return saved.readable and saved.valid and saved.preferences.enabled
