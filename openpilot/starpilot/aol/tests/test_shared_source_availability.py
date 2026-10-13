from contextlib import ExitStack
import os
from unittest import mock

import pytest
from openpilot.cereal import log
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
from openpilot.starpilot.aol.tests.test_input_deadline_continuity import BASE, intent
from openpilot.starpilot.aol.vehicle import native_matches_cp, policy_for


def callers(cleanup, family):
  if family == 'gm_bolt_pedal':
    from opendbc.car.gm.tests.test_bolt_pedal import params
    from opendbc.car.gm.values import CAR
    cp = params(CAR.CHEVROLET_BOLT_CC_2018_2021, pedal=True, camera=True)
  else:
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.honda.interface import CarInterface
    from opendbc.car.honda.values import CAR, CarControllerParams
    cleanup.callback(setattr, CarControllerParams, 'BOSCH_GAS_LOOKUP_V', list(CarControllerParams.BOSCH_GAS_LOOKUP_V))
    cp = CarInterface.get_params(CAR.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), [], True, False, False)
  assert cp.openpilotLongitudinalControl
  assert policy_for(cp).intent_supported
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  cleanup.callback(case.doCleanups)
  cleanup.enter_context(OpenpilotPrefix())
  cleanup.enter_context(mock.patch.dict(os.environ, {'SIMULATION': '0', 'AOL_REPLAY_RUNTIME': '1'}))
  sd, controls, step = case._authority_callers(full_op=True, cp=cp, genuine_events=True)
  assert 'aolIntentWire' in sd.sm.data and 'aolSafetyWire' in sd.sm.data
  assert sd.CP.brand == ('gm' if family == 'gm_bolt_pedal' else 'honda')
  assert len(sd.CP.safetyConfigs) == 1
  config = sd.CP.safetyConfigs[0]
  assert native_matches_cp(sd.CP, config.safetyModel.raw, config.safetyParam)
  def drive(tick, **kwargs):
    state = fixture.car_state()
    state.cruiseState.available = state.cruiseState.enabled = True
    kwargs.setdefault('observed_state', state)
    kwargs.setdefault('latched', False)
    return step(tick, **kwargs)
  for tick in (0, 1):
    axis, state, command = drive(tick)
    assert state.enabled and axis.lateralActive and axis.longitudinalActive
    assert command.latActive and command.longActive
  return sd, controls, drive


@pytest.mark.parametrize('family', ['gm_bolt_pedal', 'honda_classic_bosch_long'])
def test_shared_ordinary_unarmed_combined_source_loss_has_no_stale_output(family):
  with ExitStack() as cleanup:
    sd, controls, drive = callers(cleanup, family)
    original, _, command = drive(2, state_stamp=BASE, offset_ns=4_497_535,
                                 intent_message=intent(BASE, 3, latched=False))
    assert original.lateralActive and original.longitudinalActive
    assert not sd.aol_last_intent.allowedLatch and not sd.aol_last_intent.lateralArmed
    deadline = original.validUntilMonoTime
    with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=deadline+1):
      expired, _ = controls.state_control()
    assert not expired.latActive and not expired.longActive
    axis, state, command = drive(5, timeout=True, offset_ns=5_399_000,
                                intent_message=intent(BASE, 3, latched=False))
    assert state.state == log.SelfdriveState.OpenpilotState.softDisabling
    assert state.enabled and state.active and sd.state_machine.soft_disable_timer == 300
    assert state.alertType == 'commIssue/softDisable'
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert axis.sourceCarStateMonoTime == 0
    assert original.validUntilMonoTime == deadline
    assert not sd.events.contains(fixture.ET.ENABLE)
    fresh = BASE+40_000_000
    axis, state, command = drive(6, state_stamp=fresh, intent_message=intent(fresh, 4, latched=False))
    assert state.enabled and axis.lateralActive and axis.longitudinalActive
    assert command.latActive and command.longActive
    assert axis.sourceCarStateMonoTime == fresh and axis.observedMonoTime >= fresh
    assert not sd.events.contains(fixture.ET.ENABLE)


@pytest.mark.parametrize('family', ['gm_bolt_pedal', 'honda_classic_bosch_long'])
@pytest.mark.parametrize('fault', ['native_invalid', 'panda_rx'])
def test_shared_source_classification_preserves_native_and_physical_fault_gates(family, fault):
  with ExitStack() as cleanup:
    sd, _, drive = callers(cleanup, family)
    drive(2, state_stamp=BASE, offset_ns=4_497_535, intent_message=intent(BASE, 3, latched=False))
    axis, state, command = drive(5, timeout=True, offset_ns=5_399_000,
      intent_message=intent(BASE, 3, latched=False), native_valid=fault != 'native_invalid', panda_fault=fault == 'panda_rx')
    assert not axis.lateralActive and not axis.longitudinalActive
    assert not command.latActive and not command.longActive
    assert not state.enabled
    assert log.OnroadEvent.EventName.controlsMismatch in sd.events.names
