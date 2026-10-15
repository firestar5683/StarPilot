"""Exact-float lane validation preserves numeric and conversion semantics."""
from fractions import Fraction
import math
from numbers import Real
import unittest
import warnings

import numpy as np

from openpilot.starpilot.lateral import lane_centering as lane


def original_finite(value):
  if isinstance(value, bool) or not isinstance(value, Real):
    return None
  try:
    result = float(value)
  except (TypeError, ValueError, OverflowError):
    return None
  return result if math.isfinite(result) else None


def finite_outcome(function, value):
  with warnings.catch_warnings(record=True) as seen:
    warnings.simplefilter('always')
    try:
      result = function(value)
      outcome = (type(result), result, math.copysign(1., result) if result == 0 else None)
    except Exception as exc:
      outcome = (type(exc), str(exc))
  return outcome, [(item.category, str(item.message)) for item in seen]


class TestLaneFinite(unittest.TestCase):
  def test_finite_exact_float_and_other_numeric_semantics(self):
    class WarnFloat(float):
      def __float__(self):
        warnings.warn('custom conversion', RuntimeWarning, stacklevel=2)
        return 1.0
    class ErrorFloat(float):
      def __float__(self):
        raise RuntimeError('custom conversion failed')
    values = (0., -0., 1., 5e-324, 1e308, math.nan, math.inf, -math.inf,
              0, 1 << 4096, True, False, Fraction(1, 3), np.float32(.1), np.float64(.1), np.int64(3),
              WarnFloat(2), ErrorFloat(2), '1.0', None, complex(1, 0), object())
    for value in values:
      self.assertEqual(finite_outcome(lane._finite_number, value), finite_outcome(original_finite, value))


if __name__ == '__main__':
  unittest.main()
