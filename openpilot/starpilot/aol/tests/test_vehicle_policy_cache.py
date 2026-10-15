"""Exact CarParams snapshots may cache policy; live authority remains current."""

from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from unittest.mock import Mock, patch
import warnings

import pytest
from capnp import KjException

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.car_helpers import interfaces
from opendbc.car.ford.values import CAR as FORD
from opendbc.car.gm.values import CAR as GM
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.hyundai.values import CAR as HYUNDAI
from opendbc.car.mazda.values import CAR as MAZDA
from opendbc.car.tesla.fingerprints import FINGERPRINTS as TESLA_FINGERPRINTS
from opendbc.car.tesla.values import CAR as TESLA
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.starpilot.aol import vehicle


@pytest.fixture(autouse=True)
def clear_policy_cache():
  vehicle._policy_for_bytes.cache_clear()
  yield
  vehicle._policy_for_bytes.cache_clear()


def profile(brand):
  """Factory inputs from each port's existing positive admission fixtures."""
  models = {'honda': HONDA.HONDA_CIVIC_BOSCH, 'hyundai': HYUNDAI.HYUNDAI_SONATA,
            'gm': GM.CHEVROLET_BOLT_CC_2018_2021, 'ford': FORD.FORD_ESCAPE_MK4,
            'mazda': MAZDA.MAZDA_CX5_2022, 'tesla': TESLA.TESLA_MODEL_S_PREAP,
            'toyota': TOYOTA.TOYOTA_COROLLA_TSS2}
  fp = gen_empty_fingerprint()
  if brand == 'gm':
    fp[0][0x201] = 6
    fp[2].update({0x320: 8, 0x180: 4})
  elif brand == 'ford':
    fp[0][0x5A] = 8
    fp[2].update({0x3D6: 8, 0x186: 8})
  elif brand == 'tesla':
    fp[0] = dict(TESLA_FINGERPRINTS[models[brand]][0])
  return interfaces[models[brand]].get_params(models[brand], fp, [], brand == 'honda', False, False)


def assert_equivalent(cp):
  expected = vehicle._policy_for_uncached(cp)
  assert vehicle.policy_for(cp) == expected
  assert vehicle.policy_for(cp.as_reader()) == expected
  return expected


@pytest.mark.parametrize('brand', ('honda', 'hyundai', 'gm', 'ford', 'mazda', 'tesla', 'toyota'))
def test_actual_port_profile_and_startup_marking_match(brand):
  cp = profile(brand)
  initial = assert_equivalent(cp)
  assert initial.intent_supported, brand
  cp.safetyConfigs[-1].safetyParam |= initial.safety_param_addition
  cp.alternativeExperience |= initial.alternative_experience_addition
  marked = assert_equivalent(cp)
  assert marked.intent_supported and marked.runtime_supported
  assert vehicle.native_matches_cp(cp, int(cp.safetyConfigs[-1].safetyModel.raw), cp.safetyConfigs[-1].safetyParam)


@pytest.mark.parametrize('control', ('torque', 'pid', 'angle'))
def test_controller_variants_match(control):
  cp = profile('toyota')
  cp.steerControlType = 'angle' if control == 'angle' else 'torque'
  cp.lateralTuning.init('pid' if control == 'pid' else 'torque')
  assert_equivalent(cp)


@pytest.mark.parametrize('field', ('brand', 'carFingerprint', 'flags', 'passive', 'notCar', 'dashcamOnly',
                                  'pcmCruise', 'openpilotLongitudinalControl', 'alternativeExperience',
                                  'safetyParam', 'safetyModel', 'safetyConfigs', 'lateralTuning', 'carVin'))
def test_mutable_builder_and_alias_reader_never_reuse_a_prior_snapshot(field):
  cp = profile('toyota')
  alias = cp.as_reader()
  accepted = vehicle.policy_for(cp)
  assert accepted.intent_supported
  before_key = vehicle._car_params_bytes(cp)
  before = vehicle._policy_for_bytes.cache_info()
  if field == 'safetyParam':
    cp.safetyConfigs[0].safetyParam ^= 1
  elif field == 'safetyModel':
    cp.safetyConfigs[0].safetyModel = 'noOutput'
  elif field == 'safetyConfigs':
    cp.safetyConfigs = []
  elif field == 'lateralTuning':
    cp.lateralTuning.init('pid')
  elif field in ('passive', 'notCar', 'dashcamOnly', 'pcmCruise', 'openpilotLongitudinalControl'):
    setattr(cp, field, not getattr(cp, field))
  else:
    setattr(cp, field, {'brand': 'unregistered', 'carFingerprint': 'unregistered', 'flags': int(cp.flags) ^ 1,
                        'alternativeExperience': 1, 'carVin': 'CACHE-MUTATION'}[field])
  assert vehicle._car_params_bytes(cp) != before_key
  expected = vehicle._policy_for_uncached(cp)
  assert vehicle.policy_for(cp) == vehicle.policy_for(alias) == expected
  after = vehicle._policy_for_bytes.cache_info()
  assert after.misses == before.misses + 1
  assert after.hits == before.hits + 1
  if field in ('brand', 'carFingerprint', 'passive', 'notCar', 'dashcamOnly', 'safetyModel', 'safetyConfigs'):
    assert not expected.intent_supported


def test_duck_types_and_schema_spoofs_bypass_serialization_untouched(monkeypatch):
  sentinel = vehicle.AolVehiclePolicy(settings_supported=True)
  owner = SimpleNamespace(policy_for=Mock(return_value=sentinel))
  monkeypatch.setitem(vehicle._PORTS, 'cache-test', owner)
  for schema in (None, structs.CarParams.schema):
    cp = SimpleNamespace(brand='cache-test', schema=schema, to_bytes=Mock(side_effect=AssertionError),
                         copy=Mock(side_effect=AssertionError), as_builder=Mock(side_effect=AssertionError))
    assert vehicle._car_params_bytes(cp) is None
    assert vehicle.policy_for(cp) is sentinel
    owner.policy_for.assert_called_with(cp)
    cp.to_bytes.assert_not_called()
    cp.copy.assert_not_called()
    cp.as_builder.assert_not_called()

  class HostileMeta(type):
    def __eq__(cls, other):
      raise AssertionError('Unknown type equality must not run')

  class Unknown(metaclass=HostileMeta):
    brand = 'cache-test'

    @property
    def schema(self):
      raise AssertionError('Unknown schema must not be read')

  assert vehicle._car_params_bytes(Unknown()) is None
  assert vehicle.policy_for(Unknown()) is sentinel
  assert vehicle._policy_for_bytes.cache_info().misses == 0


def outcome(call, cp):
  try:
    return ('result', call(cp))
  except Exception as exc:
    return ('exception', type(exc), str(exc))


def test_malformed_wrong_schema_and_original_exceptions_are_preserved(monkeypatch):
  wrong = structs.CarState(canValid=True)
  for cp in (None, b'not a CarParams message', object(), SimpleNamespace(brand=[]), wrong, wrong.as_reader()):
    assert vehicle._car_params_bytes(cp) is None
    assert outcome(vehicle.policy_for, cp) == outcome(vehicle._policy_for_uncached, cp)
  owner = SimpleNamespace(policy_for=Mock(side_effect=RuntimeError('original dispatcher exception')))
  monkeypatch.setitem(vehicle._PORTS, 'cache-test', owner)
  cp = SimpleNamespace(brand='cache-test')
  assert outcome(vehicle.policy_for, cp) == outcome(vehicle._policy_for_uncached, cp)
  with pytest.raises((ValueError, KjException)):
    vehicle._policy_for_bytes(b'not a CarParams message')


def test_serialization_and_decode_failure_fall_back_to_original_builder(monkeypatch):
  cp = profile('toyota')
  expected = vehicle._policy_for_uncached(cp)

  class BrokenSchema:
    @property
    def schema(self):
      raise RuntimeError('schema unavailable')

  with monkeypatch.context() as broken:
    broken.setattr(vehicle, 'CarParams', BrokenSchema())
    assert vehicle._car_params_bytes(cp) is None
    assert vehicle.policy_for(cp) == expected
  decoder = SimpleNamespace(schema=structs.CarParams.schema, from_bytes=Mock(side_effect=RuntimeError('decode unavailable')))
  monkeypatch.setattr(vehicle, 'CarParams', decoder)
  with patch.object(vehicle, '_policy_for_uncached', wraps=vehicle._policy_for_uncached) as uncached:
    assert vehicle.policy_for(cp) == expected
    uncached.assert_called_once_with(cp)
  decoder.from_bytes.assert_called_once()


def test_original_builder_write_state_and_repeat_warning_are_unchanged():
  cp = profile('toyota')
  with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    for _ in range(4):
      assert_equivalent(cp)
    assert not caught
    cp.to_bytes()
    assert not caught
    cp.to_bytes()
    assert any('already been written' in str(item.message) for item in caught)


def test_lru_bound_oversize_bypass_and_frozen_result():
  cp = profile('toyota')
  for index in range(9):
    cp.carVin = str(index)
    assert_equivalent(cp)
  info = vehicle._policy_for_bytes.cache_info()
  assert info.maxsize == info.currsize == 8
  cp.carVin = '0'
  vehicle.policy_for(cp)
  assert vehicle._policy_for_bytes.cache_info().misses == info.misses + 1
  cp.carVin = 'v' * (64 * 1024)
  before = vehicle._policy_for_bytes.cache_info()
  assert vehicle._car_params_bytes(cp) is None
  result = vehicle.policy_for(cp)
  assert result == vehicle._policy_for_uncached(cp)
  assert vehicle._policy_for_bytes.cache_info() == before
  with pytest.raises(FrozenInstanceError):
    result.__setattr__('intent_supported', False)


def test_warm_policy_does_not_cache_current_state_or_native_permission():
  cp = profile('mazda')
  cp.alternativeExperience = 32
  assert vehicle.policy_for(cp).ordinary_axis_ack_required
  assert vehicle.policy_for(cp).intent_supported
  cs = structs.CarState(canValid=True, canTimeout=False, gearShifter='drive', vEgo=20)
  native = SimpleNamespace(safetyModel=int(cp.safetyConfigs[0].safetyModel.raw),
                           safetyParam=cp.safetyConfigs[0].safetyParam, requestedLateral=True, lateralAllowed=True)
  assert vehicle.ordinary_axis_request_allowed(cp, cs)
  assert not vehicle.native_latch_rejected(cp, native, state=cs)
  native.lateralAllowed = False
  assert vehicle.native_latch_rejected(cp, native, state=cs)
  cs.canValid = False
  assert not vehicle.ordinary_axis_request_allowed(cp, cs)
  cs.canValid, cs.steerFaultPermanent = True, True
  assert not vehicle.ordinary_axis_request_allowed(cp, cs)
  cs.steerFaultPermanent, cs.steerFaultTemporary = False, True
  assert not vehicle.native_latch_rejected(cp, native, state=cs)
  native.safetyParam ^= 1
  assert not vehicle.native_matches_cp(cp, native.safetyModel, native.safetyParam)
