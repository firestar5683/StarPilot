from collections import deque
from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest
from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent
from openpilot.starpilot.aol.wire import decode_intent, encode_intent


@pytest.mark.parametrize(
  ('count', 'sm_extra', 'deny_first'),
  [(2, False, False), (3, False, False), (16, False, False), (17, False, True), (31, False, True), (16, True, False), (16, True, True)],
)
def test_host_pause_accounts_for_each_raw_tuple_before_retaining_ordinary_state(count, sm_extra, deny_first):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, step, _, _ = case._ioniq_availability_callers(full_op=True)
    old, _, _ = step(2, state_stamp=BASE, offset_ns=4_497_535, intent_message=intent(BASE, 3))
    deadline = old.validUntilMonoTime
    frames = []
    for index in range(count):
      message = intent(BASE + 29_000_000 + index * 1_000, 4 + index)
      if deny_first and index == 0:
        message.aolIntentWire = encode_intent(replace(decode_intent(message.aolIntentWire), pauseLateral=True))
      frames.append(message.as_reader())
    queue = deque(frames)
    original_receive = messaging.recv_one_or_none

    def receive(sock):
      if sock is sd.aol_intent_companion.sock:
        return queue.popleft() if queue else None
      return original_receive(sock)

    conflated = intent(BASE + 29_000_000 + count * 1_000, 4 + count) if sm_extra else intent(BASE, 3)
    with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive):
      axis, state, command = step(5, timeout=True, offset_ns=5_399_000, intent_message=conflated)
    assert not queue
    assert sd.aol_step_intent_drain_count == count
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert old.validUntilMonoTime == deadline
    eligible = count <= 16 and not deny_first
    assert state.enabled == eligible
    if eligible:
      assert state.state == log.SelfdriveState.OpenpilotState.softDisabling
      assert str(axis.faultReason) == 'availabilityPause' and axis.sourceCarStateMonoTime == 0
      assert log.OnroadEvent.EventName.commIssue in sd.events.names
      assert not sd.aol_authority_lost and not getattr(sd, 'aol_availability_long_inhibit', False)
      assert not sd.events.contains(fixture.ET.ENABLE)
    else:
      assert not sd.aol_ordinary_source_pause
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=deadline + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
