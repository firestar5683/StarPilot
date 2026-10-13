from collections import deque
from contextlib import ExitStack
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_carstate_queue import message
from openpilot.starpilot.aol.tests.test_long_only_input_wait import BASE, intent
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import intent as combined_intent


@pytest.mark.parametrize('validation_wait_ns', [0, 4_000_000])
def test_actual_refresh_preserves_first_late_attempt_but_never_repeats_it(validation_wait_ns):
  state = message(BASE).carState
  owner: Any = SimpleNamespace(event_input_refresh_pending=True, aol_replay=True, axis_transport_required=True,
    aol_event_input_reconcile=True, aol_event_input_wait_attempted=False, mark_loop_phase=lambda name: None,
    car_state_envelopes=(), car_state_queue_invalid=False, car_state_last_received_ns=BASE,
    car_state_retained_source_ns=BASE, car_state_sock=object(), aol_car_state_log_ns=BASE,
    conditional_car_state_valid=True, aol_expired_healthy_source=False)
  owner.event_input_wait_ns = mock.Mock(return_value=validation_wait_ns)
  owner.car_state_poller = mock.Mock()
  owner.car_state_poller.poll.return_value = []
  now = [BASE + 29_999_999]
  with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.REPLAY', False), \
       mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: now[0]), \
       mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', return_value=None):
    SelfdriveD.refresh_event_car_state(owner, state)
    assert not owner.aol_event_input_wait_attempted
    owner.event_input_wait_ns.assert_not_called()
    now[0] = BASE + 30_100_000
    SelfdriveD.refresh_event_car_state(owner, state)
    assert owner.aol_event_input_wait_attempted
    SelfdriveD.refresh_event_car_state(owner, state)
    SelfdriveD.refresh_event_car_state(owner, state)
  owner.event_input_wait_ns.assert_called_once_with(state, BASE + 30_100_000)
  assert owner.car_state_poller.poll.call_count == (1 if validation_wait_ns else 0)
  assert owner.aol_car_state_log_ns == BASE


@pytest.mark.parametrize('prior_count', [30, 31, 32])
def test_actual_event_wait_and_prior_wrapper_share_32_message_budget(prior_count):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers(full_op=True)
      old, _, command = step(2, offset_ns=5_323_004, state_stamp=BASE, intent_message=intent(BASE, 3),
                              latched=False, pause=True, native_request_lat=False, allowed=False)
      assert old.longitudinalActive and command.longActive and not command.latActive
      sd.aol_event_input_reconcile = True
      sd.aol_step_intent_drain_count = 0
      sd.aol_step_intent_drain_ok = True
      wires = deque(intent(BASE + index + 1, index + 4).as_reader() for index in range(prior_count))
      receive_count = [0]
      def receive(sock):
        assert sock is sd.aol_intent_companion.sock
        if wires:
          receive_count[0] += 1
          return wires.popleft()
        return None
      origin = BASE + 30_338_798
      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=origin):
        prior_ok = sd.drain_axis_intent(sd.aol_intent_companion)
        assert prior_ok == (prior_count < 32)
        fresh_stamp = BASE + 30_300_000
        wires.append(intent(fresh_stamp, 50).as_reader())
        wait = sd.event_input_wait_ns(sd.CS_prev, origin)
      assert receive_count[0] <= 32
      assert sd.aol_step_intent_drain_count == min(32, prior_count + 1)
      assert bool(wait) == (prior_count == 30)
      assert sd.aol_step_intent_drain_ok == (prior_count == 30)
      if wait:
        assert origin + wait == old.validUntilMonoTime
      assert len(wires) == (1 if prior_count == 32 else 0)


def test_actual_step_final_admission_cannot_hide_failure_inside_last_refresh():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers(full_op=True)
      old, _, command = step(2, state_stamp=BASE, offset_ns=4_497_535, intent_message=combined_intent(BASE, 3))
      assert old.lateralActive and old.longitudinalActive and command.longActive
      original_refresh = sd.refresh_event_car_state
      original_receive = messaging.recv_one_or_none
      wires = deque()
      injected = [False]
      def receive(sock):
        if sock is sd.aol_intent_companion.sock:
          return wires.popleft() if wires else None
        return original_receive(sock)
      def refresh(state, **kwargs):
        result = original_refresh(state, **kwargs)
        if getattr(sd, 'aol_event_intent_drained', None) is True and not injected[0]:
          injected[0] = True
          wires.extend(combined_intent(BASE + 1 + index, 4 + index).as_reader() for index in range(32))
          assert not sd.drain_axis_intent(sd.aol_intent_companion)
          assert not sd.aol_step_intent_drain_ok
        return result
      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive), \
           mock.patch.object(sd, 'refresh_event_car_state', side_effect=refresh):
        axis, state, command = step(3, state_stamp=BASE + 10_000_000,
                                   intent_message=combined_intent(BASE + 10_000_000, 4))
      assert injected[0]
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive and not state.enabled
