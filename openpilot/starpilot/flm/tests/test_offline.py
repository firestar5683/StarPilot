"""Serialized current Cereal traces and frozen override-mask differential."""

import math
from contextlib import ExitStack
import unittest

from openpilot.cereal import log
from openpilot.starpilot.flm.offline import SegmentInput, TrackingSample, _eligible, analyze_segments
from opendbc.car.hyundai.values import CAR


def event(kind, ns, *, valid=True, **fields):
  builder = log.Event.new_message(logMonoTime=ns, valid=valid)
  payload = builder.init(kind)
  if kind == 'carParams':
    payload.carFingerprint = fields.get('fingerprint', CAR.HYUNDAI_IONIQ_6)
    payload.lateralTuning.init(fields.get('tuning', 'torque'))
    payload.steerControlType = fields.get('steering_type', 'torque')
    payload.dashcamOnly = fields.get('dashcam', False)
  elif kind == 'carState':
    payload.vEgo = fields.get('speed', 12.0)
    payload.steeringPressed = fields.get('pressed', False)
    payload.canValid = fields.get('can_valid', True)
  elif kind == 'carControl':
    payload.latActive = fields.get('lat_active', True)
  elif kind == 'controlsState':
    state = payload.lateralControlState
    state.init(fields.get('controller', 'torqueState'))
    if fields.get('controller', 'torqueState') == 'torqueState':
      state.torqueState.desiredLateralAccel = fields.get('desired', 0.4)
      state.torqueState.actualLateralAccel = fields.get('actual', 0.3)
      state.torqueState.active = fields.get('active', True)
  return builder


def serialized(builders):
  with ExitStack() as stack:
    for builder in builders:
      yield stack.enter_context(log.Event.from_bytes(builder.to_bytes()))


def segment(*, number=0, count=25, pressed=(), fingerprint=CAR.HYUNDAI_IONIQ_6, gap_at=None,
            invalid_first=False, other_last=False, bad_numeric_at=None, invalid_control_at=None):
  base = 1_000_000_000
  events = [event('carParams', base, fingerprint=fingerprint)]
  for i in range(count):
    ns = base + (i + 1) * 100_000_000 + (1_000_000_000 if gap_at is not None and i >= gap_at else 0)
    events += [event('carState', ns, pressed=i in pressed, valid=not (invalid_first and i == 0)),
               event('carControl', ns, valid=i != invalid_control_at),
               event('controlsState', ns, controller='pidState' if other_last and i == count - 1 else 'torqueState',
                     desired=float('nan') if i == bad_numeric_at else 0.4)]
  return SegmentInput('synthetic', number, serialized(events))


def frozen_mask(samples):
  """Independent translation of frozen flm_workspace._analysis_eligibility_mask."""
  eligible = [True for _ in samples]
  last_override = -math.inf
  for index, sample in enumerate(samples):
    t = sample.mono_ns / 1e9
    if sample.steering_pressed:
      last_override = t
    if sample.steering_pressed or t - last_override <= 1.0:
      eligible[index] = False
  next_override = math.inf
  for index in range(len(samples) - 1, -1, -1):
    sample = samples[index]
    t = sample.mono_ns / 1e9
    if sample.steering_pressed:
      next_override = t
    if sample.steering_pressed or next_override - t <= 0.35:
      eligible[index] = False
  eligible[0] = eligible[-1] = False
  return eligible


class OfflineTest(unittest.TestCase):
  def test_serialized_current_ioniq_torque_tracking(self):
    result = analyze_segments((segment(),)).segments[0]
    self.assertEqual(result.status, 'measured')
    self.assertEqual(result.eligible_samples, 23)
    assert result.mean_abs_error is not None
    assert result.root_mean_square_error is not None
    self.assertAlmostEqual(result.mean_abs_error, 0.1, places=6)
    self.assertAlmostEqual(result.root_mean_square_error, 0.1, places=6)
    self.assertEqual((result.series[0].desired_lat_accel, result.series[0].actual_lat_accel), (0.4000000059604645, 0.30000001192092896))
    self.assertEqual(len(result.windows), 1)
    self.assertEqual(result.windows[0].sample_count, 23)
    self.assertEqual(result.windows[0].direction, 'left')

  def test_late_consistent_car_params_has_same_complete_segment_report(self):
    base = 1_000_000_000
    samples = []
    for i in range(25):
      ns = base + (i + 1) * 100_000_000
      samples.extend((event('carState', ns), event('carControl', ns), event('controlsState', ns)))
    def analyze(events):
      return analyze_segments((SegmentInput('same', 0, serialized(events)),)).segments[0]
    early = analyze([event('carParams', base), *samples])
    late = analyze([*samples, event('carParams', base + 4_000_000_000)])
    repeated = analyze([*samples, event('carParams', base + 4_000_000_000), event('carParams', base)])
    self.assertEqual(early, late)
    self.assertEqual(late.eligible_samples, 23)
    self.assertEqual(repeated.eligible_samples, early.eligible_samples)
    self.assertNotIn('missing_or_unsupported_car_params', dict(late.exclusions))

  def test_late_invalid_or_changed_car_params_rejects_entire_segment(self):
    base = 1_000_000_000
    samples = []
    for i in range(25):
      ns = base + (i + 1) * 100_000_000
      samples.extend((event('carState', ns), event('carControl', ns), event('controlsState', ns)))
    changed = event('carParams', base + 4_000_000_000)
    changed.carParams.lateralTuning.torque.friction = .2
    for cp, reason in ((changed, 'inconsistent_car_params'),
                       (event('carParams', base + 4_000_000_000, valid=False), 'invalid_car_params'),
                       (event('carParams', 0), 'invalid_car_params')):
      with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
        analyze_segments((SegmentInput('same', 0, serialized([event('carParams', base), *samples, cp])),))

  def test_frozen_override_mask_and_gap_boundary(self):
    samples = [TrackingSample(1_000_000_000 + i * 100_000_000, 12.0, .4, .3, False, i in (5, 17)) for i in range(25)]
    self.assertEqual(_eligible(samples), frozen_mask(samples))
    result = analyze_segments((segment(pressed=(5, 17), gap_at=12),)).segments[0]
    self.assertGreater(dict(result.exclusions)['driver_override_or_boundary'], 0)
    self.assertLess(result.eligible_samples, 23)

  def test_wrong_car_and_non_torque_are_not_measured(self):
    wrong = analyze_segments((segment(fingerprint='NOT_IONIQ'),)).segments[0]
    self.assertEqual(wrong.status, 'unsupported_car')
    self.assertEqual(wrong.eligible_samples, 0)
    result = analyze_segments((segment(count=3, other_last=True),)).segments[0]
    self.assertEqual(dict(result.exclusions)['other_controller'], 1)

  def test_missing_invalid_stale_sources_and_segment_independence(self):
    report = analyze_segments((segment(count=5, invalid_first=True, invalid_control_at=1, bad_numeric_at=2),
                               segment(number=1, count=5))).segments
    self.assertEqual(dict(report[0].exclusions)['missing_or_stale_source'], 2)
    self.assertEqual(dict(report[0].exclusions)['invalid_numeric'], 1)
    self.assertEqual(report[1].status, 'measured')

  def test_series_and_message_bounds(self):
    report = analyze_segments((segment(count=300),)).segments[0]
    self.assertEqual(len(report.series), 160)
    self.assertLess(report.series[0].mono_ns, report.series[-1].mono_ns)

  def test_bounds_cancel_and_inconsistent_cp(self):
    with self.assertRaisesRegex(ValueError, 'segment_count'):
      analyze_segments(())
    with self.assertRaisesRegex(RuntimeError, 'cancelled'):
      analyze_segments((segment(),), cancelled=lambda: True)
    events = [event('carParams', 1_000_000_000), event('carParams', 1_000_000_001, fingerprint='OTHER')]
    with self.assertRaisesRegex(ValueError, 'inconsistent_car_params'):
      analyze_segments((SegmentInput('a', 0, serialized(events)),))

    repeated = event('carParams', 1_000_000_002)
    repeated.carParams.lateralTuning.torque.friction = .2
    with self.assertRaisesRegex(ValueError, 'inconsistent_car_params'):
      analyze_segments((SegmentInput('a', 0, serialized([event('carParams', 1_000_000_000), repeated])),))

  def test_inactive_press_masks_neighbors_and_breaks_window(self):
    base = 1_000_000_000
    events = [event('carParams', base)]
    for i in range(30):
      ns = base + (i + 1) * 100_000_000
      events.extend((event('carState', ns, pressed=i == 8), event('carControl', ns, lat_active=i != 8),
                     event('controlsState', ns)))
    report = analyze_segments((SegmentInput('a', 0, serialized(events)),)).segments[0]
    press_ns = base + 900_000_000
    self.assertTrue(all(not -350_000_000 <= point.mono_ns - press_ns <= 1_000_000_000 for point in report.series))
    self.assertEqual(len(report.windows), 1)
    self.assertGreater(report.windows[0].start_mono_ns, press_ns + 1_000_000_000)

  def test_short_invalid_gap_does_not_bridge_and_unrelated_interleaving_is_ignored(self):
    base = 1_000_000_000
    events = [event('carParams', base)]
    for i in range(25):
      ns = base + (i + 1) * 100_000_000
      events.append(event('carState', ns))
      if i == 10:
        events.append(event('initData', ns - 50_000_000))  # cross-service chronology is not global
      events.append(event('carControl', ns, valid=i != 12))
      events.append(event('controlsState', ns))
    report = analyze_segments((SegmentInput('a', 0, serialized(events)),)).segments[0]
    self.assertEqual(len(report.windows), 2)
    self.assertEqual(dict(report.exclusions)['missing_or_stale_source'], 1)
    self.assertNotIn('invalid_or_reordered_timestamp', dict(report.exclusions))
    before = {point.continuity_id for point in report.series if point.mono_ns < base + 1_300_000_000}
    after = {point.continuity_id for point in report.series if point.mono_ns > base + 1_300_000_000}
    self.assertTrue(before and after)
    self.assertTrue(before.isdisjoint(after))

  def test_future_publisher_arrives_before_earlier_controls_frame(self):
    base = 1_000_000_000
    events = [event('carParams', base)]
    for i in range(12):
      ns = base + (i + 1) * 100_000_000
      if i != 4:
        events.extend((event('carState', ns), event('carControl', ns)))
      if i == 3:
        future = ns + 100_000_000
        events.extend((event('carState', future), event('carControl', future)))
      events.append(event('controlsState', ns))
    report = analyze_segments((SegmentInput('a', 0, serialized(events)),)).segments[0]
    self.assertEqual(report.status, 'measured')
    self.assertEqual(report.eligible_samples, 10)
    self.assertNotIn('missing_or_stale_source', dict(report.exclusions))

  def test_invalid_vehicle_source_and_extreme_values(self):
    events = [event('carParams', 1_000_000_000)]
    for i in range(6):
      ns = 1_100_000_000 + i * 100_000_000
      events.extend((event('carState', ns, can_valid=i != 0), event('carControl', ns),
                     event('controlsState', ns, desired=3.4e38 if i == 2 else .4, active=i != 3)))
    report = analyze_segments((SegmentInput('a', 0, serialized(events)),)).segments[0]
    self.assertEqual(dict(report.exclusions)['invalid_car_state'], 1)
    self.assertEqual(dict(report.exclusions)['invalid_numeric'], 1)
    self.assertEqual(dict(report.exclusions)['lateral_inactive'], 1)
    self.assertIsNone(report.mean_abs_error)


if __name__ == '__main__':
  unittest.main()
