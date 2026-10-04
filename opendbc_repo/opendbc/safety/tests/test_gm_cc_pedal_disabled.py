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


class TestGmCcPedalDisabled(unittest.TestCase):
  WORDS = (0xC186, 0xC187)

  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker('gm_global_a_powertrain_generated')
    self.safety.set_alternative_experience(0)
    self.init(self.WORDS[0])

  def tearDown(self):
    self.safety.set_alternative_experience(0)

  def init(self, word):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(0)

  @staticmethod
  def packet(msg):
    return libsafety_py.make_CANPacket(msg[0], msg[2], msg[1])

  def rx(self, addr, data, bus=0):
    return self.safety.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, bytes(data)))

  def buttons(self, counter, button=1, bus=0):
    return self.packet(create_buttons(self.packer, bus, counter, button))

  def sensor(self, counter, track1=604, track2=304, bad_crc=False):
    data = bytearray([track1 >> 8, track1 & 255, track2 >> 8, track2 & 255, counter, 0])
    data[5] = crc(data) ^ int(bad_crc)
    return data

  def sources(self, counter=0, active=True, main=True, brake=False, gear=4, skip=None):
    c9, stock, prndl = bytearray(8), bytearray(8), bytearray(8)
    c9[3], c9[5], stock[4], prndl[3] = int(main) << 5, int(brake), int(active) << 7, gear
    sources = {0x184: bytes(8), 0x34A: bytes(5), 0xF1: bytes(6), 0x1C4: bytes(8),
               0xC9: c9, 0x1F5: prndl, 0x201: self.sensor(counter), 0x3D1: stock}
    for addr, data in sources.items():
      if addr != skip:
        self.rx(addr, data)
    if skip != 0x1E1:
      self.safety.safety_rx_hook(self.buttons(counter % 4))

  def cancel(self, counter, bus=2):
    return self.buttons(counter, 6, bus)

  def test_observed_camera_cancel_and_no_stock_inactive_exception(self):
    for word in self.WORDS:
      for active in (False, True):
        self.init(word)
        self.sources(active=active)
        self.assertFalse(self.safety.get_controls_allowed())
        self.assertEqual(self.safety.safety_tx_hook(self.cancel(0)), active)
      # Switching owners must not leak the disabled bus/counter codec into active words.
      self.init(0xC181 if word == 0xC187 else 0xC180)
      self.sources()
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(0)))
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(0, 0)))
      self.assertTrue(self.safety.safety_tx_hook(self.cancel(1, 0)))

  def test_main_stock_button_leases(self):
    for word in self.WORDS:
      self.init(word)
      self.sources(main=False)
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(0)))
      self.init(word)
      self.sources()
      self.safety.set_timer(300000)
      self.assertTrue(self.safety.safety_tx_hook(self.cancel(0)))
      for missing in (0xC9, 0x3D1, 0x1E1):
        with self.subTest(word=word, missing=missing):
          self.init(word)
          self.sources()
          self.safety.set_timer(300001)
          self.sources(counter=1, skip=missing)
          if missing != 0x1E1:
            self.safety.safety_rx_hook(self.buttons(2))
          self.assertFalse(self.safety.safety_tx_hook(self.cancel(0 if missing == 0x1E1 else 2)))

  def test_full_template_wrong_bus_counter_and_buttons(self):
    for word in self.WORDS:
      self.init(word)
      self.sources()
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(0, 0)))
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(1)))
      for button in (0, 1, 2, 3, 4, 5, 7):
        self.assertFalse(self.safety.safety_tx_hook(self.buttons(0, button, 2)))
      canonical = create_buttons(self.packer, 2, 0, 6)[1]
      for bit in range(56):
        data = bytearray(canonical)
        data[bit // 8] ^= 1 << (bit % 8)
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x1E1, 2, bytes(data))))
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x1E1, 2, canonical[:-1])))
      self.assertTrue(self.safety.safety_tx_hook(self.cancel(0)))

  def test_neutral_credit_cadence_and_interleaved_stock(self):
    for word in self.WORDS:
      self.init(word)
      self.sources()
      self.assertTrue(self.safety.safety_tx_hook(self.cancel(0)))
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(0)))
      self.safety.set_timer(40000)
      self.safety.safety_rx_hook(self.buttons(1))
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(1)))
      self.safety.set_timer(40001)
      self.assertTrue(self.safety.safety_tx_hook(self.cancel(1)))
      self.safety.set_timer(90000)
      self.safety.safety_rx_hook(self.buttons(1))
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(1)))
      self.safety.safety_rx_hook(self.buttons(3))
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(3)))
      self.safety.safety_rx_hook(self.buttons(0))
      self.rx(0x3D1, bytes(8))
      active = bytearray(8)
      active[4] = 128
      self.rx(0x3D1, active)
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(0)))
      self.safety.safety_rx_hook(self.buttons(1))
      self.assertTrue(self.safety.safety_tx_hook(self.cancel(1)))

  def test_cancel_while_braking_or_driver_override_and_sensor_fault(self):
    for word in self.WORDS:
      for condition in ('brake', 'gas', 'reverse', 'sensor_crc', 'sensor_replay'):
        with self.subTest(word=word, condition=condition):
          self.init(word)
          self.sources(brake=condition == 'brake', gear=2 if condition == 'reverse' else 4)
          if condition == 'gas':
            self.rx(0x201, self.sensor(1, 900, 450))
          elif condition == 'sensor_crc':
            self.rx(0x201, self.sensor(1, bad_crc=True))
          elif condition == 'sensor_replay':
            self.rx(0x201, self.sensor(0))
          self.assertTrue(self.safety.safety_tx_hook(self.cancel(0)))
          self.safety.set_controls_allowed(True)
          for fraction in (0., .2):
            self.assertFalse(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, fraction, 0))))

  def test_common_rx_and_relay_health(self):
    for word in self.WORDS:
      self.init(word)
      self.sources()
      self.safety.set_relay_malfunction(True)
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(0)))
      self.safety.set_relay_malfunction(False)
      self.safety.set_timer(2000000)
      self.safety.safety_tick()
      self.sources(counter=1)
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(1)))
      self.safety.safety_tick()
      self.safety.safety_rx_hook(self.buttons(2))
      self.assertTrue(self.safety.safety_tx_hook(self.cancel(2)))

  def test_camera_acc_status_does_not_replace_pt_cruise(self):
    for word in self.WORDS:
      for active in (False, True):
        self.init(word)
        self.sources(active=active)
        status = bytearray(6)
        status[2] = 0 if active else 128
        self.rx(0x370, status, 2)
        self.assertEqual(self.safety.safety_tx_hook(self.cancel(0)), active)
      self.init(word)
      self.sources(skip=0x3D1)
      status[2] = 128
      self.rx(0x370, status, 2)
      self.assertFalse(self.safety.safety_tx_hook(self.cancel(0)))

  def test_no_longitudinal_authority_including_aol(self):
    for word in self.WORDS:
      for alternative in (0, 32):
        self.safety.set_alternative_experience(alternative)
        self.init(word)
        self.sources()
        if alternative:
          self.safety.set_aol_test_heartbeat(True)
          self.safety.aol_set_host_request(1)
          self.assertEqual(self.safety.aol_get_permission_mask(), 1)
          steer = self.packet(create_steering_control(self.packer, 0, 5, 0, True))
          self.assertTrue(self.safety.safety_tx_hook(steer))
        self.safety.set_controls_allowed(True)
        if alternative:
          self.safety.aol_set_host_request(3)
        for fraction in (0., .2, 1.):
          self.assertFalse(self.safety.safety_tx_hook(self.packet(create_pedal_command(self.packer, fraction, 0))))
        for addr, length in ((0x409, 7), (0x40A, 7), (0x315, 5), (0x2CB, 8), (0x370, 6), (0x3D1, 8), (0xBD, 7), (0x1F5, 8)):
          self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, 0, bytes(length))))
        self.assertTrue(self.safety.safety_tx_hook(self.cancel(0)))
