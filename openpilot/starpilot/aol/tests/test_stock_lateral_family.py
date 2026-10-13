"""Family intent retention and fresh input recovery."""

from contextlib import ExitStack
from unittest import mock
import pytest
from openpilot.cereal import log
from openpilot.starpilot.aol.tests import stock_lateral_test_helpers as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE
from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings
from openpilot.starpilot.aol.runtime import current_native
from openpilot.starpilot.aol.wire import decode_safety
from openpilot.starpilot.aol.vehicle import native_matches_cp


from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import callers


@pytest.mark.parametrize('family', ('gm', 'toyota'))
@pytest.mark.parametrize('mode', ('combined', 'lateral_only'))
@pytest.mark.parametrize('host_lag', (False, True))
def test_family_source_expiry_preserves_intent_then_fresh_input_recovers(family, mode, host_lag):
  with ExitStack() as cleanup:
    sd, controls, drive, card, receive = callers(cleanup, family, mode == 'lateral_only')
    old, _, command = drive(2, state_stamp=BASE, offset_ns=4_497_535, **settings(mode, BASE, 3))
    assert old.lateralActive and command.latActive
    assert old.longitudinalActive == (mode == 'combined')
    assert receive(BASE + 4_497_535)
    deadline = old.validUntilMonoTime
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=deadline + 1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
    lag = mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02 if host_lag else 0.01)
    with lag:
      axis, state, command = drive(5, timeout=True, state_stamp=BASE, offset_ns=5_399_000, **settings(mode, BASE, 3))
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert axis.sourceCarStateMonoTime == 0 and not sd.conditional_car_state_valid
    assert not sd.aol_authority_lost and not getattr(sd, 'aol_availability_long_inhibit', False)
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    if mode == 'combined':
      assert state.enabled and state.state == log.SelfdriveState.OpenpilotState.softDisabling
    else:
      assert not state.enabled and not command.longActive
    assert receive(BASE + 35_399_000), 'Host-only expiry must not consume physical family intent'
    fresh = BASE + 40_000_000
    axis, state, command = drive(6, state_stamp=fresh, **settings(mode, fresh, 4))
    assert axis.lateralActive and command.latActive
    assert axis.longitudinalActive == command.longActive == (mode == 'combined')
    assert axis.sourceCarStateMonoTime == fresh
    assert receive(BASE + 40_000_000)


@pytest.mark.parametrize('family', ('gm', 'toyota'))
@pytest.mark.parametrize('fault', ('native_denied', 'pedal', 'cancel', 'mixed_hard'))
def test_family_host_gap_does_not_authorize_negative_inputs(family, fault):
  with ExitStack() as cleanup:
    sd, controls, drive, card, receive = callers(cleanup, family, False)
    old, _, command = drive(2, state_stamp=BASE, **settings('combined', BASE, 3))
    assert old.longitudinalActive and command.longActive
    physical = fixture.car_state()
    physical.cruiseState.available = True
    options = settings('combined', BASE, 3)
    if fault == 'native_denied':
      options['allowed'] = False
      options['long_allowed'] = False
    elif fault == 'pedal':
      physical.brakePressed = True
    elif fault == 'cancel':
      physical.buttonEvents = [fixture.car.CarState.ButtonEvent(type=fixture.car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    else:
      options['relay_fault'] = True
      physical.steerFaultPermanent = True
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      axis, state, command = drive(5, timeout=True, observed_state=physical, state_stamp=BASE, offset_ns=1, **options)
    assert not axis.longitudinalActive and not command.longActive
    assert not axis.lateralActive and not command.latActive
    assert old.validUntilMonoTime < 10_050_000_001
    if fault in ('native_denied', 'mixed_hard'):
      assert sd.aol_authority_lost or str(axis.faultReason) in ('critical', 'nativeDenied')
    retained = receive(10_050_000_001, physical)
    if fault in ('native_denied', 'mixed_hard'):
      assert sd.aol_authority_lost and str(axis.faultReason) == 'critical'
      assert card.aol_transport_feedback.failed
      wire = decode_safety(sd.sm['aolSafetyWire'])
      assert wire is not None and wire.pandaInventory
      assert native_matches_cp(sd.CP, wire.safetyModel, wire.safetyParam)
      if fault == 'native_denied':
        assert wire.requestedLateral and wire.requestedLongitudinal
        assert not wire.lateralAllowed and not wire.longitudinalAllowed
      else:
        assert physical.steerFaultPermanent and any(slot.faults for slot in wire.pandaInventory)
        assert current_native(sd.sm, sd.CP, now_ns=10_050_000_001, axis_session_id=sd.aol_session_id) is None
      if family == 'gm':
        assert not retained
        assert card.aol_card_intent._main_cycle_required
      else:
        # Toyota MAIN is physical permission, not a deliberate latch. Its
        # unchanged source persists while failed transport withdraws all axes.
        assert not card.aol_card_intent.explicit_latch
        assert card.aol_card_intent.settings.main_action == card.aol_card_intent.lkas_action == 0
        assert retained == bool(physical.cruiseState.available)
        assert retained and not axis.lateralActive and not axis.longitudinalActive
    assert not command.longActive and not command.latActive
