import unittest
from unittest import mock

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.selfdrived.events import Events
from openpilot.starpilot.aol.runtime import current_axis
from openpilot.starpilot.aol.tests import test_ioniq_availability as availability
from openpilot.starpilot.car.gm.aol import intent_disarming_fault


class TestFeedbackIntentBoundary(unittest.TestCase):
  _authority_callers = availability.IoniqAvailabilityTests._authority_callers
  _ioniq_availability_callers = availability.IoniqAvailabilityTests._ioniq_availability_callers

  def accepted_long_output(self):
    sd, controls, step, card, receive = self._ioniq_availability_callers()
    axis, _, command = step(2)
    self.assertTrue(axis.lateralActive and axis.longitudinalActive)
    self.assertTrue(command.latActive and command.longActive)
    proof = sd.pm.messages['aolAxisState']
    self.assertTrue(receive(10_020_000_000, axis=proof, event=sd.pm.messages['onroadEvents']))
    self.assertEqual(card.aol_transport_feedback.session, axis.sessionId)
    self.assertFalse(card.aol_transport_feedback.failed)
    return sd, controls, step, card, receive, proof

  @staticmethod
  def event_at(now, name=None):
    events = Events()
    if name is not None:
      events.add(name)
    message = messaging.new_message('onroadEvents', len(events), valid=True, logMonoTime=now)
    message.onroadEvents = events.to_msg()
    return message.as_reader()

  def assert_expired_commands_off(self, controls, proof, now):
    controls.sm.update_msgs(now / 1e9, [proof])
    self.assertIsNone(current_axis(controls.sm, now_ns=now))
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now):
      command, _ = controls.state_control()
    self.assertFalse(command.latActive or command.longActive)

  def test_expired_output_does_not_create_driver_intent_fault(self):
    with OpenpilotPrefix():
      sd, controls, step, card, receive, proof = self.accepted_long_output()
      # Advance healthy CAN/native through the real publisher, but retain the
      # independently sampled old output at Card. No fault event occurred.
      step(4, offset_ns=5_000_000)
      now = 10_051_000_000
      self.assertGreater(now, proof.aolAxisState.validUntilMonoTime)
      empty = self.event_at(now)
      self.assertFalse(intent_disarming_fault(card.CP, empty.onroadEvents, availability.car_state()))
      self.assert_expired_commands_off(controls, proof, now)
      self.assertTrue(receive(now, axis=proof, event=empty))
      self.assertFalse(card.aol_transport_feedback.failed)
      self.assertTrue(card.aol_card_intent.allowed_latch)
      self.assertFalse(card.aol_transport_feedback.qualified or card.aol_transport_feedback.awaiting)

  def test_absent_output_does_not_create_driver_intent_fault(self):
    with OpenpilotPrefix():
      _, controls, step, card, receive, proof = self.accepted_long_output()
      step(4, offset_ns=5_000_000)
      now = 10_051_000_000
      self.assert_expired_commands_off(controls, proof, now)
      # Missing output grants nothing; an empty actual event list is not a fault.
      card.sm.valid['aolAxisState'] = False
      self.assertTrue(receive(now, event=self.event_at(now)))
      self.assertTrue(card.aol_card_intent.allowed_latch)
      self.assertFalse(card.aol_transport_feedback.failed)

  def test_expired_output_never_hides_native_identity_or_real_faults(self):
    for fault in ('native_missing', 'native_denied', 'can_invalid', 'permanent_eps',
                  'session_restart', 'producer_restart', 'integrity_epoch', 'configuration',
                  'soft_event', 'immediate_event'):
      with self.subTest(fault=fault), OpenpilotPrefix():
        sd, controls, step, card, receive, proof = self.accepted_long_output()
        kwargs = {}
        if fault == 'native_missing':
          kwargs['native_valid'] = False
        elif fault == 'native_denied':
          kwargs['allowed'] = False
        step(4, offset_ns=5_000_000, **kwargs)
        now = 10_051_000_000
        changed = proof.as_builder()
        state = availability.car_state()
        name = None
        if fault == 'can_invalid':
          state.canValid = False
        elif fault == 'permanent_eps':
          state.steerFaultPermanent = True
        elif fault == 'session_restart':
          changed.aolAxisState.sessionId = 'restarted-selfdrive'
          changed.aolAxisState.faultSessionId = 'restarted-selfdrive'
        elif fault == 'producer_restart':
          changed.aolAxisState.intentProducerSessionId = 'restarted-card'
        elif fault == 'integrity_epoch':
          changed.aolAxisState.intentIntegrityEpoch += 1
        elif fault == 'configuration':
          pandas = messaging.new_message('pandaStates', len(sd.sm['pandaStates']), valid=True,
                                        logMonoTime=sd.sm.logMonoTime['pandaStates'])
          pandas.pandaStates = sd.sm['pandaStates']
          pandas.pandaStates[-1].safetyParam ^= 1
          sd.sm.update_msgs(now / 1e9, [pandas.as_reader()])
        elif fault == 'soft_event':
          name = log.OnroadEvent.EventName.commIssue
        elif fault == 'immediate_event':
          name = log.OnroadEvent.EventName.steerUnavailable
        self.assert_expired_commands_off(controls, changed.as_reader(), now)
        self.assertFalse(receive(now, axis=changed.as_reader(), event=self.event_at(now, name), state=state))
        self.assertFalse(card.aol_card_intent.allowed_latch)

  def test_sustained_brake_refreshes_healthy_lateral_baseline_before_output_gap(self):
    with OpenpilotPrefix():
      sd, controls, step, card, receive = self._ioniq_availability_callers()
      for tick in range(2, 32):
        axis, _, command = step(tick, brake=True, native_request_long=False)
        self.assertTrue(axis.lateralActive and command.latActive)
        self.assertFalse(axis.longitudinalActive or command.longActive)
        self.assertTrue(receive(10_000_000_000 + tick * 10_000_000,
                                axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'],
                                state=availability.car_state(brake=True)))
      proof = sd.pm.messages['aolAxisState']
      deadline = proof.aolAxisState.validUntilMonoTime
      now = deadline + 2_477_787
      step(34, offset_ns=2_477_787, brake=True, native_request_long=False)
      self.assert_expired_commands_off(controls, proof, now)
      self.assertTrue(receive(now, axis=proof, event=sd.pm.messages['onroadEvents'],
                              state=availability.car_state(brake=True)))
      self.assertTrue(card.aol_card_intent.allowed_latch)
      self.assertFalse(card.aol_transport_feedback.failed)
      self.assertEqual(proof.aolAxisState.validUntilMonoTime, deadline)
