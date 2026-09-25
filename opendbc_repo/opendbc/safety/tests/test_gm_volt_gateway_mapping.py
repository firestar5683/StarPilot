"""Exact native admission for the original gateway Volt gas ceiling."""

import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm import gmcan
from opendbc.car.gm.tests.test_volt_grade import command, params
from opendbc.car.gm.values import CAR, DBC, CanBus, GMSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


EXACT = int(GMSafetyFlags.EV | GMSafetyFlags.VOLT_GATEWAY_LONG)


class TestGmVoltGatewayMapping(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker(DBC[CAR.CHEVROLET_VOLT][Bus.pt])

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def mode(self, param, allowed=True):
    self.assertEqual(self.safety.set_safety_hooks(CarParams.SafetyModel.gm, param), 0)
    self.safety.init_tests()
    self.safety.set_controls_allowed(allowed)

  def gas(self, value, *, bus=CanBus.POWERTRAIN, enabled=True):
    frame = gmcan.create_gas_regen_command(self.packer, bus, value, 1, enabled, False)
    return self.packet(frame)

  def test_only_exact_selector_gets_high_ceiling_over_full_param_space(self):
    frame = self.gas(2041)
    accepted = []
    for param in range(1 << 16):
      self.mode(param)
      if self.safety.safety_tx_hook(frame):
        accepted.append(param)
    release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    expected = [EXACT, EXACT | int(GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE),
                EXACT | int(GMSafetyFlags.VOLT_AUTO_HOLD),
                EXACT | int(GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE | GMSafetyFlags.VOLT_AUTO_HOLD)]
    expected += [0xD100, 0xD101, 0xD110, 0xD111]
    if not release:
      expected += [0xD102, 0xD103, 0xD104, 0xD105, 0xD106, 0xD107, 0xD108, 0xD109, 0xD10A,
                   0xD112, 0xD113, 0xD114, 0xD115, 0xD116, 0xD117, 0xD118, 0xD119, 0xD11A]
      expected += [7, 515, 1539, 2563, 3587, 4099, 5123, 16391, 16903, 17927, 18951, 19975,
                   20487, 21511, 49489, 49520, 49523, 0x4287, 0x4687, 0x4A87, 0x4E87, 0x4087, 0x5087, 0x5487, 0xC1D1, 0xC1D3]
    self.assertEqual(accepted, sorted(expected))

  def test_new_ceiling_boundaries_disabled_wrong_bus_and_actual_controller_frames(self):
    self.mode(EXACT)
    for value, accepted in ((-650.125, False), (-650, True), (0, True),
                            (1018, True), (2041, True), (2041.125, False)):
      with self.subTest(value=value):
        self.assertEqual(self.safety.safety_tx_hook(self.gas(value)), accepted)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(2041, bus=CanBus.CHASSIS)))
    short = libsafety_py.make_CANPacket(0x2CB, CanBus.POWERTRAIN, bytes(7))
    self.assertFalse(self.safety.safety_tx_hook(short))
    self.safety.set_relay_malfunction(True)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(2041)))
    self.mode(EXACT)
    self.mode(EXACT, allowed=False)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(1)))
    self.assertTrue(self.safety.safety_tx_hook(self.gas(-650, enabled=False)))

    for alpha in (False, True):
      cp = params(CAR.CHEVROLET_VOLT, alpha=alpha)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, EXACT)
      for speed, accel in ((2., -.5), (10., 0.), (10., 1.), (2., 2.)):
        self.mode(EXACT)
        _, frames = command(cp, accel=accel, speed=speed, orientation=[])
        for frame in frames:
          if frame[0] in (0x2CB, 0x315):
            self.assertTrue(self.safety.safety_tx_hook(self.packet(frame)), (alpha, speed, accel, frame))

  def test_existing_gateway_and_camera_ceilings_stay_separate(self):
    release = self.safety.set_safety_hooks(CarParams.SafetyModel.allOutput, 0) != 0
    self.mode(int(GMSafetyFlags.EV))
    self.assertTrue(self.safety.safety_tx_hook(self.gas(1018)))
    self.assertFalse(self.safety.safety_tx_hook(self.gas(1018.125)))
    self.mode(int(GMSafetyFlags.EV | GMSafetyFlags.HW_CAM | GMSafetyFlags.HW_CAM_LONG))
    self.assertEqual(self.safety.safety_tx_hook(self.gas(1346)), not release)
    self.assertEqual(self.safety.safety_tx_hook(self.gas(1346.125)), not release)
    self.assertEqual(self.safety.safety_tx_hook(self.gas(2698)), not release)
    self.assertFalse(self.safety.safety_tx_hook(self.gas(2698.125)))

  def test_malformed_selector_has_no_transmit_permission(self):
    for other in (0, GMSafetyFlags.HW_CAM, GMSafetyFlags.NO_ACC, GMSafetyFlags.PEDAL_LONG,
                  GMSafetyFlags.SDGM, GMSafetyFlags.ASCM_INTERCEPT, GMSafetyFlags.HW_CAM_LONG):
      for base in (GMSafetyFlags.VOLT_GATEWAY_LONG, GMSafetyFlags.VOLT_GATEWAY_LONG | GMSafetyFlags.EV):
        param = int(base | other)
        if param == EXACT:
          continue
        self.mode(param)
        self.assertFalse(self.safety.safety_tx_hook(self.gas(-650, enabled=False)), param)
        self.assertFalse(self.safety.safety_tx_hook(self.gas(1052)), param)


if __name__ == '__main__':
  unittest.main()
