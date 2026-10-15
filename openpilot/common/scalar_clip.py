"""Scalar float clipping with NumPy fallback for all other cases."""

import math

import numpy as np


def clip_scalar(value, lower, upper):
  if ((type(value) is float or type(value) is np.float64) and
      (type(lower) is float or type(lower) is np.float64) and
      (type(upper) is float or type(upper) is np.float64)):
    scalar, lo, hi = float(value), float(lower), float(upper)
    if (math.isfinite(scalar) and math.isfinite(lo) and math.isfinite(hi) and
        lo < hi and scalar != lo and scalar != hi):
      return lo if scalar < lo else hi if scalar > hi else scalar
  return float(np.clip(value, lower, upper))
