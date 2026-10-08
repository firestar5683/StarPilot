"""Exact Volt SDGM alpha authority; stock and neighboring profiles stay isolated."""
import unittest
from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CAR, CruiseButtons, DBC
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py

EXACT = 0x5007


class TestGmVoltSdgm(unittest.TestCase):
  word = EXACT
  brake_source = ('ECMAcceleratorPos', {'BrakePedalPos': 8})

  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    self.packer = CANPacker(DBC[CAR.CHEVROLET_VOLT_2019][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, word=None):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, self.word if word is None else word), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def rx(self, name, values=None, bus=0):
    return self.safety.safety_rx_hook(self.packet(self.packer.make_can_msg(name, bus, values or {})))

  def gas(self, value, enabled=True, bus=0):
    return self.packet(gmcan.create_gas_regen_command(self.packer, bus, value, 1, enabled, False))

  def test_exact_limits_and_unowned_transmit(self):
    self.mode()
    self.safety.set_controls_allowed(True)
    for gas, allowed in ((-540.125, False), (-540., True), (2041., True), (2041.125, False), (2698., False)):
      self.assertEqual(self.safety.safety_tx_hook(self.gas(gas)), allowed and not self.release)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(0., bus=2)))
    for active in (False, True):
      dashboard = self.packer.make_can_msg('ASCMActiveCruiseControlStatus', 0,
                                          {'ACCCruiseState': 2, 'ACCCmdActive': active, 'FCWAlert': 2})
      self.assertEqual(self.safety.safety_tx_hook(self.packet(dashboard)), not self.release)
      self.assertFalse(self.safety.safety_tx_hook(self.packet((dashboard[0], dashboard[1], 2))))
      self.assertFalse(self.safety.safety_tx_hook(self.packet((dashboard[0], dashboard[1][:-1], 0))))
    for brake, allowed in ((0, True), (400, True), (401, False)):
      frame = self.packer.make_can_msg('EBCMFrictionBrakeCmd', 2, {'FrictionBrakeCmd': -brake})
      self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), allowed and not self.release)
      self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 0))))
    frame = self.packer.make_can_msg('ASCMLKASteeringCmd', 0, {'LKASteeringCmd': 1, 'LKASteeringCmdActive': 1})
    self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), not self.release)
    self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1][:-1], 0))))
    for addr, length, bus in ((0x200, 6, 0), (0xBD, 7, 0), (0x1F5, 8, 0), (0x3D1, 8, 0),
                              (0xA1, 7, 1), (0x306, 8, 1), (0x308, 7, 1), (0x310, 2, 1), (0x2CD, 5, 0)):
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, bytes(length))))
    self.safety.set_controls_allowed(False)
    self.assertEqual(self.safety.safety_tx_hook(self.gas(-500., enabled=False)), not self.release)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))

  def test_accepted_envelope_is_exact_and_does_not_restrict_alias_or_pedal_owners(self):
    for word in (0x5007, 0x5407):
      self.mode(word)
      self.safety.set_controls_allowed(True)
      for gas, allowed in ((-540.125, False), (-540., True), (2041., True), (2041.125, False), (2350., False)):
        self.assertEqual(self.safety.safety_tx_hook(self.gas(gas)), allowed and not self.release)
    for word in (0x5087, 0x5487, 0xD107, 0xD108, 0xD117, 0xD118):
      self.mode(word)
      self.safety.set_controls_allowed(True)
      self.assertEqual(self.safety.safety_tx_hook(self.gas(2698.)), not self.release)

  def test_driver_button_brake_gas_regen_and_timeout(self):
    self.mode()
    if self.release:
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))
      self.safety.safety_tick()
      self.assertFalse(self.safety.safety_config_valid())
      return
    for name in ('PSCMStatus', 'EBCMWheelSpdRear', 'ECMAcceleratorPos', 'ECMEngineStatus', 'AcceleratorPedal2', 'EBCMRegenPaddle'):
      self.assertTrue(self.rx(name))
    for button in (3, 1):
      self.rx('ASCMSteeringButton', {'ACCButtons': button})
    self.safety.safety_tick()
    self.assertTrue(self.safety.safety_config_valid())
    self.assertEqual(self.safety.get_controls_allowed(), not self.release)
    for name, values in (self.brake_source, ('EBCMRegenPaddle', {'RegenPaddle': 2})):
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

  def test_selected_brake_source_and_regen_bus(self):
    self.mode()
    if self.release:
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))
      return
    other_brake = ('ECMEngineStatus', {'BrakePressed': 1}) if self.word == EXACT else ('ECMAcceleratorPos', {'BrakePedalPos': 8})
    self.safety.set_controls_allowed(True)
    self.rx(*other_brake)
    self.assertEqual(self.safety.get_controls_allowed(), not self.release)
    self.safety.set_controls_allowed(True)
    self.rx('EBCMRegenPaddle', {'RegenPaddle': 2}, bus=2)
    self.assertEqual(self.safety.get_controls_allowed(), not self.release)
    self.rx('EBCMRegenPaddle', {'RegenPaddle': 2})
    self.assertFalse(self.safety.get_controls_allowed())
    self.rx('EBCMRegenPaddle')
    self.assertFalse(self.safety.get_controls_allowed())

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

  def test_extra_bits_do_not_inherit_camera_owner(self):
    for bit in (0x8, 0x10, 0x20, 0x200, 0x800, 0x2000, 0x8000):
      self.mode(self.word | bit)
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.safety.safety_tx_hook(self.gas(2698.)))

  def test_stock_and_radar_neighbors_have_no_alpha_authority(self):
    for word in (0x1005, 0x1405, 0x4807, 0x5807, 0x5C07):
      with self.subTest(word=word):
        self.mode(word)
        self.safety.set_controls_allowed(True)
        self.assertFalse(self.safety.safety_tx_hook(self.gas(2698.)))
        brake = self.packer.make_can_msg('EBCMFrictionBrakeCmd', 2, {'FrictionBrakeCmd': -1})
        self.assertFalse(self.safety.safety_tx_hook(self.packet(brake)))
        self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(0x310, 1, bytes(2))))

  def test_stock_cancel_stays_on_camera(self):
    for word in (0x1005, 0x1405):
      with self.subTest(word=word):
        self.mode(word)
        self.rx('AcceleratorPedal2', {'CruiseState': 2})
        for counter in range(4):
          cancel = gmcan.create_buttons(self.packer, 2, counter, CruiseButtons.CANCEL)
          self.assertTrue(self.safety.safety_tx_hook(self.packet(cancel)))
          self.assertFalse(self.safety.safety_tx_hook(self.packet((cancel[0], cancel[1], 0))))
        self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_buttons(self.packer, 2, 0, CruiseButtons.RES_ACCEL))))


class TestGmVoltSdgmC9(TestGmVoltSdgm):
  word = 0x5407
  brake_source = ('ECMEngineStatus', {'BrakePressed': 1})
