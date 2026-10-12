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


@pytest.mark.parametrize('pulse', ['healthy', 'cancel', 'brake', 'permanent_eps', 'temporary_eps', 'invalid_envelope', 'reordered', 'aol_gas_permanent_eps'])
def test_late_carstate_during_environment_work_reaches_final_owners_once(pulse):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      held_gas = pulse == 'aol_gas_permanent_eps'
      sd, _, step, _, _ = case._ioniq_availability_callers(full_op=not held_gas)
      initial, _, initial_command = step(2, offset_ns=4_012_592, state_stamp=BASE, intent_message=intent(BASE, 3), gas=held_gas)
      if held_gas:
        assert initial.lateralActive and initial_command.latActive and sd.CS_prev.gasPressed
        assert not initial.longitudinalActive and not initial_command.longActive and not sd.enabled
      a, b, now = BASE, BASE + 27_819_143, BASE + 30_721_946
      late = fixture.car_state()
      late.vEgo = 25.0
      late.gasPressed = held_gas
      if pulse == 'cancel':
        late.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      elif pulse == 'brake':
        late.brakePressed = True
      elif pulse in ('permanent_eps', 'aol_gas_permanent_eps'):
        late.steerFaultPermanent = True
      elif pulse == 'temporary_eps':
        late.steerFaultTemporary = late.standstill = True
      queued = deque()
      original_status = sd.update_process_health
      original_receive = messaging.recv_one_or_none

      def finish_preamble():
        result = original_status()
        queued.append(message(a - 1 if pulse == 'reordered' else b, late, valid=pulse != 'invalid_envelope'))
        return result

      def receive(sock):
        return queued.popleft() if sock is sd.car_state_sock and queued else (
          None if sock is sd.car_state_sock else original_receive(sock))

      with mock.patch.object(sd, 'update_process_health', side_effect=finish_preamble), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd.car_events, 'update', wraps=sd.car_events.update) as car_events, \
           mock.patch.object(sd.excessive_actuation_check, 'update', wraps=sd.excessive_actuation_check.update) as excessive, \
           mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update) as transition:
        axis, _, command = step(5, offset_ns=721_946, state_stamp=a, intent_message=intent(b, 4), gas=held_gas)
      assert now - a == 30_721_946 and now - b == 2_902_803
      assert not queued and sd.CS_prev.vEgo == 25.0
      assert sd.CS_prev.gasPressed == held_gas
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


@pytest.mark.parametrize('operation', ['ordinary', 'aol_only', 'aol_only_gas'])
@pytest.mark.parametrize('timing', ['timely', 'late_poll', 'processing_crosses_deadline'])
def test_fresh_source_replaces_expired_output_without_restoring_disengagement(operation, timing):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      full_op = operation == 'ordinary'
      state = fixture.car_state()
      held_gas = operation == 'aol_only_gas'
      state.gasPressed = held_gas
      sd, controls, step, _, _ = case._ioniq_availability_callers(full_op=full_op)
      original, _, command = step(2, offset_ns=4_266_961, state_stamp=BASE, intent_message=intent(BASE, 3), observed_state=state, gas=held_gas)
      assert original.lateralActive and command.latActive
      assert original.longitudinalActive == full_op and command.longActive == full_op
      assert sd.enabled == full_op and sd.aol_last_intent.allowedLatch
      assert sd.CS_prev.gasPressed == held_gas
      deadline = BASE + 34_266_961
      assert original.validUntilMonoTime == deadline
      now = [BASE + 30_254_367]
      next_stamp = BASE + 30_582_763
      queued, wires = deque(), deque()
      original_receive = messaging.recv_one_or_none
      original_car_update = sd._update_car_event_sample

      def receive(sock):
        if sock is sd.car_state_sock:
          return queued.popleft() if queued else None
        if sock is sd.aol_intent_companion.sock:
          return wires.popleft() if wires else None
        return original_receive(sock)

      def poll(timeout):
        assert 0 < timeout <= (deadline - now[0]) // 1_000_000
        held, _ = controls.state_control()
        assert held.latActive and held.longActive == full_op
        now[0] = deadline + 1 if timing == 'late_poll' else next_stamp + 100_000
        if timing == 'late_poll':
          expired, _ = controls.state_control()
          assert not expired.latActive and not expired.longActive
        queued.append(message(next_stamp, state))
        wires.append(intent(next_stamp, 4).as_reader())
        return [sd.car_state_sock]

      def car_update(sample, previous):
        result = original_car_update(sample, previous)
        if timing == 'processing_crosses_deadline':
          now[0] = deadline + 1
          expired, _ = controls.state_control()
          assert not expired.latActive and not expired.longActive
        return result

      poller = mock.Mock()
      poller.poll.side_effect = poll
      sd.car_state_poller = poller
      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd, '_update_car_event_sample', side_effect=car_update), \
           mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update) as transition:
        axis, _, command = step(5, timeout=True, offset_ns=254_367, intent_message=intent(BASE, 3), gas=held_gas)
      assert sd.CS_prev.gasPressed == held_gas
      assert poller.poll.call_count == 1 and transition.call_count == 1 and not queued
      assert sd.aol_last_intent is not None and sd.aol_last_intent.allowedLatch and sd.aol_last_intent.lateralArmed
      assert now[0] - next_stamp < 30_000_000
      assert axis.sourceCarStateMonoTime == next_stamp and axis.lateralActive and command.latActive
      assert axis.longitudinalActive == full_op and command.longActive == full_op
      assert sd.enabled == full_op and not sd.aol_authority_lost
      assert axis.validUntilMonoTime > deadline
      if operation == 'aol_only_gas':
        for tick in range(7, 107):
          continued, _, continued_command = step(tick, observed_state=state, gas=held_gas, native_request_long=False)
          assert continued.lateralActive and continued_command.latActive
          assert sd.CS_prev.gasPressed
          assert not continued.longitudinalActive and not continued_command.longActive and not sd.enabled
          assert sd.aol_last_intent.allowedLatch and sd.aol_last_intent.lateralArmed


@pytest.mark.parametrize('latched', [False, True])
def test_route_4f_new_source_after_previous_output_deadline(latched):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, controls, step, _, _ = case._ioniq_availability_callers()
      prior, _, _ = step(2, offset_ns=4_322_384, state_stamp=BASE,
                         intent_message=intent(BASE, 3, latched=latched), latched=latched)
      now = BASE + 35_936_883
      source = BASE + 32_971_113
      assert now - prior.validUntilMonoTime == 1_614_499
      assert now - source == 2_965_770
      with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now):
        expired, _ = controls.state_control()
      assert not expired.latActive and not expired.longActive
      axis, state, command = step(5, offset_ns=5_936_883, state_stamp=source,
                                 intent_message=intent(source, 4, latched=latched), latched=latched)
      assert axis.sourceCarStateMonoTime == source
      assert axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive
      assert state.enabled and sd.enabled and sd.active
      assert not sd.aol_authority_lost
      assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
