import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.ford.interface import CarInterface
from opendbc.car.ford.values import CAR, FordSafetyFlags


def fingerprint(offset=0, secoc=False):
  fp = gen_empty_fingerprint()
  fp[offset][0x5A] = 8
  fp[offset + 2][0x3D6] = 16 if secoc else 8
  fp[offset + 2][0x186] = 16 if secoc else 8
  return fp


class TestMachEProfile(unittest.TestCase):
  def test_actual_params_stock_debug_long_and_release_stock(self):
    for alpha, release, word in ((False, False, 18), (True, False, 19), (False, True, 18), (True, True, 18)):
      with self.subTest(alpha=alpha, release=release):
        cp = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, fingerprint(), [], alpha, release, False)
        self.assertEqual(cp.safetyConfigs[-1].safetyParam, word)
        self.assertEqual(cp.openpilotLongitudinalControl, word == 19)
        self.assertEqual(cp.alternativeExperience, 0)
        if release:
          self.assertFalse(cp.alphaLongitudinalAvailable)

  def test_secoc_unrelated_flags_and_ae_do_not_select_extension(self):
    cp = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, fingerprint(secoc=True), [], False, False, False)
    self.assertTrue(cp.dashcamOnly)
    self.assertFalse(cp.safetyConfigs[-1].safetyParam & FordSafetyFlags.MACH_E_EXTENDED)
    for added_flag, ae in ((4, 0), (8, 0), (16, 0), (0, 32)):
      with self.subTest(added_flag=added_flag, ae=ae):
        cp = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, fingerprint(), [], False, False, False)
        cp.flags |= added_flag
        cp.alternativeExperience = ae
        cp = CarInterface._get_params(cp, CAR.FORD_MUSTANG_MACH_E_MK1, fingerprint(), [], False, False, False)
        self.assertFalse(cp.safetyConfigs[-1].safetyParam & FordSafetyFlags.MACH_E_EXTENDED)

  def test_sibling_canfd_keeps_existing_profiles(self):
    for candidate in (CAR.FORD_F_150_MK14, CAR.FORD_ESCAPE_MK4_5, CAR.FORD_F_150_LIGHTNING_MK1):
      for alpha, word in ((False, 2), (True, 3)):
        with self.subTest(candidate=candidate, alpha=alpha):
          cp = CarInterface.get_params(candidate, fingerprint(), [], alpha, False, False)
          self.assertEqual(cp.safetyConfigs[-1].safetyParam, word)

  def test_bus_offset_keeps_no_output_first(self):
    cp = CarInterface.get_params(CAR.FORD_MUSTANG_MACH_E_MK1, fingerprint(offset=4), [], False, False, False)
    self.assertEqual(len(cp.safetyConfigs), 2)
    self.assertEqual(cp.safetyConfigs[0].safetyModel, structs.CarParams.SafetyModel.noOutput)
    self.assertEqual(cp.safetyConfigs[0].safetyParam, 0)
    self.assertEqual(cp.safetyConfigs[1].safetyParam, 18)
