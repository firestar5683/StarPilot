from collections import OrderedDict
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")

_MISSING = object()


class LRUCache(Generic[K, V]):
  """Small bounded LRU cache.

  Unlike an unbounded dict, this caps retained entries so callers that pass
  per-frame-varying keys cannot grow memory without limit.
  """

  def __init__(self, maxsize: int) -> None:
    if maxsize <= 0:
      raise ValueError("maxsize must be positive")
    self.maxsize = maxsize
    self._cache: OrderedDict[K, V] = OrderedDict()

  def __contains__(self, key: K) -> bool:
    return key in self._cache

  def get(self, key: K, default: V | None = None) -> V | None:
    value = self._cache.get(key, _MISSING)
    if value is _MISSING:
      return default
    self._cache.move_to_end(key)
    return value

  def __getitem__(self, key: K) -> V:
    value = self._cache[key]
    self._cache.move_to_end(key)
    return value

  def __setitem__(self, key: K, value: V) -> None:
    if key in self._cache:
      self._cache.move_to_end(key)
    self._cache[key] = value
    if len(self._cache) > self.maxsize:
      self._cache.popitem(last=False)

  def __len__(self) -> int:
    return len(self._cache)

  def clear(self) -> None:
    self._cache.clear()
