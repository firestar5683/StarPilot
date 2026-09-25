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


class TestGmSilveradoPedal(unittest.TestCase):
  WORDS = (0xC182, 0xC183, 0xC184, 0xC185)
  LENGTHS = {0x184: 8, 0x34A: 5, 0xC9: 8, 0x3D1: 8, 0x1E1: 7, 0x1C4: 8, 0x1F5: 8, 0x201: 6}

  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker('gm_global_a_powertrain_generated')
    self.safety.set_alternative_experience(0)
    self.init(0xC182)

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

  def sensor(self, counter, track1=604, track2=304, state=0, bad_crc=False):
    data = bytearray([track1 >> 8, track1 & 255, track2 >> 8, track2 & 255, (state << 4) | counter, 0])
    data[5] = crc(data) ^ int(bad_crc)
    return data

  def sources(self, counter=0, active=False, main=True, gear=4, brake=False, skip=None, bus=0):
    c9, stock, prndl = bytearray(8), bytearray(8), bytearray(8)
    c9[3], c9[5], stock[4], prndl[3] = (32 if main else 0), int(brake), (128 if active else 0), gear
    values = {0x184: bytes(8), 0x34A: bytes(5), 0xC9: c9, 0x3D1: stock,
              0x1C4: bytes(8), 0x1F5: prndl, 0x201: self.sensor(counter)}
    for addr, data in values.items():
      if addr != skip:
        self.rx(addr, data, bus=bus)
    if skip != 0x1E1:
      self.safety.safety_rx_hook(self.buttons(counter % 4, bus=bus))

  def command(self, counter, fraction=.2, bus=0):
    msg = create_pedal_command(self.packer, fraction, counter)
    return libsafety_py.make_CANPacket(msg[0], bus, msg[1])

  def engage(self):
    self.safety.safety_rx_hook(self.buttons(0, 2))

  def test_active_pedal_latch_and_stock_cancel_pending(self):
    for word in self.WORDS[:2]:
      for active in (False, True):
        self.init(word)
        self.sources(active=active)
        self.assertFalse(self.safety.get_controls_allowed())
        self.engage()
        self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
        self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
        self.assertTrue(self.safety.safety_tx_hook(self.command(2)))
        self.assertFalse(self.safety.safety_tx_hook(self.command(4)))
        self.assertFalse(self.safety.safety_tx_hook(self.command(3, bus=2)))

  def test_cancel_bus_counter_and_disabled_stock_state(self):
    for word in self.WORDS:
      disabled = word >= 0xC184
      for active in (False, True):
        self.init(word)
        self.sources(counter=2, active=active)
        counter, bus = (2, 2) if disabled else (3, 0)
        # An interleaved stock-off update must not erase valid disabled credit.
        stock = bytearray(8)
        stock[4] = 128 if active else 0
        self.rx(0x3D1, stock)
        self.assertFalse(self.safety.safety_tx_hook(self.buttons(counter, 6, 2 - bus)))
        self.assertFalse(self.safety.safety_tx_hook(self.buttons((counter + 1) % 4, 6, bus)))
        self.assertEqual(self.safety.safety_tx_hook(self.buttons(counter, 6, bus)), disabled or active)
        self.assertFalse(self.safety.safety_tx_hook(self.buttons(counter, 6, bus)))
        for button in (1, 2, 3):
          self.assertFalse(self.safety.safety_tx_hook(self.buttons(counter, button, bus)))
        self.assertFalse(self.safety.safety_tx_hook(self.command(0)))

  def test_cancel_credit_cadence_replay_and_noncanonical_packet(self):
    for word in self.WORDS:
      disabled, bus = word >= 0xC184, 2 if word >= 0xC184 else 0
      self.init(word)
      self.sources(active=True)
      self.assertTrue(self.safety.safety_tx_hook(self.buttons(0 if disabled else 1, 6, bus)))
      self.safety.set_timer(40000)
      self.sources(counter=1, active=True)
      self.assertFalse(self.safety.safety_tx_hook(self.buttons(1 if disabled else 2, 6, bus)))
      self.safety.set_timer(40001)
      self.assertTrue(self.safety.safety_tx_hook(self.buttons(1 if disabled else 2, 6, bus)))
      self.safety.set_timer(90000)
      self.safety.safety_rx_hook(self.buttons(1))
      self.assertFalse(self.safety.safety_tx_hook(self.buttons(1 if disabled else 2, 6, bus)))
      self.sources(counter=2, active=True)
      msg = create_buttons(self.packer, bus, 2 if disabled else 3, 6)
      for index in range(7):
        mutated = bytearray(msg[1])
        mutated[index] ^= 1
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x1E1, bus, mutated)))
      self.assertTrue(self.safety.safety_tx_hook(self.buttons(2 if disabled else 3, 6, bus)))

  def test_every_selected_source_is_required_and_bus_length_bound(self):
    for word in self.WORDS:
      for addr, length in self.LENGTHS.items():
        self.init(word)
        self.sources(active=True, skip=addr)
        self.rx(addr, bytes(length), bus=2)
        self.rx(addr, bytes(length - 1))
        if word >= 0xC184:
          self.assertFalse(self.safety.safety_tx_hook(self.buttons(0, 6, 2)))
        else:
          self.safety.set_controls_allowed(True)  # Isolate RX freshness from the engagement latch.
          self.assertFalse(self.safety.safety_tx_hook(self.command(0)))

  def test_each_source_staleness_and_recovery(self):
    for word in self.WORDS:
      for addr in self.LENGTHS:
        self.init(word)
        self.sources(active=True)
        self.safety.set_timer(300001)
        self.sources(counter=1, active=True, skip=addr)
        self.safety.set_controls_allowed(True)
        if word >= 0xC184:
          self.assertFalse(self.safety.safety_tx_hook(self.buttons(1, 6, 2)))
        else:
          self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
        self.safety.set_timer(350001)
        self.sources(counter=2, active=True)
        self.safety.safety_rx_hook(self.buttons(3))
        self.safety.set_controls_allowed(True)
        if word >= 0xC184:
          self.assertTrue(self.safety.safety_tx_hook(self.buttons(3, 6, 2)))
        else:
          self.assertTrue(self.safety.safety_tx_hook(self.command(0)))

  def test_main_off_and_disabled_never_pedal(self):
    for word in self.WORDS:
      self.init(word)
      self.sources(active=True, main=False)
      self.engage()
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
      self.assertFalse(self.safety.safety_tx_hook(self.buttons(0 if word >= 0xC184 else 1, 6, 2 if word >= 0xC184 else 0)))
      if word >= 0xC184:
        self.init(word)
        self.sources(active=True)
        self.engage()
        self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
        self.assertFalse(self.safety.safety_tx_hook(self.command(0, 0.)))

  def test_digital_brake_driver_gas_sensor_integrity_and_forward_gear(self):
    for word in self.WORDS[:2]:
      for source in ('brake', 'gas', 'crc', 'pair', 'state', 'replay', 'reverse', 'manual'):
        self.init(word)
        self.sources(brake=source == 'brake', gear=2 if source == 'reverse' else 4)
        if source == 'gas':
          self.rx(0x201, self.sensor(1, 900, 450))
        elif source == 'crc':
          self.rx(0x201, self.sensor(1, bad_crc=True))
        elif source == 'pair':
          self.rx(0x201, self.sensor(1, 900, 304))
        elif source == 'state':
          self.rx(0x201, self.sensor(1, state=1))
        elif source == 'replay':
          self.rx(0x201, self.sensor(0))
        elif source == 'manual':
          prndl = bytearray(8)
          prndl[3], prndl[5] = 4, 2
          self.rx(0x1F5, prndl)
        self.engage()
        self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
      self.init(word)
      self.sources()
      self.engage()
      self.rx(0xF1, bytes([0, 255, 0, 0, 0, 0]))
      self.rx(0xBE, bytes([0, 255, 0, 0, 0, 0]))
      self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
      low = bytearray(8)
      low[3] = 6
      self.rx(0x1F5, low)
      self.assertTrue(self.safety.safety_tx_hook(self.command(1)))

  def test_malformed_sensor_cannot_refund_disabled_cancel_and_pedal_packet_masks(self):
    for word in self.WORDS[2:]:
      for replay in (False, True):
        self.init(word)
        self.sources(active=False)
        self.rx(0x201, self.sensor(0 if replay else 1, bad_crc=not replay))
        self.assertFalse(self.safety.safety_tx_hook(self.buttons(0, 6, 2)))
    for word in self.WORDS[:2]:
      self.init(word)
      self.sources()
      self.engage()
      self.assertTrue(self.safety.safety_tx_hook(self.command(0, 1.)))
      msg = create_pedal_command(self.packer, .2, 1)
      for index in range(6):
        changed = bytearray(msg[1])
        changed[index] ^= 1
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x200, 0, changed)))
      changed = bytearray(msg[1])
      changed[4] |= 0x10
      changed[5] = crc(changed)
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x200, 0, changed)))
      changed[4] &= ~0x10
      changed[0], changed[1] = 2634 >> 8, 2634 & 255
      changed[5] = crc(changed)
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x200, 0, changed)))
      self.assertTrue(self.safety.safety_tx_hook(self.command(1, 0.)))

  def test_topology_no_unfed_scheduler_or_unowned_speed_packets(self):
    for word in self.WORDS:
      self.init(word)
      self.sources()
      for addr, length in ((0x315, 5), (0x2CB, 8), (0x2CD, 5), (0x370, 6), (0x3D1, 8), (0xBD, 7),
                           (0x1F5, 8), (0xA1, 7), (0x306, 8), (0x308, 7), (0x310, 2)):
        for bus in range(3):
          self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, bytes(length))))
      for addr in (0x409, 0x40A):
        self.assertEqual(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, 0, bytes(7))), word == 0xC183)
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, 0, bytes([1] + [0] * 6))))
      for bus, addr in ((0, 0x184), (0, 0x3D1), (2, 0x180), (2, 0x370)):
        self.assertEqual(self.safety.safety_fwd_hook(bus, addr), -1)
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x315), 0)
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x2CB), 0)

  def test_reset_removes_cancel_and_pedal_authority(self):
    for word in self.WORDS:
      self.init(word)
      self.sources(active=True)
      self.engage()
      self.init(word)
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
      self.assertFalse(self.safety.safety_tx_hook(self.buttons(0 if word >= 0xC184 else 1, 6, 2 if word >= 0xC184 else 0)))

  def test_aol_does_not_grant_longitudinal_and_stock_only_stays_denied(self):
    for word in self.WORDS:
      self.safety.set_alternative_experience(32)
      self.init(word)
      self.safety.set_aol_test_heartbeat(True)
      self.sources()
      self.safety.aol_set_host_request(1)
      self.assertEqual(self.safety.aol_get_permission_mask(), 1)
      self.assertTrue(self.safety.safety_tx_hook(self.packet(create_steering_control(self.packer, 0, 5, 0, True))))
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
      self.engage()
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
      self.safety.aol_set_host_request(3)
      self.assertEqual(self.safety.safety_tx_hook(self.command(0)), word < 0xC184)

  def test_alternative_zero_has_no_aol_axis_permission(self):
    for word in self.WORDS:
      self.init(word)
      self.safety.set_aol_test_heartbeat(True)
      self.sources()
      self.safety.aol_set_host_request(3)
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)))
