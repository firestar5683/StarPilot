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

  def observations(self, *, speed=0, right=None, acc=4, main=True, brake=False, gas=False, gear=4, analog=True, sensor=True, gear_source=True):
    self.now += 10_000
    self.safety.set_timer(self.now)
    self.rx(0x184, bytes(8))
    self.rx(0x34A, [speed >> 8, speed & 255, (speed if right is None else right) >> 8,
                    (speed if right is None else right) & 255, 0])
    self.rx(0x1E1, bytes(7))
    if analog:
      self.rx(0xF1 if self.word in (0xE101, 0xE103, 0xE111, 0xE113, 0xC171) else 0xBE, bytes(6))
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
    self.safety.safety_tick()

  def engage(self):
    for button in (3, 1):
      frame = self.packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': button})
      self.rx(frame[0], frame[1])

  def gas(self, demand=-500, idx=0, enabled=True):
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
