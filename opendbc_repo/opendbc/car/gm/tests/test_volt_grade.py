import math
import unittest
from types import SimpleNamespace

import numpy as np

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm import gmcan
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.tests.test_bolt_acc_pedal_friction import brake_fields
from opendbc.car.gm.values import CAR, DBC, CanBus, GMFlags, GMSafetyFlags


def params(candidate, *, alpha=False, sascm=False, accelerator=True):
  fingerprint = gen_empty_fingerprint()
  if accelerator:
    fingerprint[CanBus.POWERTRAIN][0xbe] = 6
  fingerprint[CanBus.OBSTACLE][1120] = 8
  if sascm:
    fingerprint[CanBus.POWERTRAIN][0x2ff] = 8
  return CarInterface.get_params(candidate, fingerprint, [], alpha, False, False)


def original_grade_demands(accel, speed, pitch, stopping_speed, minimum, maximum):
  grade = math.sin(pitch) * 9.81 if pitch is not None and speed > stopping_speed else 0.0
  if grade > 0.0 and accel > 0.0:
    grade = 0.0
  else:
    grade = min(grade, 0.20)
  gas = float(np.clip(accel + grade, minimum, maximum))
  brake = float(np.clip(accel + grade * np.interp(speed, [5.0, 10.0], [0.0, 1.0]), minimum, maximum))
  return gas, brake


def command(cp, *, accel, speed, orientation, active=True, frame=4):
  controller = CarController(DBC[cp.carFingerprint], cp)
  controller.frame = frame
  controller.last_steer_frame = frame
  control = structs.CarControl()
  control.enabled = True
  control.longActive = active
  control.actuators.accel = accel
  control.orientationNED = orientation
  state = structs.CarState()
  state.vEgo = speed
  state.cruiseState.available = True
  cs = SimpleNamespace(out=state.as_reader(), stock_fcw_alert=0, cam_lka_steering_cmd_counter=0,
                       loopback_lka_steering_cmd_updated=False,
                       loopback_lka_steering_cmd_ts_nanos=1_000_000_000,
                       pt_lka_steering_cmd_counter=0,
                       pscm_status={key: 0 for key in ("HandsOffSWDetectionMode", "HandsOffSWlDetectionStatus",
                                                            "LKATorqueDeliveredStatus", "LKADriverAppldTrq",
                                                            "LKATorqueDelivered", "LKATotalTorqueDelivered",
                                                            "RollingCounter", "PSCMStatusChecksum")})
  _, messages = controller.update(control.as_reader(), cs, 1_000_000_000)
  return controller, messages


class TestVoltGrade(unittest.TestCase):
  def test_legacy_unmarked_ascm_grade_shape_reaches_gas_and_brake_frames(self):
    for candidate, alpha, sascm in ((CAR.CHEVROLET_VOLT_ASCM, True, True),):
      cp = params(candidate, alpha=alpha, sascm=sascm)
      cp.safetyConfigs[0].safetyParam &= ~int(GMSafetyFlags.VOLT_LONG)
      self.assertTrue(cp.openpilotLongitudinalControl)
      self.assertFalse(cp.pcmCruise)
      self.assertFalse(cp.dashcamOnly)
      self.assertFalse(cp.flags & GMFlags.PEDAL_LONG)
      packer = CANPacker(DBC[candidate][Bus.pt])
      for accel, speed, pitch in ((-1.5, 4.0, -0.04), (-1.5, 7.0, -0.04), (-1.5, 12.0, -0.04),
                                  (-1.5, 12.0, 0.04), (0.5, 12.0, 0.04), (0.0, 12.0, 0.04),
                                  (-3.9, 12.0, -0.15), (1.9, 12.0, -0.04), (-1.5, 0.6, -0.04),
                                  (-1.5, 0.1, -0.04)):
        with self.subTest(candidate=candidate, alpha=alpha, accel=accel, speed=speed, pitch=pitch):
          controller, messages = command(cp, accel=accel, speed=speed, orientation=[0.0, pitch, 0.0])
          stop_speed = 0.75 if cp.networkLocation == structs.CarParams.NetworkLocation.gateway else 0.25
          gas_demand, brake_demand = original_grade_demands(float(np.float32(accel)), float(np.float32(speed)),
                                                            float(np.float32(pitch)), stop_speed,
                                                            controller.params.ACCEL_MIN, controller.params.ACCEL_MAX)
          gas = float(np.interp(gas_demand, controller.params.GAS_LOOKUP_BP, controller.params.GAS_LOOKUP_V))
          brake = int(round(np.interp(brake_demand, controller.params.BRAKE_LOOKUP_BP, controller.params.BRAKE_LOOKUP_V)))
          self.assertEqual(controller.apply_gas, gas)
          self.assertEqual(controller.apply_brake, brake)
          actual_gas = next(message for message in messages if message[0] == 0x2cb)
          actual_brake = next(message for message in messages if message[0] == 0x315)
          self.assertEqual(actual_gas, gmcan.create_gas_regen_command(packer, CanBus.POWERTRAIN, gas, 1, True, False))
          self.assertEqual(brake_fields(actual_brake)[1], brake)

  def test_missing_invalid_pitch_and_lost_long_ownership_leave_no_grade(self):
    cp = params(CAR.CHEVROLET_VOLT)
    baseline, _ = command(cp, accel=-1.5, speed=12.0, orientation=[0.0, 0.0, 0.0])
    for orientation in ([], [0.0, float('nan'), 0.0], [0.0, float('inf'), 0.0]):
      controller, _ = command(cp, accel=-1.5, speed=12.0, orientation=orientation)
      self.assertEqual((controller.apply_gas, controller.apply_brake),
                       (baseline.apply_gas, baseline.apply_brake))
    inactive, messages = command(cp, accel=-1.5, speed=12.0, orientation=[0.0, -0.04, 0.0], active=False)
    self.assertEqual((inactive.apply_gas, inactive.apply_brake), (inactive.params.INACTIVE_REGEN, 0))
    self.assertEqual(brake_fields(next(message for message in messages if message[0] == 0x315))[1], 0)
    stock = params(CAR.CHEVROLET_VOLT_ASCM, alpha=False, sascm=True)
    self.assertTrue(stock.pcmCruise)
    self.assertFalse(stock.openpilotLongitudinalControl)
    _, messages = command(stock, accel=-1.5, speed=12.0, orientation=[0.0, -0.04, 0.0])
    self.assertFalse(any(message[0] in (0x2cb, 0x315) for message in messages))


if __name__ == '__main__':
  unittest.main()
