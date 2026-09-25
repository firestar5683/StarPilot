"""Pure angle lane-centering trim adapted from BluePilot bp-dev e22afa6b.

Alan Polk and ghbarker; the source also credits StarPilot/u/jc01rho.
See ../CREDITS.md, ../LICENSE and ../LICENSE.md. Geometry/confidence/fallback,
filter and slew follow lane_center_trim.py; this module receives immutable arrays
instead of a host model. Stale geometry and driver pressure additionally suppress
trim, and nonfinite confidence cannot create correction.
"""
from dataclasses import dataclass
import math
from ..params.trim import DEFAULTS, BOUNDS


def clip(value, low, high):
  return max(low, min(high, value))


def interp(value, xs, ys):
  if value <= xs[0]:
    return ys[0]
  for index in range(1, len(xs)):
    if value < xs[index]:
      return ys[index - 1] + (ys[index] - ys[index - 1]) * (value - xs[index - 1]) / (xs[index] - xs[index - 1])
  return ys[-1]


@dataclass(frozen=True)
class TrimConfig:
  enabled: bool = DEFAULTS["enabled"]
  offset_m: float = DEFAULTS["offset_m"]
  gain: float = DEFAULTS["gain"]


@dataclass(frozen=True)
class LaneGeometry:
  position_x: tuple = ()
  position_y: tuple = ()
  left_x: tuple = ()
  left_y: tuple = ()
  right_x: tuple = ()
  right_y: tuple = ()
  probabilities: tuple = ()
  standard_deviations: tuple = ()
  fresh: bool = False


def sample(xs, ys, distance):
  if (not isinstance(xs, tuple) or not isinstance(ys, tuple) or len(xs) < 2 or len(xs) != len(ys) or
      not all(math.isfinite(v) for v in (*xs, *ys)) or not all(b > a for a, b in zip(xs, xs[1:], strict=False))):
    return None
  return interp(distance, xs, ys)


class LaneCenterTrim:
  def __init__(self):
    self.correction = 0.0

  def reset(self):
    self.correction = 0.0

  def update(self, requested, speed, geometry, config, *, active, lane_change, steering_pressed=False):
    try:
      valid = (isinstance(config, TrimConfig) and config.enabled is True and active and not lane_change and
               not steering_pressed and isinstance(geometry, LaneGeometry) and geometry.fresh is True and
               math.isfinite(requested) and math.isfinite(speed) and speed >= 0.0 and
               math.isfinite(config.offset_m) and BOUNDS["offset_m"][0] <= config.offset_m <= BOUNDS["offset_m"][1] and
               math.isfinite(config.gain) and BOUNDS["gain"][0] <= config.gain <= BOUNDS["gain"][1])
      authority = interp(speed, BOUNDS["speed_mps"], BOUNDS["speed_authority"]) if valid else 0.0
      if not valid or authority <= 0.0:
        self.reset()
        return requested
      distance = clip(speed, *BOUNDS["lookahead_m"])
      model_y = sample(geometry.position_x, geometry.position_y, distance)
      if model_y is None:
        self.reset()
        return requested
      # Bad lane-only geometry retains the source's model-position/offset fallback.
      scale, center = self.lane_blend(geometry, distance)
      error = scale * (center - model_y) + config.offset_m
      raw = 2.0 * error / distance ** 2
      target = clip(raw, -BOUNDS["raw_correction"], BOUNDS["raw_correction"]) * config.gain * authority
      alpha = 1.0 - math.exp(-BOUNDS["period_s"] / BOUNDS["tau_s"])
      filtered = alpha * target + (1.0 - alpha) * self.correction
      self.correction = clip(filtered, self.correction - BOUNDS["correction_delta"], self.correction + BOUNDS["correction_delta"])
      return requested + self.correction
    except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
      self.reset()
      return requested

  def lane_blend(self, geometry, distance):
    try:
      left = sample(geometry.left_x, geometry.left_y, distance)
      right = sample(geometry.right_x, geometry.right_y, distance)
      probs, stds = geometry.probabilities, geometry.standard_deviations
      if (left is None or right is None or not isinstance(probs, tuple) or not isinstance(stds, tuple) or
          len(probs) != 2 or len(stds) != 2 or not all(math.isfinite(p) and 0.0 <= p <= 1.0 for p in probs) or
          not all(math.isfinite(s) and s >= 0.0 for s in stds)):
        return 0.0, 0.0
      confidence = min(*probs, interp(right - left, BOUNDS["width_m"], BOUNDS["width_tolerance"]),
                       interp(max(stds), BOUNDS["std"], BOUNDS["std_tolerance"]))
      scale = clip(interp(confidence, BOUNDS["confidence"], (0.0, 1.0)), 0.0, 1.0)
      return scale, 0.5 * (left + right)
    except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
      return 0.0, 0.0
