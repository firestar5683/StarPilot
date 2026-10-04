import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.fingerprints import FINGERPRINTS, FW_VERSIONS
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, CC_GATEWAY_STOCK_CAR, ORDINARY_CC_CAR, DBC, GMSafetyFlags
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.structs import CarParams


def params(car, *, alpha=False, release=False):
  return CarInterface.get_params(car, gen_empty_fingerprint(), [], alpha, release, False)


def pt_frames(packer, *, cruise=True, main=True, brake=False, gas=False, counter=0, acc_cruise=0):
  values = {
    "PSCMStatus": {}, "ESPStatus": {},
    "EBCMWheelSpdFront": {"FLWheelSpd": 60, "FRWheelSpd": 60},
    "EBCMWheelSpdRear": {"RLWheelSpd": 60, "RRWheelSpd": 60},
    "EBCMFrictionBrakeStatus": {}, "PSCMSteeringAngle": {},
    "ECMPRDNL2": {"PRNDL2": 4},
    "AcceleratorPedal2": {"CruiseState": acc_cruise, "AcceleratorPedal2": 30 if gas else 0},
    "ECMEngineStatus": {"CruiseMainOn": int(main)},
    "BCMTurnSignals": {}, "BCMDoorBeltStatus": {"LeftSeatBelt": 1},
    "BCMGeneralPlatformStatus": {},
    "ASCMSteeringButton": {"ACCButtons": 1, "RollingCounter": counter},
    "ECMAcceleratorPos": {"BrakePedalPos": 10 if brake else 0},
    "ECMCruiseControl": {"CruiseActive": int(cruise), "CruiseSetSpeed": 80},
  }
  return [packer.make_can_msg(name, 0, val) for name, val in values.items()]


class TestCcGatewayStock(unittest.TestCase):
  def test_production_firmware_matcher_never_infers_manual_identity(self):
    # GM has no production firmware literals. Vary complete/partial/mixed
    # observations: no observation can identify a no-ACC installation.
    gm_fw = [CarParams.CarFw(ecu=CarParams.Ecu.engine, address=0x7e0,
                             fwVersion=b"GM-observed-engine", brand="gm"),
             CarParams.CarFw(ecu=CarParams.Ecu.eps, address=0x7e8,
                             fwVersion=b"GM-observed-eps", brand="gm")]
    sibling = CarParams.CarFw(ecu=CarParams.Ecu.fwdCamera, address=0x24b,
                              fwVersion=b"ACC-sibling-camera", brand="gm")
    for observed in (gm_fw, gm_fw[:1], gm_fw[1:], gm_fw + [sibling], [sibling]):
      _, matches = match_fw_to_car(observed, "", log=False)
      self.assertFalse(CC_GATEWAY_STOCK_CAR & matches)

  def test_manual_identity_and_stock_ownership(self):
    self.assertEqual(len(CC_GATEWAY_STOCK_CAR), 9)
    for car in CC_GATEWAY_STOCK_CAR:
      self.assertEqual(car.config.car_docs, [])
      automatic = {CAR.CADILLAC_CT6_CC, CAR.CADILLAC_XT5_CC, CAR.CHEVROLET_EQUINOX_CC,
                   CAR.CHEVROLET_MALIBU_CC, CAR.CHEVROLET_SUBURBAN_CC, CAR.CHEVROLET_TRAILBLAZER_CC}
      self.assertEqual(car in FINGERPRINTS, car in automatic)
      self.assertNotIn(car, FW_VERSIONS)
      for alpha, release in ((False, False), (True, False), (True, True)):
        with self.subTest(car=car, alpha=alpha, release=release):
          cp = params(car, alpha=alpha, release=release)
          self.assertEqual(cp.networkLocation, CarParams.NetworkLocation.gateway)
          self.assertEqual(cp.pcmCruise, car not in ORDINARY_CC_CAR)
          self.assertEqual(cp.openpilotLongitudinalControl, car in ORDINARY_CC_CAR)
          self.assertFalse(cp.alphaLongitudinalAvailable)
          self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC160 if car in ORDINARY_CC_CAR else GMSafetyFlags.NO_ACC)
          self.assertEqual(cp.dashcamOnly, car not in ORDINARY_CC_CAR)

  def test_real_pt_parser_state_and_required_messages(self):
    for car in CC_GATEWAY_STOCK_CAR:
      with self.subTest(car=car):
        cp = params(car)
        state = CarState(cp)
        parsers = state.get_can_parsers(cp)
        packer = CANPacker(DBC[car][Bus.pt])
        frames = pt_frames(packer)
        parsers[Bus.pt].update([(1_000_000_000, frames)])
        self.assertTrue(parsers[Bus.pt].can_valid)
        out = state.update(parsers)
        self.assertTrue(out.cruiseState.available)
        self.assertTrue(out.cruiseState.enabled)
        self.assertEqual(out.cruiseState.nonAdaptive, car not in ORDINARY_CC_CAR)
        self.assertAlmostEqual(out.cruiseState.speed, 80 / 3.6, places=5)
        self.assertGreater(out.vEgo, 0)
        self.assertFalse(out.brakePressed)
        for missing in (0x3D1, 0x1E1, 0xBE, 0x1C4, 0x184, 0x34A):
          parser = CarState.get_can_parsers(cp)[Bus.pt]
          parser.update([(1_000_000_000, [f for f in frames if f[0] != missing])])
          self.assertFalse(parser.can_valid, hex(missing))

  def test_stock_status_brake_and_main_are_independent_of_acc(self):
    cp = params(next(iter(CC_GATEWAY_STOCK_CAR)))
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    for cruise, main, brake, gas in ((False, True, False, False), (True, False, False, False),
                                     (True, True, True, False), (True, True, False, True)):
      state = CarState(cp)
      parsers = state.get_can_parsers(cp)
      parsers[Bus.pt].update([(1_000_000_000, pt_frames(packer, cruise=cruise, main=main, brake=brake, gas=gas))])
      out = state.update(parsers)
      self.assertEqual(out.cruiseState.enabled, cruise)
      self.assertEqual(out.cruiseState.available, main)
      self.assertEqual(out.brakePressed, brake)
      self.assertEqual(out.gasPressed, gas)

  def test_stock_cruise_parser_stales_without_required_pt_source(self):
    cp = params(next(iter(CC_GATEWAY_STOCK_CAR)))
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    parser = CarState.get_can_parsers(cp)[Bus.pt]
    frames = pt_frames(packer)
    parser.update([(1_000_000_000, frames)])
    self.assertTrue(parser.can_valid)
    for index in range(20):
      parser.update([(1_600_000_000 + index * 100_000_000,
                      [frame for frame in frames if frame[0] != 0x3D1])])
      _ = parser.can_valid
    self.assertFalse(parser.can_valid)


if __name__ == "__main__":
  unittest.main()
