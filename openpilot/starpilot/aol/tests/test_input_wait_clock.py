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


@pytest.mark.parametrize('condition', [
  'timely', 'drain_at_deadline', 'drain_after_deadline', 'future_intent', 'pause_long',
  'producer_change', 'invalid_intent', 'latch_change', 'missing', 'late_poll', 'processing_deadline',
  'native_deadline', 'cancel', 'brake', 'pause_clear',
])
def test_last_refresh_intent_wait_uses_post_drain_clock(condition):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, controls, step, _, _ = case._ioniq_availability_callers(full_op=True)
      original, _, command = step(2, offset_ns=5_323_004, state_stamp=BASE, intent_message=intent(BASE, 3),
                                  latched=False, pause=True, native_request_lat=False, allowed=False)
      assert original.longitudinalActive and command.longActive and not command.latActive
      deadline = original.validUntilMonoTime
      assert deadline == BASE + 35_323_004
      now = [BASE + 29_900_000]
      wait_origin = BASE + 30_338_798
      next_stamp = BASE + 31_338_798
      queued, wires = deque(), deque()
      in_wait, injected = False, False
      clock_reads, waits, poll_windows = [], [], []
      original_receive = messaging.recv_one_or_none
      original_wait = sd.event_input_wait_ns
      original_update = sd._update_car_event_sample
      original_native = owner.current_native
      state = fixture.car_state()
      if condition == 'cancel':
        state.buttonEvents = [fixture.car.CarState.ButtonEvent(type=fixture.car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      elif condition == 'brake':
        state.brakePressed = True

      def clock():
        assert not clock_reads or now[0] >= clock_reads[-1]
        clock_reads.append(now[0])
        return now[0]

      def receive(sock):
        nonlocal injected
        if sock is sd.car_state_sock:
          return queued.popleft() if queued else None
        if sock is sd.aol_intent_companion.sock:
          if in_wait and not injected:
            injected = True
            now[0] = deadline if condition == 'drain_at_deadline' else deadline + 1 if condition == 'drain_after_deadline' else next_stamp + 100_000
            stamp = now[0] + 1 if condition == 'future_intent' else next_stamp
            wire = intent(stamp, 4, pause_lat=condition != 'pause_clear', pause_long=condition == 'pause_long',
                          producer='new-card' if condition == 'producer_change' else 'authority-card')
            if condition == 'invalid_intent':
              wire.valid = False
            if condition == 'latch_change':
              decoded = decode_intent(wire.aolIntentWire)
              assert decoded is not None
              wire.aolIntentWire = encode_intent(replace(decoded, allowedLatch=True))
            wires.append(wire.as_reader())
          return wires.popleft() if wires else None
        return original_receive(sock)

      def wait(sample, sampled_now):
        nonlocal in_wait
        in_wait = True
        try:
          result = original_wait(sample, sampled_now)
          waits.append((sampled_now, result, now[0]))
          return result
        finally:
          in_wait = False

      def car_update(sample, previous):
        result = original_update(sample, previous)
        # The first refresh precedes source expiry; ordinary event work crosses
        # it. Intent arrives during the final refresh's drain, before carState.
        now[0] = max(now[0], wait_origin)
        if condition == 'processing_deadline' and sample is not sd.CS_prev and poll_windows:
          now[0] = deadline + 1
        return result

      def native(*args, **kwargs):
        result = original_native(*args, **kwargs)
        if in_wait and condition == 'native_deadline':
          now[0] = deadline + 1
        return result

      def poll(timeout):
        absolute_end = now[0] + timeout * 1_000_000
        poll_windows.append((now[0], timeout, absolute_end))
        assert 0 < timeout and absolute_end <= min(deadline, wait_origin + 10_000_000)
        held, _ = controls.state_control()
        assert held.longActive and not held.latActive
        if condition == 'missing':
          now[0] = absolute_end
          return []
        now[0] = deadline + 1 if condition == 'late_poll' else now[0] + 100_000
        queued.append(message(next_stamp, state, valid=True))
        return [sd.car_state_sock]

      poller = mock.Mock()
      poller.poll.side_effect = poll
      sd.car_state_poller = poller
      with mock.patch.object(owner.time, 'monotonic_ns', side_effect=clock), \
           mock.patch.object(owner.messaging, 'recv_one_or_none', side_effect=receive), \
           mock.patch.object(owner, 'current_native', side_effect=native), \
           mock.patch.object(sd, 'event_input_wait_ns', side_effect=wait), \
           mock.patch.object(sd, '_update_car_event_sample', side_effect=car_update):
        axis, _, command = step(5, timeout=True, offset_ns=-100_000, intent_message=intent(BASE, 3),
                                latched=False, pause=True, native_request_lat=False, allowed=False)
      assert injected and len(waits) == 1
      assert waits[0][0] == wait_origin
      denied = condition in ('drain_at_deadline', 'drain_after_deadline', 'future_intent', 'pause_long',
                             'producer_change', 'invalid_intent', 'latch_change', 'native_deadline')
      assert poller.poll.call_count == (0 if denied else 1)
      if not denied:
        # Return duration remains anchored to the original caller timestamp.
        assert waits[0][0] + waits[0][1] == deadline
      if condition in ('timely', 'pause_clear'):
        assert axis.longitudinalActive and command.longActive and sd.enabled and sd.active
        assert not axis.lateralActive and not command.latActive
        assert axis.sourceCarStateMonoTime == next_stamp and now[0] < deadline
      else:
        assert not axis.longitudinalActive and not command.longActive
        assert not axis.lateralActive and not command.latActive
        assert not sd.enabled and not sd.active


@pytest.mark.parametrize('boundary', ['cap_inside', 'cap_at', 'cap_after', 'rollback', 'deadline_inside', 'deadline_at'])
def test_post_drain_clock_never_renews_original_wait(boundary):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers(full_op=True)
      axis, _, command = step(2, offset_ns=5_323_004, state_stamp=BASE, intent_message=intent(BASE, 3),
                              latched=False, pause=True, native_request_lat=False, allowed=False)
      assert axis.longitudinalActive and command.longActive
      origin = BASE + (30_338_798 if boundary.startswith('deadline') else 5_323_005)
      cap = min(axis.validUntilMonoTime, origin + 10_000_000)
      sampled = {'cap_inside': cap - 1, 'cap_at': cap, 'cap_after': cap + 1, 'rollback': origin - 1,
                 'deadline_inside': cap - 1, 'deadline_at': cap}[boundary]
      with mock.patch.object(owner.time, 'monotonic_ns', return_value=sampled), \
           mock.patch.object(owner.messaging, 'recv_one_or_none', return_value=None):
        wait = sd.event_input_wait_ns(sd.CS_prev, origin)
      assert wait == (cap - origin if boundary.endswith('inside') else 0)
      if wait:
        assert origin + wait == cap
        assert origin + wait - sampled == 1
