"""Actual Card/intent recovery after an unmatched availability episode.

Factory CI/RI, actual SD/Controls and v2 native inventory use the existing
controlled IPC fixture. CAN parsing and receive transport are synthetic;
feedback validation and physical-button intent processing are unpatched.
"""
import unittest
from unittest import mock

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.starpilot.aol.tests import test_ioniq_availability as helpers


class LkasRetentionRecoveryTests(unittest.TestCase):
  _authority_callers = helpers.IoniqAvailabilityTests._authority_callers
  _ioniq_availability_callers = helpers.IoniqAvailabilityTests._ioniq_availability_callers

  def _terminal_episode(self):
    sd, controls, step, card, receive = self._ioniq_availability_callers()
    axis, _, command = step(2, car_output_valid=False)
    self.assertEqual(str(axis.faultReason), 'availabilityPause')
    self.assertFalse(command.latActive or command.longActive)
    self.assertTrue(receive(10_020_000_000, axis=sd.pm.messages['aolAxisState']))
    feedback = card.aol_transport_feedback
    self.assertTrue(feedback.retention_pending)
    self.assertEqual(feedback.retention_started_ns, 10_020_000_000)
    # The matching onroadEvents occurrence never reaches Card. A new, current
    # typed proof cannot extend this original bounded wait.
    axis, _, command = step(6, car_output_valid=False)
    self.assertEqual(str(axis.faultReason), 'availabilityPause')
    self.assertFalse(command.latActive or command.longActive)
    self.assertFalse(receive(10_060_000_000, axis=sd.pm.messages['aolAxisState']))
    self.assertTrue(feedback.failed)
    self.assertTrue(card.aol_card_intent._fault_inhibit)
    self.assertFalse(card.aol_card_intent.allowed_latch)
    return sd, controls, step, card, receive

  @staticmethod
  def _button(pressed):
    state = helpers.car_state()
    state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=pressed)]
    return state

  def _healthy(self, sd, step, receive, tick, *, state=None, event=True):
    axis, published, command = step(tick, native_request_long=False)
    self.assertEqual(str(axis.faultReason), 'none')
    self.assertTrue(axis.nativeAcknowledged)
    self.assertFalse(sd.enabled or published.enabled or axis.longitudinalActive or command.longActive)
    return receive(10_000_000_000 + tick * 10_000_000, axis=sd.pm.messages['aolAxisState'],
                   event=sd.pm.messages['onroadEvents'] if event else None, state=state)

  def test_terminal_withdrawal_then_healthy_neutral_requires_new_lkas_edge(self):
    with OpenpilotPrefix():
      sd, _, step, card, receive = self._terminal_episode()
      # The helper armed LKAS with a press; deliver its real release before
      # expecting another press to constitute a deliberate new edge.
      for tick in (7, 8):
        self.assertFalse(self._healthy(sd, step, receive, tick,
                                       state=self._button(False) if tick == 7 else None))
        self.assertFalse(card.aol_card_intent.allowed_latch)
      # Duplicate observations of the exact accepted healthy proof grant no
      # output or intent; the subsequent physical edge alone owns rearming.
      self.assertFalse(receive(10_081_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']))
      self.assertTrue(self._healthy(sd, step, receive, 9, state=self._button(True)))
      self.assertFalse(card.aol_transport_feedback.failed)
      self.assertEqual(card.aol_transport_feedback.retention_started_ns, 0)
      self.assertEqual(card.aol_transport_feedback.retention_event_ns, 0)
      self.assertFalse(card.aol_transport_feedback.retention_verified)
      self.assertFalse(sd.enabled or step(10, native_request_long=False)[2].longActive)
      self.assertTrue(self._healthy(sd, step, receive, 11, state=self._button(False)))
      self.assertFalse(self._healthy(sd, step, receive, 12, state=self._button(True)))
      self.assertFalse(self._healthy(sd, step, receive, 13, state=self._button(False)))
      self.assertTrue(self._healthy(sd, step, receive, 14, state=self._button(True)))
      self.assertFalse(sd.enabled)

  def test_held_lkas_during_recovery_requires_release_and_fresh_edge(self):
    with OpenpilotPrefix():
      sd, _, step, card, receive = self._terminal_episode()
      for tick in (7, 8, 9):
        self.assertFalse(self._healthy(sd, step, receive, tick, state=self._button(True)))
      self.assertFalse(card.aol_card_intent.allowed_latch)
      self.assertFalse(self._healthy(sd, step, receive, 10, state=self._button(False)))
      self.assertTrue(self._healthy(sd, step, receive, 11, state=self._button(True)))
      self.assertFalse(sd.enabled)

  def test_missing_fresh_events_cannot_remove_intent_fault_inhibition(self):
    with OpenpilotPrefix():
      sd, _, step, card, receive = self._terminal_episode()
      self.assertFalse(self._healthy(sd, step, receive, 7, event=False))
      self.assertTrue(card.aol_card_intent._fault_inhibit)
      self.assertFalse(self._healthy(sd, step, receive, 8, state=self._button(True), event=False))
      self.assertFalse(self._healthy(sd, step, receive, 9, state=self._button(False)))
      self.assertTrue(self._healthy(sd, step, receive, 10, state=self._button(True)))

  def test_invalid_stale_critical_or_unacknowledged_recovery_never_rearms(self):
    for failure in ('invalid_can', 'timeout', 'permanent', 'native_invalid', 'native_denied', 'panda_fault',
                    'critical', 'axis_stale', 'axis_future', 'source_missing', 'axis_invalid', 'foreign_session',
                    'foreign_fault_session', 'changed_vehicle', 'changed_cp', 'unacknowledged'):
      with self.subTest(failure=failure), OpenpilotPrefix():
        case = LkasRetentionRecoveryTests()
        try:
          sd, _, step, card, receive = case._terminal_episode()
          kwargs = {'native_request_long': False}
          if failure == 'native_invalid':
            kwargs['native_valid'] = False
          elif failure == 'native_denied':
            kwargs['allowed'] = False
          elif failure == 'panda_fault':
            kwargs['panda_fault'] = True
          elif failure == 'critical':
            kwargs['critical_event'] = log.OnroadEvent.EventName.controlsMismatch
          step(7, **kwargs)
          proof = sd.pm.messages['aolAxisState'].as_builder()
          state = case._button(True)
          if failure == 'invalid_can':
            state.canValid = False
          elif failure == 'timeout':
            state.canTimeout = True
          elif failure == 'permanent':
            state.steerFaultPermanent = True
          elif failure == 'axis_stale':
            proof.logMonoTime = proof.aolAxisState.observedMonoTime = 10_000_000_000
            proof.aolAxisState.validUntilMonoTime = 10_030_000_000
          elif failure == 'axis_future':
            proof.logMonoTime = proof.aolAxisState.observedMonoTime = 10_080_000_000
            proof.aolAxisState.validUntilMonoTime = 10_110_000_000
          elif failure == 'source_missing':
            proof.aolAxisState.sourceCarStateMonoTime = 0
          elif failure == 'axis_invalid':
            proof.valid = False
          elif failure == 'foreign_session':
            proof.aolAxisState.sessionId = proof.aolAxisState.faultSessionId = 'foreign-session'
          elif failure == 'foreign_fault_session':
            proof.aolAxisState.faultSessionId = 'foreign-session'
          elif failure in ('changed_vehicle', 'changed_cp'):
            changed = card.CP.as_reader().as_builder()
            if failure == 'changed_vehicle':
              changed.carFingerprint = 'unknown-vehicle'
            else:
              changed.flags ^= 1
            case.enterContext(mock.patch.object(card, 'CP', changed.as_reader()))
          elif failure == 'unacknowledged':
            proof.aolAxisState.nativeAcknowledged = False
          immutable = messaging.log_from_bytes(proof.to_bytes())
          self.assertFalse(receive(10_070_000_000, axis=immutable, event=sd.pm.messages['onroadEvents'], state=state))
          self.assertFalse(card.aol_card_intent.allowed_latch)
        finally:
          case.doCleanups()
