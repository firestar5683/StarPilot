"""Frozen committed-turn boundaries with current-source unknown semantics."""

import unittest

from openpilot.starpilot.conditional_mode.turn_scene import MAX_TURN_SPEED_MPS, committed_turn_scene


def turn(**changes):
  values = {'speed_mps': 5.0, 'standstill': False, 'left_blinker': True,
            'right_blinker': False, 'steering_angle_deg': 45.0, 'driving_in_curve': False}
  return committed_turn_scene(**(values | changes))


class TestCommittedTurnScene(unittest.TestCase):
  def test_frozen_speed_angle_and_measured_curve_boundaries(self):
    self.assertTrue(turn(speed_mps=MAX_TURN_SPEED_MPS))
    self.assertFalse(turn(speed_mps=MAX_TURN_SPEED_MPS + 0.001))
    self.assertFalse(turn(steering_angle_deg=44.999))
    self.assertTrue(turn(steering_angle_deg=44.999, driving_in_curve=True))
    self.assertFalse(turn(left_blinker=False))
    self.assertTrue(turn(left_blinker=False, right_blinker=True))
    self.assertFalse(turn(standstill=True))

  def test_short_circuits_known_absence_but_not_active_missing_evidence(self):
    self.assertFalse(turn(left_blinker=False, steering_angle_deg=None, driving_in_curve=None))
    self.assertFalse(turn(standstill=True, steering_angle_deg=None, driving_in_curve=None))
    self.assertFalse(turn(speed_mps=7.0, steering_angle_deg=None, driving_in_curve=None))
    self.assertIsNone(turn(steering_angle_deg=45.0, driving_in_curve=None))
    self.assertIsNone(turn(steering_angle_deg=None, driving_in_curve=True))
    self.assertIsNone(turn(driving_in_curve=1))
    self.assertIsNone(turn(speed_mps=float('nan')))
    self.assertIsNone(turn(speed_mps=10**10000))
    self.assertIsNone(turn(standstill=0))
    self.assertIsNone(turn(left_blinker=1))


if __name__ == '__main__':
  unittest.main()
