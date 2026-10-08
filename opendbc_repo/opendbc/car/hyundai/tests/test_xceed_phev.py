import unittest

from opendbc.can import CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.fingerprints import FW_VERSIONS
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import RADAR_START_ADDR, get_radar_can_parser
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags, HyundaiSafetyFlags
from opendbc.safety.tests import common
from opendbc.safety.tests.libsafety import libsafety_py


class TestXceedPhevPort(unittest.TestCase):
  @staticmethod
  def params(alpha_long=False, *, release=False):
    fingerprint = gen_empty_fingerprint()
    fingerprint[1][RADAR_START_ADDR] = 8
    return CarInterface.get_params(CAR.KIA_XCEED_PHEV, fingerprint, [], alpha_long, release, False)

  def test_saved_firmware_and_stock_legacy_hybrid_configuration(self):
    versions = FW_VERSIONS[CAR.KIA_XCEED_PHEV]
    self.assertEqual(len(versions), 3)
    observed = [structs.CarParams.CarFw(ecu=ecu, address=addr, subAddress=0,
                                         fwVersion=values[0], brand='hyundai')
                for (ecu, addr, _), values in versions.items()]
    exact, matches = match_fw_to_car(observed, '', allow_exact=True, allow_fuzzy=False, log=False)
    self.assertTrue(exact)
    self.assertEqual(matches, {CAR.KIA_XCEED_PHEV, CAR.KIA_CEED_PHEV})
    for alpha_long, release in ((False, False), (True, False), (False, True), (True, True)):
      cp = self.params(alpha_long, release=release)
      self.assertTrue(cp.flags & HyundaiFlags.LEGACY)
      self.assertTrue(cp.flags & HyundaiFlags.HYBRID)
      self.assertTrue(cp.flags & HyundaiFlags.MANDO_RADAR)
      self.assertEqual(cp.alphaLongitudinalAvailable, not release)
      self.assertFalse(cp.openpilotLongitudinalControl)
      self.assertTrue(cp.pcmCruise)
      self.assertFalse(cp.radarUnavailable)
      self.assertEqual(cp.safetyConfigs[-1].safetyModel, structs.CarParams.SafetyModel.hyundaiLegacy)
      self.assertTrue(cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.HYBRID_GAS)
      self.assertFalse(cp.safetyConfigs[-1].safetyParam & HyundaiSafetyFlags.LONG)
      self.assertEqual(DBC[CAR.KIA_XCEED_PHEV][Bus.radar], 'hyundai_kia_mando_front_radar_generated')
      self.assertEqual(get_radar_can_parser(cp).bus, 1)

  def test_actual_controller_and_native_safety_keep_scc_with_stock(self):
    cp = self.params()
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    state.update(parsers)
    control = structs.CarControl()
    control.enabled = True
    control.latActive = True
    control.longActive = False
    controller = CarController(DBC[CAR.KIA_XCEED_PHEV], cp)
    _, sends = controller.update(control.as_reader(), state, 1_000_000_000)
    self.assertIn(0x340, [addr for addr, _, _ in sends])
    self.assertNotIn(0x420, [addr for addr, _, _ in sends])
    self.assertNotIn(0x421, [addr for addr, _, _ in sends])

    safety = libsafety_py.libsafety
    safety.set_safety_hooks(int(cp.safetyConfigs[-1].safetyModel.raw), cp.safetyConfigs[-1].safetyParam)
    safety.init_tests()
    self.assertFalse(safety.safety_tx_hook(common.make_msg(0, 0x420, 8)))
    lkas = next(frame for frame in sends if frame[0] == 0x340)
    self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(lkas[0], lkas[2], lkas[1])))
    parser = CANParser(DBC[CAR.KIA_XCEED_PHEV][Bus.pt], [('LKAS11', 0)], 0)
    parser.update([(1_000_000_000, sends)])
    self.assertEqual(parser.vl['LKAS11']['CR_Lkas_StrToqReq'], 0)


if __name__ == '__main__':
  unittest.main()
