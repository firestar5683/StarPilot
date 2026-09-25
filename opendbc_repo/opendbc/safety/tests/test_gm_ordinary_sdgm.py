"""Exact non-EV SDGM longitudinal ownership and stock-profile isolation."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CAR, CruiseButtons, DBC
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


class TestGmOrdinarySdgm(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    self.safety.set_alternative_experience(0)
    self.packer = CANPacker(DBC[CAR.CHEVROLET_MALIBU_SDGM][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, word):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def rx(self, name, values=None, bus=0):
    return self.safety.safety_rx_hook(self.packet(self.packer.make_can_msg(name, bus, values or {})))

  def gas(self, value, enabled=True, bus=0):
    return self.packet(gmcan.create_gas_regen_command(self.packer, bus, value, 1, enabled, False))

  def test_exact_limits_and_bus_ownership(self):
    for word in (0x1003, 0x1403):
      with self.subTest(word=word):
        self.mode(word)
        self.safety.set_controls_allowed(True)
        for value, allowed in ((-540.125, False), (-540., True), (2698., True), (2698.125, False)):
          self.assertEqual(self.safety.safety_tx_hook(self.gas(value)), allowed and not self.release)
        self.assertFalse(self.safety.safety_tx_hook(self.gas(0., bus=2)))
        for brake, allowed in ((0, True), (400, True), (401, False)):
          frame = self.packer.make_can_msg('EBCMFrictionBrakeCmd', 2, {'FrictionBrakeCmd': -brake})
          self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), allowed and not self.release)
          self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 0))))
        self.safety.set_controls_allowed(False)
        self.assertEqual(self.safety.safety_tx_hook(self.gas(-500., enabled=False)), not self.release)
        self.assertFalse(self.safety.safety_tx_hook(self.gas(-500.125, enabled=False)))
        for address, length in ((0x2CD, 5), (0x310, 2), (0x306, 8), (0x308, 7), (0xA1, 7), (0x200, 6)):
          self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(address, 1 if address != 0x2CD else 0, bytes(length))))

  def test_selected_driver_source_and_forwarding(self):
    for word in (0x1003, 0x1403):
      with self.subTest(word=word):
        self.mode(word)
        if self.release:
          self.safety.set_controls_allowed(True)
          self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))
          continue
        selected = ('ECMEngineStatus', {'BrakePressed': 1}) if word == 0x1403 else ('ECMAcceleratorPos', {'BrakePedalPos': 8})
        other = ('ECMAcceleratorPos', {'BrakePedalPos': 8}) if word == 0x1403 else ('ECMEngineStatus', {'BrakePressed': 1})
        self.safety.set_controls_allowed(True)
        self.rx(*other)
        self.assertTrue(self.safety.get_controls_allowed())
        self.rx(*selected)
        self.assertFalse(self.safety.get_controls_allowed())
        self.rx(selected[0])
        self.assertFalse(self.safety.get_controls_allowed())
        self.safety.set_controls_allowed(True)
        self.rx('AcceleratorPedal2', {'AcceleratorPedal2': 1})
        self.assertTrue(self.safety.get_controls_allowed())
        self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))
        for bus, addresses in ((0, (0x184,)), (2, (0x180, 0x315, 0x2CB, 0x370, 0x2CD))):
          for address in addresses:
            self.assertEqual(self.safety.safety_fwd_hook(bus, address), -1)
        self.assertEqual(self.safety.safety_fwd_hook(2, 0x3D1), 0)
        self.safety.set_relay_malfunction(True)
        self.assertFalse(self.safety.safety_tx_hook(self.gas(-500., enabled=False)))

  def test_stock_cancel_and_negative_combinations(self):
    for word in (0x1001, 0x1401, 0x3001, 0x3401):
      with self.subTest(word=word):
        self.mode(word)
        self.rx('AcceleratorPedal2', {'CruiseState': 2})
        bus = 0 if word & 0x2000 else 2
        cancel = gmcan.create_buttons(self.packer, bus, 0, CruiseButtons.CANCEL)
        self.assertTrue(self.safety.safety_tx_hook(self.packet(cancel)))
        self.assertFalse(self.safety.safety_tx_hook(self.packet((cancel[0], cancel[1], 2 - bus))))
        self.safety.set_controls_allowed(True)
        self.assertFalse(self.safety.safety_tx_hook(self.gas(2698.)))
    for word in (0x1003, 0x1403):
      for bit in (0x8, 0x10, 0x20, 0x200, 0x800, 0x2000, 0x8000):
        with self.subTest(word=word, bit=bit):
          self.mode(word | bit)
          self.safety.set_controls_allowed(True)
          self.assertFalse(self.safety.safety_tx_hook(self.gas(2698.)))

  def test_non_ev_source_health_and_steering(self):
    for word in (0x1003, 0x1403):
      with self.subTest(word=word):
        self.mode(word)
        if self.release:
          continue
        for name in ('PSCMStatus', 'EBCMWheelSpdRear', 'ASCMSteeringButton', 'AcceleratorPedal2'):
          self.rx(name)
        self.rx('ECMEngineStatus' if word == 0x1403 else 'ECMAcceleratorPos')
        self.assertTrue(self.safety.safety_config_valid())
        self.safety.set_controls_allowed(True)
        self.safety.set_torque_driver(0, 0)
        self.safety.set_desired_torque_last(0)
        self.safety.set_rt_torque_last(0)
        steer = self.packer.make_can_msg('ASCMLKASteeringCmd', 0, {'LKASteeringCmd': 1, 'LKASteeringCmdActive': 1})
        self.assertTrue(self.safety.safety_tx_hook(self.packet(steer)))
        self.rx('EBCMRegenPaddle', {'RegenPaddle': 2})
        self.assertTrue(self.safety.get_controls_allowed())
        self.safety.set_timer(2_100_000)
        self.safety.safety_tick()
        self.assertFalse(self.safety.safety_config_valid())
        self.assertFalse(self.safety.get_controls_allowed())

  def test_aol_main_source_and_longitudinal_separation(self):
    for word in (0x1001, 0x1401, 0x3001, 0x3401, 0x1003, 0x1403):
      for alternative in (0, 32):
        with self.subTest(word=word, alternative=alternative):
          self.safety.set_alternative_experience(alternative)
          self.mode(word)
          self.safety.set_aol_test_heartbeat(True)
          for name in ('PSCMStatus', 'EBCMWheelSpdRear', 'ASCMSteeringButton', 'AcceleratorPedal2'):
            self.rx(name)
          self.rx('ECMAcceleratorPos')
          self.rx('ECMEngineStatus', {'CruiseMainOn': 1})
          self.safety.safety_tick()
          supported = alternative == 32 and not (self.release and word in (0x1003, 0x1403))
          self.safety.aol_set_host_request(3)
          self.assertEqual(self.safety.aol_get_permission_mask(), 1 if supported else 0)
          self.assertFalse(self.safety.get_controls_allowed())
          self.assertFalse(self.safety.safety_tx_hook(self.gas(0.)))
          steering = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
          self.assertEqual(self.safety.safety_tx_hook(self.packet(steering)), supported)
          self.safety.set_timer(1_300_001)
          self.safety.aol_set_host_request(1)
          self.assertEqual(self.safety.aol_get_permission_mask(), 0)
    self.safety.set_alternative_experience(0)
