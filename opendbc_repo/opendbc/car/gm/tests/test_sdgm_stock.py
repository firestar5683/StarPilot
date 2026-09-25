import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.fingerprints import FINGERPRINTS, FW_VERSIONS
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import (DBC, GMSafetyFlags, SDGM_STOCK_CAR, SDGM_CANCEL_PT_CAR)
from opendbc.car.structs import CarParams


def params(car, *, brake_c9=False, radar=False, alpha=False, release=False):
  fp = gen_empty_fingerprint()
  if not brake_c9:
    fp[0][0xBE] = 6
  if radar:
    fp[1][0x460] = 8
  return CarInterface.get_params(car, fp, [], alpha, release, False)


class TestSdgmStock(unittest.TestCase):
  def test_five_manual_ids_and_stock_only_modes(self):
    self.assertEqual(len(SDGM_STOCK_CAR), 5)
    for car in SDGM_STOCK_CAR:
      for brake_c9, radar, alpha, release in ((False, False, False, False), (True, True, True, False),
                                              (False, True, True, True)):
        with self.subTest(car=car, brake_c9=brake_c9, radar=radar, alpha=alpha, release=release):
          cp = params(car, brake_c9=brake_c9, radar=radar, alpha=alpha, release=release)
          flags = cp.safetyConfigs[0].safetyParam
          self.assertEqual(cp.networkLocation, CarParams.NetworkLocation.fwdCamera)
          self.assertTrue(cp.pcmCruise)
          self.assertFalse(cp.openpilotLongitudinalControl)
          self.assertFalse(cp.alphaLongitudinalAvailable)
          self.assertEqual(bool(flags & GMSafetyFlags.SDGM_CANCEL_PT), car in SDGM_CANCEL_PT_CAR)
          self.assertEqual(bool(flags & GMSafetyFlags.BRAKE_C9), brake_c9)
          self.assertTrue(flags & GMSafetyFlags.HW_CAM)
          self.assertTrue(flags & GMSafetyFlags.SDGM)
          self.assertFalse(flags & GMSafetyFlags.HW_CAM_LONG)
          self.assertEqual(cp.radarUnavailable, not radar)
          self.assertEqual(car.config.car_docs, [])
          self.assertNotIn(car, FINGERPRINTS)
          self.assertNotIn(car, FW_VERSIONS)

  def test_parser_camera_required_aeb_absent_and_brake_source(self):
    for car in SDGM_STOCK_CAR:
      for brake_c9 in (False, True):
        with self.subTest(car=car, brake_c9=brake_c9):
          cp = params(car, brake_c9=brake_c9)
          state = CarState(cp)
          parsers = state.get_can_parsers(cp)
          packer = CANPacker(DBC[car][Bus.pt])
          steer = packer.make_can_msg("ASCMLKASteeringCmd", 2, {})
          status = packer.make_can_msg("ASCMActiveCruiseControlStatus", 2, {"ACCCruiseState": 1})
          parsers[Bus.cam].update([(1_000_000_000, [steer, status])])
          self.assertTrue(parsers[Bus.cam].can_valid)
          out = state.update(parsers)
          self.assertFalse(out.stockAeb)
          self.assertTrue(out.cruiseState.nonAdaptive)
          brake = packer.make_can_msg("ECMEngineStatus" if brake_c9 else "ECMAcceleratorPos", 0,
                                      {"BrakePressed": 1} if brake_c9 else {"BrakePedalPos": 10})
          parsers[Bus.pt].update([(1_000_000_000, [brake])])
          self.assertTrue(state.update(parsers).brakePressed)
          for index in range(5):
            parsers[Bus.cam].update([(1_600_000_000 + index * 40_000_000, [steer])])
            _ = parsers[Bus.cam].can_valid
          self.assertFalse(parsers[Bus.cam].can_valid)

  def test_pt_required_subscription_and_optional_absent_be(self):
    for brake_c9 in (False, True):
      cp = params(next(iter(SDGM_STOCK_CAR)), brake_c9=brake_c9)
      parser = CarState.get_can_parsers(cp)[Bus.pt]
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      required = ("PSCMStatus", "ESPStatus", "EBCMWheelSpdFront", "EBCMWheelSpdRear",
                  "EBCMFrictionBrakeStatus", "PSCMSteeringAngle", "ECMPRDNL2", "AcceleratorPedal2",
                  "ECMEngineStatus", "BCMTurnSignals", "BCMDoorBeltStatus",
                  "BCMGeneralPlatformStatus", "ASCMSteeringButton")
      if not brake_c9:
        required += ("ECMAcceleratorPos",)
      frames = [packer.make_can_msg(name, 0, {}) for name in required]
      parser.update([(1_000_000_000, frames)])
      self.assertTrue(parser.can_valid)
      for index in range(6):
        parser.update([(1_600_000_000 + index * 40_000_000,
                        [frame for frame in frames if frame[0] != 0x1C4])])
        _ = parser.can_valid
      self.assertFalse(parser.can_valid)
