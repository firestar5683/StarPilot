"""Camera ACC paired-interceptor physical ownership and neutral handoff."""
import unittest
from types import SimpleNamespace

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CAR, DBC
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


class TestGmCameraAccPedal(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    self.packer = CANPacker(DBC[CAR.CHEVROLET_SILVERADO][Bus.pt])
    self.cp = SimpleNamespace(carFingerprint=CAR.CHEVROLET_SILVERADO)

  def init(self, word):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word), 0)
    self.safety.init_tests()
    self.word = word
    self.now = 1
    self.sensor_counter = 0
    self.safety.set_timer(self.now)

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def rx(self, addr, data):
    return self.safety.safety_rx_hook(libsafety_py.make_CANPacket(addr, 0, bytes(data)))

  def observations(self, *, speed=0, right=None, acc=4, main=True, brake=False, gas=False, gear=4, analog=True, sensor=True, gear_source=True,
                   regen=False, regen_source=True, friction_source=True):
    self.now += 10_000
    self.safety.set_timer(self.now)
    self.rx(0x184, bytes(8))
    self.rx(0x34A, [speed >> 8, speed & 255, (speed if right is None else right) >> 8,
                    (speed if right is None else right) & 255, 0])
    self.rx(0x1E1, bytes(7))
    if analog:
      alternate = self.word in (0xE101, 0xE103, 0xE111, 0xE113,
                                0xE301, 0xE303, 0xE311, 0xE313, 0xE321, 0xE323, 0xE341, 0xE343, 0xE361, 0xE363,
                                0xC171, 0xE201, 0xE203, 0xE211, 0xE213, 0xE221, 0xE223, 0xE241, 0xE243, 0xE261, 0xE263)
      gateway_f1 = self.word in (0xE301, 0xE303, 0xE321, 0xE323, 0xE341, 0xE343, 0xE361, 0xE363)
      self.rx(0xF1 if alternate else 0xBE, bytes([0, 6 if brake and gateway_f1 else 0]) + bytes(4))
    engine = bytearray(8)
    engine[1] = acc << 5
    engine[5] = int(gas)
    self.rx(0x1C4, engine)
    c9 = bytearray(8)
    c9[3] = 0x20 if main else 0
    c9[5] = int(brake)
    self.rx(0xC9, c9)
    if sensor:
      data = bytearray([2, 92, 1, 48, self.sensor_counter & 15, 0])
      data[5] = gmcan.pedal_crc(data)
      self.sensor_counter += 1
      self.rx(0x201, data)
    prndl = bytearray(8)
    prndl[3] = gear
    if gear_source:
      self.rx(0x1F5, prndl)
    if regen_source:
      self.rx(0xBD, [0x10 if regen else 0, 0, 0, 0, 0, 0, 0])
    if friction_source:
      self.rx(0x232, bytes(8))
    self.safety.safety_tick()

  def engage(self):
    for button in (3, 1):
      frame = self.packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': button})
      self.rx(frame[0], frame[1])

  def gas(self, demand=None, idx=0, enabled=True):
    if demand is None:
      demand = -650 if self.word in tuple(base + i for base in (0xE300, 0xE310, 0xE320, 0xE340, 0xE360) for i in range(4)) else -500
    return self.packet(gmcan.create_gas_regen_command(self.packer, 0, demand, idx, enabled, False))

  def brake(self, demand=0, idx=0):
    return self.packet(gmcan.create_friction_brake_command(self.packer, 0, demand, idx, True, False, False, self.cp))

  def pedal(self, fraction=18 / 255, idx=0):
    return self.packet(gmcan.create_pedal_command(self.packer, fraction, idx))

  def neutral_pair(self, idx=0):
    self.assertTrue(self.safety.safety_tx_hook(self.gas(idx=idx)))
    self.assertTrue(self.safety.safety_tx_hook(self.brake(idx=idx)))

  def ready(self, word):
    self.init(word)
    self.observations()
    self.engage()

  def test_volt_gateway_exact_compositions_and_neutral_codec(self):
    words = tuple(base + i for base in (0xE300, 0xE320, 0xE340, 0xE360) for i in range(4))
    for word in words:
      self.init(word)
      if self.release:
        self.observations()
        self.engage()
        self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
        continue
      self.ready(word)
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertTrue(self.safety.safety_tx_hook(self.gas(-500)))
      self.assertTrue(self.safety.safety_tx_hook(self.brake()))
      self.assertFalse(self.safety.safety_tx_hook(self.pedal(.16)))
      self.neutral_pair()
      self.assertTrue(self.safety.safety_tx_hook(self.pedal(.16)))
      self.assertFalse(self.safety.safety_tx_hook(self.brake(100, idx=1)))
      self.assertTrue(self.safety.safety_tx_hook(self.pedal(0, idx=1)))
      self.assertTrue(self.safety.safety_tx_hook(self.gas(100, idx=1)))
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x315, 2, bytes(5))))
    for word in (0xE304, 0xE314, 0xE324, 0xE344, 0xE364):
      self.ready(word)
      self.assertFalse(self.safety.safety_tx_hook(self.pedal()))

  def test_volt_gateway_selected_physical_brake_owner(self):
    if self.release:
      self.skipTest("Active Volt interceptor profiles are DEBUG-only")
    self.ready(0xE300)
    # BE travel does not replace the reached camera-forwarded C9 pressed signal.
    self.rx(0xBE, bytes([0, 8]) + bytes(4))
    self.assertFalse(self.safety.get_brake_pressed_prev())
    self.observations(brake=True)
    self.assertTrue(self.safety.get_brake_pressed_prev())
    self.ready(0xE301)
    self.observations()
    self.rx(0xC9, bytes([0, 0, 0, 32, 0, 1, 0, 0]))
    self.assertFalse(self.safety.get_brake_pressed_prev())
    self.rx(0xF1, bytes([0, 5]) + bytes(4))
    self.assertFalse(self.safety.get_brake_pressed_prev())
    self.rx(0xF1, bytes([0, 6]) + bytes(4))
    self.assertTrue(self.safety.get_brake_pressed_prev())

  def test_volt_gateway_gear_cadence_and_expiry(self):
    if self.release:
      self.skipTest("Active Volt interceptor profiles are DEBUG-only")
    for word in (0xE300, 0xE301, 0xE302, 0xE303):
      self.ready(word)
      for tick in range(220):
        self.observations(gear_source=tick % 11 == 0)
        self.assertTrue(self.safety.safety_config_valid())
        self.assertTrue(self.safety.safety_tx_hook(self.gas(100)))
      self.observations(gear_source=True)
      for _ in range(100):
        self.observations(gear_source=False)
      self.assertTrue(self.safety.safety_tx_hook(self.gas(100)))
      self.observations(gear_source=False)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(100)))
      self.observations(gear_source=True)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(100)))
      self.engage()
      self.assertTrue(self.safety.safety_tx_hook(self.gas(100)))

  def test_volt_gateway_stock_no_pedal_or_gear_authority(self):
    for word in (0xE310, 0xE311, 0xE312, 0xE313):
      self.init(word)
      self.observations(sensor=False, gear_source=False)
      self.engage()
      self.assertTrue(self.safety.safety_config_valid())
      for frame in (self.pedal(), self.gas(), self.brake(100)):
        self.assertFalse(self.safety.safety_tx_hook(frame))

  def test_volt_gateway_stock_cancel_physical_credit(self):
    for word in (0xE310, 0xE311, 0xE312, 0xE313):
      self.init(word)
      self.observations(sensor=False, gear_source=False)
      neutral = gmcan.create_buttons(self.packer, 0, 1, 1)
      cancel = self.packet(gmcan.create_buttons(self.packer, 2, 1, 6))
      self.assertFalse(self.safety.safety_tx_hook(cancel))
      self.assertTrue(self.rx(neutral[0], neutral[1]))
      for button in (1, 2, 3, 4, 5):
        self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_buttons(self.packer, 2, 1, button))))
      self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_buttons(self.packer, 0, 1, 6))))
      self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_buttons(self.packer, 2, 2, 6))))
      self.assertTrue(self.safety.safety_tx_hook(cancel))
      self.assertFalse(self.safety.safety_tx_hook(cancel))
      self.assertTrue(self.rx(neutral[0], neutral[1]))
      self.assertFalse(self.safety.safety_tx_hook(cancel))
      self.now += 50000
      self.safety.set_timer(self.now)
      next_neutral = gmcan.create_buttons(self.packer, 0, 2, 1)
      self.assertTrue(self.rx(next_neutral[0], next_neutral[1]))
      next_cancel = self.packet(gmcan.create_buttons(self.packer, 2, 2, 6))
      self.assertTrue(self.safety.safety_tx_hook(next_cancel))
      for changes in ({'main': False}, {'acc': 0}):
        self.init(word)
        self.observations(sensor=False, gear_source=False, **changes)
        self.assertTrue(self.rx(neutral[0], neutral[1]))
        self.assertFalse(self.safety.safety_tx_hook(cancel))
      self.init(word)
      self.observations(sensor=False, gear_source=False)
      self.assertTrue(self.rx(neutral[0], neutral[1]))
      self.safety.set_timer(self.now + 100001)
      self.assertFalse(self.safety.safety_tx_hook(cancel))

  def test_volt_interceptor_gas_withdraws_inactive_hold_and_rearm_credit(self):
    if self.release:
      self.skipTest("Active Volt interceptor profiles are DEBUG-only")
    for word in (0xE220, 0xE221, 0xE222, 0xE223, 0xE260, 0xE261, 0xE262, 0xE263,
                 0xE320, 0xE321, 0xE322, 0xE323, 0xE360, 0xE361, 0xE362, 0xE363):
      for fault in ('gas', 'adc', 'stale'):
        self.init(word)
        for _ in range(320):
          self.observations(speed=100)
        self.observations(speed=0, brake=True)
        self.assertFalse(self.safety.get_controls_allowed())
        brake = 100
        raw = 0x1000 - brake
        checksum = (0x10000 - (0xD << 12) - raw) & 0xFFFF
        hold = libsafety_py.make_CANPacket(0x315, 0, bytes([0xD0 | (raw >> 8), raw & 255, checksum >> 8, checksum & 255, 0]))
        self.assertTrue(self.safety.safety_tx_hook(hold))
        checksum = (0x10000 - (0xD << 12) - raw - 1) & 0xFFFF
        hold = libsafety_py.make_CANPacket(0x315, 0, bytes([0xD0 | (raw >> 8), raw & 255, checksum >> 8, checksum & 255, 1]))
        data = bytearray.fromhex('053502ba0164' if fault == 'gas' else '0279012a06f6')
        if fault == 'adc':
          data[:2] = (4096).to_bytes(2, 'big')
        data[4] = self.sensor_counter & 15
        data[5] = gmcan.pedal_crc(data)
        self.sensor_counter += 1
        self.rx(0x201, data)
        if fault == 'stale':
          self.now += 100001
          self.safety.set_timer(self.now)
        self.assertFalse(self.safety.safety_tx_hook(hold))
        self.observations(speed=0, brake=False)
        self.assertFalse(self.safety.safety_tx_hook(hold))

  def test_volt_camera_exact_compositions_and_maneuver_bounds(self):
    active = (0xE200, 0xE201, 0xE202, 0xE203, 0xE220, 0xE221, 0xE222, 0xE223,
              0xE240, 0xE241, 0xE242, 0xE243, 0xE260, 0xE261, 0xE262, 0xE263)
    for word in active:
      with self.subTest(word=hex(word)):
        self.ready(word)
        if self.release:
          self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
          self.assertFalse(self.safety.safety_tx_hook(self.pedal(.16)))
          continue
        self.assertTrue(self.safety.safety_config_valid())
        self.observations(speed=231)
        self.neutral_pair()
        self.assertFalse(self.safety.safety_tx_hook(self.pedal(.161)))
        self.assertTrue(self.safety.safety_tx_hook(self.pedal(.16)))
        self.assertTrue(self.safety.safety_tx_hook(self.pedal(0, 1)))
        self.observations(speed=232)
        self.neutral_pair(2)
        self.assertFalse(self.safety.safety_tx_hook(self.pedal(.16, 2)))
        self.observations(speed=0, regen=True)
        self.assertFalse(self.safety.safety_tx_hook(self.pedal(idx=2)))
    for word in (0xE210, 0xE211, 0xE212, 0xE213):
      self.init(word)
      self.observations(sensor=False, gear_source=False)
      self.assertTrue(self.safety.safety_config_valid())
      self.assertFalse(self.safety.safety_tx_hook(self.pedal(.16)))
      self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
    for word in (0xE204, 0xE214, 0xE224, 0xE244, 0xE264, 0xE2FF):
      self.ready(word)
      self.assertFalse(self.safety.safety_tx_hook(self.pedal(.16)))
      self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))

  def test_exact_profiles_and_stock_without_pedal_or_gear(self):
    for word in (0xE110, 0xE111, 0xE112, 0xE113):
      self.init(word)
      self.observations(sensor=False, gear_source=False)
      self.assertTrue(self.safety.safety_config_valid())
      self.assertTrue(self.safety.get_controls_allowed())
      steer = self.packer.make_can_msg('ASCMLKASteeringCmd', 0, {'LKASteeringCmd': 1, 'LKASteeringCmdActive': 1})
      self.assertTrue(self.safety.safety_tx_hook(self.packet(steer)))
      self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
      self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
    for word in (0xE100, 0xE101, 0xE102, 0xE103):
      self.ready(word)
      if self.release:
        self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
        self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
      else:
        self.assertTrue(self.safety.safety_config_valid())
        self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
        self.neutral_pair()
        self.assertTrue(self.safety.safety_tx_hook(self.pedal()))

  def test_launch_requires_neutral_counter_epoch_and_no_overlap(self):
    if self.release:
      self.skipTest("Active camera interceptor profiles are DEBUG-only")
    self.ready(0xE100)
    self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
    self.assertTrue(self.safety.safety_tx_hook(self.gas()))
    self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
    self.assertTrue(self.safety.safety_tx_hook(self.brake()))
    self.assertFalse(self.safety.safety_tx_hook(self.pedal(idx=1)))
    self.assertTrue(self.safety.safety_tx_hook(self.pedal()))
    self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
    self.assertFalse(self.safety.safety_tx_hook(self.brake(1)))
    self.assertTrue(self.safety.safety_tx_hook(self.pedal(0, 1)))
    self.assertTrue(self.safety.safety_tx_hook(self.gas(2698, 1)))
    self.assertFalse(self.safety.safety_tx_hook(self.gas(2699, 1)))
    self.assertTrue(self.safety.safety_tx_hook(self.brake(400, 1)))
    self.assertFalse(self.safety.safety_tx_hook(self.brake(401, 1)))

  def test_physical_nearzero_and_driver_withdrawal(self):
    if self.release:
      self.skipTest("Active camera interceptor profiles are DEBUG-only")
    for changes in ({'speed': 34}, {'speed': 35}, {'speed': 0, 'right': 35}, {'acc': 0}, {'acc': 1}, {'acc': 3},
                    {'main': False}, {'brake': True}, {'gas': True}, {'gear': 2}):
      self.ready(0xE101)
      self.observations(**changes)
      # Neutral releases remain legal even if driver/state admission withdraws.
      self.assertTrue(self.safety.safety_tx_hook(self.gas(enabled=self.safety.get_controls_allowed())))
      self.assertTrue(self.safety.safety_tx_hook(self.brake()))
      allowed = changes == {'speed': 34}
      self.assertEqual(self.safety.safety_tx_hook(self.pedal()), allowed)

  def test_stale_pair_and_selected_analog_deny_all_demands(self):
    if self.release:
      self.skipTest("Active camera interceptor profiles are DEBUG-only")
    for word in (0xE100, 0xE101):
      for missing in ('sensor', 'analog'):
        self.ready(word)
        for _ in range(32):
          self.observations(**{missing: False})
          if missing == 'analog':
            self.rx(0xBE if word == 0xE101 else 0xF1, bytes(6))
        self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
        self.assertFalse(self.safety.safety_tx_hook(self.brake(1)))
        self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
        self.assertTrue(self.safety.safety_tx_hook(self.gas(enabled=False)))
        self.assertTrue(self.safety.safety_tx_hook(self.brake()))

  def test_credit_expiry_invalid_shapes_and_timer_wrap(self):
    if self.release:
      self.skipTest("Active camera interceptor profiles are DEBUG-only")
    self.ready(0xE100)
    self.neutral_pair()
    for _ in range(9):
      self.observations()
    self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
    bad = bytearray(gmcan.create_gas_regen_command(self.packer, 0, -500, 0, True, False)[1])
    bad[7] ^= 1
    self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x2CB, 0, bad)))
    self.assertTrue(self.safety.safety_tx_hook(self.brake()))
    self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
    self.now = 0xFFFF0000
    self.observations()
    self.neutral_pair()
    self.now = (self.now + 100_000) & 0xFFFFFFFF
    self.observations()
    self.assertFalse(self.safety.safety_tx_hook(self.pedal()))

  def test_counter_three_to_zero_and_unknown_neighbors(self):
    if not self.release:
      self.ready(0xE102)
      for idx in (3, 0, 1):
        self.neutral_pair(idx)
        self.assertTrue(self.safety.safety_tx_hook(self.pedal(idx=idx)))
      self.neutral_pair(0)
      self.assertFalse(self.safety.safety_tx_hook(self.pedal(idx=0)))
      self.assertFalse(self.safety.safety_tx_hook(self.pedal(idx=4)))
    for word in (0xE0FF, 0xE104, 0xE10F, 0xE114, 0xE11F):
      self.ready(word)
      self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
      self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))

  def test_profile_reset_does_not_require_active_tails_in_stock(self):
    for word in (0xE102, 0xE110, 0xE103, 0xE113, 0xC171):
      self.init(word)
      self.observations(sensor=False, gear_source=False)
      if word not in (0xE102, 0xE103):
        # Stock/profile baseline excludes sensor and gear health from RX admission.
        self.assertTrue(self.safety.safety_config_valid())
      self.assertFalse(self.safety.safety_tx_hook(self.pedal()))

  def test_extended_rx_storage_resets_across_camera_hold_and_stock(self):
    if self.release:
      self.skipTest("Active camera interceptor profiles are DEBUG-only")
    from opendbc.safety.tests.test_gm_volt_auto_hold import TestVoltAutoHold

    for camera in (0xE100, 0xE101, 0xE102, 0xE103):
      self.ready(camera)
      self.assertTrue(self.safety.safety_config_valid())
      hold = TestVoltAutoHold()
      hold.init(word=0x4287)
      for _ in range(32):
        hold.observations(be_length=8)
      self.assertTrue(self.safety.safety_config_valid())
      hold.init(word=0x4084)
      hold.observations(analog_source=False, healthy=False)
      self.assertFalse(self.safety.safety_config_valid())
      hold.observations()
      self.assertTrue(self.safety.safety_config_valid())
      self.init(camera)
      self.observations(sensor=False, gear_source=False)
      self.assertFalse(self.safety.safety_config_valid())
      self.observations()
      self.assertTrue(self.safety.safety_config_valid())
      self.init(0xE110 if camera in (0xE100, 0xE102) else 0xE111)
      self.observations(sensor=False, gear_source=False)
      self.assertTrue(self.safety.safety_config_valid())
      self.init(0xC171)
      self.observations(sensor=False, gear_source=False)
      self.assertTrue(self.safety.safety_config_valid())

  def test_physical_adc_samples_preserve_engagement_and_driver_gas_withdrawal(self):
    if self.release:
      self.skipTest("Active camera interceptor profiles are DEBUG-only")
    samples = ('053502ba0164', '04e30286048f', '046c024108e3', '0279012a06f6')
    for word in (0xE100, 0xE101, 0xE102, 0xE103):
      for sample in samples:
        with self.subTest(word=hex(word), sample=sample):
          self.init(word)
          self.observations(sensor=False)
          data = bytes.fromhex(sample)
          self.assertEqual(gmcan.pedal_crc(data), data[5])
          self.assertTrue(self.rx(0x201, data))
          self.safety.safety_tick()
          self.engage()
          self.assertTrue(self.safety.get_controls_allowed())
          steering = gmcan.create_steering_control(self.packer, 0, 0, 0, True)
          self.assertTrue(self.safety.safety_tx_hook(self.packet(steering)))
          driver_gas = int.from_bytes(data[:2], 'big') + int.from_bytes(data[2:4], 'big') > 1190
          if driver_gas:
            self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
            self.assertFalse(self.safety.safety_tx_hook(self.brake(1)))
            self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
          else:
            self.neutral_pair()
            self.assertTrue(self.safety.safety_tx_hook(self.pedal()))

  def test_adc_fault_crc_and_pedal_ceiling(self):
    if self.release:
      self.skipTest("Active camera interceptor profiles are DEBUG-only")
    for fault in ('crc', 'state', 'adc1', 'adc2', 'repeat'):
      self.ready(0xE100)
      data = bytearray([2, 92, 1, 48, self.sensor_counter & 15, 0])
      if fault == 'state':
        data[4] |= 0x10
      if fault == 'adc1':
        data[0:2] = (4096).to_bytes(2, 'big')
      if fault == 'adc2':
        data[2:4] = (4096).to_bytes(2, 'big')
      if fault == 'repeat':
        data[4] = (self.sensor_counter - 1) & 15
      data[5] = gmcan.pedal_crc(data)
      if fault == 'crc':
        data[5] ^= 1
      self.rx(0x201, data)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
      self.assertFalse(self.safety.safety_tx_hook(self.brake(1)))
      self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
    self.ready(0xE100)
    self.neutral_pair()
    self.assertFalse(self.safety.safety_tx_hook(self.pedal(19 / 255)))
    self.assertTrue(self.safety.safety_tx_hook(self.pedal(18 / 255)))

  def test_positive_acc_invalidates_neutral_credit(self):
    if self.release:
      self.skipTest("Active camera interceptor profiles are DEBUG-only")
    self.ready(0xE103)
    self.neutral_pair()
    self.assertTrue(self.safety.safety_tx_hook(self.gas(1)))
    self.assertFalse(self.safety.safety_tx_hook(self.pedal()))
    self.neutral_pair()
    self.assertTrue(self.safety.safety_tx_hook(self.pedal()))
    self.observations(main=False)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
    self.assertFalse(self.safety.safety_tx_hook(self.brake(1)))
    self.assertFalse(self.safety.safety_tx_hook(self.pedal(idx=1)))
    self.assertTrue(self.safety.safety_tx_hook(self.pedal(0, 1)))
