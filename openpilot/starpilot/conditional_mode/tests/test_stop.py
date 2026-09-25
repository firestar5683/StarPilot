"""Frozen stop-scene filtering with explicit current-message and owner inputs."""

from dataclasses import replace
import unittest

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.stop import StopFrame, StopLead, StopLightDetector


def wire_model(horizon_m: float, should_stop: bool):
  event = messaging.new_message('modelV2', valid=True)
  event.modelV2.timestampEof = 2_000_000_000
  event.modelV2.position.x = [horizon_m * index / 32 for index in range(33)]
  event.modelV2.position.y = [0.0] * 33
  event.modelV2.action.shouldStop = should_stop
  return messaging.log_from_bytes(event.to_bytes()).modelV2


def frame(
  tick: int,
  *,
  horizon=40.0,
  speed=10.0,
  lead=None,
  standstill=False,
  stop_sign=False,
  dashboard_sign=False,
  pedal=False,
  forcing=False,
  traffic=False,
  left=False,
  right=False,
  steering=0.0,
  measured_curve=False,
  model_time=8.0,
):
  return StopFrame(
    observed_mono_s=100.0 + tick * 0.05,
    now_mono_s=100.005 + tick * 0.05,
    speed_mps=speed,
    model_horizon_m=horizon,
    model_stop_time_s=model_time,
    traffic_mode=traffic,
    stop_sign_confirmed=stop_sign,
    forcing_stop=forcing,
    lead=lead if lead is not None else StopLead(False),
    standstill=standstill,
    left_blinker=left,
    right_blinker=right,
    steering_angle_deg=steering,
    driving_in_curve=measured_curve,
    car_fingerprint='HYUNDAI_IONIQ_6',
    dashboard_stop_sign=dashboard_sign,
    pedal_override=pedal,
  )


class TestStopDetector(unittest.TestCase):
  def test_standstill_model_threshold_replay_has_spatial_release_band(self):
    detector = StopLightDetector()
    # Preserve the 50 m entry threshold across jitter without a timer.
    first = detector.step(frame(0, horizon=50.1, speed=0., standstill=True))
    self.assertFalse(first.standstill_hold)
    for tick, horizon in enumerate((49.9, 50.1, 49.9, 50.1, 53.999), 1):
      current = detector.step(frame(tick, horizon=horizon, speed=0., standstill=True))
      self.assertTrue(current.standstill_hold)
      self.assertEqual(current.standstill_reason, 'light')
    released = detector.step(frame(6, horizon=54., speed=0., standstill=True))
    self.assertFalse(released.standstill_hold)
    self.assertFalse(detector.step(frame(7, horizon=50.1, speed=0., standstill=True)).standstill_hold)

  def test_standstill_model_band_withdraws_on_pedal_movement_and_unknown(self):
    for withdrawal in ({'pedal': True}, {'pedal': None}, {'dashboard_sign': None}, {'standstill': False}, {'traffic': None}):
      detector = StopLightDetector()
      self.assertTrue(detector.step(frame(0, horizon=49.9, speed=0., standstill=True)).standstill_hold)
      values = dict(horizon=51., speed=0., standstill=True)
      values.update(withdrawal)
      detector.step(frame(1, **values))
      self.assertFalse(detector.step(frame(2, horizon=51., speed=0., standstill=True)).standstill_hold)

  def test_speed_dependent_light_boost_and_cap_match_stop_horizon(self):
    # Below35mph: model seconds unchanged. Above45mph:1.2x, capped9s.
    for mph, seconds, adjusted in ((25., 8., 8.), (35., 8., 8.), (40., 8., 8.5),
                                   (45., 8., 9.), (60., 5., 6.), (75., 10., 9.)):
      with self.subTest(mph=mph, seconds=seconds):
        threshold = mph * .44704 * adjusted
        below = StopLightDetector().step(frame(0, speed=mph * .44704, horizon=threshold - 2.501, model_time=seconds))
        above = StopLightDetector().step(frame(0, speed=mph * .44704, horizon=threshold - 2.499, model_time=seconds))
        self.assertTrue(below.model_stopping)
        self.assertFalse(above.model_stopping)

  def test_current_should_stop_not_frozen_stop_light_alias(self):
    model = wire_model(192.0, True)
    self.assertTrue(model.action.shouldStop)
    detector = StopLightDetector()
    samples = [detector.step(frame(tick, horizon=float(model.position.x[-1]))) for tick in range(25)]
    self.assertTrue(all(sample.model_stopping is False for sample in samples))
    self.assertFalse(samples[-1].light_detected)
    short = wire_model(30.0, False)
    self.assertFalse(short.action.shouldStop)
    samples = [detector.step(frame(tick + 25, horizon=float(short.position.x[-1]))) for tick in range(25)]
    self.assertTrue(samples[-1].light_detected)

  def test_relevant_radar_lead_blocks_false_light_and_vision_handoff(self):
    detector = StopLightDetector()
    radar = StopLead(True, distance_m=30.0, speed_mps=7.0, radar=True, model_probability=0.95, tracked=True)
    blocked = [detector.step(frame(tick, lead=radar)) for tick in range(30)]
    self.assertFalse(blocked[-1].light_detected)
    vision = StopLead(True, distance_m=10.0, speed_mps=1.0, radar=False, model_probability=0.95, tracked=False)
    detector.reset()
    handoff = detector.step(frame(0, horizon=2.0, speed=1.0, lead=vision))
    self.assertTrue(handoff.light_detected)

  def test_standstill_sign_retains_until_pedal_and_light_can_release(self):
    detector = StopLightDetector()
    sign = detector.step(frame(0, horizon=192, speed=0, standstill=True, stop_sign=True, dashboard_sign=False, pedal=False))
    self.assertTrue(sign.light_detected)
    self.assertTrue(sign.standstill_hold)
    self.assertEqual(sign.standstill_reason, 'sign')
    lost = detector.step(frame(1, horizon=192, speed=0, standstill=True, dashboard_sign=False, pedal=False))
    self.assertTrue(lost.standstill_hold)  # Sign reason is retained at standstill.
    release = detector.step(frame(2, horizon=192, speed=0, standstill=True, dashboard_sign=False, pedal=True))
    self.assertFalse(release.standstill_hold)
    self.assertIsNone(release.standstill_reason)
    # A pure light/model hold has no stop-sign latch after its model clears.
    light = StopLightDetector()
    for tick in range(25):
      output = light.step(frame(tick, horizon=30.0, speed=10.0))
    self.assertTrue(output.light_detected)
    at_stop = light.step(frame(25, horizon=30.0, speed=0.0, standstill=True))
    self.assertTrue(at_stop.standstill_hold)
    self.assertEqual(at_stop.standstill_reason, 'light')
    for tick in range(26, 126):
      cleared = light.step(frame(tick, horizon=192.0, speed=0.0, standstill=True))
    self.assertFalse(cleared.standstill_hold)
    self.assertIsNone(cleared.standstill_reason)

  def test_turn_high_speed_and_unknown_source_reset(self):
    detector = StopLightDetector()
    for tick in range(25):
      result = detector.step(frame(tick))
    self.assertTrue(result.light_detected)
    turn = detector.step(frame(25, speed=5.0, left=True, steering=45.0))
    self.assertFalse(turn.light_detected)
    self.assertFalse(detector.light_detected)
    for tick in range(26, 50):
      detector.step(frame(tick))
    high = detector.step(frame(50, speed=34.0))
    self.assertFalse(high.light_detected)
    unknown = detector.step(replace(frame(51), traffic_mode=None))
    self.assertIsNone(unknown.light_detected)
    self.assertFalse(detector.light_detected)

  def test_confirmed_sign_precedes_turn_and_missing_active_curve_stays_unknown(self):
    detector = StopLightDetector()
    sign = detector.step(frame(0, speed=5.0, left=True, steering=45.0, stop_sign=True))
    self.assertTrue(sign.light_detected)
    missing = detector.step(frame(1, speed=5.0, left=True, steering=45.0, measured_curve=None))
    self.assertIsNone(missing.light_detected)
    self.assertFalse(detector.light_detected)
    recovered = detector.step(frame(2, speed=5.0, left=True, steering=44.0, measured_curve=True))
    self.assertFalse(recovered.light_detected)
    self.assertFalse(detector.light_detected)

  def test_repeated_source_gap_and_missing_sign_owner(self):
    detector = StopLightDetector()
    first = frame(0)
    self.assertFalse(detector.step(first).light_detected)
    value = detector.light_filter.x
    repeated = detector.step(replace(first, now_mono_s=100.02))
    self.assertIsNone(repeated.light_detected)
    self.assertEqual(detector.light_filter.x, value)
    gap = detector.step(frame(6))
    self.assertIsNone(gap.light_detected)
    self.assertEqual(detector.light_filter.x, 0)
    missing = detector.step(replace(frame(7), stop_sign_confirmed=None))
    self.assertIsNone(missing.light_detected)

  def test_model_cadence_advances_with_staggered_fresh_owner_observations(self):
    detector = StopLightDetector()
    for tick in range(28):
      model_time = 100.0 + tick * 0.05
      owner_time = 100.0 + (tick // 2) * 0.1
      result = detector.step(replace(frame(tick), observed_mono_s=owner_time, model_tick_mono_s=model_time))
    self.assertTrue(result.light_detected)
    value = detector.light_filter.x
    repeated = detector.step(replace(frame(27), observed_mono_s=model_time, model_tick_mono_s=model_time, now_mono_s=model_time + 0.01))
    self.assertIsNone(repeated.light_detected)
    self.assertEqual(detector.light_filter.x, value)

  def test_exact_two_frame_gap_does_not_reset_the_stop_filter(self):
    detector = StopLightDetector()
    for tick in range(40):
      stamp = 100.0 + tick / 10
      output = detector.step(replace(frame(tick), observed_mono_s=stamp, now_mono_s=stamp + .005))
      self.assertIsNotNone(output.light_detected)
    self.assertTrue(output.light_detected)
    stamp += .100000001
    output = detector.step(replace(frame(40), observed_mono_s=stamp, now_mono_s=stamp + .005))
    self.assertTrue(output.light_detected)
    stamp += .250000001
    output = detector.step(replace(frame(41), observed_mono_s=stamp, now_mono_s=stamp + .005))
    self.assertIsNone(output.light_detected)
    self.assertFalse(detector.light_detected)


if __name__ == '__main__':
  unittest.main()
