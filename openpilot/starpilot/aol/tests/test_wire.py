"""Reserved Data transport rejects malformed or historically colliding payloads."""

import unittest
import struct
from unittest.mock import Mock, patch

from openpilot.cereal import custom, messaging
from openpilot.starpilot.aol.wire import (IntentState, SafetyState, MAX_WIRE_BYTES, decode_intent,
                                          decode_safety, encode_intent, encode_safety)


class AolWireTests(unittest.TestCase):
  def test_native_cpp_flat_fixture_decodes(self):
    # Exact output of test_aol_wire.cc (the native encoder test asserts it too).
    raw = bytes.fromhex('00000000090000000000000004000200010b0100010005006400000000000000' +
                        'c80000000000000022000000000000000500000032000000050000002a000000' +
                        '70616e64610000006178697300000000')
    self.assertEqual(decode_safety(raw), SafetyState(1, True, 100, 200, 5, 34,
                                                     True, False, True, False, 'panda', 'axis'))

  def test_roundtrip_immutable_and_bounded(self):
    intent = IntentState('card', 3, 100, 100, 120, True, False, True, True)
    safety = SafetyState(1, True, 100, 200, 5, 34, True, False, True, False, 'panda', 'axis')
    self.assertEqual(decode_intent(encode_intent(intent)), intent)
    self.assertEqual(decode_safety(encode_safety(safety)), safety)
    decoded = decode_intent(encode_intent(intent))
    self.assertIsNotNone(decoded)
    assert decoded is not None
    with self.assertRaises(AttributeError):
      decoded.__setattr__('allowedLatch', False)
    with self.assertRaises(ValueError):
      encode_intent(IntentState('x' * 97, 3, 100, 100, 120, True, False, True, True))

  def test_corrupt_wrong_kind_version_and_pointer_fail_closed(self):
    valid = encode_intent(IntentState('card', 3, 100, 100, 120, True, False, True, True))
    # Even a valid packed payload cannot trigger decompression on the flat path.
    packed_payload = bytes.fromhex('100950040257010b010105016401c8012211053211052a1f70616e64610f61786973')
    for bad in (b'', valid[:3], valid + b'X' * MAX_WIRE_BYTES, b'\xff' * 12,
                packed_payload,
                struct.pack('<II', 0, 0x7fffffff) + valid[8:],
                struct.pack('<II', 1, 1) + valid[8:],
                encode_safety(SafetyState(1, True, 100, 200, 5, 34, True, False, True, False, 'panda', 'axis'))):
      with self.subTest(bad=str(bad)[:8]):
        self.assertIsNone(decode_intent(bad))
    self.assertIsNone(Mock(wraps=decode_intent)(512))
    wrong_version = custom.AolAxisState.IntentWire.new_message(kind=2, version=2, producerSessionId='card')
    self.assertIsNone(decode_intent(wrong_version.to_bytes()))
    wrong_kind = custom.AolAxisState.SafetyWire.new_message(kind=2, version=1)
    self.assertIsNone(decode_safety(wrong_kind.to_bytes()))
    # Segment table agrees with length, but the root struct pointer is invalid.
    corrupt_pointer = bytearray(valid)
    corrupt_pointer[8:16] = b'\xff' * 8
    self.assertIsNone(decode_intent(bytes(corrupt_pointer)))
    # Invalid UTF-8 in a text pointer is rejected during immutable materialization.
    invalid_utf8 = bytearray(valid)
    invalid_utf8[valid.index(b'card')] = 0xff
    self.assertIsNone(decode_intent(bytes(invalid_utf8)))

  def test_historic_map_ordinals_never_select_aol(self):
    old_extended = messaging.new_message('mapdExtendedOut')
    old_input = messaging.new_message('mapdIn')
    self.assertEqual(str(old_extended.which()), 'mapdExtendedOut')
    self.assertEqual(str(old_input.which()), 'mapdIn')
    self.assertNotEqual(old_extended.which(), 'aolSafetyWire')
    self.assertNotEqual(old_input.which(), 'aolIntentWire')
    self.assertEqual(int(custom.MapdExtendedOut.schema.node.id), 0xa30662f84033036c)
    self.assertEqual(int(custom.MapdIn.schema.node.id), 0xc86a3d38d13eb3ef)


if __name__ == '__main__':
  unittest.main()
