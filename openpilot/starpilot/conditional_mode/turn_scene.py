"""Frozen low-speed committed-turn predicate over qualified current evidence.

The caller owns producer timestamps and must not renew a held model/car sample
from a repeated poll. Missing evidence on the active branch remains unknown.
"""

from __future__ import annotations

import math


MAX_TURN_SPEED_MPS = 15.0 * 0.44704
MIN_STEERING_ANGLE_DEG = 45.0


def _finite(value: object, low: float, high: float) -> float | None:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    return None
  try:
    number = float(value)
  except (OverflowError, ValueError):
    return None
  return number if math.isfinite(number) and low <= number <= high else None


def committed_turn_scene(*, speed_mps: object, standstill: object, left_blinker: object,
                         right_blinker: object, steering_angle_deg: object,
                         driving_in_curve: object) -> bool | None:
  """Return a known turn veto, known absence, or unknown from missing evidence.

  This matches the current stop detector's evidence policy. The frozen
  untyped function could decide a 45-degree turn without model data; here the
  active branch still requires a qualified measured-curve boolean so absent
  model evidence cannot silently become a known scene.
  """
  speed = _finite(speed_mps, 0.0, 80.0)
  if (speed is None or type(standstill) is not bool or type(left_blinker) is not bool or
      type(right_blinker) is not bool):
    return None
  if standstill or speed > MAX_TURN_SPEED_MPS or not (left_blinker or right_blinker):
    return False
  angle = _finite(steering_angle_deg, -720.0, 720.0)
  if angle is None or type(driving_in_curve) is not bool:
    return None
  return abs(angle) >= MIN_STEERING_ANGLE_DEG or driving_in_curve
