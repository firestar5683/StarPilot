import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from openpilot.starpilot.controller_extensions import ManualTurnInputs, configure_controller
from openpilot.starpilot.tests import test_vehicle_preferences as preferences_tests
from opendbc.car.ford.values import CAR


class TestControllerExtensions(unittest.TestCase):
  def test_real_saved_preference_default_and_disabled(self):
    from openpilot.common.params import Params
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      self.assertTrue(params.get('FordHumanTurnDetection', return_default=True))
      params.put_bool('FordHumanTurnDetection', False, block=True)
      self.assertFalse(params.get('FordHumanTurnDetection', return_default=True))

  def test_actual_model_owner_and_cached_preference(self):
    import openpilot.cereal.messaging as messaging
    from openpilot.common.params import Params
    message = messaging.new_message('modelV2')
    message.modelV2.meta.laneChangeState = 'laneChangeStarting'
    sm = SimpleNamespace(alive={'modelV2': True}, valid={'modelV2': True}, update=lambda timeout: None)

    class ModelReader:
      alive = sm.alive
      valid = sm.valid

      def update(self, timeout):
        sm.update(timeout)

      def __getitem__(self, key):
        return message.modelV2
    with patch.object(messaging, 'SubMaster', return_value=ModelReader()), patch.object(Params, 'get', return_value=True) as read:
      inputs = ManualTurnInputs(Params())
      self.assertEqual(inputs.update(), (True, True, True))
      for _ in range(99):
        inputs.update()
      self.assertEqual(read.call_count, 2)
      inputs.update()
      self.assertEqual(read.call_count, 3)
      sm.alive['modelV2'] = False
      self.assertEqual(inputs.update(), (True, True, False))

  def test_model_preview_freshness_delay_and_invalid_output(self):
    import openpilot.cereal.messaging as messaging
    from openpilot.selfdrive.modeld.constants import ModelConstants
    now = 10_000_000_000
    model = messaging.new_message('modelV2')
    model.modelV2.orientationRate.z = [20. * (value / 100.) for value in ModelConstants.T_IDXS]
    delay = messaging.new_message('lateralDelay')
    delay.lateralDelay.lateralDelay = .3
    class Reader:
      alive = {'modelV2': True, 'lateralDelay': True}
      valid = dict(alive)
      logMonoTime = {'modelV2': now, 'lateralDelay': now}
      def __getitem__(self, key):
        return model.modelV2 if key == 'modelV2' else delay.lateralDelay
    inputs = ManualTurnInputs.__new__(ManualTurnInputs)
    inputs.sm = Reader()
    with patch('openpilot.starpilot.controller_extensions.time.monotonic_ns', return_value=now):
      self.assertAlmostEqual(inputs.preview_curvature(20.), .003)
      inputs.sm.logMonoTime['lateralDelay'] = now - 1_000_000_001
      self.assertAlmostEqual(inputs.preview_curvature(20.), .002)
      for stamp in (0, now + 1, now - 100_000_001):
        inputs.sm.logMonoTime['modelV2'] = stamp
        self.assertIsNone(inputs.preview_curvature(20.))
      inputs.sm.logMonoTime['modelV2'] = now
      self.assertIsNone(inputs.preview_curvature(0.))
      model.modelV2.orientationRate.z = [float('nan')] * 33
      self.assertIsNone(inputs.preview_curvature(20.))

  def test_real_card_finalizes_then_binds_only_admitted_controller(self):
    harness = preferences_tests.TestVehicleStartupPreferences(methodName='test_only_exact_saved_opt_in_is_loaded')
    harness.setUp()
    self.addCleanup(harness.doCleanups)
    with patch('openpilot.starpilot.controller_extensions.messaging.SubMaster', return_value=SimpleNamespace()):
      host, _, published = harness.start(CAR.FORD_MUSTANG_MACH_E_MK1)
      self.assertFalse(published.passive)
      self.assertIsInstance(host.CI.CC.manual_turn_inputs, ManualTurnInputs)
      self.assertIs(host.CI.CC.manual_turn_inputs.params, harness.params)
      host, _, published = harness.start(CAR.FORD_MUSTANG_MACH_E_MK1, enabled=False)
      self.assertTrue(published.passive)
      self.assertIsNone(host.CI.CC.manual_turn_inputs)

  def test_standalone_controller_has_no_host_owner(self):
    from opendbc.car.ford.tests.test_three_ports import params
    from opendbc.car.ford.carcontroller import CarController
    from opendbc.car.ford.values import DBC
    from opendbc.car.ford.carstate import CarState
    from opendbc.car import structs
    cp = params(CAR.FORD_MUSTANG_MACH_E_MK1)
    controller = CarController(DBC[cp.carFingerprint], cp)
    state = CarState(cp)
    state.update(state.get_can_parsers(cp))
    state.out = structs.CarState().as_reader()
    controller.update(structs.CarControl().as_reader(), state, 0)
    self.assertIsNone(controller.manual_turn_inputs)
    cp.passive = True
    configure_controller(SimpleNamespace(CP=cp, CC=controller), SimpleNamespace())
    self.assertIsNone(controller.manual_turn_inputs)
