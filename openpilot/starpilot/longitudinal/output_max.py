"""Shared saved ceiling for the final longitudinal control output."""

from dataclasses import dataclass
import math

from openpilot.starpilot.saved_source import read_saved

KEY = "LongitudinalMaxOutputAcceleration"
DEFAULT = 4.0
MINIMUM = 0.1
MAXIMUM = 4.0
MAX_BYTES = 128
REFRESH_NS = 1_000_000_000


def capability(cp) -> tuple | None:
  try:
    if (cp is None or not cp.openpilotLongitudinalControl or cp.notCar or cp.passive or cp.dashcamOnly or
        not cp.carFingerprint):
      return None
    return (str(cp.carFingerprint), str(cp.brand), bool(cp.openpilotLongitudinalControl), bool(cp.pcmCruise), int(cp.flags),
            tuple((str(c.safetyModel), int(c.safetyParam)) for c in cp.safetyConfigs))
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None


@dataclass(frozen=True)
class SavedMaximum:
  raw: bytes | None
  value: float | None
  readable: bool

  @property
  def valid(self) -> bool:
    return self.readable and self.value is not None


def read_maximum(params) -> SavedMaximum:
  try:
    raw, readable = read_saved(params, KEY, MAX_BYTES)
  except (OSError, TypeError, ValueError):
    return SavedMaximum(None, None, False)
  if not readable:
    return SavedMaximum(raw, None, False)
  if raw is None:
    return SavedMaximum(None, DEFAULT, True)
  try:
    value = float(raw)
    if math.isfinite(value) and MINIMUM <= value <= MAXIMUM:
      return SavedMaximum(raw, value, True)
  except (TypeError, ValueError, OverflowError):
    pass
  return SavedMaximum(raw, None, True)


class OutputMaximum:
  """Refresh a saved ceiling while retaining the last valid value on read failure."""

  def __init__(self, params, cp):
    self.params = params
    self.cp = cp
    self.maximum = DEFAULT
    self.saved = SavedMaximum(None, None, False)
    self.last_attempt_ns: int | None = None

  def sample(self, now_ns: int) -> float:
    if type(now_ns) is not int or now_ns < 0:
      return self.maximum
    if self.last_attempt_ns is None or now_ns < self.last_attempt_ns or now_ns - self.last_attempt_ns >= REFRESH_NS:
      self.last_attempt_ns = now_ns
      self.saved = read_maximum(self.params)
      if self.saved.valid:
        self.maximum = self.saved.value
    return self.maximum


def final_output(acceleration: float, owner: OutputMaximum | None, now_ns: int) -> float:
  """Cap the returned command without changing the controller's internal state."""
  maximum = owner.sample(now_ns) if owner is not None and capability(owner.cp) is not None else DEFAULT
  return float(min(acceleration, maximum))
