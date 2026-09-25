"""Bounded saved manual CEM/CCM state; no legacy-key adoption or control authority.

The planner owns one drive session. Storage work happens on one short-lived
worker at a time and is serialized with ordinary Params writers under .lock.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
from queue import SimpleQueue
import tempfile
import threading
import time

from openpilot.starpilot.conditional_mode.policy import ManualIntent, ModeChoice, restore_manual_status
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner, SettingsSnapshot
from openpilot.starpilot.saved_source import read_saved


KEY = 'ConditionalManualState'
LIMIT = 256
LOCK_WAIT_S = 0.25


@dataclass(frozen=True)
class SavedCodes:
  cem: int = 0
  ccm: int = 0

  def code(self, choice: ModeChoice) -> int:
    return self.cem if choice is ModeChoice.CEM else self.ccm

  def with_code(self, choice: ModeChoice, code: int) -> SavedCodes:
    return SavedCodes(code, self.ccm) if choice is ModeChoice.CEM else SavedCodes(self.cem, code)


@dataclass(frozen=True)
class SavedRead:
  status: str
  codes: SavedCodes | None
  raw: bytes | None


@dataclass(frozen=True)
class DriveStart:
  status: str
  intent: ManualIntent | None
  code: int | None


@dataclass(frozen=True)
class WriteResult:
  revision: int
  raw: bytes | None
  status: str
  committed: bool


def _unique_object(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ValueError('duplicate manual saved key')
    result[key] = value
  return result


def decode(raw: bytes | None) -> SavedCodes:
  if raw is None:
    return SavedCodes()
  if len(raw) > LIMIT:
    raise ValueError('manual state too large')
  try:
    value = json.loads(raw, object_pairs_hook=_unique_object)
  except (UnicodeDecodeError, ValueError, TypeError, RecursionError, OverflowError) as exc:
    raise ValueError('invalid manual state') from exc
  if (type(value) is not dict or set(value) != {'version', 'cem', 'ccm'} or
      type(value['version']) is not int or value['version'] != 1 or
      type(value['cem']) is not int or value['cem'] not in (0, 1, 2) or
      type(value['ccm']) is not int or value['ccm'] not in (0, 1, 2)):
    raise ValueError('invalid manual state fields')
  return SavedCodes(value['cem'], value['ccm'])


def encode(codes: SavedCodes) -> bytes:
  if (type(codes) is not SavedCodes or type(codes.cem) is not int or codes.cem not in (0, 1, 2) or
      type(codes.ccm) is not int or codes.ccm not in (0, 1, 2)):
    raise ValueError('invalid manual codes')
  return json.dumps({'version': 1, 'cem': codes.cem, 'ccm': codes.ccm}, separators=(',', ':')).encode()


def read_codes(params) -> SavedRead:
  try:
    raw, readable = read_saved(params, KEY, LIMIT)
  except (OSError, TypeError, ValueError):
    return SavedRead('read_error', None, None)
  if not readable:
    return SavedRead('read_error', None, raw)
  try:
    return SavedRead('absent' if raw is None else 'valid', decode(raw), raw)
  except ValueError:
    return SavedRead('invalid', None, raw)


def manual_lock_path(params) -> Path:
  return Path(params.get_param_path(KEY)).parent.parent / '.conditional_manual.lock'


def _lease(params) -> int | None:
  fd = None
  try:
    fd = os.open(manual_lock_path(params), os.O_CREAT | os.O_RDONLY, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return fd
  except OSError:
    if fd is not None:
      os.close(fd)
    return None


class ManualSavedOwner:
  """One drive, one asynchronous writer, exact source and byte CAS.

  begin_drive is called once after a validated settings observation. poll is
  cheap and starts at most one worker. close prevents any future rename; it
  never waits for staging I/O or a different Params writer.
  """

  def __init__(self, params, settings_owner: ConditionalSettingsOwner):
    self.params = params
    self.settings_owner = settings_owner
    self.session_fd: int | None = None
    self.snapshot: SettingsSnapshot | None = None
    self.choice = ModeChoice.STOCK
    self.drive_id = 0
    self.persist = False
    self.saved = SavedRead('unstarted', None, None)
    self.codes: SavedCodes | None = None
    self.expected_raw: bytes | None = None
    self.desired_revision = 0
    self.saved_revision = 0
    self.worker: threading.Thread | None = None
    self.worker_finalized = True
    self.completed: SimpleQueue[WriteResult] = SimpleQueue()
    self.cancel = threading.Event()
    self.commit_lock = threading.Lock()
    self.closed = False
    self.conflicted = False
    self.status = 'unstarted'
    self.retry_after_ns = 0

  def _valid(self, snapshot: SettingsSnapshot, now_ns: int, drive_id: int, choice: ModeChoice) -> bool:
    verdict = self.settings_owner.verdict(snapshot, now_mono_ns=now_ns, drive_id=drive_id)
    return bool(
      not self.closed and self._same_source(self.snapshot, snapshot) and self.drive_id == drive_id and self.choice is choice and
      verdict.status == 'ready' and verdict.selection is not None and verdict.selection.choice is choice and
      verdict.safe_mode is False and self._same_source(self.settings_owner.current, snapshot)
    )

  @staticmethod
  def _same_source(left: SettingsSnapshot | None, right: SettingsSnapshot) -> bool:
    return bool(left is not None and left.owner_token == right.owner_token and left.revision == right.revision and
                left.observed_mono_ns == right.observed_mono_ns and left.document_raw == right.document_raw and
                left.safe_mode_raw == right.safe_mode_raw and left.document_state is right.document_state and
                left.safe_mode_state is right.safe_mode_state)

  def _release_lease(self) -> None:
    if self.session_fd is not None:
      os.close(self.session_fd)
      self.session_fd = None

  def begin_drive(self, snapshot: SettingsSnapshot, *, choice: ModeChoice, drive_id: int, now_ns: int) -> DriveStart:
    if self.snapshot is not None or self.closed or choice not in (ModeChoice.CEM, ModeChoice.CCM):
      return DriveStart('unavailable', None, None)
    self.snapshot = snapshot
    self.choice = choice
    self.drive_id = drive_id
    if not self._valid(snapshot, now_ns, drive_id, choice):
      self.status = 'unavailable_settings'
      return DriveStart(self.status, None, None)
    assert snapshot.preferences is not None
    self.persist = (snapshot.preferences.cem.persist_manual if choice is ModeChoice.CEM else
                    snapshot.preferences.ccm.persist_manual)
    self.session_fd = _lease(self.params)
    if self.session_fd is None:
      self.status = 'active_elsewhere'
      return DriveStart(self.status, None, None)
    self.saved = read_codes(self.params)
    self.expected_raw = self.saved.raw
    self.codes = self.saved.codes
    self.status = self.saved.status
    if self.codes is None:
      # A corrupt persisted document cannot restore an override. Without
      # persistence the pure in-drive manual owner still starts at automatic.
      return DriveStart(self.status, ManualIntent.NONE if not self.persist else None,
                        0 if not self.persist else None)
    code = self.codes.code(choice) if self.persist else 0
    if not self.persist and self.codes.code(choice) != 0:
      # Opt-out must preserve the other mode's saved choice.
      self.codes = self.codes.with_code(choice, 0)
      self.desired_revision += 1
    return DriveStart(self.status, restore_manual_status(choice, 0, code, self.persist), code)

  def queue_code(self, code: int, *, snapshot: SettingsSnapshot, drive_id: int, now_ns: int) -> bool:
    if (type(code) is not int or code not in (0, 1, 2) or not self.persist or self.codes is None or
        self.conflicted or self.session_fd is None or not self._valid(snapshot, now_ns, drive_id, self.choice)):
      return False
    newer = self.codes.with_code(self.choice, code)
    if newer != self.codes:
      self.codes = newer
      self.desired_revision += 1
    return True

  def _identity_current(self, snapshot: SettingsSnapshot) -> bool:
    return self._same_source(self.settings_owner.current, snapshot)

  def _write(self, codes: SavedCodes, revision: int, expected: bytes | None, snapshot: SettingsSnapshot) -> None:
    staging = None
    committed = False
    raw = encode(codes)
    try:
      destination = Path(self.params.get_param_path(KEY))
      root = destination.parent.parent
      with tempfile.NamedTemporaryFile(prefix='.tmp_conditional_manual_', dir=root, delete=False) as output:
        staging = output.name
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
      lock_fd = os.open(root / '.lock', os.O_CREAT | os.O_RDONLY, 0o775)
      try:
        deadline = time.monotonic() + LOCK_WAIT_S
        while not self.cancel.is_set() and time.monotonic() < deadline:
          try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
          except BlockingIOError:
            self.cancel.wait(0.01)
        else:
          self.completed.put(WriteResult(revision, None, 'cancelled' if self.cancel.is_set() else 'lock_busy', False))
          return
        current = read_codes(self.params)
        config_raw, config_ok = read_saved(self.params, 'ConditionalModeConfig', 4096)
        safe_raw, safe_ok = read_saved(self.params, 'SafeMode', 8)
        if (current.status not in ('valid', 'absent') or current.raw != expected or not config_ok or not safe_ok or
            config_raw != snapshot.document_raw or safe_raw != snapshot.safe_mode_raw):
          self.completed.put(WriteResult(revision, None, 'external_edit', False))
          return
        with self.commit_lock:
          if self.cancel.is_set() or not self._identity_current(snapshot):
            self.completed.put(WriteResult(revision, None, 'cancelled', False))
            return
          os.replace(staging, destination)
          staging = None
          committed = True
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
          os.fsync(directory_fd)
        finally:
          os.close(directory_fd)
        verified = read_codes(self.params)
        self.completed.put(WriteResult(revision, raw if verified.raw == raw and verified.status == 'valid' else None,
                                       'saved' if verified.raw == raw and verified.status == 'valid' else 'verification_failed', committed))
      finally:
        os.close(lock_fd)
    except (OSError, RuntimeError, ValueError, TypeError, RecursionError, OverflowError):
      self.completed.put(WriteResult(revision, raw if committed else None, 'write_failed', committed))
    finally:
      if staging is not None:
        try:
          os.unlink(staging)
        except FileNotFoundError:
          pass
      with self.commit_lock:
        self.worker_finalized = True
        if self.closed:
          self._release_lease()

  def poll(self, *, snapshot: SettingsSnapshot, drive_id: int, now_ns: int) -> WriteResult | None:
    latest = None
    while not self.completed.empty():
      latest = self.completed.get()
      self.status = latest.status
      if latest.committed and latest.raw is not None:
        self.expected_raw = latest.raw
      if latest.status == 'saved':
        self.saved_revision = latest.revision
      elif latest.status == 'lock_busy':
        self.retry_after_ns = now_ns + 1_000_000_000
      elif latest.status in ('external_edit', 'verification_failed', 'write_failed'):
        self.conflicted = True
    if self.worker is not None and not self.worker.is_alive():
      self.worker = None
    if (self.session_fd is None or self.codes is None or self.conflicted or
        not self._valid(snapshot, now_ns, drive_id, self.choice)):
      self.cancel.set()
      return latest
    if self.worker is None and self.desired_revision > self.saved_revision and now_ns >= self.retry_after_ns:
      self.worker_finalized = False
      self.worker = threading.Thread(target=self._write,
                                     args=(self.codes, self.desired_revision, self.expected_raw, snapshot),
                                     daemon=True, name='conditional-manual-save')
      self.status = 'writing'
      self.worker.start()
    return latest

  def close(self) -> None:
    with self.commit_lock:
      self.closed = True
      self.cancel.set()
      if self.worker_finalized:
        self._release_lease()
