"""Real planner decisions through native SlcState and the unified onroad card."""
from unittest.mock import Mock
from openpilot.starpilot.ui.presentation import BitmapFonts


from dataclasses import replace
import unittest
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch
import pyray as rl
from openpilot.starpilot.ui.onroad_large_widgets import UnifiedSpeedWidget

from openpilot.starpilot.speed_limits.runtime import Runtime
from openpilot.starpilot.speed_limits.runtime_settings import parse
from openpilot.starpilot.ui.tests.test_slc_ui_runtime import START, replay_inputs, publish_request
from openpilot.starpilot.ui.onroad_state import ObservationKind, OnroadState, OnroadInput, SpeedLimitObservation, speed_limit_from_message
from openpilot.starpilot.ui.presentation import FontRole, Profile
from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed


class UnifiedNativeTest(unittest.TestCase):
  def test_unset_max_and_state_changes_keep_units_and_details_consistent(self):
    observation = SpeedLimitObservation(ObservationKind.VALID, 'dashboard', 30 / 3.6,
                                       accepted_speed_limit_mps=30 / 3.6, accepted_adjusted_limit_mps=35 / 3.6,
                                       effective_cluster_target_mps=35 / 3.6, action_enabled=True)
    detail_y = []
    for cruise, active, pedal, status in ((None, False, False, 'Cruise off'),
                                        (35, False, False, 'Cruise off'),
                                        (35, True, True, 'Using accelerator'),
                                        (34.99, True, False, 'Matches set speed')):
      with self.subTest(cruise=cruise, pedal=pedal):
        state = OnroadState(active, False, 20, cruise, observation, metric=True,
                            longitudinal_active=active, longitudinal_overridden=pedal)
        fonts = SimpleNamespace(draw=Mock(), measure=lambda *args: SimpleNamespace(width=100, height=20),
                                vertical_ink=lambda text, role, size: (0, 20 if text == '–' else 80))
        with patch('openpilot.starpilot.ui.onroad_large_widgets.draw_control_card'), patch.object(rl, 'draw_line_ex'):
          UnifiedSpeedWidget(cast(BitmapFonts, fonts)).render(rl.Rectangle(30, 30, 1800, 1020), state)
        draws = {call.args[0]: call.args for call in fonts.draw.call_args_list}
        detail_y.append(draws['Road limit 30 +5'][4])
        self.assertEqual(draws[status][1:3], (FontRole.NORMAL, 30))
        if status == 'Matches set speed':
          color = draws[status][-1]
          self.assertEqual((color.r, color.g, color.b, color.a), (172, 190, 203, 255))
          self.assertIn('Using set speed', draws)
          self.assertNotIn('Above set speed', draws)
          self.assertNotIn('Matches speed limit', draws)
        if cruise is None:
          self.assertIn('Not set', draws)
          self.assertNotIn('Your ceiling', draws)
          self.assertEqual(sum(call.args[0] == 'km/h' for call in fonts.draw.call_args_list), 1)
          self.assertEqual(draws['–'][4], 75 + 72 + (80 - 20) / 2)
    self.assertEqual(len(set(detail_y)), 1)

  def test_screenshot_set_override_highlights_max_but_pedal_override_does_not(self):
    factor = 2.2369362921
    for basis, status, max_color in (('persistent', 'Overridden', (197, 163, 255, 255)),
                                    ('pedal', 'Using accelerator', (172, 190, 203, 255))):
      with self.subTest(basis=basis):
        observation = SpeedLimitObservation(ObservationKind.VALID, 'dashboard', 35 / factor,
                                           accepted_speed_limit_mps=35 / factor, accepted_adjusted_limit_mps=40 / factor,
                                           effective_cluster_target_mps=40 / factor, action_enabled=True,
                                           driver_override_active=True, override_basis=basis)
        state = OnroadState(True, False, 20, 40 / factor * 3.6, observation, metric=False, longitudinal_active=True)
        fonts = SimpleNamespace(draw=Mock(), measure=lambda *args: SimpleNamespace(width=100, height=20),
                                vertical_ink=lambda text, role, size: (0, size * .7))
        with patch('openpilot.starpilot.ui.onroad_large_widgets.draw_control_card'), patch.object(rl, 'draw_line_ex'):
          UnifiedSpeedWidget(cast(BitmapFonts, fonts)).render(rl.Rectangle(30, 30, 1800, 1020), state)
        draws = {call.args[0]: call.args for call in fonts.draw.call_args_list}
        color = draws['MAX SET'][-1]
        self.assertEqual((color.r, color.g, color.b, color.a), max_color)
        self.assertEqual('Using set speed' in draws, basis == 'persistent')
        self.assertIn(status, draws)
        self.assertNotIn('Above set speed', draws)
        self.assertNotIn('Matches speed limit', draws)
        self.assertEqual(sum(call.args[0] == '40' for call in fonts.draw.call_args_list), 2)
        self.assertIn('Road limit 35 +5', draws)
        color = draws['SLC LIMIT'][-1]
        self.assertEqual((color.r, color.g, color.b, color.a), (172, 190, 203, 255))

  def test_set_speed_cap_feedback_belongs_to_max_row(self):
    factor = 2.2369362921
    observation = SpeedLimitObservation(ObservationKind.VALID, 'dashboard', 40 / factor,
                                       accepted_speed_limit_mps=40 / factor, accepted_adjusted_limit_mps=45 / factor,
                                       effective_cluster_target_mps=45 / factor, action_enabled=True)
    state = OnroadState(True, False, 20, 40 / factor * 3.6, observation, metric=False, longitudinal_active=True)
    fonts = SimpleNamespace(draw=Mock(), measure=lambda *args: SimpleNamespace(width=100, height=20),
                            vertical_ink=lambda text, role, size: (0, size * .7))
    widget = UnifiedSpeedWidget(cast(BitmapFonts, fonts))
    with patch('openpilot.starpilot.ui.onroad_large_widgets.draw_control_card'), patch.object(rl, 'draw_line_ex'):
      widget.render(rl.Rectangle(30, 30, 1800, 1020), state)
    draws = {call.args[0]: call.args for call in fonts.draw.call_args_list}
    for label in ('MAX SET', 'Using set speed'):
      color = draws[label][-1]
      self.assertEqual((color.r, color.g, color.b, color.a), (197, 163, 255, 255))
    for label in ('SLC LIMIT',):
      color = draws[label][-1]
      self.assertEqual((color.r, color.g, color.b, color.a), (172, 190, 203, 255))
    self.assertLess(draws['Using set speed'][4], draws['SLC LIMIT'][4])
    self.assertIn('40', draws)
    self.assertIn('45', draws)
    self.assertIn('Road limit 40 +5', draws)
    self.assertIn('Above set speed', draws)
    self.assertEqual(draws['Above set speed'][1:3], (FontRole.NORMAL, 30))
    color = draws['Above set speed'][-1]
    self.assertEqual((color.r, color.g, color.b, color.a), (172, 190, 203, 255))

  def test_shared_limit_highlights_both_roles_and_preserves_both_numbers(self):
    observation = SpeedLimitObservation(ObservationKind.VALID, 'dashboard', 20,
                                       accepted_speed_limit_mps=20, accepted_adjusted_limit_mps=22,
                                       effective_cluster_target_mps=22, action_enabled=True)
    state = OnroadState(True, False, 20, 79.2, observation, metric=True, longitudinal_active=True)
    fonts = SimpleNamespace(draw=Mock(), measure=lambda *args: SimpleNamespace(width=100, height=20),
                            vertical_ink=lambda text, role, size: (0, size * .7))
    widget = UnifiedSpeedWidget(cast(BitmapFonts, fonts))
    with patch('openpilot.starpilot.ui.onroad_large_widgets.draw_control_card'), patch.object(rl, 'draw_line_ex'):
      widget.render(rl.Rectangle(30, 30, 1800, 1020), state)
    draws = fonts.draw.call_args_list
    for label in ('MAX SET', 'SLC LIMIT', 'Matches speed limit', 'Matches set speed'):
      color = next(call.args[-1] for call in draws if call.args[0] == label)
      self.assertEqual((color.r, color.g, color.b, color.a), (197, 163, 255, 255))
    self.assertEqual(sum(call.args[0] == '79' for call in draws), 2)
    self.assertEqual(sum(call.args[0] == 'Matches speed limit' for call in draws), 1)
    self.assertEqual(sum(call.args[0] == 'Matches set speed' for call in draws), 1)
    self.assertTrue(any(call.args[0] == 'Road limit 72 +7' for call in draws))

  def test_real_pending_and_accept_source_survive_native_roundtrip(self):
    sm, cp = replay_inputs()
    runtime = Runtime(
      parse({'SpeedLimitController': True, 'SLCConfirmation': True, 'SLCConfirmationHigher': True, 'SLCPriority1': 'Dashboard'}), session_id='unified-native'
    )
    self.assertTrue(cp.openpilotLongitudinalControl)
    pending = runtime.step(sm, cp, now_ns=START).message
    self.assertEqual(pending.slcState.pendingSource, 'dashboard')
    obs = speed_limit_from_message(pending.slcState)
    state = OnroadState(True, False, 20, 60, obs, metric=True, longitudinal_active=True, slc_system_long_available=bool(cp.openpilotLongitudinalControl))
    self.assertEqual((resolve_unified_speed(state).posted_text, resolve_unified_speed(state).source), ('90', 'dashboard'))
    # Hidden MAX moves the sign tap to its actual visible top row.
    hidden = replace(state, appearance=replace(state.appearance, hide_max_speed=True))
    emitted = []
    touch = OnroadInput(emitted.append, Profile.LARGE)
    touch.press(120, 630, hidden)
    touch.release(120, 630, hidden)
    self.assertEqual(len(emitted), 1)
    action = publish_request(pending.slcState, emitted[0], START)
    sm.advance(START + 50_000_000)
    accepted = runtime.step(sm, cp, now_ns=START + 50_000_000, request=action).message
    self.assertEqual(accepted.slcState.acceptedSource, 'dashboard')
    self.assertFalse(accepted.slcState.hasPending)
    self.assertEqual(accepted.slcState.pendingSource, '')
    # A pending press cannot complete on the now-accepted decision.
    touch.press(120, 630, hidden)
    touch.release(120, 630, replace(hidden, speed_limit=speed_limit_from_message(accepted.slcState)))
    self.assertEqual(len(emitted), 1)

  def test_actual_lower_limit_publishes_cluster_target_and_limiting_evidence(self):
    sm, cp = replay_inputs()
    sm['slcDashboardObservation'].speedMps = 12
    runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}), session_id='unified-cap')
    outcome = runtime.step(sm, cp, now_ns=START)
    message = outcome.message.slcState
    self.assertTrue(message.hasCeiling)
    self.assertTrue(message.hasEffectiveClusterTarget)
    self.assertTrue(message.isLimitingMaxSet)
    self.assertFalse(message.driverOverrideActive)
    self.assertAlmostEqual(message.effectiveClusterTarget, 12)
    state = OnroadState(True, False, 20, 60, speed_limit_from_message(message), metric=True, longitudinal_active=True)
    self.assertEqual(resolve_unified_speed(state).active_side, 'slc')
    self.assertEqual(resolve_unified_speed(state).source, 'dashboard')

  def test_pedal_flag_means_applied_override_not_merely_pressed_pedal(self):
    for limit, expected in ((25, False), (12, True)):
      with self.subTest(limit=limit):
        sm, cp = replay_inputs()
        sm['carState'].vEgo = 20
        sm['carState'].vEgoCluster = 20
        sm['carState'].gasPressed = True
        sm['slcDashboardObservation'].speedMps = limit
        runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}), session_id='unified-pedal')
        message = runtime.step(sm, cp, now_ns=START).message.slcState
        self.assertEqual(message.driverOverrideActive, expected)
        self.assertEqual(message.acceptedSource, 'dashboard')
        shown = OnroadState(True, False, 20, 60, speed_limit_from_message(message), metric=True, longitudinal_active=True)
        if expected:
          self.assertEqual(resolve_unified_speed(shown).active_side, 'none')

  def test_malformed_auxiliary_numeric_values_do_not_crash_large_renderer(self):
    sm, cp = replay_inputs()
    sm['slcDashboardObservation'].speedMps = 12
    runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}), session_id='unified-malformed')
    message = runtime.step(sm, cp, now_ns=START).message.slcState
    fonts = SimpleNamespace(
      draw=Mock(), measure=lambda *args: SimpleNamespace(width=10, height=10), vertical_ink=lambda text, role, size: (size * 0.2, size * 0.8)
    )
    widget = UnifiedSpeedWidget(Mock(spec=BitmapFonts, **vars(fonts)))
    for accepted, pending in ((-1, -2), (float('nan'), 12), (12, float('inf'))):
      with self.subTest(accepted=accepted, pending=pending):
        message.hasAccepted = True
        message.acceptedSpeedLimit = accepted
        message.hasPending = True
        message.pendingSpeedLimit = pending
        observation = speed_limit_from_message(message)
        shown = OnroadState(True, False, 20, 60, observation, metric=True, longitudinal_active=True)
        with patch('openpilot.starpilot.ui.onroad_large_widgets.draw_control_card'), patch.object(rl, 'draw_line_ex'):
          widget.render(rl.Rectangle(30, 30, 1800, 1020), shown)
        if accepted == -1:
          self.assertEqual(resolve_unified_speed(shown).posted_text, '43')
        else:
          self.assertEqual(resolve_unified_speed(shown).mode, 'max_only')


if __name__ == '__main__':
  unittest.main()
