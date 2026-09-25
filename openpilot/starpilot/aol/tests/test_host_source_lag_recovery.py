"""Host source loss and loop-lag lifecycle regression coverage."""
from contextlib import ExitStack
from unittest import mock
import pytest
from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings

@pytest.mark.parametrize('mode', ['long_only','combined','combined_unarmed'])
def test_real_prior_lag_clears_while_source_is_still_missing_keeps_normal_soft_state(mode):
  case=fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd,_,drive,card,receive=case._ioniq_availability_callers(full_op=True)
    old,state,command=drive(2,state_stamp=BASE,offset_ns=4_497_535,**settings(mode,BASE,3))
    assert state.enabled and old.longitudinalActive and command.longActive
    if mode=='combined':
      assert receive(BASE+4_497_535,axis=sd.pm.messages['aolAxisState'],event=sd.pm.messages['onroadEvents'])
    source=BASE+10_000_000
    with mock.patch.object(sd.rk.avg_dt,'get_average',return_value=0.02):
      axis,state,command=drive(3,state_stamp=source,**settings(mode,source,4))
      assert state.enabled and state.state==log.SelfdriveState.OpenpilotState.softDisabling
      assert sd.state_machine.soft_disable_timer==300
      assert log.OnroadEvent.EventName.selfdrivedLagging in sd.events.names
      assert str(axis.faultReason)=='none' and not sd.aol_authority_lost
      assert axis.desiredLongitudinal and axis.longitudinalActive and command.longActive and axis.nativeAcknowledged
      assert bool(axis.lateralActive) == bool(command.latActive) == (mode != 'long_only')
      fresh_lag_deadline = axis.validUntilMonoTime
      if mode=='combined':
        assert receive(source,axis=sd.pm.messages['aolAxisState'],event=sd.pm.messages['onroadEvents'])
    assert not sd.rk.lagging
    axis,state,command=drive(7,timeout=True,state_stamp=source,offset_ns=5_399_000,**settings(mode,source,4))
    assert log.OnroadEvent.EventName.selfdrivedLagging not in sd.events.names
    assert log.OnroadEvent.EventName.commIssue in sd.events.names
    assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
    assert old.validUntilMonoTime<axis.observedMonoTime
    assert fresh_lag_deadline<axis.observedMonoTime
    assert state.enabled and state.state==log.SelfdriveState.OpenpilotState.softDisabling
    assert sd.state_machine.soft_disable_timer==299
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    assert not sd.aol_authority_lost and not getattr(sd,'aol_availability_long_inhibit',False)
    assert axis.sourceCarStateMonoTime==0 and not sd.conditional_car_state_valid
    if mode=='combined':
      assert receive(BASE+55_399_000,axis=sd.pm.messages['aolAxisState'],event=sd.pm.messages['onroadEvents'])
      assert card.aol_card_intent.allowed_latch
    fresh=BASE+60_000_000
    options=settings(mode,fresh,5)
    options.update(native_request_long=False,long_allowed=False)
    axis,state,command=drive(8,state_stamp=fresh,**options)
    assert state.enabled and axis.desiredLongitudinal and not axis.longitudinalActive and not command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)
    fresh+=10_000_000
    axis,state,command=drive(9,state_stamp=fresh,**settings(mode,fresh,6))
    assert state.enabled and axis.longitudinalActive and command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)
