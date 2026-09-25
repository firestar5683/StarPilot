import unittest

from opendbc.car import Bus
from opendbc.can.dbc import DBC as CANDBC
from opendbc.car.honda.fingerprints import FW_VERSIONS
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, DBC, HondaFlags, HondaSafetyFlags, STEER_THRESHOLD
from opendbc.car.structs import CarParams


NIDEC_SIX = (
  CAR.HONDA_CRV_SA, CAR.HONDA_CLARITY, CAR.HONDA_ACCORD_9G,
  CAR.ACURA_MDX_3G, CAR.ACURA_MDX_3G_MMR, CAR.ACURA_TLX_1G,
)


class TestHondaNidecSix(unittest.TestCase):
  def test_identity_and_safety_topology(self):
    for car in NIDEC_SIX:
      with self.subTest(car=car):
        cp = CarInterface.get_params(car, {0: {}, 1: {}, 2: {}}, [], False, False, False)
        self.assertEqual(cp.safetyConfigs[0].safetyModel, CarParams.SafetyModel.hondaNidec)
        self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & HondaSafetyFlags.NIDEC_ALT), car != CAR.HONDA_CLARITY)
        self.assertEqual(bool(cp.flags & HondaFlags.HAS_ALL_DOOR_STATES), car not in (CAR.ACURA_MDX_3G, CAR.ACURA_MDX_3G_MMR))
        self.assertTrue(cp.openpilotLongitudinalControl)
        self.assertTrue(cp.pcmCruise)
        self.assertEqual(DBC[car][Bus.radar], "acura_ilx_2016_nidec")
        self.assertEqual(cp.autoResumeSng, car == CAR.HONDA_CLARITY)
        self.assertEqual(STEER_THRESHOLD.get(car, 1200), 30 if car in (CAR.HONDA_ACCORD_9G, CAR.ACURA_MDX_3G,
                                                                         CAR.ACURA_MDX_3G_MMR, CAR.ACURA_TLX_1G) else 1200)

  def test_only_validated_clarity_has_firmware_discovery(self):
    self.assertEqual(set(NIDEC_SIX) & set(FW_VERSIONS), {CAR.HONDA_CLARITY})
    self.assertEqual(len(FW_VERSIONS[CAR.HONDA_CLARITY]), 6)

  def test_named_extended_dbc_control_contract(self):
    common = {
      "STEERING_CONTROL": (0xE4, 5),
      "SCM_BUTTONS": (0x1A6, 8),
      "SCM_FEEDBACK": (0x294, 8),
      "BRAKE_COMMAND": (0x1FA, 8),
      "ACC_HUD": (0x30C, 8),
      "LKAS_HUD": (0x33D, 5),
      "GEARBOX_CVT": (0x191, 8),
    }
    for car, gearbox in ((CAR.HONDA_ACCORD_9G, (0x188, 6)),
                         (CAR.ACURA_MDX_3G, (0x1A3, 8)),
                         (CAR.ACURA_TLX_1G, (0x1A3, 8))):
      with self.subTest(car=car):
        dbc = CANDBC(DBC[car][Bus.pt])
        for name, (address, size) in (common | {"GEARBOX_AUTO": gearbox}).items():
          self.assertEqual((dbc.name_to_msg[name].address, dbc.name_to_msg[name].size), (address, size))
        steer = dbc.name_to_msg["STEERING_CONTROL"].sigs
        self.assertEqual((steer["STEER_TORQUE"].start_bit, steer["STEER_TORQUE"].size), (7, 16))
        self.assertEqual((steer["STEER_TORQUE_REQUEST"].start_bit, steer["STEER_TORQUE_REQUEST"].size), (23, 1))
        self.assertEqual(dbc.name_to_msg["SCM_BUTTONS"].sigs["MAIN_ON"].start_bit, 47)
