"""Exact Volt inactive OnePedal source, routing and stopped-owner contracts."""
import unittest

from opendbc.car.gm import gmcan
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests import test_gm_volt_auto_hold as hold_fixture

CANONICAL = (0x4084, 0xC084, 0x4287, 0x4687, 0x4A87, 0x4E87, 0x4087, 0x5087, 0x5487, 0xC1D1, 0xC1D3)


class TestVoltOnePedal(unittest.TestCase):
  def fixture(self, index, paired=False, alternative=0):
    self.release = libsafety_py.libsafety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    f = hold_fixture.TestVoltAutoHold()
    f.init(word=0xD100 + index + (0x10 if paired else 0), physical_word=CANONICAL[index], alternative=alternative)
    return f

  def tearDown(self):
    libsafety_py.libsafety.set_alternative_experience(0)

  def mode(self, f, active=True, bus=0, length=4):
    frame = f.packer.make_can_msg('EVDriveMode', bus, {'SinglePedalModeActive': int(active)})
    self.assertEqual(frame[1][0] & 0x80, 0x80 if active else 0)
    f.rx(frame[0], frame[1][:length], bus)

  def test_all_exact_profiles_moving_and_stopped_bounds(self):
    for paired in (False, True):
      for index in range(11):
        with self.subTest(index=index, paired=paired):
          f = self.fixture(index, paired)
          denied = self.release and index >= 2
          for _ in range(32):
            f.observations(gear=6, healthy=not denied)
          self.assertEqual(f.tx(400), not denied)
          self.assertFalse(f.tx(401))
          self.assertFalse(f.safety.safety_tx_hook(f.frame(bus=2 if f.tx_bus == 0 else 0)))
          f.observations(speed=0, gear=6, healthy=not denied)
          minimum = 100 if index in (7, 8) else 80
          self.assertFalse(f.tx(minimum - 1))
          self.assertEqual(f.tx(minimum), not denied)
          self.assertEqual(f.tx(240), not denied)
          self.assertEqual(f.tx(400), not denied)
          self.assertFalse(f.tx(401))
          self.assertEqual(f.tx(0, 1), not denied)

  def test_solo_mode_and_paired_hold_are_distinct(self):
    for index in range(11):
      if self.release_mode() and index >= 2:
        continue
      for paired in (False, True):
        f = self.fixture(index, paired)
        f.dwell()
        self.assertEqual(f.tx(), paired)
        self.mode(f)
        self.assertTrue(f.tx())
        f.observations(speed=0, brake=True)
        self.assertEqual(f.tx(), paired)
        f.observations(speed=0)
        self.mode(f, False)
        self.assertEqual(f.tx(), paired)

  @staticmethod
  def release_mode():
    return libsafety_py.libsafety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0

  def test_mode_current_observation_low_and_physical_withdrawal(self):
    for paired in (False, True):
      f = self.fixture(0, paired)
      f.dwell()
      f.observations(speed=100)
      self.mode(f, bus=2)
      self.assertFalse(f.tx(400))
      self.mode(f, length=3)
      self.assertFalse(f.tx(400))
      self.mode(f)
      self.assertTrue(f.tx(400))
      for _ in range(4):
        f.observations(speed=100)
      self.assertFalse(f.tx(400))
      f.time = 0xFFFFFF00 - 100000
      f.observations(speed=100)
      self.assertFalse(f.tx(400))
      f.time = 0
      f.observations(speed=100)
      self.assertFalse(f.tx(400))  # Expired mode cannot revive at a 32-bit timer wrap.
      f.observations(speed=100, gear=6)
      self.assertTrue(f.tx(400))  # Fresh Low needs no drive-mode frame.
      f.observations(speed=100, gear=6, manual=True)
      self.assertFalse(f.tx(400))
      for changed in ({'main': False}, {'gas': True}, {'brake': True}, {'regen': True}, {'gear': 2}, {'brake_unavailable': True}):
        f = self.fixture(0, paired)
        for _ in range(32):
          f.observations(gear=6)
        self.assertTrue(f.tx(400))
        f.observations(gear=6, **changed) if 'gear' not in changed else f.observations(**changed)
        self.assertFalse(f.tx(400))
        self.assertTrue(f.tx(0, 1))

  def test_moving_does_not_seed_sdgm_hold_credit_or_mixed_wheels(self):
    for index in (7, 8):
      f = self.fixture(index)
      if self.release:
        self.assertFalse(f.tx())
        continue
      for _ in range(32):
        f.observations(gear=6)
      self.assertTrue(f.tx(400))
      f.observations(speed=20, gear=4)
      self.assertFalse(f.tx())  # No accepted stationary hold; mode withdrawn.
      self.mode(f)
      self.assertTrue(f.tx(400))
      f.observations(speed=0)
      self.mode(f)
      self.assertTrue(f.tx(100))
      f.observations(speed=20)
      self.mode(f)
      self.assertTrue(f.tx(240))
      self.assertTrue(f.tx(400))
      self.mode(f, False)
      self.mode(f)
      self.assertTrue(f.tx(400))  # Mode withdrawal cleared old stop credit before reactivation.
      self.assertTrue(f.tx(0, 1))
      self.assertTrue(f.tx(400))  # Explicitly moving after released stop credit.
    f = self.fixture(0)
    for _ in range(32):
      f.observations(gear=6)
    f.rx(0x34A, [0, 20, 0, 0, 0])
    self.assertFalse(f.tx(400))

  def test_no_positive_gas_and_unknown_tags_reset(self):
    f = self.fixture(0, alternative=32)
    for _ in range(32):
      f.observations(gear=6)
    f.safety.set_aol_test_heartbeat(True)
    f.safety.aol_set_host_request(1)
    self.assertTrue(f.tx(400))
    for gas, enabled, accepted in ((-650, False, True), (-649, False, False), (1, False, False), (-650, True, False)):
      frame = gmcan.create_gas_regen_command(f.packer, 0, gas, 0, enabled, False)
      self.assertEqual(f.safety.safety_tx_hook(libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])), accepted)
    for word in (0xD0FF, 0xD10B, 0xD10F, 0xD11B, 0xD11F, 0xD120):
      f.init(word=word)
      for _ in range(32):
        f.observations(gear=6, healthy=False)
      self.assertFalse(f.tx(400))
    f.init()
    for _ in range(32):
      f.observations(gear=6)
    self.assertFalse(f.tx(400))
    f.observations(speed=0)
    self.assertTrue(f.tx(80))

  def test_one_pedal_release_is_immediate_but_independent_hold_keeps_cooldown(self):
    for paired in (False, True):
      for stopped in (False, True):
        f = self.fixture(0, paired)
        for _ in range(32):
          f.observations(gear=6)
        speed = 0 if stopped else 100
        f.observations(speed=speed, gear=6, regen=True)
        self.assertFalse(f.tx(100))
        f.observations(speed=speed, gear=6)
        self.assertTrue(f.tx(100))
    f = self.fixture(0, paired=True)
    f.dwell()
    f.observations(speed=0, brake=True, regen=True)
    f.observations(speed=0, brake=True)
    self.assertFalse(f.tx())
    for _ in range(10):
      f.observations(speed=0, brake=True)
    self.assertTrue(f.tx())

  def test_independent_paired_hold_keeps_240_and_sdgm_credit(self):
    for index in (0, 7, 8):
      f = self.fixture(index, paired=True)
      if self.release and index >= 2:
        self.assertFalse(f.tx())
        continue
      f.dwell()
      self.assertTrue(f.tx(240))
      self.assertFalse(f.tx(241))
      if index in (7, 8):
        f.observations(speed=20)
        self.assertTrue(f.tx(240))
        self.assertFalse(f.tx(241))
        self.assertTrue(f.tx(0, 1))
        self.assertFalse(f.tx(240))
      f.observations(speed=0, gear=6)
      self.assertTrue(f.tx(400))
      f.observations(speed=0, gear=6, brake=True)
      self.assertTrue(f.tx(240))
      self.assertFalse(f.tx(241))

  def test_only_independent_auto_hold_seeds_sdgm_mixed_wheel_credit(self):
    for index in (7, 8):
      for paired in (False, True):
        with self.subTest(index=index, paired=paired):
          f = self.fixture(index, paired)
          if self.release:
            self.assertFalse(f.tx(200))
            continue
          for _ in range(32):
            f.observations(gear=6)
          f.observations(speed=0, gear=6)
          self.assertTrue(f.tx(200))
          f.rx(0x34A, [0, 20, 0, 0, 0])
          self.assertEqual(f.tx(200), paired)
          self.assertTrue(f.tx(0, 1))
          self.assertFalse(f.tx(200))
