"""Current serialized model lanes and qualified raw radar-track evidence."""

from dataclasses import replace
import math
import unittest

from openpilot.cereal import messaging
from openpilot.selfdrive.controls.radard import DT_MDL, KalmanParams, Track
from openpilot.starpilot.conditional_mode.adjacent import AdjacentFrame, AdjacentTrack, MonoSource, evaluate


MONO = 100_000_000_000
BOOT = MONO + 2_000_000_000


def wire_model(*, left=-1.8, right=1.8, origin=0.0, step=5.0, bad_length=False, nonmonotonic=False):
  event = messaging.new_message('modelV2', valid=True)
  event.modelV2.timestampEof = BOOT + 10_000_000
  lines = event.modelV2.init('laneLines', 4)
  xs = [origin + float(index) * step for index in range(33)]
  if nonmonotonic:
    xs[5] = xs[4]
  for index, line in enumerate(lines):
    line.x = xs[:-1] if bad_length and index == 1 else xs
    line.y = [left if index == 1 else right if index == 2 else 0.0] * len(line.x)
  return messaging.log_from_bytes(event.to_bytes()).modelV2


def frame(*, tracks=(), model=None, primary=frozenset(), standstill=False, speed=15.0):
  stamp = MONO + 10_000_000
  return AdjacentFrame(
    model=wire_model() if model is None else model,
    tracks=tuple(tracks),
    primary_track_ids=frozenset(primary),
    radar_available=True,
    radar_valid=True,
    radar_error_free=True,
    model_valid=True,
    car_valid=True,
    standstill=standstill,
    ego_speed_mps=speed,
    radar=MonoSource(stamp, stamp),
    model_source=MonoSource(stamp, stamp),
    car=MonoSource(stamp, stamp),
    model_eof_boot_ns=BOOT + 10_000_000,
    now_mono_ns=MONO + 12_000_000,
    now_boot_ns=BOOT + 12_000_000,
    expected_boot_minus_mono_ns=BOOT - MONO,
    barrier_mono_ns=MONO,
    barrier_boot_ns=BOOT,
    sample_skew_ns=1000,
  )


class TestAdjacentEvidence(unittest.TestCase):
  def test_current_radard_track_fields_adapt_without_lead_two(self):
    raw = Track(17, 8.0, KalmanParams(DT_MDL))
    raw.update(25.0, 3.0, -2.0, 8.0)
    candidate = AdjacentTrack(raw.identifier, raw.dRel, raw.yRel, raw.vLead)
    result = evaluate(frame(tracks=(candidate,)))
    self.assertTrue(result.ambiguous)
    self.assertEqual(result.left.track_id, 17)

  def test_left_right_closest_and_selected_primary_exclusion(self):
    tracks = (
      AdjacentTrack(1, 30.0, 3.0, 12.0),
      AdjacentTrack(2, 20.0, -3.0, 14.0),
      AdjacentTrack(3, 10.0, 2.4, 10.0),
      AdjacentTrack(4, 15.0, -2.4, 11.0),
    )
    result = evaluate(frame(tracks=tracks))
    self.assertTrue(result.ambiguous)
    self.assertEqual(result.left.track_id, 3)
    self.assertEqual(result.right.track_id, 4)
    excluded = evaluate(frame(tracks=tracks, primary={3, 4}))
    self.assertTrue(excluded.ambiguous)
    self.assertEqual(excluded.left.track_id, 1)
    self.assertEqual(excluded.right.track_id, 2)
    self.assertEqual(result.observed_mono_ns, MONO + 10_000_000)

  def test_closest_diagnostic_does_not_mask_another_qualified_track(self):
    # Frozen closest-first CCM misses the farther actual ambiguity. Preserve
    # closest diagnostics, but veto for any independently qualified track.
    tracks = (AdjacentTrack(1, 10.0, 6.0, 8.0), AdjacentTrack(2, 20.0, 3.0, 8.0))
    result = evaluate(frame(tracks=tracks))
    self.assertTrue(result.ambiguous)
    self.assertEqual(result.left.track_id, 1)
    slow_near = evaluate(frame(tracks=(AdjacentTrack(1, 10.0, 3.0, 1.0), AdjacentTrack(2, 20.0, 3.0, 8.0))))
    self.assertTrue(slow_near.ambiguous)
    self.assertEqual(slow_near.left.track_id, 1)
    self.assertFalse(evaluate(frame()).ambiguous)
    self.assertFalse(evaluate(frame(tracks=tracks, standstill=True)).ambiguous)
    self.assertIsNone(evaluate(replace(frame(), radar_available=False)).ambiguous)
    self.assertIsNone(evaluate(replace(frame(), radar_valid=False)).ambiguous)
    self.assertIsNone(evaluate(replace(frame(), radar_error_free=False)).ambiguous)
    self.assertIsNone(evaluate(replace(frame(), model_valid=False)).ambiguous)
    self.assertIsNone(evaluate(replace(frame(), car_valid=False)).ambiguous)

  def test_strict_distance_speed_and_lateral_boundaries(self):
    # At 15 m/s, frozen maximum is 52.5 m, and both distance/speed tests
    # are strict. A track that is only 1.0 m/s is not a CCM ambiguity.
    self.assertFalse(evaluate(frame(tracks=(AdjacentTrack(1, 52.5, 3.0, 5.0),))).ambiguous)
    self.assertFalse(evaluate(frame(tracks=(AdjacentTrack(1, 30.0, 3.0, 1.0),))).ambiguous)
    self.assertTrue(evaluate(frame(tracks=(AdjacentTrack(1, 30.0, 5.5, 1.01),))).ambiguous)
    self.assertFalse(evaluate(frame(tracks=(AdjacentTrack(1, 30.0, 5.51, 5.0),))).ambiguous)

  def test_invalid_geometry_and_raw_track_are_unavailable_not_no_lead(self):
    valid_track = (AdjacentTrack(1, 30.0, 3.0, 12.0),)
    for model in (wire_model(bad_length=True), wire_model(nonmonotonic=True), wire_model(left=2.0, right=-2.0)):
      self.assertIsNone(evaluate(frame(model=model, tracks=valid_track)).ambiguous)
    for track in (AdjacentTrack(1, 30.0, math.nan, 12.0), AdjacentTrack(1, 53.0, 3.0, 12.0)):
      if track.distance_m > 52.5:
        # Outside the veto distance, this is valid but irrelevant.
        self.assertFalse(evaluate(frame(tracks=(track,))).ambiguous)
        continue
      self.assertIsNone(evaluate(frame(tracks=(track,))).ambiguous)
    self.assertFalse(evaluate(frame(tracks=(AdjacentTrack(1, 200.0, 3.0, 12.0),))).ambiguous)
    self.assertIsNone(evaluate(frame(tracks=(AdjacentTrack(1, 40.0, 3.0, 12.0),), model=wire_model(step=1.0))).ambiguous)

  def test_small_positive_model_origin_uses_frozen_interpolation_clamp(self):
    self.assertTrue(evaluate(frame(model=wire_model(origin=0.1), tracks=(AdjacentTrack(1, 0.05, 3.0, 8.0),))).ambiguous)

  def test_stale_or_mixed_clock_sources_and_resume_barrier_are_unavailable(self):
    source = frame(tracks=(AdjacentTrack(1, 30.0, 3.0, 12.0),))
    self.assertIsNone(evaluate(replace(source, radar=MonoSource(MONO - 1, MONO + 10_000_000))).ambiguous)
    self.assertIsNone(evaluate(replace(source, model_source=MonoSource(MONO - 1, MONO + 10_000_000))).ambiguous)
    self.assertIsNone(evaluate(replace(source, model_eof_boot_ns=BOOT - 1)).ambiguous)
    self.assertIsNone(evaluate(replace(source, car=MonoSource(MONO - 1, MONO + 10_000_000))).ambiguous)
    self.assertIsNone(evaluate(replace(source, now_boot_ns=source.now_boot_ns + 90_000_000)).ambiguous)
    self.assertIsNone(evaluate(replace(source, barrier_mono_ns=MONO + 10_000_000)).ambiguous)

  def test_producer_age_not_refreshed_by_poll_time(self):
    source = frame(tracks=(AdjacentTrack(1, 30.0, 3.0, 12.0),))
    later = replace(source, now_mono_ns=source.now_mono_ns + 100_000_000, now_boot_ns=source.now_boot_ns + 100_000_000)
    self.assertTrue(evaluate(later).ambiguous)
    self.assertEqual(evaluate(later).observed_mono_ns, source.radar.producer_ns)
    expired = replace(source, now_mono_ns=source.now_mono_ns + 300_000_000, now_boot_ns=source.now_boot_ns + 300_000_000)
    self.assertIsNone(evaluate(expired).ambiguous)
