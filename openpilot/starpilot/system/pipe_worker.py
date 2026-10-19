"""Shared plumbing for the root workers that unprivileged daemons lease over a pipe.

The daemon starts the worker with ``spawn``. EOF on the worker's stdin, a missed heartbeat or SIGTERM ends the
lease, and the worker then removes only what it created (interfaces it marked with its own alias).
"""
from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path


def spawn(unit: str, module: str, popen=subprocess.Popen):
  from openpilot.common.basedir import BASEDIR
  return popen(['sudo', '-n', 'systemd-run', '--quiet', '--pipe', '--wait', '--collect', f'--unit={unit}',
                '--property=TimeoutStopSec=8', '--property=KillMode=control-group', '--working-directory=' + str(BASEDIR),
                sys.executable, '-u', '-m', module], cwd=BASEDIR,
               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, close_fds=True)


def owned(interface: str, alias: str) -> bool:
  try:
    return Path(f'/sys/class/net/{interface}/ifalias').read_text().strip() == alias
  except FileNotFoundError:
    return False


def claim(runtime: Path, name: str) -> int:
  """Root check, a private runtime directory and its lock; returns the lock's file descriptor."""
  if os.geteuid() != 0:
    raise RuntimeError(f'{name} requires network administration privileges')
  os.umask(0o077)
  runtime.mkdir(mode=0o700, exist_ok=True)
  if runtime.is_symlink() or runtime.stat().st_uid != 0:
    raise RuntimeError(f'Unsafe {name} runtime directory')
  fd = os.open(runtime / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
  fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
  return fd


def stop_event() -> threading.Event:
  stop = threading.Event()
  signal.signal(signal.SIGTERM, lambda *_: stop.set())
  signal.signal(signal.SIGINT, lambda *_: stop.set())
  return stop
