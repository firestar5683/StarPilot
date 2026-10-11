from collections import deque
from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_carstate_queue import message
from openpilot.starpilot.aol.wire import IntentState, encode_intent


BASE = 10_020_000_000


def intent(stamp, sequence, *, latched=True):
  wire = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=stamp)
  wire.aolIntentWire = encode_intent(IntentState('authority-card', sequence, stamp, stamp,
    stamp + 200_000_000, latched, False, False, True, latched))
  return wire


@pytest.mark.parametrize('pulse', ['healthy', 'cancel', 'brake', 'permanent_eps', 'temporary_eps', 'invalid_envelope', 'reordered'])
def test_late_carstate_after_event_preamble_recomputes_exact_source_once(pulse):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers()
      step(2, offset_ns=4_012_592, state_stamp=BASE, intent_message=intent(BASE, 3))
      a, b, now = BASE, BASE + 27_819_143, BASE + 30_721_946
      late = fixture.car_state()
      late.vEgo = 25.0
      if pulse == 'cancel':
        late.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      elif pulse == 'brake':
        late.brakePressed = True
      elif pulse == 'permanent_eps':
        late.steerFaultPermanent = True
      elif pulse == 'temporary_eps':
        late.steerFaultTemporary = late.standstill = True
      queued = deque()
      original_status = sd.update_big_model_status
      original_receive = messaging.recv_one_or_none

      def finish_preamble():
        result = original_status()
        queued.append(message(a - 1 if pulse == 'reordered' else b, late, valid=pulse != 'invalid_envelope'))
        return result

      def receive(sock):
        return queued.popleft() if sock is sd.car_state_sock and queued else (
          None if sock is sd.car_state_sock else original_receive(sock))

      with mock.patch.object(sd, 'update_big_model_status', side_effect=finish_preamble), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd.car_events, 'update', wraps=sd.car_events.update) as car_events, \
           mock.patch.object(sd.excessive_actuation_check, 'update', wraps=sd.excessive_actuation_check.update) as excessive, \
           mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update) as transition:
        axis, _, command = step(5, offset_ns=721_946, state_stamp=a, intent_message=intent(b, 4))
      assert now - a == 30_721_946 and now - b == 2_902_803
      assert not queued and sd.CS_prev.vEgo == 25.0
      assert car_events.call_count == 2 and transition.call_count == 1
      assert excessive.call_count == (1 if sd.calibrated_pose is not None else 0)
      if pulse == 'healthy':
        assert axis.sourceCarStateMonoTime == b and sd.aol_last_intent.carStateLogMonoTime == b
        assert axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive
        assert sd.enabled and sd.active and not sd.aol_authority_lost
      else:
        if pulse == 'temporary_eps':
          assert axis.longitudinalActive and command.longActive and sd.enabled and sd.active
        else:
          assert not axis.longitudinalActive and not command.longActive
        if pulse not in ('brake',):
          assert not axis.lateralActive and not command.latActive
        if pulse in ('invalid_envelope', 'reordered'):
          assert axis.sourceCarStateMonoTime == 0 and not sd.conditional_car_state_valid
        if pulse == 'temporary_eps':
          assert log.OnroadEvent.EventName.steerTempUnavailableSilent in sd.events.names
          assert not sd.aol_authority_lost and sd.aol_last_intent.allowedLatch
        if pulse in ('cancel', 'brake'):
          assert not sd.enabled and not sd.events.contains(fixture.ET.ENABLE)


@pytest.mark.parametrize('outcome', ['next_frame', 'unlatched_next_frame', 'deadline', 'native_fault', 'validation_crosses_deadline',
                                    'withdrawal', 'expired_intent', 'unqualified_intent'])
def test_true_producer_gap_wait_never_extends_original_output_proof(outcome):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, controls, step, _, _ = case._ioniq_availability_callers()
      latched = outcome != 'unlatched_next_frame'
      axis, _, command = step(2, offset_ns=4_266_961, state_stamp=BASE, latched=latched,
                              intent_message=intent(BASE, 3, latched=latched))
      assert axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive
      deadline = BASE + 34_266_961
      assert axis.validUntilMonoTime == deadline
      original_sequence = axis.sequence
      now = [BASE + 30_254_367]
      next_stamp = BASE + 30_582_763
      queued, wires = deque(), deque()
      original_receive = messaging.recv_one_or_none

      def receive(sock):
        if sock is sd.car_state_sock:
          return queued.popleft() if queued else None
        if sock is sd.aol_intent_companion.sock:
          return wires.popleft() if wires else None
        return original_receive(sock)

      def burn_validation(*args, **kwargs):
        from openpilot.starpilot.aol.transport_pause import healthy_transport
        result = healthy_transport(*args, **kwargs)
        now[0] = deadline + 1
        return result

      def poll(timeout):
        assert 0 < timeout <= (deadline - now[0]) // 1_000_000
        assert sd.pm.messages['aolAxisState'].aolAxisState.sequence == original_sequence
        assert sd.pm.messages['aolAxisState'].aolAxisState.validUntilMonoTime == deadline
        # The already-created real consumer still holds the original envelope;
        # a source past30ms does not restamp or extend its publication lease.
        leased_command, _ = controls.state_control()
        assert leased_command.latActive and leased_command.longActive
        if outcome in ('next_frame', 'unlatched_next_frame'):
          now[0] = next_stamp + 100_000
          queued.append(message(next_stamp))
          wires.append(intent(next_stamp, 4, latched=latched).as_reader())
          return [sd.car_state_sock]
        now[0] = deadline + 1
        expired_command, _ = controls.state_control()
        assert not expired_command.latActive and not expired_command.longActive
        assert sd.pm.messages['aolAxisState'].aolAxisState.validUntilMonoTime == deadline
        return []

      poller = mock.Mock()
      poller.poll.side_effect = poll
      sd.car_state_poller = poller
      if outcome in ('withdrawal', 'expired_intent', 'unqualified_intent'):
        denied = IntentState('authority-card', 4, BASE, BASE,
          BASE + (1 if outcome == 'expired_intent' else 200_000_000),
          outcome != 'withdrawal', False, False, outcome != 'unqualified_intent', outcome != 'withdrawal')
        denied_wire = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=BASE)
        denied_wire.aolIntentWire = encode_intent(denied)
        wires.append(denied_wire.as_reader())
      with ExitStack() as validation:
        if outcome == 'validation_crosses_deadline':
          validation.enter_context(mock.patch('openpilot.selfdrive.selfdrived.selfdrived.healthy_transport',
                                               side_effect=burn_validation))
        with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]), \
             mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
             mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update) as transition:
          failed_axis, _, failed_command = step(5, timeout=True, offset_ns=254_367,
            intent_message=intent(BASE, 3, latched=latched), latched=latched, allowed=outcome != 'native_fault')
      assert transition.call_count == 1
      assert poller.poll.call_count == (1 if outcome in ('next_frame', 'unlatched_next_frame', 'deadline') else 0)
      if outcome in ('next_frame', 'unlatched_next_frame'):
        assert failed_axis.sourceCarStateMonoTime == next_stamp
        assert sd.aol_last_intent.carStateLogMonoTime == next_stamp
        assert failed_axis.lateralActive and failed_axis.longitudinalActive
        assert failed_command.latActive and failed_command.longActive and sd.enabled
        assert failed_axis.observedMonoTime == now[0]
        assert failed_axis.validUntilMonoTime == now[0] + 30_000_000
        assert failed_axis.sequence == original_sequence + 1
        assert sd.aol_last_intent.allowedLatch == latched and sd.aol_last_intent.lateralArmed == latched
      else:
        assert not failed_axis.lateralActive and not failed_axis.longitudinalActive
        assert not failed_command.latActive and not failed_command.longActive and not sd.enabled
        recovered, _, recovered_command = step(7, native_request_long=True)
        assert not recovered.longitudinalActive and not recovered_command.longActive and not sd.enabled


def test_fresh_late_source_expiring_during_remaining_event_work_still_withdraws():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers()
      step(2, offset_ns=4_012_592, state_stamp=BASE, intent_message=intent(BASE, 3))
      b = BASE + 27_819_143
      now = [BASE + 30_721_946]
      queued = deque()
      original_status = sd.update_big_model_status
      original_receive = messaging.recv_one_or_none
      original_check = sd.excessive_actuation_check.update

      def finish_preamble():
        result = original_status()
        queued.append(message(b))
        return result

      def receive(sock):
        return queued.popleft() if sock is sd.car_state_sock and queued else (
          None if sock is sd.car_state_sock else original_receive(sock))

      def consume_remaining_budget(*args, **kwargs):
        result = original_check(*args, **kwargs)
        now[0] = b + 30_000_001
        return result

      with mock.patch.object(sd, 'update_big_model_status', side_effect=finish_preamble), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]), \
           mock.patch.object(sd.excessive_actuation_check, 'update', side_effect=consume_remaining_budget):
        axis, _, command = step(5, offset_ns=721_946, state_stamp=BASE, intent_message=intent(b, 4))
      assert not queued and now[0] - b == 30_000_001
      assert axis.sourceCarStateMonoTime == 0
      assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
      assert not sd.enabled
