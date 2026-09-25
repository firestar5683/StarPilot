"""Tagged Ioniq start admission; stock and other cars retain native LongControl."""

from openpilot.starpilot.longitudinal.extension import LongitudinalContext
from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
from openpilot.starpilot.longitudinal.tests.extension_helpers import attach_inputs
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from opendbc.car import gen_empty_fingerprint
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.ioniq6_handoff import build_ioniq6_hda2_long_candidate
from opendbc.car.hyundai.values import CAR
from opendbc.car.structs import car
from openpilot.cereal import messaging
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.controls.lib.longcontrol import LongControl, LongCtrlState
from openpilot.starpilot.longitudinal.ioniq6_start import (STRONG_SETTLE_FRAMES, StartEvidence, eligible)


def candidate(*, alternate=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[2].update({0x110: 32, 0x362: 32} if alternate else {0x50: 16, 0x2A4: 24})
  fingerprint[1].update({0x1CF: 8, 0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24,
                         0x1BA: 24, 0x1E5: 16, 0x36A: 16})
  fingerprint[0][0x3A5] = 24
  fingerprint[0][0x100] = 24
  stock = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False)
  return stock, build_ioniq6_hda2_long_candidate(stock, fingerprint)


def car_state(*, speed=0.0, gas=False, brake=False, standstill=True, valid=True, timeout=False):
  event = messaging.new_message('carState', valid=True)
  cs = event.carState
  cs.vEgo = speed
  cs.aEgo = 0.0
  cs.gasPressed = gas
  cs.brakePressed = brake
  cs.cruiseState.standstill = standstill
  cs.canValid = valid
  cs.canTimeout = timeout
  return messaging.log_from_bytes(event.to_bytes()).carState


def evidence(frame=0, *, lead_clear=True, plan_fresh=True, drive_id=900_000_000):
  return StartEvidence(True, plan_fresh, lead_clear, drive_id, 1_050_000_000 + frame * 10_000_000)


GOOD = evidence()
LIMITS = (-3.0, 2.0)


class Ioniq6StartTests(unittest.TestCase):
  def test_exact_tag_and_topology_only(self):
    for alternate in (False, True):
      stock, tagged = candidate(alternate=alternate)
      self.assertFalse(eligible(stock))
      self.assertTrue(eligible(tagged))
      self.assertIsNone(extension_state(LongControl(stock), 'ioniq6_start'))
      self.assertIsNotNone(extension_state(LongControl(tagged), 'ioniq6_start'))
      tagged.safetyConfigs[0].safetyModel = car.CarParams.SafetyModel.noOutput
      self.assertFalse(eligible(tagged))

  def test_stock_controller_preserves_native_starting_seed_fallback(self):
    stock, _ = candidate()
    native = LongControl(stock)
    native.long_control_state = LongCtrlState.starting
    output = native.update(True, car_state(), 0.8, False, LIMITS)
    self.assertEqual(native.long_control_state, LongCtrlState.starting)
    self.assertGreaterEqual(output, LIMITS[0])
    self.assertLessEqual(output, LIMITS[1])

  def test_35_fresh_strong_frames_after_stop_and_bounded_start(self):
    _, tagged = candidate()
    loc = LongControl(tagged)
    cs = car_state()
    loc.update(True, cs, -0.3, True, LIMITS, context=LongitudinalContext(start_evidence=evidence()))
    self.assertEqual(loc.long_control_state, LongCtrlState.stopping)
    for frame in range(1, STRONG_SETTLE_FRAMES):
      loc.update(True, cs, 0.8, False, LIMITS, context=LongitudinalContext(start_evidence=evidence(frame)))
      self.assertNotEqual(loc.long_control_state, LongCtrlState.starting)
    self.assertEqual(extension_state(loc, 'ioniq6_start').strong_frames, STRONG_SETTLE_FRAMES - 1)
    output = loc.update(True, cs, 0.8, False, LIMITS, context=LongitudinalContext(start_evidence=evidence(STRONG_SETTLE_FRAMES)))
    self.assertEqual(loc.long_control_state, LongCtrlState.starting)
    self.assertAlmostEqual(output, 0.8)
    self.assertLessEqual(output, LIMITS[1])
    loc.update(True, car_state(speed=0.11, standstill=False), 0.8, False, LIMITS,
               context=LongitudinalContext(start_evidence=evidence(STRONG_SETTLE_FRAMES + 1)))
    self.assertEqual(loc.long_control_state, LongCtrlState.pid)

  def test_weak_unknown_or_pedal_resets_count_without_delaying_native_pid(self):
    _, tagged = candidate()
    for interruption in ((car_state(), 0.74, evidence(STRONG_SETTLE_FRAMES)),
                         (car_state(), 0.8, evidence(STRONG_SETTLE_FRAMES, lead_clear=None)),
                         (car_state(gas=True), 0.8, evidence(STRONG_SETTLE_FRAMES)),
                         (car_state(brake=True), 0.8, evidence(STRONG_SETTLE_FRAMES)),
                         (car_state(timeout=True), 0.8, evidence(STRONG_SETTLE_FRAMES)),
                         (car_state(), 0.8, evidence(STRONG_SETTLE_FRAMES, plan_fresh=False))):
      loc = LongControl(tagged)
      loc.update(True, car_state(), -0.2, True, LIMITS, context=LongitudinalContext(start_evidence=evidence()))
      for frame in range(1, STRONG_SETTLE_FRAMES):
        loc.update(True, car_state(), 0.8, False, LIMITS, context=LongitudinalContext(start_evidence=evidence(frame)))
      cs, target, observed = interruption
      loc.update(True, cs, target, False, LIMITS, context=LongitudinalContext(start_evidence=observed))
      self.assertEqual(extension_state(loc, 'ioniq6_start').strong_frames, 0)
      self.assertNotEqual(loc.long_control_state, LongCtrlState.starting)
      loc.update(True, car_state(standstill=False), 0.8, False, LIMITS,
                 context=LongitudinalContext(start_evidence=evidence(STRONG_SETTLE_FRAMES + 1, lead_clear=None)))
      self.assertEqual(loc.long_control_state, LongCtrlState.pid)

  def test_fresh_lead_and_negative_target_revoke_start(self):
    _, tagged = candidate()
    loc = LongControl(tagged)
    loc.update(True, car_state(), -0.2, True, LIMITS, context=LongitudinalContext(start_evidence=evidence()))
    for frame in range(1, STRONG_SETTLE_FRAMES + 1):
      loc.update(True, car_state(), 0.9, False, LIMITS, context=LongitudinalContext(start_evidence=evidence(frame)))
    self.assertEqual(loc.long_control_state, LongCtrlState.starting)
    loc.update(True, car_state(), -0.2, False, LIMITS,
               context=LongitudinalContext(start_evidence=evidence(STRONG_SETTLE_FRAMES + 1, lead_clear=False)))
    self.assertEqual(loc.long_control_state, LongCtrlState.pid)
    self.assertEqual(extension_state(loc, 'ioniq6_start').strong_frames, 0)
    loc.update(False, car_state(), 0.9, False, LIMITS, context=LongitudinalContext(start_evidence=GOOD))
    self.assertEqual(loc.long_control_state, LongCtrlState.off)

  def test_new_drive_restarts_strong_window(self):
    _, tagged = candidate()
    loc = LongControl(tagged)
    for frame in range(STRONG_SETTLE_FRAMES - 1):
      loc.update(True, car_state(), 0.9, False, LIMITS, context=LongitudinalContext(start_evidence=evidence(frame)))
    next_drive = evidence(STRONG_SETTLE_FRAMES - 1, drive_id=950_000_000)
    loc.update(True, car_state(), 0.9, False, LIMITS, context=LongitudinalContext(start_evidence=next_drive))
    self.assertNotEqual(loc.long_control_state, LongCtrlState.starting)
    self.assertEqual(extension_state(loc, 'ioniq6_start').strong_frames, 1)

  def test_loop_gap_and_repeated_clock_do_not_accumulate_history(self):
    _, tagged = candidate()
    loc = LongControl(tagged)
    for frame in range(STRONG_SETTLE_FRAMES - 1):
      loc.update(True, car_state(), 0.9, False, LIMITS, context=LongitudinalContext(start_evidence=evidence(frame)))
    loc.update(True, car_state(), 0.9, False, LIMITS, context=LongitudinalContext(start_evidence=evidence(STRONG_SETTLE_FRAMES - 2)))
    self.assertEqual(extension_state(loc, 'ioniq6_start').strong_frames, 1)
    loc.update(True, car_state(), 0.9, False, LIMITS, context=LongitudinalContext(start_evidence=evidence(STRONG_SETTLE_FRAMES + 10)))
    self.assertEqual(extension_state(loc, 'ioniq6_start').strong_frames, 1)

  def test_bursty_calls_cannot_replace_elapsed_340_ms_window(self):
    _, tagged = candidate()
    loc = LongControl(tagged)
    for frame in range(STRONG_SETTLE_FRAMES):
      burst = StartEvidence(True, True, True, 900_000_000, 1_050_000_000 + frame * 1_000_000)
      loc.update(True, car_state(), 0.9, False, LIMITS, context=LongitudinalContext(start_evidence=burst))
    self.assertEqual(extension_state(loc, 'ioniq6_start').strong_frames, STRONG_SETTLE_FRAMES)
    self.assertNotEqual(loc.long_control_state, LongCtrlState.starting)

  def test_serialized_radar_clear_requires_current_drive_and_planner(self):
    now = 1_050_000_000
    radar_event = messaging.new_message('radarState', valid=True)
    radar = messaging.log_from_bytes(radar_event.to_bytes()).radarState
    device_event = messaging.new_message('deviceState', valid=True)
    device_event.deviceState.started = True
    device_event.deviceState.startedMonoTime = 900_000_000
    device = messaging.log_from_bytes(device_event.to_bytes()).deviceState

    class FakeSubMaster(NS):
      def __getitem__(self, name):
        return {'radarState': radar, 'deviceState': device}[name]

    names = ('radarState', 'deviceState', 'carState', 'longitudinalPlan')
    sm = FakeSubMaster(seen=dict.fromkeys(names, True), alive=dict.fromkeys(names, True),
                       valid=dict.fromkeys(names, True),
                       logMonoTime=dict.fromkeys(names, now - 20_000_000),
                       recv_time=dict.fromkeys(names, (now - 10_000_000) / 1e9),
                       all_checks=lambda selected: True)
    controls = Controls.__new__(Controls)
    attach_inputs(controls)
    controls.longitudinal_inputs.ioniq6_start_enabled = True
    controls.longitudinal_inputs.ioniq6_boot_offset_ns = 500_000_000
    controls.longitudinal_inputs.ioniq6_source_floor_ns = 900_000_000
    self.enterContext(patch.object(controls, 'sm', sm, create=True))
    with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now + 500_000_000)):
      self.assertEqual(controls.longitudinal_inputs._ioniq6_start_evidence(), GOOD)
      sm.logMonoTime['longitudinalPlan'] = now - 160_000_000
      self.assertFalse(controls.longitudinal_inputs._ioniq6_start_evidence().plan_fresh)
      sm.logMonoTime['longitudinalPlan'] = now - 20_000_000
      sm.valid['radarState'] = False
      self.assertIsNone(controls.longitudinal_inputs._ioniq6_start_evidence().lead_clear)


if __name__ == '__main__':
  unittest.main()
