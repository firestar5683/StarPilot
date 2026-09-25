"""Mach-E default model preview, before the upstream actuator limits."""

import math


def blend_curvature(desired: float, predicted: float, current: float) -> float:
  if not all(math.isfinite(value) for value in (desired, predicted, current)):
    return desired
  blend = 0.4
  if desired * predicted <= 0.0:
    blend = 0.0
  elif current * predicted > 0.0 and abs(current) > abs(desired) and abs(predicted) > abs(desired):
    blend *= abs(desired) / abs(predicted)
  return predicted * blend + desired * (1.0 - blend)
