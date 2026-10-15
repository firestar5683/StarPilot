"""Single-byte packing preserves bits and the original fallback semantics."""

import unittest

from opendbc.can.dbc import Signal
from opendbc.can.packer import set_value


def reference_set_value(msg, sig, ival):
  # Frozen pre-optimization setter; the private AST checker binds this to source.
  i = sig.lsb // 8
  bits = sig.size
  if sig.size < 64:
    ival &= (1 << sig.size) - 1
  while 0 <= i < len(msg) and bits > 0:
    shift = sig.lsb % 8 if (sig.lsb // 8) == i else 0
    size = min(bits, 8 - shift)
    mask = ((1 << size) - 1) << shift
    msg[i] &= ~mask
    msg[i] |= (ival & ((1 << size) - 1)) << shift
    bits -= size
    ival >>= size
    i = i + 1 if sig.is_little_endian else i - 1


def signal(lsb, size, little=True, kind=Signal):
  return kind('TEST', lsb, lsb + size - 1, lsb, size, False, 1., 0., little)


def observed(function, factory):
  msg, sig, value, events = factory()
  try:
    result = function(msg, sig, value)
    error = None
  except Exception as exc:
    result, error = None, (type(exc).__name__, str(exc))
  return bytes(msg), result, error, events


class TestPackerSingleByte(unittest.TestCase):
  def compare(self, factory):
    self.assertEqual(observed(set_value, factory), observed(reference_set_value, factory))

  def test_contained_fields_preserve_neighbor_bits_both_endiannesses(self):
    values = (0, 1, -1, 0x55, 0xAA, 1 << 96, -(1 << 96))
    for little in (False, True):
      for initial in (0, 0xA5, 255):
        for shift in range(8):
          for size in range(1, 9 - shift):
            for value in values:
              with self.subTest(little=little, initial=initial, shift=shift, size=size, value=value):
                msg = bytearray((0x3C, initial, 0xC3))
                mask = ((1 << size) - 1) << shift
                self.assertIsNone(set_value(msg, signal(8 + shift, size, little), value))
                self.assertEqual(msg, bytearray((0x3C, (initial & ~mask) | ((value << shift) & mask), 0xC3)))

  def test_cross_byte_wide_zero_negative_and_clipped_geometry(self):
    geometry = ((0, 0), (0, -1), (-1, 1), (-8, 8), (8, 1), (24, 8),
                (0, 9), (7, 2), (4, 16), (0, 63), (0, 64), (7, 65), (16, 128))
    for little in (False, True):
      for lsb, size in geometry:
        for length in (0, 1, 3, 17):
          for value in (-1, 0, 0x55, 1 << 130, -(1 << 130)):
            with self.subTest(little=little, lsb=lsb, size=size, length=length, value=value):
              self.compare(lambda length=length, lsb=lsb, size=size, little=little, value=value:
                           (bytearray([0xA5] * length), signal(lsb, size, little), value, []))

  def test_mutated_geometry_is_read_for_each_call(self):
    sig = signal(0, 1)
    for lsb, size, little in ((0, 1, True), (9, 6, False), (7, 9, True), (16, 64, False)):
      sig.lsb, sig.size, sig.is_little_endian = lsb, size, little
      expected, actual = bytearray(b'\xA5\x5A\x96'), bytearray(b'\xA5\x5A\x96')
      reference_set_value(expected, sig, -7)
      set_value(actual, sig, -7)
      self.assertEqual(actual, expected)

  def test_nonexact_buffers_preserve_fallback_writes_and_errors(self):
    class Buffer(bytearray):
      def __getitem__(self, key):
        self.events.append(('get', key))
        return super().__getitem__(key)

      def __setitem__(self, key, value):
        self.events.append(('set', key, value))
        return super().__setitem__(key, value)

    def tracked():
      msg = Buffer(b'\xA5\x5A')
      msg.events = []
      return msg, signal(2, 3), 7, msg.events

    self.compare(tracked)
    for container in (bytes, list, lambda data: memoryview(bytearray(data))):
      self.compare(lambda container=container: (container(b'\xA5\x5A'), signal(2, 3), 7, []))

  def test_signal_subclass_attribute_side_effects_keep_original_order(self):
    class TrackedSignal(Signal):
      def __getattribute__(self, name):
        if name in ('lsb', 'size', 'is_little_endian'):
          object.__getattribute__(self, 'events').append(name)
        return super().__getattribute__(name)

    def factory():
      sig = signal(3, 10, False, TrackedSignal)
      sig.events = []
      return bytearray(b'\xA5\x5A'), sig, -1, sig.events

    self.compare(factory)

  def test_nonexact_integer_values_and_fields_keep_original_operations(self):
    class Integer(int):
      def __and__(self, other):
        self.events.append(('and', other))
        return int(self) & other

      def __floordiv__(self, other):
        self.events.append(('floordiv', other))
        return int(self) // other

      def __mod__(self, other):
        self.events.append(('mod', other))
        return int(self) % other

      def __lt__(self, other):
        self.events.append(('lt', other))
        return int(self) < other

    for field in ('value', 'lsb', 'size'):
      def factory(field=field):
        events = []
        number = Integer({'value': 7, 'lsb': 2, 'size': 3}[field])
        number.events = events
        sig = signal(number if field == 'lsb' else 2, number if field == 'size' else 3)
        return bytearray(b'\xA5\x5A'), sig, number if field == 'value' else 7, events
      self.compare(factory)
    for value in (True, False, 1.5, None):
      self.compare(lambda value=value: (bytearray(b'\xA5'), signal(2, 3), value, []))
    for lsb, size, little in ((True, 3, True), (2, True, False), (2., 3, True),
                             (2, 3., True), (2, 3, 1), (2, 3, None)):
      self.compare(lambda lsb=lsb, size=size, little=little: (bytearray(b'\xA5\x5A'), signal(lsb, size, little), 7, []))

  def test_nonboolean_endian_truth_side_effects_keep_fallback_order(self):
    class Truth:
      def __init__(self, events):
        self.events = events

      def __bool__(self):
        self.events.append('bool')
        return False

    def factory():
      events = []
      return bytearray(b'\xA5\x5A'), signal(8, 9, Truth(events)), 5, events

    self.compare(factory)

  def test_deleted_signal_fields_preserve_errors_and_unread_endian(self):
    for field in ('lsb', 'size', 'is_little_endian'):
      for lsb, size, length in ((2, 3, 1), (2, 0, 1), (16, 3, 1), (2, 3, 0)):
        def factory(lsb=lsb, size=size, field=field, length=length):
          sig = signal(lsb, size)
          delattr(sig, field)
          return bytearray([0xA5] * length), sig, 7, []
        with self.subTest(field=field, lsb=lsb, size=size, length=length):
          self.compare(factory)

    class DivisionProbe:
      def __init__(self, events):
        self.events = events

      def __floordiv__(self, other):
        self.events.append(('floordiv', other))
        raise RuntimeError('original lsb operation precedes missing size')

    def missing_size():
      events = []
      sig = signal(2, 3)
      sig.lsb = DivisionProbe(events)
      del sig.size
      return bytearray(b'\xA5'), sig, 7, events

    self.compare(missing_size)


if __name__ == '__main__':
  unittest.main()
