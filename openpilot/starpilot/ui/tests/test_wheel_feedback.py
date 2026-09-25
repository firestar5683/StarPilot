"""Wheel feedback sources, saved compatibility and actual draw-call colors."""

from dataclasses import replace
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import pyray as rl

from openpilot.common.params import Params
from openpilot.starpilot import saved_document
from openpilot.starpilot.ui.appearance_owner import AppearanceOwner
from openpilot.starpilot.ui.appearance_preferences import OnroadAppearance, onroad_appearance
from openpilot.starpilot.ui.feature_settings_state import row_change
from openpilot.starpilot.ui.onroad_compact_widgets import CompactHudRenderer
from openpilot.starpilot.ui.onroad_large_widgets import SteeringWheelWidget
from openpilot.starpilot.ui.onroad_state import OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.runtime_snapshot import RuntimeSnapshotAdapter
from openpilot.starpilot.ui.shell import ShellMode
from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, ui_fake
from openpilot.starpilot.ui.wheel_feedback import ACCEL_RGB, BRAKE_RGB, WheelFeedback, observe_wheel_feedback, wheel_feedback_rgb


def car(**changes):
  return NS(**{"canValid": True, "canTimeout": False, "brakePressed": False, "regenBraking": False,
               "gasPressed": False, "aEgo": 0.0, **changes})


def control(**changes):
  return NS(longActive=True, actuators=NS(**{"accel": 0.0, "gas": 0.0, **changes}))


class WheelFeedbackTests(unittest.TestCase):
  def test_original_thresholds_and_braking_priority(self):
    cases = (
      (WheelFeedback(brake_pressed=True, gas_pressed=True), BRAKE_RGB),
      (WheelFeedback(regen_braking=True, commanded_gas=1), BRAKE_RGB),
      (WheelFeedback(acceleration=-0.251, commanded_acceleration=0.1), BRAKE_RGB),
      (WheelFeedback(acceleration=0.3, commanded_acceleration=-0.051), BRAKE_RGB),
      (WheelFeedback(gas_pressed=True), ACCEL_RGB),
      (WheelFeedback(acceleration=0.251), ACCEL_RGB),
      (WheelFeedback(commanded_acceleration=0.051), ACCEL_RGB),
      (WheelFeedback(commanded_gas=0.051), ACCEL_RGB),
      (WheelFeedback(acceleration=-0.25, commanded_acceleration=-0.05), None),
      (WheelFeedback(acceleration=0.25, commanded_acceleration=0.05, commanded_gas=0.05), None),
      (WheelFeedback(), None),
    )
    for value, expected in cases:
      with self.subTest(value=value):
        self.assertEqual(wheel_feedback_rgb(value, True), expected)
        self.assertIsNone(wheel_feedback_rgb(value, False))

  def test_missing_invalid_and_inactive_sources_do_not_invent_feedback(self):
    for vehicle in (None, car(canValid=False), car(canTimeout=True)):
      self.assertEqual(observe_wheel_feedback(vehicle, control(accel=1)), WheelFeedback())
    cmd = control(accel=-1)
    cmd.longActive = False
    self.assertIsNone(wheel_feedback_rgb(observe_wheel_feedback(car(), cmd), True))
    self.assertEqual(wheel_feedback_rgb(observe_wheel_feedback(car(brakePressed=True), None), True), BRAKE_RGB)
    value = observe_wheel_feedback(car(brakePressed="1", aEgo=float("nan")), control(accel=float("inf"), gas=True))
    self.assertIsNone(value.brake_pressed)
    self.assertIsNone(value.acceleration)
    self.assertIsNone(value.commanded_acceleration)
    self.assertIsNone(value.commanded_gas)
    self.assertIsNone(wheel_feedback_rgb(value, True))
    # Deprecated/unqualified brakeLights is deliberately not treated as a producer.
    self.assertIsNone(wheel_feedback_rgb(observe_wheel_feedback(car(brakeLights=True), None), True))

  def test_runtime_freshness_drive_boundary_and_command_expiry(self):
    ui = ui_fake()
    vars(ui.sm.messages["carState"]).update(vars(car()))
    vars(ui.sm.messages["carControl"]).update(vars(control(accel=-0.5)))
    ui.sm.messages["carControl"].actuators.torque = 0.0
    adapter = RuntimeSnapshotAdapter(ui)

    def observed():
      return adapter.build(ShellMode.ONROAD, now_ns=NOW).onroad.wheel_feedback

    self.assertEqual(wheel_feedback_rgb(observed(), True), BRAKE_RGB)
    ui.sm.logMonoTime["carControl"] = NOW - 201_000_000
    self.assertIsNone(wheel_feedback_rgb(observed(), True))
    ui.sm.messages["carState"].brakePressed = True
    self.assertEqual(wheel_feedback_rgb(observed(), True), BRAKE_RGB)
    ui.sm.logMonoTime["carState"] = NOW - 201_000_000
    self.assertEqual(observed(), WheelFeedback())
    for service in ("carControl", "carState"):
      ui.sm.logMonoTime[service] = NOW
    ui.sm.recv_frame["carState"] = ui.started_frame
    self.assertEqual(observed(), WheelFeedback())
    ui.sm.recv_frame["carState"] = ui.started_frame + 1
    ui.sm.valid["carState"] = False
    self.assertEqual(observed(), WheelFeedback())
    ui.sm.valid["carState"] = True
    ui.started = False
    self.assertEqual(observed(), WheelFeedback())

  def test_both_renderers_preserve_placement_and_alpha(self):
    state = OnroadState(True, True, 10, None, SpeedLimitObservation(), lateral_active=True,
                        appearance=OnroadAppearance(wheel_pedal_feedback=True),
                        wheel_feedback=WheelFeedback(brake_pressed=True))
    state.customization["layouts"]["large"]["steering_wheel"].update(x=900, y=200)
    large = SteeringWheelWidget.__new__(SteeringWheelWidget)
    large._texture = Mock()
    with patch.object(rl, "draw_circle"), patch.object(rl, "draw_texture_ex") as draw:
      large.render(rl.Rectangle(30, 30, 1800, 1020), state)
      args = draw.call_args.args
      self.assertEqual((args[1].x, args[1].y), (924, 224))
      self.assertEqual((args[-1].r, args[-1].g, args[-1].b, args[-1].a), (*BRAKE_RGB, 255))
      large.render(rl.Rectangle(30, 30, 1800, 1020), replace(state, appearance=OnroadAppearance()))
      self.assertEqual(draw.call_args.args[-1], rl.WHITE)
    state.customization["layouts"]["compact"]["steering_wheel"].update(x=80, y=130)
    compact = CompactHudRenderer(Mock(), Path("/unused"))
    compact._wheel = Mock()
    with patch.object(compact, "_speed_limit_sign"), patch.object(rl, "draw_texture_pro") as draw:
      compact.render(state)
      args = draw.call_args.args
      self.assertEqual((args[2].x - args[3].x, args[2].y - args[3].y), (80, 130))
      self.assertEqual(tuple(getattr(args[-1], key) for key in "rgb"), BRAKE_RGB)
      self.assertEqual(args[-1].a, int(compact._wheel_alpha.x))
      self.assertLess(args[-1].a, 255)
      draw.reset_mock()
      compact.render(replace(state, lateral_active=False))
      draw.assert_not_called()


class WheelPreferenceTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.parked = True
    self.owner = AppearanceOwner(self.params, lambda: self.parked)

  def path(self, key):
    return Path(self.params.get_param_path(key))

  def row(self, key="ShowBrakeStatus", profile=Profile.LARGE):
    return next(row for row in self.owner.snapshot(profile).rows if row.key == key)

  def test_original_default_compatibility_and_single_effective_control(self):
    self.assertFalse(onroad_appearance(self.params).wheel_pedal_feedback)
    self.assertFalse(onroad_appearance(self.params).hide_dm_icon)
    for profile in Profile:
      self.assertEqual(self.row(profile=profile).value, "Off")
    self.path("PedalsOnUI").write_bytes(b"1")
    self.assertTrue(onroad_appearance(self.params).wheel_pedal_feedback)
    request = row_change(self.row())
    self.assertEqual(request.value, "Off")
    self.assertTrue(self.owner.apply(request))
    self.assertFalse(onroad_appearance(self.params).wheel_pedal_feedback)
    self.assertEqual(self.path("PedalsOnUI").read_bytes(), b"0")
    self.assertEqual(self.path("ShowBrakeStatus").read_bytes(), b"0")
    self.assertTrue(self.owner.apply(row_change(self.row())))
    self.assertTrue(onroad_appearance(self.params).wheel_pedal_feedback)
    self.assertEqual(self.path("PedalsOnUI").read_bytes(), b"0")

  def test_source_repair_and_parked_compound_guards(self):
    request = row_change(self.row())
    self.path("PedalsOnUI").write_bytes(b"1")
    self.assertFalse(self.owner.apply(request))
    self.assertFalse(self.path("ShowBrakeStatus").exists())
    self.path("PedalsOnUI").write_bytes(b"broken")
    request = row_change(self.row())
    self.assertEqual(request.value, "Off")
    self.parked = False
    self.assertFalse(self.owner.apply(request))
    self.assertEqual(self.path("PedalsOnUI").read_bytes(), b"broken")
    self.parked = True
    self.assertTrue(self.owner.apply(request))
    request = row_change(self.row())
    actual = saved_document.os.fsync

    def revoke(fd):
      actual(fd)
      self.parked = False

    with patch.object(saved_document.os, "fsync", side_effect=revoke):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(self.path("ShowBrakeStatus").read_bytes(), b"0")

  def test_compound_failure_does_not_claim_atomic_success(self):
    self.path("PedalsOnUI").write_bytes(b"1")
    self.path("ShowBrakeStatus").write_bytes(b"1")
    request = row_change(self.row())
    original = saved_document.commit_exact

    def commit(params, **kwargs):
      if kwargs["key"] == "ShowBrakeStatus":
        return NS(committed=False, verified=False)
      return original(params, **kwargs)

    with patch("openpilot.starpilot.ui.appearance_owner.commit_exact", side_effect=commit):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(self.row().value, "On")
    self.assertTrue(onroad_appearance(self.params).wheel_pedal_feedback)
    self.assertTrue(self.owner.apply(row_change(self.row())))
    self.assertFalse(onroad_appearance(self.params).wheel_pedal_feedback)

  def test_dm_visibility_is_parked_and_source_bound(self):
    request = row_change(self.row("HideDMIcon", Profile.COMPACT))
    self.parked = False
    self.assertFalse(self.owner.apply(request))
    self.parked = True
    self.assertTrue(self.owner.apply(request))
    self.assertTrue(onroad_appearance(self.params).hide_dm_icon)
    self.assertFalse(self.owner.apply(request))


if __name__ == "__main__":
  unittest.main()
