import unittest

from opendbc.car.subaru.tests.test_ascent_angle import setup_controller, step
from opendbc.car.subaru.values import CAR


class TestAngleHandoff(unittest.TestCase):
  def test_override_release_waits_for_low_torque_and_settled_wheel(self):
    for car, high, low in ((CAR.SUBARU_CROSSTREK_2025, 150, 100), (CAR.SUBARU_LEGACY_2025, 200, 150)):
      for sign in (-1, 1):
        with self.subTest(car=car, sign=sign):
          _, controller, command, state = setup_controller(car)
          state.out.steeringRateDeg = 0
          state.out.steeringAngleDeg = 10
          # One sample above the threshold must not hand control back and forth.
          for torque, rate, expected in ((high, 0, 1), (high + 1, 0, 1), (high + 1, 0, 0),
                                         (high, 0, 0), (low, 0, 0), (low - 1, 3, 0),
                                         (0, 2, 0), (0, 2, 1)):
            state.out.steeringTorque = torque * sign
            state.out.steeringRateDeg = rate * sign
            steer, decoded = step(controller, command, state)
            self.assertEqual(steer[2], 1)
            self.assertEqual(decoded['LKAS_Request'], expected)
            if not expected:
              self.assertEqual(decoded['LKAS_Output'], 10)

  def test_engagement_waits_for_manual_turn_to_settle(self):
    for car in (CAR.SUBARU_CROSSTREK_2025, CAR.SUBARU_LEGACY_2025):
      with self.subTest(car=car):
        _, controller, command, state = setup_controller(car)
        state.out.steeringTorque = 0
        for rate, expected in ((3, 0), (2.1, 0), (2, 0), (2, 1)):
          state.out.steeringRateDeg = rate
          _, decoded = step(controller, command, state)
          self.assertEqual(decoded['LKAS_Request'], expected)

  def test_unavailable_control_clears_override_without_sending_active_commands(self):
    for car in (CAR.SUBARU_CROSSTREK_2025, CAR.SUBARU_LEGACY_2025):
      with self.subTest(car=car):
        _, controller, command, state = setup_controller(car)
        state.out.steeringRateDeg = 0
        state.out.steeringTorque = 300
        step(controller, command, state)
        step(controller, command, state)
        command.latActive = False
        _, decoded = step(controller, command, state)
        self.assertEqual(decoded['LKAS_Request'], 0)
        self.assertFalse(controller.angle_driver_override)
        self.assertFalse(controller.angle_handoff_active)
        state.out.steeringTorque = 0
        command.latActive = True
        _, decoded = step(controller, command, state)
        self.assertEqual(decoded['LKAS_Request'], 1)
