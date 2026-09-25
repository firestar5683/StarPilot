from collections import deque
from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest

from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.selfdrived import selfdrived as owner
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_carstate_queue import message
from openpilot.starpilot.aol.tests.test_long_only_input_wait import BASE, intent
from openpilot.starpilot.aol.wire import decode_intent, encode_intent


@pytest.mark.parametrize('mode', ['ordinary', 'held_gas', 'held_brake'])
@pytest.mark.parametrize('condition', ['timely', 'poll', 'missing', 'late', 'processing_late', 'pause', 'producer',
                                       'invalid_intent', 'invalid_source', 'future_source', 'reordered', 'cancel', 'brake_edge',
                                       'seq_rollback', 'settings', 'missing_intent', 'fcw', 'serialization_expiry',
                                       'second_source_expiry', 'first_final_deadline', 'drain_overrun', 'drain_deadline', 'future_intent',
                                       'same_source_serialization', 'same_source_serialization_deadline', 'burst_deny_permit'])
def test_final_handoff_full_owner(mode, condition):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      lateral_only = mode == 'held_brake'
      gas, brake = mode == 'held_gas', lateral_only
      sd, controls, step, card, card_receive = case._ioniq_availability_callers(full_op=not lateral_only)
      actual_update_msgs = controls.sm.update_msgs

      def joined_messages(timestamp, messages):
        # Replace the fixture's generic event payload in the same input batch;
        # do not add another SubMaster tick or skip its checks.
        event = sd.pm.messages.get('onroadEvents')
        if event is not None:
          messages = [sample for sample in messages if sample.which() != 'onroadEvents'] + [event]
        return actual_update_msgs(timestamp, messages)

      cleanup.enter_context(mock.patch.object(controls.sm, 'update_msgs', side_effect=joined_messages))

      def wire(stamp, sequence, **kwargs):
        result = intent(stamp, sequence, pause_lat=False, **kwargs)
        if lateral_only:
          decoded = decode_intent(result.aolIntentWire)
          result.aolIntentWire = encode_intent(replace(decoded, allowedLatch=True, lateralArmed=True))
        return result

      original, _, command = step(2, offset_ns=3_778_876, state_stamp=BASE, intent_message=wire(BASE, 3),
                                  latched=lateral_only, gas=gas, brake=brake)
      assert original.lateralActive and command.latActive
      assert original.longitudinalActive == (not lateral_only)
      assert command.longActive == (mode == 'ordinary')
      deadline = original.validUntilMonoTime
      now = [BASE + 29_900_000]
      queued, wires = deque(), deque()
      decisions, samples, states, deferred_proofs = [], [], [], []
      original_receive = messaging.recv_one_or_none
      original_decide = sd._decide_aol_axes
      original_update = sd._update_car_event_sample
      original_state = sd.state_machine.update
      next_stamp = BASE + 29_840_297
      final_time = BASE + 30_723_234
      if condition in ('serialization_expiry', 'second_source_expiry'):
        next_stamp = BASE + 2_000_000
      if condition == 'poll':
        next_stamp = final_time + 79_120
      next_state = fixture.car_state(brake=brake or condition == 'brake_edge')
      next_state.cruiseState.available = True
      next_state.gasPressed = gas
      if condition == 'cancel':
        next_state.buttonEvents = [fixture.car.CarState.ButtonEvent(type=fixture.car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      next_wire = wire(next_stamp, 2 if condition == 'seq_rollback' else 4, producer='other-card' if condition == 'producer' else 'authority-card')
      if condition == 'pause':
        decoded = decode_intent(next_wire.aolIntentWire)
        next_wire.aolIntentWire = encode_intent(replace(decoded, pauseLateral=True, pauseLongitudinal=True))
      if condition == 'future_intent':
        decoded = decode_intent(next_wire.aolIntentWire)
        next_wire.aolIntentWire = encode_intent(replace(decoded, observedMonoTime=final_time + 1_000_000))
      if condition == 'settings':
        decoded = decode_intent(next_wire.aolIntentWire)
        next_wire.aolIntentWire = encode_intent(replace(decoded, settingsQualified=False))
      if condition == 'invalid_intent':
        next_wire.valid = False
      stamp = now[0] + 20_000_000 if condition == 'future_source' else BASE - 1 if condition == 'reordered' else next_stamp
      next_message = message(stamp, next_state, valid=condition != 'invalid_source')

      def deliver():
        queued.append(next_message)
        if condition == 'burst_deny_permit':
          denied = wire(next_stamp, 4)
          decoded = decode_intent(denied.aolIntentWire)
          denied.aolIntentWire = encode_intent(replace(decoded, pauseLateral=True, pauseLongitudinal=True))
          wires.extend((denied.as_reader(), wire(next_stamp + 1, 5).as_reader()))
        elif condition == 'drain_overrun':
          wires.extend(wire(BASE + 2_000_000 + index, 4 + index).as_reader() for index in range(33))
        elif condition != 'missing_intent':
          wires.append(next_wire.as_reader())

      def receive(sock):
        if sock is sd.car_state_sock:
          return queued.popleft() if queued else None
        if sock is sd.aol_intent_companion.sock:
          if condition == 'drain_deadline' and len(decisions) == 2:
            now[0] = deadline + 1
          return wires.popleft() if wires else None
        return original_receive(sock)

      def decide(*args, **kwargs):
        value = original_decide(*args, **kwargs)
        decisions.append(value)
        if len(decisions) == 2:
          now[0] = (BASE + 29_900_000 if condition.startswith('same_source_serialization') else
                    deadline + 1 if condition == 'first_final_deadline' else final_time)
          if condition == 'fcw':
            sd.events.add(owner.EventName.fcw)
          if condition not in ('poll', 'missing', 'late'):
            deliver()
        elif len(decisions) == 4:
          if condition == 'processing_late':
            now[0] = deadline + 1
          elif condition == 'second_source_expiry':
            now[0] = next_stamp + 30_000_001
        return value

      def update(sample, previous):
        samples.append((sample.to_dict(), previous.to_dict()))
        return original_update(sample, previous)

      def state(events):
        before = (sd.state_machine.state, sd.state_machine.soft_disable_timer)
        result = original_state(events)
        states.append((before, (sd.state_machine.state, sd.state_machine.soft_disable_timer), events.names.copy()))
        return result

      actual_message = owner.messaging.new_message

      def construct(*args, **kwargs):
        result = actual_message(*args, **kwargs)
        if args and args[0] == 'aolAxisState' and len(decisions) == 2 and condition.startswith('same_source_serialization'):
          now[0] = deadline + 1 if condition.endswith('deadline') else final_time
        if args and args[0] == 'aolAxisState' and len(decisions) == 4 and condition == 'serialization_expiry':
          now[0] = next_stamp + 30_000_001
        return result

      actual_step = sd.step

      def run_normal_iterations():
        # These are two separate existing run-loop iterations. The production
        # owner does not recurse, add a tick, or process a sample a second time.
        actual_step()
        if sd.aol_axis_publication_deferred:
          retained = sd.pm.messages['aolAxisState'].aolAxisState
          deferred_proofs.append(retained.to_dict())
          assert retained.to_dict() == original.to_dict()
          assert len(states) == len(samples) == 1
          assert sd.sm.update.call_count == 1
          assert health.call_count == 1
          held, _ = controls.state_control()
          assert held.latActive and held.longActive == (mode == 'ordinary')
          card_receive(now[0], axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'], state=sd.CS_prev.as_builder())
          from openpilot.starpilot.aol.runtime import current_axis
          assert current_axis(card.sm, now_ns=now[0]) is not None
          sd.rk.monitor_time()
          if condition in ('missing', 'late'):
            now[0] = deadline + 1
            expired, _ = controls.state_control()
            assert not expired.latActive and not expired.longActive
            assert current_axis(card.sm, now_ns=now[0]) is None
          if condition == 'late':
            deliver()
          if condition == 'poll':
            now[0] = next_stamp + 1
            deliver()
          next_envelope = queued.popleft() if queued else None
          with mock.patch.object(owner.messaging, 'recv_one', return_value=next_envelope):
            actual_step()
          assert not sd.aol_axis_publication_deferred

      sd.sm.update.reset_mock()
      with mock.patch.object(sd, 'update_process_health', wraps=sd.update_process_health) as health, \
           mock.patch.object(owner.messaging, 'new_message', side_effect=construct), \
           mock.patch.object(owner.time, 'monotonic_ns', side_effect=lambda: now[0]), \
           mock.patch.object(owner.messaging, 'recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd, '_decide_aol_axes', side_effect=decide), \
           mock.patch.object(sd, '_update_car_event_sample', side_effect=update), \
           mock.patch.object(sd.state_machine, 'update', side_effect=state), \
           mock.patch.object(sd, 'step', side_effect=run_normal_iterations):
        axis, _, command = step(5, timeout=True, offset_ns=-100_000, intent_message=wire(BASE, 3),
                                latched=lateral_only, gas=gas, brake=brake)
      # A fresh source may renew the existing held-brake AOL-only override;
      # neither expiry of its predecessor nor repeated pedalPressed is a new edge.
      fresh_replacement = condition in ('late', 'processing_late')
      accepted = (condition in ('timely', 'poll', 'same_source_serialization') or fresh_replacement or
                  condition == 'brake_edge' and lateral_only)
      assert len(states) <= 2 and len(samples) <= 2
      assert sd.sm.update.call_count == health.call_count == len(states)
      if condition == 'burst_deny_permit':
        assert not deferred_proofs
        assert sd.aol_intent_companion.last_drain_count == 2
      if condition == 'drain_overrun':
        assert not deferred_proofs
        assert sd.aol_intent_companion.last_drain_count == 32
      if condition == 'fcw':
        assert not deferred_proofs
        assert any(event.name == owner.EventName.fcw for event in sd.pm.messages['onroadEvents'].onroadEvents)
      assert states[0][0] == states[0][1]
      assert all(owner.EventName.buttonEnable not in record[2] for record in states)
      if accepted:
        assert axis.sourceCarStateMonoTime == next_stamp
        assert axis.lateralActive and command.latActive
        assert axis.longitudinalActive == (not lateral_only)
        assert command.longActive == (mode == 'ordinary')
        assert len(samples) == 2
        assert (now[0] > deadline) == fresh_replacement
        assert now[0] - axis.sourceCarStateMonoTime <= owner.INTENT_MAX_AGE_NS
      else:
        assert not axis.longitudinalActive and not command.longActive
        if condition != 'brake_edge':
          assert not axis.lateralActive and not command.latActive


def test_deferred_tick_cannot_grant_conditional_mode_after_original_axis_expiry():
  from types import SimpleNamespace
  from openpilot.starpilot.conditional_mode.tests.test_status_consumer import TestModeTransport
  from openpilot.starpilot.conditional_mode.tests.test_projection import MONO, BOOT
  from openpilot.starpilot.conditional_mode.policy import ManualIntent

  case = TestModeTransport(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    case.setUp()
    case.params.put_bool('ExperimentalMode', True, block=True)
    case.owner.refresh(MONO, force=True)
    produced = MONO + 50_000_000
    now = produced + 35_000_000
    event, _, sm = case.produce(produced, intent=ManualIntent.FORCE_CHILL)
    device = messaging.new_message('deviceState', valid=True)
    device.deviceState.started = True
    device.deviceState.startedMonoTime = case.drive_id
    sm.payloads['deviceState'] = messaging.log_from_bytes(device.to_bytes()).deviceState
    sm.payloads['slcState'] = messaging.log_from_bytes(event.as_reader().as_builder().to_bytes()).slcState
    for service in ('deviceState', 'slcState'):
      sm.logMonoTime[service] = produced
      sm.recv_time[service] = produced / 1e9
      sm.seen[service] = sm.alive[service] = sm.valid[service] = True
    drive = owner.SelfdriveD.__new__(owner.SelfdriveD)
    drive.conditional_replay = drive.conditional_car_state_valid = drive.initialized = drive.enabled = drive.aol_replay = True
    drive.conditional_settings, drive.conditional_consumer = case.owner, case.consumer
    drive.aol_axis_decision = SimpleNamespace(longitudinal_active=True, lateral_active=False)
    drive.CP = SimpleNamespace(openpilotLongitudinalControl=True, passive=False)
    drive.sm = sm
    drive.aol_car_state_log_ns = produced - 2_000_000
    with mock.patch.object(owner, 'paired_clocks_ns', return_value=(now, BOOT + now - MONO, 1000)):
      drive.aol_axis_publication_deferred = False
      drive.update_conditional_mode(sm['carState'])
      assert drive.conditional_result.accepted and not drive.experimental_mode
      drive.aol_axis_publication_deferred = True
      drive.update_conditional_mode(sm['carState'])
      assert not drive.conditional_result.accepted and drive.experimental_mode
