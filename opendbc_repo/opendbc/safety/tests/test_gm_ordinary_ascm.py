"""Exact ordinary ASCM longitudinal limits and selected source contracts."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.tests.test_ascm_intercept import params
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests import test_gm_ascm_intercept as ascm


class TestGmOrdinaryAscm(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    self.packer = CANPacker(DBC[CAR.CHEVROLET_MALIBU_ASCM][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, word):
    self.safety.set_alternative_experience(0)
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def feed(self, brake_c9, omit=None):
    for frame in ascm.TestGmAscmIntercept.stock_frames(self.packer, brake_c9, ev=False):
      if frame[0] != omit:
        self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    self.safety.safety_tick()

  def test_exact_limits_inactive_and_radar_exclusion(self):
    for brake_c9 in (False, True):
      for radar in (False, True):
        cp = params(CAR.CHEVROLET_MALIBU_ASCM, sascm=True, alpha=True, accelerator=not brake_c9, radar=radar)
        self.mode(cp.safetyConfigs[0].safetyParam)
        self.feed(brake_c9)
        self.assertTrue(self.safety.safety_config_valid())
        self.safety.set_controls_allowed(True)
        for gas, allowed in ((-650.125, False), (-650, True), (1346., True), (2041., True), (2041.125, False)):
          frame = gmcan.create_gas_regen_command(self.packer, 0, gas, 1, True, False)
          self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), allowed and not self.release)
          self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 2))))
        for brake, allowed in ((0, True), (400, True), (401, False)):
          frame = gmcan.create_friction_brake_command(self.packer, 0, brake, 1, True, False, False, cp)
          self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), allowed and not self.release)
          self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 2))))
        for addr, length in ((0xa1, 7), (0x306, 8), (0x308, 7), (0x310, 2)):
          self.assertFalse(self.safety.safety_tx_hook(self.packet((addr, bytes(length), 1))))
        self.safety.set_controls_allowed(False)
        inactive = gmcan.create_gas_regen_command(self.packer, 0, -650, 1, False, False)
        self.assertEqual(self.safety.safety_tx_hook(self.packet(inactive)), not self.release)
        self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_gas_regen_command(self.packer, 0, 0., 1, True, False))))
        # Stock ownership is unchanged and cannot gain longitudinal TX.
        self.mode(cp.safetyConfigs[0].safetyParam & ~int(GMSafetyFlags.HW_CAM_LONG))
        self.safety.set_controls_allowed(True)
        self.assertFalse(self.safety.safety_tx_hook(self.packet(
          gmcan.create_gas_regen_command(self.packer, 0, 2041., 1, True, False))))

  def test_observed_brake_health_engagement_and_actual_output(self):
    for brake_c9 in (False, True):
      cp = params(CAR.CHEVROLET_MALIBU_ASCM, sascm=True, alpha=True, accelerator=not brake_c9, radar=True)
      word = cp.safetyConfigs[0].safetyParam
      self.mode(word)
      self.feed(brake_c9, omit=0xc9 if brake_c9 else 0xbe)
      self.assertFalse(self.safety.safety_config_valid())
      self.mode(word)
      self.feed(brake_c9)
      for button in (3, 1):
        frame = self.packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': button})
        self.safety.safety_rx_hook(self.packet(frame))
      self.assertEqual(self.safety.get_controls_allowed(), not self.release)
      gas = gmcan.create_gas_regen_command(self.packer, 0, 2041., 1, True, False)
      self.assertEqual(self.safety.safety_tx_hook(self.packet(gas)), not self.release)
      steering = gmcan.create_steering_control(self.packer, 0, 1, 0, True)
      self.assertEqual(self.safety.safety_tx_hook(self.packet(steering)), not self.release)
      pressed = self.packer.make_can_msg('ECMEngineStatus' if brake_c9 else 'ECMAcceleratorPos', 0,
                                        {'BrakePressed': 1} if brake_c9 else {'BrakePedalPos': 10})
      self.safety.safety_rx_hook(self.packet(pressed))
      self.assertFalse(self.safety.get_controls_allowed())
      self.safety.set_timer(2_100_000)
      self.safety.safety_tick()
      self.assertFalse(self.safety.safety_config_valid())

  def test_existing_selector_neighbors_and_relay_behavior(self):
    for brake_c9 in (False, True):
      for radar in (False, True):
        cp = params(CAR.CHEVROLET_MALIBU_ASCM, sascm=True, alpha=True, accelerator=not brake_c9, radar=radar)
        self.mode(cp.safetyConfigs[0].safetyParam | int(GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE))
        self.safety.set_controls_allowed(True)
        self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_gas_regen_command(self.packer, 0, -650, 1, False, False))))
        self.mode(cp.safetyConfigs[0].safetyParam)
        for bus, addr, expected in ((0, 0x123, 2), (2, 0x123, 0), (2, 0x180, -1),
                                    (2, 0x315, 0 if self.release else -1), (1, 0x123, -1)):
          self.assertEqual(self.safety.safety_fwd_hook(bus, addr), expected)
        self.safety.safety_rx_hook(self.packet((0x315, bytes(5), 0)))
        self.assertEqual(self.safety.get_relay_malfunction(), not self.release)
