"""Strict saved display choices; absent/invalid values preserve native policy."""

from dataclasses import dataclass
import os
import stat
from typing import Any


MASTER = "StarPilotDisplayPreferencesEnabled"
BRIGHTNESS = ("ScreenBrightness", "ScreenBrightnessOnroad")
TIMEOUTS = ("ScreenTimeout", "ScreenTimeoutOnroad")
KEYS = (MASTER, *BRIGHTNESS, *TIMEOUTS)
MAX_RAW_BYTES = 16
AUTO = 101


@dataclass(frozen=True)
class SavedChoice:
  raw: bytes | None
  value: int | None
  readable: bool = True
  unsupported: bool = False

  @property
  def valid(self) -> bool:
    return self.readable and self.value is not None and not self.unsupported


def default_value(key: str, *, large: bool) -> int:
  if key == MASTER:
    return 0
  if key in BRIGHTNESS:
    return AUTO
  if key == "ScreenTimeout":
    return 30
  if key == "ScreenTimeoutOnroad":
    return 10 if large else 5
  raise KeyError(key)


def read_choice(params: Any, key: str, *, large: bool) -> SavedChoice:
  if key not in KEYS:
    raise KeyError(key)
  try:
    descriptor = os.open(params.get_param_path(key), os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
  except FileNotFoundError:
    return SavedChoice(None, default_value(key, large=large))
  except (AttributeError, OSError, TypeError, ValueError):
    return SavedChoice(None, None, False)
  try:
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
      return SavedChoice(None, None, False)
    raw = os.read(descriptor, MAX_RAW_BYTES + 1)
  except OSError:
    return SavedChoice(None, None, False)
  finally:
    os.close(descriptor)
  if len(raw) > MAX_RAW_BYTES:
    return SavedChoice(raw, None, False)
  if not raw or not raw.isascii() or not raw.isdigit() or (len(raw) > 1 and raw[0] == ord("0")):
    return SavedChoice(raw, None)
  value = int(raw)
  if key == MASTER:
    return SavedChoice(raw, value if value in (0, 1) else None)
  if key in BRIGHTNESS:
    return SavedChoice(raw, value if 5 <= value <= 100 or value in (0, AUTO) else None,
                       unsupported=value == 0)
  return SavedChoice(raw, value if 5 <= value <= 60 and value % 5 == 0 else None)


@dataclass(frozen=True)
class DisplayPreferences:
  enabled: bool = False
  parked_brightness: int = AUTO
  driving_brightness: int = AUTO
  parked_timeout: int = 30
  driving_timeout: int = 10


def read_preferences(params: Any, *, large: bool) -> DisplayPreferences:
  master = read_choice(params, MASTER, large=large)
  if not master.valid or master.value != 1:
    return DisplayPreferences(driving_timeout=default_value("ScreenTimeoutOnroad", large=large))
  values = {key: read_choice(params, key, large=large) for key in (*BRIGHTNESS, *TIMEOUTS)}
  def effective(key: str) -> int:
    saved = values[key]
    return saved.value if saved.valid and saved.value is not None else default_value(key, large=large)
  return DisplayPreferences(enabled=True,
                            parked_brightness=effective("ScreenBrightness"),
                            driving_brightness=effective("ScreenBrightnessOnroad"),
                            parked_timeout=effective("ScreenTimeout"),
                            driving_timeout=effective("ScreenTimeoutOnroad"))
