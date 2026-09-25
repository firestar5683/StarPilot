"""Hyundai family source availability with actual caller ownership."""

from unittest import mock
import pytest
from opendbc.car import gen_empty_fingerprint
from openpilot.cereal import messaging, log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import car_state


from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import hkg_family_case as family_case


@pytest.mark.parametrize('family,full', [('hkg_classic', False), ('hkg_classic', True), ('hkg_canfd', False)])
@pytest.mark.parametrize('fault', ['baseline', 'native_deny', 'physical_cancel', 'mixed_hard'])
def test_actual_family_baseline_and_faults(family, full, fault):
  with OpenpilotPrefix():
    case = family_case(family, full)
    try:
      if full:
        assert case.family_cp.openpilotLongitudinalControl, f'{family}: actual CP does not support ordinary LONG; select legitimate supported CP instead'
      sd, controls, step, card, receive = case.family_callers(full)
      assert card.CP.to_dict() == sd.CP.to_dict()
      axis, _, command = step(2)
      assert axis.lateralActive and command.latActive
      assert bool(axis.longitudinalActive) == full
      assert receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      if fault == 'baseline':
        return
      kwargs = {}
      if fault == 'native_deny':
        kwargs['allowed'] = False
      elif fault == 'mixed_hard':
        kwargs['critical_event'] = log.OnroadEvent.EventName.controlsMismatch
      else:
        from opendbc.car.structs import car

        state = car_state()
        state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
        kwargs['observed_state'] = state
      denied, _, command = step(3, **kwargs)
      assert not denied.longitudinalActive and not command.longActive
      if fault != 'physical_cancel':
        assert not denied.lateralActive and not command.latActive
    finally:
      case.doCleanups()


@pytest.mark.parametrize('family,full', [('hkg_classic', False), ('hkg_classic', True), ('hkg_canfd', False)])
def test_actual_family_isolated_host_lag_source_gap_recovery(family, full):
  with OpenpilotPrefix():
    case = family_case(family, full)
    try:
      if full:
        assert case.family_cp.openpilotLongitudinalControl, f'{family}: actual CP lacks ordinary LONG, cannot claim this qualification'
      sd, controls, step, card, receive = case.family_callers(full)
      before, _, command = step(2)
      assert before.lateralActive and command.latActive
      accepted_wire = messaging.new_message('aolIntentWire', 0, valid=sd.sm.valid['aolIntentWire'], logMonoTime=sd.sm.logMonoTime['aolIntentWire'])
      accepted_wire.aolIntentWire = sd.sm['aolIntentWire']
      from openpilot.starpilot.aol.wire import decode_intent

      assert decode_intent(accepted_wire.aolIntentWire) == decode_intent(sd.sm['aolIntentWire'])
      assert accepted_wire.valid
      assert accepted_wire.logMonoTime == before.sourceCarStateMonoTime
      old_events = sd.update_events

      def host_lag(state):
        result = old_events(state)
        sd.events.add(log.OnroadEvent.EventName.selfdrivedLagging)
        return result

      with mock.patch.object(sd, 'update_events', side_effect=host_lag):
        off, _, command = step(5, timeout=True, offset_ns=5_000_000, intent_message=accepted_wire)
      assert not off.lateralActive and not off.longitudinalActive
      assert not command.latActive and not command.longActive
      assert not sd.aol_authority_lost
      # Native producer fixture maintains exact actual CP/session inventory;
      # Card must accept typed inactive intent retention against that identity.
      assert receive(10_055_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'])
      fresh, _, command = step(6, latched=card.aol_card_intent.allowed_latch)
      assert fresh.lateralActive and command.latActive
      assert bool(fresh.longitudinalActive) == full and bool(command.longActive) == full
    finally:
      case.doCleanups()


def test_ev6_requested_alpha_factory_topology_remains_unsupported():
  from opendbc.car.hyundai.interface import CarInterface
  from opendbc.car.hyundai.values import CAR
  from opendbc.car.hyundai.hyundaicanfd import CanBus

  fp = gen_empty_fingerprint()
  fp[CanBus(None, fp).CAM][0x50] = 16
  cp = CarInterface.get_params(CAR.KIA_EV6, fp, [], True, False, False)
  assert not cp.openpilotLongitudinalControl
  assert cp.pcmCruise
