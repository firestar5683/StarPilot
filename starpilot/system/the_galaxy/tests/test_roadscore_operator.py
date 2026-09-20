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


class CurrentWorkerTests(unittest.TestCase):
  def test_current_resident_identity_seed_and_reused_pid(self):
    import json,os
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as directory:
      root=Path(directory);generated=root/'generated';generated.mkdir();proc=root/'proc';proc.mkdir()
      (proc/'stat').write_text('btime 1\n')
      def process(pid,parent,ticks,script):
        folder=proc/str(pid);folder.mkdir(exist_ok=True)
        fields=['S',str(parent)]+['0']*17+[str(ticks)]
        (folder/'stat').write_text(f'{pid} (python) '+' '.join(fields))
        (folder/'cmdline').write_bytes(b'python\0/data/openpilot/roadscore/'+script.encode()+b'\0')
      process(10,1,100,'prototype/power_worker.py');process(11,10,200,'experiments/ace_chestnut_20260916/ace_worker.py')
      worker=dict(pid=11,generation_seed=123,profile='prism',phase='READY')
      (generated/'resident_owner.json').write_text(json.dumps(dict(power_worker_pid=10,process_start_ticks='100')))
      (generated/'ace_worker_state.json').write_text(json.dumps(worker))
      (generated/'ace_initial.json').write_text(json.dumps(dict(generation_seed=123,prepared_profile='prism')))
      (generated/'worker_ready').write_text('ace')
      (generated/'worker_service.json').write_text(json.dumps(dict(pid=999,phase='Failed',composer='sa3')))
      self.assertEqual(operator.current_worker(root,proc),worker)
      obj=operator.Operator(root,device=True)
      with patch.object(operator,'current_worker',return_value=worker),patch.object(obj,'target',return_value={}):
        self.assertEqual(obj.status(True)['state'],'READY');self.assertEqual(obj.status(True)['composer'],'ace');self.assertEqual(obj.status(True)['generation_seed'],123)
        (generated/'busy').touch();self.assertEqual(obj.status(True)['state'],'GENERATING')
      (generated/'ace_initial.json').write_text(json.dumps(dict(generation_seed=124,prepared_profile='prism')))
      self.assertEqual(operator.current_worker(root,proc),{})
      worker['phase']='PREPARING';(generated/'ace_worker_state.json').write_text(json.dumps(worker))
      self.assertEqual(operator.current_worker(root,proc)['phase'],'PREPARING')
      process(10,1,101,'prototype/power_worker.py');self.assertEqual(operator.current_worker(root,proc),{})
      process(9,1,90,'prototype/worker_service.py');process(10,9,101,'prototype/power_worker.py')
      (generated/'worker_service.json').write_text(json.dumps(dict(pid=9,start_ticks='90')))
      self.assertEqual(operator.current_worker(root,proc)['phase'],'PREPARING')
      process(9,1,91,'prototype/worker_service.py');self.assertEqual(operator.current_worker(root,proc),{})

      process(10,1,100,'prototype/power_worker.py')
      os.utime(generated/'ace_worker_state.json',(0,0));self.assertEqual(operator.current_worker(root,proc),{})
      (proc/'11/cmdline').unlink();self.assertEqual(operator.current_worker(root,proc),{})

if __name__ == '__main__': unittest.main()
