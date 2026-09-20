"""Local regression for the session descriptor inherited by detached workers."""
import fcntl
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import unittest


class NativeReceiverLockTests(unittest.TestCase):
  def test_every_background_child_closes_session_descriptor(self):
    source = Path(__file__).with_name('native_receiver.sh').read_text()
    launches = [line for line in source.splitlines() if line.rstrip().endswith(' &')]
    self.assertEqual(len(launches), 3)
    for line in launches:
      self.assertIn('9>&-', line, line)
    self.assertIn('resident_keep=1', source)
    self.assertNotIn('rm -f generated/native_session.lock', source)

  def test_live_child_cannot_retain_exited_receivers_lock(self):
    source = Path(__file__).with_name('native_receiver.sh').read_text()
    launch = next(line for line in source.splitlines() if 'setsid env ' in line)
    # Exercise the exact fd-close redirection on the resident launch locally.
    redirect = next(token for token in launch.split() if token == '9>&-')
    with tempfile.TemporaryDirectory() as directory:
      lock = Path(directory) / 'session.lock'
      child_pid = Path(directory) / 'child.pid'
      acquire = 'import fcntl; fcntl.flock(9, fcntl.LOCK_EX | fcntl.LOCK_NB)'
      script = f'''exec 9>{shlex.quote(str(lock))}
{shlex.quote(sys.executable)} -c {shlex.quote(acquire)}
sleep 30 {redirect} </dev/null >/dev/null 2>&1 &
echo $! >{shlex.quote(str(child_pid))}
'''
      subprocess.run(['bash', '-c', script], check=True, timeout=5)
      pid = int(child_pid.read_text())
      try:
        os.kill(pid, 0)  # resident surrogate stays warm/alive
        with lock.open('w') as stream:
          fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
      finally:
        os.kill(pid, signal.SIGTERM)


if __name__ == '__main__':
  unittest.main()
