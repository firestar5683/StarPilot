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

class TestGmSurface(unittest.TestCase):
  def test_selected_neutral_and_rich_default_laws(self):
    from openpilot.starpilot.flm.torque_surface import GmSurface
    from openpilot.starpilot.lateral import bolt_shaping as gm
    neutral = GmSurface('torque_universal', {})
    rich = GmSurface('gm_bolt_2022_2023', {})
    for speed, setpoint, jerk in ((3., .8, 1.2), (14., -.8, 1.2), (27., .8, -1.2), (26., 0., 0.)):
      sample = SurfaceInput(speed, setpoint, jerk, 0., 0., 0., False, 1.)
      ff, threshold = neutral.stages(sample, setpoint, gm.get_gm_base_friction_threshold(speed))
      self.assertEqual(ff, setpoint)
      self.assertEqual(threshold, gm.get_gm_base_friction_threshold(speed))
      self.assertEqual(neutral.deadband(speed), 0.)
      rich_ff, rich_threshold = rich.stages(sample, setpoint, threshold, rich=True)
      self.assertAlmostEqual(rich_ff, setpoint * gm.get_bolt_2022_2023_ff_scale(setpoint, jerk, speed), places=12)
      self.assertAlmostEqual(rich_threshold, gm.get_bolt_2022_2023_friction_threshold(speed, setpoint, jerk), places=12)
      self.assertEqual(rich.angle_assist(sample), 0.)

  def test_explicit_surface_bounds_composition_and_immutable_document(self):
    from openpilot.starpilot.flm.torque_surface import GmSurface, GmFlmBinding
    knobs = {'ff_gain_left': .3, 'ff_gain_right': -.1, 'center_deadband_low_deg': .1}
    surface = GmSurface('torque_universal', knobs, [.16, .18, .20, .23, .27])
    knobs['ff_gain_left'] = .6
    self.assertEqual(surface.knobs['ff_gain_left'], .3)
    with self.assertRaises(TypeError):
      surface.knobs['ff_gain_left'] = .5
    self.assertEqual(GmSurface.from_document(surface.document()).document(), surface.document())
    self.assertGreater(surface.deadband(5.), 0.)
    self.assertAlmostEqual(surface.base_threshold(10.), .20)
    for speed in (3., 14., 27.):
      for sign in (-1., 1.):
        sample = SurfaceInput(speed, sign*.8, sign*1.2, 0., 0., 0., False, 1.)
        ff, threshold = surface.stages(sample, sign*.8, .2)
        self.assertGreater(ff * sign, 0.)
        if speed == 3.:
          self.assertGreater(ff, .8) if sign > 0 else self.assertLess(abs(ff), .8)
        self.assertTrue(math.isfinite(threshold) and threshold > 0.)
    for knobs, curve in (({'ff_gain_left': -.4, 'turn_in_boost_left': 2.8}, None),
                         ({'ff_gain_left': math.nan}, None), ({'ff_gain_left': 10**1000}, None),
                         ({'ff_gain_left': True}, None), ({'curvy_speed_min': 25.}, None),
                         ({}, [.2]*4), ({}, [.2, .2, math.inf, .2, .2]), ({}, [10**1000]*5)):
      with self.assertRaises(ValueError):
        GmSurface('torque_universal', knobs, curve)
    binding = GmFlmBinding('starpilot', 'ordinary_ascm', (2., 0., .1), (('one', 'Surface', surface),), 'one', True)
    self.assertEqual(GmFlmBinding.from_document(binding.document()), binding)
    for value in ({**binding.document(), 'active': 'missing'}, {**binding.document(), 'baselineActive': 'one', 'baselineApplied': True}):
      with self.assertRaises(ValueError):
        GmFlmBinding.from_document(value)

  def test_actual_selected_controller_neutral_surface_has_no_double_application(self):
    from types import SimpleNamespace
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.tests.test_ascm_intercept import params as ordinary_params
    from opendbc.car.gm.tests.test_bolt_cc import params as bolt_params
    from opendbc.car.gm.values import CAR
    from opendbc.car.vehicle_model import VehicleModel
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
    from openpilot.starpilot.flm.live import gm_capability
    from openpilot.starpilot.flm import live as flm
    from openpilot.starpilot.flm.torque_surface import GmFlmBinding, GmSurface
    from openpilot.starpilot.lateral.controller_selection import ControllerMode, replace_mode
    from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, PlatformProfile, FieldChoice, serialize_document
    import json
    cases = (ordinary_params(CAR.CHEVROLET_MALIBU_ASCM), bolt_params(CAR.CHEVROLET_BOLT_CC_2022_2023, alpha=True))
    for cp_builder in cases:
      cp = cp_builder.as_reader()
      for mode in ControllerMode:
        with OpenpilotPrefix():
          saved = Params()
          saved.put('LateralControllerSelection', json.loads(replace_mode(None, cp, mode)), block=True)
          baseline = LatControlTorque(cp, CarInterface(cp), .01, controller_mode=mode)
          overlay = LatControlTorque(cp, CarInterface(cp), .01, controller_mode=mode)
          cap = gm_capability(cp, mode)
          surface = GmSurface(cap['profile'], {})
          cs = SimpleNamespace(vEgo=20., steeringAngleDeg=0., steeringPressed=False, steeringRateDeg=0., standstill=False)
          params = SimpleNamespace(angleOffsetDeg=0., roll=0.)
          vm = VehicleModel(cp)
          with mock.patch('openpilot.starpilot.flm.live.time.monotonic_ns', return_value=1_000_000_000):
            baseline.flm_source.sample(active=True, speed=cs.vEgo)
            binding = GmFlmBinding(str(mode), cap['policy'], cap['basis'], (('neutral', 'Neutral', surface),), 'neutral', True)
            saved.put(DOCUMENT_KEY, json.loads(serialize_document({str(cp.carFingerprint): PlatformProfile(cap['basis'], FieldChoice(),
              FieldChoice(), flm=binding)})), block=True)
            with mock.patch('openpilot.starpilot.flm.live.stages', wraps=flm.stages) as stages:
              for tick in range(100):
                curvature = .001 if tick < 50 else -.001
                before = baseline.update(True, cs, vm, params, False, curvature, False, .2)
                after = overlay.update(True, cs, vm, params, False, curvature, False, .2)
                self.assertEqual(before[:2], after[:2], (cp.carFingerprint, mode, tick))
                self.assertEqual(before[2].to_dict(), after[2].to_dict(), (cp.carFingerprint, mode, tick))
              self.assertEqual(stages.call_count, 200, 'exactly one generic stage call per actual controller update')
            self.assertIsNotNone(overlay.flm_surface)
            self.assertIsNone(baseline.flm_surface)
            self.assertEqual(overlay.update(False, cs, vm, params, False, .001, False, .2)[0], 0.)
            self.assertIsNone(overlay.flm_surface)


  def test_standard_bolt_explicit_universal_angle_assist_reaches_actual_generic_controller(self):
    import json
    from types import SimpleNamespace
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.tests.test_bolt_cc import params as bolt_params
    from opendbc.car.gm.values import CAR
    from opendbc.car.vehicle_model import VehicleModel
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
    from openpilot.starpilot.flm import live as flm
    from openpilot.starpilot.flm.live import gm_capability
    from openpilot.starpilot.flm.torque_surface import GmFlmBinding, GmSurface
    from openpilot.starpilot.lateral.controller_selection import ControllerMode, replace_mode
    from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, PlatformProfile, FieldChoice, serialize_document
    cp = bolt_params(CAR.CHEVROLET_BOLT_CC_2022_2023, alpha=True).as_reader()
    mode = ControllerMode.STANDARD
    with OpenpilotPrefix():
      params = Params()
      params.put('LateralControllerSelection', json.loads(replace_mode(None, cp, mode)), block=True)
      controller = LatControlTorque(cp, CarInterface(cp), .01, controller_mode=mode)
      self.assertIsNone(controller.starpilot_extension)
      cap = gm_capability(cp, mode)
      surface = GmSurface(cap['profile'], {'low_speed_angle_assist_max_torque': .1})
      binding = GmFlmBinding(str(mode), cap['policy'], cap['basis'], (('assist', 'Assist', surface),), 'assist', True)
      params.put(DOCUMENT_KEY, json.loads(serialize_document({cap['fingerprint']: PlatformProfile(cap['basis'],
        FieldChoice(), FieldChoice(), flm=binding)})), block=True)
      cs = SimpleNamespace(vEgo=3., steeringAngleDeg=0., steeringPressed=False, steeringRateDeg=0., standstill=False)
      learned = SimpleNamespace(angleOffsetDeg=0., roll=0.)
      observed = []
      original_angle = flm.angle_assist
      def actual_angle(*args):
        output = original_angle(*args)
        observed.append((args[-1], output))
        return output
      with mock.patch('openpilot.starpilot.flm.live.time.monotonic_ns', return_value=1_000_000_000), \
           mock.patch('openpilot.starpilot.flm.live.angle_assist', side_effect=actual_angle):
        result = controller.update(True, cs, VehicleModel(cp), learned, False, .003, False, .2)
      self.assertTrue(result[2].active)
      self.assertEqual(len(observed), 1)
      self.assertGreater(abs(observed[0][1] - observed[0][0]), 1e-6)
      self.assertTrue(math.isfinite(result[0]) and abs(result[0]) <= 1.)
