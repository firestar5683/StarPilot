"""Signal lane evidence from serialized current model frames."""

from dataclasses import replace
import math
import unittest

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.signal_lane import MonoSource, SignalLaneFrame, SignalLaneTracker, model_widths


MONO = 100_000_000_000
BOOT = MONO + 2_000_000_000


def wire_model(*, left_outer=-5.4, left_inner=-1.8, right_inner=1.8, right_outer=5.4,
               left_edge=-8.0, right_edge=8.0, malformed=False):
  event = messaging.new_message('modelV2', valid=True)
  event.modelV2.timestampEof = BOOT + 10_000_000
  lines = event.modelV2.init('laneLines', 4)
  edges = event.modelV2.init('roadEdges', 2)
  xs = [float(index * 5) for index in range(33)]
  for line, y in zip(lines, (left_outer, left_inner, right_inner, right_outer), strict=True):
    line.x = xs
    line.y = [y] * (32 if malformed and y == left_outer else 33)
  for edge, y in zip(edges, (left_edge, right_edge), strict=True):
    edge.x = xs
    edge.y = [y] * 33
  return messaging.log_from_bytes(event.to_bytes()).modelV2


def frame(index=1, *, model=None, speed=15.0, left=True, right=False):
  stamp = MONO + index * 50_000_000
  return SignalLaneFrame(
    model=wire_model() if model is None else model, model_valid=True, car_valid=True,
    ego_speed_mps=speed, minimum_lane_change_speed_mps=5.0,
    signal_speed_mps=20.0, lane_detection_width_m=3.0, signal_lane_detection=True,
    left_blinker=left, right_blinker=right, model_source=MonoSource(stamp, stamp),
    car_source=MonoSource(stamp, stamp), model_eof_boot_ns=BOOT + index * 50_000_000,
    now_mono_ns=stamp + 1_000_000, now_boot_ns=BOOT + index * 50_000_000 + 1_000_000,
    expected_boot_minus_mono_ns=BOOT - MONO, barrier_mono_ns=MONO,
    barrier_boot_ns=BOOT, sample_skew_ns=1000,
  )


class TestSignalLane(unittest.TestCase):
  def test_frozen_width_math_and_edge_override(self):
    widths = model_widths(wire_model())
    assert widths is not None
    for width in widths:
      self.assertAlmostEqual(width, 3.6, places=5)
    widths = model_widths(wire_model(left_edge=-2.0))
    assert widths is not None
    left, right = widths
    self.assertEqual(left, 0.0)
    self.assertAlmostEqual(right, 3.6, places=5)
    self.assertIsNone(model_widths(wire_model(malformed=True)))
    self.assertIsNone(model_widths(wire_model(left_outer=math.nan)))

  def test_four_distinct_fresh_ticks_and_side_selection(self):
    owner = SignalLaneTracker()
    for index in range(1, 4):
      self.assertIsNone(owner.update(frame(index)).lane_available)
    left = owner.update(frame(4))
    assert left.left_width_m is not None
    self.assertAlmostEqual(left.left_width_m, 3.6, places=5)
    self.assertTrue(left.lane_available)
    self.assertFalse(left.signal_scene)
    right = owner.update(frame(5, model=wire_model(right_edge=2.0), left=False, right=True))
    assert right.right_width_m is not None
    self.assertAlmostEqual(right.right_width_m, 3.6, places=5)  # Frozen four-tick cache.
    self.assertTrue(right.lane_available)
    for index in (6, 7):
      owner.update(frame(index, model=wire_model(right_edge=2.0), left=False, right=True))
    absent = owner.update(frame(8, model=wire_model(right_edge=2.0), left=False, right=True))
    self.assertEqual(absent.right_width_m, 0.0)
    self.assertFalse(absent.lane_available)
    self.assertTrue(absent.signal_scene)

  def test_unsupported_geometry_is_unknown_not_no_lane(self):
    owner = SignalLaneTracker()
    for index in range(1, 5):
      owner.update(frame(index))
    bad = owner.update(frame(5, model=wire_model(malformed=True)))
    self.assertIsNone(bad.lane_available)
    self.assertIsNone(bad.signal_scene)
    self.assertIsNone(bad.left_width_m)

  def test_source_age_replay_and_resume_clear_cache(self):
    owner = SignalLaneTracker()
    for index in range(1, 5):
      owner.update(frame(index))
    prior = frame(4)
    self.assertTrue(owner.update(prior).lane_available)  # Re-poll never advances cadence.
    self.assertIsNone(owner.update(frame(3)).lane_available)  # Reordered source clears it.
    self.assertIsNone(owner.update(replace(frame(5), model_eof_boot_ns=BOOT - 1)).lane_available)
    for index in range(6, 10):
      owner.update(frame(index))
    resumed = replace(frame(10), now_boot_ns=frame(10).now_boot_ns + 9_000_000_000)
    self.assertIsNone(owner.update(resumed).lane_available)
    self.assertIsNone(owner.update(replace(frame(11), model_source=MonoSource(MONO - 1, MONO + 550_000_000))).lane_available)

  def test_below_minimum_and_no_detection_toggle(self):
    owner = SignalLaneTracker()
    low = owner.update(frame(speed=4.9))
    self.assertEqual(low.selected_width_m, 0.0)
    self.assertTrue(low.signal_scene)
    self.assertFalse(owner.update(frame(2, speed=4.9, left=False, right=False)).signal_scene)
    disabled = owner.update(replace(frame(3, speed=4.9), signal_lane_detection=False))
    self.assertTrue(disabled.lane_available)
    self.assertFalse(disabled.signal_scene)

  def test_high_speed_known_false_without_width_and_invalid_inputs_unknown(self):
    owner = SignalLaneTracker()
    high = owner.update(frame(speed=20.0))
    self.assertIsNone(high.lane_available)
    self.assertFalse(high.signal_scene)  # Frozen strict speed threshold.
    self.assertIsNone(owner.update(replace(frame(2), model_valid=False)).signal_scene)
    self.assertIsNone(owner.update(replace(frame(3), lane_detection_width_m=math.nan)).lane_available)
    self.assertIsNone(owner.update(replace(frame(4), left_blinker=1)).lane_available)
    self.assertIsNone(owner.update(replace(frame(5), car_source=MonoSource(MONO - 1, MONO + 250_000_000))).lane_available)


if __name__ == '__main__':
  unittest.main()
