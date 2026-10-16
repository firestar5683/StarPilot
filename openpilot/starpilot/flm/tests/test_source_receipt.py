"""Source receipt leaf decoding and unchanged generic fallback contracts."""
import math
import struct
from types import SimpleNamespace
from typing import TypedDict
import unittest

from capnp.lib.capnp import KjException, _DynamicStructReader
from openpilot.cereal import custom, log, messaging
from openpilot.starpilot.flm import learning_wire
from openpilot.starpilot.flm.runtime_adapter_registry import SourceState

NOW = 10_000_000_000
CP = 'c' * 64


class ReceiptFields(TypedDict):
  version: int
  enabled: bool
  manual: bool
  resetGeneration: str
  sourceEpoch: str
  observedMonoTime: int
  validUntilMonoTime: int
  cpSha256: str
  calibrationBasis: list[float]


FIELDS: ReceiptFields = {'version': 1, 'enabled': True, 'manual': False, 'resetGeneration': 'reset-1', 'sourceEpoch': 'b' * 64,
          'observedMonoTime': NOW, 'validUntilMonoTime': NOW + 500_000_000, 'cpSha256': CP,
          'calibrationBasis': [0.0, 0.0, 0.0]}
VALID_LOG = [
  'event.valid', 'event.autoSteeringLearning', 'outer.learning', 'learning.sourceReceipt',
  'row.version', 'row.cpSha256', 'row.cpSha256', 'row.observedMonoTime',
  'row.validUntilMonoTime', 'row.observedMonoTime', 'row.enabled', 'row.sourceEpoch',
  'row.resetGeneration', 'row.resetGeneration', 'row.calibrationBasis', 'row.calibrationBasis',
  'row.enabled', 'row.manual', 'row.resetGeneration', 'row.sourceEpoch', 'row.observedMonoTime',
  'row.validUntilMonoTime', 'row.cpSha256', 'row.calibrationBasis',
]


def native(*, reader=True, **changes):
  event = messaging.new_message('autoSteeringLearning', valid=True, logMonoTime=NOW)
  event.autoSteeringLearning.learning.sourceReceipt = {**FIELDS, **changes}
  return event.as_reader() if reader else event


def envelope(row, valid=True):
  return SimpleNamespace(valid=valid, autoSteeringLearning=SimpleNamespace(learning=SimpleNamespace(sourceReceipt=row)))


def expected(**changes):
  row: ReceiptFields = {**FIELDS, **changes}
  return SourceState(row['enabled'], row['manual'], row['resetGeneration'], row['sourceEpoch'],
                     row['observedMonoTime'], row['validUntilMonoTime'], row['cpSha256'], tuple(row['calibrationBasis']))


def signature(value):
  if value is None:
    return None
  return (type(value), value.enabled, value.manual, value.reset, value.source_epoch,
          value.observed_ns, value.expires_ns, value.cp_sha256,
          tuple(struct.pack('!d', item) for item in value.calibration))


class Logged:
  def __init__(self, values, accesses, label):
    self.values, self.accesses, self.label = values, accesses, label

  def __getattr__(self, name):
    self.accesses.append(self.label + '.' + name)
    if name not in self.values:
      raise AttributeError(name)
    value = self.values[name]
    if isinstance(value, Exception):
      raise value
    return value() if callable(value) else value


def traced(accesses, *, valid=True, **changes):
  row = Logged({**FIELDS, **changes}, accesses, 'row')
  learning = Logged({'sourceReceipt': row}, accesses, 'learning')
  outer = Logged({'learning': learning}, accesses, 'outer')
  return Logged({'valid': valid, 'autoSteeringLearning': outer}, accesses, 'event')


class TestSourceReceipt(unittest.TestCase):
  def assert_receipt(self, changes, wanted, *, now=NOW, cp=CP):
    builder = native(reader=False, **changes)
    # Builders retain the original generic body; both paths must meet an explicit result.
    for event in (builder.as_reader(), builder):
      value = learning_wire.read_source_receipt(event, now_ns=now, cp_sha256=cp)
      self.assertEqual(signature(value), signature(wanted))
    return value

  def test_native_schemas_and_enabled_manual_flags(self):
    event = native()
    row = event.autoSteeringLearning.learning.sourceReceipt
    self.assertIs(type(row), _DynamicStructReader)
    self.assertEqual(event.schema, log.Event.schema)
    self.assertEqual(event.autoSteeringLearning.schema, custom.StarPilotCarParams.schema)
    self.assertEqual(row.schema, custom.AutomaticLearningSourceReceipt.schema)
    for enabled, manual in ((True, False), (True, True), (False, False), (False, True)):
      with self.subTest(enabled=enabled, manual=manual):
        changes = {'enabled': enabled, 'manual': manual}
        self.assert_receipt(changes, expected(**changes))

  def test_version_identity_reset_and_time_boundaries(self):
    rows = (
      {'version': 0}, {'version': 2}, {'cpSha256': 'd' * 64}, {'cpSha256': 'invalid'},
      {'sourceEpoch': ''}, {'sourceEpoch': 'B' * 64}, {'resetGeneration': ''},
      {'resetGeneration': 'r' * 65}, {'enabled': False, 'resetGeneration': 'r' * 65},
      {'observedMonoTime': 0}, {'observedMonoTime': NOW + 1},
      {'validUntilMonoTime': NOW - 1}, {'validUntilMonoTime': NOW + 500_000_001},
    )
    for changes in rows:
      with self.subTest(changes=changes):
        self.assert_receipt(changes, None)
    for changes in ({'enabled': False, 'sourceEpoch': '', 'resetGeneration': ''},
                    {'resetGeneration': 'r' * 64}, {'validUntilMonoTime': NOW}):
      self.assert_receipt(changes, expected(**changes))
    for now, wanted in ((NOW - 1, None), (NOW, expected()),
                        (NOW + 500_000_000, expected()), (NOW + 500_000_001, None)):
      with self.subTest(now=now):
        self.assert_receipt({}, wanted, now=now)

  def test_calibration_lengths_nonfinite_and_signed_zero(self):
    for basis in ([], [0.0], [0.0, 0.0], [0.0] * 4, [math.nan, 0.0, 0.0],
                  [0.0, math.inf, 0.0], [0.0, 0.0, -math.inf]):
      with self.subTest(basis=basis):
        self.assert_receipt({'calibrationBasis': basis}, None)
    changes = {'calibrationBasis': [-0.0, 0.0, -0.0]}
    self.assert_receipt(changes, expected(**changes))

  def test_borrowed_reader_mutations_and_fresh_result_objects(self):
    builder = native(reader=False)
    borrowed = builder.as_reader()
    first = learning_wire.read_source_receipt(borrowed, now_ns=NOW, cp_sha256=CP)
    second = learning_wire.read_source_receipt(borrowed, now_ns=NOW, cp_sha256=CP)
    self.assertEqual(signature(first), signature(expected()))
    self.assertEqual(signature(second), signature(expected()))
    self.assertIsNot(first, second)
    rows = (('enabled', False), ('manual', True), ('version', 0), ('cpSha256', 'd' * 64),
            ('sourceEpoch', 'e' * 64), ('resetGeneration', 'reset-2'),
            ('observedMonoTime', NOW - 1), ('validUntilMonoTime', NOW + 1),
            ('calibrationBasis', [-0.0, 0.25, -0.5]))
    for field, value in rows:
      with self.subTest(field=field):
        builder.autoSteeringLearning.learning.sourceReceipt = FIELDS
        setattr(builder.autoSteeringLearning.learning.sourceReceipt, field, value)
        wanted = None if field in ('version', 'cpSha256', 'observedMonoTime') else expected(**{field: value})
        actual = learning_wire.read_source_receipt(borrowed, now_ns=NOW, cp_sha256=CP)
        self.assertEqual(signature(actual), signature(wanted))
    builder.autoSteeringLearning.learning.sourceReceipt = FIELDS
    self.assertEqual(signature(learning_wire.read_source_receipt(borrowed, now_ns=NOW, cp_sha256=CP)), signature(expected()))

  def test_custom_schema_spoof_and_wrong_native_schema_fallback(self):
    row = SimpleNamespace(**FIELDS, schema=custom.AutomaticLearningSourceReceipt.schema)
    actual = learning_wire.read_source_receipt(envelope(row), now_ns=NOW, cp_sha256=CP)
    self.assertEqual(signature(actual), signature(expected()))
    wrong = messaging.new_message('carState').as_reader().carState
    with self.assertRaises((AttributeError, ValueError, KjException)):
      learning_wire.read_source_receipt(envelope(wrong), now_ns=NOW, cp_sha256=CP)
    with self.assertRaises(AttributeError):
      learning_wire.read_source_receipt(envelope(None), now_ns=NOW, cp_sha256=CP)

  def test_custom_getter_short_circuit_order_and_exception(self):
    cases = (({'valid': False}, 1), ({'version': 0}, 5), ({'cpSha256': 'd' * 64}, 6),
             ({'observedMonoTime': NOW + 1}, 8), ({'sourceEpoch': ''}, 12),
             ({'resetGeneration': ''}, 13), ({'calibrationBasis': []}, 15))
    for changes, length in cases:
      with self.subTest(changes=changes):
        accesses = []
        self.assertIsNone(learning_wire.read_source_receipt(traced(accesses, **changes), now_ns=NOW, cp_sha256=CP))
        self.assertEqual(accesses, VALID_LOG[:length])
    accesses = []
    with self.assertRaisesRegex(RuntimeError, '^manual getter$'):
      learning_wire.read_source_receipt(traced(accesses, manual=RuntimeError('manual getter')), now_ns=NOW, cp_sha256=CP)
    self.assertEqual(accesses, VALID_LOG[:18])

  def test_stateful_custom_field_keeps_original_repeated_reads(self):
    accesses = []
    values = iter((CP, 'd' * 64, 'e' * 64))
    event = traced(accesses, cpSha256=lambda: next(values))
    actual = learning_wire.read_source_receipt(event, now_ns=NOW, cp_sha256=CP)
    self.assertEqual(signature(actual), signature(expected(cpSha256='e' * 64)))
    self.assertEqual(accesses, VALID_LOG)

  def test_nonbuiltin_clock_and_cp_arguments(self):
    class IntSubclass(int):
      pass

    class StrSubclass(str):
      pass

    class Clock:
      def __init__(self, accesses):
        self.accesses = accesses

      def __ge__(self, other):
        self.accesses.append(('ge', other))
        return NOW >= other

      def __le__(self, other):
        self.accesses.append(('le', other))
        return NOW <= other

    for now, cp, wanted in ((float(NOW), CP, expected()), (IntSubclass(NOW), CP, expected()),
                            (True, CP, None), (0.0, CP, None), (-0.0, CP, None), (math.nan, CP, None),
                            (NOW, StrSubclass(CP), expected()), (NOW, None, None)):
      with self.subTest(now=now, cp=cp):
        self.assert_receipt({}, wanted, now=now, cp=cp)
    accesses = []
    value = learning_wire.read_source_receipt(native(), now_ns=Clock(accesses), cp_sha256=CP)
    self.assertEqual(signature(value), signature(expected()))
    self.assertEqual(accesses, [('ge', NOW), ('le', NOW + 500_000_000)])


if __name__ == '__main__':
  unittest.main()
