"""Exact manual Volt camera alpha authority; neighboring profiles stay isolated."""
import unittest
from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CAR, DBC
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py

EXACT = 0x4007


class TestGmVoltCamera(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    self.packer = CANPacker(DBC[CAR.CHEVROLET_VOLT_CAMERA][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, word=EXACT):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def rx(self, name, values=None, bus=0):
    return self.safety.safety_rx_hook(self.packet(self.packer.make_can_msg(name, bus, values or {})))

  def gas(self, value, enabled=True, bus=0):
    return self.packet(gmcan.create_gas_regen_command(self.packer, bus, value, 1, enabled, False))

  def test_exact_limits_and_unowned_transmit(self):
    self.mode()
    self.safety.set_controls_allowed(True)
    for gas, allowed in ((-540.125, False), (-540., True), (2698., True), (2698.125, False)):
      self.assertEqual(self.safety.safety_tx_hook(self.gas(gas)), allowed and not self.release)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(0., bus=2)))
    for active in (False, True):
      dashboard = self.packer.make_can_msg('ASCMActiveCruiseControlStatus', 0,
                                          {'ACCCruiseState': 2, 'ACCCmdActive': active, 'FCWAlert': 2})
      self.assertEqual(self.safety.safety_tx_hook(self.packet(dashboard)), not self.release)
      self.assertFalse(self.safety.safety_tx_hook(self.packet((dashboard[0], dashboard[1], 2))))
      self.assertFalse(self.safety.safety_tx_hook(self.packet((dashboard[0], dashboard[1][:-1], 0))))
    for brake, allowed in ((0, True), (400, True), (401, False)):
      frame = self.packer.make_can_msg('EBCMFrictionBrakeCmd', 0, {'FrictionBrakeCmd': -brake})
      self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), allowed and not self.release)
      self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 2))))
    frame = self.packer.make_can_msg('ASCMLKASteeringCmd', 0, {'LKASteeringCmd': 1, 'LKASteeringCmdActive': 1})
    self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), not self.release)
    self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1][:-1], 0))))
    for addr, length, bus in ((0x200, 6, 0), (0xBD, 7, 0), (0x1F5, 8, 0), (0x3D1, 8, 0),
                              (0xA1, 7, 1), (0x306, 8, 1), (0x308, 7, 1), (0x310, 2, 1)):
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, bytes(length))))
    self.safety.set_controls_allowed(False)
    self.assertEqual(self.safety.safety_tx_hook(self.gas(-500., enabled=False)), not self.release)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))

  def test_driver_button_brake_gas_regen_and_timeout(self):
    self.mode()
    for name in ('PSCMStatus', 'EBCMWheelSpdRear', 'ECMAcceleratorPos', 'ECMEngineStatus', 'AcceleratorPedal2', 'EBCMRegenPaddle'):
      self.assertTrue(self.rx(name))
    for button in (3, 1):
      self.rx('ASCMSteeringButton', {'ACCButtons': button})
    self.safety.safety_tick()
    self.assertTrue(self.safety.safety_config_valid())
    self.assertEqual(self.safety.get_controls_allowed(), not self.release)
    for name, values in (('ECMEngineStatus', {'BrakePressed': 1}), ('EBCMRegenPaddle', {'RegenPaddle': 2})):
      self.safety.set_controls_allowed(True)
      self.rx(name, values)
      self.assertFalse(self.safety.get_controls_allowed())
      self.rx(name)
      self.assertFalse(self.safety.get_controls_allowed())
    self.safety.set_controls_allowed(True)
    self.rx('AcceleratorPedal2', {'AcceleratorPedal2': 1})
    self.assertEqual(self.safety.get_controls_allowed(), not self.release)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))
    self.safety.set_timer(2_100_000)
    self.safety.safety_tick()
    self.assertFalse(self.safety.safety_config_valid())

  def test_forwarding_and_relay(self):
    self.mode()
    for source, blocked in ((0, (0x184,)), (2, (0x180, 0x315, 0x2CB, 0x370, 0x2CD))):
      for addr in blocked:
        self.assertEqual(self.safety.safety_fwd_hook(source, addr),
                         0 if self.release and source == 2 and addr != 0x180 else -1)
    self.assertEqual(self.safety.safety_fwd_hook(0, 0x460), 2)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x3D1), 0)
    self.safety.set_relay_malfunction(True)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(-500., enabled=False)))

  def test_exact_sdgm_neighbor_has_its_own_longitudinal_owner(self):
    self.mode(0x5007)
    self.safety.set_controls_allowed(True)
    self.assertEqual(self.safety.safety_tx_hook(self.gas(2041.)), not self.release)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(2041.125)))
    self.assertFalse(self.safety.safety_tx_hook(self.gas(2698.)))
    self.assertFalse(self.safety.safety_tx_hook(self.gas(2041., bus=2)))

  def test_extra_bits_do_not_inherit_camera_owner(self):
    for bit in (0x8, 0x10, 0x20, 0x200, 0x400, 0x800, 0x2000, 0x8000):
      self.mode(EXACT | bit)
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(2698.)))
