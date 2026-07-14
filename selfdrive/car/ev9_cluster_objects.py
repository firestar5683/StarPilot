from dataclasses import dataclass
import math
from typing import Any


MIN_OBJECT_DISTANCE = 0.1


def default_enabled_param(params: Any, key: str) -> bool:
  """Read a rollout flag where an absent value means enabled."""
  raw = params.get(key)
  return raw is None or raw == b"1" or raw == "1"


def ev9_cluster_display_context_valid(radar_valid: bool, main_enabled: bool, drive_gear: bool,
                                      standstill: bool, v_ego: float) -> bool:
  """Gate display-only tracking to the moving Drive/Main context seen in stock routes."""
  return bool(radar_valid and main_enabled and drive_gear and not standstill and v_ego > 0.1)


@dataclass(frozen=True)
class ClusterObject:
  track_id: int
  distance: float
  lateral: float
  relative_speed: float
  selected: bool = False


@dataclass(frozen=True)
class ClusterObjectSlots:
  primary: ClusterObject | None = None
  alternate: ClusterObject | None = None
  left: ClusterObject | None = None
  right: ClusterObject | None = None


@dataclass
class _TrackedObject:
  track_id: int
  distance: float
  lateral: float
  relative_speed: float
  hits: int = 1
  misses: int = 0
  confirmed: bool = False


class Ev9ClusterObjectTracker:
  """Small display tracker; it does not participate in planning or control."""

  ACQUISITION_SAMPLES = 3
  # MRR35 is decoded at 20 Hz. Four missing frames suppress single-frame
  # flicker while guaranteeing removal on the fifth frame (250 ms).
  DROPOUT_HOLD_SAMPLES = 4
  EMA_ALPHA = 0.35
  CENTER_HALF_WIDTH = 1.8
  ADJACENT_OUTER_WIDTH = 5.5
  MAX_DISTANCE = 180.0

  def __init__(self) -> None:
    self.tracks: dict[int, _TrackedObject] = {}
    self.slot_track_ids: dict[str, int] = {"primary": -1, "alternate": -1, "left": -1, "right": -1}

  def clear(self) -> ClusterObjectSlots:
    """Hard-clear every pending and displayed object on a context transition."""
    self.tracks.clear()
    for slot in self.slot_track_ids:
      self.slot_track_ids[slot] = -1
    return ClusterObjectSlots()

  @staticmethod
  def _valid_point(point: Any) -> bool:
    values = (float(getattr(point, "dRel", 0.0)), float(getattr(point, "yRel", 0.0)),
              float(getattr(point, "vRel", 0.0)))
    return bool(getattr(point, "measured", False)) and int(getattr(point, "trackId", -1)) >= 0 and \
      MIN_OBJECT_DISTANCE < values[0] <= Ev9ClusterObjectTracker.MAX_DISTANCE and all(math.isfinite(v) for v in values)

  @staticmethod
  def _as_cluster_object(track: _TrackedObject, selected: bool = False) -> ClusterObject:
    return ClusterObject(track.track_id, track.distance, track.lateral, track.relative_speed, selected)

  def update(self, points: list[Any], preferred_primary_track_id: int = -1,
             alternate_enabled: bool = False,
             qualified_track_ids: set[int] | None = None,
             require_preferred_primary: bool = False,
             side_qualified_track_ids: set[int] | None = None,
             right_enabled: bool = True) -> ClusterObjectSlots:
    # A non-None set is an explicit display allow-list for points present in
    # this scan. Evict a present-but-disqualified track immediately, while a
    # genuinely missing point gets the bounded dropout hold below.
    if qualified_track_ids is not None:
      incoming_track_ids = {int(point.trackId) for point in points if self._valid_point(point)}
      for track_id in set(self.tracks) & (incoming_track_ids - qualified_track_ids):
        del self.tracks[track_id]
      for slot, track_id in self.slot_track_ids.items():
        if track_id in incoming_track_ids and track_id not in qualified_track_ids:
          self.slot_track_ids[slot] = -1

    seen: set[int] = set()
    for point in points:
      if not self._valid_point(point):
        continue

      track_id = int(point.trackId)
      if qualified_track_ids is not None and track_id not in qualified_track_ids:
        continue
      seen.add(track_id)
      distance = float(point.dRel)
      lateral = float(point.yRel)
      relative_speed = float(point.vRel)
      track = self.tracks.get(track_id)
      if track is None:
        self.tracks[track_id] = _TrackedObject(track_id, distance, lateral, relative_speed)
        continue

      alpha = self.EMA_ALPHA
      track.distance += alpha * (distance - track.distance)
      track.lateral += alpha * (lateral - track.lateral)
      track.relative_speed += alpha * (relative_speed - track.relative_speed)
      track.hits += 1
      track.misses = 0
      track.confirmed = track.confirmed or track.hits >= self.ACQUISITION_SAMPLES

    for track_id, track in list(self.tracks.items()):
      if track_id not in seen:
        track.hits = 0
        track.misses += 1
        if track.misses > self.DROPOUT_HOLD_SAMPLES:
          del self.tracks[track_id]

    confirmed = [track for track in self.tracks.values() if track.confirmed]
    center = sorted((track for track in confirmed if abs(track.lateral) <= self.CENTER_HALF_WIDTH),
                    key=lambda track: track.distance)
    def side_qualified(track: _TrackedObject) -> bool:
      return side_qualified_track_ids is None or track.track_id in side_qualified_track_ids

    # Stock-correlated side slots occupy the near adjacent lane and disappear
    # beyond 80 m. This is intentionally separate from the wider primary-lead
    # allow-list and does not claim to be a BSM target decision.
    left = sorted((track for track in confirmed if side_qualified(track) and
                   self.CENTER_HALF_WIDTH < track.lateral < 4.0 and track.distance < 80.0),
                  key=lambda track: track.distance)
    right = sorted((track for track in confirmed if right_enabled and side_qualified(track) and
                    -4.0 < track.lateral < -self.CENTER_HALF_WIDTH and track.distance < 80.0),
                   key=lambda track: track.distance)

    def choose(slot: str, candidates: list[_TrackedObject], preferred_track_id: int = -1) -> _TrackedObject | None:
      chosen = next((track for track in candidates if track.track_id == preferred_track_id), None)
      if chosen is None:
        chosen = next((track for track in candidates if track.track_id == self.slot_track_ids[slot]), None)
      if chosen is None and candidates:
        chosen = candidates[0]
      self.slot_track_ids[slot] = chosen.track_id if chosen is not None else -1
      return chosen

    if require_preferred_primary:
      primary = next((track for track in center if track.track_id == preferred_primary_track_id), None) \
        if preferred_primary_track_id >= 0 else None
      self.slot_track_ids["primary"] = primary.track_id if primary is not None else -1
    else:
      primary = choose("primary", center, preferred_primary_track_id)
    # Stock EV9 routes never used LEAD_ALT. radarState.leadTwo frequently
    # describes the same fused vehicle as leadOne, so this slot stays empty
    # even when the legacy rollout argument is enabled.
    alternate = None
    self.slot_track_ids["alternate"] = -1
    left_object = choose("left", left)
    right_object = choose("right", right)

    # Slots are derived together from the current lane classification, so a
    # track moving from an adjacent lane to center cannot exist in both slots.
    return ClusterObjectSlots(
      primary=self._as_cluster_object(primary, primary.track_id == preferred_primary_track_id) if primary is not None else None,
      alternate=self._as_cluster_object(alternate) if alternate is not None else None,
      left=self._as_cluster_object(left_object, left_object.track_id == preferred_primary_track_id) if left_object is not None else None,
      right=self._as_cluster_object(right_object, right_object.track_id == preferred_primary_track_id) if right_object is not None else None,
    )


def bsm_gated_side_slots(slots: ClusterObjectSlots, left_blindspot: bool, right_blindspot: bool,
                         gate_enabled: bool = True) -> ClusterObjectSlots:
  """Fail closed on EV9 adjacent-lane objects without a matching BSM decision."""
  if not gate_enabled:
    return slots
  return ClusterObjectSlots(slots.primary, slots.alternate,
                            slots.left if left_blindspot else None,
                            slots.right if right_blindspot else None)


def radar_backed_object(lead: Any, qualified_track_ids: set[int] | None = None) -> ClusterObject | None:
  """Return a cluster-safe object only when it came from a physical radar track."""
  if not bool(getattr(lead, "status", False)) or not bool(getattr(lead, "radar", False)):
    return None

  track_id = int(getattr(lead, "radarTrackId", -1))
  distance = float(getattr(lead, "dRel", 0.0))
  lateral = float(getattr(lead, "yRel", 0.0))
  relative_speed = float(getattr(lead, "vRel", 0.0))
  if track_id < 0 or (qualified_track_ids is not None and track_id not in qualified_track_ids) or \
     distance <= MIN_OBJECT_DISTANCE or not all(math.isfinite(v) for v in (distance, lateral, relative_speed)):
    return None

  return ClusterObject(track_id, distance, lateral, relative_speed)


def filtered_radar_slots(lead_one: Any, lead_two: Any, lead_left: Any, lead_right: Any,
                         alternate_enabled: bool,
                         qualified_track_ids: set[int] | None = None) -> ClusterObjectSlots:
  """Map fused leads without allowing vision-only or duplicate cluster ghosts."""
  primary = radar_backed_object(lead_one, qualified_track_ids)
  # LEAD_ALT is not a second selected lead on the EV9. Keep it empty rather
  # than duplicating the fused primary object.
  alternate = None
  left = radar_backed_object(lead_left, qualified_track_ids)
  right = radar_backed_object(lead_right, qualified_track_ids)

  used_track_ids: set[int] = set()
  results: list[ClusterObject | None] = []
  for obj in (primary, alternate, left, right):
    if obj is None or obj.track_id in used_track_ids:
      results.append(None)
      continue
    used_track_ids.add(obj.track_id)
    results.append(obj)

  return ClusterObjectSlots(*results)
