"""Saved display-unit increments for Card-owned, non-PCM cruise."""

from dataclasses import dataclass
import math

from openpilot.starpilot.saved_source import read_saved


@dataclass(frozen=True)
class CruiseIntervals:
  short: float = 1.0
  held: float = 5.0


def _increment(raw: bytes | None, fallback: float) -> float:
  if raw is None:
    return fallback
  try:
    value = float(raw)
  except (ValueError, OverflowError):
    return fallback
  return value if math.isfinite(value) and 1.0 <= value <= 150.0 else fallback


def read_cruise_intervals(params, *, pcm_cruise: bool) -> CruiseIntervals:
  if pcm_cruise:
    return CruiseIntervals()
  short, short_readable = read_saved(params, "CustomCruise", 16)
  held, held_readable = read_saved(params, "CustomCruiseLong", 16)
  return CruiseIntervals(_increment(short, 1.0) if short_readable else 1.0,
                         _increment(held, 5.0) if held_readable else 5.0)
