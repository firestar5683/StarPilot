"""Ordinary camera EV/EUV exact native profile and original keepalive contract."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.tests.test_ascm_intercept import params
from opendbc.car.gm.tests.test_bolt_euv_control import original_demand, original_frames
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests import test_gm_ascm_intercept as ascm


class TestGmBoltEuv(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    self.cp = params(CAR.CHEVROLET_BOLT_EUV, alpha=True)
    self.packer = CANPacker(DBC[self.cp.carFingerprint][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, word):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, word), 0)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)

  def test_exact_limits_keepalive_bytes_and_neighbors(self):
    for word in (7, 3, 5, 4, 7 | int(GMSafetyFlags.ASCM_INTERCEPT),
                 7 | int(GMSafetyFlags.PEDAL_LONG), 7 | int(GMSafetyFlags.VOLT_LONG)):
      self.mode(word)
      exact = word == 7 and not self.release
      self.safety.set_controls_allowed(True)
      for value in (-540.125, -540., 1346., 1346.125, 2698., 2698.125):
        frame = gmcan.create_gas_regen_command(self.packer, 0, value, 0, True, False)
        if exact:
          self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), -540 <= value <= 2698)
        elif word == 0x4007 and not self.release:
          self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), -540 <= value <= 2698)
        elif value > 1346:
          self.assertFalse(self.safety.safety_tx_hook(self.packet(frame)))
      for idx in range(4):
        frame = gmcan.create_acc_2cd_command(0, idx)
        self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), exact or (word == 0x4007 and not self.release))
        self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 2))))
        for byte in range(5):
          bad = bytearray(frame[1])
          bad[byte] ^= 1
          self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], bytes(bad), 0))))
      self.safety.set_controls_allowed(False)
      inactive = gmcan.create_gas_regen_command(self.packer, 0, -500, 0, False, False)
      if word == 7:
        self.assertEqual(self.safety.safety_tx_hook(self.packet(inactive)), exact)
        self.assertFalse(self.safety.safety_tx_hook(self.packet(gmcan.create_gas_regen_command(self.packer, 0, 0, 0, False, False))))

  def test_original_frames_source_freshness_and_forwarding(self):
    self.mode(7)
    sources = ascm.TestGmAscmIntercept.stock_frames(self.packer, False, ev=True)
    sources.append(self.packer.make_can_msg("ECMEngineStatus", 0, {}))
    for frame in sources:
      self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    self.safety.safety_tick()
    self.assertTrue(self.safety.safety_config_valid())
    self.safety.set_controls_allowed(True)
    for idx in range(4):
      for speed, accel, state, resume, pitch in ((0.1, 1., 'stopping', False, 0.),
           (0., -4., 'stopping', False, 0.), (0., 1., 'stopping', True, 0.),
           (12., -.5, 'pid', False, 0.), (12., -2., 'pid', False, 0.),
           (35., 2., 'pid', False, 0.), (100., 2., 'pid', False, 0.)):
        raw, brake = original_demand(self.cp, True, speed, accel, state, resume, pitch)
        for frame in original_frames(raw, brake, idx, True, speed == 0 and state == 'stopping'):
          self.assertEqual(self.safety.safety_tx_hook(self.packet(frame)), not self.release)
    for bus, addr, expected in ((2, 0x2cd, -1 if not self.release else 0),
                               (0, 0x2cd, 2), (2, 0x123, 0), (0, 0x123, 2), (1, 0x2cd, -1)):
      self.assertEqual(self.safety.safety_fwd_hook(bus, addr), expected)
    self.safety.set_timer(2_100_000)
    self.safety.safety_tick()
    self.assertFalse(self.safety.safety_config_valid())
    self.mode(7)
    self.safety.safety_rx_hook(self.packet((0x2cd, bytes(5), 0)))
    self.assertEqual(self.safety.get_relay_malfunction(), not self.release)
