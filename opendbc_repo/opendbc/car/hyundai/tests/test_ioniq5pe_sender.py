"""Original PE reached-wire cases; ordinary ownership is tested separately."""
import unittest
from types import SimpleNamespace

from opendbc.can import CANPacker
from opendbc.car.hyundai.hyundaicanfd import create_angle_steering_messages
from opendbc.car.hyundai.values import CAR, HyundaiFlags


class TestIoniq5PESender(unittest.TestCase):
  @staticmethod
  def frame(candidate, angle, status):
    flags = HyundaiFlags.CANFD_ANGLE_STEERING | HyundaiFlags.CANFD_LKA_STEER_MSG | HyundaiFlags.CANFD_LKA_STEER_MSG_ALT
    cp = SimpleNamespace(carFingerprint=candidate, flags=flags, openpilotLongitudinalControl=False)
    packer = CANPacker('hyundai_canfd_generated')
    packer.counters[0x110] = 37
    return create_angle_steering_messages(packer, cp, SimpleNamespace(ACAN=0, ECAN=1),
                                         True, True, angle, 0.5, status)[0]

  def test_original_pe_signed_half_step_quantization(self):
    # Original DBC packer uses floor(angle / 0.1 + 0.5), not ties-to-even.
    for angle, units in ((0.05, 1), (-0.15, -1), (5.0, 50), (-12.3, -123)):
      with self.subTest(angle=angle):
        address, data, bus = self.frame(CAR.HYUNDAI_IONIQ_5_PE, angle, {})
        raw = (data[11] << 6) | (data[10] >> 2)
        signed = raw if raw < 8192 else raw - 16384
        self.assertEqual((address, bus, data[2], signed), (0x110, 0, 37, units))

  def test_pe_active_status_reset_preserves_sibling_status_behavior(self):
    stock = {'LKA_LHLnWrnSta': 2, 'LKA_RHLnWrnSta': 3, 'ToiFltSta': 2, 'LKA_UsmMod': 3}
    _, pe, _ = self.frame(CAR.HYUNDAI_IONIQ_5_PE, 5.0, stock)
    _, sibling, _ = self.frame(CAR.HYUNDAI_IONIQ_5_N, 5.0, stock)
    # Source-derived original active body resets these fields to zero.
    for data, expected in ((pe, (0, 0, 0, 0)), (sibling, (2, 3, 2, 3))):
      actual = ((data[3] >> 6) & 3, data[4] & 3, (data[6] >> 6) & 3, data[10] & 3)
      self.assertEqual(actual, expected)
