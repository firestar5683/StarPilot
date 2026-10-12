from collections import deque
from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest

from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent
from openpilot.starpilot.aol.wire import decode_intent, encode_intent


@pytest.mark.parametrize(('full_op', 'latched'), [(True, False), (True, True), (False, True)])
@pytest.mark.parametrize('successor', ['fresh_before_deadline', 'fresh_after_deadline', 'no_replacement'])
def test_source_cutoff_during_empty_drain_retains_only_original_output(full_op, latched, successor):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, controls, step, _, _ = case._ioniq_availability_callers(full_op=full_op)
      old, _, command = step(2, offset_ns=4_530_833, state_stamp=BASE,
                              intent_message=intent(BASE, 3, latched=latched), latched=latched)
      assert old.lateralActive and command.latActive
      assert old.longitudinalActive == full_op
      original = sd.pm.messages['aolAxisState'].as_builder().to_bytes()
      deadline = BASE + 34_530_833
      assert old.validUntilMonoTime == deadline
      clock = [BASE + 29_999_000]
      original_drain = sd.drain_axis_intent

      def drain(companion, **kwargs):
        result = original_drain(companion, **kwargs)
        assert companion.last_drain_count == 0
        clock[0] = BASE + 30_010_236
        return result

      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: clock[0]), \
           mock.patch.object(sd, 'drain_axis_intent', side_effect=drain), \
           mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update) as transition:
        axis, state, command = step(5, timeout=True, offset_ns=-1_000,
                                   intent_message=intent(BASE, 3, latched=latched), latched=latched)
      assert sd.aol_axis_publication_deferred and transition.call_count == 0
      assert sd.pm.messages['aolAxisState'].as_builder().to_bytes() == original
      assert axis.validUntilMonoTime == deadline and axis.sourceCarStateMonoTime == BASE
      assert axis.lateralActive and command.latActive and state.enabled == full_op
      assert axis.longitudinalActive == full_op and command.longActive == full_op
      assert not sd.aol_authority_lost

      if successor == 'no_replacement':
        axis, state, command = step(6, timeout=True, latched=latched,
                                   intent_message=intent(BASE, 3, latched=latched))
        assert not sd.aol_axis_publication_deferred
        assert not state.enabled and not axis.lateralActive and not axis.longitudinalActive
        assert not command.latActive and not command.longActive
        # Fresh input cannot restore ordinary LONG after a real disable.
        axis, state, command = step(7, latched=latched, native_request_long=False)
        assert not state.enabled and not axis.longitudinalActive and not command.longActive
      else:
        next_source = BASE + 31_546_896
        decision = BASE + (32_000_000 if successor == 'fresh_before_deadline' else 36_068_506)
        if successor == 'fresh_after_deadline':
          with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=deadline + 1):
            expired, _ = controls.state_control()
          assert not expired.latActive and not expired.longActive
        axis, state, command = step(6, offset_ns=decision - (BASE + 40_000_000), state_stamp=next_source,
                                   intent_message=intent(next_source, 4, latched=latched), latched=latched)
        assert axis.sourceCarStateMonoTime == next_source and axis.observedMonoTime == decision
        assert axis.validUntilMonoTime == decision + 30_000_000
        assert axis.lateralActive and command.latActive and state.enabled == full_op
        assert axis.longitudinalActive == full_op and command.longActive == full_op
        assert not sd.aol_authority_lost


@pytest.mark.parametrize('restriction', ['pause_lateral', 'pause_longitudinal', 'unlatched', 'unarmed', 'settings',
    'producer', 'sequence', 'future', 'invalid', 'deny_then_healthy', 'overrun'])
def test_post_drain_deferral_cannot_hide_new_intent_restriction(restriction):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers(full_op=True)
      old, _, _ = step(2, offset_ns=4_530_833, state_stamp=BASE, intent_message=intent(BASE, 3))
      assert old.lateralActive and old.longitudinalActive
      clock = [BASE + 29_999_000]
      stamp = BASE + 29_000_000
      message = intent(stamp, 4)
      decoded = decode_intent(message.aolIntentWire)
      changes = {'pause_lateral': {'pauseLateral': True}, 'pause_longitudinal': {'pauseLongitudinal': True},
                 'unlatched': {'allowedLatch': False}, 'unarmed': {'lateralArmed': False},
                 'settings': {'settingsQualified': False}, 'producer': {'producerSessionId': 'replacement'},
                 'sequence': {'sequence': 3}, 'future': {'observedMonoTime': BASE + 31_000_000},
                 'deny_then_healthy': {'pauseLateral': True}}
      if restriction in changes:
        message.aolIntentWire = encode_intent(replace(decoded, **changes[restriction]))
      if restriction == 'invalid':
        message.valid = False
      queue = deque([message.as_reader()])
      if restriction == 'deny_then_healthy':
        queue.append(intent(stamp + 1, 5).as_reader())
      elif restriction == 'overrun':
        queue = deque(intent(stamp + i, 4 + i).as_reader() for i in range(33))
      original_receive = messaging.recv_one_or_none
      original_drain = sd.drain_axis_intent

      def receive(sock):
        if sock is sd.aol_intent_companion.sock:
          return queue.popleft() if queue else None
        return original_receive(sock)

      def drain(companion, **kwargs):
        result = original_drain(companion, **kwargs)
        clock[0] = BASE + 30_010_236
        return result

      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: clock[0]), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd, 'drain_axis_intent', side_effect=drain):
        axis, state, command = step(5, timeout=True, offset_ns=-1_000, intent_message=intent(BASE, 3))
      assert not sd.aol_axis_publication_deferred
      assert not state.enabled and not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
