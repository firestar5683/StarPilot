import math
import unittest

from opendbc.car import Bus, structs
from opendbc.car.hyundai.fingerprints import FW_VERSIONS
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.interfaces import get_torque_params


class TestIoniq5PEMetadata(unittest.TestCase):
  def test_exact_platform_specs_and_angle_flags(self):
    config = CAR.HYUNDAI_IONIQ_5_PE.config
    self.assertEqual(config.specs, CAR.HYUNDAI_IONIQ_5.config.specs)
    self.assertEqual((config.specs.mass, config.specs.wheelbase, config.specs.steerRatio, config.specs.tireStiffnessFactor),
                     (1948, 2.97, 14.26, 0.65))
    self.assertEqual(config.flags, HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING | HyundaiFlags.CCNC)
    self.assertEqual(config.dbc_dict[Bus.pt], "hyundai_canfd_generated")
    self.assertEqual(config.dbc_dict[Bus.radar], "hyundai_mrr35_radar_generated")
    self.assertNotEqual(config.specs, CAR.HYUNDAI_IONIQ_5_N.config.specs)

  def test_original_angle_metadata_allows_interface_constructor(self):
    tune = get_torque_params()[CAR.HYUNDAI_IONIQ_5_PE]
    self.assertEqual(tune["MAX_LAT_ACCEL_MEASURED"], 2.5)
    self.assertTrue(math.isnan(tune["LAT_ACCEL_FACTOR"]))
    self.assertTrue(math.isnan(tune["FRICTION"]))
    cp = CarInterface.get_std_params(CAR.HYUNDAI_IONIQ_5_PE)
    self.assertEqual(cp.maxLateralAccel, 2.5)

  def test_exact_firmware_entries_remain_distinct(self):
    versions = FW_VERSIONS[CAR.HYUNDAI_IONIQ_5_PE]
    radar = versions[(structs.CarParams.Ecu.fwdRadar, 0x7d0, None)]
    camera = versions[(structs.CarParams.Ecu.fwdCamera, 0x7c4, None)]
    self.assertEqual(len(versions), 2)
    self.assertEqual(len(radar), 2)
    self.assertEqual(len(camera), 4)
    self.assertTrue(all(version.startswith(b"\xf1\x00NE__ RDR") for version in radar))
    self.assertTrue(all(version.startswith(b"\xf1\x00NE  MFC") for version in camera))
    old_camera = FW_VERSIONS[CAR.HYUNDAI_IONIQ_5][(structs.CarParams.Ecu.fwdCamera, 0x7c4, None)]
    self.assertFalse(set(camera) & set(old_camera))


if __name__ == "__main__":
  unittest.main()
