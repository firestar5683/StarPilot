"""Fresh control axes drive the existing large and compact onroad indicators."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import pyray as rl

from openpilot.starpilot.ui import onroad
from openpilot.starpilot.ui.onroad import axis_status_color
from openpilot.starpilot.ui.onroad_compact_widgets import CompactHudRenderer
from openpilot.starpilot.ui.onroad_large_widgets import DISENGAGED, UnifiedSpeedWidget
from openpilot.starpilot.ui.onroad_state import OnroadInput
from openpilot.starpilot.ui.onroad_torque import TorqueBarWidget
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.preview_shell import reference_onroad
from openpilot.starpilot.ui.runtime_snapshot import RuntimeSnapshotAdapter
from openpilot.starpilot.ui.shell import ShellMode
from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, ui_fake


def rgba(color: rl.Color) -> tuple[int, int, int, int]:
  return color.r, color.g, color.b, color.a


class TestOnroadAxes(unittest.TestCase):
  def setUp(self):
    self.ui = ui_fake()
    self.ui.CP = NS(carFingerprint='', openpilotLongitudinalControl=True, pcmCruise=False)
    car = self.ui.sm["carState"]
    car.canValid = True
    car.canTimeout = False
    car.cruiseState = NS(enabled=False)
    self.ui.sm["selfdriveState"].enabled = True
    self.ui.sm.put("controlsState", NS(longControlState="pid"))
    self.adapter = RuntimeSnapshotAdapter(self.ui)

  def state(self, lateral: bool, longitudinal: bool):
    control = self.ui.sm["carControl"]
    control.latActive = lateral
    control.longActive = longitudinal
    return self.adapter.build(ShellMode.ONROAD, now_ns=NOW).onroad

  def test_four_axis_modes_drive_border_max_and_compact_wheel(self):
    colors = {(False, False): (18, 40, 57, 255), (True, False): (10, 186, 181, 255),
              (False, True): (255, 105, 180, 255), (True, True): (22, 127, 64, 255)}
    for (lateral, longitudinal), expected in colors.items():
      with self.subTest(lateral=lateral, longitudinal=longitudinal):
        state = self.state(lateral, longitudinal)
        self.assertEqual((state.lateral_active, state.longitudinal_active), (lateral, longitudinal))
        self.assertEqual(rgba(axis_status_color(state)), expected)
        fonts = Mock()
        fonts.measure.return_value = NS(width=20, height=10)
        fonts.vertical_ink.return_value = (0, 10)
        with patch("openpilot.starpilot.ui.onroad_large_widgets.draw_control_card"):
          UnifiedSpeedWidget(fonts).render(rl.Rectangle(30, 30, 1800, 1020), state)
        label_color = fonts.draw.call_args_list[0].args[-1]
        self.assertEqual(rgba(label_color), rgba(rl.Color(188, 132, 255, 255) if longitudinal else DISENGAGED))
        compact = CompactHudRenderer(fonts, Path("/unused"))
        with patch.object(compact, "prepare"), patch("openpilot.starpilot.ui.onroad_compact_widgets.rl.draw_texture_pro"), \
             patch("openpilot.starpilot.ui.onroad_compact_widgets.rl.draw_circle_gradient"):
          compact.render(state)
          compact.render(state)
        self.assertEqual(compact._wheel_alpha.x > 0, lateral)
        self.assertEqual(compact._set_speed_alpha.x > 0, longitudinal)

  def test_pedal_override_keeps_cruise_display_and_uses_gray_border(self):
    self.ui.sm['carState'].gasPressed = True
    self.ui.sm['selfdriveState'].state = 'overriding'
    state = self.state(True, False)
    self.assertTrue(state.longitudinal_overridden)
    self.assertTrue(state.cruise_active)
    self.assertTrue(state.lateral_active)
    self.assertEqual(rgba(axis_status_color(state)), (145, 155, 149, 255))
    self.ui.sm['carState'].gasPressed = False
    self.assertFalse(self.state(True, False).longitudinal_overridden)
    self.ui.sm['carState'].gasPressed = True
    self.ui.sm['selfdriveState'].enabled = False
    self.assertFalse(self.state(True, False).longitudinal_overridden)
    self.ui.sm['selfdriveState'].enabled = True
    self.ui.sm.logMonoTime['selfdriveState'] = NOW - 300_000_000
    self.assertFalse(self.state(True, False).longitudinal_overridden)

  def test_traffic_returns_after_conditional_stop_without_changing_intent(self):
    from openpilot.starpilot.conditional_mode.policy import ModeChoice
    from openpilot.starpilot.ui.conditional_status import ConditionalDisplay

    traffic = replace(self.state(True, True), traffic_mode=True)
    stopping = replace(traffic, conditional_effective=ConditionalDisplay(ModeChoice.CEM, True, 'cem_stop', 8, 'test', 1))
    self.assertEqual(rgba(axis_status_color(traffic)), (201, 34, 49, 255))
    for _ in range(3):
      self.assertEqual(rgba(axis_status_color(stopping)), (218, 111, 37, 255))
      self.assertTrue(stopping.traffic_mode)
      self.assertEqual(rgba(axis_status_color(traffic)), (201, 34, 49, 255))
      self.assertTrue(traffic.traffic_mode)
    self.assertEqual(rgba(axis_status_color(replace(stopping, longitudinal_overridden=True))), (145, 155, 149, 255))

  def test_experimental_border_requires_active_combined_axes(self):
    combined = replace(self.state(True, True), experimental_enabled=True)
    self.assertEqual(rgba(axis_status_color(combined)), (218, 111, 37, 255))
    self.assertEqual(rgba(axis_status_color(replace(combined, longitudinal_active=False))), (10, 186, 181, 255))
    self.assertEqual(rgba(axis_status_color(replace(combined, lateral_active=False))), (255, 105, 180, 255))
    self.assertEqual(rgba(axis_status_color(replace(combined, lateral_active=False, longitudinal_active=False))), (18, 40, 57, 255))

  def test_both_profile_compositions_use_axis_border_and_fixtures_remain_combined(self):
    engaged_fixture = reference_onroad("onroad_engaged_no_camera")
    self.assertTrue(engaged_fixture.lateral_active and engaged_fixture.longitudinal_active)
    disengaged_fixture = reference_onroad("onroad_disengaged_no_camera")
    self.assertFalse(disengaged_fixture.lateral_active or disengaged_fixture.longitudinal_active)
    for lateral, longitudinal in ((False, False), (True, False), (False, True), (True, True)):
      state = self.state(lateral, longitudinal)
      for profile in (Profile.LARGE, Profile.COMPACT):
        with self.subTest(profile=profile, lateral=lateral, longitudinal=longitudinal):
          view = onroad.OnroadView.__new__(onroad.OnroadView)
          object.__setattr__(view, "fonts", NS(profile=profile, draw=Mock(), measure=Mock(return_value=NS(width=100, height=30))))
          view.camera_layer = Mock()
          view.extra_overlays = None
          view.alert = Mock()
          view.torque_bar = Mock()
          view.unified_speed = Mock()
          view.navigation = Mock()
          view.background_layer = None
          view.projection_viewport = None
          view._corner_cache = Mock()
          view.current_speed = Mock()
          view.steering_wheel = Mock()
          view.compact_hud = Mock()
          view.compact_sidebar = Mock()
          view._fade = None
          with patch.object(onroad.clip, "begin_scissor_mode"), patch.object(onroad.clip, "end_scissor_mode"), \
               patch.object(onroad.rl, "draw_rectangle_rec"), patch.object(onroad.rl, "draw_rectangle_gradient_v"), \
               patch.object(onroad.rl, "draw_rectangle_lines_ex"), patch.object(onroad.rl, "draw_rectangle"), \
               patch.object(onroad.rl, "draw_texture_ex"), patch.object(onroad.rl, "draw_rectangle_rounded_lines_ex") as border, \
               patch.object(onroad, "render_corner_hint"), patch.object(view, "_prepare_compact_fade"), \
               patch.object(view, "_slc_actions"):
            view.render(state)
          self.assertEqual(rgba(border.call_args.args[-1]), rgba(axis_status_color(state)))

  def test_stock_cruise_is_distinct_from_system_long_and_lateral(self):
    self.ui.CP = NS(carFingerprint='', openpilotLongitudinalControl=False, pcmCruise=True)
    self.ui.sm["carState"].cruiseState.enabled = True
    state = self.state(False, False)
    self.assertTrue(state.stock_cruise_active)
    self.assertTrue(state.cruise_active)
    self.assertFalse(state.longitudinal_active)
    self.assertEqual(rgba(axis_status_color(state)), (18, 40, 57, 255))
    fonts = Mock()
    fonts.measure.return_value = NS(width=20, height=10)
    fonts.vertical_ink.return_value = (0, 10)
    with patch("openpilot.starpilot.ui.onroad_large_widgets.draw_control_card"):
      UnifiedSpeedWidget(fonts).render(rl.Rectangle(30, 30, 1800, 1020), state)
    self.assertEqual(rgba(fonts.draw.call_args_list[0].args[-1]), rgba(rl.Color(188, 132, 255, 255)))
    compact = CompactHudRenderer(fonts, Path("/unused"))
    with patch("openpilot.starpilot.ui.onroad_compact_widgets.rl.draw_circle_gradient"):
      compact.render(state)
      compact.render(state)
    self.assertGreater(compact._set_speed_alpha.x, 0)
    self.assertEqual(compact._wheel_alpha.x, 0)
    self.ui.sm["carState"].canValid = False
    invalid = self.state(False, False)
    self.assertFalse(invalid.cruise_active)
    self.assertIsNone(invalid.cruise_kph)

  def test_lost_control_clears_steering_and_cruise_immediately_and_cancels_touch(self):
    self.ui.sm.put("controlsState", NS(longControlState="pid", lateralControlState=NS(which=lambda: "torqueState")))
    self.ui.sm.put("carOutput", NS(actuatorsOutput=NS(torque=0.4)))
    active = self.state(True, True)
    self.assertTrue(active.torque_source_available)
    self.assertAlmostEqual(active.torque_utilization, -0.4)
    requests = []
    touch = OnroadInput(requests.append, Profile.LARGE)
    touch.press(120, 530, active)
    self.ui.sm.logMonoTime["carControl"] = NOW - 300_000_000
    stale = self.adapter.build(ShellMode.ONROAD, now_ns=NOW).onroad
    self.assertFalse(stale.lateral_active or stale.longitudinal_active or stale.cruise_active)
    self.assertEqual(rgba(axis_status_color(stale)), (18, 40, 57, 255))
    touch.release(120, 530, stale)
    self.assertEqual(requests, [])
    fonts = Mock()
    fonts.measure.return_value = NS(width=20, height=10)
    compact = CompactHudRenderer(fonts, Path("/unused"))
    with patch.object(compact, "prepare"), patch("openpilot.starpilot.ui.onroad_compact_widgets.rl.draw_texture_pro"), \
         patch("openpilot.starpilot.ui.onroad_compact_widgets.rl.draw_circle_gradient"):
      compact.render(active)
      compact.render(active)
      self.assertGreater(compact._wheel_alpha.x, 0)
      self.assertGreater(compact._set_speed_alpha.x, 0)
      compact.render(stale)
    self.assertEqual(compact._wheel_alpha.x, 0)
    assert compact._last_cruise_ns is not None
    self.assertEqual(compact._set_speed_opacity(stale, compact._last_cruise_ns + 1), 0)
    self.assertEqual(compact._set_speed_opacity(stale, compact._last_cruise_ns + 150_000_001), 0)
    self.assertEqual(compact._set_speed_alpha.x, 0)
    torque = TorqueBarWidget()
    with patch("openpilot.starpilot.ui.onroad_torque.draw_polygon") as draw, \
         patch("openpilot.starpilot.ui.onroad_torque.rl.draw_circle"):
      torque.render(rl.Rectangle(0, 0, 476, 240), active, 536)
      self.assertGreater(torque._alpha_filter.x, 0)
      draw.reset_mock()
      torque.render(rl.Rectangle(0, 0, 476, 240), stale, 536)
      draw.assert_not_called()
    self.assertEqual(torque._alpha_filter.x, 0)

  def test_missing_actual_torque_output_stays_hidden_with_active_axes(self):
    self.ui.sm.put("controlsState", NS(longControlState="pid", lateralControlState=NS(which=lambda: "torqueState")))
    state = self.state(True, True)
    self.assertTrue(state.lateral_active)
    self.assertFalse(state.torque_source_available)
    torque = TorqueBarWidget()
    with patch("openpilot.starpilot.ui.onroad_torque.draw_polygon") as draw:
      torque.render(rl.Rectangle(0, 0, 476, 240), state, 536)
    draw.assert_not_called()
    self.assertEqual(torque._alpha_filter.x, 0)

  def test_pressed_control_cancels_on_axis_transition_even_with_fresh_transport(self):
    active = self.state(True, True)
    requests = []
    touch = OnroadInput(requests.append, Profile.LARGE)
    touch.press(120, 530, active)
    touch.release(120, 530, self.state(True, False))
    self.assertEqual(requests, [])
    self.assertFalse(replace(active, lateral_active=False, longitudinal_active=False).cruise_active)


if __name__ == "__main__":
  unittest.main()
