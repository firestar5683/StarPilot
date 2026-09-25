import unittest

from opendbc.can import CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.chrysler.interface import CarInterface
from opendbc.car.chrysler.values import CAR, CUSW_CARS, DBC, ChryslerFlags


def params(car, bus=None):
  fingerprint = gen_empty_fingerprint()
  if bus is not None:
    fingerprint[bus][0x4FF] = 8
  return CarInterface.get_params(car, fingerprint, [], False, False, False)


class TestSteeringSpeedBypass(unittest.TestCase):
  def test_blind_spot_detection_does_not_enable_speed_bypass(self):
    car = CAR.CHRYSLER_PACIFICA_2020
    baseline = params(car)
    for blind_spot in (False, True):
      for bypass in (False, True):
        for bus in (0, 1, 2):
          with self.subTest(blind_spot=blind_spot, bypass=bypass, bus=bus):
            fingerprint = gen_empty_fingerprint()
            if blind_spot:
              fingerprint[bus][0x2d0] = 8
            if bypass:
              fingerprint[bus][0x4ff] = 8
            cp = CarInterface.get_params(car, fingerprint, [], False, False, False)
            self.assertEqual(bool(cp.flags & ChryslerFlags.HAS_BSM), blind_spot and bus == 0)
            self.assertEqual(bool(cp.flags & ChryslerFlags.STEERING_SPEED_BYPASS), bypass and bus == 0)
            self.assertEqual(cp.minSteerSpeed, 0 if bypass and bus == 0 else baseline.minSteerSpeed)
            self.assertEqual([(str(c.safetyModel), c.safetyParam) for c in cp.safetyConfigs],
                             [(str(c.safetyModel), c.safetyParam) for c in baseline.safetyConfigs])

  def test_hardware_is_scoped_to_original_platforms_and_bus(self):
    for car in CAR:
      baseline = params(car)
      for bus in (0, 1, 2):
        with self.subTest(car=car, bus=bus):
          cp = params(car, bus)
          supported = bus == 0 and car not in CUSW_CARS
          self.assertEqual(bool(cp.flags & ChryslerFlags.STEERING_SPEED_BYPASS), supported)
          self.assertEqual(cp.minSteerSpeed, 0 if supported else baseline.minSteerSpeed)
          self.assertEqual([(str(c.safetyModel), c.safetyParam) for c in cp.safetyConfigs],
                           [(str(c.safetyModel), c.safetyParam) for c in baseline.safetyConfigs])
          self.assertEqual(cp.dashcamOnly, baseline.dashcamOnly)
          self.assertEqual(cp.pcmCruise, baseline.pcmCruise)
          self.assertFalse(cp.openpilotLongitudinalControl)

  def test_standstill_engagement_and_reentry_keep_eps_cooldown(self):
    for car in set(CAR) - CUSW_CARS:
      with self.subTest(car=car):
        ci = CarInterface(params(car, 0))
        ci.update([])
        ci.CS.out.vEgo = 0
        command = structs.CarControl()
        command.actuators.torque = 0.1
        parser = CANParser(DBC[car][Bus.pt], [('LKAS_COMMAND', 0)], 0)
        for frame, active, expected in ((200, True, False), (202, True, True), (204, True, True),
                                         (206, False, False), (208, True, False),
                                         (406, True, False), (408, True, True)):
          ci.CC.frame = frame
          command.latActive = active
          _, sends = ci.CC.update(command.as_reader(), ci.CS, frame * 10_000_000)
          parser.update((frame * 10_000_000, sends))
          self.assertEqual(ci.CC.lkas_control_bit_prev, expected)
          if not expected:
            self.assertEqual(parser.vl['LKAS_COMMAND']['STEERING_TORQUE'], 0)

  def test_without_hardware_standstill_does_not_enable_steering(self):
    for car in set(CAR) - CUSW_CARS:
      with self.subTest(car=car):
        ci = CarInterface(params(car))
        ci.update([])
        ci.CC.frame = 202
        command = structs.CarControl()
        command.latActive = True
        command.actuators.torque = 0.1
        actuators, _ = ci.CC.update(command.as_reader(), ci.CS, 2_020_000_000)
        self.assertFalse(ci.CC.lkas_control_bit_prev)
        self.assertEqual(actuators.torqueOutputCan, 0)
