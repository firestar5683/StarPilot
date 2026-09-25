from collections import deque
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest

from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.starpilot.aol.intent_companion import IntentCompanion
from openpilot.starpilot.aol.tests.test_carstate_queue import message
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent


@pytest.mark.parametrize('count', [0, 1, 30, 31, 32, 33])
def test_real_intent_budget_requires_observed_quiescence(count):
  wires = deque(intent(BASE + index, index + 1).as_reader() for index in range(count))
  companion = IntentCompanion(object())
  with mock.patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none',
                  side_effect=lambda sock: wires.popleft() if wires else None):
    result = companion.drain(max_messages=32)
  assert companion.last_drain_count == min(count, 32)
  assert result == (count < 32)
  assert companion.last_drain_ok == result
  assert len(wires) == max(0, count - 32)
  assert companion.integrity_epoch == (0 if count < 32 else 1)


@pytest.mark.parametrize('last_count', [0, 1, 2])
def test_shared_31_then_remaining_one_budget(last_count):
  wires = deque(intent(BASE + index, index + 1).as_reader() for index in range(31))
  companion = IntentCompanion(object())
  owner: Any = SimpleNamespace(aol_step_intent_drain_count=0, aol_step_intent_drain_ok=True,
                          mark_loop_phase=lambda name: None)
  with mock.patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none',
                  side_effect=lambda sock: wires.popleft() if wires else None):
    assert SelfdriveD.drain_axis_intent(owner, companion, max_messages=32)
    assert owner.aol_step_intent_drain_count == 31
    wires.extend(intent(BASE + 31 + index, 32 + index).as_reader() for index in range(last_count))
    result = SelfdriveD.drain_axis_intent(owner, companion,
                                        max_messages=32 - owner.aol_step_intent_drain_count)
  assert result == (last_count == 0)
  assert owner.aol_step_intent_drain_count == 31 + min(1, last_count)
  assert owner.aol_step_intent_drain_ok == result
  assert len(wires) == max(0, last_count - 1)


def test_actual_wrapper_failure_stays_sticky_after_fresh_success():
  # An earlier real overrun followed by an ordinary successful drain must retain
  # the cumulative failure, while preserving each legacy caller's return value.
  wires = deque(intent(BASE + index, index + 1).as_reader() for index in range(32))
  companion = IntentCompanion(object())
  owner: Any = SimpleNamespace(aol_step_intent_drain_count=0, aol_step_intent_drain_ok=True,
                          mark_loop_phase=lambda name: None)
  with mock.patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none',
                  side_effect=lambda sock: wires.popleft() if wires else None):
    assert not SelfdriveD.drain_axis_intent(owner, companion)
    assert not owner.aol_step_intent_drain_ok
    wires.append(intent(BASE + 40, 40).as_reader())
    assert SelfdriveD.drain_axis_intent(owner, companion)
  assert companion.latest is not None
  assert companion.last_drain_ok and companion.latest[0] == BASE + 40
  assert owner.aol_step_intent_drain_count == 33
  assert not owner.aol_step_intent_drain_ok


def test_exhausted_budget_reads_no_extra_message_and_fails_closed():
  companion = IntentCompanion(object())
  with mock.patch('openpilot.starpilot.aol.intent_companion.messaging.recv_one_or_none') as receive:
    assert not companion.drain(max_messages=0)
  receive.assert_not_called()
  assert companion.last_drain_count == 0 and not companion.last_drain_ok
  assert companion.integrity_epoch == 1


@pytest.mark.parametrize(('initial_count', 'new_count'), [(0, 31), (0, 32), (1, 30), (1, 31), (31, 0), (31, 1)])
def test_source_budget_is_shared_and_refresh_never_waits(initial_count, new_count):
  existing = tuple(message(BASE + index) for index in range(initial_count))
  following = deque(message(BASE + initial_count + index) for index in range(new_count))
  owner: Any = SimpleNamespace(event_input_refresh_pending=True, aol_replay=True, axis_transport_required=True,
    car_state_envelopes=existing, car_state_queue_invalid=False, car_state_last_received_ns=BASE - 1,
    car_state_retained_source_ns=BASE - 1, car_state_sock=object(), aol_car_state_log_ns=BASE - 1,
    conditional_car_state_valid=True, aol_expired_healthy_source=False)
  owner.event_input_wait_ns = mock.Mock(side_effect=AssertionError('second blocking wait'))
  with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.REPLAY', False), \
       mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', return_value=BASE + 40_000_000), \
       mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none',
                  side_effect=lambda sock: following.popleft() if following else None) as receive:
    SelfdriveD.refresh_event_car_state(owner, message(BASE).carState, allow_wait=False)
  assert len(owner.car_state_envelopes) == initial_count + new_count
  assert owner.car_state_queue_invalid == (initial_count + new_count == 32)
  assert owner.conditional_car_state_valid == (initial_count + new_count < 32)
  assert receive.call_count <= 32 - initial_count
  owner.event_input_wait_ns.assert_not_called()
