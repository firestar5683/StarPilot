"""Exact DEBUG Volt ASCM and camera-present inactive friction contracts."""
import unittest

from opendbc.car.gm import gmcan
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests import test_gm_volt_auto_hold as hold_fixture

WORDS = (0x4287, 0x4687, 0x4A87, 0x4E87, 0x4087)


class TestVoltCameraAutoHold(unittest.TestCase):
  def fixture(self, word, alternative=0):
    fixture = hold_fixture.TestVoltAutoHold()
    self.release = libsafety_py.libsafety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    fixture.init(word=word, alternative=alternative)
    return fixture

  def tearDown(self):
    libsafety_py.libsafety.set_alternative_experience(0)

  def test_exact_words_hold_and_release_denial(self):
    for word in WORDS:
      with self.subTest(word=hex(word)):
        f = self.fixture(word)
        if self.release:
          for _ in range(32):
            f.observations(healthy=False)
          f.observations(speed=0, brake=True, healthy=False)
          self.assertFalse(f.tx())
          self.assertFalse(f.tx(0, 1))
        else:
          f.dwell()
          self.assertTrue(f.tx())
          self.assertFalse(f.safety.get_controls_allowed())
          self.assertFalse(f.safety.safety_tx_hook(f.frame(bus=2)))
          f.observations(speed=0, brake_unavailable=True)
          self.assertFalse(f.tx())
          self.assertTrue(f.tx(0, 1))

  def test_selected_physical_brake_and_c9_packer_binding(self):
    for word in WORDS:
      with self.subTest(word=hex(word)):
        f = self.fixture(word)
        if self.release:
          self.assertFalse(f.tx())
          continue
        frame = f.packer.make_can_msg('ECMEngineStatus', 0, {'BrakePressed': 1, 'CruiseMainOn': 1})
        self.assertEqual(frame[1][5] & 1, 1)
        f.dwell()
        f.observations(speed=0, gas=True)
        for _ in range(2):
          f.observations(speed=0, c9_brake=not f.c9_brake, be_brake=f.c9_brake)
        self.assertFalse(f.tx())
        f.observations(speed=0, c9_brake=f.c9_brake, be_brake=not f.c9_brake)
        self.assertTrue(f.tx())

  @staticmethod
  def release_mode():
    return libsafety_py.libsafety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0

  def test_aol_and_ordinary_longitudinal_keep_existing_authority(self):
    for word in WORDS:
      for alternative in (0, 32):
        with self.subTest(word=hex(word), alternative=alternative):
          f = self.fixture(word, alternative)
          if self.release:
            self.assertFalse(f.tx())
            continue
          f.dwell()
          f.safety.set_aol_test_heartbeat(True)
          f.safety.aol_set_host_request(1)
          self.assertEqual(f.safety.aol_get_permission_mask(), 1 if alternative == 32 else 0)
          steering = gmcan.create_steering_control(f.packer, 0, 1, 0, True)
          self.assertEqual(f.safety.safety_tx_hook(libsafety_py.make_CANPacket(steering[0], steering[2], steering[1])), alternative == 32)
          f.observations(speed=100)
          f.rx(0x1E1, [0, 0, 0, 0, 0, 0x20, 0])
          self.assertTrue(f.safety.get_controls_allowed())
          if alternative:
            f.safety.aol_set_host_request(3)
          self.assertTrue(f.tx(400, 0xA))
          self.assertFalse(f.tx(401, 0xA))
          f.observations(brake=True)
          self.assertFalse(f.safety.get_controls_allowed())

  def test_existing_forwarding_and_mode_reset_do_not_leak(self):
    for word in WORDS:
      f = self.fixture(word)
      actual = {(bus, addr): f.safety.safety_fwd_hook(bus, addr) for bus in (0, 2) for addr in (0x180, 0x184, 0x315, 0x2CB, 0x370, 0x123)}
      f.safety.set_safety_hooks(CarParams.SafetyModel.gm, word & ~0x80)
      expected = {(bus, addr): f.safety.safety_fwd_hook(bus, addr) for bus, addr in actual}
      self.assertEqual(actual, expected)
    if not self.release_mode():
      for word in (0x4687, 0x4287, 0x4087, 0xC084, 0x4084):
        f = self.fixture(word)
        if word in (0xC084, 0x4084):
          f.init(alternate=word == 0xC084)
        f.dwell()
        self.assertTrue(f.tx())
