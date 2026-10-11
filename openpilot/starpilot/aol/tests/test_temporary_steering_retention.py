from contextlib import ExitStack

import pytest

from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.wire import decode_safety


@pytest.mark.parametrize('silent', [True, False])
def test_actual_temporary_eps_keeps_existing_card_latch_and_recovers(silent):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, card, receive = case._ioniq_availability_callers(full_op=False)
      for tick in range(2, 152):
        healthy, _, healthy_command = step(tick, native_request_long=False)
        assert healthy.lateralActive and healthy_command.latActive and not healthy_command.longActive
        assert receive(10_000_000_000 + tick * 10_000_000, axis=sd.pm.messages['aolAxisState'],
                       event=sd.pm.messages['onroadEvents'])
      assert sd.car_events.steering_unpressed >= 150
      temporary = fixture.car_state()
      temporary.steerFaultTemporary = True
      temporary.standstill = silent
      # Card observes the physical restriction before the next SD/native heartbeat.
      assert receive(11_519_500_000, axis=sd.pm.messages['aolAxisState'],
                     event=sd.pm.messages['onroadEvents'], state=temporary)
      assert card.aol_card_intent.allowed_latch
      for tick in range(152, 212):
        awaiting_withdrawal = tick < 154
        axis, _, command = step(tick, observed_state=temporary, allowed=awaiting_withdrawal,
                                native_request_lat=awaiting_withdrawal, native_request_long=False)
        native = decode_safety(sd.sm['aolSafetyWire'])
        assert native is not None
        assert native.requestedLateral == awaiting_withdrawal and native.lateralAllowed == awaiting_withdrawal
        assert not axis.lateralActive and not command.latActive
        assert not axis.longitudinalActive and not command.longActive and not sd.enabled
        assert not sd.aol_authority_lost and str(axis.faultReason) != 'critical'
        assert any(name in sd.events.names for name in (log.OnroadEvent.EventName.steerTempUnavailable,
                                                       log.OnroadEvent.EventName.steerTempUnavailableSilent))
        expected_event = (log.OnroadEvent.EventName.steerTempUnavailableSilent if silent else
                          log.OnroadEvent.EventName.steerTempUnavailable)
        assert expected_event in sd.events.names
        assert receive(10_000_000_000 + tick * 10_000_000, axis=sd.pm.messages['aolAxisState'],
                       event=sd.pm.messages['onroadEvents'], state=temporary)
        assert card.aol_card_intent.allowed_latch and not card.aol_transport_feedback.failed
      recovered, _, command = step(212, native_request_lat=True, native_request_long=False)
      assert recovered.lateralActive and command.latActive
      assert not recovered.longitudinalActive and not command.longActive and not sd.enabled
      assert receive(12_120_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      assert card.aol_card_intent.allowed_latch and not sd.aol_authority_lost


@pytest.mark.parametrize('fault', ['permanent_eps', 'invalid_can', 'invalid_native'])
def test_temporary_eps_never_masks_permanent_can_or_native_fault(fault):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, card, receive = case._ioniq_availability_callers(full_op=False)
      observed = fixture.car_state()
      observed.steerFaultTemporary = True
      observed.steerFaultPermanent = fault == 'permanent_eps'
      observed.canValid = fault != 'invalid_can'
      axis, _, command = step(2, observed_state=observed, native_valid=fault != 'invalid_native', native_request_long=False)
      assert not axis.lateralActive and not axis.longitudinalActive and not command.latActive and not command.longActive
      assert not receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'],
                         event=sd.pm.messages['onroadEvents'], state=observed)
      assert not card.aol_card_intent.allowed_latch
      recovered, _, command = step(3, native_request_long=False)
      assert not recovered.lateralActive and not command.latActive and not command.longActive
      assert not card.aol_card_intent.allowed_latch
