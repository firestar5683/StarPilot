import math
from operator import setitem
import unittest
from unittest import mock

from openpilot.starpilot.flm.torque_surface import Ioniq6Surface, SurfaceInput, _BOUNDS, directional_taper_target, evaluate
from openpilot.starpilot.lateral import ioniq6_policy as baseline


class TestIoniq6Surface(unittest.TestCase):
  def test_profile_validation_and_immutability(self):
    surface = Ioniq6Surface.validated("standard", {"ff_gain_left": 0.217})
    self.assertEqual(surface.value("ff_gain_left"), 0.217)
    with self.assertRaises(TypeError):
      mock.Mock(wraps=setitem)(surface.knobs, "ff_gain_left", 0.3)
    source = {"ff_gain_left": 0.24}
    direct = Ioniq6Surface("standard", source)
    source["ff_gain_left"] = 0.50
    self.assertEqual(direct.value("ff_gain_left"), 0.24)
    for variant, knobs in (("2023", {}), ("standard", {"unknown": 1.0}),
                           ("standard", {"ff_gain_left": True}),
                           ("standard", {"ff_gain_left": math.nan}),
                           ("standard", {"ff_gain_left": 10 ** 1000}),
                           ("standard", {"turn_in_boost_left": 0.2}),
                           ("standard", {"ff_gain_left": 0.601}),
                           ("standard", {"curvy_speed_min": 25.0})):
      with self.subTest(variant=variant, knobs=knobs), self.assertRaises(ValueError):
        Ioniq6Surface.validated(variant, knobs)

  def test_neutral_matches_existing_ioniq_stages(self):
    for variant in ("standard", "firmware_2025"):
      surface = Ioniq6Surface.validated(variant, {})
      for speed, setpoint, jerk, desired, actual in ((3.0, 0.7, 1.1, 11.0, 1.0),
                                                     (14.0, -0.9, -1.5, -12.0, -3.0),
                                                     (27.0, -0.8, 1.7, -3.0, -12.0),
                                                     (26.0, 0.0, 0.0, 0.0, 0.0)):
        with self.subTest(variant=variant, speed=speed, setpoint=setpoint, jerk=jerk):
          taper = baseline.get_ioniq_6_directional_taper_scale(setpoint, jerk, speed)
          i = SurfaceInput(speed, setpoint, jerk, desired, actual, 0.2, False, taper)
          shape = evaluate(surface, i)
          center = baseline.get_ioniq_6_center_taper_scale(setpoint, speed)
          self.assertAlmostEqual(shape.directional_taper_target, taper, places=12)
          self.assertAlmostEqual(shape.center_taper, center, places=12)
          self.assertAlmostEqual(shape.feedforward_scale,
                                 baseline.get_ioniq_6_ff_scale(setpoint, jerk, speed, directional_taper_scale=taper), places=12)
          self.assertAlmostEqual(shape.friction_threshold,
                                 baseline.get_ioniq_6_friction_threshold(speed, setpoint, jerk) / max(center, 1e-3), places=12)
          self.assertAlmostEqual(shape.output_after_angle_assist,
                                 baseline.get_ioniq_6_low_speed_angle_assist_torque(desired, actual, 0.2, speed), places=12)
          self.assertEqual(shape.center_deadband_deg, 0.0)

  def test_nondefault_direction_center_unwind_and_pose(self):
    surface = Ioniq6Surface.validated("standard", {
      "ff_gain_left": 0.30, "ff_gain_right": 0.12,
      "turn_in_boost_left": 1.2, "unwind_taper_right": 2.5,
      "center_taper_max": 0.16, "highway_center_taper_max": 0.15,
      "unwind_threshold_increase_right": 3.0,
      "curvy_turn_in_trim_left": 0.15, "curvy_unwind_extra_reduction_right": 0.25,
      "curvy_unwind_floor_relief_right": 0.40,
      "center_deadband_low_deg": 0.1, "center_deadband_mid_deg": 0.15,
      "low_speed_angle_assist_max_torque": 0.7,
    })
    neutral = Ioniq6Surface.validated("standard", {})
    turn = SurfaceInput(3.0, 0.8, 1.2, 12.0, 1.0, 0.0, False, 0.9)
    unwind = SurfaceInput(14.0, -0.8, 1.2, -2.0, -10.0, 0.3, False, 0.8)
    shaped_turn = evaluate(surface, turn)
    shaped_unwind = evaluate(surface, unwind)
    self.assertNotEqual(shaped_turn.feedforward_scale, evaluate(neutral, turn).feedforward_scale)
    self.assertNotEqual(shaped_turn.center_taper, evaluate(neutral, turn).center_taper)
    self.assertNotEqual(shaped_turn.output_after_angle_assist, evaluate(neutral, turn).output_after_angle_assist)
    self.assertNotEqual(shaped_unwind.directional_taper_target, evaluate(neutral, unwind).directional_taper_target)
    self.assertNotEqual(shaped_unwind.friction_threshold, evaluate(neutral, unwind).friction_threshold)
    self.assertGreater(shaped_turn.center_deadband_deg, 0.0)
    pressed = SurfaceInput(3.0, 0.8, 1.2, 12.0, 1.0, 0.2, True, 0.9)
    self.assertEqual(evaluate(surface, pressed).output_after_angle_assist, 0.2)

  def test_filtered_taper_is_separate_controller_owned_state(self):
    surface = Ioniq6Surface.validated("standard", {})
    i = SurfaceInput(14.0, -0.8, 1.2, -6.0, -2.0, 0.2, False, filtered_directional_taper=0.91)
    shape = evaluate(surface, i)
    self.assertAlmostEqual(shape.feedforward_scale,
                           baseline.get_ioniq_6_ff_scale(i.setpoint, i.jerk, i.speed, directional_taper_scale=0.91))
    self.assertNotEqual(shape.directional_taper_target, 0.91)
    for bad in (math.nan, math.inf, -2.1):
      with self.assertRaises(ValueError):
        SurfaceInput(i.speed, i.setpoint, i.jerk, i.desired_angle_deg, i.actual_angle_deg, i.output_torque, False, bad)
    for bad in (True, 10 ** 1000):
      with self.assertRaises(ValueError):
        SurfaceInput(bad, i.setpoint, i.jerk, i.desired_angle_deg, i.actual_angle_deg, i.output_torque, False, 0.9)
    unchecked_input = mock.Mock(wraps=SurfaceInput)
    with self.assertRaises(ValueError):
      unchecked_input(i.speed, i.setpoint, i.jerk, i.desired_angle_deg, i.actual_angle_deg, i.output_torque, "false", 0.9)
    with self.assertRaises(ValueError):
      unchecked_input(i.speed, i.setpoint, i.jerk, i.desired_angle_deg, i.actual_angle_deg, i.output_torque, False, None)

  def test_frozen_ioniq_stage_vectors(self):
    # Compact values from frozen 678af783 latcontrol_vehicle_tunes.py SHA256
    # 2a7793c6ee4b53b45070d3267a01e8c7105dfd8df9d38cdfc96cfe4b672a125b.
    # Generated with private AST oracle, not by importing the frozen checkout.
    surface = Ioniq6Surface.validated("standard", {
      "ff_gain_left": 0.11, "ff_gain_right": 0.09,
      "turn_in_boost_left": 2.2, "turn_in_boost_right": 2.4,
      "unwind_taper_left": 5.0, "unwind_taper_right": 10.0,
      "center_taper_max": 0.13, "highway_center_taper_max": 0.08,
      "turn_in_threshold_reduction_left": 1.1, "turn_in_threshold_reduction_right": 1.6,
      "unwind_threshold_increase_left": 5.0, "unwind_threshold_increase_right": 11.0,
      "crawl_turn_in_ff_boost_left": 0.33, "crawl_turn_in_ff_boost_right": 0.38,
      "low_speed_angle_assist_max_torque": 0.60,
    })
    # speed, accel, jerk, desired angle, actual angle; then frozen direction,
    # center, combined pre-2023 FF, threshold and pose output from 0.2 torque.
    vectors = (
      (3.0, 0.18, 0.42, 11.0, 2.0, 0.988394829429103, 0.9978605797219613,
       1.4749555335910585, 0.32048565350593106, -0.13901469137077216),
      (14.0, -0.32, 0.55, -9.0, -15.0, 0.49398782437927313, 0.9746594981685954,
       0.4814699250108986, 0.40460794823460716, 0.2),
      (27.0, 0.19, 0.50, 9.0, 4.0, 0.9444309506239349, 0.8839299279089594,
       0.9260528746519242, 0.4179582730864161, 0.2),
    )
    for speed, accel, jerk, desired, actual, direction, center, ff, threshold, pose in vectors:
      with self.subTest(speed=speed, accel=accel, jerk=jerk):
        shape = evaluate(surface, SurfaceInput(speed, accel, jerk, desired, actual, 0.2, False, direction))
        self.assertAlmostEqual(shape.directional_taper_target, direction, places=11)
        self.assertAlmostEqual(shape.center_taper, center, places=11)
        self.assertAlmostEqual(shape.feedforward_scale * shape.center_taper, ff, places=11)
        self.assertAlmostEqual(shape.friction_threshold, threshold, places=11)
        self.assertAlmostEqual(shape.output_after_angle_assist, pose, places=11)

  def test_historical_combined_extreme_is_preserved_but_unqualified(self):
    # Every individual value is inside frozen metadata, yet the combination
    # reverses the directional multiplier. Pure math must expose it, not clip it.
    surface = Ioniq6Surface.validated("standard", {name: high for name, (_, high) in _BOUNDS.items()})
    target = directional_taper_target(surface, 18.0, 0.9, -3.0)
    self.assertAlmostEqual(target, -0.13824656992744921, places=11)
    shape = evaluate(surface, SurfaceInput(18.0, 0.9, -3.0, 8.0, 4.0, 0.2, False, target))
    self.assertEqual(shape.directional_taper_target, target)
    self.assertLess(shape.feedforward_scale, 0.0)


if __name__ == "__main__":
  unittest.main()
