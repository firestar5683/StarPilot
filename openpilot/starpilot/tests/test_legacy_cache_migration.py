import math
import os
import tempfile
import unittest
from pathlib import Path

import capnp

from openpilot.cereal import log
from openpilot.starpilot import schema_cache as cache
from openpilot.starpilot.legacy_cache_migration import LEGACY_CALIBRATION_FIELDS, LegacyCalibrationError, migrate_legacy_cache


LEGACY_SCHEMA = """@0xbcb0a0a1d008d210;
struct LiveCalibrationData {
  calStatus @11 :Status;
  calCycle @2 :Int32;
  calPerc @3 :Int8;
  validBlocks @9 :Int32;
  extrinsicMatrix @4 :List(Float32);
  rpyCalib @7 :List(Float32);
  rpyCalibSpread @8 :List(Float32);
  wideFromDeviceEuler @10 :List(Float32);
  height @12 :List(Float32);
  warpMatrixDEPRECATED @0 :List(Float32);
  calStatusDEPRECATED @1 :Int8;
  warpMatrix2DEPRECATED @5 :List(Float32);
  warpMatrixBigDEPRECATED @6 :List(Float32);
  enum Status { uncalibrated @0; calibrated @1; invalid @2; recalibrating @3; }
}
"""


def calibration(**changes):
  values = {"calStatus": "calibrated", "calCycle": 2, "calPerc": 100, "validBlocks": 37,
                "rpyCalib": [0, 0.02, -0.01], "rpyCalibSpread": [0, 0.001, 0.002],
                "wideFromDeviceEuler": [0, 0.01, 0], "height": [1.22], "extrinsicMatrix": []}
  values.update(changes)
  return log.Event.new_message(logMonoTime=987654321, valid=True, extrinsicsCalibration=values)


def active_values(message):
  return {name: list(getattr(message, name)) if field_type.startswith("List") else str(getattr(message, name))
          if field_type == "Status" else getattr(message, name)
          for name, (_, field_type) in LEGACY_CALIBRATION_FIELDS.items()}


class TestLegacyCacheMigration(unittest.TestCase):
  def test_original_struct_wire_layout_and_active_values(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "legacy-calibration.capnp"
      path.write_text(LEGACY_SCHEMA)
      legacy = capnp.load(str(path)).LiveCalibrationData
      old = legacy.new_message(calStatus="calibrated", calCycle=2, calPerc=100, validBlocks=37,
                               rpyCalib=[0, 0.02, -0.01], rpyCalibSpread=[0, 0.001, 0.002],
                               wideFromDeviceEuler=[0, 0.01, 0], height=[1.22])
      with log.ExtrinsicsCalibration.from_bytes(old.to_bytes()) as decoded:
        self.assertEqual(decoded.calStatus, "calibrated")
        self.assertEqual(decoded.validBlocks, 37)
        self.assertEqual(list(decoded.rpyCalib), list(old.rpyCalib))
        values = {key: value for key, value in decoded.to_dict().items() if key != "deprecated"}
      message = log.Event.new_message(logMonoTime=987654321, valid=True, extrinsicsCalibration=values)
      converted = migrate_legacy_cache("CalibrationParams", message.to_bytes())
      payload = cache.inspect_cache("CalibrationParams", converted).payload
      with log.Event.from_bytes(payload) as result:
        self.assertEqual(result.logMonoTime, 987654321)
        self.assertEqual(active_values(result.extrinsicsCalibration), active_values(message.extrinsicsCalibration))

  def test_real_dom_fixture_when_supplied(self):
    fixture = os.environ.get("STARPILOT_DOM_CALIBRATION_FIXTURE")
    if fixture is None:
      self.skipTest("Private original-device fixture supplied only during qualification")
    raw = Path(fixture).read_bytes()
    converted = migrate_legacy_cache("CalibrationParams", raw)
    payload = cache.inspect_cache("CalibrationParams", converted).payload
    with log.Event.from_bytes(raw) as source, log.Event.from_bytes(payload) as result:
      self.assertEqual(result.logMonoTime, source.logMonoTime)
      self.assertEqual(result.valid, source.valid)
      self.assertEqual(active_values(result.extrinsicsCalibration), active_values(source.extrinsicsCalibration))

  def test_invalid_calibration_is_never_silently_reset(self):
    for changes in ({"rpyCalib": [0, 0]}, {"rpyCalib": [0, math.nan, 0]}, {"height": []},
                    {"validBlocks": 51}, {"calPerc": -1}, {"rpyCalib": [0, 2, 0]}):
      with self.subTest(changes=changes), self.assertRaises(LegacyCalibrationError):
        migrate_legacy_cache("CalibrationParams", calibration(**changes).to_bytes())

  def test_wrong_service_and_bad_encoding_rejected(self):
    for raw in (b"broken", log.Event.new_message(lateralDelay={}).to_bytes()):
      with self.subTest(raw=raw), self.assertRaises(LegacyCalibrationError):
        migrate_legacy_cache("CalibrationParams", raw)

  def test_valid_envelope_preserved_and_other_legacy_caches_retired(self):
    class Sink:
      def put(self, key, raw, **kwargs):
        self.raw = raw
    sink = Sink()
    cache.put_cache(sink, "CalibrationParams", calibration(), block=True)
    self.assertEqual(migrate_legacy_cache("CalibrationParams", sink.raw), sink.raw)
    for key in cache.CACHE_KEYS - {"CalibrationParams"}:
      with self.subTest(key=key):
        self.assertIsNone(migrate_legacy_cache(key, b"legacy cache"))


if __name__ == "__main__":
  unittest.main()
