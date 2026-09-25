from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent
from openpilot.starpilot.aol.wire import decode_safety, encode_safety


@pytest.mark.parametrize('pedal', ['brake', 'regen'])
@pytest.mark.parametrize('steering', [False, True])
@pytest.mark.parametrize('scenario', ['renew', 'late_native_deny', 'native_wait', 'native_deny', 'new_edge', 'cancel', 'permanent_eps'])
def test_fresh_lateral_source_after_held_override_deadline(pedal, steering, scenario):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, controls, step, card, feedback = case._ioniq_availability_callers(full_op=False)

      def state(held=True):
        cs = fixture.car_state(brake=held and pedal == 'brake')
        cs.regenBraking = held and pedal == 'regen'
        cs.steeringPressed = steering
        return cs

      initial_held = scenario != 'new_edge'
      old, _, command = step(2, state_stamp=BASE, offset_ns=4_078_501, intent_message=intent(BASE, 3),
                             observed_state=state(initial_held), brake=initial_held and pedal == 'brake', steering=steering)
      assert old.lateralActive and command.latActive and not command.longActive and not sd.enabled
      assert old.validUntilMonoTime == BASE + 34_078_501
      now = [BASE + 29_900_000]
      original_health = sd.update_process_health

      def finish_preamble():
        result = original_health()
        now[0] = BASE + 32_700_000
        return result

      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]), \
           mock.patch.object(sd, 'update_process_health', side_effect=finish_preamble):
        retained, _, _ = step(5, timeout=True, offset_ns=-100_000, state_stamp=BASE, intent_message=intent(BASE, 3),
                              observed_state=state(initial_held), brake=initial_held and pedal == 'brake', steering=steering)
      assert sd.aol_axis_publication_deferred and retained.to_dict() == old.to_dict()
      fresh = BASE + 34_203_797
      now[0] = BASE + 37_000_473
      current = state()
      if scenario == 'cancel':
        current.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      elif scenario == 'permanent_eps':
        current.steerFaultPermanent = True
      visited = []
      original_update = sd._update_car_event_sample

      def update(sample, previous):
        visited.append((bool(sample.brakePressed), bool(sample.regenBraking)))
        return original_update(sample, previous)

      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]), \
           mock.patch.object(sd, '_update_car_event_sample', side_effect=update), \
           mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update) as transition:
        expired, _ = controls.state_control()
        assert not expired.latActive and not expired.longActive
        axis, result, command = step(5, state_stamp=fresh, offset_ns=7_000_473, intent_message=intent(fresh, 4),
                                    observed_state=current, brake=pedal == 'brake', steering=steering,
                                    native_request_lat=scenario != 'native_wait',
                                    allowed=scenario not in ('native_wait', 'native_deny'))
        assert transition.call_count == 1 and len(visited) == 1
        assert not result.enabled and not command.longActive and not axis.longitudinalActive
        assert old.validUntilMonoTime == BASE + 34_078_501
        if scenario in ('renew', 'late_native_deny'):
          assert axis.sourceCarStateMonoTime == fresh and axis.lateralActive and command.latActive
          assert str(axis.faultReason) == 'none' and not sd.aol_authority_lost
          assert axis.validUntilMonoTime == now[0] + 30_000_000
        else:
          assert not axis.lateralActive and not command.latActive
        if scenario in ('native_wait', 'native_deny'):
          assert axis.desiredLateral and str(axis.faultReason) == 'none'
        if scenario == 'new_edge':
          assert str(axis.faultReason) == 'critical'
        if scenario == 'cancel':
          assert log.OnroadEvent.EventName.buttonCancel in sd.events.names
        latch = feedback(now[0], axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'], state=sd.CS_prev.as_builder())
        if scenario in ('renew', 'late_native_deny', 'native_wait'):
          assert latch
        elif scenario == 'native_deny':
          assert not latch
        card.sm.update_msgs(now[0] / 1e9, [controls.pm.messages['carControl']])
        card.ci_initialized = card.ioniq6_long_prearmed = card.ioniq6_host_warmed = True
        card.ioniq6_long_lost = False
        card.ioniq6_keepalive = None
        captured = []

        def apply(control, _now):
          captured.append((bool(control.latActive), bool(control.longActive)))
          return control.actuators, []

        with mock.patch.object(card.CI, 'apply', side_effect=apply), mock.patch.object(card, 'publish_sendcan'):
          card.controls_update(sd.CS_prev, command)
        assert captured == [(scenario in ('renew', 'late_native_deny'), False)]

      if scenario in ('renew', 'late_native_deny'):
        # The native publisher may withdraw its expired request after SD took its
        # snapshot. Controls must reject the old positive ack immediately when read.
        now[0] += 500_000
        native = decode_safety(sd.sm['aolSafetyWire'])
        denied = messaging.new_message('aolSafetyWire', 0, valid=True, logMonoTime=now[0])
        denied.aolSafetyWire = encode_safety(replace(native, observedMonoTime=now[0], validUntilMonoTime=now[0] + 200_000_000,
                                                   requestedLateral=scenario == 'late_native_deny', lateralAllowed=False))
        controls.sm.update_msgs(now[0] / 1e9, [denied.as_reader()])
        with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]):
          denied_command, denied_log = controls.state_control()
          controls.publish(denied_command, denied_log)
          assert not denied_command.latActive and not denied_command.longActive
          sd.sm.update_msgs(now[0] / 1e9, [denied.as_reader()])
          remaining_latch = feedback(now[0], axis=sd.pm.messages['aolAxisState'],
                                     event=sd.pm.messages['onroadEvents'], state=sd.CS_prev.as_builder())
          assert remaining_latch == (scenario == 'renew')
          card.sm.update_msgs(now[0] / 1e9, [controls.pm.messages['carControl']])
          captured.clear()
          with mock.patch.object(card.CI, 'apply', side_effect=apply), mock.patch.object(card, 'publish_sendcan'):
            card.controls_update(sd.CS_prev, denied_command)
          assert captured == [(False, False)]

      if scenario in ('renew', 'native_wait'):
        # Re-requesting LAT retains no output until a new positive native ack.
        later = BASE + 48_000_000
        waiting, waiting_state, waiting_command = step(7, state_stamp=later, intent_message=intent(later, 5),
            observed_state=state(), brake=pedal == 'brake', steering=steering, native_request_lat=False, allowed=False)
        assert waiting.desiredLateral and not waiting.lateralActive and not waiting_command.latActive
        assert not waiting_state.enabled and not waiting_command.longActive and str(waiting.faultReason) == 'none'
        last = BASE + 60_000_000
        renewed, renewed_state, renewed_command = step(8, state_stamp=last, intent_message=intent(last, 6),
            observed_state=state(), brake=pedal == 'brake', steering=steering)
        assert renewed.lateralActive and renewed_command.latActive and not renewed.longitudinalActive
        assert not renewed_state.enabled and not renewed_command.longActive and not sd.events.contains(fixture.ET.ENABLE)

      elif scenario in ('native_deny', 'late_native_deny'):
        later = BASE + 48_000_000
        denied_axis, denied_state, denied_command = step(7, state_stamp=later,
            intent_message=intent(later, 5, latched=card.aol_card_intent.allowed_latch),
            observed_state=state(), brake=pedal == 'brake', steering=steering)
        assert not denied_axis.lateralActive and not denied_command.latActive
        assert not denied_state.enabled and not denied_command.longActive
