"""Host source loss and loop-lag lifecycle regression coverage."""
from contextlib import ExitStack
from dataclasses import replace
from unittest import mock

import pytest
from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings
from openpilot.starpilot.aol.wire import decode_intent, encode_intent


@pytest.mark.parametrize('mode', ['long_only', 'combined', 'combined_unarmed'])
@pytest.mark.parametrize('prior_lag', [False, True])
def test_host_gap_during_real_loop_lag_remains_ordinary_soft_disable(mode, prior_lag):
  case=fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd,controls,drive,card,receive=case._ioniq_availability_callers(full_op=True)
    old,state,command=drive(2,state_stamp=BASE,offset_ns=4_497_535,**settings(mode,BASE,3))
    assert state.enabled and old.longitudinalActive and command.longActive
    deadline=old.validUntilMonoTime
    if mode=='combined':
      assert receive(BASE+4_497_535,axis=sd.pm.messages['aolAxisState'],event=sd.pm.messages['onroadEvents'])
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns',return_value=deadline+1):
      expired,_=controls.state_control()
    assert not expired.latActive and not expired.longActive
    source,sequence=BASE,3
    # Only a numerical input to the REAL Ratekeeper is changed. Real update_events
    # creates selfdrivedLagging; StateMachine/native/axis decisions are untouched.
    with mock.patch.object(sd.rk.avg_dt,'get_average',return_value=0.02):
      assert sd.rk.lagging
      if prior_lag:
        source,sequence=BASE+10_000_000,4
        axis,state,command=drive(3,state_stamp=source,**settings(mode,source,sequence))
        assert state.enabled and state.state==log.SelfdriveState.OpenpilotState.softDisabling
        assert log.OnroadEvent.EventName.selfdrivedLagging in sd.events.names
        assert not sd.aol_authority_lost
        # Corrected contract: fresh, already-engaged ordinary axes continue
        # under the real SOFT timer. Only the subsequent expired source is OFF.
        assert str(axis.faultReason) == 'none' and axis.longitudinalActive and command.longActive
        assert bool(axis.lateralActive) == bool(command.latActive) == (mode != 'long_only')
        fresh_lag_deadline = axis.validUntilMonoTime
        if mode=='combined':
          assert receive(BASE+10_000_000,axis=sd.pm.messages['aolAxisState'],event=sd.pm.messages['onroadEvents'])
      tick=7 if prior_lag else 5
      now=BASE+(tick-2)*10_000_000+5_399_000
      axis,state,command=drive(tick,timeout=True,state_stamp=source,offset_ns=5_399_000,**settings(mode,source,sequence))
      assert log.OnroadEvent.EventName.selfdrivedLagging in sd.events.names
      assert not axis.lateralActive and not axis.longitudinalActive
      assert not command.latActive and not command.longActive
      assert old.validUntilMonoTime==deadline<now
      if prior_lag:
        assert fresh_lag_deadline < now
      assert state.enabled and state.state==log.SelfdriveState.OpenpilotState.softDisabling
      assert log.OnroadEvent.EventName.commIssue in sd.events.names
      assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
      assert not sd.aol_authority_lost and not getattr(sd,'aol_availability_long_inhibit',False)
      assert axis.sourceCarStateMonoTime==0 and not sd.conditional_car_state_valid
      assert sd.state_machine.soft_disable_timer==(299 if prior_lag else 300)
      if mode=='combined':
        assert receive(now,axis=sd.pm.messages['aolAxisState'],event=sd.pm.messages['onroadEvents'])
        assert card.aol_card_intent.allowed_latch
    # Fresh source first negotiates a request while native LONG is still OFF.
    fresh=BASE+(tick-1)*10_000_000
    options=settings(mode,fresh,sequence+1)
    options.update(native_request_long=False,long_allowed=False)
    axis,state,command=drive(tick+1,state_stamp=fresh,**options)
    assert state.enabled and axis.desiredLongitudinal and not axis.longitudinalActive and not command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)
    fresh+=10_000_000
    axis,state,command=drive(tick+2,state_stamp=fresh,**settings(mode,fresh,sequence+2))
    assert state.enabled and axis.longitudinalActive and command.longActive
    assert not sd.events.contains(fixture.ET.ENABLE)


@pytest.mark.parametrize('fault', ['native_invalid','panda_rx','permanent_eps','producer_changed'])
def test_loop_lag_does_not_excuse_real_fault_or_changed_provenance(fault):
  case=fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd,_,drive,_,_=case._ioniq_availability_callers(full_op=True)
    old,_,_=drive(2,state_stamp=BASE,offset_ns=4_497_535,**settings('combined',BASE,3))
    options=settings('combined',BASE,3)
    observed=fixture.car_state()
    if fault=='permanent_eps':
      observed.steerFaultPermanent=True
    if fault=='producer_changed':
      from openpilot.starpilot.aol.tests.test_input_deadline_continuity import intent
      message=intent(BASE+29_000_000,4)
      message.aolIntentWire=encode_intent(replace(decode_intent(message.aolIntentWire),producerSessionId='changed-card'))
      options['intent_message']=message
    with mock.patch.object(sd.rk.avg_dt,'get_average',return_value=0.02):
      axis,state,command=drive(5,timeout=fault!='permanent_eps',state_stamp=BASE,offset_ns=5_399_000,
        observed_state=observed,native_valid=fault!='native_invalid',panda_fault=fault=='panda_rx',**options)
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert not state.enabled and not sd.aol_ordinary_source_pause
    assert old.validUntilMonoTime<axis.observedMonoTime
