"""Source-class fault seam; native imports and real Params are not exercised."""
import ast
from pathlib import Path
import pytest


def manager_class():
  tree = ast.parse((Path(__file__).parents[1] / 'model_manager.py').read_text())
  names = {'MODEL_LAB_ACCELERATOR', 'ALLOW_GPU_DOWNLOAD_WITHOUT_GPU_PARAM',
           'DOWNLOAD_PROGRESS_PARAM', 'MODEL_DOWNLOAD_PARAM', 'MODEL_LAB_DOWNLOAD_PARAM',
           'DEFAULT_MODEL_KEY', 'MODEL_KEY_CANONICAL_MAP'}
  nodes = [n for n in tree.body if
           isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets) or
           isinstance(n, ast.FunctionDef) and n.name in {'canonical_model_key', 'is_builtin_model_key'} or
           isinstance(n, ast.ClassDef) and n.name == 'ModelManager']
  ns = {'Path': Path, 'model_accelerator_artifact_metadata': lambda *args: {}}
  exec(compile(ast.Module(body=nodes, type_ignores=[]), 'model_manager.py', 'exec'), ns)
  return ns['ModelManager']


class FaultParams:
  def __init__(self, cleanup_fault=False):
    self.cleanup_fault = cleanup_fault
  def get_bool(self, key):
    return False
  def put(self, *args):
    raise OSError('synthetic Params write failure')
  def remove(self, *args):
    if self.cleanup_fault:
      raise OSError('synthetic Params removal failure')


@pytest.mark.parametrize('cleanup_fault', [False, True])
@pytest.mark.parametrize('operation', ['single', 'all', 'accelerator'])
def test_failed_download_releases_refresh_gate(cleanup_fault, operation):
  cls = manager_class()
  manager = cls.__new__(cls)
  manager.downloading_model = False
  manager.params_memory = FaultParams(cleanup_fault)
  if operation == 'all':
    manager._download_all_models = lambda allow: manager._download_model('rdf43', allow)
    call = manager.download_all_models
  elif operation == 'accelerator':
    # Failure at upstream artifact metadata lookup; cleanup must release the gate.
    def fail():
      raise OSError('synthetic hardware lookup failure')
    cls.download_model_accelerator.__globals__['model_accelerator_artifact_metadata'] = lambda *args: fail()
    call = lambda: manager.download_model_accelerator('gpu')
  else:
    call = lambda: manager.download_model('rdf43')
  with pytest.raises(OSError):
    call()
  assert manager.downloading_model is False


def test_error_releases_the_download_gate_even_for_404():
  tree = ast.parse((Path(__file__).parents[1] / 'download_functions.py').read_text())
  node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'handle_error')

  class Params:
    def __init__(self):
      self.values = {}
      self.removed = []
    def put(self, key, value):
      self.values[key] = value
    def remove(self, key):
      self.removed.append(key)
      self.values.pop(key, None)

  ns = {'delete_file': lambda path: None}
  exec(compile(ast.Module(body=[node], type_ignores=[]), 'download_functions.py', 'exec'), ns)
  params = Params()
  ns['handle_error'](None, 'Failed: Server error (404)', 'error', 'ModelToDownload', 'ModelDownloadProgress', params)
  assert params.removed == ['ModelToDownload'], 'a 404 must not strand the download gate'
  assert params.values['ModelDownloadProgress'] == 'Failed: Server error (404)'
  # Missing params must not raise; callers pass None when there is no gate to release.
  ns['handle_error'](None, 'Registration failed', 'error', None, None, None)
