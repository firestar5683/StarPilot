import ast
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[5]


def test_android_auto_key_and_build_registration_are_explicit():
  keys = (ROOT / 'openpilot/common/params_keys.h').read_text()
  assert '{"AndroidAutoEnabled", {PERSISTENT | DONT_LOG, BOOL, "0"}}' in keys
  assert '{"BluetoothEnabled", {PERSISTENT, BOOL}}' in keys
  assert "openpilot/starpilot/system/android_auto/SConscript" in (ROOT / 'SConstruct').read_text()


def test_manager_keeps_missing_or_false_feature_off():
  source = (ROOT / 'openpilot/system/manager/process_config.py').read_text()
  tree = ast.parse(source)
  predicate = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'android_auto_enabled')
  scope = {'COMMA_HARDWARE': True, 'platform': SimpleNamespace(system=lambda: 'Linux'),
           'Params': object, 'car': SimpleNamespace(CarParams=object)}
  exec(compile(ast.Module(body=[predicate], type_ignores=[]), '<manager admission>', 'exec'), scope)
  class Params:
    def __init__(self, enabled): self.enabled = enabled
    def get_bool(self, key):
      assert key == 'AndroidAutoEnabled'
      return self.enabled
  admit = scope['android_auto_enabled']
  assert not admit(False, Params(False), None)
  assert admit(False, Params(True), None)
  scope['COMMA_HARDWARE'] = False
  assert not admit(False, Params(True), None)
  scope['COMMA_HARDWARE'] = True
  scope['platform'] = SimpleNamespace(system=lambda: 'Darwin')
  assert not admit(False, Params(True), None)
  assert 'PythonProcess("android_autod", "openpilot.starpilot.system.android_auto.daemon", android_auto_enabled' in source


def test_typed_preference_controls_actual_manager_admission(tmp_path, monkeypatch):
  from openpilot.common.params import Params
  from openpilot.system.manager import process_config

  params = Params(str(tmp_path))
  monkeypatch.setattr(process_config, 'COMMA_HARDWARE', True)
  monkeypatch.setattr(process_config.platform, 'system', lambda: 'Linux')
  process = process_config.managed_processes['android_autod']

  assert params.get_default_value('AndroidAutoEnabled') is False
  assert params.get('AndroidAutoEnabled') is None
  assert not process.should_run(False, params, None)
  params.put_bool('AndroidAutoEnabled', False, block=True)
  assert not process.should_run(True, params, None)
  params.put_bool('AndroidAutoEnabled', True, block=True)
  assert process.should_run(False, params, None)
  params.remove('AndroidAutoEnabled')
  assert not process.should_run(False, params, None)
  assert process.proc is None
