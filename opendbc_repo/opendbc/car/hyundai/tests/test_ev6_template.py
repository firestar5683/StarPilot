"""Captured EV6 status integrity and pinned-original counter/Drive recipe."""
from dataclasses import FrozenInstanceError
import unittest

from opendbc.car.hyundai.ev6_template import EV6Template

# Retained original EV6 factory fixture; no new physical capture claimed.
CAPTURE = bytes.fromhex('88ed2e091700ffff5e0d0000012006ff021c2200000000000800000010000000')


def independent_crc(data):
  crc = 0
  for byte in bytes(data)[2:] + bytes((0x51, 0)):
    crc ^= byte << 8
    for _ in range(8):
      crc = ((crc << 1) ^ (0x1021 if crc & 0x8000 else 0)) & 0xFFFF
  return crc ^ 0x9F5B


def valid_capture(counter, body=CAPTURE[3:]):
  data = bytearray(bytes(2) + bytes((counter,)) + body)
  data[:2] = independent_crc(data).to_bytes(2, 'little')
  return bytes(data)


class TestEV6Template(unittest.TestCase):
  def test_retained_capture_is_crc_valid_and_immutable(self):
    self.assertEqual(independent_crc(CAPTURE), int.from_bytes(CAPTURE[:2], 'little'))
    template = EV6Template.capture(CAPTURE)
    self.assertEqual(template.counter, 46)
    self.assertEqual(template.data, CAPTURE)
    with self.assertRaises(FrozenInstanceError):
      template.data = bytes(32)

  def test_constructor_and_capture_reject_invalid_or_empty_body(self):
    corrupt = bytearray(CAPTURE)
    corrupt[12] ^= 1
    for data in (b'', CAPTURE[:-1], CAPTURE + b'\x00', bytearray(CAPTURE), bytes(corrupt),
                 valid_capture(46, bytes(29))):
      for constructor in (EV6Template, EV6Template.capture):
        with self.subTest(size=len(data), constructor=constructor):
          with self.assertRaises(ValueError):
            constructor(data)

  def test_counter_wrap_physical_drive_and_opaque_bytes_match_original(self):
    for counter in (0, 1, 46, 254, 255):
      source = valid_capture(counter)
      template = EV6Template.capture(source)
      for frame in (0, 1, 7, 255, 256, 511, 65535):
        for drive in (False, True):
          with self.subTest(counter=counter, frame=frame, drive=drive):
            packet = template.frame(frame, drive)
            expected = bytearray(source)
            expected[2] = (counter + frame + 1) & 255
            expected[3] = (source[3] & ~1) | int(drive)
            expected[:2] = independent_crc(expected).to_bytes(2, 'little')
            self.assertEqual(packet, (0x51, bytes(expected), 0))
            self.assertEqual(packet.dat[4:], source[4:])
            self.assertEqual(template.data, source)

  def test_instances_and_repeated_calls_do_not_share_mutable_state(self):
    first = EV6Template.capture(CAPTURE)
    second = EV6Template.capture(valid_capture(255))
    expected = first.frame(7, True)
    second.frame(255, False)
    first.frame(300, False)
    self.assertEqual(first.frame(7, True), expected)
    self.assertEqual(second.counter, 255)
    self.assertEqual(first.counter, 46)

  def test_invalid_frame_drive_and_bus_are_not_coerced(self):
    template = EV6Template.capture(CAPTURE)
    for frame, drive, bus in ((-1, False, 0), (True, False, 0), (.5, False, 0),
                              (0, 1, 0), (0, False, 1), (0, False, False)):
      with self.subTest(frame=frame, drive=drive, bus=bus):
        with self.assertRaises(ValueError):
          template.frame(frame, drive, bus)
