"""Stock Honda source availability and startup evidence."""

import time
from unittest import mock
import pytest
from openpilot.cereal import messaging, log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import car_state


from openpilot.starpilot.aol.tests.stock_lateral_test_helpers import honda_family_case as family_case


@pytest.mark.parametrize('family,full', [('honda', False)])
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


@pytest.mark.parametrize('family,full', [('honda', False)])
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


def test_honda_alpha_runtime_requires_actual_opt_in():
  from openpilot.common.params import Params
  from openpilot.starpilot.aol.vehicle import policy_for
  from openpilot.starpilot.feature_runtime import enabled

  with OpenpilotPrefix():
    case = family_case('honda', True)
    params = Params()
    params.put_bool('AlwaysOnLateral', True, block=True)
    policy = policy_for(case.family_cp)
    # Factory marker is not fabricated: only Card can publish runtime marking.
    assert not enabled(params, case.family_cp, 'aol', {})
    assert not policy.normal_runtime_supported


@pytest.mark.parametrize('failure', ['stale_boot', 'stale_receipt', 'wrong_config'])
def test_honda_real_startup_panda_evidence_rejects(failure):
  with OpenpilotPrefix():
    case = family_case('honda', False)
    try:
      sd, controls, step, card, receive = case.family_callers(False)
      now = 10_010_000_000
      actual_clock = time.clock_gettime_ns
      with (
        mock.patch('openpilot.selfdrive.car.card.time.monotonic_ns', return_value=now),
        mock.patch('openpilot.selfdrive.car.card.time.clock_gettime_ns', side_effect=lambda c: now if c == time.CLOCK_BOOTTIME else actual_clock(c)),
      ):
        assert card.startup_panda_configured()
        if failure == 'stale_boot':
          with mock.patch(
            'openpilot.selfdrive.car.card.time.clock_gettime_ns', side_effect=lambda c: now + 300_000_001 if c == time.CLOCK_BOOTTIME else actual_clock(c)
          ):
            assert not card.startup_panda_configured()
        elif failure == 'stale_receipt':
          with mock.patch.dict(card.sm.recv_time, {'pandaStates': (now - 300_000_001) / 1e9}):
            assert not card.startup_panda_configured()
        else:
          stamp = card.sm.logMonoTime['pandaStates']
          frame = messaging.new_message('pandaStates', len(card.sm['pandaStates']), valid=True, logMonoTime=stamp)
          frame.pandaStates = card.sm['pandaStates']
          frame.pandaStates[0].safetyParam ^= 1
          card.sm.update_msgs(now / 1e9, [frame.as_reader()])
          assert not card.startup_panda_configured()
    finally:
      case.doCleanups()
