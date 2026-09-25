"""Explicit torque values exercised against the current native controller."""

import math
import unittest

from openpilot.cereal import log
from opendbc.car.structs import car
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.torque_tuning import TorqueSource, TorqueTuning, from_record


PLATFORM = TOYOTA.TOYOTA_RAV4_TSS2


def native_controller():
  interface = interfaces[PLATFORM]
  cp = interface.get_non_essential_params(PLATFORM)
  controller = LatControlTorque(cp.as_reader(), interface(cp), DT_CTRL)
  return cp, controller, VehicleModel(cp)


def record(cp, source="vehicle"):
  tune = cp.lateralTuning.torque
  return {"source": source, "vehicle": cp.carFingerprint, "latAccelFactor": tune.latAccelFactor,
          "latAccelOffset": tune.latAccelOffset, "friction": tune.friction}


def frame(controller, vm, *, active=True, curvature=0.0, speed=20.0, steering_angle=0.0,
          steer_limited=False, steering_pressed=False):
  cs = car.CarState.new_message()
  cs.vEgo = speed
  cs.steeringAngleDeg = steering_angle
  cs.steeringPressed = steering_pressed
  return controller.update(active, cs, vm, log.VehicleParameters.new_message(),
                           steer_limited, curvature, False, 0.2)


class TestTorqueTuning(unittest.TestCase):
  def test_stock_values_leave_native_limits_unchanged(self):
    cp, controller, _ = native_controller()
    stock = from_record(record(cp))
    self.assertIs(stock.source, TorqueSource.VEHICLE)
    self.assertEqual(stock.vehicle, cp.carFingerprint)
    for selected, actual in zip(stock.upstream_update(), (controller.torque_params.latAccelFactor,
                                                          controller.torque_params.latAccelOffset,
                                                          controller.torque_params.friction), strict=True):
      self.assertAlmostEqual(selected, actual)
    original_limits = controller.pid.neg_limit, controller.pid.pos_limit
    controller.update_torque_parameters(*stock.upstream_update())
    for selected, actual in zip((controller.pid.neg_limit, controller.pid.pos_limit), original_limits, strict=True):
      self.assertAlmostEqual(selected, actual)

  def test_selected_complete_values_change_native_parameters_and_limits(self):
    cp, controller, _ = native_controller()
    selected = record(cp, "user")
    selected["latAccelFactor"] *= 1.2
    selected["latAccelOffset"] = 0.07
    selected["friction"] += 0.02
    tuning = from_record(selected)
    self.assertIs(tuning.source, TorqueSource.USER)
    initial_limit = controller.pid.pos_limit
    controller.update_torque_parameters(*tuning.upstream_update())
    self.assertAlmostEqual(controller.pid.pos_limit, initial_limit * 1.2, delta=1e-6)
    self.assertAlmostEqual(controller.pid.neg_limit, -controller.pid.pos_limit)
    self.assertAlmostEqual(controller.torque_params.latAccelOffset, 0.07)
    self.assertAlmostEqual(controller.torque_params.friction, selected["friction"])

  def test_inactive_nonzero_command_and_reengagement_use_native_buffer(self):
    cp, controller, vm = native_controller()
    learned = record(cp, "learned")
    learned["latAccelFactor"] *= 1.05
    controller.update_torque_parameters(*from_record(learned).upstream_update())
    for _ in range(controller.lat_accel_request_buffer_len):
      output, _, state = frame(controller, vm, active=False, curvature=0.001)
      self.assertEqual(output, 0.0)
      self.assertFalse(state.active)
    self.assertTrue(all(math.isclose(value, 0.4, abs_tol=1e-6) for value in controller.lat_accel_request_buffer))
    output, _, state = frame(controller, vm, curvature=0.001)
    self.assertTrue(state.active)
    self.assertAlmostEqual(state.desiredLateralAccel, 0.4)
    self.assertTrue(math.isfinite(output))
    self.assertNotEqual(output, 0.0)

  def test_native_saturation_sets_then_clears_under_bounded_inputs(self):
    _, controller, vm = native_controller()
    for _ in range(100):
      output, _, state = frame(controller, vm, curvature=0.02)
    self.assertLessEqual(abs(output), controller.steer_max + 1e-6)
    self.assertTrue(state.saturated)
    self.assertAlmostEqual(controller.sat_time, controller.sat_limit)
    for _ in range(controller.lat_accel_request_buffer_len + 100):
      output, _, state = frame(controller, vm, curvature=0.0)
    self.assertLessEqual(abs(output), controller.steer_max + 1e-6)
    self.assertFalse(state.saturated)
    self.assertAlmostEqual(controller.sat_time, 0.0)

  def test_invalid_numeric_inputs_are_rejected(self):
    values = [("latAccelFactor", 0), ("latAccelFactor", -1), ("latAccelFactor", float("nan")),
              ("latAccelFactor", True), ("latAccelOffset", float("inf")), ("latAccelOffset", False),
              ("friction", -0.01), ("friction", float("nan")), ("friction", True), ("latAccelFactor", 10 ** 1000)]
    for field, value in values:
      with self.subTest(field=field, value=value):
        source = {"source": "vehicle", "vehicle": "test-platform", "latAccelFactor": 2.0,
                  "latAccelOffset": 0.0, "friction": 0.1}
        source[field] = value
        with self.assertRaises(ValueError):
          from_record(source)

  def test_incomplete_unknown_and_legacy_fields_are_rejected(self):
    source = {"source": "vehicle", "vehicle": "test-platform", "latAccelFactor": 2.0,
              "latAccelOffset": 0.0, "friction": 0.1}
    for extra in ("kp", "ki", "kd", "kf", "steeringAngleDeadzoneDeg", "unknown"):
      with self.subTest(extra=extra), self.assertRaises(ValueError):
        from_record(source | {extra: 1.0})
    with self.assertRaises(ValueError):
      from_record({key: value for key, value in source.items() if key != "friction"})
    with self.assertRaises(ValueError):
      from_record(source | {"source": "unrecognized"})
    with self.assertRaises(ValueError):
      TorqueTuning(TorqueSource.VEHICLE, "", 2.0, 0.0, 0.1)


if __name__ == "__main__":
  unittest.main()
