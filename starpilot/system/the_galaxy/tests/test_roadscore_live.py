import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('galaxy_live_operator', Path(__file__).resolve().parents[1] / 'roadscore.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class LiveTests(unittest.TestCase):
  def setUp(self):
    self.folder = tempfile.TemporaryDirectory()
    self.addCleanup(self.folder.cleanup)
    self.operator = module.Operator(root=Path(self.folder.name), device=True)
    self.controller = Mock()
    self.controller.status.return_value = {'available': True, 'enabled': False, 'can_enable': False, 'reason': 'Car baseline not authorized'}
    self.operator.live_owner = self.controller
    self.operator.target = Mock(side_effect=AssertionError('Bench/output owner must not be controlled'))

  def test_off_is_allowed_onroad_without_authorization_or_status(self):
    self.controller.status.side_effect = RuntimeError('Health snapshot unavailable')
    self.controller.set_enabled.return_value = {'enabled': False, 'state': 'STOPPING'}
    self.assertEqual(self.operator.operate('live', {'enabled': False}, False)['state'], 'STOPPING')
    self.controller.status.assert_not_called()
    self.controller.set_enabled.assert_called_once_with(False)
    self.operator.target.assert_not_called()

  def test_on_rejects_missing_authorization(self):
    with self.assertRaisesRegex(ValueError, 'Car baseline'):
      self.operator.operate('live', {'enabled': True}, False)
    self.controller.set_enabled.assert_not_called()

  def test_on_uses_controller_readiness_not_offroad_parameter(self):
    self.controller.status.return_value.update(can_enable=True)
    self.controller.set_enabled.return_value = {'enabled': True, 'state': 'PREPARING'}
    result = self.operator.operate('live', {'enabled': True}, False)
    self.assertEqual(result['state'], 'PREPARING')
    self.controller.set_enabled.assert_called_once_with(True)

  def test_invalid_payload_never_reaches_controller(self):
    for data in ({}, {'enabled': 1}, {'enabled': 'true'}, {'enabled': False, 'pid': 123}):
      with self.assertRaises(ValueError):self.operator.operate('live', data, True)
    self.controller.set_enabled.assert_not_called()

  def test_missing_backend_has_unknown_enabled_state(self):
    self.operator.live_owner = None
    state = self.operator.live_status()
    self.assertFalse(state['available']);self.assertFalse(state['can_enable'])
    self.assertIsNone(state['enabled'])
    with self.assertRaisesRegex(ValueError, 'not available'):
      self.operator.operate('live', {'enabled': True}, True)

  def test_other_controls_still_require_parked(self):
    with self.assertRaisesRegex(ValueError, 'parked'):
      self.operator.operate('prepare', {}, False)
    self.controller.set_enabled.assert_not_called()

if __name__ == '__main__':unittest.main()
