"""Actual stock-family chronology through fresh lag then missing host input.
Factory/native owners are real; input transport, CAN parse and clocks synthetic.
No prior USER witness exception is supplied by these tests.
"""

from unittest import mock


import pytest


from openpilot.cereal import log


from openpilot.starpilot.aol.runtime import current_native


from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE


from openpilot.starpilot.aol.tests.test_ordinary_source_availability import settings


from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import stock_family


@pytest.mark.parametrize('family', ['toyota', 'hkg_classic', 'hkg_canfd', 'honda'])
def test_stock_lat_intent_fresh_lag_then_source_gap_then_recovery(family):
  with stock_family(family) as (sd, controls, drive, card, receive):
    old, _, command = drive(2, state_stamp=BASE, **settings('lateral_only', BASE, 3))
    assert old.lateralActive and command.latActive and not old.longitudinalActive and not command.longActive
    assert receive(BASE, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']) if family != 'toyota' else receive(BASE)
    first = BASE + 10_000_000
    with mock.patch.object(sd.rk.avg_dt, 'get_average', return_value=0.02):
      lag, state, command = drive(3, state_stamp=first, **settings('lateral_only', first, 4))
      assert not state.enabled and not state.active and not command.latActive and not command.longActive
      assert str(lag.faultReason) == 'critical' and lag.sourceCarStateMonoTime == first
      assert not lag.lateralActive and not lag.longitudinalActive and not lag.nativeAcknowledged
      witness = sd.aol_published_fault_proof
      assert witness is not None and len(witness) == 9 and not any(witness[4:])
      assert witness[0] == sd.aol_session_id and witness[1] == 'critical' and witness[2] == lag.faultEventMonoTime
      users = [e for e in sd.events.to_msg() if e.userDisable]
      expected = log.OnroadEvent.EventName.cruiseDisabled if family == 'honda' else log.OnroadEvent.EventName.pcmDisable
      assert users and all(e.name == expected and not e.softDisable and not e.immediateDisable for e in users)
      assert any(e.name == log.OnroadEvent.EventName.selfdrivedLagging and e.softDisable for e in sd.events.to_msg())
      assert not sd.aol_authority_lost
      assert receive(first, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']) if family != 'toyota' else receive(first)
      assert not card.aol_transport_feedback.failed
      native = current_native(sd.sm, sd.CP, now_ns=first, axis_session_id=sd.aol_session_id)
      assert native is not None and native.requestedLateral and native.lateralAllowed and not native.requestedLongitudinal
      with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=old.validUntilMonoTime + 1):
        off, _ = controls.state_control()
      assert not off.latActive and not off.longActive
      gap = BASE + 45_399_000
      paused, state, command = drive(6, timeout=True, state_stamp=first, offset_ns=5_399_000, **settings('lateral_only', first, 4))
      assert not paused.lateralActive and not paused.longitudinalActive and not command.latActive and not command.longActive
      assert not state.enabled and not state.active and not sd.events.contains('enable')
      assert not sd.aol_authority_lost and str(paused.faultReason) == 'availabilityPause'
      assert paused.sourceCarStateMonoTime == 0 and not sd.conditional_car_state_valid
      assert receive(gap, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']) if family != 'toyota' else receive(gap)
      assert not card.aol_transport_feedback.failed
      assert card.aol_transport_feedback.retention_verified
    recovered_stamp = BASE + 50_000_000
    recovered, state, command = drive(7, state_stamp=recovered_stamp, **settings('lateral_only', recovered_stamp, 5))
    assert not state.enabled and not state.active and not command.longActive and not recovered.longitudinalActive
    assert recovered.lateralActive and command.latActive and recovered.sourceCarStateMonoTime == recovered_stamp
    assert (
      receive(recovered_stamp, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents']) if family != 'toyota' else receive(recovered_stamp)
    )
    assert not card.aol_transport_feedback.failed
    assert not sd.events.contains('enable') and old.validUntilMonoTime == BASE + 30_000_000


