"""Volt 2019 SDGM inactive hold entry and accepted-command retention."""
import unittest

from opendbc.car.gm import gmcan
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests import test_gm_volt_auto_hold as hold_fixture

WORDS = (0x5087, 0x5487)


class TestVoltSdgmAutoHold(unittest.TestCase):
  def fixture(self, word, alternative=0):
    self.release = libsafety_py.libsafety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    f = hold_fixture.TestVoltAutoHold()
    f.init(word=word, alternative=alternative)
    return f

  def tearDown(self):
    libsafety_py.libsafety.set_alternative_experience(0)

  def test_exact_words_entry_retention_and_bounds(self):
    for word in WORDS:
      f = self.fixture(word)
      if self.release:
        for _ in range(32):
          f.observations(healthy=False)
        f.observations(speed=0, brake=True, healthy=False)
        self.assertFalse(f.tx())
        self.assertFalse(f.tx(0, 1))
        continue
      f.dwell()
      f.observations(speed=20)
      self.assertFalse(f.tx())  # No accepted stationary command yet.
      f.observations(speed=10)
      self.assertFalse(f.tx(99))
      bad = f.frame()
      bad.data[2] ^= 1
      self.assertFalse(f.safety.safety_tx_hook(bad))
      f.observations(speed=20)
      self.assertFalse(f.tx())
      f.observations(speed=10)
      self.assertTrue(f.tx(100))
      self.assertFalse(f.safety.safety_tx_hook(f.frame(bus=0)))
      f.observations(speed=28)
      self.assertTrue(f.tx(240))
      self.assertFalse(f.tx(241))
      f.observations(speed=29)
      self.assertFalse(f.tx())
      f.observations(speed=20)
      self.assertFalse(f.tx())
      f.observations(speed=0)
      self.assertTrue(f.tx())
      self.assertTrue(f.tx(0, 1))
      f.observations(speed=20)
      self.assertFalse(f.tx())

  def test_physical_withdrawal_clears_retained_credit(self):
    for word in WORDS:
      for changed in ({'main': False}, {'gas': True}, {'gear': 2}, {'regen': True}, {'brake_unavailable': True}):
        with self.subTest(word=hex(word), changed=changed):
          f = self.fixture(word)
          if self.release:
            self.assertFalse(f.tx())
            continue
          f.dwell()
          self.assertTrue(f.tx())
          f.observations(speed=20, **changed)
          self.assertFalse(f.tx())
          for _ in range(32):
            f.observations(speed=20)
          self.assertFalse(f.tx())
          f.observations(speed=0)
          self.assertTrue(f.tx())
          f.safety.set_timer(f.time + 300001)
          self.assertFalse(f.tx())
          f.observations(speed=20)
          self.assertFalse(f.tx())

  def test_ordinary_takeover_cannot_restore_old_hold(self):
    for word in WORDS:
      for alternative in (0, 32):
        f = self.fixture(word, alternative)
        if self.release:
          self.assertFalse(f.tx())
          continue
        f.dwell()
        self.assertTrue(f.tx())
        if alternative:
          f.safety.set_aol_test_heartbeat(True)
          f.safety.aol_set_host_request(1)
        steering = gmcan.create_steering_control(f.packer, 0, 1, 0, True)
        self.assertEqual(f.safety.safety_tx_hook(libsafety_py.make_CANPacket(steering[0], steering[2], steering[1])), alternative == 32)
        f.observations(speed=20)
        if alternative:
          f.safety.set_aol_test_heartbeat(True)
          f.safety.aol_set_host_request(3)
        f.rx(0x1E1, [0, 0, 0, 0, 0, 0x20, 0])
        self.assertTrue(f.safety.get_controls_allowed())
        self.assertTrue(f.tx(400, 0xA))
        self.assertFalse(f.tx(401, 0xA))
        f.rx(0x1E1, [0, 0, 0, 0, 0, 0x60, 0])
        self.assertFalse(f.safety.get_controls_allowed())
        if alternative:
          f.safety.aol_set_host_request(1)
        self.assertFalse(f.tx())
        f.observations(speed=0)
        self.assertTrue(f.tx())

  def test_selected_brake_forwarding_and_other_profile_reset(self):
    for word in WORDS:
      f = self.fixture(word)
      actual = {(bus, addr): f.safety.safety_fwd_hook(bus, addr) for bus in (0, 2) for addr in (0x184, 0x315, 0x2CB, 0x123)}
      f.safety.set_safety_hooks(CarParams.SafetyModel.gm, word & ~0x80)
      self.assertEqual(actual, {(bus, addr): f.safety.safety_fwd_hook(bus, addr) for bus, addr in actual})
      f = self.fixture(word)
      if self.release:
        continue
      f.dwell()
      f.observations(speed=0, gas=True)
      f.observations(speed=0, c9_brake=not f.c9_brake, be_brake=f.c9_brake)
      self.assertFalse(f.tx())
      f.observations(speed=0, c9_brake=f.c9_brake, be_brake=not f.c9_brake)
      self.assertTrue(f.tx())
    for word in (0x4084, 0x4287, 0x4087):
      f = self.fixture(word)
      if self.release and word != 0x4084:
        continue
      f.dwell()
      self.assertTrue(f.tx(80))
      f.observations(speed=20)
      self.assertFalse(f.tx())
