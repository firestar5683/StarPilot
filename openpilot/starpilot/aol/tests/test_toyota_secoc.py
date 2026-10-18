"""Always On Lateral on the SecOC Sienna (TOYOTA_SIENNA_4TH_GEN, safety param 2121)."""
import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR, ToyotaFlags
from openpilot.starpilot.aol.vehicle import policy_for
from openpilot.starpilot.car.toyota.aol import AOL_WORDS, native_accepts_cp, native_profile_supported, qualified
from openpilot.starpilot.longitudinal.toyota_output_policy import production_enabled

TOYOTA = int(structs.CarParams.SafetyModel.toyota)


def sienna(key=True):
  fp = gen_empty_fingerprint()
  fp[0][0x3F6] = 8   # BSM
  cp = CarInterface.get_params(CAR.TOYOTA_SIENNA_4TH_GEN, fp, [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.hybrid)],
                               False, False, False)
  cp.secOcKeyAvailable = key     # card.py sets this once the stored key decodes, before the AOL policy is read
  return cp


class TestSiennaSecocAol(unittest.TestCase):
  def test_factory_params_match_the_logged_car(self):
    cp = sienna()
    self.assertEqual(int(cp.flags), 3099)
    self.assertEqual([(c.safetyModel, c.safetyParam) for c in cp.safetyConfigs],
                     [(structs.CarParams.SafetyModel.toyota, 2121)])
    self.assertTrue(cp.openpilotLongitudinalControl and cp.secOcRequired and cp.pcmCruise)

  def test_admitted_and_marked_like_the_other_toyotas(self):
    cp = sienna()
    self.assertTrue(qualified(cp))
    self.assertFalse(qualified(cp, marked_only=True))
    policy = policy_for(cp)
    self.assertTrue(policy.settings_supported and policy.full_axis_runtime_required)
    self.assertEqual(policy.alternative_experience_addition, 32)
    cp.alternativeExperience |= policy.alternative_experience_addition
    self.assertTrue(qualified(cp, marked_only=True))
    self.assertTrue(native_accepts_cp(cp, TOYOTA, 2121))
    self.assertIn(2121, AOL_WORDS)
    self.assertTrue(native_profile_supported(TOYOTA, 2121))

  def test_secoc_longitudinal_output_stays_on_with_aol(self):
    cp = sienna()
    self.assertTrue(production_enabled(cp))
    cp.alternativeExperience = 32
    self.assertTrue(production_enabled(cp))
    cp.alternativeExperience = 160
    self.assertFalse(production_enabled(cp))

  def test_everything_else_is_refused(self):
    mutations = {
      'no key': lambda cp: setattr(cp, 'secOcKeyAvailable', False),
      'not secoc required': lambda cp: setattr(cp, 'secOcRequired', False),
      'stock long': lambda cp: setattr(cp, 'openpilotLongitudinalControl', False),
      'no pcm cruise': lambda cp: setattr(cp, 'pcmCruise', False),
      'passive': lambda cp: setattr(cp, 'passive', True),
      'dashcam': lambda cp: setattr(cp, 'dashcamOnly', True),
      'angle': lambda cp: setattr(cp, 'steerControlType', structs.CarParams.SteerControlType.angle),
      'word 73': lambda cp: setattr(cp.safetyConfigs[0], 'safetyParam', 73),
      'word 2120': lambda cp: setattr(cp.safetyConfigs[0], 'safetyParam', 2120),
      'no output': lambda cp: setattr(cp.safetyConfigs[0], 'safetyModel', structs.CarParams.SafetyModel.noOutput),
      'no secoc flag': lambda cp: setattr(cp, 'flags', int(cp.flags) & ~int(ToyotaFlags.SECOC)),
      'extra flag': lambda cp: setattr(cp, 'flags', int(cp.flags) | int(ToyotaFlags.AUTO_BRAKE_HOLD)),
      'hold experience': lambda cp: setattr(cp, 'alternativeExperience', 160),
      'other car': lambda cp: setattr(cp, 'carFingerprint', CAR.TOYOTA_RAV4_TSS2),
    }
    for name, mutate in mutations.items():
      with self.subTest(name):
        cp = sienna()
        mutate(cp)
        self.assertFalse(qualified(cp), name)
        self.assertFalse(policy_for(cp).settings_supported, name)
    self.assertFalse(qualified(sienna(key=False)))


if __name__ == '__main__':
  unittest.main()
