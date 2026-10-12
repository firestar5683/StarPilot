from collections import deque
from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_carstate_queue import message
from openpilot.starpilot.aol.wire import IntentState, encode_intent

BASE = 10_020_000_000


def intent(stamp, sequence, *, pause_lat=True, pause_long=False, producer="authority-card"):
  wire = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=stamp)
  wire.aolIntentWire = encode_intent(IntentState(producer, sequence, stamp, stamp,
    stamp + 200_000_000, False, pause_lat, pause_long, True, False))
  return wire


@pytest.mark.parametrize('timing', [
  'timely', 'late_poll', 'processing_crosses_deadline', 'pre_refresh_cutoff', 'missing', 'cancel', 'brake',
  'invalid_envelope', 'temporary_eps', 'permanent_eps', 'native_denied', 'pause_clear', 'pause_set', 'pause_long',
  'native_invalid', 'panda_fault', 'session_change', 'producer_change', 'reordered', 'future_source', 'construction_crosses_deadline',
])
def test_long_only_wait_keeps_original_deadline_and_restrictions(timing):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      state = fixture.car_state()
      sd, controls, step, _, _ = case._ioniq_availability_callers(full_op=True)
      original, _, command = step(2, offset_ns=5_323_004, state_stamp=BASE, intent_message=intent(BASE, 3, pause_lat=timing != 'pause_set'),
                                  latched=False, pause=True, native_request_lat=False, allowed=False)
      assert not original.lateralActive and not command.latActive
      assert original.longitudinalActive and command.longActive and sd.enabled and sd.active
      assert not sd.aol_last_intent.allowedLatch
      assert sd.aol_last_intent.pauseLateral == (timing != 'pause_set')
      deadline = BASE + 35_323_004
      assert original.validUntilMonoTime == deadline
      now = [BASE + (29_900_000 if timing == 'pre_refresh_cutoff' else 30_338_798)]
      next_stamp = BASE + 32_614_311
      queued, wires = deque(), deque()
      original_receive = messaging.recv_one_or_none
      original_car_update = sd._update_car_event_sample
      original_authority = sd._update_steering_authority
      if timing == 'cancel':
        state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      elif timing == 'brake':
        state.brakePressed = True
      elif timing == 'temporary_eps':
        state.steerFaultTemporary = state.standstill = True
      elif timing == 'permanent_eps':
        state.steerFaultPermanent = True

      def receive(sock):
        if sock is sd.car_state_sock:
          return queued.popleft() if queued else None
        if sock is sd.aol_intent_companion.sock:
          return wires.popleft() if wires else None
        return original_receive(sock)

      def poll(timeout):
        assert 0 < timeout <= (deadline - now[0]) // 1_000_000
        held, _ = controls.state_control()
        assert not held.latActive and held.longActive
        if timing == 'missing':
          now[0] += timeout * 1_000_000
          return []
        now[0] = deadline + 1 if timing == 'late_poll' else next_stamp + 100_000
        if timing == 'late_poll':
          expired, _ = controls.state_control()
          assert not expired.latActive and not expired.longActive
        selected_stamp = BASE - 1 if timing == 'reordered' else now[0] + 1 if timing == 'future_source' else next_stamp
        queued.append(message(selected_stamp, state, valid=timing != 'invalid_envelope'))
        wires.append(intent(selected_stamp, 5, pause_lat=timing != 'pause_clear').as_reader())
        return [sd.car_state_sock]

      def car_update(sample, previous):
        result = original_car_update(sample, previous)
        if timing == 'processing_crosses_deadline':
          now[0] = deadline + 1
        return result

      def authority(sample):
        if timing == 'pre_refresh_cutoff':
          now[0] = max(now[0], BASE + 30_338_798)
        return original_authority(sample)

      original_new_message = messaging.new_message
      construction_crossed = False

      def new_message(*args, **kwargs):
        nonlocal construction_crossed
        result = original_new_message(*args, **kwargs)
        if args and args[0] == 'aolAxisState' and timing == 'construction_crosses_deadline' and not construction_crossed:
          construction_crossed = True
          now[0] = deadline + 1
        return result

      if timing == 'session_change':
        sd.aol_session_id = 'replacement-session'
      latest = intent(BASE, 3, pause_lat=timing != 'pause_set')
      if timing in ('pause_clear', 'pause_set', 'pause_long', 'producer_change'):
        latest = intent(BASE + 30_000_000, 4, pause_lat=timing != 'pause_clear',
                        pause_long=timing == 'pause_long', producer='changed-card' if timing == 'producer_change' else 'authority-card')
        wires.append(latest.as_reader())
      clock_reads = []

      def clock():
        assert not clock_reads or now[0] >= clock_reads[-1]
        clock_reads.append(now[0])
        return now[0]

      poller = mock.Mock()
      poller.poll.side_effect = poll
      sd.car_state_poller = poller
      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=clock), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.new_message', side_effect=new_message), \
           mock.patch.object(sd, '_update_steering_authority', side_effect=authority), \
           mock.patch.object(sd, '_update_car_event_sample', side_effect=car_update), \
           mock.patch.object(sd.state_machine, 'update', wraps=sd.state_machine.update) as transition:
        axis, _, command = step(5, timeout=True, offset_ns=338_798, intent_message=latest,
                                latched=False, pause=True, native_request_lat=False, allowed=False,
                                long_allowed=timing != 'native_denied', native_valid=timing != 'native_invalid', panda_fault=timing == 'panda_fault')
      if timing == 'pre_refresh_cutoff':
        # The source expires after the normal refresh cutoff. One early deferral
        # retains exactly the old packet, without another state transition.
        assert sd.aol_axis_publication_deferred and transition.call_count == 0
        assert axis.to_dict() == original.to_dict() and poller.poll.call_count == 0
        with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=deadline + 1):
          expired, _ = controls.state_control()
        assert not expired.latActive and not expired.longActive
        missing, _, missing_command = step(6, timeout=True, intent_message=latest,
          latched=False, pause=True, native_request_lat=False, allowed=False)
        assert not missing.longitudinalActive and not missing_command.longActive and not sd.enabled
        recovered, _, recovered_command = step(7, latched=False, pause=True, native_request_lat=False, allowed=False)
        assert not recovered.longitudinalActive and not recovered_command.longActive and not sd.enabled
        return
      assert transition.call_count == 1
      if timing in ('native_denied', 'pause_set', 'pause_long', 'native_invalid', 'panda_fault', 'session_change', 'producer_change', 'pre_refresh_cutoff'):
        assert poller.poll.call_count == 0
      else:
        assert poller.poll.call_count == 1
      # Expired output inhibits consumers; a fresh owner decision may renew an
      # engagement that was never revoked. Source/native/physical negatives stay off.
      renewed = timing in ('late_poll', 'processing_crosses_deadline', 'construction_crosses_deadline')
      if timing in ('timely', 'temporary_eps', 'pause_clear') or renewed:
        assert poller.poll.call_count == 1 and not queued
        assert axis.sourceCarStateMonoTime == next_stamp
        assert not axis.lateralActive and not command.latActive
        assert axis.longitudinalActive and command.longActive and sd.enabled and sd.active
        assert (now[0] > deadline) == renewed
        assert now[0] - axis.sourceCarStateMonoTime <= 30_000_000
        if timing == 'temporary_eps':
          assert fixture.log.OnroadEvent.EventName.steerTempUnavailableSilent in sd.events.names
      else:
        assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
        assert not sd.enabled and not sd.active
        recovered, _, recovered_command = step(7, latched=False, pause=True, native_request_lat=False, allowed=False)
        assert not recovered.longitudinalActive and not recovered_command.longActive and not sd.enabled


@pytest.mark.parametrize('long_only', [False, True])
@pytest.mark.parametrize('transition', ['held', 'cleared', 'new_pause', 'active_pause', 'no_pause'])
def test_wait_pause_veto_is_axis_scoped_and_preserves_unpause(long_only, transition):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers(full_op=long_only)

      def wire(stamp, sequence, inactive_pause, active_pause=False):
        sample = messaging.new_message('aolIntentWire', 0, valid=True, logMonoTime=stamp)
        sample.aolIntentWire = encode_intent(IntentState('authority-card', sequence, stamp, stamp, stamp + 200_000_000,
          not long_only, inactive_pause if long_only else active_pause,
          active_pause if long_only else inactive_pause, True, not long_only))
        return sample

      old_pause = transition in ('held', 'cleared', 'active_pause')
      axis, _, _ = step(2, offset_ns=5_323_004, state_stamp=BASE, intent_message=wire(BASE, 3, old_pause),
                         latched=not long_only, native_request_lat=not long_only or not old_pause, allowed=not long_only or not old_pause)
      assert axis.lateralActive == (not long_only or not old_pause) and axis.longitudinalActive == long_only
      now = BASE + 30_338_798
      latest = wire(BASE + 30_000_000, 4, transition in ('held', 'new_pause'), transition == 'active_pause')
      queue = deque([latest.as_reader()])
      original_receive = messaging.recv_one_or_none

      def receive(sock):
        if sock is sd.aol_intent_companion.sock:
          return queue.popleft() if queue else None
        return original_receive(sock)

      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=now):
        wait = sd.event_input_wait_ns(sd.CS_prev, now)
      assert not queue
      assert wait == (0 if transition in ('new_pause', 'active_pause') else axis.validUntilMonoTime - now)
