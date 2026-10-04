"""BSM observation cannot impersonate or disqualify a GM control profile."""
import unittest

from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.can import CANPacker
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, DBC, GMFlags, control_flags
from opendbc.car.gm.aol import qualified_gm
from opendbc.car.gm.feature_capabilities import display_supported, longitudinal_supported




def params(identity, bsm):
  fingerprint = gen_empty_fingerprint()
  fingerprint[2][0x180] = 4
  if bsm:
    fingerprint[0][0x142] = 8
  return CarInterface.get_params(identity, fingerprint, [], False, False, False)


class TestBSMControlFlags(unittest.TestCase):
  def test_detected_bsm_retains_cc_authority_without_aliasing(self):
    for bsm in (False, True):
      with self.subTest(bsm=bsm):
        cp = params(CAR.CHEVROLET_BOLT_CC_2017, bsm)
        self.assertEqual(bool(cp.flags & GMFlags.HAS_BSM), bsm)
        self.assertEqual(control_flags(cp), int(GMFlags.CC_LONG))
        self.assertTrue(qualified_gm(cp))
        self.assertTrue(longitudinal_supported(cp))
        self.assertTrue(display_supported(cp))
        # Informational BSM alone cannot satisfy the required CC control bit.
        cp.flags = int(GMFlags.HAS_BSM) if bsm else 0
        self.assertFalse(qualified_gm(cp))
        self.assertFalse(longitudinal_supported(cp))
        self.assertFalse(display_supported(cp))

  def test_stock_observation_does_not_acquire_cc_authority(self):
    for bsm in (False, True):
      cp = params(CAR.CHEVROLET_BOLT_EUV, bsm)
      self.assertEqual(control_flags(cp), 0)
      self.assertTrue(qualified_gm(cp))
      self.assertTrue(display_supported(cp))
      self.assertFalse(longitudinal_supported(cp))
      cp.flags |= int(GMFlags.CC_LONG)
      self.assertFalse(qualified_gm(cp))
      self.assertFalse(display_supported(cp))
      self.assertFalse(longitudinal_supported(cp))

  def test_bsm_mask_does_not_hide_unexpected_control_flags_or_native_word(self):
    for identity in (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_EUV):
      for unexpected in (GMFlags.PEDAL_LONG, GMFlags.NO_CAMERA, GMFlags.NO_ACCELERATOR_POS_MSG, 32):
        for bsm in (False, True):
          with self.subTest(identity=identity, unexpected=unexpected, bsm=bsm):
            cp = params(identity, bsm)
            cp.flags |= int(unexpected)
            self.assertFalse(qualified_gm(cp))
            self.assertFalse(display_supported(cp))
            self.assertFalse(longitudinal_supported(cp))
      cp = params(identity, True)
      cp.safetyConfigs[0].safetyParam = 0
      self.assertFalse(qualified_gm(cp))
      self.assertFalse(display_supported(cp))
      self.assertFalse(longitudinal_supported(cp))

  def test_actual_interface_update_keeps_constructor_only_bsm_logic_out_of_state(self):
    from opendbc.car.gm.tests.test_bolt_cc import feed
    for bsm in (False, True):
      cp = params(CAR.CHEVROLET_BOLT_CC_2017, bsm)
      interface = CarInterface(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      state, messages = feed(interface, packer, 1_000_000_000)
      if bsm:
        # A detected sensor is a required parser source; include its real packet.
        messages.append(packer.make_can_msg('BCMBlindSpotMonitor', 0, {}))
        interface.update([(1_010_000_000, messages)])
        state = interface.update([(1_020_000_000, messages)])
      self.assertTrue(state.canValid)
      self.assertEqual(bool(cp.flags & GMFlags.HAS_BSM), bsm)
