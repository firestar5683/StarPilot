import math
import random
import struct
import unittest
import warnings

import numpy as np

from openpilot.common.scalar_clip import clip_scalar


class TestScalarClip(unittest.TestCase):
  def compare(self, value, lower, upper):
    results = []
    for function in (lambda v, lo, hi: float(np.clip(v, lo, hi)), clip_scalar):
      with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter('always')
        try:
          result = ('value', struct.pack('>d', function(value, lower, upper)))
        except Exception as error:
          result = ('error', type(error), str(error))
      results.append((result, [(warning.category, str(warning.message)) for warning in seen]))
    self.assertEqual(results[0], results[1], (value, lower, upper))

  def test_binary64_inputs_match_numpy_exactly(self):
    randomizer = random.Random(20261015)
    def finite():
      while True:
        value = struct.unpack('>d', randomizer.getrandbits(64).to_bytes(8, 'big'))[0]
        if math.isfinite(value):
          return value
    for _ in range(3000):
      lower, upper = sorted((finite(), finite()))
      value = finite()
      self.compare(value, lower, upper)
      self.compare(np.float64(value), lower, upper)

  def test_boundary_bits_and_nonfinite_inputs(self):
    values = (-0.0, 0.0, -math.ulp(0.0), math.ulp(0.0), -1.0, 1.0,
              math.nextafter(1.0, -math.inf), math.nextafter(1.0, math.inf),
              -math.inf, math.inf, math.nan)
    bounds = ((-1.0, 1.0), (-0.0, 1.0), (0.0, 1.0), (-1.0, -0.0), (-1.0, 0.0),
              (-0.0, 0.0), (0.0, -0.0), (1.0, 1.0), (1.0, -1.0),
              (-math.inf, math.inf), (math.nan, 1.0), (-1.0, math.nan))
    for lower, upper in bounds:
      for value in values:
        self.compare(value, lower, upper)
        self.compare(np.float64(value), lower, upper)

  def test_other_types_keep_numpy_results_errors_and_warnings(self):
    class FloatSubclass(float):
      pass
    values = (0, True, None, '0', np.float32(0.2), np.int64(2), FloatSubclass(0.2),
              np.array(0.2), np.array([0.2]), np.array([0.2, 0.5]))
    for value in values:
      for lower, upper in ((-1.0, 1.0), (-1, 1), (np.float32(-1), np.float32(1))):
        self.compare(value, lower, upper)
