"""Bounded local transport for parked, main-thread layout previews."""

from collections.abc import Callable
import json
import logging
import os
from pathlib import Path
import socket
import stat
import struct
import threading
import time

from openpilot.starpilot.ui.onroad_customization import validate_document


DEFAULT_SOCKET_PATH = Path(f'/tmp/starpilot-layout-preview-{os.getuid()}') / 'ui.sock'
MAX_REQUEST_BYTES = 32768
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_WIDTH = 2560
MAX_HEIGHT = 1440
RENDER_DEADLINE = 2.0
MIN_INTERVAL = 0.5
ERROR_LOG_INTERVAL = 10.0
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
SCENES = frozenset(('engaged', 'aol', 'long_only', 'experimental', 'braking',
                    'cem_stop_light', 'cem_lead', 'cem_curve', 'slc_pending'))
PROFILES = frozenset(('large', 'compact'))
RENDER_PROFILES = PROFILES | {'projection'}
LOGGER = logging.getLogger(__name__)


class PreviewUnavailable(RuntimeError):
  pass


class PreviewBusy(PreviewUnavailable):
  pass


class PreviewDenied(PermissionError):
  pass


class PreviewInvalid(ValueError):
  pass


class _Job:
  def __init__(self, payload: dict, deadline: float):
    self.payload = payload
    self.deadline = deadline
    self.done = threading.Event()
    self.cancelled = False
    self.result: bytes | None = None
    self.error: Exception | None = None


def _payload(value: object) -> dict:
  if not isinstance(value, dict) or type(value) is not dict or set(value) != {'document', 'profile', 'scene'}:
    raise PreviewInvalid('Invalid preview request')
  if type(value['profile']) is not str or type(value['scene']) is not str or \
     value['profile'] not in RENDER_PROFILES or value['scene'] not in SCENES:
    raise PreviewInvalid('Invalid preview profile or scene')
  try:
    if value['profile'] == 'projection':
      from openpilot.starpilot.system.android_auto.projection_layout import validate_layout_for_viewport
      source = value['document']
      if type(source) is not dict or set(source) != {'layout', 'base'}:
        raise ValueError('Invalid projection preview')
      canvas = source['layout']['canvas']
      document = {'layout': validate_layout_for_viewport(source['layout'], (canvas['width'], canvas['height'])),
                  'base': validate_document(source['base'])}
    else:
      document = validate_document(value['document'])
  except (ValueError, TypeError, OverflowError, RecursionError) as error:
    raise PreviewInvalid('Invalid layout document') from error
  return {'document': document, 'profile': value['profile'], 'scene': value['scene']}


def validate_png(value: object) -> bytes:
  if type(value) is not bytes or not 45 <= len(value) <= MAX_IMAGE_BYTES or not value.startswith(PNG_SIGNATURE):
    raise PreviewInvalid('Invalid preview image')
  if value[8:16] != b'\x00\x00\x00\rIHDR' or value[-12:-8] != b'\x00\x00\x00\x00' or value[-8:-4] != b'IEND':
    raise PreviewInvalid('Invalid preview image')
  width, height = struct.unpack('!II', value[16:24])
  if not 0 < width <= MAX_WIDTH or not 0 < height <= MAX_HEIGHT or width * height > MAX_WIDTH * MAX_HEIGHT:
    raise PreviewInvalid('Preview dimensions exceed limit')
  return value


def _recv_exact(peer: socket.socket, size: int) -> bytes:
  chunks = bytearray()
  while len(chunks) < size:
    part = peer.recv(size - len(chunks))
    if not part:
      raise PreviewUnavailable('Preview connection closed')
    chunks.extend(part)
  return bytes(chunks)


def _send(peer: socket.socket, code: bytes, data: bytes):
  peer.sendall(code + struct.pack('!I', len(data)) + data)


def _response(peer: socket.socket, timeout: float) -> bytes:
  peer.settimeout(timeout)
  code = _recv_exact(peer, 1)
  size = struct.unpack('!I', _recv_exact(peer, 4))[0]
  if size > MAX_IMAGE_BYTES:
    raise PreviewUnavailable('Preview response exceeds limit')
  body = _recv_exact(peer, size)
  if code == b'\x00':
    return body
  message = body.decode('utf-8', 'replace')[:160]
  if code == b'\x01':
    raise PreviewInvalid(message)
  if code == b'\x02':
    raise PreviewDenied(message)
  if code == b'\x03':
    raise PreviewBusy(message)
  raise PreviewUnavailable(message or 'Preview unavailable')


def request_preview(payload: dict, socket_path: str | Path | None = None, timeout: float = 2.5) -> bytes:
  normalized = _payload(payload)
  encoded = json.dumps(normalized, separators=(',', ':'), allow_nan=False).encode()
  if len(encoded) > MAX_REQUEST_BYTES:
    raise PreviewInvalid('Preview request exceeds limit')
  try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
      peer.settimeout(timeout)
      peer.connect(str(socket_path or DEFAULT_SOCKET_PATH))
      peer.sendall(b'P' + struct.pack('!I', len(encoded)) + encoded)
      return validate_png(_response(peer, timeout))
  except (PreviewDenied, PreviewBusy, PreviewInvalid, PreviewUnavailable):
    raise
  except (OSError, TimeoutError) as error:
    raise PreviewUnavailable('Onroad UI preview is unavailable') from error


def request_profile(socket_path: str | Path | None = None, timeout: float = 0.1) -> str | None:
  try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
      peer.settimeout(timeout)
      peer.connect(str(socket_path or DEFAULT_SOCKET_PATH))
      peer.sendall(b'S')
      result = json.loads(_response(peer, timeout))
      profile = result.get('activeProfile')
      return profile if profile in PROFILES else None
  except (OSError, TimeoutError, ValueError, PreviewUnavailable):
    return None


class PreviewService:
  def __init__(self, renderer_callable: Callable[[dict], bytes], parked_callable: Callable[[], bool],
               socket_path: str | Path | None = None, active_profile: str | None = None):
    if active_profile is not None and active_profile not in PROFILES:
      raise ValueError('Invalid active profile')
    self.renderer = renderer_callable
    self.parked = parked_callable
    self.socket_path = Path(socket_path or DEFAULT_SOCKET_PATH)
    self._active_profile = active_profile
    self._lock = threading.Lock()
    self._pending: _Job | None = None
    self._rendering = False
    self._last_render = -MIN_INTERVAL
    self._last_error_log = float('-inf')
    self._closed = threading.Event()
    self._listener: socket.socket | None = None
    self._thread: threading.Thread | None = None
    self._socket_identity: tuple[int, int] | None = None

  def set_active_profile(self, profile: str | None):
    if profile is not None and profile not in PROFILES:
      raise ValueError('Invalid active profile')
    with self._lock:
      self._active_profile = profile

  def start(self):
    if self._listener is not None or self._closed.is_set():
      raise PreviewUnavailable('Preview service already started or closed')
    parent = self.socket_path.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = parent.lstat()
    if info.st_uid != os.getuid() or not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
      raise PreviewUnavailable('Preview socket directory is not private')
    try:
      existing = self.socket_path.lstat()
    except FileNotFoundError:
      pass
    else:
      if existing.st_uid != os.getuid() or not stat.S_ISSOCK(existing.st_mode):
        raise PreviewUnavailable('Preview socket path is occupied')
      with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.1)
        try:
          probe.connect(str(self.socket_path))
        except (ConnectionRefusedError, FileNotFoundError):
          self.socket_path.unlink()
        else:
          raise PreviewUnavailable('Preview service is already active')
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
      listener.bind(str(self.socket_path))
      bound = self.socket_path.lstat()
      self._socket_identity = bound.st_dev, bound.st_ino
      os.chmod(self.socket_path, 0o600)
      listener.listen(1)
      listener.settimeout(0.1)
    except BaseException:
      listener.close()
      self._unlink_owned()
      raise
    self._listener = listener
    self._thread = threading.Thread(target=self._serve, args=(listener,), name='layout-preview-io', daemon=True)
    self._thread.start()

  def _serve(self, listener: socket.socket):
    while not self._closed.is_set():
      try:
        peer, _ = listener.accept()
      except TimeoutError:
        continue
      except OSError:
        break
      with peer:
        peer.settimeout(0.5)
        try:
          self._handle(peer)
        except (OSError, TimeoutError, PreviewUnavailable, ValueError, UnicodeError):
          pass

  def _handle(self, peer: socket.socket):
    opcode = _recv_exact(peer, 1)
    if opcode == b'S':
      with self._lock:
        profile = self._active_profile
      _send(peer, b'\x00', json.dumps({'activeProfile': profile}).encode())
      return
    if opcode != b'P':
      _send(peer, b'\x01', b'Invalid preview operation')
      return
    size = struct.unpack('!I', _recv_exact(peer, 4))[0]
    if not 0 < size <= MAX_REQUEST_BYTES:
      _send(peer, b'\x01', b'Invalid preview request size')
      return
    try:
      payload = _payload(json.loads(_recv_exact(peer, size)))
    except (ValueError, UnicodeError, RecursionError):
      _send(peer, b'\x01', b'Invalid preview request')
      return
    job = _Job(payload, time.monotonic() + RENDER_DEADLINE)
    with self._lock:
      if self._pending is not None or self._rendering:
        _send(peer, b'\x03', b'Preview is busy; try again shortly')
        return
      self._pending = job
    if not job.done.wait(RENDER_DEADLINE):
      with self._lock:
        job.cancelled = True
        job.result = None
        if self._pending is job:
          self._pending = None
      _send(peer, b'\x04', b'Onroad UI did not render in time')
      return
    if job.error is not None:
      code = b'\x02' if isinstance(job.error, PreviewDenied) else b'\x03' if isinstance(job.error, PreviewBusy) else b'\x04'
      _send(peer, code, str(job.error).encode()[:160])
    elif job.result is not None:
      _send(peer, b'\x00', job.result)
    else:
      _send(peer, b'\x04', b'Preview unavailable')

  def poll(self) -> bool:
    with self._lock:
      job = self._pending
      if job is None or job.cancelled or self._closed.is_set():
        return False
      completing = job.result is not None
      if not completing and time.monotonic() - self._last_render < MIN_INTERVAL:
        return False
      self._pending = None
      self._rendering = True
      if not completing:
        self._last_render = time.monotonic()
    deferred = False
    stage = 'next-frame completion' if completing else 'before render'
    try:
      if time.monotonic() >= job.deadline:
        raise PreviewUnavailable('Preview request expired')
      if not self.parked():
        raise PreviewDenied('Turn off the vehicle to preview this layout')
      if completing:
        if self._closed.is_set() or job.cancelled:
          raise PreviewUnavailable('Preview service closed or request cancelled')
        if time.monotonic() >= job.deadline:
          raise PreviewUnavailable('Preview rendering expired')
      else:
        stage = 'render'
        result = validate_png(self.renderer(job.payload))
        if time.monotonic() >= job.deadline:
          raise PreviewUnavailable('Preview rendering expired')
        # Rendering can outlast the borrowed collector's freshness window.
        # Keep one bounded result until the next normal UI update, then apply
        # the unchanged parked check to that frame's fresh evidence.
        with self._lock:
          if self._closed.is_set() or job.cancelled:
            raise PreviewUnavailable('Preview service closed or request cancelled')
          job.result = result
          self._pending = job
          deferred = True
    except PreviewDenied as error:
      LOGGER.info('Layout preview authority denied at %s after %.3f seconds', stage,
                  max(0.0, time.monotonic() - self._last_render))
      job.error = error
      job.result = None
    except PreviewUnavailable as error:
      job.error = error
      job.result = None
    except Exception:
      now = time.monotonic()
      if now - self._last_error_log >= ERROR_LOG_INTERVAL:
        self._last_error_log = now
        LOGGER.exception('Layout preview renderer failed')
      job.error = PreviewUnavailable('Onroad UI preview is unavailable')
      job.result = None
    finally:
      with self._lock:
        self._rendering = False
      if not deferred:
        job.done.set()
    return True

  def close(self):
    self._closed.set()
    with self._lock:
      if self._pending is not None:
        self._pending.cancelled = True
        self._pending.result = None
        self._pending.error = PreviewUnavailable('Preview service closed')
        self._pending.done.set()
        self._pending = None
    if self._listener is not None:
      self._listener.close()
      self._listener = None
    if self._thread is not None:
      self._thread.join(timeout=RENDER_DEADLINE + 0.2)
      self._thread = None
    self._unlink_owned()

  def _unlink_owned(self):
    identity = self._socket_identity
    self._socket_identity = None
    if identity is None:
      return
    try:
      info = self.socket_path.lstat()
    except FileNotFoundError:
      return
    if (info.st_dev, info.st_ino) == identity:
      self.socket_path.unlink()
