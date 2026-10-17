"""Unprivileged manager process; EOF or expired heartbeats revoke root's lease."""
import json
import os
import signal
import subprocess
import sys
import threading
import time

from openpilot.starpilot.galaxy.companion import CompanionRegistry
from openpilot.starpilot.galaxy.hotspot import STATUS_PATH, bounded_json


def stop_worker(child):
  try:
    child.stdin.close()
  except OSError:
    pass
  try:
    child.wait(timeout=12)
  except subprocess.TimeoutExpired:
    pass  # The root worker independently expires its pipe lease.


def main():
  from openpilot.common.basedir import BASEDIR
  from openpilot.common.hardware import PC
  if PC or os.environ.get('OPENPILOT_PREFIX'):
    raise RuntimeError('Uplink requires the primary comma instance')
  registry = CompanionRegistry()
  stop = threading.Event()
  for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda *_: stop.set())
  child = None
  try:
    while not stop.is_set():
      try:
        hotspot = bounded_json(STATUS_PATH)
        enabled = registry.enabled() and hotspot.get('active') is True and 0 <= time.monotonic() - hotspot['updated'] < 10
        lease = registry.lease() if enabled else None
        if child is not None and (not lease or child.poll() is not None):
          stop_worker(child)
          child = None
        if lease and child is None:
          child = subprocess.Popen(['sudo', '-n', 'systemd-run', '--quiet', '--pipe', '--wait', '--collect',
                                    '--unit=starpilot-companion-uplink', '--property=TimeoutStopSec=8',
                                    '--property=KillMode=control-group', '--working-directory=' + str(BASEDIR),
                                    sys.executable, '-u', '-m', 'openpilot.starpilot.galaxy.companion_uplink_worker'],
                                   cwd=BASEDIR, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, bufsize=0)
        if child is not None:
          child.stdin.write(json.dumps({'lease': lease, 'updated': time.monotonic()}).encode() + b'\n')
          child.stdin.flush()
      except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        if child is not None:
          stop_worker(child)
          child = None
      stop.wait(1)
  finally:
    if child is not None:
      stop_worker(child)


if __name__ == '__main__':
  main()
