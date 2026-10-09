"""UI request messages through the real SLC decision runtime, with no IPC."""

from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR

import openpilot.cereal.messaging as messaging
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages
from openpilot.starpilot.speed_limits.runtime import Action, Runtime
from openpilot.starpilot.speed_limits.runtime_settings import parse
from openpilot.starpilot.speed_limits.tests.test_runtime_replay import ReplaySM
from openpilot.starpilot.ui.onroad_state import OnroadInput, OnroadState, SlcActionKind, SlcUiRequest, slc_controls, speed_limit_from_message
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.slc_action_dispatch import SlcActionDispatcher


START = 2_000_000_000


def replay_inputs() -> tuple[ReplaySM, object]:
  cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  data, _ = messages()
  source = messaging.new_message("slcDashboardObservation").slcDashboardObservation
  data["slcDashboardObservation"] = source
  sm = ReplaySM(data, START)
  car = sm["carState"]
  car.vCruise = 60.0
  car.vCruiseCluster = 60.0
  car.vEgoCluster = 20.0
  sm["carControl"].enabled = True
  sm["carControl"].longActive = True
  source.producerSessionId = "card-producer"
  source.carStateLogMonoTime = START
  source.status = "valid"
  source.speedMps = 25.0
  source.observedMonoTime = START - 100_000_000
  source.validUntilMonoTime = START + 5_000_000_000
  source.episode = 1
  return sm, cp


def ui_request(message, *, profile: Profile, x: int, y: int) -> SlcUiRequest:
  observation = speed_limit_from_message(message.slcState)
  view_state = OnroadState(True, False, 20.0, 60.0, observation,
                           longitudinal_active=True, slc_system_long_available=True)
  emitted: list[SlcUiRequest] = []

  def emit(request):
    if not isinstance(request, SlcUiRequest):
      raise AssertionError("Unexpected non-SLC touch request")
    emitted.append(request)

  touch = OnroadInput(emit, profile)
  touch.press(x, y, view_state)
  touch.release(x, y, view_state)
  if len(emitted) != 1:
    raise AssertionError("Visible SLC touch emitted no request")
  return emitted[0]


def publish_request(state, request: SlcUiRequest, now_ns: int):
  sent = []
  dispatcher = SlcActionDispatcher(NS(send=lambda service, message: sent.append((service, message))),
                                   lambda _: state, lambda: now_ns)
  if not dispatcher.dispatch(request):
    raise AssertionError("Current SLC presentation rejected the UI request")
  service, message = sent[0]
  if service != "slcAction":
    raise AssertionError("Wrong SLC action service")
  action = message.slcAction
  return Action(str(action.sessionId), int(action.sequenceId), int(action.decisionId),
                int(action.presentationId), str(action.kind))


class TestSlcUiRuntime(unittest.TestCase):
  def test_card_accept_produces_planner_receipt_and_bounded_command(self):
    sm, cp = replay_inputs()
    runtime = Runtime(parse({"SpeedLimitController": True, "SLCConfirmation": True,
                             "SLCConfirmationHigher": True, "SLCPriority1": "Dashboard"}), session_id="ui-accept")
    pending = runtime.step(sm, cp, now_ns=START).message
    self.assertTrue(pending.slcState.hasPending)
    request = ui_request(pending, profile=Profile.LARGE, x=120, y=630)
    self.assertEqual(request.kind, SlcActionKind.ACCEPT)
    action = publish_request(pending.slcState, request, START)
    sm.advance(START + 50_000_000)
    result = runtime.step(sm, cp, now_ns=START + 50_000_000, request=action)
    self.assertEqual(result.message.slcState.actionStatus, "accept")
    self.assertFalse(result.message.slcState.hasPending)
    self.assertIsNotNone(result.command)
    self.assertGreater(result.command.slcCruiseCommand.targetMps, 60.0 / 3.6)

  def test_visible_reject_then_use_limit_restores_rejected_presentation(self):
    sm, cp = replay_inputs()
    runtime = Runtime(parse({"SpeedLimitController": True, "SLCConfirmation": True,
                             "SLCConfirmationHigher": True, "SLCPriority1": "Dashboard"}), session_id="ui-reject")
    pending = runtime.step(sm, cp, now_ns=START).message
    reject = ui_request(pending, profile=Profile.COMPACT, x=380, y=205)
    self.assertEqual(reject.kind, SlcActionKind.REJECT)
    action = publish_request(pending.slcState, reject, START)
    sm.advance(START + 50_000_000)
    rejected = runtime.step(sm, cp, now_ns=START + 50_000_000, request=action)
    self.assertEqual(rejected.message.slcState.actionStatus, "reject")
    self.assertFalse(rejected.message.slcState.hasPending)
    self.assertIsNone(rejected.command)
    observation = speed_limit_from_message(rejected.message.slcState)
    view_state = OnroadState(True, False, 20.0, 60.0, observation,
                             longitudinal_active=True, slc_system_long_available=True)
    self.assertEqual(slc_controls(Profile.COMPACT, view_state), ())
    adopt = ui_request(rejected.message, profile=Profile.LARGE, x=150, y=590)
    self.assertEqual(adopt.kind, SlcActionKind.ADOPT)
    restore = publish_request(rejected.message.slcState, adopt, START + 50_000_000)
    sm.advance(START + 100_000_000)
    restored = runtime.step(sm, cp, now_ns=START + 100_000_000, request=restore)
    self.assertEqual(restored.message.slcState.actionStatus, "adopt")
    self.assertIsNotNone(restored.command)

  def test_same_accepted_limit_can_be_used_with_lower_selected_cruise(self):
    sm, cp = replay_inputs()
    runtime = Runtime(parse({"SpeedLimitController": True, "SLCPriority1": "Dashboard"}), session_id="ui-readopt")
    shown = runtime.step(sm, cp, now_ns=START).message
    self.assertTrue(shown.slcState.hasAccepted)
    self.assertAlmostEqual(shown.slcState.acceptedSpeedLimit, shown.slcState.speedLimit)
    request = ui_request(shown, profile=Profile.LARGE, x=150, y=590)
    self.assertEqual(request.kind, SlcActionKind.ADOPT)
    action = publish_request(shown.slcState, request, START)
    sm.advance(START + 50_000_000)
    result = runtime.step(sm, cp, now_ns=START + 50_000_000, request=action)
    self.assertEqual(result.message.slcState.actionStatus, "adopt")
    self.assertIsNotNone(result.command)

  def test_old_press_cannot_publish_after_new_runtime_presentation_or_staleness(self):
    sm, cp = replay_inputs()
    runtime = Runtime(parse({"SpeedLimitController": True, "SLCConfirmation": True,
                             "SLCConfirmationHigher": True, "SLCPriority1": "Dashboard"}), session_id="ui-stale")
    pending = runtime.step(sm, cp, now_ns=START).message
    old_touch = ui_request(pending, profile=Profile.LARGE, x=120, y=630)
    publisher = Mock()
    stale = SlcActionDispatcher(publisher, lambda _: pending.slcState, lambda: START + 200_000_000)
    self.assertFalse(stale.dispatch(old_touch))
    source = sm["slcDashboardObservation"]
    source.speedMps = 30.0
    source.observedMonoTime = START + 40_000_000
    source.episode = 2
    sm.advance(START + 50_000_000)
    changed = runtime.step(sm, cp, now_ns=START + 50_000_000).message
    self.assertNotEqual(changed.slcState.presentationId, pending.slcState.presentationId)
    fresh = SlcActionDispatcher(publisher, lambda _: changed.slcState, lambda: START + 50_000_000)
    self.assertFalse(fresh.dispatch(old_touch))
    publisher.send.assert_not_called()


if __name__ == "__main__":
  unittest.main()
