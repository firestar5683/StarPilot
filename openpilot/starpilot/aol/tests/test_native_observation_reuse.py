"""Reuse only inventory validation performed inside one native observation."""
from dataclasses import replace
from unittest import mock

import pytest

from openpilot.cereal import messaging
from openpilot.starpilot.aol import runtime, transport_pause
from openpilot.starpilot.aol.tests.test_panda_inventory import NOW, bound_state, configured_cp, sm_for
from openpilot.starpilot.aol.tests.test_runtime import car_state


@pytest.mark.parametrize('supplied', [None, False, 'state'])
def test_local_validation_is_reused_but_external_and_falsy_inputs_are_rechecked(supplied):
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  with mock.patch.object(runtime, 'native_inventory_matches_cp', wraps=runtime.native_inventory_matches_cp) as local, \
       mock.patch.object(transport_pause, 'native_inventory_matches_cp',
                         wraps=transport_pause.native_inventory_matches_cp) as provided:
    assert transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW,
                                            native=state if supplied == 'state' else supplied)
  assert local.call_count == (0 if supplied == 'state' else 1)
  assert provided.call_count == (0 if supplied is None else 1)


@pytest.mark.parametrize('supplied', [False, True])
@pytest.mark.parametrize('change', ['slot', 'model', 'param', 'experience', 'serial', 'rx', 'heartbeat', 'fault'])
def test_native_inventory_corruption_is_rejected_with_or_without_external_state(supplied, change):
  cp = configured_cp()
  state = bound_state(cp)
  changes = {'slot': {'slotIndex': 1}, 'model': {'safetyModel': 19}, 'param': {'safetyParam': 0},
             'experience': {'alternativeExperience': cp.alternativeExperience ^ 1},
             'serial': {'hardwareSerial': 'other'}, 'rx': {'safetyRxChecksInvalid': True},
             'heartbeat': {'heartbeatLost': True}, 'fault': {'faults': 1}}
  bad = replace(state, pandaInventory=(replace(state.pandaInventory[0], **changes[change]),))
  sm = sm_for(cp, bad)
  assert not transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW,
                                              native=bad if supplied else None)


@pytest.mark.parametrize('change', ['rx', 'heartbeat', 'fault', 'controls', 'param', 'experience',
                                   'valid', 'alive', 'seen', 'stamp'])
def test_latest_panda_veto_is_checked_after_local_native_validation(change):
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  if change in ('valid', 'alive', 'seen'):
    getattr(sm, change)['pandaStates'] = False
  elif change == 'stamp':
    sm.logMonoTime['pandaStates'] = 0
  else:
    update = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=state.sourcePandaStatesMonoTime)
    update.pandaStates[0] = sm['pandaStates'][0]
    field, value = {'rx': ('safetyRxChecksInvalid', True), 'heartbeat': ('heartbeatLost', True),
                    'fault': ('faults', ['relayMalfunction']), 'controls': ('controlsAllowed', False),
                    'param': ('safetyParam', 0), 'experience': ('alternativeExperience', 1)}[change]
    setattr(update.pandaStates[0], field, value)
    sm.update_msgs(NOW / 1e9, [update.as_reader()])
  assert runtime.current_native(sm, cp, now_ns=NOW) is not None
  assert not transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW)


def test_cp_changes_between_calls_cannot_reuse_previous_inventory_or_admission():
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  def check():
    return transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW)
  assert check()
  cp.alternativeExperience ^= 1
  assert not check()
  cp.alternativeExperience ^= 1
  assert check()
  cp.radarUnavailable = True
  assert not check()
  cp.radarUnavailable = False
  assert check()


@pytest.mark.parametrize('boundary', ['at', 'expired', 'future', 'session', 'native_invalid'])
def test_local_reuse_preserves_original_native_lease_and_session(boundary):
  cp = configured_cp()
  state = bound_state(cp, now=NOW + 1 if boundary == 'future' else NOW)
  sm = sm_for(cp, state)
  if boundary == 'native_invalid':
    sm.valid['aolSafetyWire'] = False
  now = NOW + (200_000_000 if boundary == 'at' else 200_000_001 if boundary == 'expired' else 0)
  session = 'foreign' if boundary == 'session' else state.axisSessionId
  assert transport_pause.healthy_transport(sm, cp, car_state(), session, now) == (boundary == 'at')


@pytest.mark.parametrize('supplied', [False, True])
def test_independent_lateral_health_keeps_distinct_longitudinal_veto(supplied):
  cp = configured_cp()
  state = bound_state(cp)
  state = replace(state, longitudinalAllowed=False,
                  pandaInventory=(replace(state.pandaInventory[0], controlsAllowed=False),))
  sm = sm_for(cp, state)
  update = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=state.sourcePandaStatesMonoTime)
  update.pandaStates[0] = sm['pandaStates'][0]
  update.pandaStates[0].controlsAllowed = False
  sm.update_msgs(NOW / 1e9, [update.as_reader()])
  native = state if supplied else None
  assert transport_pause._configured_transport_native(sm, cp, state.axisSessionId, NOW, native) is None
  assert transport_pause._configured_transport_native(
    sm, cp, state.axisSessionId, NOW, native, require_longitudinal=False) == state


@pytest.mark.parametrize('supplied', [False, True])
@pytest.mark.parametrize('mutation', ['none', 'auxiliary_controls', 'serial', 'order', 'slot', 'count'])
def test_admitted_ev6_two_panda_inventory_preserves_every_slot_guard(supplied, mutation):
  from openpilot.starpilot.tests.test_ev6_startup import params
  from opendbc.car.hyundai.ev6_aol import qualified

  cp = params()
  # A prepared two-Panda fixture; this test performs no ECU handoff or output.
  cp.openpilotLongitudinalControl, cp.pcmCruise, cp.alternativeExperience = True, False, 32
  cp.safetyConfigs = [{'safetyModel': 'noOutput', 'safetyParam': 0},
                      {'safetyModel': 'hyundaiCanfd', 'safetyParam': 0x815}]
  assert qualified(cp, marked_only=True)
  state = bound_state(cp)
  sm = sm_for(cp, state)
  assert runtime.current_native(sm, cp, now_ns=NOW) == state
  assert transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW)
  first, owner = state.pandaInventory
  changes = {'none': (first, owner), 'auxiliary_controls': (replace(first, controlsAllowed=True), owner),
             'serial': (replace(first, hardwareSerial=owner.hardwareSerial), owner), 'order': (owner, first),
             'slot': (first, replace(owner, slotIndex=0)), 'count': (owner,)}
  state = replace(state, pandaInventory=changes[mutation])
  sm = sm_for(cp, state)
  assert transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW,
                                           native=state if supplied else None) == (mutation == 'none')


@pytest.mark.parametrize('supplied', [False, True])
def test_legacy_single_panda_empty_inventory_keeps_freshness_and_latest_health(supplied):
  cp = configured_cp()
  state = replace(bound_state(cp), sourcePandaStatesMonoTime=0, pandaInventory=())
  sm = sm_for(cp, state, panda_stamp=NOW)
  assert transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW,
                                           native=state if supplied else None)
  # Unlike v2 BOOTTIME provenance, legacy PandaStates still uses this age gate.
  sm.logMonoTime['pandaStates'] = NOW - 200_000_001
  assert not transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW,
                                              native=state if supplied else None)
