"""Gateway Volt inactive friction authority from physical CAN observations."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CAR, DBC
from opendbc.car.gm.values import GMSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


class TestVoltAutoHold(unittest.TestCase):
  def init(self, alternate=False, extra=0, alternative=0, word=None, physical_word=None):
    self.safety = libsafety_py.libsafety
    physical_word = word if physical_word is None else physical_word
    self.alternate = alternate or physical_word in (0xC084, 0xC1D3)
    self.safety.set_alternative_experience(alternative)
    word = int(GMSafetyFlags.EV | GMSafetyFlags.VOLT_GATEWAY_LONG | GMSafetyFlags.VOLT_AUTO_HOLD) if word is None else word
    if alternate:
      word |= int(GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE)
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word | extra), 0)
    self.safety.init_tests()
    self.time = 1
    self.counter = 0
    self.packer = CANPacker(DBC[CAR.CHEVROLET_VOLT][Bus.pt])
    physical_word = word if physical_word is None else physical_word
    self.c9_brake = physical_word in (0x4687, 0x4E87, 0x4087, 0x5487, 0xC1D1, 0xC1D3)
    self.tx_bus = 0 if physical_word in (0x4287, 0x4687, 0x4A87, 0x4E87, 0x4087, 0xC1D1, 0xC1D3) or self.alternate else 2

  def tearDown(self):
    libsafety_py.libsafety.set_alternative_experience(0)

  def rx(self, address, data, bus=0):
    return self.safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, bytes(data)))

  def observations(self, *, speed=100, gear=4, main=True, brake=False, gas=False, regen=False, acc=0, manual=False,
                   brake_unavailable=False, status=True, healthy=True, regen_source=True, analog_source=True, c9_brake=None, be_brake=None, be_length=6):
    self.time += 100000
    self.safety.set_timer(self.time)
    c9 = bytearray(8)
    c9[3] = 0x20 if main else 0
    c9[5] = int(brake if c9_brake is None else c9_brake)
    prndl = bytearray(8)
    prndl[3] = gear
    prndl[5] = 2 if manual else 0
    pedal = bytearray(be_length)
    pedal[1] = 10 if (brake if be_brake is None else be_brake) else 0
    engine = bytearray(8)
    engine[1] = acc << 5
    engine[5] = int(gas)
    wheels = [speed >> 8, speed & 255, speed >> 8, speed & 255, 0]
    self.rx(0x184, bytes(8))
    self.rx(0x1E1, bytes(7))
    if status:
      frame = self.packer.make_can_msg('EBCMFrictionBrakeStatus', 0, {'FrictionBrakeUnavailable': int(brake_unavailable)})
      self.assertEqual(frame[1][5] & 0x40, 0x40 if brake_unavailable else 0)
      self.assertTrue(self.rx(frame[0], frame[1]))
    for address, data in ((0xC9, c9), (0x1F5, prndl), (0xF1 if self.alternate else 0xBE, pedal),
                          (0x1C4, engine), (0xBD, [0x10 if regen else 0, 0, 0, 0, 0, 0, 0]), (0x34A, wheels)):
      if address == 0xBD and not regen_source:
        continue
      if address in (0xBE, 0xF1) and not analog_source:
        continue
      self.assertTrue(self.rx(address, data), hex(address))
    self.safety.safety_tick()
    if healthy:
      self.assertTrue(self.safety.safety_config_valid())

  def dwell(self):
    for _ in range(32):
      self.observations()
    self.observations(speed=0)
    self.assertFalse(self.safety.get_controls_allowed())

  def frame(self, brake=100, mode=0xB, *, bus=None, counter=None):
    counter = self.counter if counter is None else counter
    raw = (0x1000 - brake) & 0xFFF
    checksum = (0x10000 - (mode << 12) - raw - counter) & 0xFFFF
    data = bytes([(mode << 4) | (raw >> 8), raw & 255, checksum >> 8, checksum & 255, counter])
    return libsafety_py.make_CANPacket(0x315, self.tx_bus if bus is None else bus, data)

  def tx(self, brake=100, mode=0xB):
    accepted = self.safety.safety_tx_hook(self.frame(brake, mode))
    if accepted:
      self.counter = (self.counter + 1) % 4
    return accepted

  def test_exact_profiles_movement_arming_and_hold_bounds(self):
    for alternate in (False, True):
      with self.subTest(alternate=alternate):
        self.init(alternate)
        self.observations(speed=0, brake=True)
        self.assertFalse(self.tx())
        self.dwell()
        for brake, expected in ((79, False), (80, True), (240, True), (241, False)):
          self.assertEqual(self.tx(brake), expected)
        self.assertFalse(self.safety.get_controls_allowed())
        self.assertFalse(self.safety.safety_tx_hook(self.frame(bus=2 if alternate else 0)))
        self.assertFalse(self.tx(mode=0xD))
        self.observations(speed=0, acc=4)
        self.assertTrue(self.tx(mode=0xD))
        self.assertFalse(self.tx(mode=0xB))

  def test_physical_withdrawal_and_neutral_release(self):
    for changed in ({"main": False}, {"gas": True}, {"gear": 2}, {"regen": True}, {"speed": 20}, {"brake_unavailable": True}):
      for alternate in (False, True):
        with self.subTest(changed=changed, alternate=alternate):
          self.init(alternate)
          self.dwell()
          self.assertTrue(self.tx())
          self.observations(speed=0, **changed) if "speed" not in changed else self.observations(**changed)
          self.assertFalse(self.tx())
          self.assertTrue(self.tx(0, 1))
    self.init()
    self.dwell()
    self.safety.set_timer(self.time + 300001)
    self.assertFalse(self.tx())
    self.assertTrue(self.tx(0, 1))
    self.safety.set_timer(self.time + 1000001)
    self.safety.safety_tick()
    self.assertFalse(self.safety.safety_config_valid())
    self.assertFalse(self.tx())
    self.assertTrue(self.tx(0, 1))

  def test_regen_cooldown_forward_manumatic_and_counter_integrity(self):
    self.init()
    self.dwell()
    self.observations(speed=0, regen=True)
    self.observations(speed=0, brake=True, regen=False)
    self.assertFalse(self.tx())
    for _ in range(10):
      self.observations(speed=0, brake=True, gear=6, manual=True)
    self.assertTrue(self.tx())
    self.assertFalse(self.safety.safety_tx_hook(self.frame(counter=0)))
    bad = self.frame()
    bad.data[2] ^= 1
    self.assertFalse(self.safety.safety_tx_hook(bad))
    # An expired cooldown cannot revive when the native 32-bit timer wraps.
    self.time = 0xFFFFFF00 - 100000
    self.observations(speed=0, brake=True, gear=6, manual=True)
    self.assertTrue(self.tx())
    self.time = 0
    self.observations(speed=0, brake=True, gear=6, manual=True)
    self.assertTrue(self.tx())

  def test_unqualified_word_and_missing_sources_cannot_hold(self):
    self.init()
    self.assertFalse(self.tx())
    self.init(extra=int(GMSafetyFlags.HW_CAM))
    self.assertFalse(self.tx())

  def test_moving_dwell_quantization_and_known_forward_gears(self):
    for gear, manual, accepted in ((4, False, True), (6, False, True), (5, True, True), (7, True, True),
                                   (5, False, False), (7, False, False), (8, True, False), (13, True, False), (2, True, False)):
      with self.subTest(gear=gear, manual=manual):
        self.init()
        for _ in range(32):
          self.observations(speed=11, gear=gear, manual=manual)
        self.observations(speed=0, gear=gear, manual=manual, brake=True)
        self.assertFalse(self.tx())
        for _ in range(32):
          self.observations(speed=12, gear=gear, manual=manual)
        self.observations(speed=0, gear=gear, manual=manual, brake=True)
        self.assertEqual(self.tx(), accepted)

  def test_ordinary_longitudinal_authority_from_real_buttons_is_unchanged(self):
    for alternate in (False, True):
      self.init(alternate)
      self.observations()
      resume = bytearray(7)
      resume[5] = 0x20
      self.assertTrue(self.rx(0x1E1, resume))
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertTrue(self.tx(400, 0xA))
      self.assertFalse(self.tx(401, 0xA))
      self.observations(brake=True)
      self.assertFalse(self.safety.get_controls_allowed())
      self.assertFalse(self.tx(100, 0xA))
      self.assertTrue(self.tx(0, 1))

  def test_exact_hold_profiles_retain_aol_lateral_without_long_authority(self):
    for alternate in (False, True):
      for alternative in (0, 32):
        with self.subTest(alternate=alternate, alternative=alternative):
          self.init(alternate, alternative=alternative)
          self.dwell()
          self.safety.set_aol_test_heartbeat(True)
          self.safety.aol_set_host_request(1)
          self.assertEqual(self.safety.aol_get_permission_mask(), 1 if alternative == 32 else 0)
          # Actual nonzero lateral request, with a correct GM steering checksum.
          frame = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
          steering = libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])
          self.assertEqual(self.safety.safety_tx_hook(steering), alternative == 32)
          self.assertTrue(self.tx())
          self.assertFalse(self.safety.get_controls_allowed())

  def test_brake_status_freshness_is_independent_of_other_live_sources(self):
    for alternate in (False, True):
      self.init(alternate)
      self.dwell()
      self.assertTrue(self.tx())
      for _ in range(4):
        self.observations(speed=0, status=False)
      self.assertFalse(self.tx())
      self.assertTrue(self.tx(0, 1))
