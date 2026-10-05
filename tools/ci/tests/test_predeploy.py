import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.ci.run_predeploy import STAGES, commands, run, main


class TestPredeploy(unittest.TestCase):
  def test_failure_is_preserved_and_later_check_does_not_run(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      marker = root / 'unexpected'
      plan = [('broken', [sys.executable, '-c', 'print("diagnostic"); raise SystemExit(7)']),
              ('later', [sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).touch()'])]
      self.assertEqual(run(plan, root / 'results'), 7)
      self.assertFalse(marker.exists())
      self.assertIn('diagnostic', (root / 'results/broken.log').read_text())
      self.assertEqual(json.loads((root / 'results/results.json').read_text())[0]['returncode'], 7)

  def test_recorded_download_is_explicit_and_both_variants_run(self):
    plan = commands(Path('/results'), Path('/cache'))
    self.assertEqual([name for name, _ in plan['recorded']], ['recorded-debug', 'recorded-release'])
    self.assertTrue(all('--download' not in command for _, command in plan['recorded']))
    self.assertTrue(all('--download' in command for _, command in commands(Path('/results'), Path('/cache'), True)['recorded']))

  def test_full_plan_builds_and_requires_native_protocols(self):
    plan = commands(Path('/results'), Path('/cache'))
    self.assertEqual(plan['build'][0][1][1:], ['-m', 'SCons', '-j4'])
    self.assertEqual([name for name, _ in plan['native']], [
      'test_panda_usb', 'test_pandad_canprotocol', 'test_aol_protocol', 'test_aol_wire', 'map-ipc'])
    self.assertIn('-race', plan['native'][-1][1])

  def test_full_plan_requires_unfiltered_process_replay(self):
    with patch('tools.ci.run_predeploy.os.cpu_count', return_value=8):
      plan = commands(Path('/results'), Path('/cache'))
    self.assertIn('replay', STAGES)
    self.assertEqual(plan['replay'], [('process-replay', [sys.executable,
      'openpilot/selfdrive/test/process_replay/test_processes.py', '-j', '8', '--output', '/results/process-replay'])])

  def test_default_run_includes_process_replay(self):
    with tempfile.TemporaryDirectory() as temporary, \
         patch.object(sys, 'argv', ['run_predeploy.py', '--output', str(Path(temporary) / 'results')]), \
         patch('tools.ci.run_predeploy.platform.system', return_value='Linux'), \
         patch('tools.ci.run_predeploy.run', return_value=0) as invoke:
      self.assertEqual(main(), 0)
      self.assertIn('process-replay', [name for name, _ in invoke.call_args.args[0]])

  def test_reports_cannot_be_overwritten(self):
    with tempfile.TemporaryDirectory() as temporary:
      with self.assertRaises(FileExistsError):
        run([], Path(temporary))


  def test_full_source_stage_does_not_inherit_fast_lint(self):
    with tempfile.TemporaryDirectory() as temporary, \
         patch.dict(os.environ, {'FAST': '1'}), \
         patch.object(sys, 'argv', ['run_predeploy.py', '--output', str(Path(temporary) / 'results'), '--stage', 'source']), \
         patch('tools.ci.run_predeploy.run', return_value=0) as invoke:
      self.assertEqual(main(), 0)
      self.assertNotIn('FAST', invoke.call_args.kwargs['environment'])
      self.assertIn('lint', [name for name, _ in invoke.call_args.args[0]])


  def test_native_stage_rejects_non_linux_before_running(self):
    with tempfile.TemporaryDirectory() as temporary, \
         patch.object(sys, 'argv', ['run_predeploy.py', '--output', str(Path(temporary) / 'results')]), \
         patch('tools.ci.run_predeploy.platform.system', return_value='Darwin'), \
         patch('tools.ci.run_predeploy.run') as invoke, \
         patch('sys.stderr'):
      with self.assertRaises(SystemExit) as error:
        main()
      self.assertEqual(error.exception.code, 2)
      invoke.assert_not_called()
