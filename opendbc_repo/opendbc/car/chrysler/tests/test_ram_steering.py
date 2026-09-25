import unittest

from opendbc.can import CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.chrysler.interface import CarInterface
from opendbc.car.chrysler.values import CAR, DBC


def params(alpha=False, release=False, firmware=b"68410000"):
  fw = structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.eps, fwVersion=firmware)
  return CarInterface.get_params(CAR.RAM_1500_5TH_GEN, gen_empty_fingerprint(), [fw], alpha, release, False)


class TestRamSteering(unittest.TestCase):
  def test_enable_window_is_separate_from_steering_minimum(self):
    for firmware in (b"68310000", b"68410000"):
      for alpha in (False, True):
        for release in (False, True):
          with self.subTest(firmware=firmware, alpha=alpha, release=release):
            cp = params(alpha, release, firmware)
            self.assertEqual(cp.minEnableSpeed, 14.5)
            self.assertEqual(cp.minSteerSpeed, 0.5)
            self.assertEqual(cp.safetyConfigs[0].safetyParam, 1)
            self.assertTrue(cp.pcmCruise)
            self.assertFalse(cp.openpilotLongitudinalControl)

  def test_window_latches_but_gear_change_and_cooldown_block_reentry(self):
    ci = CarInterface(params())
    ci.update([])
    command = structs.CarControl(latActive=True)
    command.actuators.torque = 0.1
    gear = structs.CarState.GearShifter
    parser = CANParser(DBC[CAR.RAM_1500_5TH_GEN][Bus.pt], [("LKAS_COMMAND", 0)], 0)
    cases = (
      (202, 15.1, gear.drive, False),
      (204, 14.5, gear.drive, True),
      (206, 25, gear.drive, True),
      (208, 2, gear.drive, True),
      (210, 14.75, gear.reverse, False),
      (212, 14.75, gear.drive, False),
      (410, 14.75, gear.drive, False),
      (412, 14.75, gear.drive, True),
      (414, 14.75, gear.neutral, False),
      (616, 15, gear.drive, True),
    )
    for frame, speed, selected_gear, expected in cases:
      with self.subTest(frame=frame):
        ci.CC.frame = frame
        ci.CS.out.vEgo = speed
        ci.CS.out.gearShifter = selected_gear
        _, messages = ci.CC.update(command.as_reader(), ci.CS, frame * 10_000_000)
        parser.update((frame * 10_000_000, messages))
        self.assertEqual(ci.CC.lkas_control_bit_prev, expected)
        if not expected:
          self.assertEqual(parser.vl["LKAS_COMMAND"]["STEERING_TORQUE"], 0)

  def test_full_host_torque_ramp_passes_existing_native_limits(self):
    from opendbc.safety.tests.libsafety import libsafety_py
    from opendbc.safety.tests.libsafety.libsafety_py import make_CANPacket

    native = libsafety_py.libsafety
    self.assertEqual(native.set_safety_hooks(9, 1), 0)
    native.init_tests()
    native.set_controls_allowed(True)
    ci = CarInterface(params())
    ci.update([])
    ci.CS.out.vEgo = 14.75
    ci.CS.out.gearShifter = structs.CarState.GearShifter.drive
    command = structs.CarControl(latActive=True)
    command.actuators.torque = 1
    for frame in range(202, 342, 2):
      ci.CC.frame = frame
      ci.CS.out.steeringTorqueEps = ci.CC.apply_torque_last
      native.set_torque_meas(ci.CC.apply_torque_last, ci.CC.apply_torque_last)
      native.set_timer(frame * 10_000)
      actuators, messages = ci.CC.update(command.as_reader(), ci.CS, frame * 10_000_000)
      for address, data, bus in messages:
        self.assertTrue(native.safety_tx_hook(make_CANPacket(address, bus, data)), (frame, address, data))
    self.assertEqual(actuators.torqueOutputCan, 350)
    self.assertEqual(actuators.torque, 1)
    command.latActive = False
    ci.CC.frame = 344
    actuators, _ = ci.CC.update(command.as_reader(), ci.CS, 3_440_000_000)
    self.assertEqual(actuators.torqueOutputCan, 0)
