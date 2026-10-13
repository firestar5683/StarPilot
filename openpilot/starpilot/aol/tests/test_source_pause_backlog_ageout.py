from collections import deque
from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent


@pytest.mark.parametrize('count', [2, 16])
def test_healthy_unpaired_raw_backlog_ageout_does_not_replace_ordinary_soft_countdown(count):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, step, _, _ = case._ioniq_availability_callers(full_op=True)
    old, _, _ = step(2, state_stamp=BASE, offset_ns=4_497_535, intent_message=intent(BASE, 3))
    deadline = old.validUntilMonoTime
    queue = deque(intent(BASE + 29_000_000 + index * 1_000, 4 + index).as_reader() for index in range(count))
    original_receive = messaging.recv_one_or_none

    def receive(sock):
      if sock is sd.aol_intent_companion.sock:
        return queue.popleft() if queue else None
      return original_receive(sock)

    with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one_or_none', side_effect=receive):
      axis, state, command = step(5, timeout=True, offset_ns=5_399_000, intent_message=intent(BASE, 3))
      assert not queue and sd.aol_step_intent_drain_count == count
      assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.softDisabling
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
      assert sd.state_machine.soft_disable_timer == 300
      # There is no new CS/raw packet, invalid burst, changed identity or native
      # fault. Each immutable raw receipt's ORIGINAL200ms lease is still current.
      axis, state, command = step(8, timeout=True, intent_message=intent(BASE, 3))
    assert sd.aol_step_intent_drain_count == 0
    assert sd.aol_intent_companion.raw_projections
    assert all(
      stamp > BASE and axis.observedMonoTime - stamp > 30_000_000 and value.validUntilMonoTime > axis.observedMonoTime
      for stamp, (value, _, _) in sd.aol_intent_companion.raw_projections.items()
    )
    assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.softDisabling
    assert sd.state_machine.soft_disable_timer == 299
    assert axis.sourceCarStateMonoTime == 0 and not sd.conditional_car_state_valid
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert log.OnroadEvent.EventName.commIssue in sd.events.names
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    assert not sd.aol_authority_lost and not getattr(sd, 'aol_availability_long_inhibit', False)
    assert not sd.events.contains(fixture.ET.ENABLE)
    assert old.validUntilMonoTime == deadline
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=deadline + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
