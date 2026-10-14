"""Host source expiry preserves intent without expired commands."""
from contextlib import ExitStack
import time
from unittest import mock

import pytest
from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings


@pytest.mark.parametrize('prior_lag', [False, True])
def test_actual_aol_only_host_lag_source_gap_preserves_only_armed_intent(prior_lag):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, controls, drive, card, receive = case._ioniq_availability_callers(full_op=False)
    old, state, command = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings('lateral_only', BASE, 3))
    assert old.lateralActive and command.latActive and not old.longitudinalActive and not command.longActive
    assert not state.enabled and not state.active and card.aol_card_intent.allowed_latch
    assert receive(BASE + 4_497_535, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    deadline = old.validUntilMonoTime
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=deadline + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
    source, sequence = BASE, 3
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      if prior_lag:
        source, sequence = BASE + 10_000_000, 4
        axis, state, command = drive(3, state_stamp=source, **settings('lateral_only', source, sequence))
        assert log.OnroadEvent.EventName.selfdrivedLagging in sd.events.names
        assert not axis.lateralActive and not command.latActive and not sd.aol_authority_lost
        assert not state.enabled and not state.active and not axis.longitudinalActive and not command.longActive
        assert receive(source, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      tick = 7 if prior_lag else 5
      now = BASE + (tick - 2) * 10_000_000 + 5_399_000
      axis, state, command = drive(tick, timeout=True, state_stamp=source, offset_ns=5_399_000,
                                    **settings('lateral_only', source, sequence))
      assert log.OnroadEvent.EventName.selfdrivedLagging in sd.events.names
      assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
      assert old.validUntilMonoTime == deadline < now
      assert not state.enabled and not state.active
      # An ordinary host fault must not fabricate Panda-authority loss or
      # revoke established armed intent; native/config/physical inputs are healthy.
      assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
      assert not sd.aol_authority_lost
      assert receive(now, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert card.aol_card_intent.allowed_latch
    fresh = BASE + (tick - 1) * 10_000_000
    axis, state, command = drive(tick + 1, state_stamp=fresh, **settings('lateral_only', fresh, sequence + 1))
    assert not state.enabled and not state.active and not axis.longitudinalActive and not command.longActive
    assert axis.lateralActive and command.latActive
    assert not sd.events.contains(fixture.ET.ENABLE)
    assert receive(fresh, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])


@pytest.mark.parametrize('mode', ['lateral_only', 'long_only', 'combined', 'combined_unarmed'])
def test_first_real_lag_fresh_decision_expiring_during_publication_keeps_normal_state_and_intent(mode):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    full_op = mode != 'lateral_only'
    sd, controls, drive, card, receive = case._ioniq_availability_callers(full_op=full_op)
    old, state, _ = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings(mode, BASE, 3))
    assert state.enabled == full_op and old.longitudinalActive == full_op
    if mode in ('lateral_only', 'combined'):
      assert receive(BASE + 4_497_535, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
    fresh = BASE + 40_000_000
    clock = [fresh + 29_999_000]
    original_publish = sd.publish_axis_proof
    entered = []
    def publish(cs, **kwargs):
      publication_ns = time.monotonic_ns()
      entered.append((publication_ns, sd.aol_car_state_log_ns, tuple(sd.events.names),
                      sd.state_machine.state, sd.state_machine.soft_disable_timer))
      assert publication_ns == fresh + 29_999_000 and sd.aol_car_state_log_ns == fresh
      assert log.OnroadEvent.EventName.selfdrivedLagging in sd.events.names
      assert log.OnroadEvent.EventName.commIssue not in sd.events.names
      assert not sd.aol_authority_lost and sd.aol_published_fault_reason == 'none'
      clock[0] = fresh + 30_001_000
      return original_publish(cs, **kwargs)
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02), \
         mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.monotonic_ns', side_effect=lambda: clock[0]), \
         mock.patch.object(sd, 'publish_axis_proof', side_effect=publish):
      axis, state, command = drive(6, state_stamp=fresh, offset_ns=29_999_000, **settings(mode, fresh, 4))
    assert len(entered) == 1
    assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
    assert old.validUntilMonoTime < axis.observedMonoTime
    assert state.enabled == full_op and state.active == full_op
    if full_op:
      assert state.state == log.SelfdriveState.OpenpilotState.softDisabling and sd.state_machine.soft_disable_timer == 300
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    assert not sd.aol_authority_lost
    if mode in ('lateral_only', 'combined'):
      assert receive(fresh + 30_001_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert card.aol_card_intent.allowed_latch
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=old.validUntilMonoTime + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
