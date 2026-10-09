"""Strict, bounded AOL payloads in the reserved Event Data envelopes.

The outer Event remains Data at ordinals 124/125. The inner payload is flat
Cap'n Proto with its own version and kind; no caller consumes a raw reader.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct

import capnp
from openpilot.cereal import custom

SAFETY_SERVICE = 'aolSafetyWire'
INTENT_SERVICE = 'aolIntentWire'
SAFETY_KIND = 1
INTENT_KIND = 2
WIRE_VERSION = 1
MAX_WIRE_BYTES = 512
MAX_WIRE_WORDS = (MAX_WIRE_BYTES - 8) // 8
MAX_ID_BYTES = 96


@dataclass(frozen=True)
class SafetyState:
  protocolVersion: int
  compatible: bool
  observedMonoTime: int
  validUntilMonoTime: int
  safetyModel: int
  safetyParam: int
  lateralAllowed: bool
  longitudinalAllowed: bool
  requestedLateral: bool
  requestedLongitudinal: bool
  pandaSerial: str
  axisSessionId: str


@dataclass(frozen=True)
class IntentState:
  producerSessionId: str
  sequence: int
  carStateLogMonoTime: int
  observedMonoTime: int
  validUntilMonoTime: int
  allowedLatch: bool
  pauseLateral: bool
  pauseLongitudinal: bool
  settingsQualified: bool
  lateralArmed: bool = False
  optionalSetRelease: bool = False


def _bounded_id(value: str) -> str:
  if not isinstance(value, str) or len(value.encode('utf-8')) > MAX_ID_BYTES:
    raise ValueError('AOL wire identifier is invalid')
  return value


def _payload(raw_value, schema, kind: int):
  if not isinstance(raw_value, (bytes, bytearray, memoryview)):
    return None
  byte_count = raw_value.nbytes if isinstance(raw_value, memoryview) else len(raw_value)
  if not 16 <= byte_count <= MAX_WIRE_BYTES or byte_count % 8:
    return None
  try:
    raw = bytes(raw_value)
    if len(raw) != byte_count:
      return None
    segment_count_minus_one, segment_words = struct.unpack_from('<II', raw)
    if segment_count_minus_one != 0 or segment_words > MAX_WIRE_WORDS or len(raw) != 8 + 8 * segment_words:
      return None
    with schema.from_bytes(raw, traversal_limit_in_words=MAX_WIRE_WORDS, nesting_limit=4) as decoded:
      if int(decoded.kind) != kind or int(decoded.version) != WIRE_VERSION:
        return None
      return decoded.to_dict()
  except (ValueError, OverflowError, RuntimeError, UnicodeDecodeError, capnp.KjException):
    return None


def _memoized(decode):
  # Consumers poll at 100 Hz while wires change at 10-100 Hz; results are frozen, so reuse the last exact-bytes decode.
  last = [None, None]

  def wrapper(raw):
    key = bytes(raw) if isinstance(raw, (bytes, bytearray, memoryview)) else None
    if key is None:
      return decode(raw)
    if last[0] != key:
      last[0], last[1] = key, decode(key)
    return last[1]
  wrapper.__wrapped__ = decode
  return wrapper


@_memoized
def decode_safety(raw: bytes) -> SafetyState | None:
  value = _payload(raw, custom.AolAxisState.SafetyWire, SAFETY_KIND)
  if value is None:
    return None
  try:
    result = SafetyState(int(value['protocolVersion']), bool(value['compatible']), int(value['observedMonoTime']),
                         int(value['validUntilMonoTime']), int(value['safetyModel']), int(value['safetyParam']),
                         bool(value['lateralAllowed']), bool(value['longitudinalAllowed']), bool(value['requestedLateral']),
                         bool(value['requestedLongitudinal']), _bounded_id(str(value.get('pandaSerial', ''))),
                         _bounded_id(str(value.get('axisSessionId', ''))))
    if result.validUntilMonoTime < result.observedMonoTime:
      return None
    return result
  except (KeyError, ValueError, OverflowError, RuntimeError, capnp.KjException):
    return None


@_memoized
def decode_intent(raw: bytes) -> IntentState | None:
  value = _payload(raw, custom.AolAxisState.IntentWire, INTENT_KIND)
  if value is None:
    return None
  try:
    result = IntentState(_bounded_id(str(value.get('producerSessionId', ''))), int(value['sequence']),
                         int(value['carStateLogMonoTime']), int(value['observedMonoTime']), int(value['validUntilMonoTime']),
                         bool(value['allowedLatch']), bool(value['pauseLateral']), bool(value['pauseLongitudinal']),
                         bool(value['settingsQualified']), bool(value.get('lateralArmed', False)), bool(value.get('optionalSetRelease', False)))
    if result.validUntilMonoTime < result.observedMonoTime:
      return None
    return result
  except (KeyError, ValueError, OverflowError, RuntimeError, capnp.KjException):
    return None


def encode_intent(value: IntentState) -> bytes:
  _bounded_id(value.producerSessionId)
  message = custom.AolAxisState.IntentWire.new_message(
    kind=INTENT_KIND, version=WIRE_VERSION, producerSessionId=value.producerSessionId,
    sequence=value.sequence, carStateLogMonoTime=value.carStateLogMonoTime,
    observedMonoTime=value.observedMonoTime, validUntilMonoTime=value.validUntilMonoTime,
    allowedLatch=value.allowedLatch, pauseLateral=value.pauseLateral,
    pauseLongitudinal=value.pauseLongitudinal, settingsQualified=value.settingsQualified,
    lateralArmed=value.lateralArmed, optionalSetRelease=value.optionalSetRelease)
  data = message.to_bytes()
  if len(data) > MAX_WIRE_BYTES:
    raise ValueError('AOL intent payload exceeds wire bound')
  return data


def encode_safety(value: SafetyState) -> bytes:
  _bounded_id(value.pandaSerial)
  _bounded_id(value.axisSessionId)
  message = custom.AolAxisState.SafetyWire.new_message(
    kind=SAFETY_KIND, version=WIRE_VERSION, protocolVersion=value.protocolVersion,
    compatible=value.compatible, observedMonoTime=value.observedMonoTime,
    validUntilMonoTime=value.validUntilMonoTime, safetyModel=value.safetyModel,
    safetyParam=value.safetyParam, lateralAllowed=value.lateralAllowed,
    longitudinalAllowed=value.longitudinalAllowed, requestedLateral=value.requestedLateral,
    requestedLongitudinal=value.requestedLongitudinal, pandaSerial=value.pandaSerial,
    axisSessionId=value.axisSessionId)
  data = message.to_bytes()
  if len(data) > MAX_WIRE_BYTES:
    raise ValueError('AOL safety payload exceeds wire bound')
  return data
