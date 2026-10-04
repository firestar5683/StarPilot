"""Conventional Bolt ownership through the registered GM hooks."""

import unittest
from opendbc.car.gm.bolt_cc import button_bytes
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py

WORDS = (0xC110, 0xC111, 0xC120, 0xC121, 0xC130, 0xC131)


def setup(word):
  safety = libsafety_py.libsafety
  safety.init_tests()
  assert safety.set_safety_hooks(int(CarParams.SafetyModel.gm), word) == 0


def packet(address, data, us=1_000_000, *, transmit=False, bus=0):
  safety = libsafety_py.libsafety
  safety.set_timer(us)
  msg = libsafety_py.make_CANPacket(address, bus, data)
  return safety.safety_tx_hook(msg) if transmit else safety.safety_rx_hook(msg)


def ready(word, *, gas=False):
  setup(word)
  wheel = int(20 * 3.6 / 0.0311)
  frames = [
    (0x1F5, bytes((0, 0, 0, 4, 0, 0, 0, 0))),
    (0xC9, bytes(8)),
    (0xBD, bytes(7)),
    (0x1C4, bytes((0, 0, 0, 0, 0, int(gas), 0, 0))),
    (0x184, bytes(8)),
    (0x34A, bytes((wheel >> 8, wheel & 255, wheel >> 8, wheel & 255, 9))),
    (0x1E1, button_bytes(1, 0)),
    (0x3D1, bytes((0, 0, 0, 0, 128, 0, 0, 0))),
  ]
  for address, data in frames:
    packet(address, data)
  return frames


class TestGmBoltCcSafety(unittest.TestCase):
  def test_pcm_rising_cannot_override_held_park_brake_or_paddle(self):
    for word in WORDS:
      for source, blocked, clear in (
        (0x1F5, bytes((0, 0, 0, 1, 0, 0, 0, 0)), bytes((0, 0, 0, 4, 0, 0, 0, 0))),
        (0xC9, bytes((0, 0, 0, 0, 0, 1, 0, 0)), bytes(8)),
        (0xBD, bytes((16, 0, 0, 0, 0, 0, 0)), bytes(7)),
      ):
        with self.subTest(word=word, source=source):
          ready(word)
          packet(0x3D1, bytes(8), 1_002_000)
          packet(source, blocked, 1_003_000)
          packet(0x3D1, bytes((0, 0, 0, 0, 128, 0, 0, 0)), 1_004_000)
          self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
          self.assertFalse(packet(0x180, bytes((8, 1, 0, 0)), 1_005_000, transmit=True))
          packet(source, clear, 1_006_000)
          packet(0x1E1, button_bytes(1, 1), 1_007_000)
          self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
          packet(0x1E1, button_bytes(3, 2), 1_008_000)
          self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
          packet(0x1E1, button_bytes(1, 3), 1_009_000)
          self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
          self.assertTrue(packet(0x1E1, button_bytes(2, 0), 1_010_000, transmit=True))

  def test_required_health_and_global_revocation_latch(self):
    for word in WORDS:
      frames = ready(word)
      safety = libsafety_py.libsafety
      self.assertTrue(safety.get_controls_allowed())
      safety.set_timer(3_000_000)
      safety.safety_tick()
      self.assertFalse(safety.get_controls_allowed())
      for address, data in frames:
        packet(address, button_bytes(1, 1) if address == 0x1E1 else data, 3_001_000)
      self.assertFalse(safety.get_controls_allowed())
      packet(0x1E1, button_bytes(2, 2), 3_002_000)
      self.assertTrue(safety.get_controls_allowed())

  def test_gas_lateral_and_exact_unowned_transmit_denials(self):
    for word in WORDS:
      ready(word, gas=True)
      self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
      self.assertTrue(packet(0x180, bytes((8, 1, 0, 0)), 1_001_000, transmit=True))
      self.assertFalse(packet(0x1E1, button_bytes(2, 1), 1_001_000, transmit=True))
      ready(word, gas=True)
      self.assertTrue(packet(0x1E1, button_bytes(3, 1), 1_001_000, transmit=True))
      for address, length in ((0x200, 6), (0x315, 5), (0x2CB, 8), (0xBD, 7), (0x1F5, 8), (0x3D1, 8)):
        self.assertFalse(packet(address, bytes(length), 1_002_000, transmit=True))
      ready(word)
      bad = bytearray(button_bytes(2, 1))
      bad[6] ^= 1
      self.assertFalse(packet(0x1E1, bad, 1_001_000, transmit=True))
      self.assertFalse(packet(0x1E1, button_bytes(2, 1), 1_002_000, transmit=True))

  def test_invalid_sibling_words_and_existing_camera_owner(self):
    for word in (0xC112, 0xC125, 0xC000, 0xFFFF):
      setup(word)
      self.assertFalse(packet(0x180, bytes(4), transmit=True))
      self.assertFalse(packet(0x1E1, button_bytes(3, 1), transmit=True))
    setup(1)
    packet(0x1C4, bytes((0, 32, 0, 0, 0, 0, 0, 0)))
    self.assertTrue(libsafety_py.libsafety.get_controls_allowed())
    self.assertTrue(packet(0x180, bytes(4), 1_001_000, transmit=True))
    self.assertFalse(packet(0x200, bytes(6), 1_001_000, transmit=True))
