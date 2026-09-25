"""Read-only, bounded-refresh owner for saved conditional-mode preferences.

The caller supplies monotonic observation time and invokes refresh off the
control-frame cadence. A current owner revision must be affirmed each sample;
neither this owner nor the codec writes Params or adopts legacy keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import secrets
from typing import Any

from openpilot.starpilot.conditional_mode.preferences import (
  MAX_DOCUMENT_BYTES, CCMOptions, CEMOptions, ModeSelection, PreferenceError,
  SavedPreferences, decode_preferences, saved_selection_for_drive,
)
from openpilot.starpilot.saved_source import read_saved


DOCUMENT_KEY = 'ConditionalModeConfig'
SAFE_MODE_KEY = 'SafeMode'
REFRESH_NS = 1_000_000_000
REVERIFY_NS = REFRESH_NS // 2


class DocumentState(StrEnum):
  ABSENT = 'absent'
  VALID = 'valid'
  INVALID = 'invalid'
  READ_ERROR = 'read_error'


class SafeModeState(StrEnum):
  ABSENT_FALSE = 'absent_false'
  FALSE = 'false'
  TRUE = 'true'
  INVALID = 'invalid'
  READ_ERROR = 'read_error'


@dataclass(frozen=True)
class SettingsSnapshot:
  owner_token: str
  revision: int
  observed_mono_ns: int
  verified_mono_ns: int
  document_state: DocumentState
  safe_mode_state: SafeModeState
  document_raw: bytes | None
  safe_mode_raw: bytes | None
  preferences: SavedPreferences | None


@dataclass(frozen=True)
class SettingsVerdict:
  status: str
  revision: int | None
  observed_mono_ns: int | None
  selection: ModeSelection | None
  cem: CEMOptions | None
  ccm: CCMOptions | None
  safe_mode: bool | None


def _read(params: Any, key: str, limit: int) -> tuple[bytes | None, bool]:
  try:
    return read_saved(params, key, limit)
  except (OSError, TypeError, ValueError):
    return b'', False


def _document(raw: bytes | None, readable: bool) -> tuple[DocumentState, SavedPreferences | None]:
  if not readable:
    return DocumentState.READ_ERROR, None
  if raw is None:
    return DocumentState.ABSENT, SavedPreferences()
  try:
    return DocumentState.VALID, decode_preferences(raw)
  except PreferenceError:
    return DocumentState.INVALID, None


def _safe_mode(raw: bytes | None, readable: bool) -> SafeModeState:
  if not readable:
    return SafeModeState.READ_ERROR
  if raw is None:
    return SafeModeState.ABSENT_FALSE
  if raw == b'0':
    return SafeModeState.FALSE
  if raw == b'1':
    return SafeModeState.TRUE
  return SafeModeState.INVALID


class ConditionalSettingsOwner:
  """One in-memory revision, reread before its one-second authority expires."""

  def __init__(self, params: Any):
    self.params = params
    self.owner_token = secrets.token_hex(16)
    self.current: SettingsSnapshot | None = None
    self.last_refresh_ns: int | None = None

  def _unavailable(self, now_mono_ns: int) -> SettingsSnapshot:
    previous = self.current
    snapshot = SettingsSnapshot(
      self.owner_token, 1 if previous is None else previous.revision + 1,
      now_mono_ns, now_mono_ns, DocumentState.READ_ERROR, SafeModeState.READ_ERROR,
      None, None, None,
    )
    self.current = snapshot
    self.last_refresh_ns = now_mono_ns
    return snapshot

  def refresh(self, now_mono_ns: int) -> SettingsSnapshot:
    """Perform a bounded disk read when due; errors invalidate prior authority."""
    if type(now_mono_ns) is not int or now_mono_ns <= 0:
      return self._unavailable(0)
    if self.last_refresh_ns is not None and now_mono_ns < self.last_refresh_ns:
      return self._unavailable(now_mono_ns)
    if self.current is not None and self.last_refresh_ns is not None and now_mono_ns - self.last_refresh_ns < REVERIFY_NS:
      return self.current

    document_raw, document_readable = _read(self.params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    safe_raw, safe_readable = _read(self.params, SAFE_MODE_KEY, 8)
    document_state, preferences = _document(document_raw, document_readable)
    safe_state = _safe_mode(safe_raw, safe_readable)
    previous = self.current
    same_source = bool(previous is not None and previous.document_raw == document_raw and
                       previous.safe_mode_raw == safe_raw and previous.document_state is document_state and
                       previous.safe_mode_state is safe_state and previous.preferences == preferences)
    snapshot = SettingsSnapshot(
      self.owner_token,
      previous.revision if same_source and previous is not None else (1 if previous is None else previous.revision + 1),
      previous.observed_mono_ns if same_source and previous is not None else now_mono_ns,
      now_mono_ns,
      document_state, safe_state, document_raw, safe_raw, preferences,
    )
    self.current = snapshot
    self.last_refresh_ns = now_mono_ns
    return snapshot

  def affirm(self, snapshot: SettingsSnapshot | None, *, now_mono_ns: int) -> bool:
    """Validate the current owner revision without another Params read."""
    current = self.current
    return bool(
      type(snapshot) is SettingsSnapshot and current is not None and
      snapshot.owner_token == self.owner_token and snapshot.revision == current.revision and
      snapshot.observed_mono_ns == current.observed_mono_ns and
      current.document_state in (DocumentState.ABSENT, DocumentState.VALID) and
      current.safe_mode_state in (SafeModeState.ABSENT_FALSE, SafeModeState.FALSE) and
      type(now_mono_ns) is int and current.verified_mono_ns <= now_mono_ns <= current.verified_mono_ns + REFRESH_NS
    )

  def verdict(self, snapshot: SettingsSnapshot | None, *, now_mono_ns: int, drive_id: int) -> SettingsVerdict:
    """Supply saved options only while this exact owner revision is live."""
    current = self.current
    safe = (False if current is not None and current.safe_mode_state in (SafeModeState.ABSENT_FALSE, SafeModeState.FALSE)
            else True if current is not None and current.safe_mode_state is SafeModeState.TRUE else None)
    if not self.affirm(snapshot, now_mono_ns=now_mono_ns):
      status = ('read_error' if current is not None and (current.document_state is DocumentState.READ_ERROR or
                                                         current.safe_mode_state is SafeModeState.READ_ERROR) else
                'unavailable_document' if current is not None and current.document_state is DocumentState.INVALID else
                'invalid_safe_mode' if current is not None and current.safe_mode_state is SafeModeState.INVALID else
                'safe_mode' if safe is True else
                'stale_or_foreign_revision')
      return SettingsVerdict(status, current.revision if current is not None else None,
                             current.observed_mono_ns if current is not None else None,
                             None, None, None, safe)
    assert current is not None and current.preferences is not None
    selection = saved_selection_for_drive(current.preferences, drive_id)
    return SettingsVerdict('ready' if selection is not None else 'invalid_drive', current.revision,
                           current.observed_mono_ns, selection, current.preferences.cem,
                           current.preferences.ccm, safe)
