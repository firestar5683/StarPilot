"""Independent camera-removed Volt authority and physical cancellation slots."""
import unittest
from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CAR, DBC
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


class TestGmVoltCameraRemoved(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    self.packer = CANPacker(DBC[CAR.CHEVROLET_VOLT_CAMERA][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, word):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def rx(self, name, values=None, bus=0):
    return self.safety.safety_rx_hook(self.packet(self.packer.make_can_msg(name, bus, values or {})))

  def physical(self, counter=0, active=True):
    self.rx('ECMEngineStatus', {'CruiseMainOn': 1})
    self.rx('AcceleratorPedal2', {'CruiseState': 2 if active else 0})
    self.safety.safety_rx_hook(self.packet(gmcan.create_buttons(self.packer, 0, counter, 1)))

  def test_exact_alpha_limits_and_no_extra_authority(self):
    self.mode(0xC151)
    self.safety.set_controls_allowed(True)
    for gas, allowed in ((-540.125, False), (-540., True), (2698., True), (2698.125, False)):
      frame = gmcan.create_gas_regen_command(self.packer, 0, gas, 1, True, False)
      self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), allowed and not self.release)
    for address, length, bus in ((0x2CD, 5, 0), (0x3D1, 8, 0), (0x200, 6, 0), (0x315, 5, 2),
                                (0x1E1, 7, 0), (0xA1, 7, 1), (0x306, 8, 1), (0x308, 7, 1), (0x310, 2, 1)):
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, bytes(length))))
    for frame in gmcan.create_adas_keepalive(0):
      self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), not self.release)
      self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 2))))
    self.safety.set_controls_allowed(False)
    frame = gmcan.create_gas_regen_command(self.packer, 0, -500., 1, False, False)
    self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), not self.release)

  def test_stock_cancel_requires_fresh_physical_slot_and_exact_shape(self):
    self.mode(0xC150)
    self.physical()
    cancel = gmcan.create_buttons(self.packer, 0, 0, 6)
    self.assertTrue(self.safety.safety_tx_hook(self.packet(cancel)))
    self.assertFalse(self.safety.safety_tx_hook(self.packet(cancel)))
    self.physical()
    self.assertFalse(self.safety.safety_tx_hook(self.packet(cancel)))
    self.safety.set_timer(1_040_001)
    self.physical(1)
    cancel = gmcan.create_buttons(self.packer, 0, 1, 6)
    for button in (2, 3):
      self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_buttons(self.packer, 0, 1, button))))
    self.assertFalse(self.safety.safety_tx_hook(self.packet((cancel[0], cancel[1], 2))))
    mutated = bytearray(cancel[1])
    mutated[0] = 1
    self.assertFalse(self.safety.safety_tx_hook(self.packet((cancel[0], bytes(mutated), 0))))
    self.assertTrue(self.safety.safety_tx_hook(self.packet(cancel)))
    self.safety.set_timer(1_080_002)
    self.physical(2)
    self.safety.set_timer(1_180_003)
    self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_buttons(self.packer, 0, 2, 6))))

  def test_driver_gas_brake_regen_and_required_health(self):
    for word in (0xC150, 0xC151):
      self.mode(word)
      for name in ('PSCMStatus', 'EBCMWheelSpdRear', 'ECMEngineStatus', 'AcceleratorPedal2', 'ASCMSteeringButton', 'EBCMRegenPaddle'):
        self.rx(name)
      self.safety.safety_tick()
      if word == 0xC151 and self.release:
        self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_steering_control(self.packer, 0, 1, 0, True))))
        continue
      self.assertTrue(self.safety.safety_config_valid())
      self.safety.set_controls_allowed(True)
      self.rx('AcceleratorPedal2', {'AcceleratorPedal2': 10, 'CruiseState': 2})
      self.assertTrue(self.safety.get_controls_allowed())
      self.rx('ECMEngineStatus', {'BrakePressed': 1})
      self.assertFalse(self.safety.get_controls_allowed())
      self.safety.set_controls_allowed(True)
      self.rx('EBCMRegenPaddle', {'RegenPaddle': 1})
      self.assertFalse(self.safety.get_controls_allowed())
      self.safety.set_timer(3_000_000)
      self.safety.safety_tick()
      self.assertFalse(self.safety.safety_config_valid())

  def test_neutral_gap_recovers_without_reusing_cancel_slot(self):
    self.mode(0xC150)
    for stamp, counter in ((1_000_000, 0), (1_150_000, 1), (1_180_000, 2), (1_185_000, 2)):
      self.safety.set_timer(stamp)
      self.physical(counter)
      cancel = self.packet(gmcan.create_buttons(self.packer, 0, counter, 6))
      self.assertEqual(bool(self.safety.safety_tx_hook(cancel)), stamp in (1_000_000, 1_180_000))
      self.assertFalse(self.safety.safety_tx_hook(cancel))

  def test_forwarding_and_reinitialization_clear_cancel_credit(self):
    for word in (0xC150, 0xC151):
      self.mode(word)
      if word == 0xC151 and self.release:
        continue
      self.assertEqual(self.safety.safety_fwd_hook(0, 0x184), -1)
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x180), -1)
      for address in (0x315, 0x2CB, 0x370, 0x2CD):
        self.assertEqual(self.safety.safety_fwd_hook(2, address), -1 if word == 0xC151 else 0)
    self.mode(0xC150)
    self.physical()
    for middle in (5, 0x4007, 0x1005, 4):
      self.mode(middle)
      self.mode(0xC150)
      self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_buttons(self.packer, 0, 0, 6))))

  def test_neutral_checksum_cadence_and_timer_wrap(self):
    self.mode(0xC150)
    self.rx('ECMEngineStatus', {'CruiseMainOn': 1})
    self.rx('AcceleratorPedal2', {'CruiseState': 2})
    neutral = gmcan.create_buttons(self.packer, 0, 0, 1)
    bad = bytearray(neutral[1])
    bad[6] ^= 1
    self.safety.safety_rx_hook(self.packet((neutral[0], bytes(bad), 0)))
    cancel = gmcan.create_buttons(self.packer, 0, 0, 6)
    self.assertFalse(self.safety.safety_tx_hook(self.packet(cancel)))
    self.mode(0xC150)
    self.safety.set_timer(0xFFFFFFF0)
    self.physical()
    self.safety.set_timer(40000)
    self.assertTrue(self.safety.safety_tx_hook(self.packet(cancel)))
    self.safety.set_timer(70000)
    self.physical(1)
    cancel = gmcan.create_buttons(self.packer, 0, 1, 6)
    self.assertFalse(self.safety.safety_tx_hook(self.packet(cancel)))
    self.safety.set_timer(80001)
    self.assertTrue(self.safety.safety_tx_hook(self.packet(cancel)))
