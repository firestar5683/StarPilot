import unittest

from opendbc.car import structs
from opendbc.safety.tests.common import make_msg
from opendbc.safety.tests.libsafety import libsafety_py


class TestTeslaPreapStock(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.safety.init_tests()
    self.safety.set_alternative_experience(32)
    self.safety.set_safety_hooks(39, 0)
    self.time = 1_000_000
    self.counter = 0
    self.safety.set_timer(self.time)

  def tearDown(self):
    self.safety.init_tests()
    self.safety.set_alternative_experience(0)
    self.safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)

  @staticmethod
  def crc(data):
    crc = 255
    for byte in data:
      crc ^= byte
      for _ in range(8):
        crc = ((crc << 1) ^ 29 if crc & 128 else crc << 1) & 255
    return crc ^ 255

  def stalk(self, lever, counter=None):
    data = bytearray(8)
    data[0] = lever | 64
    data[6] = (self.counter if counter is None else counter) << 4
    data[7] = self.crc(data[:7])
    return make_msg(0, 0x45, dat=bytes(data))

  def feed(self, lever=0, brake=1, gear=4, eps=1, belt=1, stalk=True, fault=None, target=None):
    packets = (
      (0x108, bytes(8)),
      (0x118, bytes([0, gear << 4, 0, 0, 0, 0])),
      (0x20A, bytes([brake << 2]) + bytes(7)),
      (0x368, bytes([0, 16]) + bytes(6)),
      (0x318, bytes(8)),
      (0x155, bytes(5) + bytes([31, 64, 0])),
      (0x370, bytes(4) + bytes([32, 0, eps << 5, 0])),
      (0x201, bytes([belt << 4]) + bytes(4)),
    )
    for address, data in packets:
      if address == target:
        if fault == 'missing':
          continue
        self.safety.safety_rx_hook(make_msg(1 if fault == 'bus' else 0, address,
                                           dat=data[:-1] if fault == 'length' else data))
      else:
        self.safety.safety_rx_hook(make_msg(0, address, dat=data))
    if stalk:
      self.counter = (self.counter + 1) % 16
      packet = self.stalk(lever)
      if target != 0x45:
        self.safety.safety_rx_hook(packet)
      elif fault != 'missing':
        data = bytes([lever | 64]) + bytes(5) + bytes([self.counter << 4])
        self.safety.safety_rx_hook(make_msg(1 if fault == 'bus' else 0, 0x45,
                                           dat=data if fault == 'length' else data + bytes([self.crc(data)])))
    self.safety.safety_tick()

  def arm(self):
    self.safety.set_aol_test_heartbeat(False)
    for _ in range(10):
      self.feed()
    self.feed(lever=2)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.safety.set_aol_test_heartbeat(True)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)

  def test_physical_grant_brake_truth_and_fault_rearm(self):
    self.arm()
    self.feed(brake=2)
    self.assertTrue(self.safety.get_brake_pressed_prev())
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.feed(brake=0)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.feed()
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.feed(lever=2)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.feed(eps=3)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_exact_cancel_echo_single_consume_then_physical_cancel(self):
    self.arm()
    echo = self.stalk(1, (self.counter + 1) % 16)
    self.assertTrue(self.safety.safety_tx_hook(echo))
    self.assertTrue(self.safety.safety_rx_hook(echo))
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.feed()
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.feed(lever=1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_duplicate_counter_and_software_echo_cannot_refresh_physical_source(self):
    self.arm()
    self.safety.safety_rx_hook(self.stalk(2))
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.arm()
    echo = self.stalk(1, (self.counter + 1) % 16)
    self.assertTrue(self.safety.safety_tx_hook(echo))
    self.time += 99_000
    self.safety.set_timer(self.time)
    self.safety.safety_rx_hook(echo)
    self.time += 201_001
    self.safety.set_timer(self.time)
    self.feed(stalk=False)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_epas_mode_checksum_and_forbidden_longitudinal(self):
    for mode in (0, 1):
      data = bytes([mode, 0, (22 + mode) & 255])
      self.assertTrue(self.safety.safety_tx_hook(make_msg(0, 0x214, dat=data)))
    for data in (bytes([2, 0, 24]), bytes([1, 16, 39]), bytes([1, 0, 0])):
      self.assertFalse(self.safety.safety_tx_hook(make_msg(0, 0x214, dat=data)))
    for address, length in ((0x2B9, 8), (0x551, 6)):
      self.assertFalse(self.safety.safety_tx_hook(make_msg(0, address, dat=bytes(length))))

  def test_cold_held_main_and_stock_engagement_cannot_arm(self):
    self.safety.set_aol_test_heartbeat(True)
    for _ in range(20):
      self.feed(lever=2)
      self.safety.aol_set_host_request(1)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.feed()
    self.feed(lever=2)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)

  @staticmethod
  def steering(angle=0, control_type=1):
    raw = angle + 16384
    data = bytearray([(raw >> 8) & 127, raw & 255, control_type << 6, 0])
    data[3] = (140 + sum(data[:3])) & 255
    return make_msg(0, 0x488, dat=bytes(data))

  def test_angle_limits_rate_checksum_type_and_disabled_neutral(self):
    self.arm()
    self.assertTrue(self.safety.safety_tx_hook(self.steering()))
    for angle in (-3601, 3601, -3600, 3600):
      self.assertFalse(self.safety.safety_tx_hook(self.steering(angle)))
    self.assertTrue(self.safety.safety_tx_hook(self.steering(control_type=0)))
    self.assertFalse(self.safety.safety_tx_hook(self.steering(1000, control_type=0)))
    for control_type in (2, 3):
      self.assertFalse(self.safety.safety_tx_hook(self.steering(control_type=control_type)))
    self.assertFalse(self.safety.safety_tx_hook(make_msg(0, 0x488, dat=bytes([64, 0, 64, 0]))))
    self.assertFalse(self.safety.safety_tx_hook(make_msg(1, 0x488, dat=bytes([64, 0, 64, 12]))))

  def test_all_16bit_parameters_reject_every_nonzero_profile(self):
    command = self.steering(control_type=0)
    for parameter in range(65536):
      self.safety.set_safety_hooks(39, parameter)
      self.assertEqual(bool(self.safety.safety_tx_hook(command)), parameter == 0, parameter)

  def test_required_sources_loss_wrong_bus_length_and_fresh_rearm(self):
    for address in (0x370, 0x108, 0x118, 0x20A, 0x368, 0x318, 0x45, 0x155, 0x201):
      for fault in ('missing', 'bus', 'length'):
        with self.subTest(address=address, fault=fault):
          self.setUp()
          self.arm()
          for _ in range(120):
            self.time += 10_000
            self.safety.set_timer(self.time)
            self.feed(target=address, fault=fault)
            self.safety.aol_set_host_request(1)
          self.assertEqual(self.safety.aol_get_permission_mask(), 0)
          for _ in range(10):
            self.feed()
            self.safety.aol_set_host_request(1)
            self.assertEqual(self.safety.aol_get_permission_mask(), 0)
          self.feed(lever=2)
          self.safety.aol_set_host_request(1)
          self.assertEqual(self.safety.aol_get_permission_mask(), 1)
