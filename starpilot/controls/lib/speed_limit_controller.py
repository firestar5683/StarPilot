#!/usr/bin/env python3
# PFEIFER - SLC - Modified by FrogAi
from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.car.cruise import V_CRUISE_UNSET

from cereal import custom
from openpilot.starpilot.controls.lib.mapbox_speed_limit import MapboxSpeedLimit


SOURCE_NONE = "None"
SOURCE_DASHBOARD = "Dashboard"
SOURCE_MAP = "Map Data"
SOURCE_VISION = "Vision"
SOURCE_MAPBOX = "Mapbox"
SOURCE_PREVIOUS_LIMIT = "Previous Limit"
REAL_SOURCES = (SOURCE_DASHBOARD, SOURCE_MAP, SOURCE_VISION, SOURCE_MAPBOX)

OFFSET_MAP_IMPERIAL = [
  (0, 11.2, "speed_limit_offset1"),     # 0–24 mph
  (11.2, 15.2, "speed_limit_offset2"),  # 25–34
  (15.2, 19.6, "speed_limit_offset3"),  # 35–44
  (19.6, 24.1, "speed_limit_offset4"),  # 45–54
  (24.1, 28.6, "speed_limit_offset5"),  # 55–64
  (28.6, 33.1, "speed_limit_offset6"),  # 65–74
  (33.1, 44.2, "speed_limit_offset7"),  # 75–99
]

OFFSET_MAP_METRIC = [
  (0, 8.1, "speed_limit_offset1"),      # 0–29 km/h
  (8.1, 13.6, "speed_limit_offset2"),   # 30–49
  (13.6, 16.4, "speed_limit_offset3"),  # 50–59
  (16.4, 21.9, "speed_limit_offset4"),  # 60–79
  (21.9, 27.5, "speed_limit_offset5"),  # 80–99
  (27.5, 33.1, "speed_limit_offset6"),  # 100–119
  (33.1, 38.9, "speed_limit_offset7"),  # 120–140
]

SLC_OVERRIDE_DISABLE_CLEAR_TIME = 0.75
SET_SPEED_CHANGE_TOLERANCE_METERS_PER_SECOND = 0.1
SAME_LIMIT_TOLERANCE = 1.0
VISION_LARGE_REFERENCE_SPEED_DELTA = 30 * CV.MPH_TO_MS
VISION_LARGE_SET_SPEED_MIN_SUPPORT = 3
VISION_SUPPORT_SPEED_TOLERANCE = 0.5 * CV.MPH_TO_MS


class SpeedLimitController:
  def __init__(self, StarPilotVCruise):
    self.starpilot_planner = StarPilotVCruise.starpilot_planner
    self.starpilot_toggles = None
    self.mapbox = MapboxSpeedLimit(self.starpilot_planner.params)

    self.source = SOURCE_NONE
    self.target = 0.0
    self.map_speed_limit = 0.0
    self.next_speed_limit = 0.0
    self.vision_limit = 0.0
    self.overridden_speed = 0.0

    self.last_valid_limit = max(self.starpilot_planner.params.get_float("PreviousSpeedLimit"), 0.0)
    self.last_valid_source = SOURCE_NONE  # The persisted number has no known live source.
    self.pending_limit = 0.0
    self.pending_source = SOURCE_NONE
    self.confirmation_time = 0.0
    self.denied_limit = 0.0
    self.previous_road_name = ""

    self.set_speed_override = 0.0
    self.pedal_override = 0.0
    self.previous_set_speed = None
    self.consume_set_speed_change = False
    self.override_disable_time = 0.0
    self.limit_change_started = False
    self.confirmation_button_consumed = False
    self._active_control = False
    self._using_experimental_fallback = False
    self._using_previous_limit_fallback = False
    self._mode = "off"

  def shutdown(self):
    self.mapbox.shutdown()

  @property
  def mapbox_limit(self):
    return self.mapbox.limit

  @property
  def confirmation_pending(self):
    return self.pending_limit >= 1

  @property
  def unconfirmed_speed_limit(self):
    return self.pending_limit

  @property
  def presented_source(self):
    if self.confirmation_pending:
      return self.pending_source
    if self.source in REAL_SOURCES:
      return self.source
    if self._using_previous_limit_fallback and self.target >= 1:
      return self.last_valid_source if self.last_valid_source in REAL_SOURCES else SOURCE_PREVIOUS_LIMIT
    if (self.denied_limit > 0 and self.last_valid_limit > 0 and self.target >= 1 and
        abs(self.target - self.last_valid_limit) < SAME_LIMIT_TOLERANCE):
      return self.last_valid_source if self.last_valid_source in REAL_SOURCES else SOURCE_PREVIOUS_LIMIT
    return SOURCE_NONE

  @property
  def experimental_mode(self):
    return self._active_control and self._using_experimental_fallback

  @property
  def target_to_use(self):
    # Keep Set Speed fallback from arming an override against a higher fake limit.
    if self.source == SOURCE_NONE and self.target > 0 and self.last_valid_limit > 0:
      return min(self.target, self.last_valid_limit)
    return self.target

  def get_offset(self, limit):
    if self.starpilot_toggles is None:
      return 0.0
    offset_map = OFFSET_MAP_METRIC if self.starpilot_toggles.is_metric else OFFSET_MAP_IMPERIAL
    return next((getattr(self.starpilot_toggles, name) for low, high, name in offset_map if low <= limit < high), 0.0)

  @property
  def offset(self):
    return self.get_offset(self.target)

  def low_vision_limit_filtered(self, limit):
    return (
      getattr(self.starpilot_toggles, "vision_speed_limit_low_limit_filter", False) and
      0 < limit <= max(getattr(self.starpilot_toggles, "vision_speed_limit_low_limit_threshold", 0), 0)
    )

  def reset_control_state(self):
    self._clear_pending()
    self.clear_override()
    self.previous_set_speed = None
    self.consume_set_speed_change = False
    self.override_disable_time = 0.0
    self.limit_change_started = False
    self.confirmation_button_consumed = False
    self._active_control = False
    self._using_experimental_fallback = False
    self.starpilot_planner.params_memory.remove("SpeedLimitAccepted")
    self.starpilot_planner.params_memory.remove("SLCAdoptSpeedLimit")

  def _get_vision_limit(self, v_ego, sm, display_only):
    enabled = getattr(self.starpilot_toggles, "vision_speed_limit_detection", False)
    self.vision_limit = self.starpilot_planner.params_memory.get_float("VisionSpeedLimit") if enabled else 0.0
    limit = self.vision_limit
    if not display_only and self.low_vision_limit_filtered(limit):
      return 0.0

    raw_set_speed_kph = float(sm["carState"].vCruise)
    selected_speed = raw_set_speed_kph * CV.KPH_TO_MS if 0 < raw_set_speed_kph < V_CRUISE_UNSET else 0.0
    reference_speed = selected_speed if selected_speed > 0 else max(float(v_ego), 0.0)
    if (limit > 0 and reference_speed > 0 and not sm["carState"].standstill and
        abs(limit - reference_speed) >= VISION_LARGE_REFERENCE_SPEED_DELTA):
      memory = self.starpilot_planner.params_memory
      count = memory.get_int("VisionSpeedLimitSupportCount")
      support_speed = memory.get_float("VisionSpeedLimitSupportSpeed")
      if count < VISION_LARGE_SET_SPEED_MIN_SUPPORT or abs(support_speed - limit) > VISION_SUPPORT_SPEED_TOLERANCE:
        return 0.0
    return limit

  def _update_map_speed_limit(self, v_ego, sm):
    map_data = sm["mapdOut"]
    way_sel = map_data.waySelectionType
    if way_sel in (custom.WaySelectionType.current, custom.WaySelectionType.extended):
      self.map_speed_limit = map_data.speedLimit
      self.next_speed_limit = map_data.nextSpeedLimit
    elif way_sel in (custom.WaySelectionType.predicted, custom.WaySelectionType.possible):
      speed = map_data.speedLimit
      if speed > 0 and (self.map_speed_limit == 0 or speed < self.map_speed_limit):
        self.map_speed_limit = speed
      self.next_speed_limit = 0.0
    else:
      # Explicit selection failure means the old current limit is no longer live.
      self.map_speed_limit = 0.0
      self.next_speed_limit = 0.0

    if self.next_speed_limit > 0:
      if self.map_speed_limit < self.next_speed_limit:
        lookahead = self.starpilot_toggles.map_speed_lookahead_higher * v_ego
      elif self.map_speed_limit > self.next_speed_limit:
        lookahead = self.starpilot_toggles.map_speed_lookahead_lower * v_ego
      else:
        lookahead = 0.0
      if map_data.nextSpeedLimitDistance < lookahead:
        self.map_speed_limit = self.next_speed_limit

  def _select_limit(self, dashboard, map_limit, vision_limit):
    priorities = (self.starpilot_toggles.speed_limit_priority1, self.starpilot_toggles.speed_limit_priority2)
    limits = {SOURCE_DASHBOARD: dashboard, SOURCE_MAP: map_limit}
    if SOURCE_VISION in priorities:
      limits[SOURCE_VISION] = vision_limit
    valid = {source: limit for source, limit in limits.items() if limit >= 1}
    if not valid:
      return SOURCE_NONE, 0.0
    if self.starpilot_toggles.speed_limit_priority_highest:
      source = max(valid, key=valid.get)
    elif self.starpilot_toggles.speed_limit_priority_lowest:
      source = min(valid, key=valid.get)
    else:
      source = next((name for name in priorities if name in valid), SOURCE_NONE)
    return source, valid.get(source, 0.0)

  def _apply_mapbox_filler(self, source, limit, now, time_validated, v_ego, sm):
    if source != SOURCE_NONE or not self.starpilot_toggles.slc_mapbox_filler:
      self.mapbox.reset()
      return source, limit
    self.mapbox.update(
      now, time_validated, v_ego, self.starpilot_planner.gps_valid, self.starpilot_planner.gps_position,
      sm["carState"].steeringAngleDeg, sm["liveParameters"].angleOffsetDeg,
    )
    if self.mapbox.limit >= 1:
      return SOURCE_MAPBOX, self.mapbox.limit
    return source, limit

  def _apply_fallback(self, v_cruise, enabled):
    self._using_experimental_fallback = False
    self._using_previous_limit_fallback = False
    previous_vision_filtered = self.last_valid_source == SOURCE_VISION and self.low_vision_limit_filtered(self.last_valid_limit)
    if self.starpilot_toggles.slc_fallback_previous_speed_limit and self.last_valid_limit > 0 and not previous_vision_filtered:
      self.source = self.last_valid_source
      self.target = self.last_valid_limit
      self._using_previous_limit_fallback = True
    elif enabled and self.starpilot_toggles.slc_fallback_set_speed:
      self.source = SOURCE_NONE
      self.target = v_cruise
    else:
      self.source = SOURCE_NONE
      self.target = 0.0
      self._using_experimental_fallback = bool(self.starpilot_toggles.slc_fallback_experimental_mode)

  def _confirmation_required(self, limit):
    current = self.last_valid_limit
    return ((limit < current and self.starpilot_toggles.speed_limit_confirmation_lower) or
            (limit > current and self.starpilot_toggles.speed_limit_confirmation_higher))

  def _clear_pending(self):
    self.pending_limit = 0.0
    self.pending_source = SOURCE_NONE
    self.confirmation_time = 0.0

  def _reconcile_set_speed_override(self, old_limit, new_limit):
    if self.set_speed_override <= 0 or old_limit <= 0 or new_limit <= 0 or abs(new_limit - old_limit) < 0.1:
      return
    if (new_limit < old_limit or
        self.set_speed_override <= new_limit + self.get_offset(new_limit) + SET_SPEED_CHANGE_TOLERANCE_METERS_PER_SECOND):
      self.set_speed_override = 0.0
      self.overridden_speed = self.pedal_override

  def _accept_limit(self, source, limit, *, persist=True):
    assert source in REAL_SOURCES and limit >= 1
    old_limit = self.last_valid_limit
    self._reconcile_set_speed_override(old_limit, limit)
    self.source = source
    self.target = limit
    self.last_valid_limit = limit
    self.last_valid_source = source
    self.denied_limit = 0.0
    self._clear_pending()
    if persist and abs(limit - old_limit) >= 0.1:
      self.starpilot_planner.params.put_nonblocking("PreviousSpeedLimit", float(limit))

  def _reject_limit(self, limit):
    self.denied_limit = limit
    self.source = SOURCE_NONE
    self._clear_pending()
    self.starpilot_planner.params_memory.remove("SpeedLimitAccepted")

  def _update_limit(self, source, limit, sm):
    road_name = sm["mapdOut"].roadName if source == SOURCE_MAP else ""
    if road_name and road_name != self.previous_road_name:
      self.denied_limit = 0.0
      self.previous_road_name = road_name

    if source == SOURCE_NONE:
      self._clear_pending()
      self.starpilot_planner.params_memory.remove("SpeedLimitAccepted")
      return

    current = self.last_valid_limit
    if current > 0 and abs(limit - current) < SAME_LIMIT_TOLERANCE:
      self._accept_limit(source, limit, persist=False)
      self.starpilot_planner.params_memory.remove("SpeedLimitAccepted")
      return

    confirmation_required = self._confirmation_required(limit)
    if self.denied_limit > 0 and abs(limit - self.denied_limit) < SAME_LIMIT_TOLERANCE:
      if confirmation_required:
        self._clear_pending()
        self.starpilot_planner.params_memory.remove("SpeedLimitAccepted")
        self.source = SOURCE_NONE
        return
      # Turning confirmation off applies the already-announced candidate.
      self._accept_limit(source, limit)
      self.starpilot_planner.params_memory.remove("SpeedLimitAccepted")
      return
    self.denied_limit = 0.0

    if self.pending_limit == 0 or abs(limit - self.pending_limit) >= SAME_LIMIT_TOLERANCE:
      self.pending_limit = limit
      self.pending_source = source
      self.confirmation_time = 0.0
      self.limit_change_started = True
      new_pending = True
    else:
      self.pending_source = source
      new_pending = False

    if not confirmation_required:
      self._accept_limit(source, limit)
      self.starpilot_planner.params_memory.remove("SpeedLimitAccepted")
      return

    self.source = SOURCE_NONE
    self.confirmation_time += DT_MDL
    long_active = sm["carControl"].longActive
    accel_accept = bool(sm["starpilotCarState"].accelPressed and long_active)
    if new_pending and accel_accept:
      # This press cannot confirm a candidate that was replaced on this frame.
      self.confirmation_button_consumed = True
      self.consume_set_speed_change = True
    memory = self.starpilot_planner.params_memory
    ui_accept = memory.get_bool("SpeedLimitAccepted")
    if ui_accept:
      memory.remove("SpeedLimitAccepted")

    fully_disengaged = not long_active and not sm["selfdriveState"].enabled
    if ((accel_accept or ui_accept) and not new_pending) or fully_disengaged:
      pending_limit, pending_source = self.pending_limit, self.pending_source
      higher = pending_limit > current
      self._accept_limit(pending_source, pending_limit)
      if accel_accept:
        self.consume_set_speed_change = True
        self.confirmation_button_consumed = True
      set_speed_kph = float(sm["carState"].vCruise)
      target_with_offset = self.target + self.offset
      if (higher and long_active and 0 < set_speed_kph < V_CRUISE_UNSET and
          set_speed_kph * CV.KPH_TO_MS < target_with_offset):
        memory.put_float("SLCForceCruiseSpeed", target_with_offset)
    elif sm["starpilotCarState"].decelPressed or (self.confirmation_time >= 30 and long_active):
      self._reject_limit(self.pending_limit)

  def _process_adopt_request(self, source, limit):
    memory = self.starpilot_planner.params_memory
    if not memory.get_bool("SLCAdoptSpeedLimit"):
      return
    memory.remove("SLCAdoptSpeedLimit")
    if source not in REAL_SOURCES or limit < 1:
      return
    self.clear_override()
    self.consume_set_speed_change = True
    self._accept_limit(source, limit)
    memory.put_float("SLCForceCruiseSpeed", self.target + self.offset)

  def clear_override(self):
    self.set_speed_override = 0.0
    self.pedal_override = 0.0
    self.overridden_speed = 0.0

  def _update_override(self, v_cruise, v_cruise_diff, v_ego, v_ego_diff, sm):
    previous = self.previous_set_speed
    self.previous_set_speed = v_cruise
    changed = previous is not None and abs(v_cruise - previous) > SET_SPEED_CHANGE_TOLERANCE_METERS_PER_SECOND
    raised = previous is not None and v_cruise > previous + SET_SPEED_CHANGE_TOLERANCE_METERS_PER_SECOND
    consumed = self.consume_set_speed_change
    if consumed and (changed or not sm["starpilotCarState"].accelPressed):
      self.consume_set_speed_change = False

    if not sm["selfdriveState"].enabled:
      self.override_disable_time += DT_MDL
      if self.override_disable_time >= SLC_OVERRIDE_DISABLE_CLEAR_TIME:
        self.clear_override()
      return
    self.override_disable_time = 0.0

    target = self.target_to_use
    target_with_offset = target + self.get_offset(target)
    set_speed = v_cruise + v_cruise_diff
    bidirectional = getattr(self.starpilot_toggles, "redneck_cruise", False)
    if self.set_speed_override > 0:
      if bidirectional:
        self.set_speed_override = max(set_speed, 0.0)
      elif set_speed <= 0 or (target_with_offset > 0 and set_speed <= target_with_offset and
                              (self.source != SOURCE_NONE or changed)):
        self.set_speed_override = 0.0
      else:
        self.set_speed_override = set_speed
    elif (target_with_offset > 0 and set_speed > 0 and not consumed and
          ((bidirectional and changed) or (not bidirectional and raised and set_speed > target_with_offset))):
      self.set_speed_override = set_speed

    self.pedal_override = v_ego + v_ego_diff if sm["carState"].gasPressed and v_ego > target_with_offset > 0 else 0.0
    self.overridden_speed = self.pedal_override or self.set_speed_override

  def update(self, dashboard_speed_limit, now, time_validated, v_cruise, v_cruise_diff, v_ego, v_ego_diff, sm,
             *, active=True, display_only=False):
    self.limit_change_started = False
    self.confirmation_button_consumed = False
    self._using_experimental_fallback = False
    self._using_previous_limit_fallback = False
    mode = "display" if display_only else "active" if active else "off"
    if mode != self._mode:
      self.mapbox.reset()
      self._mode = mode
    if not active and not display_only:
      self.reset_control_state()
      self.mapbox.reset()
      self.source, self.target = SOURCE_NONE, 0.0
      self.map_speed_limit = self.next_speed_limit = self.vision_limit = 0.0
      return

    self._update_map_speed_limit(v_ego, sm)
    vision_limit = self._get_vision_limit(v_ego, sm, display_only)
    source, limit = self._select_limit(dashboard_speed_limit, self.map_speed_limit, vision_limit)
    source, limit = self._apply_mapbox_filler(source, limit, now, time_validated, v_ego, sm)

    if display_only:
      self.reset_control_state()
      self.source, self.target = (source, limit) if limit >= 1 else (SOURCE_NONE, 0.0)
      return

    self._active_control = True
    if source == SOURCE_NONE:
      self._update_limit(source, limit, sm)
      self._apply_fallback(v_cruise, sm["selfdriveState"].enabled)
    else:
      self._update_limit(source, limit, sm)
    self._process_adopt_request(source, limit)
    self._update_override(v_cruise, v_cruise_diff, v_ego, v_ego_diff, sm)
