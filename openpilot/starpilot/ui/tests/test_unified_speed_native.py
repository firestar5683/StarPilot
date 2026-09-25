"""Real planner decisions through native SlcState and the unified onroad card."""
from dataclasses import replace
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pyray as rl
from openpilot.starpilot.ui.onroad_large_widgets import UnifiedSpeedWidget

from openpilot.starpilot.speed_limits.runtime import Runtime
from openpilot.starpilot.speed_limits.runtime_settings import parse
from openpilot.starpilot.ui.tests.test_slc_ui_runtime import START, replay_inputs, ui_request, publish_request
from openpilot.starpilot.ui.onroad_state import OnroadState, OnroadInput, speed_limit_from_message
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.unified_speed_presentation import resolve_unified_speed


class UnifiedNativeTest(unittest.TestCase):
  def test_real_pending_and_accept_source_survive_native_roundtrip(self):
    sm, cp = replay_inputs()
    runtime = Runtime(parse({'SpeedLimitController': True, 'SLCConfirmation': True,
                             'SLCConfirmationHigher': True, 'SLCPriority1': 'Dashboard'}), session_id='unified-native')
    self.assertTrue(cp.openpilotLongitudinalControl)
    pending = runtime.step(sm, cp, now_ns=START).message
    self.assertEqual(pending.slcState.pendingSource, 'dashboard')
    obs = speed_limit_from_message(pending.slcState)
    state = OnroadState(True, False, 20, 60, obs, metric=True, longitudinal_active=True,
                        slc_system_long_available=bool(cp.openpilotLongitudinalControl))
    self.assertEqual((resolve_unified_speed(state).posted_text, resolve_unified_speed(state).source), ('90', 'dashboard'))
    # Hidden MAX moves the sign tap to its actual visible top row.
    hidden = replace(state, appearance=replace(state.appearance, hide_max_speed=True))
    emitted=[]
    touch=OnroadInput(emitted.append, Profile.LARGE)
    touch.press(120, 180, hidden)
    touch.release(120, 180, hidden)
    self.assertEqual(len(emitted), 1)
    action=publish_request(pending.slcState, emitted[0], START)
    sm.advance(START + 50_000_000)
    accepted=runtime.step(sm, cp, now_ns=START + 50_000_000, request=action).message
    self.assertEqual(accepted.slcState.acceptedSource, 'dashboard')
    self.assertFalse(accepted.slcState.hasPending)
    self.assertEqual(accepted.slcState.pendingSource, '')
    # A pending press cannot complete on the now-accepted decision.
    touch.press(120, 180, hidden)
    touch.release(120, 180, replace(hidden, speed_limit=speed_limit_from_message(accepted.slcState)))
    self.assertEqual(len(emitted), 1)

  def test_actual_lower_limit_publishes_cluster_target_and_limiting_evidence(self):
    sm, cp = replay_inputs()
    sm['slcDashboardObservation'].speedMps=12
    runtime=Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}),session_id='unified-cap')
    outcome=runtime.step(sm, cp, now_ns=START)
    message=outcome.message.slcState
    self.assertTrue(message.hasCeiling)
    self.assertTrue(message.hasEffectiveClusterTarget)
    self.assertTrue(message.isLimitingMaxSet)
    self.assertFalse(message.driverOverrideActive)
    self.assertAlmostEqual(message.effectiveClusterTarget, 12)
    state=OnroadState(True, False, 20, 60, speed_limit_from_message(message),metric=True,longitudinal_active=True)
    self.assertEqual(resolve_unified_speed(state).active_side,'slc')
    self.assertEqual(resolve_unified_speed(state).source,'dashboard')

  def test_pedal_flag_means_applied_override_not_merely_pressed_pedal(self):
    for limit, expected in ((25, False), (12, True)):
      with self.subTest(limit=limit):
        sm, cp = replay_inputs()
        sm['carState'].vEgo = 20
        sm['carState'].vEgoCluster = 20
        sm['carState'].gasPressed = True
        sm['slcDashboardObservation'].speedMps = limit
        runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}),
                          session_id='unified-pedal')
        message = runtime.step(sm, cp, now_ns=START).message.slcState
        self.assertEqual(message.driverOverrideActive, expected)
        self.assertEqual(message.acceptedSource, 'dashboard')
        shown = OnroadState(True, False, 20, 60, speed_limit_from_message(message),
                           metric=True, longitudinal_active=True)
        if expected:
          self.assertEqual(resolve_unified_speed(shown).active_side, 'none')

  def test_malformed_auxiliary_numeric_values_do_not_crash_large_renderer(self):
    sm, cp = replay_inputs()
    sm['slcDashboardObservation'].speedMps = 12
    runtime = Runtime(parse({'SpeedLimitController': True, 'SLCPriority1': 'Dashboard'}),session_id='unified-malformed')
    message = runtime.step(sm, cp, now_ns=START).message.slcState
    fonts = SimpleNamespace(draw=Mock(),measure=lambda *args: SimpleNamespace(width=10,height=10),
                            vertical_ink=lambda text, role, size: (size * .2, size * .8))
    widget = UnifiedSpeedWidget(fonts)
    for accepted,pending in ((-1,-2),(float('nan'),12),(12,float('inf'))):
      with self.subTest(accepted=accepted,pending=pending):
        message.hasAccepted = True
        message.acceptedSpeedLimit = accepted
        message.hasPending = True
        message.pendingSpeedLimit = pending
        observation = speed_limit_from_message(message)
        shown = OnroadState(True,False,20,60,observation,metric=True,longitudinal_active=True)
        with patch('openpilot.starpilot.ui.onroad_large_widgets.draw_control_card'):
          widget.render(rl.Rectangle(30,30,1800,1020),shown)
        if accepted == -1:
          self.assertEqual(resolve_unified_speed(shown).posted_text,'43')
        else:
          self.assertEqual(resolve_unified_speed(shown).mode,'max_only')


if __name__=='__main__': unittest.main()
