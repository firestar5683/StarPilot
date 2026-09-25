import errno
import json
import logging
import os
from pathlib import Path
import socket
import stat
import struct
import threading
import time

DEFAULT_SOCKET_PATH = Path(f'/tmp/starpilot-controllers-{os.getuid()}') / 'ui.sock'
MAX_BYTES = 65536
REQUEST_DEADLINE = 1.0
LOGGER = logging.getLogger(__name__)


class ControllerUnavailable(RuntimeError):
  pass


class ControllerBusy(ControllerUnavailable):
  pass


class ControllerDenied(PermissionError):
  pass


class ControllerInvalid(ValueError):
  pass


def _receive(peer, count):
  data = bytearray()
  while len(data) < count:
    part = peer.recv(count - len(data))
    if not part:
      raise ControllerUnavailable('Controller connection closed')
    data.extend(part)
  return bytes(data)


def _decode(data):
  def unique(pairs):
    result = {}
    for key, value in pairs:
      if key in result:
        raise ControllerInvalid('Duplicate controller field')
      result[key] = value
    return result
  return json.loads(data, object_pairs_hook=unique,
                    parse_constant=lambda _: (_ for _ in ()).throw(ControllerInvalid('Invalid controller value')))


def _encode(value):
  data = json.dumps(value, separators=(',', ':'), allow_nan=False).encode()
  if not 0 < len(data) <= MAX_BYTES:
    raise ControllerInvalid('Controller message exceeds limit')
  return data


def _request(payload, socket_path, timeout):
  encoded = _encode(payload)
  try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
      peer.settimeout(timeout)
      peer.connect(str(socket_path or DEFAULT_SOCKET_PATH))
      peer.sendall(struct.pack('!I', len(encoded)) + encoded)
      size = struct.unpack('!I', _receive(peer, 4))[0]
      if not 0 < size <= MAX_BYTES:
        raise ControllerUnavailable('Invalid controller response size')
      response = _decode(_receive(peer, size))
    if type(response) is not dict or set(response) != {'status', 'result'}:
      raise ControllerUnavailable('Invalid controller response')
    status, result = response['status'], response['result']
    if status == 'ok' and type(result) is dict:
      return result
    errors = {'invalid': ControllerInvalid, 'denied': ControllerDenied, 'busy': ControllerBusy}
    raise errors.get(status, ControllerUnavailable)(result if type(result) is str else 'Controller buttons are unavailable')
  except (ControllerInvalid, ControllerDenied, ControllerUnavailable):
    raise
  except (OSError, ValueError, RecursionError) as error:
    raise ControllerUnavailable('Controller buttons are unavailable. Refresh to check their state.') from error


def request_status(socket_path=None, timeout=1.5):
  return _request({'operation': 'status'}, socket_path, timeout)


def request_action(payload, socket_path=None, timeout=1.5):
  if type(payload) is not dict or payload.get('operation') not in {'save', 'learn', 'cancel', 'test', 'remove'}:
    raise ControllerInvalid('Invalid controller operation')
  return _request(payload, socket_path, timeout)


class _Job:
  def __init__(self, payload):
    self.payload = payload
    self.deadline = time.monotonic() + REQUEST_DEADLINE
    self.done = threading.Event()
    self.cancelled = False
    self.started = False
    self.response = {'status': 'unavailable', 'result': 'Controller buttons are unavailable'}


class ControllerService:
  """The socket accepts configuration; physical button execution stays on the UI thread."""
  def __init__(self, owner, socket_path=None):
    self.owner = owner
    self.path = Path(socket_path or DEFAULT_SOCKET_PATH)
    self._lock = threading.Lock()
    self._pending = None
    self._closed = threading.Event()
    self._listener = None
    self._thread = None
    self._identity = None
    self._last_error = float('-inf')

  def start(self):
    if self._listener is not None or self._closed.is_set():
      raise ControllerUnavailable('Controller service already started or closed')
    self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = self.path.parent.lstat()
    if parent.st_uid != os.getuid() or not stat.S_ISDIR(parent.st_mode) or parent.st_mode & 0o077:
      raise ControllerUnavailable('Controller socket directory is not private')
    try:
      existing = self.path.lstat()
    except FileNotFoundError:
      pass
    else:
      if existing.st_uid != os.getuid() or not stat.S_ISSOCK(existing.st_mode):
        raise ControllerUnavailable('Controller socket path is occupied')
      with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
        peer.settimeout(0.1)
        try:
          peer.connect(str(self.path))
        except (ConnectionRefusedError, FileNotFoundError):
          self.path.unlink()
        else:
          raise ControllerUnavailable('Controller service is already active')
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
      listener.bind(str(self.path))
      info = self.path.lstat()
      self._identity = info.st_dev, info.st_ino
      os.chmod(self.path, 0o600)
      listener.listen(8)
      listener.settimeout(0.1)
    except BaseException:
      listener.close()
      self._unlink_owned()
      raise
    self._listener = listener
    self._thread = threading.Thread(target=self._serve, args=(listener,), name='controller-settings', daemon=True)
    self._thread.start()

  def _serve(self, listener):
    while not self._closed.is_set():
      try:
        peer, _ = listener.accept()
      except TimeoutError:
        continue
      except OSError as error:
        if error.errno in (errno.ECONNABORTED, errno.EINTR):
          continue
        break
      with peer:
        peer.settimeout(0.5)
        try:
          size = struct.unpack('!I', _receive(peer, 4))[0]
          if not 0 < size <= MAX_BYTES:
            raise ControllerInvalid('Invalid controller request size')
          payload = _decode(_receive(peer, size))
          if type(payload) is not dict or payload.get('operation') not in {'status', 'save', 'learn', 'cancel', 'test', 'remove'}:
            raise ControllerInvalid('Invalid controller operation')
          job = _Job(payload)
          with self._lock:
            self._pending = job
          if not job.done.wait(REQUEST_DEADLINE):
            with self._lock:
              if not job.started:
                job.cancelled = True
                if self._pending is job:
                  self._pending = None
              uncertain = job.started
            job.response = {'status': 'unavailable', 'result': (
              'Controller settings may have changed. Refresh before trying again.' if uncertain else
              'Controller request expired before it ran. Refresh to try again.')}
          encoded = _encode(job.response)
          peer.sendall(struct.pack('!I', len(encoded)) + encoded)
        except (ValueError, RecursionError) as error:
          try:
            encoded = _encode({'status': 'invalid', 'result': str(error)[:160]})
            peer.sendall(struct.pack('!I', len(encoded)) + encoded)
          except OSError:
            pass
        except (OSError, ControllerUnavailable):
          pass

  def poll(self):
    with self._lock:
      job = self._pending
      self._pending = None
      if job is None or job.cancelled or self._closed.is_set() or time.monotonic() >= job.deadline:
        return
      job.started = True
    try:
      payload = job.payload
      if payload == {'operation': 'status'}:
        result = self.owner.snapshot()
      elif payload.get('operation') == 'status':
        raise ControllerInvalid('Invalid controller status request')
      else:
        result = self.owner.action(payload)
      job.response = {'status': 'ok', 'result': result}
      _encode(job.response)
    except PermissionError as error:
      job.response = {'status': 'denied', 'result': str(error)[:160]}
    except ValueError as error:
      job.response = {'status': 'invalid', 'result': str(error)[:160]}
    except (OSError, RuntimeError) as error:
      job.response = {'status': 'unavailable', 'result': str(error)[:160]}
    except Exception:
      now = time.monotonic()
      if now - self._last_error >= 10:
        self._last_error = now
        LOGGER.exception('Controller settings failed')
      job.response = {'status': 'unavailable', 'result': 'Controller buttons are unavailable'}
    finally:
      job.done.set()

  def close(self):
    self._closed.set()
    with self._lock:
      if self._pending is not None:
        self._pending.cancelled = True
        self._pending.done.set()
        self._pending = None
    if self._listener is not None:
      self._listener.close()
      self._listener = None
    if self._thread is not None:
      self._thread.join(REQUEST_DEADLINE + 0.2)
      self._thread = None
    self._unlink_owned()

  def _unlink_owned(self):
    identity, self._identity = self._identity, None
    if identity is not None:
      try:
        info = self.path.lstat()
        if (info.st_dev, info.st_ino) == identity:
          self.path.unlink()
      except FileNotFoundError:
        pass
