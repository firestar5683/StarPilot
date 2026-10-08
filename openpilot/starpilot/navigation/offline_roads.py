"""Road-line tiles on disk: the cache, saved drives, offline areas, and shared state.

Three tile directories, read in this order:
  saved/    tiles inside an offline area; kept until the area is deleted
  driven/   tiles near the car while "save as you drive" is on; trimmed at their own cap
  cache/    everything else the map has needed; trimmed least recently used first

State files beside them:
  areas/<id>.json   Galaxy writes definitions; navtilesd updates refresh times under the shared lock
  settings.json     save-as-you-drive (Galaxy writes)
  status.json       download progress, sizes, network and usage (navtilesd writes)
"""

from __future__ import annotations

import fcntl
import json
import math
import os
import re
import shutil
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from openpilot.starpilot.navigation.road_tiles import DATA_ZOOM, TileKey, meters_per_tile, tiles_in_radius

KINDS = ("saved", "driven", "cache")
CACHE_MAX_BYTES = 150 * 1024 * 1024
DRIVEN_MAX_BYTES = 600 * 1024 * 1024
SAVED_MAX_BYTES = 3 * 1024 ** 3
MIN_FREE_BYTES = 1024 ** 3                 # never fill /data for a map
AVERAGE_DOWNLOAD_BYTES = 38_000            # a z14 Mapbox Streets tile, all layers
AVERAGE_STORED_BYTES = 6_500               # the same tile reduced to road lines
AREA_MIN_RADIUS_KM, AREA_MAX_RADIUS_KM, AREA_DEFAULT_RADIUS_KM = 2.0, 200.0, 25.0
MAX_AREAS = 24
AREA_REFRESH_SECONDS = 120 * 24 * 3600
STATUS_STALE_SECONDS = 20.0
FREE_TILES_PER_MONTH = 200_000             # Mapbox Vector Tiles API free tier
MAX_AREA_TILES = int(FREE_TILES_PER_MONTH * 0.99)  # bound planning memory as well as a month's downloads
_ID = re.compile(r"[0-9a-f]{32}\Z")


def roads_root() -> Path:
  if os.path.isdir("/data/media/0"):
    from openpilot.starpilot.maps.storage import STORAGE_ANCHOR, offline_root
    return offline_root(STORAGE_ANCHOR).parent / "roads"
  from openpilot.starpilot.storage import starpilot_storage_root
  return starpilot_storage_root() / "maps/roads"


def _wall() -> float:
  return time.time()  # noqa: TID251 - persisted timestamps must survive reboots


def write_json(path: Path, value: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
  try:
    with os.fdopen(fd, "w") as handle:
      json.dump(value, handle, separators=(",", ":"), allow_nan=False)
    os.replace(temp, path)
  except BaseException:
    Path(temp).unlink(missing_ok=True)
    raise


def read_json(path: Path, limit: int = 1 << 20) -> Any:
  try:
    with path.open("rb") as handle:
      raw = handle.read(limit + 1)
    return None if len(raw) > limit else json.loads(raw)
  except (OSError, ValueError):
    return None


# ---------------------------------------------------------------- tiles

def _existing_ancestor(path: Path) -> Path:
  while not path.exists() and path != path.parent:
    path = path.parent
  return path


class TileStore:
  def __init__(self, root: Path | None = None, min_free_bytes: int = MIN_FREE_BYTES):
    self.root = Path(root) if root is not None else roads_root()
    self.min_free_bytes = min_free_bytes

  def path(self, kind: str, key: TileKey) -> Path:
    assert kind in KINDS
    return self.root / kind / key.path()

  def find(self, key: TileKey) -> Path | None:
    for kind in KINDS:
      path = self.path(kind, key)
      if path.is_file():
        return path
    return None

  def read(self, key: TileKey) -> bytes | None:
    path = self.find(key)
    if path is None:
      return None
    try:
      return path.read_bytes()
    except OSError:
      return None

  def has(self, kind: str, key: TileKey) -> bool:
    return self.path(kind, key).is_file()

  def age(self, kind: str, key: TileKey) -> float | None:
    try:
      return max(0.0, _wall() - self.path(kind, key).stat().st_mtime)
    except OSError:
      return None

  def write(self, kind: str, key: TileKey, data: bytes) -> bool:
    path = self.path(kind, key)
    try:
      if not self.has_space(len(data)):
        return False
      path.parent.mkdir(parents=True, exist_ok=True)
      fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".tile-")
      with os.fdopen(fd, "wb") as handle:
        handle.write(data)
      os.replace(temp, path)
    except OSError:
      return False
    if kind != "cache":
      self.path("cache", key).unlink(missing_ok=True)
    return True

  def has_space(self, size: int = 0) -> bool:
    return shutil.disk_usage(_existing_ancestor(self.root)).free >= self.min_free_bytes + size

  def promote(self, kind: str, key: TileKey) -> bool:
    """Move a tile already on disk into a longer-lived directory without downloading it."""
    target = self.path(kind, key)
    if target.is_file():
      return True
    for source_kind in KINDS[KINDS.index(kind) + 1:]:
      source = self.path(source_kind, key)
      if source.is_file():
        try:
          target.parent.mkdir(parents=True, exist_ok=True)
          os.replace(source, target)
          return True
        except OSError:
          return False
    return False

  def touch(self, key: TileKey) -> None:
    path = self.find(key)
    if path is not None and path.parent.parent.parent.name in ("cache", "driven"):
      try:
        os.utime(path, None)
      except OSError:
        pass

  def size(self, kind: str) -> int:
    total = 0
    for directory, _, names in os.walk(self.root / kind):
      for name in names:
        try:
          total += os.stat(os.path.join(directory, name)).st_size
        except OSError:
          pass
    return total

  def trim(self, kind: str, max_bytes: int) -> int:
    """Delete least recently used tiles until the directory is 90% of its cap; returns its size."""
    entries = []
    for directory, _, names in os.walk(self.root / kind):
      for name in names:
        full = os.path.join(directory, name)
        try:
          info = os.stat(full)
        except OSError:
          continue
        entries.append((info.st_mtime, info.st_size, full))
    total = sum(size for _, size, _ in entries)
    if total <= max_bytes:
      return total
    for _, size, full in sorted(entries):
      if total <= max_bytes * 0.9:
        break
      try:
        os.unlink(full)
        total -= size
      except OSError:
        pass
    return total

  def clear(self, kind: str) -> None:
    shutil.rmtree(self.root / kind, ignore_errors=True)

  def demote_saved(self, keys: set[TileKey]) -> None:
    """An area was deleted: its tiles become ordinary cache, trimmed like any other."""
    for key in keys:
      source = self.path("saved", key)
      if source.is_file():
        target = self.path("cache", key)
        try:
          target.parent.mkdir(parents=True, exist_ok=True)
          os.replace(source, target)
        except OSError:
          source.unlink(missing_ok=True)


# ---------------------------------------------------------------- areas and settings

def validate_area(value: Any) -> dict:
  if not isinstance(value, dict):
    raise ValueError("Invalid offline area")
  try:
    latitude, longitude = float(value["latitude"]), float(value["longitude"])
    radius = float(value["radiusKm"])
  except (KeyError, TypeError, ValueError):
    raise ValueError("Invalid offline area") from None
  name = value.get("name", "")
  if (not math.isfinite(latitude) or not -84 <= latitude <= 84 or not math.isfinite(longitude) or
      not -180 <= longitude <= 180 or not math.isfinite(radius) or
      not AREA_MIN_RADIUS_KM <= radius <= AREA_MAX_RADIUS_KM or not isinstance(name, str) or len(name) > 80):
    raise ValueError("Choose a place and a radius between 2 and 200 km")
  if estimate(latitude, longitude, radius)["tiles"] > MAX_AREA_TILES:
    raise ValueError("Choose a smaller offline area")
  area = {"latitude": round(latitude, 6), "longitude": round(longitude, 6), "radiusKm": round(radius, 1),
          "name": " ".join(name.split()) or f"{latitude:.3f}, {longitude:.3f}"}
  for key in ("id", "created", "refreshed"):
    if key in value:
      area[key] = value[key]
  return area


def area_tiles(area: dict) -> list[TileKey]:
  return tiles_in_radius(area["latitude"], area["longitude"], area["radiusKm"] * 1000.0, DATA_ZOOM)


def estimate(latitude: float, longitude: float, radius_km: float) -> dict:
  """Tile count and sizes without listing the tiles (the area is a circle of tiles)."""
  side_km = meters_per_tile(latitude) / 1000.0
  tiles = max(1, round(math.pi * (radius_km / side_km + 0.5) ** 2))
  return {"tiles": tiles, "downloadBytes": tiles * AVERAGE_DOWNLOAD_BYTES, "storedBytes": tiles * AVERAGE_STORED_BYTES}


class OfflineState:
  def __init__(self, root: Path | None = None):
    self.root = Path(root) if root is not None else roads_root()

  @contextmanager
  def _exclusive(self):
    self.root.mkdir(parents=True, exist_ok=True)
    with (self.root / ".areas.lock").open("a") as lock:
      fcntl.flock(lock, fcntl.LOCK_EX)
      yield

  @property
  def areas_dir(self) -> Path:
    return self.root / "areas"

  def areas(self) -> list[dict]:
    result = []
    try:
      names = sorted(os.listdir(self.areas_dir))
    except OSError:
      return result
    for name in names[:MAX_AREAS * 2]:
      if not name.endswith(".json") or not _ID.fullmatch(name[:-5]):
        continue
      try:
        area = validate_area(read_json(self.areas_dir / name, 4096))
      except ValueError:
        continue
      area["id"] = name[:-5]
      result.append(area)
    return sorted(result, key=lambda area: area.get("created", 0))

  def add_area(self, value: Any) -> dict:
    area = validate_area(value)
    with self._exclusive():
      areas = self.areas()
      if len(areas) >= MAX_AREAS:
        raise ValueError(f"Up to {MAX_AREAS} offline areas can be saved")
      if sum(estimate(row["latitude"], row["longitude"], row["radiusKm"])["tiles"] for row in [*areas, area]) > MAX_AREA_TILES:
        raise ValueError("Choose a smaller area or delete an existing area")
      area.update(id=uuid.uuid4().hex, created=_wall(), refreshed=0)
      write_json(self.areas_dir / f"{area['id']}.json", area)
    return area

  def delete_area(self, area_id: str) -> None:
    if not isinstance(area_id, str) or not _ID.fullmatch(area_id):
      raise ValueError("Unknown offline area")
    with self._exclusive():
      (self.areas_dir / f"{area_id}.json").unlink(missing_ok=True)

  def mark_refreshed(self, area: dict, when: float | None = None) -> None:
    path = self.areas_dir / f"{area['id']}.json"
    with self._exclusive():
      if path.is_file():
        write_json(path, {**{k: v for k, v in area.items() if k != "id"}, "refreshed": _wall() if when is None else when})

  def settings(self) -> dict:
    value = read_json(self.root / "settings.json", 4096)
    save_driven = value.get("saveDriven") if isinstance(value, dict) else None
    return {"saveDriven": save_driven if type(save_driven) is bool else True}

  def set_settings(self, patch: Any) -> dict:
    if not isinstance(patch, dict) or not patch or set(patch) - {"saveDriven"} or type(patch.get("saveDriven")) is not bool:
      raise ValueError("Invalid offline map setting")
    value = {**self.settings(), **patch}
    write_json(self.root / "settings.json", value)
    return value

  def status(self) -> dict | None:
    value = read_json(self.root / "status.json", 1 << 18)
    return value if isinstance(value, dict) else None

  def write_status(self, value: dict) -> None:
    write_json(self.root / "status.json", value)


# ---------------------------------------------------------------- Mapbox usage

class Usage:
  """Tile requests made this calendar month, persisted so restarts don't reset the count."""

  def __init__(self, root: Path, clock=_wall):
    self.path = Path(root) / "usage.json"
    self.clock = clock
    value = read_json(self.path, 4096)
    self.month = value.get("month") if isinstance(value, dict) else None
    self.tiles = value.get("tiles", 0) if isinstance(value, dict) and type(value.get("tiles")) is int else 0
    self._dirty = 0

  def _current(self) -> str:
    return time.strftime("%Y-%m", time.gmtime(self.clock()))

  def add(self, count: int = 1) -> None:
    month = self._current()
    if month != self.month:
      self.month, self.tiles = month, 0
    self.tiles += count
    self._dirty += count
    if self._dirty >= 25:
      self.flush()

  def snapshot(self) -> dict:
    if self._current() != self.month:
      return {"month": self._current(), "tiles": 0, "freeTiles": FREE_TILES_PER_MONTH}
    return {"month": self.month, "tiles": self.tiles, "freeTiles": FREE_TILES_PER_MONTH}

  def flush(self) -> None:
    if self._dirty:
      try:
        write_json(self.path, {"month": self.month, "tiles": self.tiles})
        self._dirty = 0
      except OSError:
        pass
