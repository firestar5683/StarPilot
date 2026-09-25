import unittest

from opendbc.car.hyundai.canfd_stock_aol import qualified_long
from opendbc.car.hyundai.torque_ev_startup import candidate
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.starpilot.aol.tests.test_canfd_stock_profiles import params
from openpilot.starpilot.car.hyundai.aol import native_accepts_cp, policy_for


class TestCanfdLongProfiles(unittest.TestCase):
  def test_actual_factory_candidate_and_exact_final_marker(self):
    for identity in (CAR.HYUNDAI_IONIQ_5, CAR.HYUNDAI_KONA_EV_2ND_GEN):
      for alternate in (False, True):
        stock = params(identity, alternate)
        cp = candidate(stock, requested=True, is_release=False)
        self.assertIsNotNone(cp)
        assert cp is not None
        self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x95 if alternate else 0x15)
        self.assertTrue(qualified_long(cp))
        self.assertFalse(qualified_long(cp, marked_only=True))
        policy = policy_for(cp)
        self.assertEqual(policy.safety_param_addition, 0x800)
        self.assertEqual(policy.alternative_experience_addition, 32)
        cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
        cp.alternativeExperience |= policy.alternative_experience_addition
        self.assertTrue(qualified_long(cp, marked_only=True))
        model = int(cp.safetyConfigs[0].safetyModel.raw)
        self.assertTrue(native_accepts_cp(cp, model, 0x895 if alternate else 0x815))
        self.assertFalse(native_accepts_cp(cp, model, 0x815 if alternate else 0x895))
        self.assertIsNone(candidate(stock, requested=True, is_release=True))
        self.assertIsNone(candidate(stock, requested=False, is_release=False))
        self.assertFalse(qualified_long(stock))

  def test_identity_topology_axis_and_experience_negatives(self):
    cp = candidate(params(CAR.HYUNDAI_IONIQ_5), requested=True, is_release=False)
    assert cp is not None
    for field, value in (('carFingerprint', CAR.HYUNDAI_IONIQ_6), ('pcmCruise', True),
                         ('openpilotLongitudinalControl', False), ('passive', True),
                         ('dashcamOnly', True), ('notCar', True), ('alternativeExperience', 32)):
      bad = cp.as_reader().as_builder()
      setattr(bad, field, value)
      self.assertFalse(qualified_long(bad))
    for flag in (HyundaiFlags.CANFD_ALT_BUTTONS, HyundaiFlags.CANFD_CAMERA_SCC,
                 HyundaiFlags.HYBRID, HyundaiFlags.CANFD_ANGLE_STEERING):
      bad = cp.as_reader().as_builder()
      bad.flags = int(bad.flags) | int(flag)
      self.assertFalse(qualified_long(bad))
    for word in (0x11, 0x91, 0x815, 0x895, 0x8015, 0x8815, 0x1815):
      bad = cp.as_reader().as_builder()
      bad.safetyConfigs[0].safetyParam = word
      self.assertFalse(qualified_long(bad))
