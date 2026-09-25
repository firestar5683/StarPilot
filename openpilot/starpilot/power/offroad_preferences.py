"""Strict optional parked-power document; invalid or absent means stock policy."""

from dataclasses import dataclass
import json
import os
import stat
from typing import Any


KEY = "OffroadPowerPreferences"
MAX_BYTES = 512
STOCK_HOURS = 30
STOCK_VOLTS_TENTHS = 118


@dataclass(frozen=True)
class PowerPolicy:
  enabled: bool = False
  delay_hours: int = STOCK_HOURS
  cutoff_tenths: int = STOCK_VOLTS_TENTHS


@dataclass(frozen=True)
class SavedPower:
  raw: bytes | None
  policy: PowerPolicy = PowerPolicy()
  valid: bool = True
  readable: bool = True


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
  value: dict[str, object] = {}
  for key, item in pairs:
    if key in value:
      raise ValueError("duplicate parked-power field")
    value[key] = item
  return value


def decode(raw: bytes) -> PowerPolicy | None:
  if len(raw) > MAX_BYTES:
    return None
  try:
    data = json.loads(raw, parse_constant=lambda _value: None, object_pairs_hook=_unique_object)
  except (UnicodeDecodeError, ValueError, TypeError, RecursionError, OverflowError):
    return None
  if not isinstance(data, dict) or set(data) != {"version", "enabled", "delayHours", "cutoffTenths"}:
    return None
  version, enabled = data["version"], data["enabled"]
  hours, tenths = data["delayHours"], data["cutoffTenths"]
  if (type(version) is not int or version != 1 or type(enabled) is not bool or
      type(hours) is not int or not 1 <= hours <= 30 or
      type(tenths) is not int or not 118 <= tenths <= 125):
    return None
  return PowerPolicy(enabled, hours, tenths)


def encode(policy: PowerPolicy) -> bytes:
  return json.dumps(to_value(policy), sort_keys=True, separators=(",", ":")).encode()


def to_value(policy: PowerPolicy) -> dict[str, int | bool]:
  if (type(policy.enabled) is not bool or type(policy.delay_hours) is not int or
      type(policy.cutoff_tenths) is not int or not 1 <= policy.delay_hours <= 30 or
      not 118 <= policy.cutoff_tenths <= 125):
    raise ValueError("invalid parked-power policy")
  return {"version": 1, "enabled": policy.enabled, "delayHours": policy.delay_hours,
          "cutoffTenths": policy.cutoff_tenths}


def read_saved(params: Any) -> SavedPower:
  try:
    fd = os.open(params.get_param_path(KEY), os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
  except FileNotFoundError:
    return SavedPower(None)
  except (AttributeError, OSError, TypeError, ValueError):
    return SavedPower(None, valid=False, readable=False)
  try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
      return SavedPower(None, valid=False, readable=False)
    raw = os.read(fd, MAX_BYTES + 1)
  except OSError:
    return SavedPower(None, valid=False, readable=False)
  finally:
    os.close(fd)
  if len(raw) > MAX_BYTES:
    return SavedPower(raw, valid=False, readable=False)
  policy = decode(raw)
  return SavedPower(raw, policy if policy is not None else PowerPolicy(), valid=policy is not None)


def effective(saved: SavedPower) -> PowerPolicy:
  return saved.policy if saved.readable and saved.valid and saved.policy.enabled else PowerPolicy()
