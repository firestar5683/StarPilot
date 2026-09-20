"""Exclusive Mac showcase ownership while the compiled camera port is global."""
from contextlib import contextmanager
import errno
import fcntl
import os
from pathlib import Path
import socket


class ReplayBusy(RuntimeError):
  pass


def check_camera_port():
  """Check the existing IPv4 ZMQ publisher bind without connecting or sending."""
  try:
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as probe:
      # Match a normal listening socket's restart behavior after TIME_WAIT.
      probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
      probe.bind(('0.0.0.0',9000))
  except OSError as error:
    if error.errno==errno.EADDRINUSE:
      raise ReplayBusy('Mac replay camera port 9000 is already in use. Close the existing Mac replay before starting another.') from None
    raise ReplayBusy('Cannot verify Mac replay camera port 9000: '+str(error)) from error


@contextmanager
def mac_replay_lease(root, *, port_check=None):
  """Hold this descriptor until parent cleanup ends; children never inherit it."""
  path=Path(root)/'generated/mac_showcase.lock'
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('a+') as lease:
    os.set_inheritable(lease.fileno(),False)
    try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
      raise ReplayBusy('A Mac RoadScore replay is already running. Close its existing demo before starting another.') from None
    try:
      (check_camera_port if port_check is None else port_check)()
      yield lease
    finally:fcntl.flock(lease,fcntl.LOCK_UN)


def preflight(root):
  """Advisory check before paired launch; the Mac parent later holds its lease."""
  with mac_replay_lease(root):pass
