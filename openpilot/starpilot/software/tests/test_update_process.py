import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from openpilot.starpilot.software.fast_update import run


class TestUpdateProcess(unittest.TestCase):
  def setUp(self):
    self.temporary = tempfile.TemporaryDirectory()
    self.addCleanup(self.temporary.cleanup)
    self.directory = Path(self.temporary.name)

  def command(self, source):
    script = self.directory / 'command.py'
    script.write_text(source)
    return [sys.executable, '-u', str(script)]

  def test_output_and_failure(self):
    command = self.command("import sys\nprint('first')\nprint('last', file=sys.stderr)\nsys.exit(7)\n")
    with self.assertRaises(subprocess.CalledProcessError) as error:
      run(command, self.directory)
    self.assertEqual(error.exception.returncode, 7)
    self.assertEqual(error.exception.output, b'first\nlast\n')

  def test_progress_and_success(self):
    command = self.command("print('Receiving objects: 50%\\rReceiving objects: 100%')\nprint('done')\n")
    progress = []
    result = run(command, self.directory, progress.append)
    self.assertEqual(result, 'Receiving objects: 50%\rReceiving objects: 100%\ndone\n')
    self.assertEqual(progress, ['Receiving objects: 50%', 'Receiving objects: 100%'])

  def test_timeout_allows_lock_cleanup(self):
    command = self.command("""import signal
import time
from pathlib import Path

def terminate(*_):
  raise SystemExit(1)

signal.signal(signal.SIGTERM, terminate)
lock = Path('shallow.lock')
lock.touch()
print('locked')
try:
  time.sleep(60)
finally:
  lock.unlink()
""")
    with self.assertRaises(subprocess.TimeoutExpired) as error:
      run(command, self.directory, timeout=0.5)
    self.assertEqual(error.exception.output, b'locked\n')
    self.assertFalse((self.directory / 'shallow.lock').exists())

  def test_stubborn_command_is_killed(self):
    command = self.command("""import os
import signal
import time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
print(os.getpid())
time.sleep(60)
""")
    started = time.monotonic()
    with self.assertRaises(subprocess.TimeoutExpired) as error:
      run(command, self.directory, timeout=0.5)
    self.assertLess(time.monotonic() - started, 8)
    with self.assertRaises(ProcessLookupError):
      os.kill(int(error.exception.output.strip()), 0)

  def test_exited_parent_with_child_pipe_is_bounded(self):
    command = self.command("""import subprocess
import sys
import time
from pathlib import Path
subprocess.Popen([sys.executable, '-u', '-c', '''import signal
import time
from pathlib import Path
def terminate(*_):
  Path('child_stopped').touch()
  raise SystemExit(0)
signal.signal(signal.SIGTERM, terminate)
Path('child_ready').touch()
time.sleep(60)
'''])
while not Path('child_ready').exists():
  time.sleep(0.01)
print('parent exited')
""")
    started = time.monotonic()
    with self.assertRaises(subprocess.TimeoutExpired):
      run(command, self.directory, timeout=0.5)
    self.assertLess(time.monotonic() - started, 8)
    self.assertTrue((self.directory / 'child_stopped').exists())


if __name__ == '__main__':
  unittest.main()
