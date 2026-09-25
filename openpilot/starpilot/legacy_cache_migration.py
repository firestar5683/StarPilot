import math

import capnp

from openpilot.starpilot import schema_cache as cache


LEGACY_CALIBRATION_FIELDS = {
  "calStatus": (11, "Status"), "calCycle": (2, "Int32"), "calPerc": (3, "Int8"),
  "validBlocks": (9, "Int32"), "extrinsicMatrix": (4, "List(Float32)"),
  "rpyCalib": (7, "List(Float32)"), "rpyCalibSpread": (8, "List(Float32)"),
  "wideFromDeviceEuler": (10, "List(Float32)"), "height": (12, "List(Float32)"),
}


class LegacyCalibrationError(ValueError):
  pass


class _EnvelopeSink:
  def put(self, key, value, *, block):
    self.raw = value


def _validate_calibration(values):
  for key, lengths in (("rpyCalib", (3,)), ("wideFromDeviceEuler", (3,)),
                       ("height", (1,)), ("rpyCalibSpread", (0, 3)), ("extrinsicMatrix", (0, 12))):
    vector = values[key]
    if len(vector) not in lengths or any(not math.isfinite(value) for value in vector):
      raise LegacyCalibrationError(f"Invalid legacy calibration {key}")
  if not 0 <= values["validBlocks"] <= 50 or not 0 <= values["calPerc"] <= 100 or values["calCycle"] < 0:
    raise LegacyCalibrationError("Invalid legacy calibration progress")
  if values["calStatus"] not in ("uncalibrated", "calibrated", "invalid", "recalibrating"):
    raise LegacyCalibrationError("Invalid legacy calibration status")
  rpy = values["rpyCalib"]
  if abs(rpy[0]) > math.pi or not -0.15 <= rpy[1] <= 0.23 or abs(rpy[2]) > 0.075:
    raise LegacyCalibrationError("Legacy calibration angles exceed producer limits")
  if any(abs(value) > math.pi for value in values["wideFromDeviceEuler"]) or not 0 < values["height"][0] < 10:
    raise LegacyCalibrationError("Invalid legacy calibration camera geometry")
  if any(value < 0 or value > math.pi for value in values["rpyCalibSpread"]):
    raise LegacyCalibrationError("Invalid legacy calibration spread")


def migrate_legacy_cache(key, raw):
  inspected = cache.inspect_cache(key, raw)
  if inspected.status == "valid":
    return raw
  if key != "CalibrationParams":
    return None
  if not raw or raw.startswith(cache.MAGIC) or len(raw) > cache.MAX_PAYLOAD_BYTES:
    raise LegacyCalibrationError("Unsupported legacy calibration encoding")
  try:
    with cache.CONTRACTS[key].root.from_bytes(raw, traversal_limit_in_words=cache.MAX_PAYLOAD_BYTES // 8) as source:
      if source.which() != "extrinsicsCalibration":
        raise LegacyCalibrationError("Legacy calibration has the wrong Event service")
      selected = source.extrinsicsCalibration
      values = {name: getattr(selected, name) for name in LEGACY_CALIBRATION_FIELDS}
      values = {name: list(value) if field_type.startswith("List") else str(value) if field_type == "Status" else value
                for name, value in values.items() for _, field_type in (LEGACY_CALIBRATION_FIELDS[name],)}
      _validate_calibration(values)
      converted = cache.CONTRACTS[key].root.new_message(
        logMonoTime=source.logMonoTime, valid=source.valid, extrinsicsCalibration=values,
      )
      sink = _EnvelopeSink()
      cache.put_cache(sink, key, converted, block=True)
      check = cache.inspect_cache(key, sink.raw)
      if check.status != "valid":
        raise LegacyCalibrationError("Converted calibration envelope failed validation")
      with cache.CONTRACTS[key].root.from_bytes(check.payload) as result:
        if any(getattr(result.extrinsicsCalibration, name) != getattr(converted.extrinsicsCalibration, name)
               for name, (_, field_type) in LEGACY_CALIBRATION_FIELDS.items() if not field_type.startswith("List")):
          raise LegacyCalibrationError("Converted calibration scalar readback differs")
        for name, (_, field_type) in LEGACY_CALIBRATION_FIELDS.items():
          if field_type.startswith("List") and list(getattr(result.extrinsicsCalibration, name)) != values[name]:
            raise LegacyCalibrationError("Converted calibration vector readback differs")
        if result.logMonoTime != source.logMonoTime or result.valid != source.valid:
          raise LegacyCalibrationError("Converted calibration metadata readback differs")
      return sink.raw
  except LegacyCalibrationError:
    raise
  except (capnp.KjException, ValueError, TypeError, OverflowError) as error:
    raise LegacyCalibrationError("Legacy calibration could not be decoded completely") from error
