"""Reuse structural admission only; every live native gate remains per call."""
from dataclasses import replace
from unittest import mock

import pytest

from openpilot.cereal import messaging
from openpilot.starpilot.aol import runtime, transport_pause
from openpilot.starpilot.aol.tests.test_panda_inventory import NOW, bound_state, configured_cp, sm_for
from openpilot.starpilot.aol.tests.test_runtime import car_state
from openpilot.starpilot.aol.wire import encode_safety


def receive(sm, state, *, stamp=None, valid=True, raw=None):
  stamp = state.observedMonoTime if stamp is None else stamp
  message = messaging.new_message('aolSafetyWire', 0, valid=valid, logMonoTime=stamp)
  message.aolSafetyWire = encode_safety(state) if raw is None else raw
  sm.update_msgs(max(NOW, stamp) / 1e9, [message.as_reader()])


def current(sm, cp, now=NOW, session=None):
  return runtime.current_native(sm, cp, now_ns=now, axis_session_id=session)


def test_twenty_observations_per_two_hundred_live_checks_and_owner_isolation():
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  other = sm_for(cp, state)
  with mock.patch.object(runtime, 'native_matches_cp', wraps=runtime.native_matches_cp) as profile, \
       mock.patch.object(runtime, 'native_inventory_matches_cp', wraps=runtime.native_inventory_matches_cp) as inventory:
    for tick in range(200):
      now = NOW + tick * 10_000_000
      if tick % 10 == 0:
        state = bound_state(cp, now=now)
        receive(sm, state)
      assert current(sm, cp, now, state.axisSessionId if tick % 2 else None) == state
    assert profile.call_count == inventory.call_count == 20
    assert current(other, cp) is not None
    assert profile.call_count == inventory.call_count == 21
    assert len(sm._aol_native_admission) == 3


@pytest.mark.parametrize('field,value', [
  ('brand', 'mock'), ('carFingerprint', 'mock'), ('flags', 0), ('radarUnavailable', True),
  ('notCar', True), ('passive', True), ('dashcamOnly', True),
  ('openpilotLongitudinalControl', False), ('pcmCruise', True), ('alternativeExperience', 32),
  ('safetyModel', 0), ('safetyParam', 0), ('extra_slot', True),
])
def test_every_cp_admission_input_invalidates_a_hot_entry(field, value):
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  assert current(sm, cp) is not None
  original = cp.as_reader().as_builder()
  if field == 'extra_slot':
    cp.safetyConfigs = [original.safetyConfigs[0], original.safetyConfigs[0]]
  elif field in ('safetyModel', 'safetyParam'):
    setattr(cp.safetyConfigs[0], field, value)
  else:
    setattr(cp, field, value)
  assert current(sm, cp) is None
  assert sm._aol_native_admission is None
  if field == 'extra_slot':
    cp.safetyConfigs = [original.safetyConfigs[0]]
  elif field in ('safetyModel', 'safetyParam'):
    setattr(cp.safetyConfigs[0], field, getattr(original.safetyConfigs[0], field))
  else:
    setattr(cp, field, getattr(original, field))
  with mock.patch.object(runtime, 'native_matches_cp', wraps=runtime.native_matches_cp) as profile:
    assert current(sm, cp) is not None
    assert profile.call_count == 1


@pytest.mark.parametrize('field', ['valid', 'alive', 'seen'])
def test_live_envelope_health_invalidates_hot_entry(field):
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  assert current(sm, cp) is not None
  getattr(sm, field)['aolSafetyWire'] = False
  assert current(sm, cp) is None
  assert sm._aol_native_admission is None
  getattr(sm, field)['aolSafetyWire'] = True
  with mock.patch.object(runtime, 'native_matches_cp', wraps=runtime.native_matches_cp) as profile:
    assert current(sm, cp) is not None
    assert profile.call_count == 1


@pytest.mark.parametrize('change', ['session', 'future_clock', 'expired', 'future_source', 'changed_source', 'bad_byte'])
def test_live_identity_and_original_lease_reject_hot_entry(change):
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  assert current(sm, cp) is not None
  now, session = NOW, state.axisSessionId
  if change == 'session':
    session = 'foreign'
  elif change == 'future_clock':
    now -= 1
  elif change == 'expired':
    now += 200_000_001
  elif change in ('future_source', 'changed_source'):
    sm.logMonoTime['aolSafetyWire'] += 1 if change == 'future_source' else -1
  else:
    raw = bytearray(encode_safety(state))
    raw[0] ^= 1
    receive(sm, state, raw=bytes(raw))
  assert current(sm, cp, now, session) is None
  assert sm._aol_native_admission is None


@pytest.mark.parametrize('change', ['lateral', 'longitudinal', 'rx', 'heartbeat', 'fault', 'serial', 'inventory', 'compatible', 'protocol'])
def test_changed_wire_cannot_borrow_previous_native_permission_or_health(change):
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  assert current(sm, cp) is not None
  values = {'lateral': {'lateralAllowed': False}, 'longitudinal': {'longitudinalAllowed': False},
            'serial': {'pandaSerial': 'foreign'}, 'compatible': {'compatible': False}, 'protocol': {'protocolVersion': 2}}
  if change in values:
    updated = replace(state, **values[change])
  else:
    slot = state.pandaInventory[0]
    fields = {'rx': {'safetyRxChecksInvalid': True}, 'heartbeat': {'heartbeatLost': True},
              'fault': {'faults': 1}, 'inventory': {'safetyParam': 0}}
    updated = replace(state, pandaInventory=(replace(slot, **fields[change]),))
  receive(sm, updated)
  result = current(sm, cp)
  if change in ('lateral', 'longitudinal'):
    assert result == updated
    assert not getattr(result, 'lateralAllowed' if change == 'lateral' else 'longitudinalAllowed')
  else:
    assert result is None
    assert sm._aol_native_admission is None


def test_latest_panda_fault_is_still_checked_on_a_native_cache_hit():
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  assert transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW)
  pandas = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=state.sourcePandaStatesMonoTime)
  pandas.pandaStates[0] = sm['pandaStates'][0]
  pandas.pandaStates[0].heartbeatLost = True
  sm.update_msgs(NOW / 1e9, [pandas.as_reader()])
  assert current(sm, cp) is not None
  assert not transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW)


def test_same_builder_mutation_during_miss_cannot_store_an_old_key():
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  original = runtime.native_inventory_matches_cp

  def validate_then_mutate(native, params):
    result = original(native, params)
    params.radarUnavailable = True
    return result

  with mock.patch.object(runtime, 'native_inventory_matches_cp', side_effect=validate_then_mutate):
    assert current(sm, cp) is not None  # Same result as the uncached validation call.
  assert sm._aol_native_admission is None
  assert current(sm, cp) is None


@pytest.mark.parametrize('legacy', [False, True])
def test_unsupported_owner_or_legacy_wire_keeps_full_validation(legacy):
  cp = configured_cp()
  state = bound_state(cp)
  if legacy:
    state = replace(state, sourcePandaStatesMonoTime=0, pandaInventory=())
  original = sm_for(cp, state)

  class SlottedOwner:
    __slots__ = ('valid', 'alive', 'seen', 'logMonoTime')

    def __init__(self):
      for name in self.__slots__:
        setattr(self, name, getattr(original, name))

    def __getitem__(self, name):
      return original[name]

  sm = original if legacy else SlottedOwner()
  with mock.patch.object(runtime, 'native_matches_cp', wraps=runtime.native_matches_cp) as profile:
    assert current(sm, cp) is not None
    assert current(sm, cp) is not None
    assert profile.call_count == 2


@pytest.mark.parametrize('profile_name', ['honda', 'ev6_two_pandas'])
def test_other_admitted_profiles_keep_full_validation(profile_name):
  if profile_name == 'honda':
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.honda.interface import CarInterface
    from opendbc.car.honda.values import CAR
    fingerprint = gen_empty_fingerprint()
    fingerprint[1][0x1A3] = 8
    cp = CarInterface.get_params(CAR.HONDA_ACCORD, fingerprint, [], False, False, False)
    cp.alternativeExperience = 32
  else:
    from openpilot.starpilot.tests.test_ev6_startup import params
    cp = params()
    cp.openpilotLongitudinalControl, cp.pcmCruise, cp.alternativeExperience = True, False, 32
    cp.safetyConfigs = [{'safetyModel': 'noOutput', 'safetyParam': 0},
                        {'safetyModel': 'hyundaiCanfd', 'safetyParam': 0x815}]
  state = bound_state(cp)
  sm = sm_for(cp, state)
  with mock.patch.object(runtime, 'native_matches_cp', wraps=runtime.native_matches_cp) as profile:
    assert current(sm, cp) == state
    assert current(sm, cp) == state
    assert profile.call_count == 2
  assert sm._aol_native_admission is None


def test_rejected_observation_then_valid_recovery_cannot_reuse_a_failed_verdict():
  cp = configured_cp()
  good = bound_state(cp)
  bad = replace(good, pandaSerial='other')
  sm = sm_for(cp, bad)
  with mock.patch.object(runtime, 'native_matches_cp', wraps=runtime.native_matches_cp) as profile:
    assert current(sm, cp) is None
    assert current(sm, cp) is None
    assert profile.call_count == 2
    assert sm._aol_native_admission is None
    receive(sm, good)
    assert current(sm, cp) == good
    assert current(sm, cp) == good
    assert profile.call_count == 3


def test_cache_key_failure_falls_back_to_complete_validation():
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  assert current(sm, cp) == state
  with mock.patch.object(runtime, 'native_admission_key', side_effect=RuntimeError('cache failure')), \
       mock.patch.object(runtime, 'native_matches_cp', wraps=runtime.native_matches_cp) as profile:
    assert current(sm, cp) == state
    assert current(sm, cp) == state
    assert profile.call_count == 2
  assert sm._aol_native_admission is None


@pytest.mark.parametrize('field,value', [('canValid', False), ('canTimeout', True),
                                         ('steerFaultTemporary', True), ('steerFaultPermanent', True)])
def test_live_car_state_veto_remains_after_native_cache_hit(field, value):
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  cs = car_state()
  assert transport_pause.healthy_transport(sm, cp, cs, state.axisSessionId, NOW)
  setattr(cs, field, value)
  assert current(sm, cp) == state
  assert not transport_pause.healthy_transport(sm, cp, cs, state.axisSessionId, NOW)


@pytest.mark.parametrize('field,value', [('controlsAllowed', False), ('safetyParam', 0),
                                         ('alternativeExperience', 32), ('safetyRxChecksInvalid', True)])
def test_latest_panda_permission_and_configuration_veto_a_native_cache_hit(field, value):
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  assert transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW)
  pandas = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=state.sourcePandaStatesMonoTime)
  pandas.pandaStates[0] = sm['pandaStates'][0]
  setattr(pandas.pandaStates[0], field, value)
  sm.update_msgs(NOW / 1e9, [pandas.as_reader()])
  assert current(sm, cp) == state
  assert not transport_pause.healthy_transport(sm, cp, car_state(), state.axisSessionId, NOW)


def test_cache_hit_uses_exact_original_inclusive_deadline():
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  with mock.patch.object(runtime, 'native_matches_cp', wraps=runtime.native_matches_cp) as profile:
    assert current(sm, cp) == state
    assert current(sm, cp, state.validUntilMonoTime) == state
    assert profile.call_count == 1
    assert current(sm, cp, state.validUntilMonoTime + 1) is None
  assert sm._aol_native_admission is None


def test_invalid_profile_keeps_original_short_circuit_with_missing_owner_stamp():
  cp = configured_cp()
  state = bound_state(cp)
  sm = sm_for(cp, state)
  cp.radarUnavailable = True
  sm.logMonoTime.pop('aolSafetyWire')
  assert current(sm, cp) is None
