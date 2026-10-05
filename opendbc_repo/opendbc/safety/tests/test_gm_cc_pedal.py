import unittest

from opendbc.can import CANPacker
from opendbc.car.gm.gmcan import create_buttons, create_pedal_command, create_steering_control
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


def crc(data):
  value = 255
  for byte in reversed(data[:5]):
    value ^= byte
    for _ in range(8):
      value = ((value << 1) ^ (0xD5 if value & 128 else 0)) & 255
  return value


class TestGmCcPedal(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker('gm_global_a_powertrain_generated')
    self.init(0xC180)

  def init(self, word):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(0)

  @staticmethod
  def packet(msg):
    return libsafety_py.make_CANPacket(msg[0], msg[2], msg[1])

  def rx(self, addr, data, bus=0):
    return self.safety.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, bytes(data)))

  def buttons(self, counter, button=1):
    return self.packet(create_buttons(self.packer, 0, counter, button))

  def sensor(self, counter, track1=604, track2=304, bad_crc=False):
    data = bytearray([track1 >> 8, track1 & 255, track2 >> 8, track2 & 255, counter, 0])
    data[5] = crc(data) ^ int(bad_crc)
    return data

  def feed(self, counter=0, active=False, main=True, gear=4, brake=False):
    self.rx(0x184, bytes(8))
    self.rx(0x34A, bytes(5))
    self.rx(0xF1, bytes(6))
    self.rx(0x1C4, bytes(8))
    c9 = bytearray(8)
    c9[3] = 32 if main else 0
    c9[5] = int(brake)
    self.rx(0xC9, c9)
    prndl = bytearray(8)
    prndl[3] = gear
    self.rx(0x1F5, prndl)
    self.rx(0x201, self.sensor(counter))
    stock = bytearray(8)
    stock[4] = 128 if active else 0
    self.rx(0x3D1, stock)
    self.safety.safety_rx_hook(self.buttons(counter % 4))

  def command(self, counter, fraction=.2):
    return self.packet(create_pedal_command(self.packer, fraction, counter))

  def engage(self):
    self.safety.safety_rx_hook(self.buttons(0, 2))

  def test_physical_latch_independent_from_stock_and_sensor_drop_recovery(self):
    for word in (0xC180, 0xC181):
      self.init(word)
      self.feed(active=False)
      self.assertFalse(self.safety.get_controls_allowed())
      self.engage()
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
      self.rx(0x201, self.sensor(3))  # Missed sensor counters do not revoke the independent latch.
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertTrue(self.safety.safety_tx_hook(self.command(2)))
      self.rx(0x3D1, bytes(8))
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertTrue(self.safety.safety_tx_hook(self.command(3)))
      self.assertFalse(self.safety.safety_tx_hook(self.command(4)))
      low = bytearray(8)
      low[3] = 6
      self.rx(0x1F5, low)
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
      low[3] = 4
      self.rx(0x1F5, low)
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertTrue(self.safety.safety_tx_hook(self.command(1)))

  def test_sensor_crc_override_and_stale_sources(self):
    self.feed()
    self.engage()
    self.rx(0x201, self.sensor(1, bad_crc=True))
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
    self.assertTrue(self.safety.safety_tx_hook(self.command(0, 0.)))
    self.rx(0x201, self.sensor(4))
    self.engage()
    # Release then press is a genuine physical rearm edge.
    self.safety.safety_rx_hook(self.buttons(1))
    self.engage()
    self.assertTrue(self.safety.safety_tx_hook(self.command(1)))
    self.safety.set_timer(100001)
    self.assertFalse(self.safety.safety_tx_hook(self.command(2)))
    self.assertTrue(self.safety.safety_tx_hook(self.command(2, 0.)))
    self.rx(0x201, self.sensor(8, track1=900, track2=450))
    self.assertFalse(self.safety.safety_tx_hook(self.command(3)))

  def test_cancel_has_physical_credit_and_never_acceleration_buttons(self):
    self.feed(active=True)
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertTrue(self.safety.safety_tx_hook(self.buttons(1, 6)))
    self.assertFalse(self.safety.safety_tx_hook(self.buttons(1, 6)))
    self.assertFalse(self.safety.safety_tx_hook(self.buttons(1, 2)))
    self.assertFalse(self.safety.safety_tx_hook(self.buttons(1, 3)))
    self.safety.set_timer(50000)
    self.safety.safety_rx_hook(self.buttons(1))
    self.assertTrue(self.safety.safety_tx_hook(self.buttons(2, 6)))
    self.safety.set_timer(100000)
    self.safety.safety_rx_hook(self.buttons(1))
    self.assertFalse(self.safety.safety_tx_hook(self.buttons(2, 6)))
    self.rx(0x3D1, bytes(8))
    self.safety.safety_rx_hook(self.buttons(2))
    self.assertFalse(self.safety.safety_tx_hook(self.buttons(3, 6)))

  def test_main_brake_gear_and_wrong_sensor_provenance(self):
    for main, gear, brake in ((False, 4, False), (True, 2, False), (True, 0, False), (True, 4, True)):
      self.init(0xC180)
      self.feed(main=main, gear=gear, brake=brake)
      self.engage()
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
    self.init(0xC180)
    self.feed()
    self.engage()
    self.safety.set_timer(100001)
    self.rx(0x201, self.sensor(1), bus=2)
    self.rx(0x201, self.sensor(1)[:-1])
    self.assertFalse(self.safety.safety_tx_hook(self.command(0)))

  def test_topology_and_unowned_messages(self):
    for word in (0xC180, 0xC181):
      self.init(word)
      for addr, length in ((0x315, 8), (0x2CB, 5), (0x370, 6), (0x3D1, 8), (0xBD, 7), (0x1F5, 8)):
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, 0, bytes(length))))
      for addr in (0x409, 0x40A):
        packet = libsafety_py.make_CANPacket(addr, 0, bytes(7))
        self.assertEqual(self.safety.safety_tx_hook(packet), word == 0xC181)
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, 0, bytes([1] + [0] * 6))))

  def test_cancel_jitter_skipped_slot_and_idle_recovery(self):
    self.feed(active=True)
    self.assertTrue(self.safety.safety_tx_hook(self.buttons(1, 6)))
    self.safety.set_timer(110000)
    self.safety.safety_rx_hook(self.buttons(1))
    self.assertTrue(self.safety.safety_tx_hook(self.buttons(2, 6)))
    self.safety.set_timer(220000)
    self.safety.safety_rx_hook(self.buttons(3))  # A dropped physical neutral cannot grant fresh credit.
    self.assertFalse(self.safety.safety_tx_hook(self.buttons(0, 6)))
    self.safety.set_timer(250000)
    self.safety.safety_rx_hook(self.buttons(0))
    self.assertTrue(self.safety.safety_tx_hook(self.buttons(1, 6)))
    self.safety.set_timer(600000)
    self.feed(counter=1, active=True)
    self.assertFalse(self.safety.safety_tx_hook(self.buttons(2, 6)))
    self.safety.set_timer(650000)
    self.safety.safety_rx_hook(self.buttons(2))
    self.assertTrue(self.safety.safety_tx_hook(self.buttons(3, 6)))

  def test_aol_lateral_never_grants_pedal_longitudinal(self):
    for word in (0xC180, 0xC181):
      self.safety.set_alternative_experience(32)
      self.init(word)
      self.safety.set_aol_test_heartbeat(True)
      self.feed(active=False)
      self.safety.aol_set_host_request(1)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      steer = self.packet(create_steering_control(self.packer, 0, 5, 0, True))
      self.assertTrue(self.safety.safety_tx_hook(steer))
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
      self.engage()
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
      self.safety.aol_set_host_request(3)
      self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
    self.safety.set_alternative_experience(0)

  def test_recorded_adc_tracks_and_overflow_keep_command_pair_contract(self):
    for sample in ('053502ba0164', '04e30286048f', '046c024108e3', '0279012a06f6'):
      with self.subTest(sample=sample):
        self.init(0xC180)
        self.feed()
        self.engage()
        self.assertTrue(self.safety.get_controls_allowed())
        data = bytes.fromhex(sample)
        self.assertEqual(crc(data), data[5])
        self.assertTrue(self.rx(0x201, data))
        self.assertTrue(self.safety.get_controls_allowed())
        self.assertEqual(self.safety.safety_tx_hook(self.command(1)), sample == '0279012a06f6')
    self.init(0xC180)
    self.feed()
    self.engage()
    command = create_pedal_command(self.packer, .2, 1)
    bad_pair = bytearray(command[1])
    bad_pair[2:4] = (int.from_bytes(bad_pair[2:4], "big") + 12).to_bytes(2, "big")
    bad_pair[5] = crc(bad_pair)
    self.assertFalse(self.safety.safety_tx_hook(self.packet((command[0], bytes(bad_pair), command[2]))))
    self.assertTrue(self.safety.safety_tx_hook(self.packet(command)))
    for track1, track2 in ((4096, 304), (604, 4096)):
      self.feed(counter=8 if track1 == 4096 else 9)
      self.safety.safety_rx_hook(self.buttons(1))
      self.engage()
      self.assertTrue(self.safety.get_controls_allowed())
      self.rx(0x201, self.sensor(2 if track1 == 4096 else 3, track1=track1, track2=track2))
      self.assertFalse(self.safety.get_controls_allowed())
