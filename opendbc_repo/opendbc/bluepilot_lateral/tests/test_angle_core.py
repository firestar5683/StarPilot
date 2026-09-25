"""Pure angle host-independent finite inputs and explicit override/blip reset."""
import math
import unittest
from opendbc.bluepilot_lateral.core.angle import AngleController, Inputs, Command
from opendbc.bluepilot_lateral.params import limits
from opendbc.bluepilot_lateral.tests import reference
from opendbc.bluepilot_lateral.hosts.starpilot import CLASSIC, CANFD, TRUCKS
from opendbc.bluepilot_lateral.can.ford import lateral, lka
from opendbc.can import CANPacker
from types import SimpleNamespace
from dataclasses import replace
from opendbc.bluepilot_lateral.core.trim import LaneCenterTrim, LaneGeometry, TrimConfig
from opendbc.bluepilot_lateral.hosts.starpilot import model_geometry
from openpilot.selfdrive.modeld.constants import ModelConstants


class TestAngleCore(unittest.TestCase):
  def test_finite_permission_and_inactive_state_clear_pending_history(self):
    for value in (math.nan, math.inf, -math.inf):
      for field in ("speed", "desired_curvature", "measured_curvature", "steering_angle", "lateral_delay"):
        core = AngleController()
        inputs = Inputs(active=True, speed=15., measured_curvature=0., desired_curvature=.001)
        self.assertEqual(core.step(replace(inputs, **{field: value})), Command())
    core = AngleController()
    for _ in range(10):
      self.assertTrue(core.step(Inputs(True, 15., 0., .001)).active)
    self.assertEqual(core.step(Inputs(False, 15., 0., .001)), Command())
    self.assertEqual(core.path_last, 0.)

  def test_actual_equivalent_jerk_and_cap_both_signs_and_speeds(self):
    for speed in (1., 9., 10., 15., 25., 40., 55.):
      for direction in (-1, 1):
        core = AngleController(low_gain=.95, high_gain=.95)
        previous = 0.
        for _ in range(60):
          command = core.step(Inputs(True, speed, 0., direction * .002))
          if command.active:
            equivalent = command.path_angle / speed / limits.GAIN_MIN
            self.assertLessEqual(abs(equivalent), min(limits.CURVATURE_MAX, limits.LATERAL_ACCEL / max(speed, 1.) ** 2))
            self.assertLessEqual(abs(equivalent - previous), limits.LATERAL_JERK / max(speed - 1., 1.) ** 2 * .05)
            previous = equivalent
          else:
            previous = 0.

  def test_human_turn_and_release_blips_are_neutral_then_bounded(self):
    core = AngleController()
    for _ in range(61):
      result = core.step(Inputs(True, 15., 0., .001, steering_pressed=True, steering_angle=60.))
    self.assertFalse(result.active)
    self.assertEqual(result.path_angle, 0.)
    core = AngleController()
    for _ in range(12):
      core.step(Inputs(True, 15., 0., .001, steering_pressed=True))
    for _ in range(6):
      self.assertEqual(core.step(Inputs(True, 15., 0., .001)), Command())
    resumed = core.step(Inputs(True, 15., 0., .001))
    self.assertTrue(resumed.active)
    self.assertLess(abs(resumed.path_angle), .02)

  def test_pinned_bp7_pure_angle_and_actual_control_bytes_with_documented_limits(self):
    builders = reference.builders()
    bus = SimpleNamespace(main=0)
    differences = set()
    packer = CANPacker("ford_lincoln_base_pt")
    for identity in sorted(CLASSIC | CANFD):
      gains = (.95, .95) if identity in TRUCKS else ((1., 1.05) if identity in CANFD else (1., 1.15))
      for speed in (5., 15., 25., 40.):
        for direction in (-1, 1):
          adapted, upstream = AngleController(low_gain=gains[0], high_gain=gains[1]), reference.Angle(identity)
          for tick in range(60):
            # Tiny tracking curves stay clear of all intentional envelope changes.
            desired = direction * .00005 * (1. + .2 * math.sin(tick / 8.))
            inputs = Inputs(True, speed, desired, desired,
                            yaw_predictions=tuple(desired * speed for _ in ModelConstants.T_IDXS),
                            time_indices=tuple(ModelConstants.T_IDXS), lateral_delay=.15,
                            lane_change=tick >= 30, lane_direction=1 if direction < 0 else 2)
            result = upstream.step(inputs)
            command = adapted.step(inputs)
            self.assertTrue(command.active)
            self.assertAlmostEqual(command.path_angle, result.path_angle, places=12)
            self.assertEqual(command.precision, result.precision_type)
            fd = identity in CANFD
            actual = lateral(packer, 0, command, canfd=fd, counter=tick % 16)
            expected = (builders["create_lat_ctl2_msg"](packer, bus, 1, result.ramp_type, result.precision_type,
                        0., -result.path_angle, 0., 0., tick % 16) if fd else
                        builders["create_lat_ctl_msg"](packer, bus, True, result.ramp_type, result.precision_type,
                        0., -result.path_angle, 0., 0.))
            self.assertEqual(actual, expected)
            old_shadow = builders["create_lka_msg"](packer, bus, True, SimpleNamespace(), True, upstream.controller.bp_kappa_cmd)
            new_shadow = lka(packer, 0, command.shadow_curvature, tick % 8)
            # bp7 packs an empty body as raw zeros; the strict native contract requires physical zeros.
            self.assertEqual(old_shadow[1][:4], b"\x00\x00\x00\x00")
            self.assertEqual(new_shadow[1][:4], b"\x00\x80\x08\x00")
            differences.update(("physical_neutral_dbc_offsets", "versioned_side_channel"))
          # Aggressive entry demonstrates the required stricter native-equivalent derivative/cap.
          adapted, upstream = AngleController(low_gain=gains[0], high_gain=gains[1]), reference.Angle(identity)
          previous = 0.
          for _tick in range(8):
            inputs = Inputs(True, speed, 0., direction * .02,
                            yaw_predictions=tuple(direction * .02 * speed for _ in ModelConstants.T_IDXS),
                            time_indices=tuple(ModelConstants.T_IDXS), lateral_delay=.15)
            result, command = upstream.step(inputs), adapted.step(inputs)
            if command.active:
              equivalent = command.path_angle / max(speed, .1) / limits.GAIN_MIN
              self.assertLessEqual(abs(equivalent), min(limits.CURVATURE_MAX, limits.LATERAL_ACCEL / max(speed, 1.) ** 2))
              self.assertLessEqual(abs(equivalent - previous), limits.LATERAL_JERK / max(speed - 1., 1.) ** 2 * .05)
              previous = equivalent
              if abs(command.path_angle - result.path_angle) > 1e-7:
                differences.add("native_cap_jerk_deviation_packing")
            else:
              previous = 0.
    self.assertEqual(differences, {"physical_neutral_dbc_offsets", "versioned_side_channel", "native_cap_jerk_deviation_packing"})


class TestAngleTrim(unittest.TestCase):
  @staticmethod
  def geometry(direction=1., *, width=3.3, probability=.9):
    xs = (0., 10., 40.)
    return LaneGeometry(xs, (direction * .3,) * 3, xs, (-width / 2,) * 3,
                        xs, (width / 2,) * 3, (probability,) * 2, (.1,) * 2, True)

  @staticmethod
  def model(g):
    return SimpleNamespace(position=SimpleNamespace(x=g.position_x, y=g.position_y),
                           laneLines=[SimpleNamespace(x=(), y=()), SimpleNamespace(x=g.left_x, y=g.left_y),
                                      SimpleNamespace(x=g.right_x, y=g.right_y)],
                           laneLineProbs=[0., *g.probabilities], laneLineStds=[0., *g.standard_deviations])

  def test_disabled_trim_preserves_all_eleven_default_commands_and_wire_bytes(self):
    packer = CANPacker("ford_lincoln_base_pt")
    for identity in sorted(CLASSIC | CANFD):
      low, high = (.95, .95) if identity in TRUCKS else ((1., 1.05) if identity in CANFD else (1., 1.15))
      for speed in (5., 15., 25., 40.):
        for direction in (-1, 1):
          baseline, supplied = AngleController(low_gain=low, high_gain=high), AngleController(low_gain=low, high_gain=high)
          self.assertFalse(supplied.trim_config.enabled)
          for tick in range(30):
            i = Inputs(True, speed, 0., direction * .0002)
            a, b = baseline.step(i), supplied.step(replace(i, geometry=self.geometry(direction)))
            self.assertEqual(a, b)
            self.assertEqual(lateral(packer, 0, a, canfd=identity in CANFD, counter=tick % 16),
                             lateral(packer, 0, b, canfd=identity in CANFD, counter=tick % 16))
            self.assertEqual(lka(packer, 0, a.shadow_curvature, tick % 8), lka(packer, 0, b.shadow_curvature, tick % 8))
            self.assertEqual(supplied.trim.correction, 0.)

  def test_fresh_geometry_matches_exact_currentdev_trim_and_model_fallback(self):
    for speed in (5., 9., 12., 15., 25., 40.):
      for direction in (-1, 1):
        adapted, upstream = LaneCenterTrim(), reference.trim()()
        config = TrimConfig(True, direction * .1, .25)
        for tick in range(90):
          g = self.geometry(direction, width=3.3 if tick < 30 or tick >= 60 else 1.5,
                            probability=.9 if tick < 60 else .3)
          actual = adapted.update(.0001, speed, g, config, active=True, lane_change=False)
          expected = upstream.update(.0001, self.model(g), speed, True, config.offset_m, config.gain, True, False)
          self.assertAlmostEqual(actual, expected, places=14)
          self.assertAlmostEqual(adapted.correction, upstream.correction, places=14)
        projected = model_geometry(self.model(g), fresh=True)
        self.assertEqual(projected, g)
        self.assertIsNone(model_geometry(self.model(g), fresh=False))

  def test_invalid_stale_driver_and_lane_change_suppress_trim_and_reset_history(self):
    original = self.geometry()
    config = TrimConfig(True, 0., .25)
    for geometry in (replace(original, fresh=False), replace(original, position_x=(0., 0., 40.)),
                     replace(original, position_y=(0., math.nan, 0.)), replace(original, position_y=(0.,)), None):
      trim = LaneCenterTrim()
      self.assertNotEqual(trim.update(0., 15., original, config, active=True, lane_change=False), 0.)
      self.assertEqual(trim.update(.001, 15., geometry, config, active=True, lane_change=False), .001)
      self.assertEqual(trim.correction, 0.)
    for changes in ({"active": False}, {"lane_change": True}, {"steering_pressed": True}):
      trim = LaneCenterTrim()
      trim.update(0., 15., original, config, active=True, lane_change=False)
      flags = dict(active=True, lane_change=False, steering_pressed=False)
      flags.update(changes)
      self.assertEqual(trim.update(.001, 15., original, config, **flags), .001)
      self.assertEqual(trim.correction, 0.)
    for invalid in (TrimConfig(True, math.nan, .25), TrimConfig(True, 0., math.inf), TrimConfig(True, .6, .25)):
      self.assertEqual(LaneCenterTrim().update(.001, 15., original, invalid, active=True, lane_change=False), .001)
    # Bad lane-only references fall back to the model+offset, not a stale lane correction.
    bad = replace(original, probabilities=(math.nan, .9))
    without_lines = replace(original, left_x=(), right_x=())
    a, b = LaneCenterTrim(), LaneCenterTrim()
    self.assertEqual(a.update(0., 15., bad, TrimConfig(True, .1, .25), active=True, lane_change=False),
                     b.update(0., 15., without_lines, TrimConfig(True, .1, .25), active=True, lane_change=False))
    core = AngleController(trim_config=config)
    core.step(Inputs(True, 15., 0., 0., geometry=original))
    self.assertNotEqual(core.trim.correction, 0.)
    self.assertEqual(core.step(Inputs(False, 15., 0., 0., geometry=original)), Command())
    self.assertEqual(core.trim.correction, 0.)

  def test_enabled_trim_remains_inside_final_curvature_jerk_and_shadow_bounds(self):
    for speed in (9., 10., 15., 25., 40.):
      for direction in (-1, 1):
        core = AngleController(low_gain=.95, high_gain=.95, trim_config=TrimConfig(True, direction * .5, 1.))
        previous, previous_trim, previous_active = 0., 0., False
        for _tick in range(100):
          command = core.step(Inputs(True, speed, 0., direction * .02, geometry=self.geometry(-direction)))
          if command.active and previous_active:
            self.assertLessEqual(abs(core.trim.correction - previous_trim), .00015 + 1e-12)
          previous_trim, previous_active = core.trim.correction, command.active
          if command.active:
            equivalent = command.path_angle / speed / limits.GAIN_MIN
            self.assertLessEqual(abs(equivalent), min(limits.CURVATURE_MAX, limits.LATERAL_ACCEL / max(speed, 1.) ** 2))
            self.assertLessEqual(abs(equivalent - previous), limits.LATERAL_JERK / max(speed - 1., 1.) ** 2 * .05)
            self.assertLessEqual(abs(command.shadow_curvature), min(limits.CURVATURE_MAX, limits.LATERAL_ACCEL / max(speed, 1.) ** 2))
            # Shadow comes from the final path; no independent trim/shadow command can bypass bounds.
            ratio = command.path_angle / (speed * command.shadow_curvature) if command.shadow_curvature else 1.
            self.assertTrue(limits.GAIN_MIN - 1e-12 <= ratio <= limits.GAIN_MAX + 1e-12)
            previous = equivalent
          else:
            previous = 0.
            self.assertEqual(core.trim.correction, 0.)
