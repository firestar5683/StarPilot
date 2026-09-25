import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm.gmcan import create_friction_brake_command
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_bolt_pedal import params
from opendbc.car.gm.values import CAR, DBC, PEDAL_BOLT_CAR


class TestBoltAccPedalParams(unittest.TestCase):
  def test_stop_target_and_delay_follow_final_control_owner(self):
    for candidate in PEDAL_BOLT_CAR:
      for alpha in (False, True):
        for setting in (False, True):
          for observed in (False, True):
            with self.subTest(candidate=candidate, alpha=alpha, setting=setting, observed=observed):
              cp = params(candidate, setting, observed, alpha_long=alpha)
              self.assertAlmostEqual(cp.stopAccel, -0.25)
              expected_delay = 0.6 if setting and observed else 1.0
              self.assertAlmostEqual(cp.longitudinalActuatorDelay, expected_delay)
    for candidate in (CAR.CHEVROLET_BOLT_EUV, CAR.CHEVROLET_BOLT_ACC_2022_2023):
      for alpha in (False, True):
        with self.subTest(candidate=candidate, alpha=alpha):
          cp = params(candidate, True, True, alpha_long=alpha)
          expected_stop = -0.25 if candidate == CAR.CHEVROLET_BOLT_ACC_2022_2023 or alpha else -2.0
          self.assertAlmostEqual(cp.stopAccel, expected_stop)
          self.assertAlmostEqual(cp.longitudinalActuatorDelay, 0.5)

  def test_final_stop_target_for_all_bolt_cc_camera_profiles(self):
    for candidate in (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021,
                      CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL):
      for alpha in (False, True):
        for camera in (False, True):
          for setting in (False, True):
            for observed in (False, True):
              with self.subTest(candidate=candidate, alpha=alpha, camera=camera, setting=setting, observed=observed):
                cp = params(candidate, setting, observed, alpha_long=alpha, camera=camera)
                self.assertEqual(cp.stopAccel, -0.25)
                self.assertAlmostEqual(cp.longitudinalActuatorDelay, 0.6 if setting and observed else 1.0)
                self.assertTrue(cp.openpilotLongitudinalControl)

  def test_friction_braking_and_speed_shaped_launch_limits(self):
    for alpha in (False, True):
      cp = params(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, True, True, alpha_long=alpha)
      for speed, maximum in ((0., .54), (.75, .64), (1.5, .74), (4., 1.03), (8., 1.46), (15., 2.), (40., 2.)):
        with self.subTest(alpha=alpha, speed=speed):
          minimum, actual_maximum = CarInterface.get_pid_accel_limits(cp, speed, 30.)
          self.assertEqual(minimum, -4.)
          self.assertAlmostEqual(actual_maximum, maximum)

  def test_non_acc_pedal_keeps_regen_only_limits(self):
    cp = params(CAR.CHEVROLET_BOLT_CC_2022_2023, True, True)
    for speed, minimum, maximum in ((0., -.93, .54), (1.5, -1.28, .74), (4., -1.98, 1.03),
                                    (8., -2.58, 1.46), (15., -2.86, 2.), (30., -2.95, 2.)):
      self.assertEqual(CarInterface.get_pid_accel_limits(cp, speed, 30.), (minimum, maximum))

  def test_friction_payload_modes_counter_and_checksum(self):
    cp = params(CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL, True, True)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.chassis])
    for counter in range(4):
      for brake, enabled, full_stop, mode in ((0, False, False, 1), (0, True, False, 9),
                                             (100, True, False, 10), (400, True, True, 13)):
        with self.subTest(counter=counter, brake=brake, enabled=enabled, full_stop=full_stop):
          message = create_friction_brake_command(packer, 0, brake, counter, enabled, False, full_stop, cp)
          encoded = (-brake) & 0xfff
          checksum = (-(mode << 12) - encoded - counter) & 0xffff
          expected = bytes(((mode << 4) | (encoded >> 8), encoded & 0xff,
                            checksum >> 8, checksum & 0xff, counter))
          self.assertEqual(message, (0x315, expected, 0))


if __name__ == "__main__":
  unittest.main()
