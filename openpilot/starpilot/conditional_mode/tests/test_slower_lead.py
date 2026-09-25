"""Frozen Following/CEM slower-lead behavior with actual current RadarState wire."""

from dataclasses import replace
import unittest

from openpilot.cereal import messaging
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import COMFORT_BRAKE
from openpilot.starpilot.conditional_mode.policy import LeadEvidence
from openpilot.starpilot.conditional_mode.slower_lead import SlowerLeadDetector, SlowerLeadFrame, following_slow_lead


def wire_lead(*, present=True, radar=True, distance=50.0, speed=20.0, probability=0.95, tracked=True):
  event = messaging.new_message('radarState', valid=True)
  lead = event.radarState.leadOne
  lead.present = present
  lead.radar = radar
  lead.dRel = distance
  lead.vLead = speed
  lead.aLeadK = 0.0
  lead.modelProb = probability
  decoded = messaging.log_from_bytes(event.to_bytes()).radarState.leadOne
  return LeadEvidence(decoded.present, tracked, decoded.radar, decoded.dRel, decoded.vLead, decoded.aLeadK, decoded.modelProb)


def frame(
  tick: int,
  *,
  lead=None,
  speed=30.0,
  headway=1.45,
  long_active=True,
  slower=True,
  stopped=False,
  previous_experimental=False,
  traffic=False,
  sign=False,
  turn=False,
  standstill=False,
):
  return SlowerLeadFrame(
    observed_mono_s=100.0 + tick * 0.05,
    now_mono_s=100.005 + tick * 0.05,
    speed_mps=speed,
    selected_follow_s=headway,
    long_active=long_active,
    lead=lead if lead is not None else wire_lead(),
    slower_option=slower,
    stopped_option=stopped,
    previous_experimental=previous_experimental,
    traffic_mode=traffic,
    stop_sign_confirmed=sign,
    committed_turn_scene=turn,
    standstill=standstill,
  )


class TestSlowerLead(unittest.TestCase):
  def test_following_formula_uses_actual_comfort_brake_and_headway(self):
    self.assertEqual(COMFORT_BRAKE, 2.5)
    self.assertTrue(
      following_slow_lead(long_active=True, tracking=True, option=True, speed_mps=30, lead_distance_m=50, lead_speed_mps=20, selected_follow_s=1.45)
    )
    self.assertFalse(
      following_slow_lead(long_active=True, tracking=True, option=True, speed_mps=30, lead_distance_m=30, lead_speed_mps=20, selected_follow_s=1.45)
    )
    self.assertFalse(
      following_slow_lead(long_active=False, tracking=True, option=True, speed_mps=30, lead_distance_m=50, lead_speed_mps=20, selected_follow_s=1.45)
    )

  def test_filtered_slower_lead_and_authority_source(self):
    detector = SlowerLeadDetector()
    states = [detector.step(frame(tick)) for tick in range(25)]
    self.assertTrue(states[0].following_slow)
    self.assertFalse(states[0].detected)
    self.assertTrue(states[-1].detected)
    off = detector.step(frame(25, long_active=False))
    self.assertFalse(off.following_slow)
    self.assertTrue(off.detected)  # Frozen filter release is not instantaneous.
    for tick in range(26, 46):
      state = detector.step(frame(tick, long_active=False))
    self.assertFalse(state.detected)

  def test_stopped_and_vision_continuity_are_distinct(self):
    detector = SlowerLeadDetector()
    stopped_lead = wire_lead(distance=10, speed=0, radar=True)
    low = detector.step(frame(0, speed=5, lead=stopped_lead, slower=False, stopped=True))
    self.assertTrue(low.stopped_candidate)
    self.assertFalse(low.following_slow)
    for tick in range(1, 15):
      low = detector.step(frame(tick, speed=5, lead=stopped_lead, slower=False, stopped=True))
    self.assertTrue(low.detected)

    vision = SlowerLeadDetector()
    tracked = wire_lead(distance=30, speed=10, radar=False, tracked=True)
    for tick in range(25):
      out = vision.step(frame(tick, speed=20, lead=tracked, previous_experimental=True))
    self.assertTrue(out.detected)
    untracked = wire_lead(distance=30, speed=10, radar=False, tracked=False)
    continuity = vision.step(frame(25, speed=20, lead=untracked, previous_experimental=True))
    self.assertFalse(continuity.following_slow)
    self.assertTrue(continuity.vision_candidate)
    self.assertTrue(continuity.detected)

  def test_fast_clear_unknown_and_repeated_source(self):
    detector = SlowerLeadDetector()
    for tick in range(25):
      detector.step(frame(tick))
    self.assertTrue(detector.detected)
    near_match = wire_lead(distance=50, speed=29.8)
    cleared = detector.step(frame(25, lead=near_match))
    self.assertFalse(cleared.detected)
    value = detector.filter.x
    repeated = detector.step(replace(frame(25), now_mono_s=101.27))
    self.assertIsNone(repeated.detected)
    self.assertEqual(detector.filter.x, value)
    unknown = detector.step(replace(frame(26), selected_follow_s=None))
    self.assertIsNone(unknown.detected)
    self.assertEqual(detector.filter.x, 0.0)
    stale = detector.step(replace(frame(27), now_mono_s=102.0))
    self.assertIsNone(stale.detected)

  def test_standstill_drops_old_consensus_and_malformed_lead_stays_unknown(self):
    detector = SlowerLeadDetector()
    for tick in range(25):
      detector.step(frame(tick))
    halted = detector.step(frame(25, standstill=True))
    self.assertIsNone(halted.detected)
    self.assertEqual(detector.filter.x, 0.0)
    invalid = detector.step(replace(frame(26), lead=wire_lead(distance=50, probability=float('nan'))))
    self.assertIsNone(invalid.detected)

  def test_fresh_known_absence_releases_without_numeric_lead_defaults(self):
    detector = SlowerLeadDetector()
    for tick in range(25):
      present = detector.step(frame(tick))
    self.assertTrue(present.detected)
    absent = LeadEvidence(False, False, True)
    released = detector.step(frame(25, lead=absent))
    self.assertFalse(released.following_slow)
    self.assertFalse(released.detected)
    self.assertFalse(released.stopped_candidate)
    self.assertFalse(released.vision_candidate)
    unknown = detector.step(replace(frame(26, lead=absent), observed_mono_s=100.0))
    self.assertIsNone(unknown.detected)

  def test_model_cadence_advances_when_radar_and_options_update_at_half_rate(self):
    detector = SlowerLeadDetector()
    for tick in range(28):
      model_time = 100.0 + tick * 0.05
      source_time = 100.0 + (tick // 2) * 0.1
      result = detector.step(replace(frame(tick), observed_mono_s=source_time, model_tick_mono_s=model_time))
    self.assertTrue(result.detected)
    value = detector.filter.x
    repeated = detector.step(replace(frame(27), observed_mono_s=model_time, model_tick_mono_s=model_time, now_mono_s=model_time + 0.01))
    self.assertIsNone(repeated.detected)
    self.assertEqual(detector.filter.x, value)


if __name__ == '__main__':
  unittest.main()
