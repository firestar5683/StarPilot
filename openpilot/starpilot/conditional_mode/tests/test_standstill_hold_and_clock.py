import unittest

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.consumer import ModeConsumer
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.projection import STANDSTILL_PATH_JITTER_M, _horizon, _standstill_path_extent
from openpilot.starpilot.conditional_mode.stop import StopFrame, StopLead, StopLightDetector
from openpilot.starpilot.conditional_mode.tests.test_stop_commit_transport import CLEAR_97_X
from openpilot.starpilot.conditional_mode.tests.test_waiting_barrier import DRIVE, FINGERPRINT, MS, T, proposal


def sample(consumer, event, now, boot, skew):
  value = event.slcState.conditionalMode
  return consumer.sample(event.slcState, now_ns=now, now_boot_ns=boot, sample_skew_ns=skew,
    message_ns=int(event.logMonoTime), receipt_ns=int(event.logMonoTime), drive_id=DRIVE,
    model_ns=int(value.modelMonoTime), car_state_ns=int(value.carStateMonoTime),
    authority=True, stock_experimental=False, choice=ModeChoice.CEM, settings_fingerprint=FINGERPRINT)


def stop_frame(t, *, horizon=None, extent=None, standstill=True, gas=False):
  return StopFrame(observed_mono_s=t, now_mono_s=t, speed_mps=0.0, model_horizon_m=horizon, model_stop_time_s=8.0,
    traffic_mode=False, stop_sign_confirmed=False, forcing_stop=False, lead=StopLead(False), standstill=standstill,
    left_blinker=False, right_blinker=False, steering_angle_deg=0.0, driving_in_curve=False,
    car_fingerprint='HYUNDAI_IONIQ_6', dashboard_stop_sign=False, pedal_override=gas, model_tick_mono_s=t,
    model_should_stop=False, standstill_path_extent_m=extent)


class TestPairedClockMidpoint(unittest.TestCase):
  def warm(self, boot_offset):
    consumer = ModeConsumer()
    result = None
    for index in range(3):
      observed = T + index * 50 * MS
      now = observed + 30 * MS
      result = sample(consumer, proposal(observed - 2 * MS, observed - MS, observed, index + 1), now, now + boot_offset, 4_000)
    return consumer, result

  def test_boottime_trailing_midpoint_within_skew_is_accepted(self):
    consumer, result = self.warm(-2_000)
    self.assertTrue(result.accepted and result.experimental)
    self.assertIsNone(consumer.rejection)

  def test_boottime_trailing_midpoint_beyond_skew_is_rejected(self):
    consumer, _ = self.warm(-2_000)
    observed = T + 150 * MS
    now = observed + 30 * MS
    result = sample(consumer, proposal(observed - 2 * MS, observed - MS, observed, 4), now, now - 4_001, 4_000)
    self.assertFalse(result.accepted)
    self.assertEqual(consumer.rejection, 'clock_inputs')


class TestUncommittedStandstillHold(unittest.TestCase):
  def run_frames(self, detector, extents, start=100.0):
    return [detector.step(stop_frame(start + index * 0.05, extent=extent)) for index, extent in enumerate(extents)]

  def test_short_jittery_path_holds_and_extending_path_releases_with_hysteresis(self):
    detector = StopLightDetector()
    observations = self.run_frames(detector, [3.0] * 5 + [52.0] * 5 + [60.0] * 5)
    self.assertTrue(all(o.standstill_hold is True for o in observations[:10]))
    self.assertEqual(observations[0].standstill_reason, 'light')
    self.assertTrue(all(o.standstill_hold is False for o in observations[10:]))
    self.assertFalse(detector.committed)

  def test_missing_extent_stays_unknown(self):
    observations = self.run_frames(StopLightDetector(), [None] * 5)
    self.assertTrue(all(o.standstill_hold is None for o in observations))

  def test_tolerant_extent_cannot_release_a_committed_stop(self):
    detector = StopLightDetector()
    detector.committed = True
    detector.commit_distance_m = 20.0
    observations = self.run_frames(detector, [80.0] * 20)
    self.assertTrue(all(o.standstill_hold is True and o.light_detected is True for o in observations))
    self.assertTrue(detector.committed)


class TestStandstillPathExtent(unittest.TestCase):
  def test_recorded_stationary_jitter_has_extent_but_no_spatial_horizon(self):
    model = messaging.new_message('modelV2').modelV2
    model.position.x = CLEAR_97_X
    self.assertIsNone(_horizon(model))
    self.assertEqual(_standstill_path_extent(model), max(CLEAR_97_X))

  def test_dip_beyond_jitter_is_rejected(self):
    model = messaging.new_message('modelV2').modelV2
    values = list(CLEAR_97_X)
    values[20] = values[19] - STANDSTILL_PATH_JITTER_M - 0.01
    model.position.x = values
    self.assertIsNone(_standstill_path_extent(model))
