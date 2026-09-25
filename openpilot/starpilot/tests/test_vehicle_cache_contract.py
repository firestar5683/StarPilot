import unittest
from dataclasses import replace
from unittest.mock import patch

from openpilot.cereal import log
from opendbc.car import structs
from openpilot.starpilot import schema_cache


class MemoryParams:
  def __init__(self):
    self.values = {}

  def get(self, key):
    return self.values.get(key)

  def put(self, key, value, block=False):
    self.values[key] = value


class TestVehicleCacheContract(unittest.TestCase):
  def test_previous_vehicle_flags_require_fresh_identification(self):
    for key in ('CarParamsCache', 'CarParamsPersistent', 'CarParamsPrevRoute'):
      with self.subTest(key=key):
        params = MemoryParams()
        cp = structs.CarParams(carFingerprint='CHRYSLER_PACIFICA_2020', flags=2)
        current = schema_cache.CONTRACTS[key]
        previous = replace(current, producer='identified-car-params-v1')
        with patch.dict(schema_cache.CONTRACTS, {key: previous}):
          schema_cache.put_cache(params, key, cp, block=True)
          self.assertIsNotNone(schema_cache.get_cache(params, key))
        original = params.values.copy()
        self.assertIsNone(schema_cache.get_cache(params, key))
        self.assertEqual(schema_cache.inspect_cache(key, params.get(key)).status, 'incompatible')
        self.assertEqual(params.values, original)
        schema_cache.put_cache(params, key, cp, block=True)
        self.assertIsNotNone(schema_cache.get_cache(params, key))

  def test_vehicle_epoch_does_not_invalidate_calibration_or_learned_values(self):
    params = MemoryParams()
    params.put('CustomPreference', b'user-choice')
    for key, contract in schema_cache.CONTRACTS.items():
      if contract.service is None:
        continue
      event = log.Event.new_message()
      event.init(contract.service)
      schema_cache.put_cache(params, key, event, block=True)
    original = params.values.copy()
    for key, contract in schema_cache.CONTRACTS.items():
      if contract.service is not None:
        self.assertIsNotNone(schema_cache.get_cache(params, key), key)
    self.assertEqual(params.values, original)
