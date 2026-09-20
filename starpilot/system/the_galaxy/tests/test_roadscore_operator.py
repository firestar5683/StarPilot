import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
def load(name):
  spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module
operator = load('roadscore')

class OperatorTests(unittest.TestCase):
  def test_validation(self):
    for value in [True, 1.5, -501, 1501, float('nan'), '100']:
      with self.assertRaises(ValueError): operator.validate_settings({'latency_ms': value})
    for value in [{'profile': 'circuit'}, {'seed': 12}, []]:
      with self.assertRaises(ValueError): operator.validate_settings(value)
    self.assertEqual(operator.validate_settings({'latency_ms': 120}), {'latency_ms': 120})

  def test_unavailable_does_not_imply_safe(self):
    with tempfile.TemporaryDirectory() as directory:
      obj = operator.Operator(Path(directory), device=False)
      status = obj.status(True)
      self.assertTrue(status['locked'])
      self.assertFalse(status['can_prepare'])
      self.assertIsNone(status['latency_ms'])
      with self.assertRaises(ValueError): obj.operate('prepare', {}, True)

  def test_onroad_denied(self):
    obj = operator.Operator(device=False)
    with self.assertRaises(ValueError): obj.operate('settings', {'profile': 'aurora'}, False)

class AppliedSettingsTests(unittest.TestCase):
  def test_actual_output_bound_save_and_profile(self):
    spec = importlib.util.spec_from_file_location('operator_output', Path(__file__).resolve().parents[4] / 'roadscore/prototype/operator_output.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as directory:
      obj = operator.Operator(Path(directory), device=True, offroad=lambda: True)
      obj.output_owner = module.OutputOwner(Path(directory), lambda: True, output_provider=lambda: {'id':'synthetic-speaker','name':'Test','connected':True,'muted':False})
      module.playback_process_active=lambda:False
      self.assertFalse(obj.status(True)['can_prepare'])
      obj.operate('settings', {'latency_ms':180}, True)
      self.assertEqual(obj.status(True)['latency_ms'],180)
      with self.assertRaises(ValueError):obj.operate('settings', {'profile':'aurora'}, True)
      self.assertEqual(obj.status(True)['selected_profile'],'prism')
      with module.lease(Path(directory)/'generated/operator.lock'):
        with self.assertRaises(ValueError): obj.operate('settings',{'profile':'prism'},True)
      with self.assertRaises(ValueError):obj.operate('prepare',{'seed':17},True)

if __name__ == '__main__': unittest.main()
