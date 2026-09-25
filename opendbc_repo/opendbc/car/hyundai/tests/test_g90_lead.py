"""Source-derived G90 lead hysteresis and existing CAN encoder fields."""
import unittest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, structs
from opendbc.car.hyundai.g90_lead import G90LeadState, LeadObservation
from opendbc.car.hyundai.hyundaican import create_acc_commands
from opendbc.car.hyundai.tests.test_g90_longitudinal import params
from opendbc.car.hyundai.values import CAR, DBC


def observation(distance=26., relative=-.5, present=True, drive=1):
  return LeadObservation(drive, 100, 101, 102, present, distance, relative)


class TestG90Lead(unittest.TestCase):
  def test_visibility_gap_and_relative_state_counts_controller_updates(self):
    state = G90LeadState()
    for _ in range(49):
      lead = state.update(observation(), False)
    self.assertFalse(lead.lead_visible)
    self.assertEqual(lead.object_gap, 0)
    lead = state.update(observation(), False)
    self.assertTrue(lead.lead_visible)
    self.assertEqual((lead.object_gap, lead.object_rel_gap), (4, 2))
    for _ in range(49):
      lead = state.update(observation(0, 0, False), False)
    self.assertTrue(lead.lead_visible)
    self.assertFalse(state.update(observation(0, 0, False), False).lead_visible)
    state = G90LeadState()
    for frame in range(50):
      lead = state.update(observation(15 if frame % 2 else 26), False)
    self.assertEqual(lead.object_gap, 2)  # Original non-current gaps share one counter.
    self.assertEqual(state.update(observation(.05, -1), False).lead_distance, 20.)
    self.assertEqual(state.update(observation(999, -999), False).lead_rel_speed, -170.)
    self.assertEqual(state.update(observation(26, -.2), False).object_rel_gap, 1)

  def test_optional_payload_preserves_sibling_and_accel_aeb_bytes(self):
    for car, alpha in ((CAR.GENESIS_G90, True), (CAR.GENESIS_G90, False), (CAR.GENESIS_G80, True)):
      cp = params(car, alpha)
      hud = structs.CarControl.HUDControl(leadVisible=True, leadDistanceBars=2)
      state = G90LeadState()
      for _ in range(50):
        lead = state.update(observation(), False)
      def packed(payload, cp=cp, hud=hud):
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        return create_acc_commands(packer, True, .2, 1., 7, hud, 70., False, False, True, cp, lead_data=payload)
      baseline, changed = packed(None), packed(lead)
      if car != CAR.GENESIS_G90 or not alpha:
        self.assertEqual(baseline, changed)
      else:
        for old, new in zip(baseline, changed, strict=True):
          if old[0] in (0x421, 0x38d):
            self.assertEqual(old, new)
        parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('FCA11', 0), ('SCC12', 0)], 0)
        parser.update([(1_000_000_000, changed)])
        self.assertEqual(parser.vl['FCA11']['FCA_Status'], 1)
        non_fca = create_acc_commands(CANPacker(DBC[cp.carFingerprint][Bus.pt]), True, .2, 1., 7,
                                      hud, 70., False, False, False, cp, lead_data=lead)
        parser.update([(1_010_000_000, non_fca)])
        self.assertEqual(parser.vl['SCC12']['AEB_Status'], 1)

