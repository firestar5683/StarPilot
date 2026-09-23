"""Shared speed-limit offset selection for controls and the on-road UI."""

from collections.abc import Sequence


_OFFSET_UPPER_BOUNDS_IMPERIAL = (11.2, 15.2, 19.6, 24.1, 28.6, 33.1, 44.2)
_OFFSET_UPPER_BOUNDS_METRIC = (8.1, 13.6, 16.4, 21.9, 27.5, 33.1, 38.9)


def get_speed_limit_offset(target_speed: float, is_metric: bool, offsets: Sequence[float]) -> float:
  """Return the configured offset for a speed limit, with speeds and offsets in m/s."""
  if target_speed < 0:
    return 0.0

  upper_bounds = _OFFSET_UPPER_BOUNDS_METRIC if is_metric else _OFFSET_UPPER_BOUNDS_IMPERIAL
  for upper_bound, offset in zip(upper_bounds, offsets):
    if target_speed < upper_bound:
      return float(offset)
  return 0.0
