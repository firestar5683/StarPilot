import unittest

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.nissan.interface import CarInterface
from opendbc.car.nissan.values import CAR, DBC, NissanSafetyFlags


def interface(car, alpha=False, release=False):
  cp = CarInterface.get_params(car, gen_empty_fingerprint(), [], alpha, release, False)
  return CarInterface(cp)


class TestNissanStockControl(unittest.TestCase):
  def test_stock_cruise_ownership_in_both_alpha_modes(self):
    for car in CAR:
      for alpha in (False, True):
        for release in (False, True):
          with self.subTest(car=car, alpha=alpha, release=release):
            cp = interface(car, alpha, release).CP
            self.assertTrue(cp.pcmCruise)
            self.assertFalse(cp.alphaLongitudinalAvailable)
            self.assertFalse(cp.openpilotLongitudinalControl)
            self.assertFalse(cp.dashcamOnly)
            self.assertEqual(cp.steerControlType, structs.CarParams.SteerControlType.angle)
            self.assertEqual(cp.safetyConfigs[0].safetyModel, structs.CarParams.SafetyModel.nissan)
            expected = NissanSafetyFlags.ALT_EPS_BUS if car == CAR.NISSAN_ALTIMA else 0
            self.assertEqual(cp.safetyConfigs[0].safetyParam, expected)

  def test_eps_angle_and_fault_follow_eps_bus(self):
    for car in CAR:
      with self.subTest(car=car):
        ci = interface(car)
        ci.update([])
        packer = CANPacker(DBC[car][Bus.pt])
        pt_bus = 1 if car == CAR.NISSAN_ALTIMA else 0
        for frame, (angle, status) in enumerate(((12.35, 0), (-25.67, 9), (0.0, 0)), 1):
          frames = [
            packer.make_can_msg('STEER_TORQUE_SENSOR', 0, {'STEER_ANGLE': angle, 'LKAS_STATUS': status}),
            packer.make_can_msg('STEER_TORQUE_SENSOR', 1, {'STEER_ANGLE': 100, 'LKAS_STATUS': 9}),
            packer.make_can_msg('STEER_ANGLE_SENSOR', pt_bus, {'STEER_ANGLE': -100}),
          ]
          state = ci.update([(frame * 10_000_000, frames)])
          self.assertAlmostEqual(state.steeringAngleDeg, angle, places=4)
          self.assertEqual(state.steerFaultTemporary, status == 9)

  def test_driver_override_reduces_requested_torque_without_angle_jump(self):
    for car in CAR:
      with self.subTest(car=car):
        ci = interface(car)
        ci.CS.out = ci.update([])
        command = structs.CarControl()
        command.enabled = command.latActive = True
        parser = CANParser(DBC[car][Bus.pt], [('LKAS', 0)], 0)
        for frame, (active, pressed, torque, expected) in enumerate(
          ((True, False, 0.0, 1.0), (True, True, 10.0, 0.2),
           (True, True, -10.0, 0.2), (False, False, 0.0, 0.0)), 1,
        ):
          command.latActive = active
          ci.CS.out.steeringPressed = pressed
          ci.CS.out.steeringTorque = torque
          _, sends = ci.CC.update(command.as_reader(), ci.CS, frame * 10_000_000)
          parser.update((frame * 10_000_000, sends))
          self.assertAlmostEqual(parser.vl['LKAS']['MAX_TORQUE'], expected, places=4)
          self.assertEqual(parser.vl['LKAS']['LKA_ACTIVE'], active)
          self.assertEqual(parser.vl['LKAS']['DESIRED_ANGLE'], 0)

  def test_cancel_uses_stock_protocol_and_bus(self):
    for car in CAR:
      with self.subTest(car=car):
        ci = interface(car, alpha=True)
        ci.CS.out = ci.update([])
        command = structs.CarControl()
        command.cruiseControl.cancel = True
        _, sends = ci.CC.update(command.as_reader(), ci.CS, 10_000_000)
        leaf = car in (CAR.NISSAN_LEAF, CAR.NISSAN_LEAF_IC)
        name = 'CANCEL_MSG' if leaf else 'CRUISE_THROTTLE'
        bus = 1 if car == CAR.NISSAN_ALTIMA else 2
        parser = CANParser(DBC[car][Bus.pt], [(name, 0)], bus)
        updated = parser.update((10_000_000, sends))
        self.assertIn(0x280 if leaf else 0x20B, updated)
        values = parser.vl[name]
        self.assertEqual(values['CANCEL_SEATBELT' if leaf else 'CANCEL_BUTTON'], 1)
        if not leaf:
          for button in ('PROPILOT_BUTTON', 'SET_BUTTON', 'RES_BUTTON', 'FOLLOW_DISTANCE_BUTTON'):
            self.assertEqual(values[button], 0)
        self.assertNotIn(0x1C3, {frame[0] for frame in sends})
        self.assertNotIn(0x2B0, {frame[0] for frame in sends})
