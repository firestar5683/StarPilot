"""Source-cache transitions that must not require a native build or device."""

import os
import fcntl
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from tools.host_runtime import HostRuntime


def git(root: Path, *args: str) -> None:
  subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)


class TestHostRuntimeSourceSync(unittest.TestCase):
  def setUp(self) -> None:
    self.temporary = tempfile.TemporaryDirectory()
    self.addCleanup(self.temporary.cleanup)
    self.root = Path(self.temporary.name) / 'source'
    self.root.mkdir()
    git(self.root, 'init', '-q')
    git(self.root, 'config', 'user.name', 'Host Runtime Test')
    git(self.root, 'config', 'user.email', 'host-runtime@example.invalid')
    (self.root / 'README').write_text('fixture\n')
    git(self.root, 'add', 'README')
    git(self.root, 'commit', '-qm', 'fixture')
    self.runtime = HostRuntime(self.root, 'shared', system='Darwin', machine='arm64')

  def test_same_size_and_mtime_edit_reaches_cache(self) -> None:
    source = self.root / 'README'
    self.runtime.sync()
    before = source.stat()
    source.write_text('changed\n')
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))

    self.runtime.sync()

    self.assertEqual((self.runtime.work / 'README').read_text(), 'changed\n')

  def test_tracked_child_replaced_by_file_reaches_cache(self) -> None:
    directory = self.root / 'path'
    directory.mkdir()
    (directory / 'child').write_text('old\n')
    git(self.root, 'add', 'path/child')
    git(self.root, 'commit', '-qm', 'child')
    self.runtime.sync()

    (directory / 'child').unlink()
    directory.rmdir()
    directory.write_text('new\n')
    self.runtime.sync()

    cached = self.runtime.work / 'path'
    self.assertTrue(cached.is_file())
    self.assertEqual(cached.read_text(), 'new\n')

  def test_tracked_file_replaced_by_child_reaches_cache(self) -> None:
    source = self.root / 'path'
    source.write_text('old\n')
    git(self.root, 'add', 'path')
    git(self.root, 'commit', '-qm', 'file')
    self.runtime.sync()

    source.unlink()
    source.mkdir()
    (source / 'child').write_text('new\n')
    self.runtime.sync()

    cached = self.runtime.work / 'path'
    self.assertTrue(cached.is_dir())
    self.assertEqual((cached / 'child').read_text(), 'new\n')

  def test_wrapper_sigkill_keeps_lock_until_child_exits(self) -> None:
    runtime = self.runtime
    runtime.work.mkdir(parents=True)
    (runtime.venv / 'bin').mkdir(parents=True)
    (runtime.venv / 'bin/python').symlink_to(sys.executable)
    child_pid_file = self.root / 'child.pid'
    source_root = Path(__file__).resolve().parents[3]
    wrapper_code = '''import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from tools.host_runtime import HostRuntime
runtime = HostRuntime(sys.argv[2], 'shared', system='Darwin', machine='arm64')
child = "import os,sys,time; from pathlib import Path; Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(30)"
with runtime.locked():
  runtime.launch('python', 1, ['-c', child, sys.argv[3]])
'''
    wrapper = subprocess.Popen([sys.executable, '-c', wrapper_code, str(source_root), str(self.root),
                                str(child_pid_file)], start_new_session=True)
    ipc = Path('/tmp') / f'msgq_{runtime.prefix}'
    lock_path = runtime.cache / 'lock'
    try:
      deadline = time.monotonic() + 5
      while not child_pid_file.exists() and wrapper.poll() is None and time.monotonic() < deadline:
        time.sleep(.02)
      self.assertTrue(child_pid_file.exists(), 'child did not start')
      wrapper.kill()
      wrapper.wait(timeout=3)
      with lock_path.open('a+') as contender:
        with self.assertRaises(BlockingIOError):
          fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
      try:
        os.killpg(wrapper.pid, signal.SIGTERM)
      except ProcessLookupError:
        pass
      if wrapper.poll() is None:
        wrapper.kill()
        wrapper.wait(timeout=3)
      deadline = time.monotonic() + 5
      while time.monotonic() < deadline:
        with lock_path.open('a+') as contender:
          try:
            fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
          except BlockingIOError:
            time.sleep(.02)
          else:
            fcntl.flock(contender, fcntl.LOCK_UN)
            break
      else:
        self.fail('owned child did not release the lock after stopping')
      if ipc.exists():
        shutil.rmtree(ipc)


if __name__ == '__main__':
  unittest.main()
