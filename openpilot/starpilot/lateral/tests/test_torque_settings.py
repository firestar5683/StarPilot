"""Versioned Torque preference document against real temporary Params."""

from pathlib import Path
import json
import unittest

from openpilot.common.params import ParamKeyType, Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.lateral.torque_runtime import TorqueHost, read_settings
from openpilot.starpilot.lateral.torque_settings import (
  DOCUMENT_KEY, LEGACY_KEYS, FieldChoice, LegacyMode, PlatformProfile, interpret_legacy, parse_document,
  replace_field, resolve_document, serialize_document,
)
from opendbc.car.car_helpers import interfaces


def corolla():
  return interfaces["TOYOTA_COROLLA_TSS2"].get_non_essential_params("TOYOTA_COROLLA_TSS2")


class TorqueDocumentTests(unittest.TestCase):
  def test_native_key_is_optional_nondefault_json(self):
    with OpenpilotPrefix():
      params = Params()
      self.assertEqual(params.get_type(DOCUMENT_KEY), ParamKeyType.JSON)
      self.assertIsNone(params.get(DOCUMENT_KEY, return_default=True))

  def test_legacy_absence_and_explicit_document_ignore_old_bytes(self):
    with OpenpilotPrefix():
      params = Params()
      host = TorqueHost(params, corolla())
      basis = (host.vehicle.lat_accel_factor, host.vehicle.lat_accel_offset, host.vehicle.friction)
      params.put_bool("AdvancedLateralTune", True, block=True)
      old_factor = basis[0] * 1.2
      params.put("SteerLatAccel", old_factor, block=True)
      before = {key: Path(params.get_param_path(key)).read_bytes() if Path(params.get_param_path(key)).exists() else None
                for key in LEGACY_KEYS}
      self.assertEqual(read_settings(params, host.vehicle).user_factor, old_factor)
      raw = serialize_document({host.vehicle.vehicle: PlatformProfile(basis, FieldChoice("custom", basis[0]), FieldChoice())})
      params.put(DOCUMENT_KEY, json.loads(raw), block=True)
      after = read_settings(params, host.vehicle)
      self.assertTrue(after.valid)
      self.assertIsNone(after.user_factor)
      self.assertEqual(parse_document(raw)[host.vehicle.vehicle].factor.mode, "custom")
      self.assertEqual({key: Path(params.get_param_path(key)).read_bytes() if Path(params.get_param_path(key)).exists() else None
                        for key in LEGACY_KEYS}, before)

  def test_partial_fields_round_trip_and_model_scope(self):
    cp = corolla()
    host = TorqueHost(Params(), cp)
    basis = (host.vehicle.lat_accel_factor, host.vehicle.lat_accel_offset, host.vehicle.friction)
    profiles = replace_field({}, host.vehicle.vehicle, basis, "factor", "custom", basis[0] * 1.1)
    profiles = replace_field(profiles, host.vehicle.vehicle, basis, "friction", "custom", basis[2] * 1.2)
    profiles = replace_field(profiles, host.vehicle.vehicle, basis, "factor", "source", None)
    parsed = parse_document(serialize_document(profiles))
    self.assertEqual(parsed[host.vehicle.vehicle].factor.custom_value, basis[0] * 1.1)
    self.assertEqual(resolve_document(parsed, host.vehicle.vehicle, basis), (None, basis[2] * 1.2, False))
    self.assertEqual(resolve_document(parsed, "TOYOTA_CAMRY", basis), (None, None, False))
    changed_basis = (basis[0] * 1.1, basis[1], basis[2])
    self.assertEqual(resolve_document(parsed, host.vehicle.vehicle, changed_basis), (None, None, True))

  def test_bad_document_fails_closed_without_legacy_fallback(self):
    with OpenpilotPrefix():
      params = Params()
      host = TorqueHost(params, corolla())
      params.put_bool("AdvancedLateralTune", True, block=True)
      params.put("SteerLatAccel", host.vehicle.lat_accel_factor * 1.2, block=True)
      for raw in (b"{}", b'{"schemaVersion":1,"schemaVersion":1,"vehicles":{}}',
                  b'{"schemaVersion":1,"vehicles":{"TOYOTA_COROLLA_TSS2":{"basis":{},"factor":{},"friction":{}}}}',
                  b'[' * 1100 + b'0' + b']' * 1100,
                  b'{"schemaVersion":1,"vehicles":{}}' + b' ' * 20_000,
                  b'{"schemaVersion":' + b'9' * 5000 + b',"vehicles":{}}',
                  b'{"schemaVersion":1,"vehicles":{"TOYOTA_COROLLA_TSS2":{"basis":{"latAccelFactor":' +
                  b'9' * 350 + b',"latAccelOffset":0,"friction":0},"factor":{"mode":"source","customValue":null},' +
                  b'"friction":{"mode":"source","customValue":null}}}}'):
        Path(params.get_param_path(DOCUMENT_KEY)).write_bytes(raw)
        self.assertFalse(read_settings(params, host.vehicle).valid)
        self.assertEqual(Path(params.get_param_path(DOCUMENT_KEY)).read_bytes(), raw)

  def test_shared_legacy_parser_rejects_bad_stock_marker(self):
    basis = (2.0, 0.1, 0.12)
    with self.assertRaises(ValueError):
      interpret_legacy({"SteerLatAccel": b"2.1", "SteerLatAccelStock": b"bad"}, basis)
    old_stock = interpret_legacy({"SteerLatAccel": b"2.2", "SteerLatAccelStock": b"2.2"}, basis)
    self.assertEqual((old_stock.factor_mode, old_stock.factor, old_stock.factor_saved),
                     (LegacyMode.STOCK, None, 2.2))
