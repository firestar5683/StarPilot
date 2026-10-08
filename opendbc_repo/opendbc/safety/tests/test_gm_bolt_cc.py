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


def ready(word, *, gas=False, gear=4, manual=False):
  setup(word)
  wheel = int(20 * 3.6 / 0.0311)
  frames = [
    (0x1F5, bytes((0, 0, 0, gear, 0, 2 * int(manual), 0, 0))),
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
  def test_forward_gear_transitions_retain_permission_but_revocation_requires_button_edge(self):
    for word in (*WORDS, 0xC140, 0xC141):
      for denied_gear, manual in ((0, False), (1, False), (2, False), (3, False),
                                  (5, False), (7, False), (4, True), (6, True)):
        with self.subTest(word=word, denied_gear=denied_gear, manual=manual):
          ready(word, gear=6)
          safety = libsafety_py.libsafety
          self.assertTrue(safety.get_controls_allowed())
          for step, gear in enumerate((4, 6), start=1):
            packet(0x1F5, bytes((0, 0, 0, gear, 0, 0, 0, 0)), 1_000_000 + step * 1000)
            self.assertTrue(safety.get_controls_allowed())
          packet(0x1F5, bytes((0, 0, 0, denied_gear, 0, 2 * int(manual), 0, 0)), 1_003_000)
          self.assertFalse(safety.get_controls_allowed())
          packet(0x1F5, bytes((0, 0, 0, 6, 0, 0, 0, 0)), 1_004_000)
          self.assertFalse(safety.get_controls_allowed())
          packet(0x1E1, button_bytes(1, 1), 1_005_000)
          self.assertFalse(safety.get_controls_allowed())
          packet(0x1E1, button_bytes(3, 2), 1_006_000)
          self.assertFalse(safety.get_controls_allowed())
          packet(0x1E1, button_bytes(1, 3), 1_007_000)
          self.assertTrue(safety.get_controls_allowed())

  def test_low_gear_physical_cruise_and_set_rearm_for_every_bolt_profile(self):
    for word in (*WORDS, 0xC140, 0xC141):
      for gear in (4, 6):
        with self.subTest(word=word, gear=gear):
          ready(word, gear=gear)
          safety = libsafety_py.libsafety
          self.assertTrue(safety.get_controls_allowed())
          self.assertTrue(packet(0x180, bytes((8, 1, 0, 0)), 1_001_000, transmit=True))
          packet(0xC9, bytes((0, 0, 0, 0, 0, 1, 0, 0)), 1_002_000)
          self.assertFalse(safety.get_controls_allowed())
          packet(0xC9, bytes(8), 1_003_000)
          self.assertFalse(safety.get_controls_allowed())
          packet(0x1E1, button_bytes(3, 1), 1_004_000)
          self.assertFalse(safety.get_controls_allowed())
          packet(0x1E1, button_bytes(1, 2), 1_005_000)
          self.assertTrue(safety.get_controls_allowed())
          packet(0x1F5, bytes((0, 0, 0, 2, 0, 0, 0, 0)), 1_006_000)
          self.assertFalse(safety.get_controls_allowed())

  def test_non_forward_and_manual_gears_cannot_grant_bolt_permission(self):
    for word in (*WORDS, 0xC140, 0xC141):
      for gear, manual in ((0, False), (1, False), (2, False), (3, False),
                           (5, False), (7, False), (4, True), (6, True)):
        with self.subTest(word=word, gear=gear, manual=manual):
          ready(word, gear=gear, manual=manual)
          safety = libsafety_py.libsafety
          self.assertFalse(safety.get_controls_allowed())
          packet(0x1E1, button_bytes(3, 1), 1_001_000)
          packet(0x1E1, button_bytes(1, 2), 1_002_000)
          self.assertFalse(safety.get_controls_allowed())
          self.assertFalse(packet(0x180, bytes((8, 1, 0, 0)), 1_003_000, transmit=True))

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

  def test_timer_rollover_preserves_fresh_physical_sources(self):
    safety = libsafety_py.libsafety
    safety.set_alternative_experience(0)
    for word in WORDS:
      frames = ready(word)
      setup(word)
      for address, data in frames:
        packet(address, data, 0xFFFFF000)
      self.assertTrue(safety.get_controls_allowed())
      self.assertTrue(packet(0x180, bytes((8, 1, 0, 0)), 1000, transmit=True))
      packet(0xC9, bytes((0, 0, 0, 0, 0, 1, 0, 0)), 2000)
      self.assertFalse(safety.get_controls_allowed())
      self.assertFalse(packet(0x180, bytes((8, 1, 0, 0)), 3000, transmit=True))

  def test_pscm_copy_requires_exact_payload_fresh_source_and_cadence(self):
    libsafety_py.libsafety.set_alternative_experience(0)
    for word in WORDS:
      for source, expected in ((bytes(8), bytes((0, 0, 32, 0, 0, 32, 0, 0))),
                               (bytes((0, 0, 32, 0, 0, 32, 0, 0)), bytes((0, 0, 32, 0, 0, 32, 0, 0)))):
        with self.subTest(word=word, source=source):
          ready(word)
          packet(0x184, source, 1_000_001)
          for index in range(8):
            bad = bytearray(expected)
            bad[index] ^= 1
            self.assertFalse(packet(0x184, bad, 1_001_000, transmit=True, bus=2))
          self.assertTrue(packet(0x184, expected, 1_001_000, transmit=True, bus=2))
          self.assertFalse(packet(0x184, expected, 1_002_000, transmit=True, bus=2))
          self.assertFalse(packet(0x184, expected, 1_101_001, transmit=True, bus=2))
          packet(0x184, source, 1_101_002)
          self.assertTrue(packet(0x184, expected, 1_101_003, transmit=True, bus=2))
      for address in (0x409, 0x40A):
        ready(word)
        self.assertEqual(packet(address, bytes(7), 1_001_000, transmit=True), word in (0xC111, 0xC121, 0xC131))
        for index in range(7):
          bad = bytearray(7)
          bad[index] = 1
          self.assertFalse(packet(address, bad, 1_002_000, transmit=True))

  def test_camera_cancel_requires_fresh_active_camera_and_consumes_credit(self):
    libsafety_py.libsafety.set_alternative_experience(0)
    for camera in (bytes(6), bytes((0, 0, 128, 0, 0, 0))):
      ready(0xC140)
      packet(0x370, camera, 1_000_001, bus=2)
      expected = bool(camera[2] & 128)
      self.assertEqual(packet(0x1E1, button_bytes(6, 1), 1_001_000, transmit=True, bus=2), expected)
      self.assertFalse(packet(0x1E1, button_bytes(6, 1), 1_002_000, transmit=True, bus=2))
    frames = ready(0xC140)
    packet(0x370, bytes((0, 0, 128, 0, 0, 0)), 1_000_001, bus=2)
    for address, data in frames:
      packet(address, button_bytes(1, 1) if address == 0x1E1 else data, 1_301_000)
    self.assertFalse(packet(0x1E1, button_bytes(6, 2), 1_302_000, transmit=True, bus=2))
    packet(0x370, bytes((0, 0, 128, 0, 0, 0)), 1_303_000, bus=2)
    packet(0x1E1, button_bytes(1, 2), 1_304_000)
    self.assertTrue(packet(0x1E1, button_bytes(6, 3), 1_305_000, transmit=True, bus=2))

  def test_physical_cancel_withdraws_and_set_release_rearms(self):
    libsafety_py.libsafety.set_alternative_experience(0)
    for word in WORDS:
      ready(word)
      packet(0x1E1, button_bytes(6, 1), 1_001_000)
      self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
      packet(0x1E1, button_bytes(1, 2), 1_002_000)
      self.assertFalse(libsafety_py.libsafety.get_controls_allowed())
      packet(0x1E1, button_bytes(3, 3), 1_003_000)
      packet(0x1E1, button_bytes(1, 0), 1_004_000)
      self.assertTrue(libsafety_py.libsafety.get_controls_allowed())

  def test_invalid_profile_initializer_rejects_transmit_admission(self):
    setup(0xC110)
    self.assertFalse(libsafety_py.libsafety.safety_test_gm_bolt_unowned_tx())
    self.assertTrue(libsafety_py.libsafety.safety_test_gm_bolt_invalid_profile())
    setup(0xC110)
    self.assertFalse(packet(0x200, bytes(6), transmit=True))

  def test_selected_forwarding_policy_preserves_owned_blocks_and_unowned_routing(self):
    for word in WORDS:
      libsafety_py.libsafety.set_alternative_experience(0)
      setup(word)
      for bus in (0, 1, 2):
        for address in (0x180, 0x184, 0x3D1, 0x321):
          with self.subTest(word=word, bus=bus, address=hex(address)):
            blocked = (bus == 2 and address == 0x180) or (bus == 0 and address in (0x184, 0x3D1))
            self.assertEqual(libsafety_py.libsafety.safety_test_selected_fwd(bus, address), blocked)
            destination = -1 if blocked or bus == 1 else 2 if bus == 0 else 0
            self.assertEqual(libsafety_py.libsafety.safety_fwd_hook(bus, address), destination)


class TestGmRemovedBoltStockSafety(unittest.TestCase):
  def test_reduced_stock_has_cancel_only_physical_button_authority(self):
    for word in (0xE710, 0xE711, 0xE712, 0xE713):
      for button in (2, 3, 6):
        with self.subTest(word=word, button=button):
          ready(word)
          packet(0xC9, bytes((0, 0, 0, 32, 0, 0, 0, 0)), 1_000_001)
          self.assertEqual(packet(0x1E1, button_bytes(button, 1), 1_001_000, transmit=True), button == 6)
          if button == 6:
            self.assertFalse(packet(0x1E1, button_bytes(6, 1), 1_002_000, transmit=True))
          for address, length in ((0x200, 6), (0x315, 5), (0xBD, 7), (0x1F5, 8), (0x409, 7), (0x40A, 7)):
            self.assertFalse(packet(address, bytes(length), 1_002_000, transmit=True))
          self.assertFalse(packet(0x1E1, button_bytes(6, 1), 1_002_000, transmit=True, bus=2))

  def test_reduced_stock_requires_current_cruise_and_neutral_credit(self):
    for word in (0xE710, 0xE711, 0xE712, 0xE713):
      with self.subTest(word=word):
        ready(word)
        packet(0xC9, bytes((0, 0, 0, 32, 0, 0, 0, 0)), 1_000_001)
        self.assertFalse(packet(0x1E1, button_bytes(6, 1), 1_100_001, transmit=True))
        ready(word)
        packet(0xC9, bytes((0, 0, 0, 32, 0, 0, 0, 0)), 1_000_001)
        packet(0x3D1, bytes(8), 1_001_000)
        self.assertFalse(packet(0x1E1, button_bytes(6, 1), 1_002_000, transmit=True))
        ready(word)
        packet(0xC9, bytes((0, 0, 0, 32, 0, 0, 0, 0)), 1_000_001)
        self.assertTrue(packet(0x1E1, button_bytes(6, 1), 1_001_000, transmit=True))
        packet(0x1E1, button_bytes(1, 0), 1_002_000)
        self.assertFalse(packet(0x1E1, button_bytes(6, 1), 1_003_000, transmit=True))

  def test_stock_dispatch_resets_to_existing_manual_button_authority(self):
    for stock, ordinary in ((0xE710, 0xC111), (0xE711, 0xC121), (0xE712, 0xC131), (0xE713, 0xC141)):
      for word, expected in ((stock, False), (ordinary, True), (stock, False)):
        ready(word)
        packet(0xC9, bytes((0, 0, 0, 32, 0, 0, 0, 0)), 1_000_001)
        libsafety_py.libsafety.set_controls_allowed(True)
        self.assertEqual(packet(0x1E1, button_bytes(2, 1), 1_001_000, transmit=True), expected)

  def test_stock_main_cycle_cannot_restore_consumed_or_withdrawn_credit(self):
    for word in (0xE710, 0xE711, 0xE712, 0xE713):
      ready(word)
      packet(0xC9, bytes(8), 1_000_001)
      packet(0xC9, bytes((0, 0, 0, 32, 0, 0, 0, 0)), 1_000_002)
      self.assertFalse(packet(0x1E1, button_bytes(6, 1), 1_001_000, transmit=True))
      packet(0x1E1, button_bytes(1, 1), 1_002_000)
      self.assertTrue(packet(0x1E1, button_bytes(6, 2), 1_003_000, transmit=True))

  def test_unknown_removed_bolt_words_cannot_borrow_stock_or_active_authority(self):
    for word in (0xE6FF, 0xE704, 0xE70F, 0xE714, 0xE7FF):
      setup(word)
      libsafety_py.libsafety.set_controls_allowed(True)
      self.assertFalse(packet(0x180, bytes(4), transmit=True))
      self.assertFalse(packet(0x1E1, button_bytes(6, 1), transmit=True))
      self.assertFalse(packet(0x409, bytes(7), transmit=True))
