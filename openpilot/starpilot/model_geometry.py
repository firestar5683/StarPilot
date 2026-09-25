"""Validated shared model geometry; no control authority or mutable state."""

import math

ORIGIN_ROUNDOFF_M = 1e-6


def normalized_origin(distances: tuple) -> tuple:
  """Only remove sub-micrometre model-origin roundoff; callers validate all geometry."""
  if distances and _finite(distances[0], low=-ORIGIN_ROUNDOFF_M, high=0.0) is not None and distances[0] < 0:
    return (0.0, *distances[1:])
  return distances


def _finite(value: object, *, low: float, high: float) -> float | None:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    return None
  try:
    result = float(value)
  except (OverflowError, ValueError):
    return None
  return result if math.isfinite(result) and low <= result <= high else None


def road_curvature(model: object, speed_mps: float) -> tuple[float, float] | None:
  """Exact frozen max-|orientationRate.z * velocity.x| selection.

  The original helper divides by max(vEgo, 1)^2 and floors time at 1 s.
  Invalid or incomplete current model arrays remain unknown.
  """
  speed = _finite(speed_mps, low=0.0, high=80.0)
  if speed is None:
    return None
  try:
    rates = tuple(model.orientationRate.z)
    times = tuple(model.orientationRate.t)
    velocities = tuple(model.velocity.x)
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None
  if not len(rates) == len(times) == len(velocities) == 33:
    return None
  triples = []
  for rate, timestamp, velocity in zip(rates, times, velocities, strict=True):
    r = _finite(rate, low=-10.0, high=10.0)
    t = _finite(timestamp, low=0.0, high=20.0)
    v = _finite(velocity, low=0.0, high=100.0)
    if r is None or t is None or v is None:
      return None
    triples.append((r * v, t))
  acceleration, timestamp = max(triples, key=lambda pair: abs(pair[0]))
  return acceleration / max(speed, 1.0) ** 2, max(timestamp, 1.0)
