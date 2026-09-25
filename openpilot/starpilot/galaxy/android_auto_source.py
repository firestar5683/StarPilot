"""Opaque, revocable bridge from an authenticated Galaxy session to android_autod."""
from __future__ import annotations

import re
import secrets
import threading
import time
from collections.abc import Callable

SOURCE_ID = re.compile(r'[0-9a-f]{64}\Z')


class GalaxySourceRegistry:
  LIFETIME = 180.0
  MAX_SOURCES = 64

  def __init__(self, session_valid: Callable[[tuple], bool], clock=time.monotonic):
    self.session_valid, self.clock = session_valid, clock
    self.lock = threading.Lock()
    self.sources: dict[str, tuple[tuple, float]] = {}

  def mint(self, identity: tuple) -> str:
    if not self.session_valid(identity):
      raise ValueError('Galaxy session expired')
    with self.lock:
      self._prune()
      if len(self.sources) >= self.MAX_SOURCES:
        raise ValueError('Too many Android Auto pairing requests')
      source = secrets.token_hex(32)
      self.sources[source] = (identity, self.clock() + self.LIFETIME)
      return source

  def _prune(self) -> None:
    now = self.clock()
    self.sources = {key: value for key, value in self.sources.items() if value[1] > now}

  def valid(self, source: str) -> bool:
    if not isinstance(source, str) or not SOURCE_ID.fullmatch(source):
      return False
    with self.lock:
      self._prune()
      entry = self.sources.get(source)
      if entry is None:
        return False
      if not self.session_valid(entry[0]):
        self.sources.pop(source, None)
        return False
      return True

  def current(self, identity: tuple) -> str | None:
    if not self.session_valid(identity):
      return None
    with self.lock:
      self._prune()
      return next((source for source, entry in reversed(tuple(self.sources.items())) if entry[0] == identity), None)

  def revoke(self, identity: tuple) -> None:
    with self.lock:
      self.sources = {key: value for key, value in self.sources.items() if value[0] != identity}

  def revoke_source(self, source: str) -> None:
    with self.lock:
      self.sources.pop(source, None)
