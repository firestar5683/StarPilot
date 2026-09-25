"""Explicit approval for a head unit pairing with StarPilot in the phone role."""
from __future__ import annotations

import threading
from collections.abc import Callable

from openpilot.starpilot.bluetooth.owner import PairingSession

HFP_AUDIO_GATEWAY = '0000111f-0000-1000-8000-00805f9b34fb'


class IncomingPairing:
  def __init__(self, identity: tuple, *, devices: Callable[[], list[dict]], live: Callable[[], bool],
               clock: Callable[[], float], deadline: float):
    self.identity, self.devices, self.live, self.clock, self.deadline = identity, devices, live, clock, deadline
    self.lock = threading.RLock()
    self.session: PairingSession | None = None
    self.name = ''
    self.approved_address = ''
    self.closed = False

  def _current(self) -> bool:
    return not self.closed and self.live() and self.clock() < self.deadline

  def _candidate(self, path: str) -> PairingSession | None:
    if not self._current():
      return None
    device = next((device for device in self.devices() if device['path'] == path), None)
    if device is None:
      return None
    with self.lock:
      if self.session is None:
        if device['paired']:
          return None
        self.session = PairingSession(self.identity, device['address'], path, self._current, self.clock)
        self.session.deadline = min(self.session.deadline, self.deadline)
        self.name = device['name']
      if self.session.path != path or self.session.address != device['address']:
        return None
      return self.session

  def handle(self, member: str, body: tuple) -> tuple[bool, str | None, tuple]:
    """Validate one BlueZ Agent1 call; a prompt response is required before approval."""
    if member in ('Release', 'Cancel'):
      if body:
        return False, None, ()
      self.close()
      return True, None, ()
    if not body or type(body[0]) is not str:
      return False, None, ()
    session = self._candidate(body[0])
    if session is None:
      return False, None, ()
    path = body[0]
    allowed, value, signature = False, '', None
    if member == 'RequestPinCode' and len(body) == 1:
      allowed, value = session.ask('pin', path)
      signature = 's'
    elif member == 'RequestPasskey' and len(body) == 1:
      allowed, value = session.ask('passkey', path)
      signature = 'u'
    elif member == 'RequestConfirmation' and len(body) == 2 and type(body[1]) is int and 0 <= body[1] <= 999999:
      allowed, _ = session.ask('confirmation', path, f'{body[1]:06d}')
    elif member == 'RequestAuthorization' and len(body) == 1:
      allowed, _ = session.ask('authorization', path)
    elif member == 'AuthorizeService' and len(body) == 2 and type(body[1]) is str and \
         body[1].lower() == HFP_AUDIO_GATEWAY:
      allowed, _ = session.ask('authorization', path)
    elif member == 'DisplayPinCode' and len(body) == 2 and type(body[1]) is str and \
         1 <= len(body[1]) <= 16 and body[1].isascii() and body[1].isprintable():
      allowed = self._display(session, 'display_pin', path, body[1])
    elif member == 'DisplayPasskey' and len(body) == 3 and type(body[1]) is int and \
         0 <= body[1] <= 999999 and type(body[2]) is int and 0 <= body[2] <= 6:
      allowed = self._display(session, 'display_passkey', path, f'{body[1]:06d}')
    if allowed and self._current():
      with self.lock:
        self.approved_address = session.address
      return True, signature, (int(value),) if signature == 'u' else (value,) if signature == 's' else ()
    return False, None, ()

  def _display(self, session: PairingSession, kind: str, path: str, value: str) -> bool:
    # A display-only BlueZ callback must not silently approve an unknown receiver.
    if self.approved_address != session.address:
      allowed, _ = session.ask('authorization', path)
      if not allowed:
        return False
    return session.display(kind, path, value)

  def respond(self, identity: tuple, prompt_id: str, accepted: bool, value: str = '') -> bool:
    with self.lock:
      session = self.session
    return bool(self._current() and session and session.respond(identity, prompt_id, accepted, value))

  def status(self) -> dict:
    with self.lock:
      session = self.session
      if session is not None:
        with session.condition:
          prompt = dict(session.prompt) if session.prompt else None
      else:
        prompt = None
      return {'active': self._current(), 'receiver': {'address': session.address, 'name': self.name} if session else None,
              'prompt': prompt, 'approved': bool(self.approved_address)}

  def close(self) -> None:
    with self.lock:
      self.closed = True
      if self.session is not None:
        self.session.cancel()
        self.session.close_callbacks()
