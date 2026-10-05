"""Exact removed-camera Volt and ICE gateway inactive friction owners."""
import unittest

from opendbc.car.gm import gmcan
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests import test_gm_volt_auto_hold as hold_fixture


class TestGmAutoHoldSources(unittest.TestCase):
  def fixture(self, word, alternative=0):
    self.release = libsafety_py.libsafety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    f = hold_fixture.TestVoltAutoHold()
    f.init(word=word, alternative=alternative)
    return f

  def tearDown(self):
    libsafety_py.libsafety.set_alternative_experience(0)

  def dwell(self, f, word):
    for _ in range(32):
      f.observations(regen_source=word != 0x80, healthy=not (self.release and word != 0x80))
    f.observations(speed=0, regen_source=word != 0x80, healthy=not (self.release and word != 0x80))

  def test_exact_owners_bounds_bus_and_release(self):
    for word in (0x80, 0xC1D1, 0xC1D3):
      f = self.fixture(word)
      self.dwell(f, word)
      if self.release and word != 0x80:
        self.assertFalse(f.tx())
        self.assertFalse(f.tx(0, 1))
        continue
      self.assertFalse(f.safety.get_controls_allowed())
      for brake, accepted in ((79, False), (80, True), (240, True), (241, False)):
        self.assertEqual(f.tx(brake), accepted)
      self.assertFalse(f.safety.safety_tx_hook(f.frame(bus=0 if word == 0x80 else 2)))
      f.observations(speed=20, regen_source=word != 0x80)
      self.assertFalse(f.tx())
      self.assertTrue(f.tx(0, 1))

  def test_removed_requires_c9_pressed_and_selected_analog_clock(self):
    for word in (0xC1D1, 0xC1D3):
      f = self.fixture(word)
      if self.release:
        self.assertFalse(f.tx())
        continue
      self.dwell(f, word)
      f.observations(speed=0, gas=True)
      f.observations(speed=0, c9_brake=False, be_brake=True)
      self.assertFalse(f.tx())
      f.observations(speed=0, c9_brake=True, be_brake=False)
      self.assertTrue(f.tx())  # Analog zero is valid; C9 owns pressed.
      for _ in range(4):
        f.observations(speed=0, brake=True, analog_source=False, healthy=False)
        f.rx(0xBE if f.alternate else 0xF1, bytes(6))
      self.assertFalse(f.tx())
      f.observations(speed=0, brake=True)
      self.assertTrue(f.tx())
      f.observations(speed=0, brake=True, regen=True)
      self.assertFalse(f.tx())
      f.observations(speed=0, brake=True)
      self.assertFalse(f.tx())
      for _ in range(10):
        f.observations(speed=0, brake=True)
      self.assertTrue(f.tx())
      f.safety.set_timer(f.time + 1000001)
      f.safety.safety_tick()
      self.assertFalse(f.safety.safety_config_valid())
      self.assertFalse(f.tx())

  def test_removed_physical_withdrawal_and_zero_release(self):
    for word in (0xC1D1, 0xC1D3):
      for changed in ({'main': False}, {'gas': True}, {'gear': 2}, {'regen': True}, {'brake_unavailable': True}):
        with self.subTest(word=hex(word), changed=changed):
          f = self.fixture(word)
          if self.release:
            self.assertFalse(f.tx())
            continue
          self.dwell(f, word)
          self.assertTrue(f.tx())
          f.observations(speed=0, **changed)
          self.assertFalse(f.tx())
          self.assertTrue(f.tx(0, 1))

  def test_ice_six_real_sources_faults_and_mode_reset(self):
    for changed in ({'main': False}, {'gas': True}, {'gear': 2}, {'brake_unavailable': True}):
      f = self.fixture(0x80)
      self.dwell(f, 0x80)
      self.assertTrue(f.tx())
      f.observations(speed=0, regen_source=False, **changed)
      self.assertFalse(f.tx())
      self.assertTrue(f.tx(0, 1))
    for word in (0x80, 0xC1D3, 0x4084, 0x80, 0xC1D1, 0x4287, 0x80, 0x5487):
      f = self.fixture(word)
      self.dwell(f, word)
      self.assertEqual(f.tx(), not self.release or word in (0x80, 0x4084))
    f = self.fixture(0x80)
    self.dwell(f, 0x80)
    for _ in range(4):
      f.observations(speed=0, regen_source=False, status=False)
    self.assertFalse(f.tx())

  def test_profile_switch_preserves_regen_rx_health_deadlines(self):
    for word, deadline in ((0xC1D1, 200000), (0x80, None), (0x4084, 250000), (0x4287, 250000), (0x5087, 250000)):
      f = self.fixture(word, 32)
      if self.release and word not in (0x80, 0x4084):
        continue
      self.dwell(f, word)
      if word == 0x80:
        for _ in range(4):
          f.observations(speed=0, regen_source=False)
        f.safety.safety_tick()
        self.assertTrue(f.safety.safety_config_valid())
        self.assertTrue(f.tx())
        continue
      last_regen = f.time
      f.observations(speed=0, regen_source=False)
      f.observations(speed=0, regen_source=False)
      if deadline == 250000:
        f.time -= 50000
        f.observations(speed=0, regen_source=False)
      self.assertEqual(f.time - last_regen, deadline)
      f.safety.set_aol_test_heartbeat(True)
      f.safety.aol_set_host_request(1)
      self.assertEqual(f.safety.aol_get_permission_mask(), 1)
      f.safety.set_timer(f.time + 1)
      f.safety.set_aol_test_heartbeat(True)
      f.safety.aol_set_host_request(1)
      self.assertEqual(f.safety.aol_get_permission_mask(), 0)

  def test_forwarding_ordinary_long_and_aol_scope(self):
    for word, base in ((0x80, 0), (0xC1D1, 0xC151), (0xC1D3, 0xC151)):
      for alternative in (0, 32):
        f = self.fixture(word, alternative)
        actual = {(bus, addr): f.safety.safety_fwd_hook(bus, addr) for bus in (0, 2) for addr in (0x184, 0x315, 0x2CB, 0x370, 0x1E1, 0x123)}
        f.safety.set_safety_hooks(CarParams.SafetyModel.gm, base)
        self.assertEqual(actual, {(bus, addr): f.safety.safety_fwd_hook(bus, addr) for bus, addr in actual})
        f = self.fixture(word, alternative)
        self.dwell(f, word)
        if self.release and word != 0x80:
          continue
        f.safety.set_aol_test_heartbeat(True)
        f.safety.aol_set_host_request(1)
        steering = gmcan.create_steering_control(f.packer, 0, 1, 0, True)
        self.assertEqual(f.safety.safety_tx_hook(libsafety_py.make_CANPacket(steering[0], steering[2], steering[1])), alternative == 32 and word != 0x80)
        f.observations(speed=100, regen_source=word != 0x80)
        f.rx(0x1E1, [0, 0, 0, 0, 0, 0x20, 0])
        self.assertTrue(f.safety.get_controls_allowed())
        f.safety.aol_set_host_request(3)
        self.assertTrue(f.tx(400, 0xA))
        self.assertFalse(f.tx(401, 0xA))
        f.observations(brake=True, regen_source=word != 0x80)
        self.assertFalse(f.safety.get_controls_allowed())
