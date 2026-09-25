"""Synthetic CRC-valid fixtures qualify arithmetic, not GV70 hardware provenance."""
from dataclasses import FrozenInstanceError
import math
import unittest

from opendbc.car.hyundai.ev6_template import EV6Template
from opendbc.car.hyundai.gv70_template import GV70Template


def crc(data):
  value = 0
  for byte in data[2:] + bytes((0x51, 0)):
    value ^= byte << 8
    for _ in range(8):
      value = ((value << 1) ^ (0x1021 if value & 0x8000 else 0)) & 65535
  return value ^ 0x9f5b


def capture(counter=254):
  data = bytearray(range(32))
  data[2] = counter
  data[:2] = crc(data).to_bytes(2, 'little')
  return bytes(data)


class TestGV70Template(unittest.TestCase):
  def test_finite_speed_round_clip_counter_drive_and_crc(self):
    for counter in (0, 254, 255):
      source = capture(counter)
      template = GV70Template.capture(source)
      for frame in (0, 1, 255, 256):
        for drive in (False, True):
          for speed in (-1., 0., .005, .015, 1.005, 12.345, 655.335, 655.34, 655.345, 1000.):
            with self.subTest(counter=counter, frame=frame, drive=drive, speed=speed):
              expected = bytearray(source)
              expected[2] = (counter + frame + 1) & 255
              expected[3] = (source[3] & ~1) | int(drive)
              expected[8:10] = min(max(round(speed * 100.), 0), 65534).to_bytes(2, 'little')
              expected[:2] = crc(expected).to_bytes(2, 'little')
              self.assertEqual(template.frame(frame, drive, speed=speed), (0x51, bytes(expected), 0))
              self.assertEqual(template.data, source)

  def test_absent_and_nonfinite_speed_preserve_capture(self):
    source = capture()
    descriptor = GV70Template.capture(source)
    ev6 = EV6Template.capture(source)
    for speed in (None, math.nan, math.inf, -math.inf):
      self.assertEqual(descriptor.frame(7, True, speed=speed), ev6.frame(7, True))
      self.assertEqual(descriptor.frame(7, True, speed=speed).dat[8:10], source[8:10])

  def test_capture_integrity_instances_and_ev6_signature_remain_closed(self):
    source = capture()
    descriptor = GV70Template.capture(source)
    for instance in (descriptor, EV6Template.capture(source)):
      for name, value in (('data', bytes(32)), ('frame', None), ('_finish', None), ('extra', 1)):
        with self.subTest(descriptor=type(instance).__name__, field=name):
          with self.assertRaises(FrozenInstanceError):
            setattr(instance, name, value)
    bad = bytearray(source)
    bad[12] ^= 1
    for value in (b'', source[:-1], source+b'0', bytearray(source), bytes(bad)):
      with self.assertRaises(ValueError):
        GV70Template.capture(value)
    with self.assertRaises(TypeError):
      EV6Template.capture(source).frame(0, False, speed=123.)
    other = GV70Template.capture(capture(0))
    self.assertNotEqual(descriptor.frame(0, False).dat[2], other.frame(0, False).dat[2])
    for args in ((-1, False, 0), (True, False, 0), (0, 1, 0), (0, False, 1)):
      with self.assertRaises(ValueError):
        descriptor.frame(*args, speed=1.)
