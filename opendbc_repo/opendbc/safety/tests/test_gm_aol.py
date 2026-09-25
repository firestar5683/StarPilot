"""Registered GM independent-axis source and permission contracts."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm import gmcan
from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
from opendbc.car.gm.values import CAR, DBC
from opendbc.safety.tests.libsafety import libsafety_py


class TestGmAol(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    self.packer = CANPacker(DBC[CAR.CHEVROLET_VOLT][Bus.pt])

  def tearDown(self):
    self.safety.set_alternative_experience(0)

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def reset(self, word=5, alternative=32):
    self.safety.init_tests()
    self.safety.set_alternative_experience(alternative)
    self.assertEqual(self.safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, word), 0)
    self.safety.set_timer(1_000_000)
    self.safety.set_aol_test_heartbeat(True)

  def feed(self, *, main=True, active=False, gas=False, brake=False, missing=None):
    frames = pt_frames(self.packer, main=main, cruise=active, gas=gas, brake=brake,
                       acc_cruise=2 if active else 0)
    frames.append(self.packer.make_can_msg('EBCMRegenPaddle', 0, {}))
    frames.append((0xF1, bytes(6), 0))
    for frame in frames:
      if frame[0] != missing:
        self.safety.safety_rx_hook(self.packet(frame))
    self.safety.safety_tick()

  def request(self, axes):
    self.safety.aol_set_host_request(axes)
    return self.safety.aol_get_permission_mask()

  def test_registered_main_source_without_stock_cruise(self):
    # BE-selected ASCM/SDGM rows must receive C9 through the actual registry.
    for word in (5, 0x205, 0x1005, 0x4004, 0xC004):
      with self.subTest(word=hex(word)):
        self.reset(word)
        self.feed()
        self.assertFalse(self.safety.get_controls_allowed())
        self.assertEqual(self.request(1), 1, hex(word))
        steering = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
        self.assertTrue(self.safety.safety_tx_hook(self.packet(steering)))
        self.assertEqual(self.request(3), 1)
        self.safety.set_controls_allowed(True)
        self.assertEqual(self.request(3), 3)
        self.safety.set_controls_allowed(False)
        self.assertEqual(self.request(2), 0)

  def test_main_source_missing_wrong_bus_length_and_expiry(self):
    for word in (5, 0x205, 0x1005):
      with self.subTest(word=hex(word)):
        self.reset(word)
        self.feed(missing=0xC9)
        self.assertEqual(self.request(1), 0)
        main = self.packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1})
        self.safety.safety_rx_hook(self.packet((main[0], main[1], 2)))
        self.assertEqual(self.request(1), 0)
        self.safety.safety_rx_hook(self.packet((main[0], main[1][:-1], 0)))
        self.assertEqual(self.request(1), 0)
        self.feed()
        self.assertEqual(self.request(1), 1)
        self.safety.set_timer(1_300_001)
        self.safety.aol_set_host_request(1)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_main_off_heartbeat_and_mode_reset(self):
    self.reset()
    self.feed()
    self.assertEqual(self.request(1), 1)
    self.feed(main=False)
    self.assertEqual(self.safety.aol_get_request_mask(), 0)
    self.assertEqual(self.request(1), 0)
    self.feed()
    self.assertEqual(self.request(1), 1)
    self.safety.set_aol_test_heartbeat(False)
    self.assertEqual(self.request(1), 0)
    for alternative in (0, 4, 33, 34, 64):
      self.reset(alternative=alternative)
      self.feed()
      self.assertEqual(self.request(1), 0)
    self.reset()
    self.feed()
    self.assertEqual(self.request(1), 1)
    self.safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)


  def test_volt_gas_override_retains_long_axis_but_lateral_only_cannot_set(self):
    from opendbc.safety.tests.test_gm_volt_cc_gas import TestGmVoltCcGas
    fixture = TestGmVoltCcGas()
    fixture.setUp()
    for axes in (1, 3):
      fixture.safety.init_tests()
      fixture.safety.set_alternative_experience(32)
      fixture.safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, 20)
      fixture.safety.set_aol_test_heartbeat(True)
      fixture.safety.set_timer(990_000)
      fixture.feed(counter=3, gas=False)
      fixture.safety.set_timer(1_000_000)
      fixture.feed(counter=0, gas=True)
      fixture.safety.aol_set_host_request(axes)
      self.assertEqual(fixture.safety.get_controls_allowed(), not self.release)
      self.assertFalse(fixture.tx(button=2))
      self.assertEqual(fixture.tx(button=3), axes == 3 and not self.release)
      self.assertFalse(fixture.tx(button=3))
      fixture.safety.set_controls_allowed(False)
      self.assertFalse(fixture.tx(button=3))

  def test_base_gateway_typed_axes_and_ordinary_controls(self):
    from opendbc.safety.tests.test_gm_volt_auto_hold import TestVoltAutoHold
    for word in (0, 0x80):
      for alternative in (0, 32):
        with self.subTest(word=word, alternative=alternative):
          f = TestVoltAutoHold()
          f.init(word=word, alternative=alternative)
          f.observations(regen_source=False)
          f.safety.set_aol_test_heartbeat(True)
          f.safety.aol_set_host_request(3)
          self.assertFalse(f.safety.get_controls_allowed())
          self.assertEqual(f.safety.aol_get_permission_mask(), 1 if alternative == 32 else 0)
          steering = gmcan.create_steering_control(f.packer, 0, 1, 0, True)
          self.assertEqual(f.safety.safety_tx_hook(self.packet(steering)), alternative == 32)
          self.assertFalse(f.tx(80))
          f.rx(0x1E1, [0, 0, 0, 0, 0, 0x20, 0])
          self.assertTrue(f.safety.get_controls_allowed())
          if alternative == 32:
            self.assertEqual(f.safety.aol_get_permission_mask(), 3)
          self.assertTrue(f.safety.safety_tx_hook(self.packet(steering)))
          self.assertTrue(f.tx(400, 0xA))
          self.assertFalse(f.tx(401, 0xA))
          f.observations(brake=True, regen_source=False)
          self.assertFalse(f.safety.get_controls_allowed())
          if alternative == 32:
            self.assertEqual(f.safety.aol_get_permission_mask(), 1)
          f.observations(main=False, regen_source=False)
          self.assertFalse(f.safety.safety_tx_hook(self.packet(steering)))

  def test_base_gateway_main_health_and_unknown_neighbors(self):
    from opendbc.safety.tests.test_gm_volt_auto_hold import TestVoltAutoHold
    for word in (0, 0x80):
      f = TestVoltAutoHold()
      f.init(word=word, alternative=32)
      f.observations(regen_source=False)
      f.safety.set_aol_test_heartbeat(True)
      self.assertEqual(self.request(1), 1)
      f.safety.set_timer(f.time + 300001)
      self.assertEqual(self.request(1), 0)
      f.observations(main=False, regen_source=False)
      self.assertEqual(self.request(1), 0)
    for word in (0x40, 0x81, 0x82, 0x84, 0x180):
      self.reset(word)
      self.feed()
      self.assertEqual(self.request(3), 0)
