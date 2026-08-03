#!/usr/bin/env python3
# PFEIFER - SLC - Modified by FrogAi
import calendar
import json
import numpy as np
import requests

from concurrent.futures import ThreadPoolExecutor

from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.car.cruise import V_CRUISE_UNSET

from cereal import custom
from openpilot.starpilot.common.starpilot_utilities import calculate_bearing_offset, calculate_distance_to_point, is_url_pingable

FREE_MAPBOX_REQUESTS = 100_000

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
# Minimum set-speed increase (m/s) counted as a deliberate +/- press. Below the smallest
# real step (1 km/h ≈ 0.28 m/s), above cluster/float jitter.
SET_SPEED_RAISE_EPS = 0.1
VISION_LARGE_REFERENCE_SPEED_DELTA = 30 * CV.MPH_TO_MS
VISION_LARGE_SET_SPEED_MIN_SUPPORT = 3
VISION_SUPPORT_SPEED_TOLERANCE = 0.5 * CV.MPH_TO_MS

class SpeedLimitController:
  def __init__(self, StarPilotVCruise):
    self.starpilot_planner = StarPilotVCruise.starpilot_planner
    self.starpilot_toggles = None

    self.calling_mapbox = False
    self.override_slc = False
    self.override_requires_gas_release = False
    self.override_disable_timer = 0.0
    self._prev_v_cruise = None

    self.denied_target = 0
    self.map_speed_limit = 0
    self.mapbox_limit = 0
    self.next_speed_limit = 0
    self.overridden_speed = 0
    self.segment_distance = 0
    self.speed_limit_changed_timer = 0
    self.target = 0
    self.unconfirmed_speed_limit = 0
    self.vision_limit = 0

    self.previous_source = "None"
    self.source = "None"
    self.previous_road_name = ""

    self._slc_adopt_counter = 0

    mapbox_requests_raw = self.starpilot_planner.params.get("MapBoxRequests", encoding="utf-8")
    try:
      self.mapbox_requests = json.loads(mapbox_requests_raw or "{}")
    except (TypeError, ValueError):
      self.mapbox_requests = {}
    self.mapbox_requests.setdefault("total_requests", 0)
    self.mapbox_requests.setdefault("max_requests", FREE_MAPBOX_REQUESTS - (28 * 100))

    self.mapbox_host = "https://api.mapbox.com"
    self.mapbox_token = self.starpilot_planner.params.get("MapboxSecretKey", encoding="utf-8")

    self.previous_target = self.starpilot_planner.params.get_float("PreviousSpeedLimit")
    self.last_valid_limit = self.previous_target if self.previous_target > 0 else 0

    self.executor = ThreadPoolExecutor(max_workers=1)
    self.mapbox_future = None

    self.session = requests.Session()
    self.session.headers.update({"Accept-Language": "en"})
    self.session.headers.update({"User-Agent": "starpilot-mapbox-speed-limit-retriever/1.0 (https://github.com/FrogAi/StarPilot)"})

  def shutdown(self):
    self.executor.shutdown(wait=False, cancel_futures=True)
    self.session.close()

  @property
  def experimental_mode(self):
    return self.target == 0 and bool(getattr(self.starpilot_toggles, "slc_fallback_experimental_mode", False))

  @property
  def target_to_use(self):
    if self.source == "None" and self.target > 0 and self.last_valid_limit > 0:
      if self.target >= self.last_valid_limit:
        return self.last_valid_limit
    return self.target

  def get_offset(self, target_speed):
    if self.starpilot_toggles is None:
      return 0
    offset_map = OFFSET_MAP_METRIC if self.starpilot_toggles.is_metric else OFFSET_MAP_IMPERIAL
    return next((getattr(self.starpilot_toggles, offset) for low, high, offset in offset_map if low <= target_speed < high), 0)

  @property
  def offset(self):
    return self.get_offset(self.target)

  @property
  def override_mode_enabled(self):
    if self.starpilot_toggles is None:
      return False
    return self.starpilot_toggles.speed_limit_controller_override_manual or self.starpilot_toggles.speed_limit_controller_override_set_speed

  def override_active(self, v_ego, gas_pressed):
    target_to_use = self.target_to_use
    target_with_offset = target_to_use + self.get_offset(target_to_use)
    if target_with_offset <= 0 or not self.override_mode_enabled:
      return False
    return self.overridden_speed > target_with_offset or (gas_pressed and v_ego > target_with_offset)

  def clear_override_for_source_limit(self, desired_source, desired_target, had_override):
    if desired_source == "None" or desired_target <= 0:
      return
    if not had_override and self.overridden_speed <= 0:
      return
    if abs(desired_target - self.last_valid_limit) < 0.1:
      return

    # A new posted limit starts a new segment, so the previous segment's gas override
    # should not carry through until the driver releases and reapplies the pedal.
    self.override_slc = False
    self.overridden_speed = 0
    if had_override:
      self.override_requires_gas_release = True

  def get_mapbox_speed_limit(self, now, time_validated, v_ego, sm):
    if not self.starpilot_planner.gps_valid or not self.mapbox_token or abs(sm["carState"].steeringAngleDeg - sm["liveParameters"].angleOffsetDeg) >= 45:
      self.mapbox_limit = 0
      self.segment_distance = 0
      return

    if v_ego < 1:
      return

    if self.segment_distance > 0:
      self.segment_distance -= v_ego * DT_MDL
      return

    if self.calling_mapbox:
      self.segment_distance = v_ego
      return

    def make_request():
      successful = False
      response_data = None
      try:
        if not is_url_pingable(self.mapbox_host):
          self.segment_distance = 1000
          successful = True
          return None

        if time_validated:
          current_month = now.month
          if current_month != self.mapbox_requests.get("month"):
            self.mapbox_requests.update({
              "month": current_month,
              "total_requests": 0,
              "max_requests": FREE_MAPBOX_REQUESTS - calendar.monthrange(now.year, current_month)[1] * 100,
            })

        self.mapbox_requests["total_requests"] += 1
        self.starpilot_planner.params.put_nonblocking("MapBoxRequests", json.dumps(self.mapbox_requests))

        current_bearing = self.starpilot_planner.gps_position.get("bearing")
        current_latitude = self.starpilot_planner.gps_position.get("latitude")
        current_longitude = self.starpilot_planner.gps_position.get("longitude")

        future_latitude, future_longitude = calculate_bearing_offset(current_latitude, current_longitude, current_bearing, v_ego)

        url = (
          f"{self.mapbox_host}/matching/v5/mapbox/driving/"
          f"{current_longitude},{current_latitude};"
          f"{future_longitude},{future_latitude}.json"
        )

        mapbox_params = {
          "access_token": self.mapbox_token,
          "annotations": "maxspeed,distance",
          "geometries": "polyline6",
          "overview": "full",
          "steps": "false",
          "radiuses": "10;10",
          "tidy": "true",
        }

        response = self.session.get(url, params=mapbox_params, timeout=10)
        response.raise_for_status()

        successful = True
        response_data = response.json()
      except Exception as exception:
        print(f"Unexpected error in Mapbox request: {exception}")
      finally:
        self.calling_mapbox = False

        if not successful:
          self.mapbox_limit = 0
          self.segment_distance = v_ego
      return response_data

    def complete_request(future):
      try:
        data = future.result()
        if data:
          matchings = data.get("matchings") or []
          if not matchings:
            self.mapbox_limit = 0
            self.segment_distance = v_ego
            return

          legs = (matchings[0] or {}).get("legs") or []
          if not legs:
            self.mapbox_limit = 0
            self.segment_distance = v_ego
            return

          annotation = legs[0].get("annotation") or {}

          distances = annotation.get("distance") or [v_ego]
          segment_distance = distances[0]

          speed_data = annotation.get("maxspeed", [])
          if speed_data:
            first_segment_speed = speed_data[0]
            try:
              raw_speed = float(first_segment_speed.get("speed") if first_segment_speed.get("speed") != "none" else 0.0)
            except (ValueError, TypeError):
              raw_speed = 0.0
            unit = first_segment_speed.get("unit", "km/h")
            if raw_speed > 0:
              if unit == "mph":
                self.mapbox_limit = raw_speed * CV.MPH_TO_MS
              else:
                self.mapbox_limit = raw_speed * CV.KPH_TO_MS
              self.segment_distance = segment_distance
              return

        self.mapbox_limit = 0
        self.segment_distance = v_ego

      except Exception as exception:
        print(f"Mapbox Callback Error: {exception}")
        self.mapbox_limit = 0
        self.segment_distance = v_ego
      finally:
        self.mapbox_future = None

    self.calling_mapbox = True
    try:
      future = self.executor.submit(make_request)
    except RuntimeError:
      self.calling_mapbox = False
      self.segment_distance = v_ego
      return

    self.mapbox_future = future
    future.add_done_callback(complete_request)

  def handle_limit_change(self, desired_source, desired_target, current_road_name, v_ego, sm):
    self.speed_limit_changed_timer += DT_MDL
    had_override = self.override_active(v_ego, sm["carState"].gasPressed)

    long_active = sm["carControl"].longActive
    speed_limit_accepted = sm["starpilotCarState"].accelPressed and long_active
    if not speed_limit_accepted and self._slc_adopt_counter % 4 == 0:
      speed_limit_accepted = self.starpilot_planner.params_memory.get_bool("SpeedLimitAccepted")
    speed_limit_denied = sm["starpilotCarState"].decelPressed or (self.speed_limit_changed_timer >= 30 and long_active)

    if not long_active and not sm["selfdriveState"].enabled:
      speed_limit_accepted = True

    if speed_limit_accepted:
      self.source = desired_source
      self.target = desired_target
      self.clear_override_for_source_limit(desired_source, desired_target, had_override)

      self.starpilot_planner.params_memory.remove("SpeedLimitAccepted")

    elif speed_limit_denied:
      self.denied_target = desired_target

      self.previous_source = desired_source
      self.previous_target = desired_target
      self.previous_road_name = current_road_name

    elif desired_target < self.target and (desired_source == "None" or not self.starpilot_toggles.speed_limit_confirmation_lower):
      self.source = desired_source
      self.target = desired_target
      self.clear_override_for_source_limit(desired_source, desired_target, had_override)

    elif desired_target > self.target and (desired_source == "None" or not self.starpilot_toggles.speed_limit_confirmation_higher):
      self.source = desired_source
      self.target = desired_target
      if 0 < self.overridden_speed <= self.target + self.get_offset(self.target):
        self.clear_override_for_source_limit(desired_source, desired_target, had_override)

    elif desired_target == self.target:
      self.source = desired_source
      self.target = desired_target

    else:
      self.source = "None"
      self.unconfirmed_speed_limit = desired_target

    if (self.target != self.previous_target or self.previous_road_name != current_road_name) and self.target > 0 and not speed_limit_denied:
      self.denied_target = 0

      self.previous_source = self.source
      self.previous_target = self.target
      self.previous_road_name = current_road_name

      self.starpilot_planner.params.put_nonblocking("PreviousSpeedLimit", float(self.target))

  def update_limits(self, dashboard_speed_limit, now, time_validated, v_cruise, v_ego, sm, display_only=False):
    self.update_map_speed_limit(v_ego, sm)
    vision_enabled = getattr(self.starpilot_toggles, "vision_speed_limit_detection", False)
    self.vision_limit = self.starpilot_planner.params_memory.get_float("VisionSpeedLimit") if vision_enabled else 0
    usable_vision_limit = self.vision_limit
    # The planner clamps V_CRUISE_UNSET to V_CRUISE_MAX, so plausibility must use the raw selected speed.
    raw_set_speed_kph = float(sm["carState"].vCruise)
    selected_set_speed = raw_set_speed_kph * CV.KPH_TO_MS if 0 < raw_set_speed_kph < V_CRUISE_UNSET else 0
    reference_speed = selected_set_speed if selected_set_speed > 0 else max(float(v_ego), 0)
    if (
      usable_vision_limit > 0 and reference_speed > 0 and
      abs(usable_vision_limit - reference_speed) >= VISION_LARGE_REFERENCE_SPEED_DELTA
    ):
      support_count = self.starpilot_planner.params_memory.get_int("VisionSpeedLimitSupportCount")
      support_speed = self.starpilot_planner.params_memory.get_float("VisionSpeedLimitSupportSpeed")
      if support_count < VISION_LARGE_SET_SPEED_MIN_SUPPORT or abs(support_speed - usable_vision_limit) > VISION_SUPPORT_SPEED_TOLERANCE:
        usable_vision_limit = 0

    configured_priorities = {
      self.starpilot_toggles.speed_limit_priority1,
      self.starpilot_toggles.speed_limit_priority2,
    }
    limits = {
      "Dashboard": dashboard_speed_limit,
      "Map Data": self.map_speed_limit,
    }
    if "Vision" in configured_priorities:
      limits["Vision"] = usable_vision_limit
    filtered_limits = {source: limit for source, limit in limits.items() if limit >= 1}

    if self.starpilot_toggles.speed_limit_priority_highest:
      desired_source = max(filtered_limits, key=filtered_limits.get, default="None")
      desired_target = filtered_limits.get(desired_source, 0)

    elif self.starpilot_toggles.speed_limit_priority_lowest:
      desired_source = min(filtered_limits, key=filtered_limits.get, default="None")
      desired_target = filtered_limits.get(desired_source, 0)

    elif filtered_limits:
      for priority in [
        self.starpilot_toggles.speed_limit_priority1,
        self.starpilot_toggles.speed_limit_priority2
      ]:
        if priority in filtered_limits:
          desired_source = priority
          desired_target = filtered_limits[desired_source]
          break
      else:
        desired_source = "None"
        desired_target = 0

    else:
      desired_source = "None"
      desired_target = 0

    if desired_target == 0:
      if self.mapbox_requests["total_requests"] < self.mapbox_requests["max_requests"] and self.starpilot_toggles.slc_mapbox_filler:
        self.get_mapbox_speed_limit(now, time_validated, v_ego, sm)

        if self.mapbox_limit >= 1:
          desired_source = "Mapbox"
          desired_target = self.mapbox_limit

      if not display_only and desired_target == 0:
        if self.previous_target > 0 and self.starpilot_toggles.slc_fallback_previous_speed_limit:
          desired_source = self.previous_source
          desired_target = self.previous_target

          self.target = desired_target

        elif sm["selfdriveState"].enabled and self.starpilot_toggles.slc_fallback_set_speed:
          desired_source = "None"
          desired_target = v_cruise
    else:
      self.mapbox_limit = 0
      self.segment_distance = 0

    if display_only:
      self.speed_limit_changed_timer = 0
      self.unconfirmed_speed_limit = 0
      self.overridden_speed = 0
      self.override_requires_gas_release = False

      if desired_target >= 1:
        self.source = desired_source
        self.target = desired_target
      else:
        self.source = "None"
        self.target = 0

      return

    current_road_name = sm["mapdOut"].roadName if desired_source == "Map Data" else ""

    if abs(desired_target - self.previous_target) >= 1 or (current_road_name != self.previous_road_name and current_road_name != ""):
      self.handle_limit_change(desired_source, desired_target, current_road_name, v_ego, sm)
    elif desired_source != self.source and (abs(desired_target - self.target) < 1 or self.target == 0):
      self.source = desired_source
      self.target = desired_target
    else:
      self.speed_limit_changed_timer = 0
      self.unconfirmed_speed_limit = 0

    if self.source != "None" and self.target > 0:
      self.last_valid_limit = self.target

    self._slc_adopt_counter += 1
    if self._slc_adopt_counter % 4 == 0 and self.starpilot_planner.params_memory.get_bool("SLCAdoptSpeedLimit"):
      self.starpilot_planner.params_memory.remove("SLCAdoptSpeedLimit")
      if desired_target > 0:
        self.overridden_speed = 0
        self.denied_target = 0
        self.source = desired_source
        self.target = desired_target
        self.previous_source = desired_source
        self.previous_target = desired_target
        self.speed_limit_changed_timer = 0
        self.unconfirmed_speed_limit = 0
        self.starpilot_planner.params.put_nonblocking("PreviousSpeedLimit", float(self.target))
        self.starpilot_planner.params_memory.put_float("SLCForceCruiseSpeed", self.target + self.offset)

  def update_map_speed_limit(self, v_ego, sm):
    next_speed_limit_distance = sm["mapdOut"].nextSpeedLimitDistance

    way_sel = sm["mapdOut"].waySelectionType
    if way_sel in (custom.WaySelectionType.current,
                   custom.WaySelectionType.extended):
      self.map_speed_limit = sm["mapdOut"].speedLimit
      self.next_speed_limit = sm["mapdOut"].nextSpeedLimit
    elif way_sel in (custom.WaySelectionType.predicted,
                     custom.WaySelectionType.possible):
      speed = sm["mapdOut"].speedLimit
      if speed > 0 and (self.map_speed_limit == 0 or speed < self.map_speed_limit):
        self.map_speed_limit = speed
      self.next_speed_limit = 0
    else:
      self.next_speed_limit = 0

    if self.next_speed_limit > 0:
      if self.map_speed_limit < self.next_speed_limit:
        max_lookahead = self.starpilot_toggles.map_speed_lookahead_higher * v_ego
      elif self.map_speed_limit > self.next_speed_limit:
        max_lookahead = self.starpilot_toggles.map_speed_lookahead_lower * v_ego
      else:
        max_lookahead = 0

      if next_speed_limit_distance < max_lookahead:
        self.map_speed_limit = self.next_speed_limit

  def update_override(self, v_cruise, v_cruise_diff, v_ego, v_ego_diff, sm):
    # A +/- press that raises the set speed is the gesture that (re)arms Max Set Speed
    # override. Detect the rising edge on the raw set speed (button-driven, no cluster jitter);
    # requiring a fresh edge is what makes the override clear per speed zone — once a new posted
    # limit wipes it (clear_override_for_source_limit), a steady high set speed will not re-arm.
    prev_v_cruise = self._prev_v_cruise
    self._prev_v_cruise = v_cruise
    set_speed_raised = prev_v_cruise is not None and v_cruise > prev_v_cruise + SET_SPEED_RAISE_EPS

    if not sm["selfdriveState"].enabled:
      self.override_disable_timer += DT_MDL
      if self.override_disable_timer >= SLC_OVERRIDE_DISABLE_CLEAR_TIME:
        self.override_slc = False
        self.overridden_speed = 0
        self.override_requires_gas_release = False
      return

    self.override_disable_timer = 0.0

    if not sm["carState"].gasPressed:
      self.override_requires_gas_release = False

    target_to_use = self.target_to_use
    offset = self.get_offset(target_to_use)
    set_speed = v_cruise + v_cruise_diff
    self.override_slc = self.override_slc and self.overridden_speed > target_to_use + offset > 0
    self.override_slc |= not self.override_requires_gas_release and sm["carState"].gasPressed and v_ego > target_to_use + offset > 0
    # Max Set Speed mode: raising the set speed (+/-) above the posted limit overrides the
    # SLC hold directly, no gas pedal required. Only a fresh +/- press arms it, so entering a
    # new speed zone clears the override until the driver raises the set speed again.
    self.override_slc |= (self.starpilot_toggles.speed_limit_controller_override_set_speed
                          and set_speed_raised and set_speed > target_to_use + offset > 0)

    if self.override_slc:
      if self.starpilot_toggles.speed_limit_controller_override_manual:
        if sm["carState"].gasPressed:
          self.overridden_speed = max(v_ego + v_ego_diff, self.overridden_speed)
        self.overridden_speed = float(np.clip(self.overridden_speed, target_to_use + offset, v_cruise + v_cruise_diff))
      elif self.starpilot_toggles.speed_limit_controller_override_set_speed:
        self.overridden_speed = set_speed
    else:
      self.overridden_speed = 0
