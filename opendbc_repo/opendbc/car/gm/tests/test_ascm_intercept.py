import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car import gen_empty_fingerprint
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.fingerprints import FINGERPRINTS, FW_VERSIONS
from opendbc.car.gm.values import ASCM_INTERCEPT_CAR, CAR, DBC, GMSafetyFlags, CarControllerParams
from opendbc.car.structs import CarParams


def params(car, *, sascm=False, accelerator=True, radar=False, alpha=False, release=False):
  fp = gen_empty_fingerprint()
  if sascm:
    fp[0][0x2ff] = 8
  if accelerator:
    fp[0][0xbe] = 6
  if radar:
    fp[1][0x460] = 8
  return CarInterface.get_params(car, fp, [], alpha, release, False)


class TestAscmIntercept(unittest.TestCase):
  def test_eight_manual_ids_have_stock_acc_default(self):
    self.assertEqual(len(ASCM_INTERCEPT_CAR), 8)
    for car in ASCM_INTERCEPT_CAR:
      with self.subTest(car=car):
        cp = params(car)
        self.assertEqual(cp.networkLocation, CarParams.NetworkLocation.fwdCamera)
        self.assertTrue(cp.pcmCruise)
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertFalse(cp.alphaLongitudinalAvailable)
        self.assertAlmostEqual(cp.minEnableSpeed, -1. if car == CAR.CADILLAC_ESCALADE_ESV_2019_ASCM else 5 / 3.6, places=6)
        self.assertTrue(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_INTERCEPT)
        self.assertFalse(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.HW_CAM_LONG)
        self.assertEqual(car.config.car_docs, [])
        self.assertNotIn(car, FINGERPRINTS)
        self.assertNotIn(car, FW_VERSIONS)

  def test_sascm_alpha_requires_source_opt_in_and_debug(self):
    for car in ASCM_INTERCEPT_CAR:
      for sascm, alpha, release in ((False, True, False), (True, False, False),
                                    (True, True, True), (True, True, False)):
        with self.subTest(car=car, sascm=sascm, alpha=alpha, release=release):
          cp = params(car, sascm=sascm, alpha=alpha, release=release)
          enabled = sascm and alpha and not release
          self.assertEqual(cp.openpilotLongitudinalControl, enabled)
          self.assertEqual(cp.pcmCruise, not enabled)
          self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.HW_CAM_LONG), enabled)

  def test_brake_source_and_radar_follow_observed_frames(self):
    for car in ASCM_INTERCEPT_CAR:
      for accelerator, radar in ((True, True), (False, False)):
        cp = params(car, accelerator=accelerator, radar=radar)
        self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_BRAKE_C9), not accelerator)
        self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_RADAR), radar)
        self.assertEqual(cp.radarUnavailable, not radar)

  def test_existing_gateway_and_bolt_configuration_unchanged(self):
    gateway = params(CAR.GMC_ACADIA)
    self.assertEqual(gateway.networkLocation, CarParams.NetworkLocation.gateway)
    self.assertTrue(gateway.openpilotLongitudinalControl)
    self.assertFalse(gateway.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_INTERCEPT)
    bolt = params(CAR.CHEVROLET_BOLT_EUV)
    self.assertFalse(bolt.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_INTERCEPT)

  def test_intercept_alpha_limits_match_ordinary_ascm_long(self):
    cp = params(CAR.CADILLAC_ESCALADE_ASCM, sascm=True, alpha=True)
    limits = CarControllerParams(cp)
    self.assertEqual((limits.MAX_GAS, limits.MAX_ACC_REGEN, limits.INACTIVE_REGEN), (2041., -650., -650.))

  def test_camera_parser_requires_status_but_aeb_is_optional(self):
    for car in ASCM_INTERCEPT_CAR:
      with self.subTest(car=car):
        cp = params(car)
        state = CarState(cp)
        parsers = state.get_can_parsers(cp)
        camera = parsers[Bus.cam]
        packer = CANPacker(DBC[car][Bus.pt])
        steer = packer.make_can_msg("ASCMLKASteeringCmd", 2, {})
        status = packer.make_can_msg("ASCMActiveCruiseControlStatus", 2, {"ACCCruiseState": 0})
        camera.update([(1_000_000_000, [steer, status])])
        self.assertTrue(camera.can_valid)
        out = state.update(parsers)
        self.assertFalse(out.stockAeb)
        self.assertFalse(out.cruiseState.nonAdaptive)
        aeb = packer.make_can_msg("AEBCmd", 2, {"AEBCmdActive": 1})
        camera.update([(1_100_000_000, [steer, status, aeb])])
        self.assertTrue(state.update(parsers).stockAeb)
        camera.update([(12_000_000_000, [steer, status])])
        self.assertTrue(camera.can_valid)
        for index in range(5):
          camera.update([(12_600_000_000 + index * 40_000_000, [steer])])
          _ = camera.can_valid
        self.assertFalse(camera.can_valid)

  def test_intercept_stock_status_never_infers_nonadaptive(self):
    cp = params(CAR.GMC_ACADIA_ASCM)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    camera = parsers[Bus.cam]
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    for index, cruise_state in enumerate((0, 1, 2, 3)):
      status = packer.make_can_msg("ASCMActiveCruiseControlStatus", 2, {"ACCCruiseState": cruise_state})
      camera.update([(1_000_000_000 + index * 40_000_000, [status])])
      self.assertFalse(state.update(parsers).cruiseState.nonAdaptive)
