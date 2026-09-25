"""Galaxy's view of offline road maps: areas, save-as-you-drive, and navtilesd's progress.

Galaxy only writes area definitions and the setting; navtilesd does every
download, move and delete, so a slow request can never leave tiles half-written.
"""

from __future__ import annotations

import math
import time
from pathlib import Path

from openpilot.starpilot.navigation.offline_roads import (
  AREA_DEFAULT_RADIUS_KM, AREA_MAX_RADIUS_KM, AREA_MIN_RADIUS_KM, AVERAGE_DOWNLOAD_BYTES, AVERAGE_STORED_BYTES,
  FREE_TILES_PER_MONTH, MAX_AREAS, STATUS_STALE_SECONDS, OfflineState,
)

ACTIONS = {"addArea": {"area"}, "deleteArea": {"id"}, "settings": {"patch"}}


class OfflineMapsOwner:
  def __init__(self, root: Path | None = None, position=None, wall=time.time):  # noqa: TID251 - heartbeats are wall clock
    self.state = OfflineState(root)
    self.position = position          # callable returning {'latitude', 'longitude'} or None
    self.wall = wall

  def snapshot(self) -> dict:
    status = self.state.status() or {}
    heartbeat = status.get("heartbeat")
    running = (isinstance(heartbeat, (int, float)) and type(heartbeat) in (int, float) and math.isfinite(heartbeat)
               and 0 <= self.wall() - heartbeat < STATUS_STALE_SECONDS)
    progress = status.get("areas") if isinstance(status.get("areas"), dict) else {}
    areas = []
    for area in self.state.areas():
      row = progress.get(area["id"]) if running else None
      areas.append({**area, "progress": row if isinstance(row, dict) else None})
    position = None
    if self.position is not None:
      try:
        point = self.position()
        if point and all(math.isfinite(float(point[key])) for key in ("latitude", "longitude")):
          position = {"latitude": float(point["latitude"]), "longitude": float(point["longitude"])}
      except (TypeError, ValueError, KeyError, OSError):
        position = None
    usage = status.get("usage") if isinstance(status.get("usage"), dict) else None
    return {
      "areas": areas, "settings": self.state.settings(), "position": position,
      "service": {"running": running, "network": status.get("network") if running else None,
                  "failure": status.get("failure") if running else None, "noSpace": bool(status.get("noSpace")) and running,
                  "hasKey": status.get("hasKey") if running else None},
      "bytes": status.get("bytes") if isinstance(status.get("bytes"), dict) else None,
      "limits": status.get("limits") if isinstance(status.get("limits"), dict) else None,
      "usage": usage or {"tiles": 0, "freeTiles": FREE_TILES_PER_MONTH},
      "route": status.get("route") if running and isinstance(status.get("route"), dict) else None,
      "constants": {"minRadiusKm": AREA_MIN_RADIUS_KM, "maxRadiusKm": AREA_MAX_RADIUS_KM,
                    "defaultRadiusKm": AREA_DEFAULT_RADIUS_KM, "averageDownloadBytes": AVERAGE_DOWNLOAD_BYTES,
                    "averageStoredBytes": AVERAGE_STORED_BYTES, "maxAreas": MAX_AREAS},
    }

  def action(self, payload) -> dict:
    if type(payload) is not dict or payload.get("action") not in ACTIONS or set(payload) != {"action"} | ACTIONS[payload["action"]]:
      raise ValueError("Invalid offline map request")
    if payload["action"] == "addArea":
      self.state.add_area(payload["area"])
    elif payload["action"] == "deleteArea":
      self.state.delete_area(payload["id"])
    else:
      self.state.set_settings(payload["patch"])
    return self.snapshot()
