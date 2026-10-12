"""Authenticated projection of the existing parked vehicle-selection owner."""

from dataclasses import dataclass
import hashlib
import secrets
import threading
import time

from openpilot.starpilot.vehicle_selection import VehicleSelectionOwner


class VehicleSelectionChanged(Exception):
  pass


class VehicleSelectionUnverified(Exception):
  pass


@dataclass(frozen=True)
class _View:
  session: bytes
  generation: bytes
  raw: bytes | None
  valid: bool
  expires: float


@dataclass(frozen=True)
class _Intent:
  session: bytes
  generation: bytes
  raw: bytes | None
  platform: str | None
  expires: float


class VehicleSelectionGateway:
  MAX_PENDING = 64
  TTL_SECONDS = 60.0

  def __init__(self, params, context, *, clock=time.monotonic):
    self.params = params
    self.context = context
    self.clock = clock
    self.lock = threading.Lock()
    self.owner = VehicleSelectionOwner(params, context.parked)
    self.catalog = self.owner.choices()
    self.by_platform = {str(choice.platform): choice for choice in self.catalog}
    self.views: dict[str, _View] = {}
    self.intents: dict[str, _Intent] = {}

  def close(self) -> None:
    close = getattr(self.context, 'close', None)
    if callable(close):
      close()

  def _clean(self) -> None:
    now = self.clock()
    self.views = {key: item for key, item in self.views.items() if item.expires > now}
    self.intents = {key: item for key, item in self.intents.items() if item.expires > now}

  @staticmethod
  def _session(token: str) -> bytes:
    return hashlib.sha256(token.encode('ascii')).digest()

  def page(self, token: str, generation: bytes) -> dict:
    saved = self.owner.snapshot()
    parked = self.context.parked()
    reported = None
    try:
      cp = self.context.sample().cp
      platform = str(cp.carFingerprint) if cp is not None else ''
      if not cp.notCar and platform in self.by_platform:
        choice = self.by_platform[platform]
        reported = {'platform': platform, 'make': str(choice.make), 'label': str(choice.label)}
    except (AttributeError, TypeError, ValueError, OSError, RuntimeError):
      pass
    view = None
    if saved.readable:
      with self.lock:
        self._clean()
        if len(self.views) >= self.MAX_PENDING:
          self.views.pop(next(iter(self.views)))
        view = secrets.token_urlsafe(24)
        self.views[view] = _View(self._session(token), generation, saved.raw, saved.valid, self.clock() + self.TTL_SECONDS)
    selected = self.by_platform.get(str(saved.platform)) if saved.valid and saved.platform is not None else None
    return {'version': 1, 'parked': parked, 'readable': saved.readable, 'valid': saved.valid,
            'selected': str(saved.platform) if selected is not None else None,
            'selectedLabel': str(selected.label) if selected is not None else 'Auto detection' if saved.valid else
                             'Needs review' if saved.readable else 'Unavailable',
            'reported': reported, 'view': view,
            'choices': [{'platform': str(choice.platform), 'make': str(choice.make), 'label': str(choice.label)}
                        for choice in self.catalog]}

  def preview(self, view_id: str, platform: str | None, token: str, generation: bytes) -> dict:
    if platform is not None and (type(platform) is not str or platform not in self.by_platform):
      raise ValueError('Invalid vehicle')
    with self.lock:
      self._clean()
      view = self.views.get(view_id)
    if view is None or view.session != self._session(token) or view.generation != generation:
      raise VehicleSelectionChanged('Refresh vehicle selection')
    saved = self.owner.snapshot()
    if not saved.readable or saved.raw != view.raw or saved.valid != view.valid or not self.context.parked():
      raise VehicleSelectionChanged('Vehicle selection changed')
    if not saved.valid and platform is not None:
      raise VehicleSelectionChanged('Restore Auto detection first')
    with self.lock:
      self._clean()
      if len(self.intents) >= self.MAX_PENDING:
        self.intents.pop(next(iter(self.intents)))
      intent = secrets.token_urlsafe(24)
      self.intents[intent] = _Intent(view.session, generation, view.raw, platform, self.clock() + self.TTL_SECONDS)
    label = self.by_platform[platform].label if platform is not None else 'Auto detection'
    return {'intent': intent, 'question': f'Save {label} for the next start?', 'selected': platform, 'label': str(label)}

  def confirm(self, intent_id: str, token: str, generation: bytes, *, session_valid=lambda: True) -> bool:
    with self.lock:
      self._clean()
      intent = self.intents.pop(intent_id, None)
    if intent is None or intent.session != self._session(token) or intent.generation != generation or not session_valid():
      raise VehicleSelectionChanged('Refresh vehicle selection')
    current = self.owner.snapshot()
    if not current.readable or current.raw != intent.raw or not self.context.parked():
      raise VehicleSelectionChanged('Vehicle selection changed')
    owner = VehicleSelectionOwner(self.params, lambda: self.context.parked() and session_valid())
    result = owner.choose(intent.raw, intent.platform)
    if not result.verified:
      if result.committed:
        raise VehicleSelectionUnverified('Vehicle selection may have been saved')
      raise VehicleSelectionChanged('Vehicle selection could not be confirmed')
    saved = self.owner.snapshot()
    if not saved.readable or not saved.valid or saved.platform != intent.platform:
      raise VehicleSelectionChanged('Vehicle selection could not be confirmed')
    return True
