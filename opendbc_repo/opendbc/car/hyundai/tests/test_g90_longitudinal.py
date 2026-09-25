import unittest

from opendbc.can import CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.hyundai.g90_longitudinal import G90LongitudinalPolicy, LongCtrlState
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC


def params(car=CAR.GENESIS_G90, alpha=True, release=False):
  return CarInterface.get_params(car, gen_empty_fingerprint(), [], alpha, release, False)


class TestG90Longitudinal(unittest.TestCase):
  def test_stop_hold_relaxes_braking_then_release_ramps(self):
    policy = G90LongitudinalPolicy()
    self.assertAlmostEqual(policy.update(-2, 2, LongCtrlState.stopping, True), -1.4)
    self.assertAlmostEqual(policy.update(-2, 0, LongCtrlState.stopping, True), -1.3)
    for _ in range(20):
      policy.update(-2, 0, LongCtrlState.stopping, True)
    self.assertAlmostEqual(policy.actual_accel, -0.1)
    self.assertAlmostEqual(policy.update(1, 0, LongCtrlState.pid, True), -0.05)
    self.assertTrue(policy.release_active)
    self.assertAlmostEqual(policy.update(1, 0, LongCtrlState.pid, True), 0)
    self.assertEqual(policy.update(1, 0, LongCtrlState.off, False), 0)
    self.assertFalse(policy.release_active)
    self.assertEqual(policy.update(1, 0, LongCtrlState.pid, True), 1)

  def test_only_g90_with_longitudinal_ownership_uses_policy(self):
    for car in (CAR.GENESIS_G90, CAR.GENESIS_G80):
      for alpha in (False, True):
        for release in (False, True):
          with self.subTest(car=car, alpha=alpha, release=release):
            cp = params(car, alpha, release)
            ci = CarInterface(cp)
            self.assertEqual(ci.CC.g90_longitudinal is not None, car == CAR.GENESIS_G90 and cp.openpilotLongitudinalControl)
            self.assertEqual(cp.pcmCruise, not cp.openpilotLongitudinalControl)

  def test_classic_can_uses_shaped_accel_and_inactive_messages_are_neutral(self):
    from opendbc.safety.tests.libsafety import libsafety_py
    from opendbc.safety.tests.libsafety.libsafety_py import make_CANPacket

    cp = params()
    native = libsafety_py.libsafety
    self.assertEqual(native.set_safety_hooks(cp.safetyConfigs[-1].safetyModel.raw, cp.safetyConfigs[-1].safetyParam), 0)
    native.init_tests()
    native.set_controls_allowed(True)
    ci = CarInterface(cp)
    ci.update([])
    parser = CANParser(DBC[CAR.GENESIS_G90][Bus.pt], [("SCC12", 0)], 0)
    command = structs.CarControl(enabled=True, longActive=True)
    command.hudControl.setSpeed = 20
    for frame in range(160):
      stopped = frame < 80
      command.actuators.longControlState = LongCtrlState.stopping if stopped else LongCtrlState.pid
      command.actuators.accel = -2 if stopped else 1
      ci.CS.out.vEgo = max(0, 2 - frame * 0.05)
      native.set_timer(frame * 10_000)
      actuators, messages = ci.CC.update(command.as_reader(), ci.CS, frame * 10_000_000)
      for address, data, bus in messages:
        self.assertTrue(native.safety_tx_hook(make_CANPacket(address, bus, data)), (frame, address, data))
      if frame % 2 == 0:
        parser.update((1_000_000_000 + frame * 10_000_000, messages))
        self.assertAlmostEqual(parser.vl["SCC12"]["aReqRaw"], actuators.accel, delta=0.011)
        self.assertAlmostEqual(parser.vl["SCC12"]["aReqValue"], actuators.accel, delta=0.011)
    command.enabled = command.longActive = False
    command.actuators.accel = 0
    _, messages = ci.CC.update(command.as_reader(), ci.CS, 1_600_000_000)
    parser.update((2_600_000_000, messages))
    self.assertEqual(parser.vl["SCC12"]["aReqRaw"], 0)
    self.assertEqual(parser.vl["SCC12"]["aReqValue"], 0)
