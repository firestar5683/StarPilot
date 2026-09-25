from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.runtime import current_native
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings


@pytest.mark.parametrize('mode', ['long_only', 'combined', 'combined_unarmed'])
def test_fresh_source_requests_long_before_delayed_native_ack_then_activates(mode):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, drive, _, _ = case._ioniq_availability_callers(full_op=True)
    old, _, command = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings(mode, BASE, 3))
    assert old.longitudinalActive and command.longActive
    old_deadline = old.validUntilMonoTime
    options = settings(mode, BASE, 3)
    options.update(native_request_long=False, long_allowed=False)
    axis, state, command = drive(5, timeout=True, offset_ns=5_399_000, **options)
    assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.softDisabling
    assert axis.sourceCarStateMonoTime == 0 and not axis.desiredLongitudinal
    assert not axis.longitudinalActive and not command.longActive
    # The newly accepted CS/intent arrives before the native 10Hz request/ACK.
    # Deliver actual healthy native OFF wire bytes; no axis/decision is mocked.
    fresh = BASE + 40_000_000
    options = settings(mode, fresh, 4)
    options.update(native_request_long=False, long_allowed=False)
    axis, state, command = drive(6, state_stamp=fresh, **options)
    native = current_native(sd.sm, sd.CP, now_ns=axis.observedMonoTime, axis_session_id=sd.aol_session_id)
    assert native is not None and not native.requestedLongitudinal and not native.longitudinalAllowed
    assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.enabled
    assert axis.sourceCarStateMonoTime == fresh and axis.desiredLongitudinal
    assert not axis.longitudinalActive and not command.longActive
    assert not sd.aol_authority_lost and not getattr(sd, 'aol_availability_long_inhibit', False)
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    assert not sd.events.contains(fixture.ET.ENABLE)
    # Panda's next actual wire ACK grants only the new current source.
    newer = BASE + 50_000_000
    axis, state, command = drive(7, state_stamp=newer, **settings(mode, newer, 5))
    native = current_native(sd.sm, sd.CP, now_ns=axis.observedMonoTime, axis_session_id=sd.aol_session_id)
    assert native is not None and native.requestedLongitudinal and native.longitudinalAllowed
    assert state.enabled and axis.desiredLongitudinal and axis.longitudinalActive and command.longActive
    assert axis.sourceCarStateMonoTime == newer and axis.validUntilMonoTime > old_deadline
    assert not sd.events.contains(fixture.ET.ENABLE)
    assert old.validUntilMonoTime == old_deadline
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=axis.validUntilMonoTime + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
