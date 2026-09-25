"""Native gateway Volt brake-source and bus permissions."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.tests.test_bolt_volt_configurations import ordinary_params, controller_messages
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


BASE = int(GMSafetyFlags.EV | GMSafetyFlags.VOLT_GATEWAY_LONG)
ALT = BASE | int(GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE)


class TestGmVoltAlternateBrake(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker(DBC[CAR.CHEVROLET_VOLT][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, param=ALT):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, param), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def frame(self, name, values=None, bus=0):
    return self.packet(self.packer.make_can_msg(name, bus, values or {}))

  def feed_sources(self, brake_source='EBCMBrakePedalPosition'):
    for name in ('PSCMStatus', 'EBCMWheelSpdRear', 'ASCMSteeringButton', 'AcceleratorPedal2',
                 'ECMEngineStatus', 'EBCMRegenPaddle', brake_source):
      self.assertTrue(self.safety.safety_rx_hook(self.frame(name)))
    self.safety.safety_tick()

  def test_required_brake_input_and_timeout(self):
    self.mode()
    self.feed_sources('ECMAcceleratorPos')
    self.assertFalse(self.safety.safety_config_valid())
    self.safety.safety_rx_hook(self.frame('EBCMBrakePedalPosition', bus=2))
    self.safety.safety_tick()
    self.assertFalse(self.safety.safety_config_valid())
    self.safety.safety_rx_hook(self.frame('EBCMBrakePedalPosition'))
    self.safety.safety_tick()
    self.assertTrue(self.safety.safety_config_valid())
    self.safety.set_timer(2_100_000)
    self.feed_sources('ECMAcceleratorPos')
    self.assertFalse(self.safety.safety_config_valid())
    self.assertFalse(self.safety.safety_tx_hook(self.packet((0x315, bytes.fromhex('afff500001'), 0))))

  def test_original_ebcm_threshold_and_no_other_brake_source(self):
    for raw in (0, 5, 6, 7, 255):
      self.mode()
      self.feed_sources()
      self.safety.set_controls_allowed(True)
      self.safety.safety_rx_hook(self.frame('EBCMBrakePedalPosition', {'BrakePedalPosition': raw}))
      self.assertEqual(self.safety.get_brake_pressed_prev(), raw >= 6)
      self.assertEqual(self.safety.get_controls_allowed(), raw < 6)
      for name, fields in (('ECMEngineStatus', {'BrakePressed': int(raw < 6)}),
                           ('ECMAcceleratorPos', {'BrakePedalPos': 255 if raw < 6 else 0})):
        self.safety.safety_rx_hook(self.frame(name, fields))
        self.assertEqual(self.safety.get_brake_pressed_prev(), raw >= 6)
      self.safety.safety_rx_hook(self.frame('EBCMBrakePedalPosition', {'BrakePedalPosition': 0 if raw >= 6 else 255}, bus=2))
      self.assertEqual(self.safety.get_brake_pressed_prev(), raw >= 6)

  def test_braking_limits_bus_relay_regen_and_no_forwarding(self):
    for param, bus in ((BASE, 2), (ALT, 0)):
      self.mode(param)
      self.safety.set_controls_allowed(True)
      cp = ordinary_params(CAR.CHEVROLET_VOLT, radar=True, accelerator=param == BASE)
      for demand, accepted in ((0, True), (1, True), (400, True), (401, False)):
        frame = gmcan.create_friction_brake_command(self.packer, bus, demand, 1, True, False, False, cp)
        self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), accepted)
        self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 2 - bus))))
      self.safety.set_controls_allowed(False)
      frame = gmcan.create_friction_brake_command(self.packer, bus, 1, 1, True, False, False, cp)
      self.assertFalse(self.safety.safety_tx_hook(self.packet(frame)))
      self.safety.set_controls_allowed(True)
      self.safety.safety_rx_hook(self.frame('EBCMRegenPaddle', {'RegenPaddle': 1}))
      self.assertFalse(self.safety.get_controls_allowed())
      for rx_bus in (0, 1, 2):
        for address in (0x180, 0x315, 0x2cb, 0xf1, 0xbe):
          self.assertEqual(self.safety.safety_fwd_hook(rx_bus, address), -1)
    # Stock friction on the owned PT bus is a real relay malfunction, while
    # the same frame on the unowned chassis bus must not trigger that check.
    for bus, expected in ((2, False), (0, True)):
      self.mode()
      self.safety.safety_rx_hook(self.packet((0x315, bytes.fromhex('1000efff01'), bus)))
      self.assertEqual(self.safety.get_relay_malfunction(), expected)
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(self.packet((0x315, bytes.fromhex('afff500001'), 0))))

  def test_actual_controller_frames_after_observed_engagement(self):
    for alpha in (False, True):
      cp = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, radar=True, accelerator=False)
      self.mode(cp.safetyConfigs[0].safetyParam)
      self.feed_sources()
      self.assertTrue(self.safety.safety_config_valid())
      self.safety.safety_rx_hook(self.frame('ASCMSteeringButton', {'ACCButtons': 3}))
      self.safety.safety_rx_hook(self.frame('ASCMSteeringButton', {'ACCButtons': 1}))
      self.assertTrue(self.safety.get_controls_allowed())
      for demand in (-4., -.5, 0., 2.):
        _, frames = controller_messages(cp, 4, accel=demand)
        for frame in frames:
          self.assertTrue(self.safety.safety_tx_hook(self.packet(frame)), (alpha, demand, frame))
      brake = gmcan.create_friction_brake_command(self.packer, 0, 1, 1, True, False, False, cp)
      self.safety.safety_rx_hook(self.frame('EBCMBrakePedalPosition', {'BrakePedalPosition': 6}))
      self.assertFalse(self.safety.safety_tx_hook(self.packet(brake)))

  def test_malformed_alt_selector_and_ordinary_source_do_not_cross(self):
    for param in (int(GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE), ALT ^ int(GMSafetyFlags.EV),
                  ALT ^ int(GMSafetyFlags.VOLT_GATEWAY_LONG), ALT | int(GMSafetyFlags.HW_CAM),
                  ALT | int(GMSafetyFlags.PEDAL_LONG), ALT | int(GMSafetyFlags.NO_ACC),
                  ALT | int(GMSafetyFlags.ASCM_INTERCEPT), ALT | int(GMSafetyFlags.SDGM)):
      self.mode(param)
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.safety.safety_tx_hook(self.packet((0x315, bytes.fromhex('1000efff01'), 0))))
      self.assertFalse(self.safety.safety_tx_hook(self.packet((0x2cb, bytes.fromhex('4142fff800bd0007'), 0))))
    self.mode(BASE)
    self.safety.set_controls_allowed(True)
    self.safety.safety_rx_hook(self.frame('EBCMBrakePedalPosition', {'BrakePedalPosition': 255}))
    self.assertFalse(self.safety.get_brake_pressed_prev())
    self.safety.safety_rx_hook(self.frame('ECMAcceleratorPos', {'BrakePedalPos': 8}))
    self.assertTrue(self.safety.get_brake_pressed_prev())


if __name__ == '__main__':
  unittest.main()
