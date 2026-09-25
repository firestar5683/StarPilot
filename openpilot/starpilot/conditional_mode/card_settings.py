"""Worker-verified settings with one read-only, frame-local Card view.

The live settings worker reads proactively on its existing ~100 ms cadence.
Only conditional/Switchback proposals depend on this view: stale, busy or failed
reads deny those proposals without changing ordinary control or AOL authority.
Replay continues to use the synchronous source-clock owner.
"""

from dataclasses import dataclass
from typing import Any

from openpilot.starpilot.conditional_mode.runtime_settings import (
  REVERIFY_NS, ConditionalSettingsOwner, SettingsSnapshot,
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

  def adopt(self, observation: CardSettingsObservation) -> None:
    # Latch the whole immutable source once per frame. The worker never writes
    # this view; all consumers within that frame see the same revision.
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
