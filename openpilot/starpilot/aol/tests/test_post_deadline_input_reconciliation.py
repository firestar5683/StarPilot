from collections import deque
from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_carstate_queue import message
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent
from openpilot.starpilot.aol.wire import decode_intent, encode_intent


@pytest.mark.parametrize(('full_op', 'latched'), [(True, False), (True, True), (False, True)])
@pytest.mark.parametrize('pulse', ['healthy', 'cancel_then_enable', 'brake_then_clear', 'regen_then_clear',
    'gas_then_clear', 'permanent_eps', 'invalid_then_valid', 'reordered', 'future_source', 'missing_source',
    'missing_intent', 'pause_lateral', 'pause_longitudinal', 'unlatched', 'settings', 'producer', 'sequence',
    'future_intent', 'intermediate_deny', 'native_deny', 'disabled', 'inhibited', 'owner_session', 'queue_overrun'])
def test_source_arriving_after_expired_proof_before_owner_decision(full_op, latched, pulse):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, controls, step, card, feedback = case._ioniq_availability_callers(full_op=full_op)
      old, _, command = step(2, state_stamp=BASE, offset_ns=6_218_996, intent_message=intent(BASE, 3, latched=latched))
      assert old.lateralActive and command.latActive
      assert old.validUntilMonoTime == BASE + 36_218_996
      fresh = BASE + 36_664_812
      now = BASE + 37_841_154
      clock_ns = [BASE + 29_000_000]
      assert old.validUntilMonoTime < fresh < now
      queue, wires = deque(), deque()
      original_receive = messaging.recv_one_or_none
      original_car_update = sd._update_car_event_sample
      original_health = sd.update_process_health
      visited = []
      injected = False
      sd.disengage_on_accelerator = True
      if pulse == 'disabled':
        sd.state_machine.state = log.SelfdriveState.OpenpilotState.disabled
        sd.enabled = sd.active = False
      elif pulse == 'inhibited':
        sd.aol_availability_long_inhibit = True
      elif pulse == 'owner_session':
        sd.aol_session_id = 'new-owner-session'
      burst = pulse in ('cancel_then_enable', 'brake_then_clear', 'regen_then_clear', 'gas_then_clear',
                        'invalid_then_valid', 'intermediate_deny')

      def receive(sock):
        if sock is sd.car_state_sock:
          return queue.popleft() if queue else None
        if sock is sd.aol_intent_companion.sock:
          return wires.popleft() if wires else None
        return original_receive(sock)

      def finish_preamble():
        result = original_health()
        # The original socket wait timed out while its source was still fresh.
        # Environment work then crossed the preceding proof's absolute deadline.
        clock_ns[0] = now
        expired, _ = controls.state_control()
        assert not expired.latActive and not expired.longActive
        return result

      def car_update(sample, previous):
        nonlocal injected
        visited.append(float(sample.vEgo))
        result = original_car_update(sample, previous)
        if not injected:
          injected = True
          late = fixture.car_state()
          late.cruiseState.available = True
          late.vEgo = 25.0
          if pulse == 'cancel_then_enable':
            late.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
          elif pulse == 'brake_then_clear':
            late.brakePressed = True
          elif pulse == 'regen_then_clear':
            late.regenBraking = True
          elif pulse == 'gas_then_clear':
            late.gasPressed = True
          elif pulse == 'permanent_eps':
            late.steerFaultPermanent = True
          stamp = BASE - 1 if pulse == 'reordered' else now + 1 if pulse == 'future_source' else fresh
          if pulse != 'missing_source':
            queue.append(message(stamp, late, valid=pulse != 'invalid_then_valid'))
          wire = intent(stamp, 2 if pulse == 'sequence' else 4, latched=latched)
          changes = {
            'pause_lateral': {'pauseLateral': True}, 'pause_longitudinal': {'pauseLongitudinal': True},
            'unlatched': {'allowedLatch': False, 'lateralArmed': False}, 'settings': {'settingsQualified': False},
            'producer': {'producerSessionId': 'replacement-card'}, 'future_intent': {'observedMonoTime': now + 1},
            'intermediate_deny': {'pauseLongitudinal': True},
          }.get(pulse, {})
          wire.aolIntentWire = encode_intent(replace(decode_intent(wire.aolIntentWire), **changes))
          if pulse != 'missing_intent':
            wires.append(wire.as_reader())
          if burst:
            clear = fixture.car_state()
            clear.cruiseState.available = True
            clear.vEgo = 26.
            clear.buttonEnable = pulse == 'cancel_then_enable'
            queue.append(message(fresh + 100_000, clear))
            wires.append(intent(fresh + 100_000, 5, latched=latched).as_reader())
          if pulse == 'queue_overrun':
            for index in range(1, 32):
              sample = fixture.car_state()
              sample.cruiseState.available = True
              sample.vEgo = 25. + index
              stamp = fresh + index * 10_000
              queue.append(message(stamp, sample))
              wires.append(intent(stamp, 4 + index, latched=latched).as_reader())
        return result

      sd.car_state_poller = mock.Mock()
      sd.car_state_poller.poll.return_value = []
      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: clock_ns[0]), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd, '_update_car_event_sample', side_effect=car_update), \
           mock.patch.object(sd, 'update_process_health', side_effect=finish_preamble), \
           mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update) as transition, \
           mock.patch.object(sd.excessive_actuation_check, 'update', wraps=sd.excessive_actuation_check.update) as excessive:
        axis, state, command = step(4, timeout=True, state_stamp=BASE, offset_ns=9_000_000, intent_message=intent(BASE, 3, latched=latched),
                                    allowed=pulse != 'native_deny', long_allowed=pulse != 'native_deny')
        print({'source': axis.sourceCarStateMonoTime, 'fault': str(axis.faultReason),
               'enabled': state.enabled, 'lat': command.latActive, 'long': command.longActive,
               'snapshot': sd.aol_intent_companion.last_snapshot, 'unread_carstate': len(queue)})
        if pulse == 'queue_overrun':
          assert not queue and len(visited) == 33 and sd.car_state_queue_invalid
          assert axis.sourceCarStateMonoTime == 0
        elif pulse != 'owner_session':
          assert not queue
          assert visited == ([20.0] if pulse == 'missing_source' else [20.0, 25.0, 26.0] if burst else [20.0, 25.0])
        assert transition.call_count == 1
        assert excessive.call_count == (1 if sd.calibrated_pose is not None else 0)
        assert sd.car_state_poller.poll.call_count == 0
        if pulse == 'healthy':
          assert axis.sourceCarStateMonoTime == fresh and sd.aol_last_intent.carStateLogMonoTime == fresh
          assert axis.lateralActive and command.latActive
          assert axis.longitudinalActive == full_op and command.longActive == full_op
          assert sd.enabled == full_op and not sd.aol_authority_lost
          assert axis.validUntilMonoTime == now + 30_000_000
        elif pulse == 'pause_lateral':
          assert not axis.lateralActive and not command.latActive
          assert axis.longitudinalActive == full_op and command.longActive == full_op
        elif pulse == 'unlatched':
          if not full_op:
            assert not axis.lateralActive and not command.latActive
        else:
          assert not axis.longitudinalActive and not command.longActive
          if pulse in ('cancel_then_enable', 'permanent_eps', 'invalid_then_valid', 'reordered', 'future_source',
                       'missing_source', 'missing_intent', 'settings', 'producer', 'sequence', 'future_intent',
                       'native_deny', 'owner_session', 'queue_overrun'):
            assert not axis.lateralActive and not command.latActive
          if pulse in ('cancel_then_enable', 'brake_then_clear', 'regen_then_clear', 'gas_then_clear',
                       'permanent_eps', 'disabled', 'inhibited'):
            assert not sd.enabled
          if pulse == 'cancel_then_enable':
            assert log.OnroadEvent.EventName.buttonCancel in sd.events.names and not sd.events.contains(fixture.ET.ENABLE)
          if pulse in ('brake_then_clear', 'regen_then_clear', 'gas_then_clear'):
            assert log.OnroadEvent.EventName.pedalPressed in sd.events.names
        assert old.validUntilMonoTime == BASE + 36_218_996
        feedback(now, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
        card.sm.update_msgs(now / 1e9, [controls.pm.messages['carControl']])
        card.ci_initialized = card.ioniq6_long_prearmed = card.ioniq6_host_warmed = True
        card.ioniq6_long_lost = False
        card.ioniq6_keepalive = None
        captured = []
        def apply(control, _now):
          captured.append((bool(control.latActive), bool(control.longActive)))
          return control.actuators, []
        with mock.patch.object(card.CI, 'apply', side_effect=apply), mock.patch.object(card, 'publish_sendcan'):
          card.controls_update(sd.CS_prev, command)
        assert captured == [(bool(command.latActive), bool(command.longActive))]

      if full_op and pulse in ('cancel_then_enable', 'brake_then_clear', 'regen_then_clear', 'gas_then_clear',
                               'permanent_eps', 'invalid_then_valid', 'reordered', 'future_source',
                               'missing_source', 'missing_intent', 'settings', 'producer', 'sequence',
                               'future_intent', 'native_deny', 'disabled', 'inhibited', 'queue_overrun'):
        fresh_after_disable = BASE + 50_000_000
        next_axis, next_state, next_command = step(7, state_stamp=fresh_after_disable,
                                                intent_message=intent(fresh_after_disable, 40, latched=latched))
        assert not next_axis.longitudinalActive and not next_command.longActive and not next_state.enabled
        assert not sd.events.contains(fixture.ET.ENABLE)
