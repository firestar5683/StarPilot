"""Same-frame adjacent width for automatic lane changes."""

import bisect
import math
from statistics import median

from openpilot.selfdrive.modeld.constants import ModelConstants


def _points(line):
  xs, ys = list(line.x), list(line.y)
  if (len(xs) != ModelConstants.IDX_N or len(ys) != ModelConstants.IDX_N or
      not all(math.isfinite(value) for value in xs + ys) or
      any(b <= a for a, b in zip(xs, xs[1:], strict=False))):
    return None
  return xs, ys


def _at(points, x):
  xs, ys = points
  if x <= xs[0]:
    return ys[0]
  if x >= xs[-1]:
    return ys[-1]
  index = bisect.bisect_left(xs, x)
  ratio = (x - xs[index - 1]) / (xs[index] - xs[index - 1])
  return ys[index - 1] + ratio * (ys[index] - ys[index - 1])


def adjacent_lane_available(model, direction: int, minimum_width_m: float) -> bool:
  """Compare median adjacent width with the saved minimum."""
  try:
    if not math.isfinite(minimum_width_m) or not 0 <= minimum_width_m <= 4.572 or direction not in (-1, 1):
      return False
    inner, outer, edge = ((1, 0, 0) if direction == -1 else (2, 3, 1))
    if (len(model.laneLines) != 4 or len(model.roadEdges) != 2 or len(model.laneLineProbs) != 4 or
        len(model.laneLineStds) != 4 or len(model.roadEdgeStds) != 2):
      return False
    if (not all(math.isfinite(value) and 0 <= value <= 1 for value in model.laneLineProbs) or
        not all(math.isfinite(value) and value >= 0 for value in list(model.laneLineStds) + list(model.roadEdgeStds))):
      return False
    inner_points = _points(model.laneLines[inner])
    outer_points = _points(model.laneLines[outer])
    edge_points = _points(model.roadEdges[edge])
    if inner_points is None or outer_points is None or edge_points is None:
      return False
    xs, ys = inner_points
    lane_distances = [abs(y - _at(outer_points, x)) for x, y in zip(xs, ys, strict=True)]
    edge_distances = [abs(y - _at(edge_points, x)) for x, y in zip(xs, ys, strict=True)]
    if not all(math.isfinite(value) for value in lane_distances + edge_distances):
      return False
    width = median(lane_distances)
    if median(edge_distances) < width:
      width = 0.0
    return width >= minimum_width_m
  except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
    return False
