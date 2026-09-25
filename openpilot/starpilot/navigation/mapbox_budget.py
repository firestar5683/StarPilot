"""Track Mapbox usage and cap services with a free monthly allowance.

Requests are counted on the comma; capped flows stop at 99% of the
free tier for the calendar month (UTC, as Mapbox bills). The last 1% absorbs
small differences between this count and Mapbox's (sessions Mapbox splits on its
own, counts not yet written when a process restarts). Requests made with the
same key elsewhere (another comma, a web page) are not seen here. Counts persist across
restarts. One file per service, written only by the process that uses it.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path

# Free monthly allowances (mapbox.com/pricing, 2026-10).
FREE = {
  "searchSessions": 500,       # Search Box API sessions (typing and searching)
  "geocoding": 0,              # Permanent address results have no free tier; counted, not capped
  "staticTiles": 200_000,      # Static Tiles API (Galaxy's map pictures)
  "directions": 100_000,       # Directions API (routes)
  "vectorTiles": 200_000,      # Vector Tiles API (offline road maps)
}
STOP_FRACTION = 0.99
LABELS = {"searchSessions": "searches", "geocoding": "address lookups", "staticTiles": "map views", "directions": "routes", "vectorTiles": "offline map tiles"}


class BudgetExhausted(RuntimeError):
  pass


def usage_root() -> Path:
  from openpilot.starpilot.storage import starpilot_storage_root
  return starpilot_storage_root() / "navigation" / "mapbox-usage"


def _month(wall: float) -> str:
  return time.strftime("%Y-%m", time.gmtime(wall))


class MonthlyBudget:
  def __init__(self, service: str, root: Path | None = None, clock=time.time, flush_every: int = 1):  # noqa: TID251 - calendar months
    if service not in FREE:
      raise ValueError("Unknown Mapbox service")
    self.service = service
    self.path = Path(root if root is not None else usage_root()) / f"{service}.json"
    self.clock = clock
    self.flush_every = flush_every
    self.limit = int(FREE[service] * STOP_FRACTION)
    self._lock = threading.Lock()
    self._dirty = 0
    self.month, self.used = _month(clock()), 0
    try:
      value = json.loads(self.path.read_text())
      if isinstance(value, dict) and value.get("month") == self.month and type(value.get("used")) is int and value["used"] >= 0:
        self.used = value["used"]
    except (OSError, ValueError):
      pass

  def _roll(self) -> None:
    month = _month(self.clock())
    if month != self.month:
      self.month, self.used, self._dirty = month, 0, 1

  def remaining(self) -> int:
    with self._lock:
      self._roll()
      return max(0, self.limit - self.used)

  def spend(self, count: int = 1, *, enforce: bool = True) -> None:
    """Count requests about to be made, or refuse them when the free allowance is used up.

    ``enforce=False`` only counts: for upstream flows that keep their own behavior,
    so the total stays accurate for the flows that are capped."""
    with self._lock:
      self._roll()
      if enforce and self.used + count > self.limit:
        raise BudgetExhausted(f"This month's free Mapbox {LABELS[self.service]} are used up. They reset on the 1st.")
      self.used += count
      self._dirty += count
      if self._dirty >= self.flush_every:
        self._flush_locked()

  def snapshot(self) -> dict:
    with self._lock:
      self._roll()
      return {"month": self.month, "used": self.used, "limit": self.limit, "free": FREE[self.service]}

  def flush(self) -> None:
    with self._lock:
      self._flush_locked()

  def _flush_locked(self) -> None:
    if not self._dirty:
      return
    try:
      self.path.parent.mkdir(parents=True, exist_ok=True)
      fd, temp = tempfile.mkstemp(dir=self.path.parent, prefix=".tmp-")
      with os.fdopen(fd, "w") as handle:
        json.dump({"month": self.month, "used": self.used}, handle)
      os.replace(temp, self.path)
      self._dirty = 0
    except OSError:
      pass  # counting continues in memory; the next write retries


def read_usage(root: Path | None = None, clock=time.time) -> dict:  # noqa: TID251 - calendar months
  """This month's counts for display, read fresh from each service's file."""
  root = Path(root if root is not None else usage_root())
  month = _month(clock())
  result = {}
  for service in ("searchSessions", "geocoding", "staticTiles", "directions"):
    used = 0
    try:
      value = json.loads((root / f"{service}.json").read_text())
      if isinstance(value, dict) and value.get("month") == month and type(value.get("used")) is int:
        used = max(0, value["used"])
    except (OSError, ValueError):
      pass
    result[service] = {"used": used, "limit": int(FREE[service] * STOP_FRACTION), "free": FREE[service]}
  return result
