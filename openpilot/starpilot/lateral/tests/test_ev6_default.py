"""Untuned EV6 lateral selection and steering command boundaries."""

import unittest

from opendbc.can import CANParser
from opendbc.car import Bus, DT_CTRL, gen_empty_fingerprint, structs
from opendbc.car.hyundai.carcontroller import CarController, MAX_ANGLE_FRAMES
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.torque_extension import selected_policy
from openpilot.starpilot.lateral.torque_runtime import runtime_enabled


def ev6(lka_steering: bool):
  fingerprint = gen_empty_fingerprint()
  if lka_steering:
    fingerprint[CanBus(None, fingerprint).CAM][0x50] = 16
  return CarInterface.get_params(CAR.KIA_EV6, fingerprint, [], False, False, False)


class NoTorqueSettings:
  def get_param_path(self, _key):
    raise AssertionError("untuned EV6 must not read saved torque settings")


class TestEV6DefaultLateral(unittest.TestCase):
  def test_hda_topologies_keep_vehicle_tune_and_generic_controller(self):
    for lka_steering in (False, True):
      with self.subTest(lka_steering=lka_steering):
        cp = ev6(lka_steering)
        self.assertEqual(bool(cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG), lka_steering)
        self.assertEqual(cp.lateralTuning.which(), "torque")
        self.assertAlmostEqual(cp.lateralTuning.torque.latAccelFactor, 3.2)
        self.assertAlmostEqual(cp.lateralTuning.torque.friction, 0.005)
        self.assertFalse(runtime_enabled(cp, NoTorqueSettings()))
        lateral = LatControlTorque(cp.as_reader(), CarInterface(cp), DT_CTRL)
        self.assertIsNone(selected_policy(lateral))
        self.assertAlmostEqual(lateral.torque_params.latAccelFactor, cp.lateralTuning.torque.latAccelFactor)
        controller = CarController(DBC[cp.carFingerprint], cp)
        self.assertIsNone(controller.ioniq6_longitudinal)
        self.assertEqual(controller.params.STEER_MAX, 409)
        self.assertEqual(controller.params.STEER_DRIVER_ALLOWANCE, 250)

  def test_opposing_driver_torque_limits_can_command_and_angle_request(self):
    for lka_steering in (False, True):
      with self.subTest(lka_steering=lka_steering):
        cp = ev6(lka_steering)
        state = CarState(cp)
        state.out = state.update(state.get_can_parsers(cp))
        control = structs.CarControl()
        control.enabled = control.latActive = True
        control.actuators.torque = 1.0
        controller = CarController(DBC[cp.carFingerprint], cp)
        can = CanBus(cp)
        name = "LKAS" if lka_steering else "LFA"
        bus = can.ACAN if lka_steering else can.ECAN
        parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [(name, 0)], bus)

        state.out.steeringTorque = 0
        controller.apply_torque_last = 60
        _, sent = controller.update(control.as_reader(), state, 1_000_000_000)
        self.assertLessEqual(controller.apply_torque_last, 62)
        self.assertEqual(parser.update((1_000_000_000, sent)), {next(msg[0] for msg in sent if msg[2] == bus)})
        self.assertEqual(parser.vl[name]["ActToiSta"], 1)

        state.out.steeringTorque = -400
        for frame in range(30):
          previous = controller.apply_torque_last
          _, sent = controller.update(control.as_reader(), state, 1_010_000_000 + frame * 10_000_000)
          self.assertLessEqual(controller.apply_torque_last, previous)
        self.assertEqual(controller.apply_torque_last, 0)
        parser.update((1_310_000_000, sent))
        self.assertEqual(parser.vl[name]["StrTqReqVal"], 0)

        state.out.steeringAngleDeg = 90.0
        state.out.steeringTorque = 0
        requests = []
        for frame in range(MAX_ANGLE_FRAMES + 2):
          _, sent = controller.update(control.as_reader(), state, 1_320_000_000 + frame * 10_000_000)
          parser.update((1_320_000_000 + frame * 10_000_000, sent))
          requests.append(parser.vl[name]["ActToiSta"])
        self.assertIn(0, requests[-2:])


if __name__ == "__main__":
  unittest.main()
