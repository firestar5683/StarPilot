import os
import unittest

from opendbc.safety.tests.common import CANPackerSafety, make_msg
from opendbc.safety.tests.libsafety import libsafety_py


class TestTeslaScreenButton(unittest.TestCase):
  def setUp(self):
    self.lib = libsafety_py.libsafety
    self.packer = CANPackerSafety('tesla_model3_party')
    self.start(512)

  def tearDown(self):
    self.lib.init_tests()
    self.lib.set_alternative_experience(0)
    self.lib.set_safety_hooks(0, 0)

  def start(self, word):
    self.lib.init_tests()
    self.lib.set_alternative_experience(32)
    self.assertEqual(self.lib.set_safety_hooks(10, word), 0)
    self.time = 1_000_000
    self.lib.set_timer(self.time)
    self.lib.set_aol_test_heartbeat(True)
    for _ in range(12):
      self.feed()
    self.lib.aol_set_host_request(1)

  def feed(self, state=0, brake=False, hands=0, gear=4, door=False, belt=True, eps=1, autopark=0, stock_type=0):
    values = (
      ('DAS_control', 2, {}),
      ('DAS_steeringControl', 2, {'DAS_steeringControlType': stock_type}),
      ('DI_speed', 0, {'DI_vehicleSpeed': 0}),
      ('ESP_B', 0, {'ESP_vehicleSpeed': 0, 'ESP_wheelSpeedsQF': 1, 'ESP_vehicleStandstillSts': 1}),
      ('EPAS3S_sysStatus', 0, {'EPAS3S_internalSAS': 0, 'EPAS3S_eacStatus': eps, 'EPAS3S_handsOnLevel': hands}),
      ('DI_systemStatus', 0, {'DI_gear': gear, 'DI_accelPedalPos': 0}),
      ('ESP_status', 0, {'ESP_driverBrakeApply': 2 if brake else 1}),
      ('UI_warning', 0, {'anyDoorOpen': int(door), 'buckleStatus': int(belt)}),
      ('DI_state', 0, {'DI_cruiseState': state, 'DI_autoparkState': autopark}),
    )
    for name, bus, signals in values:
      self.assertTrue(self.lib.safety_rx_hook(self.packer.make_can_msg_safety(name, bus, signals)))
    self.lib.safety_tick()

  def touch(self, count, bus=1, length=8):
    data = bytearray(length)
    if length > 3:
      data[3] = count
    self.lib.safety_rx_hook(make_msg(bus, 0x3DF, dat=bytes(data)))

  def permission(self, mask=1):
    self.lib.aol_set_host_request(mask)
    return self.lib.aol_get_permission_mask()

  def arm(self):
    self.touch(0)
    self.touch(3)
    self.assertEqual(self.permission(), 1)

  def test_first_touch_baseline_exact_optional_ingress_and_toggle(self):
    self.touch(3)
    self.assertEqual(self.permission(), 0)
    self.touch(3)
    self.assertEqual(self.permission(), 0)
    self.touch(0)
    for bus, length in ((0, 8), (2, 8), (1, 7), (1, 6)):
      self.touch(3, bus, length)
      self.assertEqual(self.permission(), 0)
    self.touch(3)
    self.assertEqual(self.permission(), 1)
    self.touch(3)
    self.assertEqual(self.permission(), 1)
    self.touch(2)
    self.touch(3)
    self.assertEqual(self.permission(), 0)

  def test_cruise_baseline_screen_override_and_main_cycle(self):
    self.feed(state=1)
    self.assertEqual(self.permission(), 1)
    self.touch(0)
    self.touch(3)
    self.assertEqual(self.permission(), 0)
    self.feed(state=2)
    self.assertEqual(self.permission(), 1)
    self.touch(0)
    self.touch(3)
    self.assertEqual(self.permission(), 0)
    self.feed(state=0)
    self.feed(state=1)
    self.assertEqual(self.permission(), 1)

  def test_brake_word_and_physical_faults_withdraw(self):
    for word in (512, 1536):
      self.start(word)
      self.arm()
      self.feed(brake=True)
      self.assertEqual(self.permission(), 1 if word == 512 else 0)
    for fault in ({'hands': 3}, {'gear': 2}, {'door': True}, {'belt': False}, {'eps': 3}, {'autopark': 3}):
      self.start(512)
      self.arm()
      self.feed(**fault)
      self.assertEqual(self.permission(), 0, fault)
      self.feed()
      self.assertEqual(self.permission(), 0, fault)
      self.arm()

  def test_expired_request_and_unhealthy_sources_require_new_gesture(self):
    self.arm()
    self.time += 1_100_000
    self.lib.set_timer(self.time)
    self.assertEqual(self.lib.aol_get_permission_mask(), 0)
    self.feed()
    self.assertEqual(self.permission(), 0)
    self.arm()
    self.lib.set_aol_test_heartbeat(False)
    self.assertEqual(self.permission(), 0)
    self.lib.set_aol_test_heartbeat(True)
    self.assertEqual(self.permission(), 0)

  def test_typed_lateral_does_not_grant_longitudinal(self):
    self.arm()
    self.assertEqual(self.permission(3), 1)
    positive = self.packer.make_can_msg_safety('DAS_control', 0, {'DAS_accelMin': 1, 'DAS_accelMax': 1})
    self.assertFalse(self.lib.safety_tx_hook(positive))
    steering = self.packer.make_can_msg_safety('DAS_steeringControl', 0,
                                              {'DAS_steeringAngleRequest': 0, 'DAS_steeringControlType': 1})
    self.assertTrue(self.lib.safety_tx_hook(steering))
    self.touch(0)
    self.touch(3)
    self.assertFalse(self.lib.safety_tx_hook(steering))

  def test_screen_namespace_excludes_hw1_neighbors_and_unknown_flags(self):
    for word in (16 | 512, 1024, 514, 1538, 512 | 256, 0xFFFF):
      self.assertEqual(self.lib.set_safety_hooks(10, word), -1, hex(word))

  def test_exact_long_words_debug_authority_and_release_rejection(self):
    for word in (513, 1537):
      if os.environ.get('TESLA_SCREEN_NATIVE_RELEASE') == '1':
        self.assertEqual(self.lib.set_safety_hooks(10, word), -1)
        positive = self.packer.make_can_msg_safety('DAS_control', 0, {'DAS_accelMin': 1, 'DAS_accelMax': 1})
        self.assertFalse(self.lib.safety_tx_hook(positive))
      else:
        self.start(word)
        self.feed(state=2)
        self.assertEqual(self.permission(3), 3)
        positive = self.packer.make_can_msg_safety('DAS_control', 0, {'DAS_accelMin': 1, 'DAS_accelMax': 1})
        self.assertTrue(self.lib.safety_tx_hook(positive))
        self.feed(state=0)
        self.assertEqual(self.permission(3), 0)
        self.arm()
        self.assertEqual(self.permission(3), 1)
        self.assertFalse(self.lib.safety_tx_hook(positive))

  def test_stock_lkas_ownership_and_bus_one_remain_separate(self):
    self.arm()
    self.feed(stock_type=2)
    self.assertEqual(self.permission(), 1)
    self.assertEqual(self.lib.safety_fwd_hook(2, 0x488), -1)
    self.assertEqual(self.lib.safety_fwd_hook(1, 0x3DF), -1)
    self.touch(0)
    self.touch(3)
    self.feed(stock_type=0)
    self.feed(stock_type=2)
    self.assertEqual(self.permission(), 0)
    self.assertEqual(self.lib.safety_fwd_hook(2, 0x488), 0)
