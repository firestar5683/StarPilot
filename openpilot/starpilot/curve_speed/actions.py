"""Confirmed parked learning edits, shared by native settings and Galaxy."""

from collections.abc import Callable
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import tempfile

from openpilot.starpilot.curve_speed.learning import LearnedCurve
from openpilot.starpilot.curve_speed.preferences import (
  DOCUMENT_KEY, LEGACY_KEY, MASTER_KEY, DOCUMENT_LIMIT,
  acquire_learning_lease, decode, learning_lock_path,
)
from openpilot.starpilot.saved_source import read_saved


ACTION_KEYS = frozenset(('curve_reset',))
SOURCE_KEYS = (DOCUMENT_KEY, LEGACY_KEY, MASTER_KEY)


@dataclass(frozen=True)
class LearningSnapshot:
  sources: tuple[tuple[str, bytes | None], ...]
  readable: bool
  valid: bool
  reason: str
  progress: float | None
  comfort: float | None
  has_samples: bool
  resettable: bool


@dataclass(frozen=True)
class ActionResult:
  committed: bool
  reason: str


def _sources(params) -> tuple[tuple[tuple[str, bytes | None], ...], bool]:
  reads = [(key, *read_saved(params, key, 8 if key == MASTER_KEY else DOCUMENT_LIMIT)) for key in SOURCE_KEYS]
  return tuple((key, raw) for key, raw, _readable in reads), all(readable for _key, _raw, readable in reads)


def _loaded(sources):
  current, legacy, _master = (raw for _key, raw in sources)
  raw = current if current is not None else legacy
  try:
    document = decode(raw)
    if raw is not None and (document is None or current is not None and
                           (type(document) is not dict or document.get('version') != 1)):
      raise ValueError('invalid saved document')
    return LearnedCurve.load(document)
  except (ValueError, UnicodeDecodeError, RecursionError, OverflowError):
    return LearnedCurve.load(False)


def _idle(params) -> bool:
  """Read-only hint; the action must acquire its own exclusive lease."""
  try:
    fd = os.open(learning_lock_path(params), os.O_RDONLY)
  except FileNotFoundError:
    return True
  except OSError:
    return False
  try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return True
  except OSError:
    return False
  finally:
    os.close(fd)


def learning_snapshot(params) -> LearningSnapshot:
  sources, readable = _sources(params)
  current, legacy, master = (raw for _key, raw in sources)
  loaded = _loaded(sources)
  valid = readable and loaded.valid
  idle = _idle(params)
  allowed = readable and master in (None, b'0', b'1') and idle
  reason = ('unreadable_learning' if not readable else 'invalid_curve_switch' if master not in (None, b'0', b'1') else
            'learning_active' if not idle else loaded.reason)
  return LearningSnapshot(sources, readable, valid, reason,
                          loaded.curve.progress if valid else None,
                          loaded.curve.average_comfort if valid else None,
                          bool(loaded.curve.document()['buckets']) if valid else False,
                          allowed and (bool(loaded.curve.document()['buckets']) if valid else current is not None or legacy is not None))


def apply_learning(params, kind: str, expected_sources: tuple[tuple[str, bytes | None], ...], *,
                   authorized: Callable[[], bool]) -> ActionResult:
  """Caller owns confirmation. Fresh authority and exact sources are rechecked.

  Lock ordering is learning lease, then the ordinary Params root lock. Both
  acquisitions are nonblocking, keeping a parked UI action bounded under load.
  Legacy bytes and the saved master are never changed. Reset writes an empty
  canonical document so preserved legacy learning cannot become active again.
  """
  if kind not in ACTION_KEYS or not authorized():
    return ActionResult(False, 'unavailable')
  sources, readable = _sources(params)
  if not readable or sources != expected_sources:
    return ActionResult(False, 'source_changed')
  current, legacy, master = (raw for _key, raw in sources)
  if master not in (None, b'0', b'1'):
    return ActionResult(False, 'invalid_curve_switch')
  loaded = _loaded(sources)
  if kind == 'curve_reset' and current is None and legacy is None:
    return ActionResult(False, 'no_saved_learning')
  document = LearnedCurve().document()
  raw = json.dumps(document, allow_nan=False, separators=(',', ':')).encode()
  lease = acquire_learning_lease(params)
  if lease is None:
    return ActionResult(False, 'learning_active')
  lock_fd = None
  temporary = None
  committed = False
  try:
    destination = Path(params.get_param_path(DOCUMENT_KEY))
    root = destination.parent.parent
    with tempfile.NamedTemporaryFile(prefix='.tmp_curve_action_', dir=root, delete=False) as staging:
      temporary = staging.name
      staging.write(raw)
      staging.flush()
      os.fsync(staging.fileno())
    lock_fd = os.open(root / '.lock', os.O_CREAT | os.O_RDONLY, 0o775)
    try:
      fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
      return ActionResult(False, 'storage_busy')
    actual, readable = _sources(params)
    if not readable or actual != expected_sources:
      return ActionResult(False, 'source_changed')
    if not authorized():
      return ActionResult(False, 'unavailable')
    os.replace(temporary, destination)
    temporary = None
    committed = True
    directory_fd = os.open(destination.parent, os.O_RDONLY)
    try:
      os.fsync(directory_fd)
    finally:
      os.close(directory_fd)
    actual, readable = read_saved(params, DOCUMENT_KEY, DOCUMENT_LIMIT)
    if not readable or actual != raw:
      return ActionResult(True, 'verification_failed')
    return ActionResult(True, 'saved')
  except (OSError, ValueError, TypeError, RuntimeError):
    return ActionResult(committed, 'sync_failed' if committed else 'write_failed')
  finally:
    if lock_fd is not None:
      os.close(lock_fd)
    os.close(lease)
    if temporary is not None:
      try:
        os.unlink(temporary)
      except FileNotFoundError:
        pass
