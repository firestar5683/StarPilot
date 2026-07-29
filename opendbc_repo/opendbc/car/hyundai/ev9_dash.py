from dataclasses import dataclass
import math
from typing import Any


MIN_OBJECT_DISTANCE = 0.1
MAX_TARGET_DISTANCE = 204.7
TARGET_LINE_OBJECT_CLEARANCE = 4.0
SIDE_MOVING_OBJECT_MIN_SPEED = 2.78
EV9_RAW_BLINDSPOT_BASE_MASK = 0x02
EV9_RAW_BLINDSPOT_RIGHT_MASK = 0x08
EV9_RAW_BLINDSPOT_LEFT_MASK = 0x10


def display_context_valid(radar_valid: bool, main_enabled: bool, drive_gear: bool) -> bool:
  """Keep the display-only tracker inside the stock Drive/Main envelope."""
  return bool(radar_valid and main_enabled and drive_gear)


def resolve_ev9_blindspot_state(native_left: bool, native_right: bool, native_fresh: bool,
                                 reconstructed_left: bool, reconstructed_right: bool,
                                 reconstruction_enabled: bool) -> tuple[bool, bool]:
  if native_fresh:
    return native_left, native_right
  if reconstruction_enabled:
    return reconstructed_left, reconstructed_right
  return False, False


def select_target_line_distance(display_active: bool, starpilot_plan_valid: bool, longitudinal_plan_valid: bool,
                                model_valid: bool, forcing_stop: bool, stop_sign_confirmed: bool,
                                red_light: bool, should_stop: bool, model_should_stop: bool,
                                experimental_mode: bool, has_lead: bool, tracking_lead: bool,
                                vehicle_stopped: bool,
                                lead_distance: float,
                                desired_follow_distance: float,
                                model_terminal_speed: float, model_distance: float) -> float | None:
  """Select the planner's stop point or ego target behind a tracked lead."""
  if not (display_active and starpilot_plan_valid and longitudinal_plan_valid):
    return None

  model_committed_stop = experimental_mode and model_valid and math.isfinite(model_terminal_speed) and \
    abs(float(model_terminal_speed)) <= 1.0 and (red_light or model_should_stop)
  untracked_stop_context = not has_lead or (vehicle_stopped and not tracking_lead)
  stop_scene = experimental_mode and (forcing_stop or stop_sign_confirmed or
    (untracked_stop_context and (should_stop or model_committed_stop)))
  candidates = []
  if stop_scene and math.isfinite(model_distance):
    candidates.append(float(model_distance))

  if has_lead and tracking_lead and math.isfinite(lead_distance) and \
     math.isfinite(desired_follow_distance) and desired_follow_distance > 0.0:
    candidates.append(float(lead_distance) - float(desired_follow_distance))
  return min(max(min(candidates), MIN_OBJECT_DISTANCE), MAX_TARGET_DISTANCE) if candidates else None


class Ev9TargetLineTracker:
  """Smooth source and planner transitions without moving through a lead icon."""

  EMA_ALPHA = 0.20
  MAX_STEP_METRES = 0.5

  def __init__(self) -> None:
    self.distance: float | None = None

  def clear(self) -> None:
    self.distance = None

  def update(self, display_active: bool, inputs_updated: bool,
             requested_distance: float | None, fallback_distance: float,
             maximum_distance: float | None = None) -> float | None:
    if not display_active:
      self.clear()
      return None
    if not inputs_updated:
      return self.distance

    candidate = requested_distance if requested_distance is not None else fallback_distance
    if not math.isfinite(candidate):
      self.clear()
      return None
    candidate = min(max(float(candidate), MIN_OBJECT_DISTANCE), MAX_TARGET_DISTANCE)
    if maximum_distance is not None and math.isfinite(maximum_distance):
      candidate = min(candidate, max(float(maximum_distance), MIN_OBJECT_DISTANCE))
    if self.distance is None:
      self.distance = candidate
      return self.distance

    delta = self.EMA_ALPHA * (candidate - self.distance)
    delta = min(max(delta, -self.MAX_STEP_METRES), self.MAX_STEP_METRES)
    self.distance = min(max(self.distance + delta, MIN_OBJECT_DISTANCE), MAX_TARGET_DISTANCE)
    if maximum_distance is not None and math.isfinite(maximum_distance):
      self.distance = min(self.distance, max(float(maximum_distance), MIN_OBJECT_DISTANCE))
    return self.distance


def select_lane_change_direction(lat_active: bool, model_valid: bool,
                                 lane_change_committed: bool, direction: str | None) -> str | None:
  """Expose only an active comma lane-change maneuver, never pre-lane-change intent."""
  return direction if lat_active and model_valid and lane_change_committed and direction in ("left", "right") else None


@dataclass(frozen=True)
class Ev9LaneOutline:
  left_visible: bool = False
  right_visible: bool = False
  desired_curvature: float = 0.0


@dataclass(frozen=True)
class Ev9LaneBoundary:
  confidence: float = 0.0
  curvature: float | None = None


def _ev9_boundary_curvature(boundary: Any) -> float | None:
  """Estimate one observed boundary's curvature from three fixed lookahead points."""
  xs = list(getattr(boundary, "x", ()))
  ys = list(getattr(boundary, "y", ()))
  points = [(float(x), float(y)) for x, y in zip(xs, ys, strict=False)
            if math.isfinite(float(x)) and math.isfinite(float(y))]
  if len(points) < 3:
    return None

  selected = [min(points, key=lambda point: abs(point[0] - target)) for target in (5.0, 20.0, 35.0)]
  (x0, y0), (x1, y1), (x2, y2) = selected
  if x1 - x0 < 1.0 or x2 - x1 < 1.0:
    return None

  first_heading = math.atan2(y1 - y0, x1 - x0)
  second_heading = math.atan2(y2 - y1, x2 - x1)
  heading_distance = 0.5 * (x2 - x0)
  # Keep observed boundaries in the model/action convention. The CCNC encoder
  # performs the single conversion to Hyundai's steering-angle sign.
  curvature = (second_heading - first_heading) / heading_distance
  return min(max(curvature, -Ev9LaneOutlineTracker.CURVATURE_LIMIT), Ev9LaneOutlineTracker.CURVATURE_LIMIT)


def select_ev9_lane_boundaries(lane_line_probabilities: list[float], lane_lines: list[Any],
                               road_edge_stds: list[float], road_edges: list[Any]) -> tuple[Ev9LaneBoundary, Ev9LaneBoundary]:
  """Prefer observed inner lane lines and fall back per side to a confident road edge."""
  boundaries = []
  for lane_index, edge_index in ((1, 0), (2, 1)):
    lane_probability = float(lane_line_probabilities[lane_index]) if lane_index < len(lane_line_probabilities) else 0.0
    edge_confidence = 1.0 - float(road_edge_stds[edge_index]) if edge_index < len(road_edge_stds) else 0.0
    lane_probability = min(max(lane_probability, 0.0), 1.0) if math.isfinite(lane_probability) else 0.0
    edge_confidence = min(max(edge_confidence, 0.0), 1.0) if math.isfinite(edge_confidence) else 0.0

    use_edge = lane_probability < Ev9LaneOutlineTracker.VISIBILITY_ACQUIRE_PROBABILITY and \
      edge_confidence > lane_probability
    source = road_edges[edge_index] if use_edge and edge_index < len(road_edges) else \
      lane_lines[lane_index] if lane_index < len(lane_lines) else None
    confidence = edge_confidence if use_edge else lane_probability
    boundaries.append(Ev9LaneBoundary(confidence, _ev9_boundary_curvature(source) if source is not None else None))
  return boundaries[0], boundaries[1]


class Ev9LaneOutlineTracker:
  """Stabilize model lane visibility and curvature for the display-only CCNC scene."""

  VISIBILITY_ACQUIRE_PROBABILITY = 0.55
  VISIBILITY_RELEASE_PROBABILITY = 0.45
  VISIBILITY_DROPOUT_SAMPLES = 10
  CURVATURE_LIMIT = 0.05
  CURVATURE_EMA_ALPHA = 0.35

  def __init__(self) -> None:
    self.outline = Ev9LaneOutline()
    self._curvature_initialized = False
    self._visibility_misses = [0, 0]

  def clear(self) -> Ev9LaneOutline:
    self.outline = Ev9LaneOutline()
    self._curvature_initialized = False
    self._visibility_misses = [0, 0]
    return self.outline

  def _visible(self, index: int, probability: float, previous: bool) -> bool:
    if not previous:
      self._visibility_misses[index] = 0
      return probability >= self.VISIBILITY_ACQUIRE_PROBABILITY
    if probability >= self.VISIBILITY_RELEASE_PROBABILITY:
      self._visibility_misses[index] = 0
      return True
    self._visibility_misses[index] += 1
    return self._visibility_misses[index] <= self.VISIBILITY_DROPOUT_SAMPLES

  def update(self, display_enabled: bool, model_valid: bool, model_updated: bool,
             left_boundary: Ev9LaneBoundary, right_boundary: Ev9LaneBoundary,
             desired_curvature: float) -> Ev9LaneOutline:
    if not display_enabled or not model_valid:
      return self.clear()
    if not model_updated:
      return self.outline
    if not math.isfinite(desired_curvature):
      return self.clear()

    left_probability = float(left_boundary.confidence)
    right_probability = float(right_boundary.confidence)
    if not math.isfinite(left_probability) or not math.isfinite(right_probability):
      return self.clear()

    left_visible = self._visible(0, left_probability, self.outline.left_visible)
    right_visible = self._visible(1, right_probability, self.outline.right_visible)
    observed_curvatures = [float(boundary.curvature) for boundary, visible in (
      (left_boundary, left_visible), (right_boundary, right_visible),
    ) if visible and boundary.confidence >= self.VISIBILITY_RELEASE_PROBABILITY and
      boundary.curvature is not None and math.isfinite(float(boundary.curvature))]
    curvature_sample = sum(observed_curvatures) / len(observed_curvatures) if observed_curvatures else None
    if curvature_sample is None and not self._curvature_initialized and (left_visible or right_visible):
      curvature_sample = min(max(float(desired_curvature), -self.CURVATURE_LIMIT), self.CURVATURE_LIMIT)

    curvature = self.outline.desired_curvature
    if curvature_sample is not None:
      curvature = min(max(float(curvature_sample), -self.CURVATURE_LIMIT), self.CURVATURE_LIMIT)
      if self._curvature_initialized:
        curvature = self.CURVATURE_EMA_ALPHA * curvature + \
                    (1.0 - self.CURVATURE_EMA_ALPHA) * self.outline.desired_curvature
      else:
        self._curvature_initialized = True

    self.outline = Ev9LaneOutline(
      left_visible=left_visible,
      right_visible=right_visible,
      desired_curvature=curvature,
    )
    return self.outline


@dataclass(frozen=True)
class ClusterObject:
  track_id: int
  distance: float
  lateral: float
  relative_speed: float
  motion_confirmed: bool = False
  raw_relative_speed: float | None = None


@dataclass(frozen=True)
class ClusterObjectSlots:
  primary: ClusterObject | None = None
  left: ClusterObject | None = None
  right: ClusterObject | None = None
  left_rear: ClusterObject | None = None
  right_rear: ClusterObject | None = None


@dataclass(frozen=True)
class Ev9DashTrackCandidates:
  display: frozenset[int] = frozenset()
  side: frozenset[int] = frozenset()
  side_retention: frozenset[int] = frozenset()


@dataclass
class Ev9RawBlindspotGateState:
  left_hits: int = 0
  right_hits: int = 0

  def clear(self) -> tuple[bool, bool]:
    self.left_hits = 0
    self.right_hits = 0
    return False, False


def update_ev9_raw_blindspot_gate(state: Ev9RawBlindspotGateState, raw_state: int, raw_fresh: bool,
                                  drive_gear: bool, points: list[Any], display_track_ids: set[int],
                                  side_track_ids: set[int], v_ego: float) -> tuple[bool, bool]:
  """Conservatively qualify retained 0x36A against adjacent-lane MRR35 tracks.

  Stock-route precision is asymmetric: left requires the strict side lifecycle,
  while right uses the broader display lifecycle and three consecutive scans.
  No dropout hold is applied because every tested hold increased false output.
  """
  if not raw_fresh or not drive_gear or not (int(raw_state) & EV9_RAW_BLINDSPOT_BASE_MASK):
    return state.clear()

  def qualified(point: Any, left: bool) -> bool:
    if not bool(getattr(point, "measured", False)):
      return False
    track_id = int(getattr(point, "trackId", -1))
    distance = float(getattr(point, "dRel", math.nan))
    lateral = float(getattr(point, "yRel", math.nan))
    relative_speed = float(getattr(point, "vRel", math.nan))
    if track_id < 0 or not all(math.isfinite(value) for value in (distance, lateral, relative_speed)) or \
       not MIN_OBJECT_DISTANCE < distance <= 60.0 or \
       abs(float(v_ego) + relative_speed) < SIDE_MOVING_OBJECT_MIN_SPEED:
      return False
    if left:
      return track_id in side_track_ids and 2.5 <= lateral <= 4.0
    return track_id in (display_track_ids | side_track_ids) and -4.5 <= lateral <= -2.5

  left_candidate = bool(int(raw_state) & EV9_RAW_BLINDSPOT_LEFT_MASK) and \
    any(qualified(point, True) for point in points)
  right_candidate = bool(int(raw_state) & EV9_RAW_BLINDSPOT_RIGHT_MASK) and \
    any(qualified(point, False) for point in points)
  state.left_hits = min(state.left_hits + 1, 1) if left_candidate else 0
  state.right_hits = min(state.right_hits + 1, 3) if right_candidate else 0
  return state.left_hits >= 1, state.right_hits >= 3


@dataclass(frozen=True)
class Ev9DashScene:
  objects: ClusterObjectSlots = ClusterObjectSlots()
  lane_outline: Ev9LaneOutline = Ev9LaneOutline()
  target_line_distance: float | None = None
  lane_change_direction: str | None = None
  speed_limit_raw: int = 0
  speed_limit_warning: bool = False
  objects_enabled: bool = True
  headway_enabled: bool = True
  side_objects_enabled: bool = True


def filter_side_objects(slots: ClusterObjectSlots, side_objects_enabled: bool) -> ClusterObjectSlots:
  """Apply the persistent side-object kill switch without changing primary output."""
  return slots if side_objects_enabled else ClusterObjectSlots(primary=slots.primary)


@dataclass
class _TrackedObject:
  track_id: int
  distance: float
  lateral: float
  relative_speed: float
  hits: int = 1
  misses: int = 0
  confirmed: bool = False
  raw_distance: float = 0.0
  raw_lateral: float = 0.0
  raw_relative_speed: float = 0.0
  right_entry_hits: int = 0
  side_motion_hits: int = 0
  side_motion_confirmed: bool = False
  side_qualified: bool = False
  side_retention_qualified: bool = False
  primary_confidence_hits: int = 0
  primary_confidence_misses: int = 0
  primary_confident: bool = False


class Ev9DashObjectTracker:
  """Route-qualified display tracker that never participates in planning or control."""

  # MRR35 publishes at 20 Hz. Three samples prevent one-frame acquisitions,
  # while a four-sample dropout hold removes brief radar channel churn.
  ACQUISITION_SAMPLES = 3
  DROPOUT_HOLD_SAMPLES = 4
  EMA_ALPHA = 0.35
  PRIMARY_ENTRY_HALF_WIDTH = 2.5
  PRIMARY_RETENTION_HALF_WIDTH = 2.5
  # The held-out route's multi-second false display leads had materially lower
  # fused model confidence. Apply this only to the display path; radarState and
  # planning remain untouched. Distant leads use the stricter route-backed bar.
  PRIMARY_MODEL_PROB_NEAR = 0.75
  PRIMARY_MODEL_PROB_FAR = 0.90
  PRIMARY_MODEL_PROB_FAR_DISTANCE = 100.0
  SIDE_INNER_WIDTH = 1.8
  SIDE_RETENTION_INNER_WIDTH = 0.25
  MAX_DISTANCE = 180.0

  def __init__(self) -> None:
    self.tracks: dict[int, _TrackedObject] = {}
    self.slot_track_ids: dict[str, int] = {
      "primary": -1,
      "left": -1,
      "right": -1,
    }

  def clear(self) -> ClusterObjectSlots:
    self.tracks.clear()
    for slot in self.slot_track_ids:
      self.slot_track_ids[slot] = -1
    return ClusterObjectSlots()

  @staticmethod
  def _valid_point(point: Any) -> bool:
    values = (float(getattr(point, "dRel", 0.0)), float(getattr(point, "yRel", 0.0)),
              float(getattr(point, "vRel", 0.0)))
    return bool(getattr(point, "measured", False)) and int(getattr(point, "trackId", -1)) >= 0 and \
      MIN_OBJECT_DISTANCE < values[0] <= Ev9DashObjectTracker.MAX_DISTANCE and all(math.isfinite(v) for v in values)

  @staticmethod
  def _as_cluster_object(track: _TrackedObject) -> ClusterObject:
    return ClusterObject(track.track_id, track.distance, track.lateral, track.relative_speed,
                         track.side_motion_confirmed, track.raw_relative_speed)

  @staticmethod
  def _side_motion_valid(track: _TrackedObject, v_ego: float, standstill: bool) -> bool:
    # A stationary wall has vRel ~= -vEgo. At a stop, retain only a target
    # whose motion was previously established or which is moving now.
    if standstill or abs(float(v_ego)) <= 0.1:
      return track.side_motion_confirmed or abs(track.raw_relative_speed) >= SIDE_MOVING_OBJECT_MIN_SPEED
    return abs(float(v_ego) + track.raw_relative_speed) >= SIDE_MOVING_OBJECT_MIN_SPEED

  @classmethod
  def _primary_confidence_sample(cls, distance: float, model_prob: float) -> bool:
    threshold = cls.PRIMARY_MODEL_PROB_FAR \
      if distance > cls.PRIMARY_MODEL_PROB_FAR_DISTANCE else cls.PRIMARY_MODEL_PROB_NEAR
    return math.isfinite(model_prob) and model_prob >= threshold

  def update(self, points: list[Any], preferred_primary_track_id: int,
             preferred_primary_model_prob: float,
             qualified_track_ids: set[int], side_qualified_track_ids: set[int],
             side_retention_track_ids: set[int], v_ego: float, standstill: bool) -> ClusterObjectSlots:
    # A present track that no longer passes the route-derived display discriminator is
    # removed immediately. A genuinely absent track receives the short hold.
    incoming_track_ids = {int(point.trackId) for point in points if self._valid_point(point)}
    # The raw display discriminator is strong on the preserved d4-d6
    # firmware, but a held-out stock route uses a different score range. The
    # fused radar-backed lead is already the strongest available primary proof,
    # so never make that route-variant score a mandatory primary gate.
    allowed_track_ids = set(qualified_track_ids) | set(side_qualified_track_ids) | set(side_retention_track_ids)
    if preferred_primary_track_id in incoming_track_ids:
      allowed_track_ids.add(preferred_primary_track_id)
    for track_id in set(self.tracks) & (incoming_track_ids - allowed_track_ids):
      del self.tracks[track_id]
    for slot, track_id in self.slot_track_ids.items():
      if track_id in incoming_track_ids and track_id not in allowed_track_ids:
        self.slot_track_ids[slot] = -1

    seen: set[int] = set()
    for point in points:
      if not self._valid_point(point):
        continue

      track_id = int(point.trackId)
      if track_id not in allowed_track_ids:
        continue
      seen.add(track_id)
      distance = float(point.dRel)
      lateral = float(point.yRel)
      relative_speed = float(point.vRel)
      track = self.tracks.get(track_id)
      if track is None:
        side_motion = abs(relative_speed) >= SIDE_MOVING_OBJECT_MIN_SPEED if standstill or abs(float(v_ego)) <= 0.1 else \
          abs(float(v_ego) + relative_speed) >= SIDE_MOVING_OBJECT_MIN_SPEED
        primary_confidence = track_id == preferred_primary_track_id and \
          self._primary_confidence_sample(distance, preferred_primary_model_prob)
        self.tracks[track_id] = _TrackedObject(
          track_id, distance, lateral, relative_speed,
          raw_distance=distance, raw_lateral=lateral, raw_relative_speed=relative_speed,
          side_motion_hits=int(side_motion),
          side_qualified=track_id in side_qualified_track_ids,
          side_retention_qualified=track_id in side_retention_track_ids,
          primary_confidence_hits=int(primary_confidence),
        )
        continue

      track.raw_distance = distance
      track.raw_lateral = lateral
      track.raw_relative_speed = relative_speed
      track.side_qualified = track_id in side_qualified_track_ids
      track.side_retention_qualified = track_id in side_retention_track_ids
      track.distance += self.EMA_ALPHA * (distance - track.distance)
      track.lateral += self.EMA_ALPHA * (lateral - track.lateral)
      track.relative_speed += self.EMA_ALPHA * (relative_speed - track.relative_speed)
      track.hits += 1
      track.misses = 0
      track.confirmed = track.confirmed or track.hits >= self.ACQUISITION_SAMPLES

      side_motion = abs(track.raw_relative_speed) >= SIDE_MOVING_OBJECT_MIN_SPEED \
        if standstill or abs(float(v_ego)) <= 0.1 else \
        abs(float(v_ego) + track.raw_relative_speed) >= SIDE_MOVING_OBJECT_MIN_SPEED
      track.side_motion_hits = track.side_motion_hits + 1 if side_motion else 0
      track.side_motion_confirmed = track.side_motion_confirmed or \
        track.side_motion_hits >= self.ACQUISITION_SAMPLES

      if track_id == preferred_primary_track_id:
        primary_confidence = self._primary_confidence_sample(distance, preferred_primary_model_prob)
        if primary_confidence:
          track.primary_confidence_hits += 1
          track.primary_confidence_misses = 0
          track.primary_confident = track.primary_confident or \
            track.primary_confidence_hits >= self.ACQUISITION_SAMPLES
        else:
          track.primary_confidence_hits = 0
          track.primary_confidence_misses += 1
          if track.primary_confidence_misses > self.DROPOUT_HOLD_SAMPLES:
            track.primary_confident = False
      else:
        track.primary_confidence_hits = 0
        track.primary_confidence_misses = 0
        track.primary_confident = False

    for track_id, track in list(self.tracks.items()):
      if track_id not in seen:
        track.hits = 0
        track.misses += 1
        if track.misses > self.DROPOUT_HOLD_SAMPLES:
          del self.tracks[track_id]

    # The stock right slot has an asymmetric entry/retention envelope. This
    # rejects long-lived d6 roadside ghosts without keying on radar addresses.
    for track in self.tracks.values():
      right_entry = track.track_id in seen and track.side_qualified and \
        -4.3 < track.raw_lateral < -2.2 and track.raw_distance < 60.0 and \
        self._side_motion_valid(track, v_ego, standstill)
      track.right_entry_hits = track.right_entry_hits + 1 if right_entry else 0

    confirmed = [track for track in self.tracks.values() if track.confirmed]
    previous_primary_track_id = self.slot_track_ids["primary"]
    current_left_track_id = self.slot_track_ids["left"]
    current_right_track_id = self.slot_track_ids["right"]

    def left_candidate(track: _TrackedObject) -> bool:
      entered = track.side_qualified and self.SIDE_INNER_WIDTH < track.lateral < 4.0 and \
        track.distance < 80.0 and self._side_motion_valid(track, v_ego, standstill)
      promoting = track.track_id == current_left_track_id == preferred_primary_track_id and \
        track.side_retention_qualified and \
        self.SIDE_RETENTION_INNER_WIDTH < track.raw_lateral < 4.5 and track.raw_distance < 82.0 and \
        self._side_motion_valid(track, v_ego, standstill)
      handoff = track.track_id == previous_primary_track_id and track.side_retention_qualified and \
        self.SIDE_INNER_WIDTH < track.raw_lateral < 4.5 and track.raw_distance < 82.0 and \
        self._side_motion_valid(track, v_ego, standstill)
      return entered or promoting or handoff

    left = sorted((track for track in confirmed if left_candidate(track)), key=lambda track: track.distance)

    def right_candidate(track: _TrackedObject) -> bool:
      retained = track.track_id == current_right_track_id and track.side_retention_qualified and \
        -4.5 < track.raw_lateral < -1.5 and track.raw_distance < 62.0 and \
        self._side_motion_valid(track, v_ego, standstill)
      promoting = track.track_id == current_right_track_id == preferred_primary_track_id and \
        track.side_retention_qualified and \
        -4.5 < track.raw_lateral < -self.SIDE_RETENTION_INNER_WIDTH and track.raw_distance < 62.0 and \
        self._side_motion_valid(track, v_ego, standstill)
      handoff = track.track_id == previous_primary_track_id and track.side_retention_qualified and \
        -4.5 < track.raw_lateral < -2.2 and track.raw_distance < 62.0 and \
        self._side_motion_valid(track, v_ego, standstill)
      entered = track.right_entry_hits >= self.ACQUISITION_SAMPLES and \
        self._side_motion_valid(track, v_ego, standstill)
      return retained or promoting or handoff or entered

    right = sorted((track for track in confirmed if right_candidate(track)), key=lambda track: track.distance)

    # The primary white box must remain the radar-backed fused lead. Raw
    # nearest-track selection created convincing but false center objects.
    current_primary_track_id = previous_primary_track_id
    primary = next((track for track in confirmed if track.track_id == preferred_primary_track_id and
                    track.primary_confident), None) \
      if preferred_primary_track_id >= 0 else None
    if primary is not None:
      primary_half_width = self.PRIMARY_RETENTION_HALF_WIDTH \
        if primary.track_id == current_primary_track_id else self.PRIMARY_ENTRY_HALF_WIDTH
      if abs(primary.raw_lateral) > primary_half_width:
        primary = None
    self.slot_track_ids["primary"] = primary.track_id if primary is not None else -1
    if primary is not None:
      left = [track for track in left if track.track_id != primary.track_id]
      right = [track for track in right if track.track_id != primary.track_id]

    def choose_side(slot: str, candidates: list[_TrackedObject]) -> _TrackedObject | None:
      chosen = next((track for track in candidates if track.track_id == self.slot_track_ids[slot]), None)
      # Stock moves one physical identity atomically between the center and
      # adjacent slot. Prioritize that handoff even when another side target is
      # present, otherwise a lane-crossing car can disappear for one scan.
      handoff = next((track for track in candidates if track.track_id == previous_primary_track_id), None)
      if primary is None and handoff is not None:
        chosen = handoff
      # Outside a known center-to-side handoff, acquire only an unambiguous
      # scene. The preserved routes do not expose a trustworthy retained source
      # for the separate fixed rear marker.
      if chosen is None and len(candidates) == 1:
        chosen = candidates[0]
      self.slot_track_ids[slot] = chosen.track_id if chosen is not None else -1
      return chosen

    left_object = choose_side("left", left)
    right_object = choose_side("right", right)
    return ClusterObjectSlots(
      primary=self._as_cluster_object(primary) if primary is not None else None,
      left=self._as_cluster_object(left_object) if left_object is not None else None,
      right=self._as_cluster_object(right_object) if right_object is not None else None,
    )


def radar_backed_object(lead: Any) -> ClusterObject | None:
  if not bool(getattr(lead, "status", False)) or not bool(getattr(lead, "radar", False)):
    return None

  track_id = int(getattr(lead, "radarTrackId", -1))
  distance = float(getattr(lead, "dRel", 0.0))
  lateral = float(getattr(lead, "yRel", 0.0))
  relative_speed = float(getattr(lead, "vRel", 0.0))
  if track_id < 0 or distance <= MIN_OBJECT_DISTANCE or \
     not all(math.isfinite(v) for v in (distance, lateral, relative_speed)):
    return None
  return ClusterObject(track_id, distance, lateral, relative_speed)


def validate_slots_for_output(slots: ClusterObjectSlots, lead_one: Any, v_ego: float,
                              standstill: bool) -> ClusterObjectSlots:
  """Fail closed when held display state outlives current fusion or motion."""
  fused_primary = radar_backed_object(lead_one)
  primary = slots.primary
  if fused_primary is None or primary is None or primary.track_id != fused_primary.track_id:
    primary = None

  def valid_side(obj: ClusterObject | None) -> ClusterObject | None:
    if obj is None:
      return None
    if standstill or abs(float(v_ego)) <= 0.1:
      return obj if obj.motion_confirmed else None
    relative_speed = obj.raw_relative_speed if obj.raw_relative_speed is not None else obj.relative_speed
    return obj if abs(float(v_ego) + relative_speed) >= SIDE_MOVING_OBJECT_MIN_SPEED else None

  return ClusterObjectSlots(
    primary,
    valid_side(slots.left),
    valid_side(slots.right),
    valid_side(slots.left_rear),
    valid_side(slots.right_rear),
  )
