"""Current CP eligibility and bounded Toyota target-shaping traces."""

from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR
from openpilot.cereal import messaging
from openpilot.starpilot.longitudinal.toyota_output_policy import Lead, ToyotaOutputPolicy, clock_pair_ns, eligible, leads_from_radar


class ToyotaOutputPolicyTests(unittest.TestCase):
  def test_resume_clock_pair_requires_real_boottime(self):
    clock = NS(monotonic_ns=iter((100, 102)).__next__, clock_gettime_ns=lambda _clock: 900, CLOCK_BOOTTIME=7)
    with patch('openpilot.starpilot.longitudinal.toyota_output_policy.time', clock):
      self.assertEqual(clock_pair_ns(), (101, 900))
    clock = NS(monotonic_ns=lambda: 100, clock_gettime_ns=lambda _clock: 900)
    with patch('openpilot.starpilot.longitudinal.toyota_output_policy.time', clock):
      self.assertIsNone(clock_pair_ns())

  def assert_target(self, actual: float | None, expected: float) -> None:
    self.assertIsNotNone(actual)
    assert actual is not None
    self.assertAlmostEqual(actual, expected)

  @staticmethod
  def cp(car):
    return CarInterface.get_non_essential_params(car)

  def test_actual_cp_eligibility_and_stock_gates(self):
    self.assertTrue(eligible(self.cp(CAR.TOYOTA_COROLLA_TSS2)))
    self.assertTrue(eligible(self.cp(CAR.TOYOTA_SIENNA_4TH_GEN)))
    self.assertFalse(eligible(self.cp(CAR.TOYOTA_SIENNA)))  # Current stock-PCM 3G.
    self.assertFalse(eligible(self.cp(CAR.TOYOTA_CAMRY_TSS2)))
    cp = self.cp(CAR.TOYOTA_COROLLA_TSS2)
    cp.openpilotLongitudinalControl = False
    self.assertFalse(eligible(cp))
    cp.openpilotLongitudinalControl = True
    cp.dashcamOnly = True
    self.assertFalse(eligible(cp))
    self.assertFalse(eligible(NS(brand='toyota', carFingerprint=CAR.TOYOTA_COROLLA_TSS2)))

  def test_corolla_release_brake_bypass_and_reset(self):
    policy = ToyotaOutputPolicy(self.cp(CAR.TOYOTA_COROLLA_TSS2))
    self.assert_target(policy.target(1.0, 1.0, False, 0.0), 0.03225806451612903)
    self.assert_target(policy.target(1.0, 1.0, False, 0.0), 0.06347554630593132)
    self.assertEqual(policy.target(-1.0, 1.0, False, 0.0), -1.0)  # Hard braking bypass.
    self.assertEqual(policy.target(0.5, 1.0, True, -1.0), 0.5)  # Stop clears prior filter.
    self.assert_target(policy.target(1.0, 1.0, False, -0.5), -0.45161290322580644)
    policy.reset()
    self.assert_target(policy.target(1.0, 1.0, False, 0.0), 0.03225806451612903)

  def test_sienna_low_speed_comfort_bypass_departure_cap_and_reset(self):
    policy = ToyotaOutputPolicy(self.cp(CAR.TOYOTA_SIENNA_4TH_GEN))
    empty = ()
    self.assert_target(policy.target(1.0, 0.0, False, 0.0, leads=empty), 0.0196078431372549)
    self.assert_target(policy.target(1.0, 0.0, False, 0.0, leads=empty), 0.03883121876201461)
    departing = (Lead(True, 15.0, 0.0, 10.0, 0.0),)
    paced = (Lead(True, 15.0, 0.0, 2.1, 0.0),)
    policy.reset()
    self.assertEqual(policy.target(2.0, 2.0, False, 0.0, leads=paced), 2.0)  # Centered comfort lead bypasses low-speed filter.
    policy.reset()
    self.assertEqual(policy.target(2.0, 6.0, False, 0.0, leads=departing), 1.55)  # Departure cap after target shape.
    policy.reset()
    self.assertEqual(policy.target(-3.0, 4.0, False, 0.0, leads=departing), -3.0)  # Urgent brake bypass.
    self.assertEqual(policy.target(1.0, 4.0, True, 0.0, leads=departing), 1.0)
    self.assert_target(policy.target(1.0, 0.0, False, 0.0, leads=empty), 0.0196078431372549)

  def test_invalid_or_missing_inputs_reset_and_never_produce_a_target(self):
    sienna = ToyotaOutputPolicy(self.cp(CAR.TOYOTA_SIENNA_4TH_GEN))
    self.assertIsNone(sienna.target(1.0, 1.0, False, 0.0, leads=None))
    self.assertIsNone(sienna.target(float('nan'), 1.0, False, 0.0, leads=()))
    self.assert_target(sienna.target(0.5, -0.238205, False, 0.0, leads=()), 0.5 * 0.01 / 0.51)
    self.assertIsNone(sienna.target(1.0, 1.0, False, 0.0, leads=(Lead(True, float('inf'), 0.0, 0.0, 0.0),)))
    self.assertIsNone(sienna.target(1.0, 1.0, True, True, leads=()))
    self.assert_target(sienna.target(1.0, 0.0, False, 0.0, leads=()), 0.0196078431372549)

  def test_actual_radar_message_requires_fresh_same_drive_transport(self):
    event = messaging.new_message('radarState', valid=True)
    event.radarState.leadOne.present = True
    event.radarState.leadOne.dRel = 15.0
    event.radarState.leadOne.yRel = 0.25
    event.radarState.leadOne.vLead = 10.0
    event.radarState.leadOne.aLeadK = -0.5
    radar = messaging.log_from_bytes(event.to_bytes()).radarState
    leads = leads_from_radar(radar, message_ns=1_000_000_000, receipt_ns=1_001_000_000,
                             now_ns=1_002_000_000, drive_id=900_000_000, valid=True)
    self.assertIsNotNone(leads)
    assert leads is not None
    self.assertEqual(leads[0].distance_m, 15.0)
    self.assertFalse(leads[1].present)
    self.assertIsNone(leads_from_radar(radar, message_ns=1_000_000_000, receipt_ns=1_001_000_000,
                                       now_ns=1_002_000_000, drive_id=900_000_000, valid=False))
    self.assertIsNone(leads_from_radar(radar, message_ns=1_000_000_000, receipt_ns=1_001_000_000,
                                       now_ns=1_100_000_001, drive_id=900_000_000, valid=True))
    self.assertIsNone(leads_from_radar(radar, message_ns=1_000_000_000, receipt_ns=999_000_000,
                                       now_ns=1_002_000_000, drive_id=900_000_000, valid=True))
    self.assertIsNone(leads_from_radar(radar, message_ns=1_000_000_000, receipt_ns=1_001_000_000,
                                       now_ns=1_002_000_000, drive_id=1_000_000_000, valid=True))


if __name__ == '__main__':
  unittest.main()
