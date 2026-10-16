"""Worker-verified settings with one read-only, frame-local Card view.

The live settings worker reads proactively on its existing ~100 ms cadence.
Only conditional/Switchback proposals depend on this view: stale, busy or failed
reads deny those proposals without changing ordinary control or AOL authority.
Replay continues to use the synchronous source-clock owner.
"""

from dataclasses import dataclass
from typing import Any

from openpilot.starpilot.conditional_mode.preferences import CCMOptions, CEMOptions, ModeSelection, SavedPreferences
from openpilot.starpilot.conditional_mode.runtime_settings import (
  REVERIFY_NS, ConditionalSettingsOwner, DocumentState, SafeModeState, SettingsSnapshot,
)


@dataclass(frozen=True)
class CardSettingsObservation:
  snapshot: SettingsSnapshot | None
  status: str
  read_started_ns: int


class CardSettingsView(ConditionalSettingsOwner):
  """Main-thread-only view. refresh/affirm never touch the filesystem."""

  def __init__(self, owner_token: str):
    super().__init__(None)
    self.owner_token = owner_token
    self.unavailable = self._unavailable(0)
    self._selection_cache = None
    self._fingerprint_cache = None

  def adopt(self, observation: CardSettingsObservation) -> None:
    # Latch the whole immutable source once per frame. The worker never writes
    # this view; all consumers within that frame see the same revision.
    self._selection_cache = None
    self._fingerprint_cache = None
    snapshot = observation.snapshot
    self.current = (snapshot if observation.status == 'verified' and
                    type(snapshot) is SettingsSnapshot and snapshot.owner_token == self.owner_token
                    else self.unavailable)

  def refresh(self, now_mono_ns: int, *, force: bool = False, wait: bool = False) -> SettingsSnapshot:
    assert self.current is not None
    return self.current

  def affirm(self, snapshot: SettingsSnapshot | None, *, now_mono_ns: int) -> bool:
    current = self.current
    return bool(current is not None and type(now_mono_ns) is int and
                0 <= now_mono_ns - current.verified_mono_ns < REVERIFY_NS and
                super().affirm(snapshot, now_mono_ns=now_mono_ns))

  @staticmethod
  def _preference_fields(snapshot: SettingsSnapshot):
    try:
      preferences = snapshot.preferences
      if (type(preferences) is not SavedPreferences or type(preferences.cem) is not CEMOptions or
          type(preferences.ccm) is not CCMOptions):
        return None
      cem, ccm = preferences.cem, preferences.ccm
      # Each successful derivation validated exact immutable scalars. Identity
      # checks also notice deliberate object.__setattr__ fixture mutations.
      return (preferences, cem, ccm, preferences.version, preferences.mode,
              cem.speed_mps, cem.speed_with_lead_mps, cem.signal_speed_mps,
              cem.open_road, cem.curves, cem.curves_with_lead, cem.lead, cem.slower_lead,
              cem.stopped_lead, cem.stop_lights, cem.model_stop_s, cem.signal_lane_detection,
              cem.signal_lane_width_m, cem.persist_manual, ccm.speed_mps, ccm.speed_with_lead_mps,
              ccm.set_speed_margin_mps, ccm.lead, ccm.launch_assist, ccm.persist_manual)
    except AttributeError:
      return None

  def _selection_for_drive(self, snapshot: SettingsSnapshot, drive_id: int) -> ModeSelection | None:
    # verdict still checks the current owner, revision, SafeMode and clock on
    # every call. Only its pure post-affirmation derivation may be reused.
    if (type(self) is not CardSettingsView or type(snapshot) is not SettingsSnapshot or
        snapshot is not self.current or type(drive_id) is not int or drive_id <= 0):
      return super()._selection_for_drive(snapshot, drive_id)
    key = self._preference_fields(snapshot)
    if key is None:
      return super()._selection_for_drive(snapshot, drive_id)
    cached = self._selection_cache
    if cached is not None and cached[0] == drive_id and all(a is b for a, b in zip(key, cached[1], strict=True)):
      return cached[2]
    selection = super()._selection_for_drive(snapshot, drive_id)
    self._selection_cache = (drive_id, key, selection)
    return selection

  def fingerprint(self, snapshot: SettingsSnapshot | None) -> str | None:
    from openpilot.starpilot.conditional_mode.status import _settings_fingerprint

    if (type(self) is not CardSettingsView or type(snapshot) is not SettingsSnapshot or
        snapshot is not self.current or type(snapshot.document_state) is not DocumentState or
        type(snapshot.safe_mode_state) is not SafeModeState or
        snapshot.document_raw is not None and type(snapshot.document_raw) is not bytes or
        snapshot.safe_mode_raw is not None and type(snapshot.safe_mode_raw) is not bytes):
      return _settings_fingerprint(snapshot)
    key = (snapshot.document_state, snapshot.safe_mode_state, snapshot.document_raw, snapshot.safe_mode_raw)
    cached = self._fingerprint_cache
    if cached is not None and all(a is b for a, b in zip(key, cached[0], strict=True)):
      return cached[1]
    fingerprint = _settings_fingerprint(snapshot)
    self._fingerprint_cache = (key, fingerprint)
    return fingerprint


class CardSettingsWorker:
  """One worker-owned reader and an atomically replaced immutable publication."""

  def __init__(self, params: Any):
    self.reader = ConditionalSettingsOwner(params)
    self.view = CardSettingsView(self.reader.owner_token)
    self.published = CardSettingsObservation(None, 'startup', 0)

  def refresh(self, read_started_ns: int) -> None:
    # The caller samples MONOTONIC before I/O. Slow reads never receive a fresh
    # completion timestamp. A stalled worker cannot renew the view's authority.
    previous = self.reader.current
    try:
      snapshot = self.reader.refresh(read_started_ns, force=True)
      # With force=True only a busy writer lock returns the previous object.
      # Do not carry the old owner's one-second busy-lock permission extension.
      observation = CardSettingsObservation(None, 'busy', read_started_ns) if snapshot is previous else \
                    CardSettingsObservation(snapshot, 'verified', read_started_ns)
    except Exception:
      # Observational settings failure must neither kill the worker nor escape
      # into Card. Missing publication remains restrictive until a good read.
      observation = CardSettingsObservation(None, 'error', read_started_ns)
    self.published = observation

  def adopt(self) -> None:
    self.view.adopt(self.published)
