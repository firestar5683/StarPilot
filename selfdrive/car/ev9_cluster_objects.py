from dataclasses import dataclass
import math
from typing import Any


MIN_OBJECT_DISTANCE = 0.1


@dataclass(frozen=True)
class ClusterObject:
  track_id: int
  distance: float
  lateral: float
  relative_speed: float


@dataclass(frozen=True)
class ClusterObjectSlots:
  primary: ClusterObject | None = None
  alternate: ClusterObject | None = None
  left: ClusterObject | None = None
  right: ClusterObject | None = None


def radar_backed_object(lead: Any) -> ClusterObject | None:
  """Return a cluster-safe object only when it came from a physical radar track."""
  if not bool(getattr(lead, "status", False)) or not bool(getattr(lead, "radar", False)):
    return None

  track_id = int(getattr(lead, "radarTrackId", -1))
  distance = float(getattr(lead, "dRel", 0.0))
  lateral = float(getattr(lead, "yRel", 0.0))
  relative_speed = float(getattr(lead, "vRel", 0.0))
  if track_id < 0 or distance <= MIN_OBJECT_DISTANCE or not all(math.isfinite(v) for v in (distance, lateral, relative_speed)):
    return None

  return ClusterObject(track_id, distance, lateral, relative_speed)


def filtered_radar_slots(lead_one: Any, lead_two: Any, lead_left: Any, lead_right: Any,
                         alternate_enabled: bool) -> ClusterObjectSlots:
  """Map fused leads without allowing vision-only or duplicate cluster ghosts."""
  primary = radar_backed_object(lead_one)
  alternate = radar_backed_object(lead_two) if alternate_enabled else None
  left = radar_backed_object(lead_left)
  right = radar_backed_object(lead_right)

  used_track_ids: set[int] = set()
  results: list[ClusterObject | None] = []
  for obj in (primary, alternate, left, right):
    if obj is None or obj.track_id in used_track_ids:
      results.append(None)
      continue
    used_track_ids.add(obj.track_id)
    results.append(obj)

  return ClusterObjectSlots(*results)
