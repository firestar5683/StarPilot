"""Experimental same-frame adjacent-lane evidence for automatic lane changes.

These conservative thresholds are development-only. No saved preference alone
qualifies a roadway or replaces a driver blindspot check.
"""

import math
from openpilot.selfdrive.modeld.constants import ModelConstants


MIN_PROBABILITY = 0.8
MAX_LINE_STD_M = 0.5
MAX_EDGE_STD_M = 0.5
SAMPLE_X_M = (5., 10., 20., 30., 40.)


def _at(line, x: float) -> float | None:
  try:
    xs, ys = list(line.x), list(line.y)
    if len(xs) != ModelConstants.IDX_N or len(ys) != ModelConstants.IDX_N or not all(math.isfinite(v) for v in xs + ys):
      return None
    if any(b <= a for a, b in zip(xs, xs[1:], strict=False)) or not xs[0] <= x <= xs[-1]:
      return None
    for i in range(1, len(xs)):
      if xs[i] >= x:
        ratio = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
        return ys[i - 1] + ratio * (ys[i] - ys[i - 1])
  except (AttributeError, TypeError, ValueError, OverflowError):
    return None
  return None


def adjacent_lane_available(model, direction: int, minimum_width_m: float) -> bool:
  """Read only lane/edge arrays from the model message just filled this frame."""
  if not math.isfinite(minimum_width_m) or not 0 <= minimum_width_m <= 4.572:
    return False
  if direction not in (-1, 1):
    return False
  try:
    inner, outer, edge = ((1, 0, 0) if direction == -1 else (2, 3, 1))
    lines = model.laneLines
    edges = model.roadEdges
    if (len(lines) != 4 or len(edges) != 2 or len(model.laneLineProbs) != 4 or
        len(model.laneLineStds) != 4 or len(model.roadEdgeStds) != 2):
      return False
    for index in (inner, outer):
      if not (math.isfinite(model.laneLineProbs[index]) and MIN_PROBABILITY <= model.laneLineProbs[index] <= 1.0 and
              math.isfinite(model.laneLineStds[index]) and 0 <= model.laneLineStds[index] <= MAX_LINE_STD_M):
        return False
    if not (math.isfinite(model.roadEdgeStds[edge]) and 0 <= model.roadEdgeStds[edge] <= MAX_EDGE_STD_M):
      return False
    for x in SAMPLE_X_M:
      y_inner, y_outer, y_edge = (_at(lines[inner], x), _at(lines[outer], x), _at(edges[edge], x))
      if y_inner is None or y_outer is None or y_edge is None:
        return False
      if direction == -1:
        if not (y_edge < y_outer < y_inner and y_inner - y_outer >= minimum_width_m and y_outer - y_edge >= 0.5):
          return False
      elif not (y_inner < y_outer < y_edge and y_outer - y_inner >= minimum_width_m and y_edge - y_outer >= 0.5):
        return False
    return True
  except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
    return False
