import math
import pytest

from openpilot.starpilot.lateral.ioniq6_policy import get_ioniq_6_low_speed_angle_assist_torque as assist


@pytest.mark.parametrize('speed', [0., 1., 3., 6., 20.])
def test_small_error_sign_change_is_continuous(speed):
  epsilon = 1e-5
  # No model error means no additional angle-assist torque.
  assert assist(0., 0., 0., speed) == 0.
  assert abs(assist(epsilon, 0., 0., speed) - assist(-epsilon, 0., 0., speed)) < epsilon
  # Same continuity while tracking a turn and releasing error across zero.
  assert abs(assist(10. + epsilon, 10., 0., speed) - assist(10. - epsilon, 10., 0., speed)) < epsilon


def test_center_assist_is_bounded_and_does_not_reverse_direction():
  for speed in (0., 1., 3., 7., 20.):
    for desired in (-.9, -.1, 0., .1, .9):
      output = assist(desired, 0., 0., speed)
      assert math.isfinite(output) and abs(output) <= 1.
      assert output * desired <= 0.


@pytest.mark.parametrize('desired, actual, torque, speed, expected', [
  (10., 0., 0., 1., -.39409320626365096),
  (-10., 0., 0., 1., .39409320626365096),
  (0., 10., 0., 1., .07246171113121364),
  (0., -10., 0., 1., -.07246171113121364),
  (10., 8., -.5, 3., -.5322587905665043),
])
def test_existing_turn_and_unwind_response_outside_center_is_unchanged(desired, actual, torque, speed, expected):
  assert assist(desired, actual, torque, speed) == expected


def test_center_correction_retains_output_saturation_and_symmetry():
  for speed in (0., 1., 3., 10., 40.):
    for actual in (0., 10., 30.):
      for error in (-.9, -.5, -.01, 0., .01, .5, .9):
        for torque in (-1., -.99, -.5, 0., .5, .99, 1.):
          positive = assist(actual + error, actual, torque, speed)
          negative = assist(-actual - error, -actual, -torque, speed)
          assert -1. <= positive <= 1.
          assert positive == -negative
