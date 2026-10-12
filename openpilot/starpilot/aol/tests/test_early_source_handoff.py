from collections import deque
from contextlib import ExitStack
from unittest import mock
from dataclasses import replace
import pytest
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.cereal import messaging
from openpilot.selfdrive.selfdrived import selfdrived as owner
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_long_only_input_wait import BASE, intent
from openpilot.starpilot.aol.wire import decode_intent, encode_intent


@pytest.mark.parametrize('mode', ['ordinary', 'held_gas', 'lateral_gas', 'held_brake'])
@pytest.mark.parametrize('condition', ['timely', 'entry_expired', 'deadline', 'fcw', 'deny', 'physical_cancel', 'repeat'])
def test_early(mode, condition):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as stack:
    stack.callback(case.doCleanups)
    with OpenpilotPrefix():
      lateral = mode in ['lateral_gas', 'held_brake']
      gas = mode in ['lateral_gas', 'held_gas']
      brake = mode == 'held_brake'
      sd, controls, step, card, card_receive = case._ioniq_availability_callers(full_op=not lateral)
      actual_update_msgs = controls.sm.update_msgs

      def joined_messages(timestamp, messages):
        event = sd.pm.messages.get('onroadEvents')
        if event is not None:
          messages = [sample for sample in messages if sample.which() != 'onroadEvents'] + [event]
        return actual_update_msgs(timestamp, messages)

      stack.enter_context(mock.patch.object(controls.sm, 'update_msgs', side_effect=joined_messages))

      def wire(stamp, seq, deny=False):
        m = intent(stamp, seq, pause_lat=False)
        v = decode_intent(m.aolIntentWire)
        m.aolIntentWire = encode_intent(replace(v, allowedLatch=lateral, lateralArmed=lateral, pauseLateral=deny))
        return m

      original, _, cc = step(2, state_stamp=BASE, offset_ns=4_837_661, intent_message=wire(BASE, 3), gas=gas, brake=brake, steering=True, latched=lateral)
      assert original.lateralActive
      now = [BASE + (31_625_140 if condition == 'entry_expired' else 29_900_000)]
      old_update = sd.update_events
      old_receive = messaging.recv_one_or_none
      wires = deque()
      attempt = []
      old_defer = sd.defer_expired_axis_publication

      def receive(sock):
        if sock is sd.aol_intent_companion.sock:
          return wires.popleft() if wires else None
        return old_receive(sock)

      def events(cs):
        result = old_update(cs)
        now[0] = original.validUntilMonoTime + 1 if condition == 'deadline' else BASE + 31_625_140
        if condition == 'fcw':
          sd.events.add(owner.EventName.fcw)
        if condition == 'physical_cancel':
          sd.events.add(owner.EventName.buttonCancel)
        if condition == 'deny':
          wires.append(wire(BASE + 31_000_000, 4, True).as_reader())
        return result

      def defer(cs, initial):
        out = old_defer(cs, initial)
        attempt.append(out)
        return out

      with (
        mock.patch.object(owner.time, 'monotonic_ns', side_effect=lambda: now[0]),
        mock.patch.object(sd, 'update_events', side_effect=events),
        mock.patch.object(sd, 'defer_expired_axis_publication', side_effect=defer),
        mock.patch.object(messaging, 'recv_one_or_none', side_effect=receive),
      ):
        axis, state, command = step(5, timeout=True, offset_ns=-100_000, intent_message=wire(BASE, 3), gas=gas, brake=brake, steering=True, latched=lateral)
      if condition in ['timely', 'repeat']:
        assert axis.to_dict() == original.to_dict() and command.latActive
        assert command.longActive == (mode == 'ordinary')
        assert sd.aol_axis_publication_deferred and attempt == [True]
        if condition == 'repeat':
          # Next normal iteration gets no new source; the original deadline is
          # still unexpired and a second deferral may not retain it again.
          axis, _, command = step(5, timeout=True, offset_ns=2_000_000, intent_message=wire(BASE, 3), gas=gas, brake=brake, steering=True, latched=lateral)
          assert not sd.aol_axis_publication_deferred and not command.latActive and not command.longActive
      else:
        assert not sd.aol_axis_publication_deferred
        assert axis.faultReason != 'none' or not axis.lateralActive
        assert not command.latActive and not command.longActive
        if condition == 'fcw':
          assert owner.EventName.fcw in sd.events.names
