"""Actual source transitions must not silently alter vehicle startup limits."""

from dataclasses import replace
from unittest import mock
import unittest

from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR as HYUNDAI
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral.torque_runtime import TorqueHost
from openpilot.starpilot.lateral.torque_tuning import TorqueSource


class TestTorqueApplication(unittest.TestCase):
  def controller(self, vehicle):
    cp = interfaces[vehicle].get_non_essential_params(vehicle)
    controller = LatControlTorque(cp.as_reader(), interfaces[vehicle](cp), DT_CTRL)
    return TorqueHost(Params(), cp), controller

  def test_initial_vehicle_preserves_ioniq_startup_and_explicit_equal_source_updates(self):
    with OpenpilotPrefix():
      for source in (TorqueSource.LEARNED, TorqueSource.USER):
        with self.subTest(source=source):
          host, controller = self.controller(HYUNDAI.HYUNDAI_IONIQ_6)
          with mock.patch.object(controller, 'update_torque_parameters', wraps=controller.update_torque_parameters) as update:
            initial_limit = controller.pid.pos_limit
            for _ in range(3):
              self.assertFalse(host.apply(controller, host.vehicle))
            update.assert_not_called()
            self.assertEqual(controller.pid.pos_limit, initial_limit)
            self.assertAlmostEqual(initial_limit, 3.0)
            selected = replace(host.vehicle, source=source)
            self.assertTrue(host.apply(controller, selected))
            self.assertAlmostEqual(controller.pid.pos_limit, 3.0 * 1.22, places=6)
            self.assertFalse(host.apply(controller, selected))
            self.assertEqual(update.call_count, 1)
            self.assertAlmostEqual(controller.torque_params.latAccelFactor, 3.0 * 1.22, places=6)

  def test_changed_values_fallback_and_new_controller_do_not_inherit_application(self):
    with OpenpilotPrefix():
      host, controller = self.controller(HYUNDAI.HYUNDAI_IONIQ_6)
      custom = replace(host.vehicle, source=TorqueSource.USER, lat_accel_factor=3.3, friction=0.12)
      self.assertTrue(host.apply(controller, custom))
      self.assertAlmostEqual(controller.torque_params.latAccelFactor, 3.3 * 1.22, places=6)
      self.assertTrue(host.apply(controller, host.vehicle))
      self.assertAlmostEqual(controller.torque_params.latAccelFactor, 3.0 * 1.22, places=6)
      self.assertAlmostEqual(controller.torque_params.friction, 0.09, places=6)
      # A fallback restores values through the normal update API. It does not
      # rewind the controller's history to its pre-update initialization state.
      self.assertAlmostEqual(controller.pid.pos_limit, 3.0 * 1.22, places=6)
      self.assertFalse(host.apply(controller, host.vehicle))
      _, other = self.controller(HYUNDAI.HYUNDAI_IONIQ_6)
      self.assertFalse(host.apply(other, host.vehicle))
      self.assertAlmostEqual(other.pid.pos_limit, 3.0)
      self.assertTrue(host.apply(other, custom))

  def test_vehicle_only_samples_do_not_unlock_limit(self):
    with OpenpilotPrefix():
      host, controller = self.controller(HYUNDAI.HYUNDAI_IONIQ_6)
      # Inactive or malformed saved settings return the exact vehicle source.
      sm = mock.Mock()
      sm.all_checks.return_value = False
      host.params.put_bool('AdvancedLateralTune', True, block=True)
      host.params.put('TorqueOverrideDocument', {'invalid': True}, block=True)
      for now, active in ((1_000_000_000, False), (1_010_000_000, True), (2_000_000_000, True)):
        tune = host.sample(sm, now_ns=now, lat_active=active)
        self.assertEqual(tune, host.vehicle)
        self.assertFalse(host.apply(controller, tune))
        self.assertAlmostEqual(controller.pid.pos_limit, 3.0)

  def test_inactive_fallback_and_failed_application_are_not_cached_as_success(self):
    with OpenpilotPrefix():
      host, controller = self.controller(HYUNDAI.HYUNDAI_IONIQ_6)
      custom = replace(host.vehicle, source=TorqueSource.USER, lat_accel_factor=3.3, friction=0.12)
      with mock.patch.object(controller, 'update_torque_parameters', side_effect=ValueError('rejected')):
        with self.assertRaises(ValueError):
          host.apply(controller, custom)
      self.assertTrue(host.apply(controller, custom))
      self.assertAlmostEqual(controller.torque_params.latAccelFactor, 3.3 * 1.22, places=6)
      fallback = host.sample(mock.Mock(), now_ns=1_000_000_000, lat_active=False)
      self.assertEqual(fallback, host.vehicle)
      self.assertTrue(host.apply(controller, fallback))
      self.assertAlmostEqual(controller.torque_params.latAccelFactor, 3.0 * 1.22, places=6)
      self.assertAlmostEqual(controller.torque_params.friction, 0.09, places=6)

  def test_non_ioniq_controller_and_cross_vehicle_rejection(self):
    with OpenpilotPrefix():
      host, controller = self.controller(TOYOTA.TOYOTA_COROLLA_TSS2)
      original = (controller.pid.pos_limit, controller.pid.neg_limit)
      self.assertFalse(host.apply(controller, host.vehicle))
      self.assertEqual((controller.pid.pos_limit, controller.pid.neg_limit), original)
      self.assertTrue(host.apply(controller, replace(host.vehicle, source=TorqueSource.USER)))
      self.assertEqual((controller.pid.pos_limit, controller.pid.neg_limit), original)
      with self.assertRaises(ValueError):
        host.apply(controller, replace(host.vehicle, vehicle='HYUNDAI_IONIQ_6'))


if __name__ == '__main__':
  unittest.main()
