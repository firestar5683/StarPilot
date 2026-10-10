"""Unprivileged manager process; a closed pipe revokes the root worker's lease."""
import json
import os
import select
import signal
import subprocess
import sys
import threading
import time

from openpilot.starpilot.galaxy.hotspot import HotspotSettings, STATUS_PATH, atomic_json


def main():
  from openpilot.common.basedir import BASEDIR
  from openpilot.common.hardware import PC
  if PC or os.environ.get('OPENPILOT_PREFIX'):
    raise RuntimeError('Hotspot requires the primary comma instance')
  settings = HotspotSettings()
  stop = threading.Event()
  signal.signal(signal.SIGINT, lambda *_: stop.set())
  signal.signal(signal.SIGTERM, lambda *_: stop.set())
  child, revision, buffer, last_reply = None, None, b'', 0.0
  runtime = {'active': False, 'state': 'disabled', 'reason': ''}
  try:
    while not stop.is_set():
      try:
        config = settings.read()
        revision = settings.revision(config)
        if not config['enabled']:
          if child is not None:
            child.stdin.close()
            child.wait(timeout=20)
            child.stdout.close()
            child = None
          runtime = {'active': False, 'state': 'disabled', 'reason': ''}
        else:
          if child is None:
            child = subprocess.Popen(['sudo', '-n', 'systemd-run', '--quiet', '--pipe', '--wait', '--collect',
                                      '--unit=starpilot-galaxy-hotspot', '--property=TimeoutStopSec=8',
                                      '--property=KillMode=control-group', '--working-directory=' + str(BASEDIR),
                                      sys.executable, '-u', '-m',
                                      'openpilot.starpilot.galaxy.hotspot_worker'], cwd=BASEDIR,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     close_fds=True)
            buffer = b''
            last_reply = time.monotonic()
            runtime = {'active': False, 'state': 'starting', 'reason': 'Starting hotspot service.'}
          if child.poll() is not None:
            raise RuntimeError('Worker exited')
          child.stdin.write(json.dumps(config).encode() + b'\n')
          child.stdin.flush()
          if select.select([child.stdout], [], [], 1)[0]:
            data = os.read(child.stdout.fileno(), 4097)
            if not data:
              raise RuntimeError('Worker disconnected')
            buffer += data
            if len(buffer) > 4096:
              raise ValueError('Oversized status')
            while b'\n' in buffer:
              line, buffer = buffer.split(b'\n', 1)
              runtime = json.loads(line)
              last_reply = time.monotonic()
          if time.monotonic() - last_reply > 20:
            raise RuntimeError('Worker unresponsive')
        atomic_json(STATUS_PATH, {**runtime, 'revision': runtime.get('revision', revision), 'updated': time.monotonic()})
      except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        if child is not None:
          if not child.stdin.closed:
            child.stdin.close()
          try:
            child.wait(timeout=20)
          except subprocess.TimeoutExpired:
            # Lease expiry is enforced independently inside the privileged worker.
            pass
          child.stdout.close()
          child = None
        atomic_json(STATUS_PATH, {'active': False, 'state': 'error', 'reason': 'Hotspot service unavailable.',
                                 'revision': revision, 'updated': time.monotonic()})
        stop.wait(15)
      stop.wait(2)
  finally:
    if child is not None and not child.stdin.closed:
      child.stdin.close()
    atomic_json(STATUS_PATH, {'active': False, 'state': 'disabled', 'reason': 'Hotspot service stopped.',
                             'revision': revision, 'updated': time.monotonic()})


if __name__ == '__main__':
  main()
