"""Strict saved choices and a bounded asynchronous learning writer."""

from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
from queue import SimpleQueue
import tempfile
import threading

from openpilot.starpilot.curve_speed.host import CurveHost
from openpilot.starpilot.curve_speed.learning import LearnedCurve
from openpilot.starpilot.saved_source import read_saved


DOCUMENT_KEY = 'CurveComfortData'
LEGACY_KEY = 'CurvatureData'
MASTER_KEY = 'CurveSpeedController'
NO_LEAD_KEY = 'CurveSpeedControllerNoLead'
DOCUMENT_LIMIT = 32768
REFRESH_NS = 1_000_000_000


def learning_lock_path(params) -> Path:
  return Path(params.get_param_path(DOCUMENT_KEY)).parent.parent / '.curve_learning.lock'


def acquire_learning_lease(params) -> int | None:
  """Exclude a second learning owner and parked edits for this Params root."""
  fd = None
  try:
    fd = os.open(learning_lock_path(params), os.O_CREAT | os.O_RDONLY, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return fd
  except OSError:
    if fd is not None:
      os.close(fd)
    return None


def _unique_object(items):
  result = {}
  for key, value in items:
    if key in result:
      raise ValueError('duplicate JSON key')
    result[key] = value
  return result


def decode(raw: bytes | None):
  return None if raw is None else json.loads(raw, object_pairs_hook=_unique_object)


@dataclass(frozen=True)
class SavedLearning:
  document: object
  valid: bool
  reason: str
  current_raw: bytes | None


def read_learning(params) -> SavedLearning:
  current, readable = read_saved(params, DOCUMENT_KEY, DOCUMENT_LIMIT)
  if not readable:
    return SavedLearning(None, False, 'unreadable_learning', current)
  raw = current
  if raw is None:
    raw, readable = read_saved(params, LEGACY_KEY, DOCUMENT_LIMIT)
    if not readable:
      return SavedLearning(None, False, 'unreadable_legacy', current)
  try:
    document = decode(raw)
    if raw is not None and (document is None or (current is not None and
                             (type(document) is not dict or document.get('version') != 1))):
      raise ValueError('invalid saved document')
    loaded = LearnedCurve.load(document)
  except (ValueError, UnicodeDecodeError, RecursionError, OverflowError):
    return SavedLearning(None, False, 'invalid_learning', current)
  return SavedLearning(document, loaded.valid, loaded.reason, current)


class PreferenceHost:
  """One drive owns the new document. Legacy bytes are never modified.

  Writes execute off the planner thread and only acknowledge a verified saved
  revision. The conditional replace uses the same lock as ordinary Params
  writers. A conflicting external edit suspends persistence for this session.
  Closing cancels any write that has not reached its atomic replace; a replace
  already completed may still be finishing its directory sync.
  """

  def __init__(self, params):
    self.params = params
    self.saved = read_learning(params)
    self.expected_raw = self.saved.current_raw
    self.last_refresh_ns = -REFRESH_NS
    self.last_attempt_ns = -REFRESH_NS
    self.worker: threading.Thread | None = None
    self.completed = SimpleQueue()
    self.status = 'idle' if self.saved.valid else self.saved.reason
    self.closed = False
    self.conflicted = False
    self.host: CurveHost | None = None
    self.cancel_write = threading.Event()
    self.commit_lock = threading.Lock()
    self.session_fd: int | None = None

  def make_host(self, *, replay: bool = False) -> CurveHost:
    if self.host is not None or self.closed:
      raise RuntimeError('learning session already initialized')
    self.session_fd = acquire_learning_lease(self.params)
    # An editor may have changed the document after this owner was constructed.
    # Capture the initial document only after excluding other learning owners.
    self.saved = read_learning(self.params)
    self.expected_raw = self.saved.current_raw
    self.status = ('idle' if self.saved.valid else self.saved.reason) if self.session_fd is not None else 'learning_active'
    self.host = CurveHost(self.saved.document, replay=replay)
    self.host.runtime.document_valid = self.saved.valid and self.session_fd is not None
    self.host.runtime.document_reason = self.saved.reason if self.session_fd is not None else 'learning_active'
    return self.host

  def refresh(self, host: CurveHost, now_ns: int) -> None:
    if host is not self.host:
      raise ValueError('different learning session')
    if now_ns < self.last_refresh_ns:
      self.last_refresh_ns = now_ns - REFRESH_NS
    if now_ns - self.last_refresh_ns < REFRESH_NS:
      return
    self.last_refresh_ns = now_ns
    choices = []
    for key in (MASTER_KEY, NO_LEAD_KEY):
      raw, readable = read_saved(self.params, key, 8)
      choices.append((raw == b'1', readable and raw in (None, b'0', b'1')))
    valid = all(readable for _enabled, readable in choices)
    host.runtime.enabled = choices[0][0] and valid and not self.closed and not self.conflicted and self.session_fd is not None
    host.runtime.no_lead = choices[1][0] if valid else True

  def _write(self, document: dict, revision: int, expected: bytes | None) -> None:
    temporary = None
    committed_raw = None
    try:
      raw = json.dumps(document, allow_nan=False, separators=(',', ':')).encode()
      if len(raw) > DOCUMENT_LIMIT:
        raise ValueError('learning document too large')
      destination = Path(self.params.get_param_path(DOCUMENT_KEY))
      # Keep the lexical prefix path: its parent is the Params root containing
      # .lock, even when the active prefix is a symlink to a version directory.
      root = destination.parent.parent
      with tempfile.NamedTemporaryFile(prefix='.tmp_curve_', dir=root, delete=False) as staging:
        temporary = staging.name
        staging.write(raw)
        staging.flush()
        os.fsync(staging.fileno())
      lock_fd = os.open(root / '.lock', os.O_CREAT | os.O_RDONLY, 0o775)
      try:
        while not self.cancel_write.is_set():
          try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
          except BlockingIOError:
            self.cancel_write.wait(0.01)
        else:
          self.completed.put((revision, None, 'cancelled'))
          return
        current, readable = read_saved(self.params, DOCUMENT_KEY, DOCUMENT_LIMIT)
        if not readable or current != expected:
          self.completed.put((revision, None, 'external_edit'))
          return
        # close() shares only this short rename critical section. It never
        # waits for another Params owner, staging I/O, or directory fsync.
        with self.commit_lock:
          if self.cancel_write.is_set():
            self.completed.put((revision, None, 'cancelled'))
            return
          os.replace(temporary, destination)
          temporary = None
          committed_raw = raw
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
          os.fsync(directory_fd)
        finally:
          os.close(directory_fd)
        actual, readable = read_saved(self.params, DOCUMENT_KEY, DOCUMENT_LIMIT)
        if not readable or actual != raw:
          raise OSError('learning write not verified')
        self.completed.put((revision, actual, 'saved'))
      finally:
        os.close(lock_fd)
    except (OSError, RuntimeError, ValueError, TypeError, RecursionError, OverflowError):
      self.completed.put((revision, committed_raw, 'write_failed'))
    finally:
      if temporary is not None:
        try:
          os.unlink(temporary)
        except FileNotFoundError:
          pass

  def persist(self, host: CurveHost, result, now_ns: int) -> None:
    if host is not self.host:
      raise ValueError('different learning session')
    while not self.completed.empty():
      revision, actual, self.status = self.completed.get()
      self.worker = None
      if actual is not None:
        self.expected_raw = actual
      if self.status == 'saved':
        host.runtime.acknowledge_saved(revision)
      elif self.status == 'external_edit':
        self.conflicted = True
        host.runtime.enabled = False
    if now_ns < self.last_attempt_ns:
      self.last_attempt_ns = now_ns - REFRESH_NS
    if (self.closed or self.session_fd is None or self.conflicted or not self.saved.valid or self.worker is not None or
        result.dirty_revision is None or not host.runtime.curve.dirty or now_ns - self.last_attempt_ns < REFRESH_NS):
      return
    self.last_attempt_ns = now_ns
    revision = host.runtime.curve.revision
    document = host.runtime.curve.document()
    self.worker = threading.Thread(target=self._write, args=(document, revision, self.expected_raw), daemon=True, name='curve-learning')
    self.status = 'writing'
    self.worker.start()

  def close(self) -> None:
    with self.commit_lock:
      self.closed = True
      self.cancel_write.set()
    if self.host is not None:
      self.host.runtime.enabled = False
    if self.worker is not None:
      self.worker.join(timeout=0.25)
    if self.session_fd is not None:
      os.close(self.session_fd)
      self.session_fd = None
