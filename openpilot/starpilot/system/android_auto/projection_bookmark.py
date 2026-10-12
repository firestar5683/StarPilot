"""Fresh bookmark requests to the native UI, which owns the bookmark publishers."""
import os
import socket
import time

DEFAULT_SOCKET = '/tmp/starpilot-projection-bookmark.sock'
MAX_AGE_NS = 1_000_000_000


class BookmarkSender:
  def __init__(self, path=DEFAULT_SOCKET):
    self.path = str(path)
    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    self.sock.setblocking(False)

  def send(self, car_state_ns):
    if type(car_state_ns) is not int or car_state_ns <= 0:
      return False
    try:
      self.sock.sendto(f'{time.monotonic_ns()}:{car_state_ns}'.encode(), self.path)
      return True
    except OSError:
      return False

  def close(self):
    self.sock.close()


class BookmarkReceiver:
  def __init__(self, path=DEFAULT_SOCKET):
    self.path = str(path)
    self.last_request_ns = 0
    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
      try:
        os.unlink(self.path)
      except FileNotFoundError:
        pass
      self.sock.bind(self.path)
      os.chmod(self.path, 0o600)
      self.sock.setblocking(False)
    except BaseException:
      self.sock.close()
      raise

  def drain(self, now_ns, car_state_ns, *, authorized):
    accepted = 0
    # Malformed or repeated input must not hold up the native UI's frame loop.
    for _ in range(8):
      try:
        raw = self.sock.recv(128)
      except BlockingIOError:
        break
      try:
        requested, source = (int(value) for value in raw.split(b':'))
      except ValueError:
        continue
      if (not authorized or not 0 < requested <= now_ns or requested <= self.last_request_ns or
          now_ns - requested > MAX_AGE_NS or source <= 0 or abs(car_state_ns - source) > MAX_AGE_NS):
        continue
      self.last_request_ns = requested
      accepted += 1
    return accepted

  def close(self):
    self.sock.close()
    try:
      os.unlink(self.path)
    except FileNotFoundError:
      pass
