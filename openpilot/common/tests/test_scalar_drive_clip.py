"""Scalar clipping and drive limits preserve NumPy bits, types, and callbacks."""
from decimal import Decimal
from fractions import Fraction
from itertools import product
import math
import struct
import unittest
from unittest.mock import patch
import warnings

import numpy as np

from openpilot.common import scalar_clip
from openpilot.selfdrive.controls.lib import drive_helpers as drive
from openpilot.selfdrive.controls.lib.drive_helpers import (
  ACCELERATION_DUE_TO_GRAVITY, DT_CTRL, MAX_CURVATURE, MAX_LATERAL_ACCEL_NO_ROLL, MAX_LATERAL_JERK, MIN_SPEED,
)


def original_clip(value, lower, upper):
  return float(np.clip(value, lower, upper))


def clamp(val, min_val, max_val):
  clamped_val = float(np.clip(val, min_val, max_val))
  return clamped_val, clamped_val != val


def original_clip_curvature(v_ego, prev_curvature, new_curvature, roll):
  v_ego = max(v_ego, MIN_SPEED)
  max_curvature_rate = MAX_LATERAL_JERK / (v_ego ** 2)
  new_curvature = np.clip(new_curvature,
                          prev_curvature - max_curvature_rate * DT_CTRL,
                          prev_curvature + max_curvature_rate * DT_CTRL)
  roll_compensation = roll * ACCELERATION_DUE_TO_GRAVITY
  max_lat_accel = MAX_LATERAL_ACCEL_NO_ROLL + roll_compensation
  min_lat_accel = -MAX_LATERAL_ACCEL_NO_ROLL + roll_compensation
  new_curvature, limited_accel = clamp(new_curvature, min_lat_accel / v_ego ** 2, max_lat_accel / v_ego ** 2)
  new_curvature, limited_max_curv = clamp(new_curvature, -MAX_CURVATURE, MAX_CURVATURE)
  return float(new_curvature), limited_accel or limited_max_curv


def encoded(value):
  if isinstance(value, tuple):
    return type(value), tuple(encoded(item) for item in value)
  if isinstance(value, np.ndarray):
    return type(value), value.dtype.str, value.shape, value.tobytes()
  if isinstance(value, np.generic):
    return type(value), value.dtype.str, value.tobytes()
  if type(value) is float:
    return float, struct.pack('!d', value)
  return type(value), value


def outcome(function, *args):
  with warnings.catch_warnings(record=True) as seen:
    warnings.simplefilter('always')
    try:
      result = ('return', encoded(function(*args)))
    except Exception as exc:
      result = ('raise', type(exc), str(exc))
  return result, [(item.category, str(item.message)) for item in seen]


class TestScalarDriveClip(unittest.TestCase):
  def test_exact_float64_bounds_bit_parity_at_boundaries_and_special_values(self):
    triples = ((.5, 0., 1.), (-2., -1., 1.), (2., -1., 1.),
               (-0., 0., 1.), (0., -0., 1.), (-0., -1., 0.), (0., -1., -0.),
               (1., 1., 1.), (0., 1., -1.), (math.nan, -1., 1.),
               (.5, math.nan, 1.), (.5, -1., math.nan), (math.inf, -1., 1.),
               (-math.inf, -1., 1.), (.5, -math.inf, math.inf))
    for value_type, lower_type, upper_type in product((float, np.float64), repeat=3):
      for value, lower, upper in triples:
        args = value_type(value), lower_type(lower), upper_type(upper)
        self.assertEqual(outcome(scalar_clip.clip_scalar, *args), outcome(original_clip, *args))

  def test_unsupported_types_use_numpy_fallback_with_identical_warnings_and_errors(self):
    class FloatSubclass(float):
      pass
    class IntSubclass(int):
      pass
    cases = ((np.float32(.5), 0., 1.), (.5, np.float32(0), 1.),
             (np.longdouble('1.000000000000000001'), np.longdouble(0), np.longdouble(2)),
             (1, 0, 2), (1 << 4096, -1., 1.), (True, False, True),
             (FloatSubclass(.5), 0., 1.), (.5, FloatSubclass(0), 1.), (IntSubclass(1), 0, 2),
             (Fraction(1, 3), Fraction(0), Fraction(1)), (Decimal('.5'), Decimal(0), Decimal(1)),
             (np.array(.5), 0., 1.), (np.array([.5]), 0., 1.), (np.array([.5, 2.]), 0., 1.),
             (None, 0., 1.), (object(), 0., 1.), ('invalid', 0., 1.))
    numpy_clip = np.clip
    for args in cases:
      expected = outcome(original_clip, *args)
      with patch.object(scalar_clip.np, 'clip', wraps=numpy_clip) as fallback:
        self.assertEqual(outcome(scalar_clip.clip_scalar, *args), expected)
        fallback.assert_called_once()

  def test_clamp_preserves_comparison_type_shape_and_side_effect_order(self):
    for args in ((.5, 0., 1.), (np.float64(2), np.float64(0), np.float64(1)),
                 (np.float32(.5), 0., 1.), (-0., 0., 1.), (math.nan, -1., 1.),
                 (np.array(.5), 0., 1.), (np.array([.5]), 0., 1.), (np.array([.5, 2.]), 0., 1.)):
      self.assertEqual(outcome(drive.clamp, *args), outcome(clamp, *args))
    expected = clamp(np.float64(2), 0., 1.)
    actual = drive.clamp(np.float64(2), 0., 1.)
    self.assertIs(type(actual[1]), type(expected[1]))
    self.assertIs(type(actual[1]), np.bool_)
    class Callback:
      def __init__(self, events):
        self.events = events
      def __array_function__(self, function, types, args, kwargs):
        self.events.append(('clip', function.__name__))
        return np.float64(.25)
      def __ne__(self, other):
        self.events.append(('ne', encoded(other)))
        return np.array([False, True])
    for function, reference in ((scalar_clip.clip_scalar, original_clip), (drive.clamp, clamp)):
      actual_events, expected_events = [], []
      actual = outcome(function, Callback(actual_events), 0., 1.)
      expected = outcome(reference, Callback(expected_events), 0., 1.)
      self.assertEqual(actual, expected)
      self.assertEqual(actual_events, expected_events)

  def test_actual_curvature_grid_matches_frozen_body_and_retains_first_numpy_clip(self):
    for args in product((0., 1., 20., 100., np.float64(20)), (-.25, 0., .25), (-.2, .0002, .2), (-.1, 0., .1)):
      self.assertEqual(outcome(drive.clip_curvature, *args), outcome(original_clip_curvature, *args))
    for args in ((20., 0., math.nan, 0.), (math.inf, 0., .001, 0.), (20., .001, math.inf, math.nan)):
      self.assertEqual(outcome(drive.clip_curvature, *args), outcome(original_clip_curvature, *args))
    numpy_clip = np.clip
    args = (np.float64(20), .001, .002, np.float64(.01))
    expected = outcome(original_clip_curvature, *args)
    with patch.object(drive.np, 'clip', wraps=numpy_clip) as clip:
      self.assertEqual(outcome(drive.clip_curvature, *args), expected)
      self.assertGreaterEqual(clip.call_count, 1)
      self.assertIs(clip.call_args_list[0].args[0], args[2])


if __name__ == '__main__':
  unittest.main()
