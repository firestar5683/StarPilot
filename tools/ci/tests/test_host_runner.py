import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.ci import run_host_tests


class TestHostTestIsolation(unittest.TestCase):
  def test_pytest_selection_finds_nested_files_with_top_level_functions(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      nested = root / 'openpilot/starpilot/example/tests'
      nested.mkdir(parents=True)
      (nested / 'test_mixed.py').write_text('''def test_plain(): pass
async def test_async(): pass
class TestCase:
  def test_method(self): pass
class TestPlain:
  def test_method(self): pass
def helper():
  def test_inner(): pass
''')
      (nested / 'test_classonly.py').write_text('class TestPlain:\n  def test_method(self): pass\n')
      self.assertEqual(run_host_tests.pytest_files(root), [
        'openpilot/starpilot/example/tests/test_classonly.py',
        'openpilot/starpilot/example/tests/test_mixed.py',
      ])

  def test_pytest_mode_uses_disposable_state_and_selected_files(self):
    selected = ['openpilot/starpilot/example/tests/test_mixed.py']
    calls = []

    def invoke(command, *, cwd, env, check):
      calls.append((command, cwd, env, check))
      self.assertTrue(Path(env['PARAMS_ROOT']).is_dir())
      self.assertTrue(env['OPENPILOT_PREFIX'].startswith('starpilot-host-'))
      return SimpleNamespace(returncode=0)

    with patch.object(run_host_tests, 'pytest_files', return_value=selected), \
         patch.object(run_host_tests.subprocess, 'run', side_effect=invoke):
      self.assertEqual(run_host_tests.main(['--pytest']), 0)
    self.assertEqual(calls[0][0], [run_host_tests.sys.executable, '-m', 'pytest', '-q', '--import-mode=importlib', *selected])
    self.assertFalse(Path(calls[0][2]['PARAMS_ROOT']).exists())

  def test_duplicate_module_names_are_both_collected(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      for package in ('first', 'second'):
        folder = root / 'openpilot/starpilot' / package / 'tests'
        folder.mkdir(parents=True)
        (folder / 'test_owner.py').write_text('def test_valid(): assert True\n')
      selected = run_host_tests.pytest_files(root)
      self.assertEqual(len(selected), 2)
      with patch.object(run_host_tests, 'ROOT', root), patch.object(run_host_tests, 'pytest_files', return_value=selected):
        self.assertEqual(run_host_tests.main(['--pytest']), 0)

  def test_pytest_mode_fails_closed_when_nothing_is_discovered(self):
    with patch.object(run_host_tests, 'pytest_files', return_value=[]), \
         patch.object(run_host_tests.subprocess, 'run') as invoke:
      self.assertEqual(run_host_tests.main(['--pytest']), 5)
    invoke.assert_not_called()

  def test_child_failure_is_preserved_and_only_disposable_state_is_removed(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      real_params = root / 'existing-params'
      real_params.mkdir()
      saved = real_params / 'saved-choice'
      saved.write_text('preserve')
      report = root / 'child.json'
      runner = root / 'fixture.py'
      runner.write_text('''import json, os, pathlib, platform, sys
params = pathlib.Path(os.environ['PARAMS_ROOT'])
ipc = pathlib.Path('/tmp' if platform.system() == 'Darwin' else '/dev/shm') / ('msgq_' + os.environ['OPENPILOT_PREFIX'])
assert params.is_dir() and ipc.is_dir()
(params / 'write').write_text('temporary test write')
(ipc / 'message').write_text('temporary test message')
pathlib.Path(sys.argv[1]).write_text(json.dumps({'params': str(params), 'ipc': str(ipc), 'scale': os.environ['SCALE'], 'args': sys.argv[2:]}))
sys.exit(7)
''')
      with patch.object(run_host_tests, 'RUNNER', runner), \
           patch.dict(os.environ, {'PARAMS_ROOT': str(real_params), 'OPENPILOT_PREFIX': 'existing', 'SCALE': 'auto'}):
        self.assertEqual(run_host_tests.main([str(report), '--json-output', 'result.json']), 7)
        self.assertEqual(os.environ['PARAMS_ROOT'], str(real_params))
        self.assertEqual(os.environ['OPENPILOT_PREFIX'], 'existing')
      child = json.loads(report.read_text())
      self.assertNotEqual(child['params'], str(real_params))
      self.assertEqual(child['scale'], '1')
      self.assertEqual(child['args'], ['--json-output', 'result.json'])
      self.assertFalse(Path(child['params']).exists())
      self.assertFalse(Path(child['ipc']).exists())
      self.assertEqual(saved.read_text(), 'preserve')


if __name__ == '__main__':
  unittest.main()
