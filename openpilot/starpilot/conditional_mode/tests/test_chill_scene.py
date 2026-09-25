"""Frozen Conditional Chill low-speed and launch behavior over fresh owner inputs."""

from dataclasses import replace
import unittest

from openpilot.starpilot.conditional_mode.chill_scene import (
  ChillLead, ChillSceneDetector, ChillSceneFrame, LAUNCH_EXIT_MPS, LOW_SPEED_STOP_MAX_MPS,
)


def frame(tick: int, **changes) -> ChillSceneFrame:
  sample = ChillSceneFrame(
    observed_mono_s=100.0 + tick * 0.05,
    model_tick_mono_s=100.0 + tick * 0.05,
    now_mono_s=100.005 + tick * 0.05,
    speed_mps=0.0,
    lead=ChillLead(False),
    tracking_lead=False,
    raw_model_stopped=False,
    model_stopped=False,
    stop_light_model_detected=False,
    stop_light_detected=False,
    stop_sign_confirmed=False,
    forcing_stop=False,
    red_light=False,
    plan_forcing_stop=False,
    should_stop=False,
    allow_throttle=True,
    selfdrive_enabled=True,
  )
  return replace(sample, **changes)


class TestChillScene(unittest.TestCase):
  def test_low_speed_stop_edges_and_lead_boundary(self):
    detector = ChillSceneDetector()
    stopped = detector.step(frame(0, speed_mps=LOW_SPEED_STOP_MAX_MPS - 1e-6, raw_model_stopped=True))
    self.assertTrue(stopped.low_speed_stop_scene)
    at_limit = detector.step(frame(1, speed_mps=LOW_SPEED_STOP_MAX_MPS, raw_model_stopped=True))
    self.assertFalse(at_limit.low_speed_stop_scene)
    lead = ChillLead(True, distance_m=39.9, speed_mps=5.9, relative_speed_mps=0.0, accel_mps2=0.0)
    self.assertTrue(detector.step(frame(2, speed_mps=0.5, lead=lead)).low_speed_stop_scene)
    self.assertFalse(detector.step(frame(3, speed_mps=0.5, lead=replace(lead, distance_m=40.0))).low_speed_stop_scene)
    self.assertFalse(detector.step(frame(4, speed_mps=0.5, lead=replace(lead, speed_mps=6.0))).low_speed_stop_scene)

  def test_launch_assist_uses_raw_relative_speed_and_forces_immediate_exit(self):
    detector = ChillSceneDetector()
    lead = ChillLead(True, distance_m=18.0, speed_mps=0.8, relative_speed_mps=0.05, accel_mps2=0.2)
    blocked = detector.step(frame(0, lead=lead, tracking_lead=True))
    self.assertFalse(blocked.launch_candidate)
    self.assertEqual(blocked.lead_reason, 'not_departing')
    departure = detector.step(frame(1, lead=replace(lead, relative_speed_mps=0.5), tracking_lead=True))
    self.assertTrue(departure.launch_candidate)
    self.assertEqual(departure.launch_status, 'lead')
    self.assertEqual(departure.lead_reason, 'departing')
    # A previous candidate exits immediately even if dwell/soft-exit policy exists elsewhere.
    stop = detector.step(frame(2, lead=lead, tracking_lead=True, should_stop=True))
    self.assertFalse(stop.launch_candidate)
    self.assertTrue(stop.forced_exit)
    self.assertEqual(stop.speed_reason, 'longitudinal_stop')
    self.assertFalse(detector.launch_active)

  def test_speed_exit_and_no_lead_status(self):
    detector = ChillSceneDetector()
    entered = detector.step(frame(0))
    self.assertTrue(entered.launch_candidate)
    self.assertEqual(entered.launch_status, 'speed')
    still = detector.step(frame(1, speed_mps=LAUNCH_EXIT_MPS - 1e-6))
    self.assertTrue(still.launch_candidate)
    exited = detector.step(frame(2, speed_mps=LAUNCH_EXIT_MPS))
    self.assertTrue(exited.forced_exit)
    self.assertFalse(exited.launch_candidate)
    self.assertEqual(exited.speed_reason, 'exit_speed')
    high_new = detector.step(frame(3, speed_mps=1.001))
    self.assertFalse(high_new.launch_candidate)
    self.assertEqual(high_new.speed_reason, 'above_entry_speed')

  def test_missing_stale_replayed_or_malformed_evidence_never_enables(self):
    invalid = (
      (replace(frame(0), should_stop=None), False),
      (replace(frame(0), now_mono_s=100.26), None),
      (replace(frame(0), now_mono_s=99.99), None),
      (replace(frame(0), lead=ChillLead(True, distance_m=18.0, speed_mps=0.8, relative_speed_mps=None, accel_mps2=0.2)), True),
      (replace(frame(0), lead=ChillLead(True, distance_m=18.0, speed_mps=0.8, relative_speed_mps=float('nan'), accel_mps2=0.2)), True),
      (replace(frame(0), speed_mps=True), None),
    )
    for item, low_speed_stop in invalid:
      with self.subTest(item=item):
        detector = ChillSceneDetector()
        value = detector.step(item)
        self.assertIsNone(value.launch_candidate)
        self.assertEqual(value.low_speed_stop_scene, low_speed_stop)
        self.assertFalse(detector.launch_active)
    detector = ChillSceneDetector()
    self.assertTrue(detector.step(frame(0)).launch_candidate)
    repeated = detector.step(replace(frame(0), now_mono_s=100.02))
    self.assertIsNone(repeated.launch_candidate)
    self.assertTrue(repeated.forced_exit)
    self.assertFalse(detector.launch_active)
    self.assertTrue(detector.step(frame(3)).launch_candidate)
    self.assertIsNone(detector.step(frame(6)).launch_candidate)  # 150 ms gap exceeds two model ticks.
    self.assertTrue(detector.step(frame(7)).launch_candidate)

  def test_stop_and_plan_vetoes_are_distinct_from_lead_departure(self):
    for changes in ({'stop_light_detected': True}, {'red_light': True}, {'plan_forcing_stop': True},
                    {'raw_model_stopped': True}, {'model_stopped': True}, {'stop_sign_confirmed': True},
                    {'forcing_stop': True}, {'allow_throttle': False}, {'selfdrive_enabled': False}):
      with self.subTest(changes=changes):
        detector = ChillSceneDetector()
        value = detector.step(frame(0, **changes))
        self.assertFalse(value.launch_candidate)
        self.assertFalse(value.forced_exit)


if __name__ == '__main__':
  unittest.main()
