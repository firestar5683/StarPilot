"""Small, shared cache for read-mostly UI parameters.

Parameter reads are file-backed.  The raylib UIs ask for the same values from
multiple widgets during a frame, so a short cache avoids repeated open/read/
close cycles without making settings changes sticky: every write invalidates
the affected key immediately and the short TTL bounds visibility of writes
from other processes.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from openpilot.common.params import Params


class UIParamCache:
  def __init__(self, params: Params | Any | None = None, ttl: float = 0.1,
               clock: Callable[[], float] = time.monotonic):
    self._params = params if params is not None else Params()
    self._ttl = max(0.0, ttl)
    self._clock = clock
    self._cache: dict[tuple[Any, ...], tuple[float, Any]] = {}

  @staticmethod
  def _cache_key(method: str, key: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, ...]:
    # Params arguments are primitive values in UI call sites. repr keeps this
    # robust for an occasional list/dict default without requiring hashability.
    return (method, key, repr(args), repr(sorted(kwargs.items())))

  def _read(self, method: str, key: str, *args: Any, **kwargs: Any) -> Any:
    cache_key = self._cache_key(method, key, args, kwargs)
    now = self._clock()
    cached = self._cache.get(cache_key)
    if cached is not None and now - cached[0] < self._ttl:
      return cached[1]

    value = getattr(self._params, method)(key, *args, **kwargs)
    self._cache[cache_key] = (now, value)
    return value

  def get(self, key: str, *args: Any, **kwargs: Any) -> Any:
    return self._read("get", key, *args, **kwargs)

  def get_bool(self, key: str, *args: Any, **kwargs: Any) -> bool:
    return self._read("get_bool", key, *args, **kwargs)

  def get_int(self, key: str, *args: Any, **kwargs: Any) -> int:
    return self._read("get_int", key, *args, **kwargs)

  def get_float(self, key: str, *args: Any, **kwargs: Any) -> float:
    return self._read("get_float", key, *args, **kwargs)

  def invalidate(self, key: str | None = None) -> None:
    if key is None:
      self._cache.clear()
      return
    self._cache = {cache_key: value for cache_key, value in self._cache.items()
                   if cache_key[1] != key}

  def put(self, key: str, value: Any, *args: Any, **kwargs: Any) -> None:
    self._params.put(key, value, *args, **kwargs)
    self.invalidate(key)

  def put_bool(self, key: str, value: bool, *args: Any, **kwargs: Any) -> None:
    self._params.put_bool(key, value, *args, **kwargs)
    self.invalidate(key)

  def put_int(self, key: str, value: int, *args: Any, **kwargs: Any) -> None:
    self._params.put_int(key, value, *args, **kwargs)
    self.invalidate(key)

  def put_float(self, key: str, value: float, *args: Any, **kwargs: Any) -> None:
    self._params.put_float(key, value, *args, **kwargs)
    self.invalidate(key)

  def put_nonblocking(self, key: str, value: Any) -> None:
    self._params.put_nonblocking(key, value)
    self.invalidate(key)

  def put_bool_nonblocking(self, key: str, value: bool) -> None:
    self._params.put_bool_nonblocking(key, value)
    self.invalidate(key)

  def remove(self, key: str) -> None:
    self._params.remove(key)
    self.invalidate(key)

  def clear_all(self, *args: Any, **kwargs: Any) -> None:
    self._params.clear_all(*args, **kwargs)
    self.invalidate()

  def __getattr__(self, name: str) -> Any:
    return getattr(self._params, name)


_SHARED_UI_PARAMS: UIParamCache | None = None


def shared_ui_params() -> UIParamCache:
  """Return the cache shared by raylib UI views and settings panels."""
  global _SHARED_UI_PARAMS
  if _SHARED_UI_PARAMS is None:
    _SHARED_UI_PARAMS = UIParamCache()
  return _SHARED_UI_PARAMS
