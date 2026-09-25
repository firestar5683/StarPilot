"""Actual custom Event acknowledgment and historical alert compatibility."""

from types import SimpleNamespace as NS
from dataclasses import replace
import time
import unittest
from unittest.mock import patch

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.consumer import ConsumerResult, ModeConsumer
from openpilot.starpilot.conditional_mode.effective_status import LIFETIME_NS, observation, publish_ack
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.status import ModeObservation


NOW = 100_000_000_000
SESSION = 'a' * 32
PLANNER = 'b' * 32


def proposal() -> ModeObservation:
  return ModeObservation(PLANNER, 7, NOW - 2_000_000, NOW + 30_000_000, NOW - 1_000_000_000,
                         NOW - 20_000_000, NOW - 5_000_000, 3, 'c' * 64, ModeChoice.CEM,
                         True, 'proposed', 'cem_speed', 3)


class TestEffectiveStatus(unittest.TestCase):
  def test_actual_selfdrived_publish_joins_emitted_state_and_clears_fallback(self):
    from openpilot.selfdrive.selfdrived.alertmanager import AlertManager
    from openpilot.selfdrive.selfdrived.events import Events
    from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD, State

    sent = {}
    daemon = SelfdriveD.__new__(SelfdriveD)
    daemon.enabled = daemon.active = daemon.experimental_mode = True
    daemon.personality = 'standard'
    self.enterContext(patch.object(daemon, "state_machine", NS(state=State.enabled), create=True))
    daemon.events = Events()
    daemon.events_prev = []
    daemon.AM = AlertManager()
    daemon.aol_replay = False
    daemon.conditional_replay = True
    daemon.conditional_ack_session = SESSION
    daemon.conditional_ack_sequence = 0
    sm = type('SM', (dict,), {'frame': 1})()
    self.enterContext(patch.object(daemon, 'sm', sm, create=True))
    current = time.monotonic_ns()
    sm['deviceState'] = NS(startedMonoTime=current - 1_000_000_000)
    self.enterContext(patch.object(daemon, 'pm', NS(send=lambda service, event: sent.__setitem__(service, event.to_bytes())), create=True))
    actual_proposal = replace(proposal(), observed_ns=current - 1_000_000, expires_ns=current + 30_000_000,
                              drive_id=current - 1_000_000_000, model_ns=current - 20_000_000,
                              car_state_ns=current - 5_000_000)
    daemon.conditional_result = ConsumerResult(True, True, 'proposed')
    daemon.conditional_consumer = ModeConsumer()
    daemon.conditional_consumer.last = actual_proposal
    daemon.publish_selfdriveState(NS(vEgo=12.0))
    state = messaging.log_from_bytes(sent['selfdriveState'])
    ack = messaging.log_from_bytes(sent['starpilotSelfdriveState'])
    value = observation(ack.starpilotSelfdriveState, ack.logMonoTime)
    self.assertIsNotNone(value)
    self.assertEqual(value.selfdrive_state_ns, state.logMonoTime)
    self.assertEqual(value.effective_experimental, state.selfdriveState.experimentalMode)
    self.assertEqual(value.reason, 'cem_speed')

    daemon.conditional_result = ConsumerResult(False, False, 'unavailable')
    daemon.experimental_mode = False
    daemon.publish_selfdriveState(NS(vEgo=12.0))
    fallback = messaging.log_from_bytes(sent['starpilotSelfdriveState'])
    value = observation(fallback.starpilotSelfdriveState, fallback.logMonoTime)
    self.assertIsNotNone(value)
    self.assertFalse(value.accepted)
    self.assertIsNone(value.reason)

  def test_serialized_accepted_receipt_binds_actual_mode_and_source_frame(self):
    event = publish_ack(session=SESSION, sequence=4, observed_ns=NOW, selfdrive_state_ns=NOW - 1_000_000,
                        drive_id=NOW - 1_000_000_000, effective_experimental=True,
                        result=ConsumerResult(True, True, 'proposed'), accepted_proposal=proposal())
    event.starpilotSelfdriveState.alertText1 = 'Keep hands on wheel'
    event.starpilotSelfdriveState.alertStatus = 'userPrompt'
    event.starpilotSelfdriveState.alertSound = 'prompt'
    decoded = messaging.log_from_bytes(event.to_bytes())
    self.assertEqual(decoded.starpilotSelfdriveState.alertText1, 'Keep hands on wheel')
    self.assertEqual(str(decoded.starpilotSelfdriveState.alertStatus), 'userPrompt')
    self.assertEqual(str(decoded.starpilotSelfdriveState.alertSound), 'prompt')
    value = observation(decoded.starpilotSelfdriveState, NOW)
    self.assertIsNotNone(value)
    self.assertTrue(value.accepted)
    self.assertEqual(value.choice, ModeChoice.CEM)
    self.assertEqual(value.selfdrive_state_ns, NOW - 1_000_000)
    self.assertEqual(value.planner_session, PLANNER)
    self.assertEqual(value.reason, 'cem_speed')
    self.assertIsNone(observation(decoded.starpilotSelfdriveState, NOW + LIFETIME_NS + 1))

  def test_fallback_clears_prior_planner_reason_and_malformed_receipts(self):
    event = publish_ack(session=SESSION, sequence=5, observed_ns=NOW, selfdrive_state_ns=NOW - 1_000_000,
                        drive_id=NOW - 1_000_000_000, effective_experimental=False,
                        result=ConsumerResult(False, False, 'unavailable'), accepted_proposal=proposal())
    raw = event.to_bytes()
    decoded = messaging.log_from_bytes(raw).starpilotSelfdriveState
    value = observation(decoded, NOW)
    self.assertIsNotNone(value)
    self.assertFalse(value.accepted)
    self.assertIsNone(value.reason)
    self.assertEqual(value.planner_sequence, 0)
    self.assertEqual(value.choice, ModeChoice.STOCK)
    for field, bad in (('version', 2), ('sessionId', ''), ('sequence', 0),
                       ('sourceSelfdriveStateMonoTime', NOW + 1), ('reason', 'stale reason')):
      changed = messaging.log_from_bytes(raw).as_builder()
      setattr(changed.starpilotSelfdriveState.conditionalModeAck, field, bad)
      with self.subTest(field=field):
        self.assertIsNone(observation(messaging.log_from_bytes(changed.to_bytes()).starpilotSelfdriveState, NOW))

  def test_accepted_flag_cannot_be_derived_from_cached_proposal(self):
    wrong_mode = publish_ack(session=SESSION, sequence=6, observed_ns=NOW, selfdrive_state_ns=NOW - 1_000_000,
                             drive_id=NOW - 1_000_000_000, effective_experimental=False,
                             result=ConsumerResult(False, True, 'proposed'), accepted_proposal=proposal())
    self.assertFalse(observation(messaging.log_from_bytes(wrong_mode.to_bytes()).starpilotSelfdriveState, NOW).accepted)
