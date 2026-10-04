"""Exact ordinary removed-camera authority and primary physical sources."""
import unittest
from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CAR, DBC
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py

EXACT = 0xC173


class TestGmOrdinaryCameraRemoved(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    self.packer = CANPacker(DBC[CAR.CHEVROLET_EQUINOX][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, word=EXACT, alternative=0):
    self.safety.init_tests()
    self.safety.set_alternative_experience(alternative)
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word), 0)
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
    for name in ('PSCMStatus', 'EBCMWheelSpdRear', 'EBCMBrakePedalPosition', 'ECMEngineStatus', 'AcceleratorPedal2'):
      self.assertTrue(self.rx(name))
    for button in (3, 1):
      self.rx('ASCMSteeringButton', {'ACCButtons': button})
    self.safety.safety_tick()
    if self.release:
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))
      return
    self.assertTrue(self.safety.safety_config_valid())
    if not self.release:
      self.assertTrue(self.safety.get_controls_allowed())
    for name, values in (('ECMEngineStatus', {'BrakePressed': 1}),):
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
    if self.release:
      self.assertFalse(self.safety.safety_tx_hook(self.gas(-500., enabled=False)))
      return
    for source, blocked in ((0, (0x184,)), (2, (0x180, 0x315, 0x2CB, 0x370, 0x2CD))):
      for addr in blocked:
        self.assertEqual(self.safety.safety_fwd_hook(source, addr),
                         -1)
    self.assertEqual(self.safety.safety_fwd_hook(0, 0x460), -1 if self.release else 2)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x3D1), -1 if self.release else 0)
    self.safety.set_relay_malfunction(True)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(-500., enabled=False)))

  def test_stock_cancel_and_reached_keepalive(self):
    self.mode(0xC172)
    cancel = self.packer.make_can_msg('ASCMSteeringButton', 2, {'ACCButtons': 6, 'RollingCounter': 2})
    self.assertFalse(self.safety.safety_tx_hook(self.packet(cancel)))
    self.rx('AcceleratorPedal2', {'CruiseState': 1})
    self.assertTrue(self.safety.safety_tx_hook(self.packet(cancel)))
    for button in (2, 3):
      frame = self.packer.make_can_msg('ASCMSteeringButton', 2, {'ACCButtons': button})
      self.assertFalse(self.safety.safety_tx_hook(self.packet(frame)))
    self.assertFalse(self.safety.safety_tx_hook(self.packet((cancel[0], cancel[1], 0))))
    self.rx('AcceleratorPedal2')
    self.assertFalse(self.safety.safety_tx_hook(self.packet(cancel)))
    for word in (0xC172, EXACT):
      self.mode(word)
      for addr in (0x409, 0x40A):
        self.assertEqual(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, 0, bytes(7))),
                         word == EXACT and not self.release)
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, 1, bytes(7))))
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x2CD, 0, bytes(5))))

  def test_extra_bits_do_not_inherit_camera_owner(self):
    for bit in (4, 8, 0x80, 0x200, 0x400, 0x800, 0x1000, 0x2000):
      self.mode(EXACT | bit)
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(2698.)))

  def test_camera_main_aol_stock_and_alpha(self):
    for word in (0xC172, EXACT):
      self.mode(word, alternative=32)
      self.safety.set_aol_test_heartbeat(True)
      for name in ('PSCMStatus', 'EBCMWheelSpdRear', 'EBCMBrakePedalPosition', 'ECMEngineStatus', 'AcceleratorPedal2', 'ASCMSteeringButton'):
        self.rx(name, {'CruiseMainOn': 1} if name == 'ECMEngineStatus' else {})
      self.safety.safety_tick()
      self.rx('ECMEngineStatus', {'CruiseMainOn': 1})
      if word == 0xC172 or not self.release:
        self.assertTrue(self.safety.safety_config_valid())
      self.safety.set_controls_allowed(False)
      self.safety.aol_set_host_request(3)
      allowed = word == 0xC172 or not self.release
      self.assertEqual(self.safety.aol_get_permission_mask(), 1 if allowed else 0)
      frame = self.packer.make_can_msg('ASCMLKASteeringCmd', 0, {'LKASteeringCmd': 1, 'LKASteeringCmdActive': 1})
      self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), allowed)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))
      self.rx('ECMEngineStatus')
      self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.safety.set_alternative_experience(0)

  def test_primary_f1_is_required_and_be_cannot_replace_it(self):
    for word in ((0xC172,) if self.release else (0xC172, EXACT)):
      self.mode(word)
      for name in ('PSCMStatus', 'EBCMWheelSpdRear', 'ECMAcceleratorPos', 'ECMEngineStatus', 'AcceleratorPedal2', 'ASCMSteeringButton'):
        self.rx(name)
      self.safety.safety_tick()
      self.assertFalse(self.safety.safety_config_valid())
      frame = self.packer.make_can_msg('EBCMBrakePedalPosition', 0, {})
      self.safety.safety_rx_hook(self.packet((frame[0], frame[1], 2)))
      self.safety.safety_rx_hook(self.packet((frame[0], frame[1][:-1], 0)))
      self.safety.safety_tick()
      self.assertFalse(self.safety.safety_config_valid())
      self.rx('EBCMBrakePedalPosition')
      self.safety.safety_tick()
      self.assertTrue(self.safety.safety_config_valid())
      self.safety.set_timer(2_100_000)
      self.safety.safety_tick()
      self.assertFalse(self.safety.safety_config_valid())
