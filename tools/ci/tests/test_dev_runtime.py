import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.host_runtime import HostRuntime, parse


class TestDeveloperRuntime(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name) / 'source with spaces'
    self.root.mkdir()
    self.git('init', '-q')
    self.git('config', 'user.email', 'test@example.invalid')
    self.git('config', 'user.name', 'Test')
    (self.root / '.gitignore').write_text('.host_runtime/\n*.so\n')
    (self.root / 'source.py').write_text('original\n')
    self.git('add', '.')
    self.git('commit', '-qm', 'fixture')
    self.runtime = HostRuntime(self.root, 'shared', system='Darwin', machine='arm64')

  def git(self, *args):
    return subprocess.check_output(['git', *args], cwd=self.root, text=True)

  def test_sync_includes_local_edits_and_untracked_but_not_device_artifacts(self):
    (self.root / 'source.py').write_text('local edit\n')
    (self.root / 'new.py').write_text('new\n')
    (self.root / 'native.so').write_bytes(b'device binary')
    index_before = hashlib.sha256((self.root / '.git/index').read_bytes()).hexdigest()
    with self.runtime.locked():
      self.runtime.sync()
    self.assertEqual((self.runtime.work / 'source.py').read_text(), 'local edit\n')
    self.assertTrue((self.runtime.work / 'new.py').is_file())
    self.assertFalse((self.runtime.work / 'native.so').exists())
    self.assertFalse((self.runtime.work / '.git').is_symlink())
    self.assertEqual(hashlib.sha256((self.root / '.git/index').read_bytes()).hexdigest(), index_before)
    subprocess.check_call(['git', 'add', 'source.py'], cwd=self.runtime.work)
    self.assertEqual(hashlib.sha256((self.root / '.git/index').read_bytes()).hexdigest(), index_before)

  def test_resync_removes_deleted_source_and_keeps_host_builds_incremental(self):
    self.runtime.sync()
    native = self.runtime.work / 'native.so'
    native.write_bytes(b'host binary')
    source = self.runtime.work / 'source.py'
    before = source.stat().st_mtime_ns
    self.runtime.sync()
    self.assertEqual(source.stat().st_mtime_ns, before)
    (self.root / 'source.py').unlink()
    self.runtime.sync()
    self.assertFalse(source.exists())
    self.assertEqual(native.read_bytes(), b'host binary')

  def test_sync_skips_tracked_native_outputs_and_preserves_host_builds(self):
    artifacts = ('native.a', 'native.so', 'native.so.1', 'native.dylib', 'native.o', 'native.os')
    for name in artifacts:
      (self.root / name).write_bytes(b'device binary')
    self.git('add', '-f', *artifacts)
    self.runtime.sync()
    for name in artifacts:
      self.assertFalse((self.runtime.work / name).exists(), name)
    native = self.runtime.work / 'native.a'
    native.write_bytes(b'host binary')
    self.runtime.sync()
    self.assertEqual(native.read_bytes(), b'host binary')

  def test_ui_build_prepares_mpc_import_dependency(self):
    solver = 'openpilot/selfdrive/controls/lib/longitudinal_mpc_lib/c_generated_code/acados_ocp_solver_pyx.so'
    for command in ('c3', 'c4', 'onroad'):
      with self.subTest(command=command), patch('tools.host_runtime.run') as build:
        self.runtime.build(command, 4)
        self.assertIn(solver, build.call_args.args[0])

  def test_cache_environment_ignores_external_imports_and_settings(self):
    with patch.dict(os.environ, PYTHONPATH='/elsewhere', PARAMS_ROOT='/real/params', OPENPILOT_PREFIX='real', CC='cross-compiler'):
      env = self.runtime.environment()
    self.assertNotIn('/elsewhere', env['PYTHONPATH'])
    self.assertEqual(env['CC'], '/usr/bin/clang')
    self.assertTrue(Path(env['PARAMS_ROOT']).is_relative_to(self.runtime.cache))
    self.assertNotEqual(env['OPENPILOT_PREFIX'], 'real')
    second = HostRuntime(self.root, 'shared', system='Darwin', machine='arm64')
    cabana = HostRuntime(self.root, 'cabana', system='Darwin', machine='arm64')
    self.assertEqual(second.prefix, self.runtime.prefix)
    self.assertNotEqual(cabana.prefix, self.runtime.prefix)

  def test_cache_symlink_cannot_write_into_source(self):
    self.runtime.cache.mkdir(parents=True)
    self.runtime.work.symlink_to(self.root, target_is_directory=True)
    with self.assertRaises(RuntimeError):
      self.runtime.sync()
    self.assertEqual((self.root / 'source.py').read_text(), 'original\n')

  def test_cache_cannot_borrow_source_git_index(self):
    self.runtime.work.mkdir(parents=True)
    (self.runtime.work / '.git').symlink_to(self.root / '.git', target_is_directory=True)
    with self.assertRaisesRegex(RuntimeError, 'shared Git'):
      self.runtime.sync_git()

  def test_command_parsing_preserves_tool_arguments(self):
    self.assertEqual(parse(['c3', '8', '--demo']), ('c3', 8, ['--demo']))
    self.assertEqual(parse(['juggle', '4', '--demo']), ('plotjuggler', 4, ['--demo']))
    self.assertEqual(parse(['python', '-c', 'print(1)'])[2], ['-c', 'print(1)'])
    self.assertEqual(parse(['pytest', '-n', '2'])[2], ['-n', '2'])
    self.assertEqual(parse(['--help'])[0], 'help')
    for args in (['unknown'], ['c4', '0'], ['sync', '../oops'], ['sync', 'shared', 'extra']):
      with self.subTest(args=args), self.assertRaises(ValueError):
        parse(args)


if __name__ == '__main__':
  unittest.main()
