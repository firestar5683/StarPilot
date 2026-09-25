"""Shared stock EV authority stays bound to the factory topology and word."""
import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.hyundai.canfd_stock_aol import STOCK_EV_CARS, qualified
from openpilot.starpilot.aol.intent import AolSettings, AOL_TOGGLE
from openpilot.starpilot.car.hyundai.aol import create_intent, native_accepts_cp, policy_for


def params(identity, alternate=False, release=False):
  fp = gen_empty_fingerprint()
  fp[2][0x110 if alternate else 0x50] = 32 if alternate else 16
  fp[1].update({0x1cf: 8, 0x130: 32, 0x35: 32, 0x175: 24, 0xa0: 24, 0xea: 24, 0x1a0: 32})
  return CarInterface.get_params(identity, fp, [], False, release, False)


class TestCanfdStockProfiles(unittest.TestCase):
  def test_actual_factory_words_and_exact_native_binding(self):
    for identity in STOCK_EV_CARS:
      for alternate in (False, True):
        for release in (False, True):
          cp = params(identity, alternate, release)
          self.assertTrue(qualified(cp))
          self.assertTrue(cp.pcmCruise)
          self.assertFalse(cp.openpilotLongitudinalControl)
          expected = 0x91 if alternate else 0x11
          self.assertEqual(cp.safetyConfigs[0].safetyParam, expected)
          policy = policy_for(cp)
          self.assertTrue(policy.explicit_latch)
          self.assertEqual(policy.safety_param_addition, 0x800)
          cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
          self.assertTrue(qualified(cp, marked_only=True))
          model = int(cp.safetyConfigs[0].safetyModel.raw)
          self.assertTrue(native_accepts_cp(cp, model, expected | 0x800))
          self.assertFalse(native_accepts_cp(cp, model, (expected | 0x800) ^ 0x80))

  def test_unsupported_flags_words_experience_and_identity_fail_closed(self):
    cp = params(CAR.KIA_EV6)
    for flag in (HyundaiFlags.HYBRID, HyundaiFlags.CANFD_ANGLE_STEERING,
                 HyundaiFlags.CANFD_ALT_BUTTONS, HyundaiFlags.CANFD_CAMERA_SCC):
      bad = cp.as_reader().as_builder()
      bad.flags = int(bad.flags) | int(flag)
      self.assertFalse(qualified(bad))
    for field, value in (('alternativeExperience', 32), ('openpilotLongitudinalControl', True),
                         ('passive', True), ('dashcamOnly', True), ('notCar', True), ('pcmCruise', False)):
      bad = cp.as_reader().as_builder()
      setattr(bad, field, value)
      self.assertFalse(qualified(bad))
    for word in (0x15, 0x895, 0x1811, 0x811 | 0x4000):
      bad = cp.as_reader().as_builder()
      bad.safetyConfigs[0].safetyParam = word
      self.assertFalse(qualified(bad))
    bad = cp.as_reader().as_builder()
    bad.carFingerprint = CAR.HYUNDAI_IONIQ_6
    self.assertFalse(qualified(bad))
    bad = cp.as_reader().as_builder()
    bad.safetyConfigs = [structs.CarParams.SafetyConfig(safetyModel='noOutput'), cp.safetyConfigs[0]]
    self.assertFalse(qualified(bad))

  def test_physical_intent_neutral_press_cancel_and_health(self):
    for identity in STOCK_EV_CARS:
      cp = params(identity)
      intent = create_intent(cp, AolSettings(True, 0., AOL_TOGGLE, AOL_TOGGLE, (0, 0, 0), (0, 0, 0)))
      cs = structs.CarState(canValid=True, gearShifter='drive')
      cs.cruiseState.available = True
      intent.update(cs, now_ns=1, fault_active=False)
      self.assertFalse(intent.allowed_latch)
      cs.buttonEvents = [structs.CarState.ButtonEvent(type='mainCruise', pressed=True)]
      intent.update(cs, now_ns=2, fault_active=False)
      self.assertTrue(intent.allowed_latch)
      cs.buttonEvents = [structs.CarState.ButtonEvent(type='cancel', pressed=True)]
      intent.update(cs, now_ns=3, fault_active=False)
      self.assertFalse(intent.allowed_latch)
      cs.canValid = False
      intent.update(cs, now_ns=4, fault_active=False)
      self.assertFalse(intent.output(cs)[0])
