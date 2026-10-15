"""Scalar float clipping with NumPy fallback for all other cases."""

import math

import numpy as np


def clip_scalar(value, lower, upper):
  if ((type(value) is float or type(value) is np.float64) and
      type(lower) is float and type(upper) is float):
    scalar = float(value)
    if (math.isfinite(scalar) and math.isfinite(lower) and math.isfinite(upper) and
        lower < upper and scalar != lower and scalar != upper):
      return lower if scalar < lower else upper if scalar > upper else scalar
  return float(np.clip(value, lower, upper))
