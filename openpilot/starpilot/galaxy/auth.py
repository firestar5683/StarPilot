"""Bounded, process-local browser sessions for loopback Galaxy diagnostics."""

import hashlib
import hmac
import secrets
import time
from collections.abc import Callable


class LocalSessions:
  LIFETIME = 30 * 60
  MAX_SESSIONS = 64
  MAX_FAILURES = 5
  FAILURE_PAUSE = 30

  def __init__(self, clock: Callable[[], float] = time.monotonic):
    self.clock = clock
    self._sessions: dict[bytes, tuple[float, bytes]] = {}
    self._failures = 0
    self._blocked_until = 0.0

  @staticmethod
  def _key(token: str) -> bytes:
    return hashlib.sha256(token.encode('ascii')).digest()

  def _expire(self) -> None:
    now = self.clock()
    self._sessions = {key: value for key, value in self._sessions.items() if value[0] > now}

  def throttled(self) -> bool:
    if self._failures >= self.MAX_FAILURES and self.clock() < self._blocked_until:
      return True
    if self._blocked_until > 0 and self.clock() >= self._blocked_until:
      self._failures = 0
      self._blocked_until = 0.0
    return False

  def failed_login(self) -> None:
    self._failures += 1
    if self._failures >= self.MAX_FAILURES:
      self._blocked_until = self.clock() + self.FAILURE_PAUSE

  def create(self, generation: bytes, *, reset_failures: bool = True) -> str:
    self._expire()
    if len(self._sessions) >= self.MAX_SESSIONS:
      oldest = min(self._sessions, key=lambda key: self._sessions[key][0])
      self._sessions.pop(oldest)
    token = secrets.token_urlsafe(32)
    self._sessions[self._key(token)] = (self.clock() + self.LIFETIME, generation)
    if reset_failures:
      self._failures = 0
    return token

  def valid(self, token: str | None, generation: bytes | None) -> bool:
    if token is None or generation is None or len(token) > 128 or not token.isascii():
      return False
    self._expire()
    session = self._sessions.get(self._key(token))
    return bool(session is not None and hmac.compare_digest(session[1], generation))

  def revoke(self, token: str | None) -> None:
    if token is not None and len(token) <= 128 and token.isascii():
      self._sessions.pop(self._key(token), None)
