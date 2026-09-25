"""State-bound SLC touch and request transport without a live PubMaster."""

from dataclasses import replace
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

from openpilot.starpilot.ui.onroad_state import (ObservationKind, OnroadInput, OnroadRequest, OnroadState,
                                                 SlcActionKind, SlcUiRequest, SpeedLimitObservation, slc_controls)
from openpilot.starpilot.ui.presentation import Profile
from openpilot.starpilot.ui.preview_home import reference_state
from openpilot.starpilot.ui.preview_settings import reference_settings_state
from openpilot.starpilot.ui.shell import ShellInput, ShellMode, ShellRequest, ShellSnapshot
from openpilot.starpilot.ui.slc_action_dispatch import SlcActionDispatcher


NOW = 10_000_000_000


def state(*, pending: bool = True, decision: int = 7, presentation: int = 9) -> OnroadState:
  observation = SpeedLimitObservation(kind=ObservationKind.VALID, source="dashboard", speed_limit_mps=22.0,
                                      pending_speed_limit_mps=22.0 if pending else None,
                                      accepted_speed_limit_mps=18.0, session_id="drive-session",
                                      decision_id=decision, presentation_id=presentation, action_enabled=True)
  return OnroadState(True, False, 20.0, 80.0, observation,
                     longitudinal_active=True, slc_system_long_available=True)


def native_state(*, pending: bool = True, session: str = "drive-session", decision: int = 7,
                 presentation: int = 9, now_ns: int = NOW) -> NS:
  return NS(sessionId=session, frameMonoTime=now_ns, enabled=True, observationKind="valid", source="dashboard",
            speedLimit=22.0, hasPending=pending, pendingSpeedLimit=22.0 if pending else 0.0,
            hasAccepted=True, acceptedSpeedLimit=18.0, decisionId=decision, presentationId=presentation,
            actionSequenceId=0)


class TestSlcTouch(unittest.TestCase):
  def test_shell_routes_visible_card_action_as_typed_slc_request(self):
    emitted: list[ShellRequest] = []
    shell = ShellInput(Profile.LARGE, emitted.append)
    snapshot = ShellSnapshot(ShellMode.ONROAD, reference_state(), reference_settings_state(), state())
    shell.press(120, 360, 0.0, snapshot)
    shell.release(120, 360, 0.1, snapshot)
    self.assertEqual(emitted[0].source, "slc")
    self.assertIsInstance(emitted[0].action, SlcUiRequest)

  def test_pending_card_accept_and_visible_reject_in_both_profiles(self):
    emitted: list[OnroadRequest | SlcUiRequest] = []
    large = OnroadInput(emitted.append, Profile.LARGE)
    large.press(120, 360, state())  # established speed-limit card tap
    large.release(120, 360, state())
    self.assertEqual(emitted[-1].kind, SlcActionKind.ACCEPT)
    large.press(210, 530, state())
    large.release(210, 530, state())
    self.assertEqual(emitted[-1].kind, SlcActionKind.REJECT)
    compact = OnroadInput(emitted.append, Profile.COMPACT)
    compact.press(240, 205, state())
    compact.release(240, 205, state())
    self.assertEqual(emitted[-1].kind, SlcActionKind.ACCEPT)
    self.assertEqual(len(slc_controls(Profile.COMPACT, state())), 2)

  def test_old_press_cannot_act_on_new_decision_or_presentation(self):
    emitted: list[OnroadRequest | SlcUiRequest] = []
    touch = OnroadInput(emitted.append, Profile.LARGE)
    touch.press(120, 360, state())
    touch.release(120, 360, state(decision=8))
    touch.press(210, 530, state())
    touch.release(210, 530, state(presentation=10))
    self.assertEqual(emitted, [])

  def test_adopt_same_accepted_limit_and_rejected_limit_remain_visible(self):
    emitted: list[OnroadRequest | SlcUiRequest] = []
    adoptable = state(pending=False)
    for profile, xy in ((Profile.LARGE, (150, 530)),):
      touch = OnroadInput(emitted.append, profile)
      touch.press(*xy, adoptable)
      touch.release(*xy, adoptable)
      self.assertEqual(emitted[-1].kind, SlcActionKind.ADOPT)
    self.assertEqual(slc_controls(Profile.COMPACT, adoptable), ())
    same_accepted = replace(adoptable, speed_limit=replace(adoptable.speed_limit, speed_limit_mps=18.0))
    previously_rejected = replace(adoptable, speed_limit=replace(adoptable.speed_limit, accepted_speed_limit_mps=None))
    self.assertEqual(slc_controls(Profile.LARGE, same_accepted)[0].label, "USE LIMIT")
    self.assertEqual(slc_controls(Profile.LARGE, previously_rejected)[0].label, "USE LIMIT")
    self.assertEqual(slc_controls(Profile.LARGE, replace(adoptable, longitudinal_active=False)), ())


class TestSlcDispatcher(unittest.TestCase):
  def test_publishes_schema_action_once_without_mutating_supplied_state(self):
    current = native_state()
    publisher = Mock()
    clock = [NOW]
    dispatcher = SlcActionDispatcher(publisher, lambda _: current, lambda: clock[0])
    request = SlcUiRequest(SlcActionKind.ACCEPT, "drive-session", 7, 9, 22.0)
    self.assertTrue(dispatcher.dispatch(request))
    service, message = publisher.send.call_args.args
    self.assertEqual(service, "slcAction")
    self.assertTrue(message.valid)
    self.assertEqual(str(message.slcAction.kind), "accept")
    self.assertEqual(message.slcAction.sessionId, "drive-session")
    self.assertEqual(message.slcAction.decisionId, 7)
    self.assertEqual(message.slcAction.presentationId, 9)
    self.assertGreaterEqual(message.slcAction.sequenceId, NOW)
    self.assertTrue(current.hasPending)
    self.assertFalse(dispatcher.dispatch(request))
    publisher.send.assert_called_once()

  def test_rechecks_session_decision_freshness_and_action_eligibility(self):
    current = native_state()
    publisher = Mock()
    dispatcher = SlcActionDispatcher(publisher, lambda _: current, lambda: NOW)
    request = SlcUiRequest(SlcActionKind.REJECT, "drive-session", 7, 9, 22.0)
    for mutation in ({"sessionId": "next-drive"}, {"decisionId": 8}, {"presentationId": 10},
                     {"frameMonoTime": NOW - 200_000_000}, {"hasPending": False}, {"enabled": False}):
      current = NS(**(vars(native_state()) | mutation))
      self.assertFalse(dispatcher.dispatch(request), mutation)
    publisher.send.assert_not_called()

  def test_adopt_requires_current_presentation_and_sequence_survives_restart(self):
    current = native_state(pending=False)
    current.actionSequenceId = NOW + 5
    publisher = Mock()
    dispatcher = SlcActionDispatcher(publisher, lambda _: current, lambda: NOW)
    request = SlcUiRequest(SlcActionKind.ADOPT, "drive-session", 7, 9, 22.0)
    self.assertTrue(dispatcher.dispatch(request))
    self.assertEqual(publisher.send.call_args.args[1].slcAction.sequenceId, NOW + 6)
    current = NS(**(vars(current) | {"speedLimit": 24.0}))
    self.assertFalse(dispatcher.dispatch(request))
    self.assertEqual(publisher.send.call_count, 1)

  def test_failed_publish_does_not_acknowledge_or_mutate_state(self):
    current = native_state()
    publisher = Mock()
    publisher.send.side_effect = OSError("isolated transport unavailable")
    dispatcher = SlcActionDispatcher(publisher, lambda _: current, lambda: NOW)
    request = SlcUiRequest(SlcActionKind.ACCEPT, "drive-session", 7, 9, 22.0)
    self.assertFalse(dispatcher.dispatch(request))
    self.assertEqual(current.actionSequenceId, 0)
    self.assertTrue(current.hasPending)


if __name__ == "__main__":
  unittest.main()
