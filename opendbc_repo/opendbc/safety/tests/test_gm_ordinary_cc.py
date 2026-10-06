"""Non-EV conventional cruise: physical slot, driver and axis ownership."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.gm import gmcan
from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
from opendbc.car.gm.values import CAR, DBC
from opendbc.safety.tests.libsafety import libsafety_py


class TestGmOrdinaryCc(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker(DBC[CAR.CADILLAC_CT6_CC][Bus.pt])

  def tearDown(self):
    self.safety.set_alternative_experience(0)

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def reset(self, word=0xC160, alternative=0):
    self.safety.init_tests()
    self.safety.set_alternative_experience(alternative)
    self.assertEqual(self.safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, word), 0)
    self.safety.set_timer(1_000_000)

  def feed(self, counter=0, *, speed=20., stock_kph=54., active=True, main=True, gas=False, brake=False, gear=4, manual=False, missing=None):
    frames = pt_frames(self.packer, counter=counter, gas=gas, brake=brake)
    replacements = [gmcan.create_buttons(self.packer, 0, counter, 1),
                    self.packer.make_can_msg('EBCMWheelSpdRear', 0, {'RLWheelSpd': speed * 3.6, 'RRWheelSpd': speed * 3.6, 'RLWheelDir': 1, 'RRWheelDir': 1}),
                    self.packer.make_can_msg('ECMCruiseControl', 0, {'CruiseActive': active, 'CruiseSetSpeed': stock_kph}),
                    self.packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': main}),
                    self.packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': gear, 'ManualMode': manual})]
    addresses = {frame[0] for frame in replacements}
    frames = [frame for frame in frames if frame[0] not in addresses and frame[0] != 0xBD] + replacements
    for frame in sorted(frames, key=lambda frame: 2 if frame[0] == 0x1E1 else 1 if frame[0] == 0x3D1 else 0):
      if frame[0] != missing:
        self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    self.safety.safety_tick()

  def tx(self, counter=1, button=2):
    return self.safety.safety_tx_hook(self.packet(gmcan.create_buttons(self.packer, 0, counter, button)))

  def test_physical_credit_and_xt4_counter_burst(self):
    self.reset()
    self.feed()
    self.assertTrue(self.safety.safety_config_valid())
    self.assertTrue(self.tx())
    self.assertFalse(self.tx())
    for step in range(1, 7):
      self.safety.set_timer(1_000_000 + step * 30_000)
      self.feed(counter=step % 4)
      self.assertTrue(self.tx(counter=(step + 1) % 4))
      self.assertFalse(self.tx(counter=(step + 1) % 4))
    self.safety.set_timer(1_181_000)
    self.feed(counter=2)
    self.assertFalse(self.tx(counter=3))
    self.reset()
    self.feed()
    self.assertTrue(self.tx())
    self.safety.set_timer(1_010_000)
    self.feed(counter=1)
    self.assertFalse(self.tx(counter=2))
    self.safety.set_timer(1_021_000)
    self.assertTrue(self.tx(counter=2))

  def test_gas_set_and_longitudinal_axis(self):
    for alternative, axes, allowed in ((0, 0, True), (32, 1, False), (32, 3, True)):
      self.reset(alternative=alternative)
      self.safety.set_aol_test_heartbeat(True)
      self.feed(gas=True)
      self.safety.aol_set_host_request(axes)
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertFalse(self.tx(button=2))
      self.assertEqual(self.tx(button=3), allowed)
      self.assertFalse(self.tx(button=3))
      steering = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
      self.assertTrue(self.safety.safety_tx_hook(self.packet(steering)))
    for stamp, allowed in ((1_519_999, False), (1_520_000, True)):
      self.reset()
      self.feed(gas=True)
      self.assertTrue(self.tx(button=3))
      for step in range(1, 6):
        self.safety.set_timer(1_000_000 + step * 90_000)
        self.feed(counter=step % 4, gas=True)
      self.safety.set_timer(stamp)
      self.feed(counter=2, gas=True)
      self.assertEqual(self.tx(counter=3, button=3), allowed)
    self.reset()
    self.feed(gas=True, stock_kph=72.)
    self.assertFalse(self.tx(button=3))

  def test_driver_source_rearm_gear_and_expiry(self):
    for kwargs in ({'active': False}, {'main': False}, {'gear': 0}, {'gear': 2}, {'manual': True}, {'brake': True}, {'speed': 10.}):
      self.reset()
      self.feed(**kwargs)
      self.assertFalse(self.tx())
    self.reset()
    self.feed(brake=True)
    self.safety.set_timer(1_030_000)
    self.feed(counter=1)
    self.assertFalse(self.tx(counter=2))
    self.safety.set_timer(1_060_000)
    self.feed(counter=2, active=False)
    self.safety.set_timer(1_090_000)
    self.feed(counter=3, gear=6)
    self.assertTrue(self.tx(counter=0))
    self.safety.set_timer(1_190_001)
    self.assertFalse(self.tx(counter=0))
    for address in (0x184, 0x3D1, 0x1E1, 0xC9, 0xBE, 0x1C4, 0x1F5, 0x34A):
      self.reset()
      self.feed(missing=address)
      self.assertFalse(self.safety.safety_config_valid())
      self.assertFalse(self.tx())

  def test_complete_button_tuple_and_unowned_output(self):
    self.reset()
    self.feed()
    good = gmcan.create_buttons(self.packer, 0, 1, 2)
    for index in range(7):
      data = bytearray(good[1])
      data[index] ^= 1
      self.assertFalse(self.safety.safety_tx_hook(self.packet((good[0], bytes(data), 0))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet((good[0], good[1], 2))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet((good[0], good[1][:-1], 0))))
    for address, length in ((0x2CB, 8), (0x315, 5), (0x370, 6), (0x3D1, 8), (0x200, 6), (0xBD, 7), (0x1F5, 8), (0x184, 8)):
      for bus in (0, 1, 2):
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, bytes(length))))
    for address in (0x409, 0x40A):
      self.assertTrue(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(address, 0, bytes(7))))
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(address, 0, bytes([1]) + bytes(6))))
    for bit in (1, 2, 4, 8, 0x200, 0x400, 0x800, 0x2000):
      self.reset(word=0xC160 | bit)
      self.feed()
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.tx())

  def test_aol_off_and_main_following_no_longitudinal_permission(self):
    for alternative in (0, 32):
      self.reset(alternative=alternative)
      self.safety.set_aol_test_heartbeat(True)
      self.feed(active=False)
      self.safety.aol_set_host_request(3)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1 if alternative == 32 else 0)
      self.assertFalse(self.tx())
      steering = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
      self.assertEqual(self.safety.safety_tx_hook(self.packet(steering)), alternative == 32)
      self.feed(active=False, main=False)
      self.safety.aol_set_host_request(1)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_stock_silverado_aol_is_lateral_only_and_requires_forward_gear(self):
    self.reset(word=16, alternative=32)
    self.safety.set_aol_test_heartbeat(True)
    self.feed(active=False)
    self.safety.aol_set_host_request(3)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.safety.set_controls_allowed(True)
    self.safety.aol_set_host_request(3)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.assertFalse(self.tx(button=2))
    self.assertFalse(self.tx(button=3))
    for gear, manual in ((2, False), (3, False), (0, False), (4, True)):
      self.feed(active=False, gear=gear, manual=manual)
      self.safety.aol_set_host_request(1)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.feed(active=False, gear=4)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.safety.set_timer(2_000_001)
    self.feed(active=False, missing=0x1F5)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

  def test_stock_silverado_aol_physical_sources_and_mode_reset(self):
    for missing, deadline in ((0xBE, 2_000_001), (0xC9, 1_300_001), (0x1F5, 2_000_001)):
      with self.subTest(missing=hex(missing)):
        self.reset(word=16, alternative=32)
        self.safety.set_aol_test_heartbeat(True)
        self.feed(active=False)
        self.safety.aol_set_host_request(1)
        self.assertEqual(self.safety.aol_get_permission_mask(), 1)
        self.safety.set_timer(deadline)
        self.feed(active=False, missing=missing)
        self.safety.aol_set_host_request(1)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)

    for bus, length in ((1, 8), (2, 8), (0, 7), (0, 6)):
      with self.subTest(bus=bus, length=length):
        self.reset(word=16, alternative=32)
        self.safety.set_aol_test_heartbeat(True)
        self.feed(active=False, missing=0x1F5)
        gear = self.packer.make_can_msg('ECMPRDNL2', bus, {'PRNDL2': 4})
        self.safety.safety_rx_hook(libsafety_py.make_CANPacket(gear[0], bus, gear[1][:length]))
        self.safety.aol_set_host_request(1)
        self.assertEqual(self.safety.aol_get_permission_mask(), 0)

    self.reset(word=16, alternative=32)
    self.safety.set_aol_test_heartbeat(True)
    self.feed(active=False)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 1)
    self.reset(word=16, alternative=32)
    self.safety.set_aol_test_heartbeat(True)
    self.feed(active=False, missing=0x1F5)
    self.safety.aol_set_host_request(1)
    self.assertEqual(self.safety.aol_get_permission_mask(), 0)

    # The ordinary stock owner retains its original seven checks, without gear admission.
    self.reset(word=16, alternative=0)
    self.feed(active=True, missing=0x1F5)
    self.assertTrue(self.safety.safety_config_valid())
    self.assertTrue(self.safety.get_controls_allowed())

  def test_neutral_request_handoff_does_not_grant_torque(self):
    for kwargs in ({'active': False}, {'active': False, 'main': False}, {'active': False, 'missing': 0xBE}):
      self.reset()
      self.feed(**kwargs)
      self.safety.set_controls_allowed(False)
      neutral = gmcan.create_steering_control(self.packer, 0, 0, 0, True)
      torque = gmcan.create_steering_control(self.packer, 0, 1, 1, True)
      self.assertTrue(self.safety.safety_tx_hook(self.packet(neutral)))
      self.assertFalse(self.safety.safety_tx_hook(self.packet(torque)))
