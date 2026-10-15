"""Native validation skips width math while retaining cadence and revocation."""

from dataclasses import replace
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode import signal_lane as lane
from openpilot.starpilot.conditional_mode.tests.test_signal_lane import BOOT, MONO, frame, wire_model


def native_event(index=1, *, line=None, defect=None, **geometry):
  """Reusable serialized ModelDataV2 event; line0..3 lanes,4..5 road edges."""
  event = messaging.new_message('modelV2', valid=True, logMonoTime=MONO + index * 50_000_000)
  event.modelV2 = wire_model(**geometry)
  event.modelV2.timestampEof = BOOT + index * 50_000_000
  if line is not None:
    selected = event.modelV2.laneLines[line] if line < 4 else event.modelV2.roadEdges[line - 4]
    if defect == 'length':
      selected.y = list(selected.y)[:-1]
    elif defect == 'nan':
      selected.y[10] = math.nan
    elif defect == 'nonincreasing':
      selected.x[10] = selected.x[9]
    elif defect == 'origin_roundoff':
      selected.x[0] = -1e-8
    else:
      raise ValueError('unknown geometry defect')
  return messaging.log_from_bytes(event.to_bytes())


def native_model(index=1, **changes):
  return native_event(index, **changes).modelV2


def native_frame(index=1, *, model=None, **changes):
  return replace(frame(index, model=native_model(index) if model is None else model), **changes)


def warmed_tracker():
  tracker = lane.SignalLaneTracker()
  for index in range(1, 5):
    tracker.update(native_frame(index))
  return tracker


class TestSignalLaneValidation(unittest.TestCase):
  def test_actual_native_valid_edge_override_origin_and_shape(self):
    for geometry in ({}, {'left_edge': -2.0}, {'right_edge': 2.0}):
      model = native_model(**geometry)
      expected = lane.model_widths(model)
      self.assertIsNotNone(expected)
      with patch.object(lane, '_line', wraps=lane._line) as lines, \
           patch.object(lane.np, 'interp', side_effect=AssertionError('validation interpolated')), \
           patch.object(lane.np, 'median', side_effect=AssertionError('validation computed median')):
        self.assertTrue(lane._model_widths_valid(model))
        self.assertEqual(lines.call_count, 6)
    for index in range(6):
      model = native_model(line=index, defect='origin_roundoff')
      self.assertEqual(lane._model_widths_valid(model), lane.model_widths(model) is not None)
    for field, length in (('laneLines', 3), ('roadEdges', 1)):
      event = messaging.new_message('modelV2', valid=True)
      event.modelV2 = native_model()
      event.modelV2.init(field, length)
      model = messaging.log_from_bytes(event.to_bytes()).modelV2
      self.assertFalse(lane._model_widths_valid(model))
      self.assertIsNone(lane.model_widths(model))
    backing = native_event(4).as_builder()
    alias = backing.modelV2.as_reader()
    tracker = warmed_tracker()
    self.assertTrue(lane._model_widths_valid(alias))
    self.assertTrue(tracker.update(native_frame(4, model=alias)).lane_available)
    backing.modelV2.roadEdges[1].y[10] = math.nan
    self.assertFalse(lane._model_widths_valid(alias))
    self.assertIsNone(lane.model_widths(alias))
    self.assertIsNone(tracker.update(native_frame(4, model=alias)).lane_available)
    boundary = native_event().as_builder()
    xs = [0.0, math.ldexp(1.0, -149), *map(float, range(1, 31)), 500.0]
    for index, line in enumerate((*boundary.modelV2.laneLines, *boundary.modelV2.roadEdges)):
      line.x = xs
      line.y = [-30.0 if index % 2 == 0 else 30.0] * 33
    model = messaging.log_from_bytes(boundary.to_bytes()).modelV2
    self.assertEqual(lane._model_widths_valid(model), lane.model_widths(model) is not None)

  def test_each_native_lane_and_edge_rejects_length_nan_and_nonincreasing_x(self):
    for index in range(6):
      for defect in ('length', 'nan', 'nonincreasing'):
        with self.subTest(line=index, defect=defect):
          model = native_model(line=index, defect=defect)
          self.assertIsNone(lane.model_widths(model))
          self.assertFalse(lane._model_widths_valid(model))

  def test_custom_builder_and_wrong_schema_use_full_fallback(self):
    reader = native_model()
    wrong_schema = messaging.new_message('carState').as_reader().carState
    custom = SimpleNamespace(schema=reader.schema, laneLines=reader.laneLines, roadEdges=reader.roadEdges)
    for model in (None, custom, reader.as_builder(), wrong_schema):
      for result in (None, (3.6, 3.6)):
        with self.subTest(model=type(model), result=result), patch.object(lane, 'model_widths', return_value=result) as full:
          self.assertEqual(lane._model_widths_valid(model), result is not None)
          full.assert_called_once_with(model)
    with patch.object(lane, 'model_widths', side_effect=RuntimeError('custom fallback')):
      with self.assertRaisesRegex(RuntimeError, 'custom fallback'):
        lane._model_widths_valid(custom)

  def test_three_intervening_and_repeated_native_frames_skip_math_fourth_retained(self):
    tracker = lane.SignalLaneTracker()
    with patch.object(lane, 'model_widths', wraps=lane.model_widths) as full, \
         patch.object(lane.np, 'interp', wraps=lane.np.interp) as interp, \
         patch.object(lane.np, 'median', wraps=lane.np.median) as median:
      for index in range(1, 4):
        self.assertIsNone(tracker.update(native_frame(index)).lane_available)
      self.assertEqual((full.call_count, interp.call_count, median.call_count), (0, 0, 0))
      measured = tracker.update(native_frame(4))
      self.assertTrue(measured.lane_available)
      assert measured.left_width_m is not None
      self.assertAlmostEqual(measured.left_width_m, 3.6, places=5)
      self.assertEqual((full.call_count, interp.call_count, median.call_count), (1, 4, 4))
      repeated = tracker.update(native_frame(4))
      self.assertEqual(repeated, measured)
      self.assertEqual(tracker._count, 4)
      for index in range(5, 8):
        model = native_model(index, left_outer=-3.8)
        self.assertTrue(tracker.update(native_frame(index, model=model)).lane_available)
      self.assertEqual((full.call_count, interp.call_count, median.call_count), (1, 4, 4))
      changed = tracker.update(native_frame(8, model=native_model(8, left_outer=-3.8)))
      self.assertFalse(changed.lane_available)
      assert changed.left_width_m is not None
      self.assertAlmostEqual(changed.left_width_m, 2.0, places=5)
      self.assertEqual((full.call_count, interp.call_count, median.call_count), (2, 8, 8))

  def test_bad_intervening_repeated_and_stale_sources_revoke_cached_widths(self):
    for index in (4, 5):
      tracker = warmed_tracker()
      malformed = native_frame(index, model=native_model(index, line=5, defect='nan'))
      with patch.object(lane.np, 'interp', side_effect=AssertionError('malformed validation interpolated')):
        invalid = tracker.update(malformed)
      self.assertIsNone(invalid.left_width_m)
      self.assertIsNone(invalid.right_width_m)
      self.assertIsNone(invalid.lane_available)
      self.assertIsNone(invalid.signal_scene)
      for next_index in range(index + 1, 8):
        self.assertIsNone(tracker.update(native_frame(next_index)).lane_available)
      self.assertTrue(tracker.update(native_frame(8)).lane_available)
    current = native_frame(5)
    stale = replace(current, now_mono_ns=current.now_mono_ns + lane.MODEL_MAX_AGE_NS + 1,
                    now_boot_ns=current.now_boot_ns + lane.MODEL_MAX_AGE_NS + 1)
    bad_car = replace(current, car_source=lane.MonoSource(MONO - 1, current.now_mono_ns))
    for invalid in (stale, bad_car, replace(current, model_eof_boot_ns=BOOT - 1), native_frame(3)):
      tracker = warmed_tracker()
      self.assertEqual(tracker.update(invalid), lane.UNKNOWN)
      self.assertIsNone(tracker._widths)
      self.assertEqual(tracker._count, 0)


if __name__ == '__main__':
  unittest.main()
