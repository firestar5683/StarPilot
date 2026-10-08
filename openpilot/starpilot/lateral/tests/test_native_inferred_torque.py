"""Real Params and exact Ioniq TorqueHost override/reset regression."""
from pathlib import Path
import unittest

from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.car_helpers import interfaces
from openpilot.starpilot.lateral.torque_runtime import TorqueHost, read_settings, runtime_enabled, production_supported_cp, manual_overrides_present
from openpilot.starpilot.lateral.torque_tuning import TorqueSource
from openpilot.starpilot.ui.torque_feature import TorqueFeature
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest


class TestNativeInferredTorque(unittest.TestCase):
  def test_saved_deviation_and_individual_reset_use_actual_vehicle_tune(self):
    with OpenpilotPrefix():
      params = Params()
      cp = interfaces['HYUNDAI_IONIQ_6'].get_non_essential_params('HYUNDAI_IONIQ_6')
      self.assertFalse(runtime_enabled(cp, params))
      self.assertFalse(manual_overrides_present(cp, params))
      host = TorqueHost(params, cp, allow_learning=False)
      stock = host.vehicle
      params.put('SteerLatAccel', stock.lat_accel_factor * 1.1, block=True)
      params.put('SteerFriction', min(stock.friction + 0.03, max(0.1, 2.0 * stock.friction), 1.0), block=True)
      self.assertTrue(manual_overrides_present(cp, params))
      self.assertTrue(runtime_enabled(cp, params))
      host.settings = read_settings(params, stock, allow_learning=False)
      self.assertIsNotNone(host.settings.user_factor)
      selected = host._select(None, 1)
      self.assertEqual(selected.source, TorqueSource.USER)
      self.assertEqual(selected.lat_accel_factor, stock.lat_accel_factor * 1.1)
      owner = type('EditorOwner', (), {})()
      owner.params = params
      owner.authority = lambda group: True
      owner.vehicle_fingerprint = lambda: stock.vehicle
      owner.vehicle_params = lambda: cp
      cap = (stock.vehicle, str(cp.brand), str(cp.steerControlType), str(cp.lateralTuning.which()),
             bool(cp.dashcamOnly), stock.lat_accel_factor, stock.lat_accel_offset, stock.friction)
      owner._capability = lambda group: cap
      def raw(key):
        path = Path(params.get_param_path(key))
        return path.read_bytes() if path.exists() else None
      owner._raw = raw
      owner._readable = lambda key: True
      owner._dependents = lambda *keys: tuple((key, raw(key)) for key in keys)
      editor = TorqueFeature(owner)
      valid, rows = editor.rows(cap, True)
      self.assertTrue(valid)
      row = next(row for row in rows if row.key == 'torque:factor:reset')
      request = FeatureSettingsRequest(row.key, row.source, 'Reset', vehicle_fingerprint=stock.vehicle,
                                      capability=cap, dependencies=row.dependencies)
      self.assertTrue(editor.apply(request))
      host.settings = read_settings(params, stock, allow_learning=False)
      self.assertIsNone(host.settings.user_factor)
      self.assertEqual(host._select(None, 1).lat_accel_factor, stock.lat_accel_factor)
      self.assertEqual(host.settings.user_friction, min(stock.friction + 0.03, max(0.1, 2.0 * stock.friction), 1.0))
      valid, rows = editor.rows(cap, True)
      row = next(row for row in rows if row.key == 'torque:friction:reset')
      self.assertTrue(editor.apply(FeatureSettingsRequest(row.key, row.source, 'Reset', vehicle_fingerprint=stock.vehicle,
                                                          capability=cap, dependencies=row.dependencies)))
      host.settings = read_settings(params, stock, allow_learning=False)
      self.assertEqual(host._select(None, 1), stock)
      self.assertFalse(manual_overrides_present(cp, params))
  def test_production_scope_does_not_offer_unconsumed_toyota_overrides(self):
    from unittest.mock import patch
    with OpenpilotPrefix(), patch.dict('os.environ', {'TORQUE_REPLAY_RUNTIME': '0'}):
      params = Params()
      cp = interfaces['TOYOTA_COROLLA_TSS2'].get_non_essential_params('TOYOTA_COROLLA_TSS2')
      self.assertFalse(production_supported_cp(cp))
      self.assertFalse(runtime_enabled(cp, params))

  def test_default_numeric_snapshot_preserves_both_controller_startups_and_learning_policy(self):
    from unittest.mock import patch
    from openpilot.common.realtime import DT_CTRL
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
    from openpilot.starpilot.lateral.controller_selection import ControllerMode, read_selection, replace_mode, learning_allowed
    import json
    with OpenpilotPrefix(), patch.dict('os.environ', {'TORQUE_REPLAY_RUNTIME': '0'}):
      params = Params()
      cp = interfaces['HYUNDAI_IONIQ_6'].get_non_essential_params('HYUNDAI_IONIQ_6')
      ci = interfaces['HYUNDAI_IONIQ_6'](cp)
      def snapshot(controller):
        tune = controller.torque_params
        return (controller.controller_mode, controller.controller_policy, tune.latAccelFactor,
                tune.latAccelOffset, tune.friction, controller.pid.pos_limit, controller.pid.neg_limit)
      for mode in (ControllerMode.STANDARD, ControllerMode.STARPILOT):
        with self.subTest(mode=mode):
          params.put('LateralControllerSelection', json.loads(replace_mode(None, cp, mode)), block=True)
          params.put_bool('ForceAutoTuneOff', False, block=True)
          selected = read_selection(params, cp)
          baseline = LatControlTorque(cp.as_reader(), ci, DT_CTRL, controller_mode=selected.mode)
          expected_learning = learning_allowed(params, cp, selection=selected)
          self.assertEqual(expected_learning, mode == ControllerMode.STANDARD)
          params.put('SteerLatAccel', float(cp.lateralTuning.torque.latAccelFactor), block=True)
          params.put('SteerFriction', float(cp.lateralTuning.torque.friction), block=True)
          self.assertFalse(runtime_enabled(cp, params))
          self.assertFalse(manual_overrides_present(cp, params))
          current = LatControlTorque(cp.as_reader(), ci, DT_CTRL, controller_mode=selected.mode)
          self.assertEqual(snapshot(current), snapshot(baseline))
          self.assertEqual(learning_allowed(params, cp, selection=selected), expected_learning)
          # torqued's cache admission predicate remains exactly the controller
          # learning policy when saved fields equal the supplied tune.
          self.assertEqual(not expected_learning or manual_overrides_present(cp, params), not expected_learning)


if __name__ == '__main__':
  unittest.main()
