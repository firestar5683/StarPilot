"""Measured local-segment coverage never becomes a fabricated route total."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.cereal import messaging
import zstandard as zstd

from openpilot.starpilot.galaxy.segment_summary import SegmentSummary, SegmentSummaryChanged, SegmentSummaryUnavailable


NAME = '00000042--abcdef1234--0'


def car(stamp: int, speed: float, *, valid: bool = True):
  event = messaging.new_message('carState', valid=valid)
  event.logMonoTime = stamp
  event.carState.vEgo = speed
  return event


def control(stamp: int, lat: bool, long: bool, *, valid: bool = True):
  event = messaging.new_message('carControl', valid=valid)
  event.logMonoTime = stamp
  event.carControl.latActive = lat
  event.carControl.longActive = long
  return event


def write(root: Path, events) -> Path:
  segment = root / NAME
  segment.mkdir(parents=True, exist_ok=True)
  source = segment / 'rlog.zst'
  source.write_bytes(zstd.compress(b''.join(event.to_bytes() for event in events)))
  return source


class SegmentSummaryTest(unittest.TestCase):
  def test_two_axes_and_speed_distance_from_serialized_events(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory).resolve()
      write(root, [car(1_000_000_000, 0), control(1_000_000_000, True, False),
                   car(2_000_000_000, 10), control(2_000_000_000, True, True),
                   car(3_000_000_000, 10), control(3_000_000_000, False, True)])
      result = SegmentSummary(root).snapshot(NAME, permitted=lambda: True)
      self.assertEqual(result['source'], 'closed_local_rlog')
      self.assertEqual(result['segmentName'], NAME)
      self.assertEqual(len(result['sourceSha256']), 64)
      self.assertEqual(result['observedCarSpanSeconds'], 2)
      self.assertEqual(result['estimatedDistanceMeters'], 15)
      self.assertEqual(result['observedLatActiveSeconds'], 2)
      self.assertEqual(result['observedLongActiveSeconds'], 1)
      self.assertTrue(result['sampleCoverageComplete'])

  def test_missing_axis_gap_and_invalid_speed_are_unknown_not_zero(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory).resolve()
      source = write(root, [car(1_000_000_000, 5)])
      result = SegmentSummary(root).snapshot(NAME, permitted=lambda: True)
      self.assertIsNone(result['observedCarSpanSeconds'])
      self.assertIsNone(result['estimatedDistanceMeters'])
      self.assertIsNone(result['observedLatActiveSeconds'])
      self.assertIsNone(result['observedLongActiveSeconds'])
      self.assertFalse(result['sampleCoverageComplete'])
      source.write_bytes(zstd.compress(b''.join(event.to_bytes() for event in
        [car(1_000_000_000, 5), car(4_000_000_000, 5), car(4_100_000_000, float('nan')),
         control(1_000_000_000, False, True), control(2_000_000_000, False, True)])))
      partial = SegmentSummary(root).snapshot(NAME, permitted=lambda: True)
      self.assertEqual(partial['observedCarSpanSeconds'], 3)
      self.assertIsNone(partial['estimatedDistanceMeters'])
      self.assertGreaterEqual(partial['gaps']['carState'], 2)
      self.assertEqual(partial['observedLatActiveSeconds'], 0)
      self.assertEqual(partial['observedLongActiveSeconds'], 1)
      self.assertFalse(partial['sampleCoverageComplete'])

  def test_short_control_window_does_not_claim_complete_segment_coverage(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory).resolve()
      write(root, [car(1_000_000_000, 5), car(2_000_000_000, 5),
                   control(1_500_000_000, True, False), control(1_750_000_000, True, False)])
      result = SegmentSummary(root).snapshot(NAME, permitted=lambda: True)
      self.assertEqual(result['observedLatActiveSeconds'], .25)
      self.assertFalse(result['sampleCoverageComplete'])

  def test_out_of_order_duplicates_and_invalid_reset_do_not_recount_intervals(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory).resolve()
      stamps = [1_000_000_000, 2_000_000_000, 1_500_000_000, 1_600_000_000,
                2_100_000_000, 2_200_000_000]
      events = []
      for stamp in stamps:
        events.extend([car(stamp, 10), control(stamp, True, True)])
      events.extend([car(2_200_000_000, 10), control(2_200_000_000, True, True),
                     car(2_300_000_000, float('nan')), control(2_300_000_000, True, True, valid=False)])
      events.extend([car(2_250_000_000, 10), control(2_250_000_000, True, True),
                     car(2_260_000_000, 10), control(2_260_000_000, True, True)])
      write(root, events)
      result = SegmentSummary(root).snapshot(NAME, permitted=lambda: True)
      self.assertEqual(result['estimatedDistanceMeters'], 11)
      self.assertEqual(result['observedLatActiveSeconds'], 1.1)
      self.assertEqual(result['observedLongActiveSeconds'], 1.1)
      self.assertGreaterEqual(result['gaps']['carState'], 6)
      self.assertGreaterEqual(result['gaps']['carControl'], 6)
      self.assertFalse(result['sampleCoverageComplete'])

  def test_active_symlink_and_post_decode_in_place_change(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory).resolve()
      source = write(root, [car(1_000_000_000, 5), car(2_000_000_000, 5)])
      lock = source.parent / 'rlog.lock'
      lock.touch()
      with self.assertRaises(SegmentSummaryChanged):
        SegmentSummary(root).snapshot(NAME, permitted=lambda: True)
      lock.unlink()
      from openpilot.starpilot.galaxy import segment_summary
      decode = segment_summary.decode_segment
      def mutate(data, codec, *, cancelled):
        events = decode(data, codec, cancelled=cancelled)
        with source.open('ab') as output:
          output.write(b'changed')
        return events
      with patch.object(segment_summary, 'decode_segment', mutate), self.assertRaises(SegmentSummaryChanged):
        SegmentSummary(root).snapshot(NAME, permitted=lambda: True)
      source.unlink()
      source.symlink_to('missing')
      with self.assertRaises(SegmentSummaryUnavailable):
        SegmentSummary(root).snapshot(NAME, permitted=lambda: True)

  def test_permission_loss_withholds_result(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory).resolve()
      write(root, [car(1_000_000_000, 5), car(2_000_000_000, 5)])
      calls = 0
      def permit():
        nonlocal calls
        calls += 1
        return calls < 4
      with self.assertRaises(SegmentSummaryUnavailable):
        SegmentSummary(root).snapshot(NAME, permitted=permit)
