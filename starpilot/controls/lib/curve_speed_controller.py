#!/usr/bin/env python3
import numpy as np

from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL

from openpilot.starpilot.common.starpilot_variables import (
  CITY_SPEED_LIMIT,
  CRUISING_SPEED,
  DEFAULT_LATERAL_ACCELERATION,
  PLANNER_TIME,
)

CALIBRATION_PROGRESS_THRESHOLD = 10 / DT_MDL
CSC_MIN_SPEED = CITY_SPEED_LIMIT * CV.MPH_TO_MS

# braking distance is (v^2 - v_curve^2) / (2 * this), so lower starts the slowdown
# sooner and spreads it further.
CSC_APPROACH_DECEL = 0.3
CSC_TARGET_UP_RATE = 3.0
CSC_TARGET_DOWN_RATE = 2.5
CSC_TARGET_FILTER_RC = 0.4
CSC_EGO_HEADROOM = 2.0            # target never trails below v_ego, so CSC can't drag re-acceleration
CSC_RELEASE_DEBOUNCE = 0.25       # s the envelope must stay clear before that floor applies
CSC_ACTIVE_ON_DELTA = 0.5
CSC_ACTIVE_OFF_DELTA = 0.25
CSC_GLOW_ON_DELTA = 1.0           # ~2.2 mph; separate from CSC_ACTIVE_ON_DELTA (training) so a trivial graze doesn't light the glow
CSC_GLOW_HOLD_TIME = 3.0          # s the cap must stay released before the glow clears, so it doesn't flicker on/off across one curve

CSC_COUNT_CAP = 600               # EMA floor: samples beyond this stop shrinking the update step
CSC_PRIOR_COUNT = 100             # bucket count at which learned data and the prior have equal weight
CSC_LAT_ACCEL_MIN = 1.2
CSC_LAT_ACCEL_MAX = 3.2
CSC_NUDGE = 0.15
CSC_NUDGE_WEIGHT = 20             # counts a single override pseudo-sample is worth
CSC_OVERRIDE_WATCH_TIME = 6.0     # s to keep watching what the driver holds after they reject a cut
CSC_TRAINING_QUIET_TIME = 5.0     # blocks passive samples after CSC limited speed, so it can't learn its own cap
CSC_TRAINING_SETTLE_TIME = 2.0    # driver-owned seconds before a sample counts, so it isn't openpilot's leftover speed
CSC_COMFORT_MARGIN = 1.0          # 1.0 = matches the driver's own learned cornering, no extra cushion

# The model under-reads curvature at range: measured 0.81x actual beyond ~75 m. That holds
# only where the reading is already firm -- weak distant readings carry no usable magnitude
# (0.40x median with a 14:1 spread), so scaling those would amplify noise, not signal.
CSC_FARFIELD_MIN_CURVATURE = 0.004   # ~R 250 m; at this strength range readings were 85%+ reliable
CSC_FARFIELD_MIN_DISTANCE = 30.0     # inside this the model is already accurate
CSC_FARFIELD_GAIN = 1.23             # 1 / 0.81

# Buckets are spaced geometrically, not linearly: comfort is a speed and v = sqrt(a/k), so equal
# steps in k give wildly uneven speed resolution. Regridding is safe -- _normalize_curvature_data
# re-buckets stored keys on load.
MIN_CURVATURE = 0.0005            # R 2000 m — gentler than this never constrains anything
MAX_CURVATURE = 0.02              # R 50 m — already well below the CSC_MIN_SPEED floor
CURVATURE_BUCKETS = 24            # keeps every bucket under ~7 mph wide without over-thinning the data
ROUNDING_PRECISION = 6
CURVATURE_GRID = MIN_CURVATURE * np.power(MAX_CURVATURE / MIN_CURVATURE,
                                          np.arange(CURVATURE_BUCKETS) / (CURVATURE_BUCKETS - 1))
LOG_CURVATURE_GRID = np.log(CURVATURE_GRID)

# Drivers accept more lateral acceleration in sharp slow corners than in highway sweepers.
PRIOR_CURVATURE_BP = [0.001, 0.003, 0.01, 0.03, 0.1]
PRIOR_LAT_ACCEL_V = [1.5, 1.8, 2.2, 2.6, 2.9]


def weighted_isotonic(values, weights):
  """Weighted non-decreasing fit (pool adjacent violators).

  Keeps comfort from falling as curves tighten, without letting a sparse bucket
  overrule a well-sampled neighbour the way a running maximum would.
  """
  block_values: list[float] = []
  block_weights: list[float] = []
  block_sizes: list[int] = []

  for value, weight in zip(values, weights, strict=True):
    block_values.append(float(value))
    block_weights.append(float(weight))
    block_sizes.append(1)

    while len(block_values) > 1 and block_values[-2] > block_values[-1]:
      merged_weight = block_weights[-2] + block_weights[-1]
      merged_value = ((block_values[-2] * block_weights[-2]) + (block_values[-1] * block_weights[-1])) / merged_weight
      block_values.pop()
      block_weights.pop()
      merged_size = block_sizes.pop()
      block_values[-1] = merged_value
      block_weights[-1] = merged_weight
      block_sizes[-1] += merged_size

  fitted = np.empty(len(values))
  index = 0
  for value, size in zip(block_values, block_sizes, strict=True):
    fitted[index:index + size] = value
    index += size
  return fitted


def is_user_overriding_longitudinal(sm):
  try:
    if any(getattr(event, "overrideLongitudinal", False) for event in sm["onroadEvents"]):
      return True
  except (KeyError, TypeError):
    pass

  car_state = sm["carState"]
  starpilot_car_state = sm["starpilotCarState"]
  return bool(
    getattr(car_state, "gasPressed", False) or
    getattr(car_state, "brakePressed", False) or
    getattr(starpilot_car_state, "accelPressed", False)
  )


def is_manual_speed_control(sm):
  """Return whether the driver, rather than longitudinal control, owns speed."""
  return not bool(sm["carControl"].longActive) or is_user_overriding_longitudinal(sm)


class CurveSpeedController:
  def __init__(self, StarPilotVCruise):
    self.starpilot_planner = StarPilotVCruise.starpilot_planner

    self.enable_training = False
    self.nudge_applied = False

    self.override_watch_key = None
    self.override_watch_peak = 0.0
    self.override_watch_timer = 0.0

    self.training_timer = 0.0
    self.persistence_timer = 0.0
    self.training_quiet_timer = 0.0
    self.data_dirty = False

    self.target = 0.0
    self.binding_distance = 0.0
    self.release_timer = 0.0
    self.target_filter = FirstOrderFilter(0.0, CSC_TARGET_FILTER_RC, DT_MDL, initialized=False)
    self.seed_pending = True

    self._long_active_prev = False

    curvature_data = self.starpilot_planner.params.get("CurvatureData")
    self.curvature_data = self._normalize_curvature_data(curvature_data)

    # built through the bucketer so the keys are byte-identical to what training writes
    self.required_curvatures = [self._bucket_curvature(curvature) for curvature in CURVATURE_GRID]

    self.rebuild_lat_accel_curve()
    # publish on the first flush even if this drive never trains, or the readout
    # keeps showing whatever a previous build left behind
    self.data_dirty = True
    # the Settings screen reads the memory param for a live readout -- seed it now, or it
    # shows nothing until the first disk flush
    self._publish_live_values()

  @staticmethod
  def _bucket_curvature(road_curvature):
    clipped_curvature = float(np.clip(abs(road_curvature), MIN_CURVATURE, MAX_CURVATURE))
    # nearest in log space, so a bucket is a constant speed step rather than a constant radius one
    bucket_index = int(np.argmin(np.abs(LOG_CURVATURE_GRID - np.log(clipped_curvature))))
    return str(round(float(CURVATURE_GRID[bucket_index]), ROUNDING_PRECISION))

  @classmethod
  def _normalize_curvature_data(cls, curvature_data):
    if not isinstance(curvature_data, dict):
      return {}

    normalized = {}
    for key, value in curvature_data.items():
      if not isinstance(value, dict):
        continue

      try:
        raw_curvature = abs(float(key))
        average = float(value["average"])
        count = int(value["count"])
      except (KeyError, TypeError, ValueError):
        continue

      if count <= 0:
        continue

      bucket = cls._bucket_curvature(raw_curvature)
      if bucket in normalized:
        existing = normalized[bucket]
        total_count = existing["count"] + count
        normalized[bucket] = {
          "average": ((existing["average"] * existing["count"]) + (average * count)) / total_count,
          "count": total_count,
        }
      else:
        normalized[bucket] = {
          "average": average,
          "count": count,
        }

    return normalized

  def _calibration_progress(self):
    progress = 0.0
    for key in self.required_curvatures:
      if key in self.curvature_data:
        progress += min(self.curvature_data[key]["count"] / CALIBRATION_PROGRESS_THRESHOLD, 1.0)
    return (progress / len(self.required_curvatures)) * 100

  def _publish_live_values(self, progress=None):
    # memory-only and cheap, so this can run every frame training touches the data --
    # it's what the on-device Settings screen reads for a live readout between disk flushes
    params_memory = getattr(self.starpilot_planner, "params_memory", None)
    if params_memory is None:
      return
    if progress is None:
      progress = self._calibration_progress()
    params_memory.put_nonblocking("CalibratedLateralAcceleration", self.lateral_acceleration)
    params_memory.put_nonblocking("CalibrationProgress", progress)

  def _persist_data(self):
    if not self.data_dirty:
      return

    progress = self._calibration_progress()
    self.starpilot_planner.params.put_nonblocking("CalibratedLateralAcceleration", self.lateral_acceleration)
    self.starpilot_planner.params.put_nonblocking("CalibrationProgress", progress)
    self.starpilot_planner.params.put_nonblocking("CurvatureData", self.curvature_data)
    self._publish_live_values(progress)
    self.data_dirty = False
    self.persistence_timer = 0.0

  def flush_data(self):
    self._persist_data()

  def log_data(self, v_ego, sm):
    self.training_quiet_timer = max(self.training_quiet_timer - DT_MDL, 0.0)

    eligible = (
      v_ego > CRUISING_SPEED and
      not self.starpilot_planner.tracking_lead and
      is_manual_speed_control(sm) and
      self.training_quiet_timer <= 0.0
    )
    self.enable_training = False

    if not eligible:
      self.flush_data()
      # decay instead of resetting: a lead flickering in and out of the tracker used to
      # cost the full re-arm, which left almost nothing to learn from on a real drive
      self.training_timer = max(self.training_timer - DT_MDL, 0.0)
      self.persistence_timer = 0.0
      return

    self.training_timer += DT_MDL
    if self.data_dirty:
      self.persistence_timer += DT_MDL

    in_curve = (
      self.training_timer >= CSC_TRAINING_SETTLE_TIME and
      self.starpilot_planner.driving_in_curve and
      not (sm["carState"].leftBlinker or sm["carState"].rightBlinker)
    )
    if in_curve:
      lateral_acceleration = abs(self.starpilot_planner.lateral_acceleration)
      road_curvature = self._bucket_curvature(abs(self.starpilot_planner.road_curvature))

      if road_curvature in self.curvature_data:
        data = self.curvature_data[road_curvature]
        # capped so an established bucket still tracks a change in driving style
        effective_count = min(data["count"], CSC_COUNT_CAP)
        self.curvature_data[road_curvature] = {
          "average": ((data["average"] * effective_count) + lateral_acceleration) / (effective_count + 1),
          "count": data["count"] + 1
        }
      else:
        self.curvature_data[road_curvature] = {
          "average": lateral_acceleration,
          "count": 1
        }

      self.data_dirty = True
      self.rebuild_lat_accel_curve()
      self._publish_live_values()
      self.enable_training = True

      if self.persistence_timer >= PLANNER_TIME:
        self.flush_data()
    elif self.data_dirty:
      self.flush_data()

  def handle_override(self, v_ego, was_controlling, sm, accel_button=False):
    long_active = bool(sm["carControl"].longActive)
    long_dropped = self._long_active_prev and not long_active
    self._long_active_prev = long_active

    self._update_override_watch(sm)

    if not was_controlling:
      self.nudge_applied = False
      return

    if self.nudge_applied:
      return

    if accel_button or (sm["carState"].gasPressed and self.target < v_ego - 0.5):
      # Watch what the driver actually holds instead of stepping by a fixed amount -- CSC is
      # suspended while overridden, so their cornering now measures their real comfort.
      self.override_watch_key = self._bucket_curvature(abs(self.starpilot_planner.road_curvature))
      self.override_watch_peak = abs(self.starpilot_planner.lateral_acceleration)
      self.override_watch_timer = CSC_OVERRIDE_WATCH_TIME
      self.nudge_applied = True
    elif (getattr(sm["carState"], "brakePressed", False) or long_dropped) and self.starpilot_planner.driving_in_curve:
      self._apply_nudge(-CSC_NUDGE)

  def _update_override_watch(self, sm):
    if self.override_watch_key is None:
      return

    lateral_acceleration = abs(self.starpilot_planner.lateral_acceleration)
    if lateral_acceleration > self.override_watch_peak:
      # credit the bucket the peak actually happened in, not the one at the button press
      self.override_watch_peak = lateral_acceleration
      self.override_watch_key = self._bucket_curvature(abs(self.starpilot_planner.road_curvature))

    self.override_watch_timer -= DT_MDL
    if self.override_watch_timer > 0.0 and (is_user_overriding_longitudinal(sm) or
                                            self.starpilot_planner.driving_in_curve):
      return

    key = self.override_watch_key
    self.override_watch_key = None
    # floored at the old fixed step, so a rejection that never reaches a corner still counts
    # and this path can only ever raise the bucket
    self._record_pseudo_sample(key, max(self.override_watch_peak,
                                        self.learned_lat_accel(float(key)) + CSC_NUDGE))

  def _apply_nudge(self, offset):
    key = self._bucket_curvature(abs(self.starpilot_planner.road_curvature))
    # relative to the learned value, not the margined one, or repeated overrides walk the bucket down
    self._record_pseudo_sample(key, self.learned_lat_accel(float(key)) + offset)
    self.nudge_applied = True

  def _record_pseudo_sample(self, key, sample):
    sample = float(np.clip(sample, CSC_LAT_ACCEL_MIN, CSC_LAT_ACCEL_MAX))

    data = self.curvature_data.get(key, {"average": sample, "count": 0})
    effective_count = min(data["count"], CSC_COUNT_CAP)
    total = effective_count + CSC_NUDGE_WEIGHT
    self.curvature_data[key] = {
      "average": ((data["average"] * effective_count) + (sample * CSC_NUDGE_WEIGHT)) / total,
      "count": data["count"] + CSC_NUDGE_WEIGHT,
    }

    self.rebuild_lat_accel_curve()
    self.data_dirty = True
    self.flush_data()

  def rebuild_lat_accel_curve(self):
    grid_k = np.array([float(key) for key in self.required_curvatures])
    prior = np.interp(grid_k, PRIOR_CURVATURE_BP, PRIOR_LAT_ACCEL_V)

    blended = prior.copy()
    counts = np.zeros(len(grid_k))
    for i, key in enumerate(self.required_curvatures):
      data = self.curvature_data.get(key)
      if data:
        confidence = data["count"] / (data["count"] + CSC_PRIOR_COUNT)
        blended[i] = confidence * data["average"] + (1.0 - confidence) * prior[i]
        counts[i] = data["count"]

    blended = np.clip(blended, CSC_LAT_ACCEL_MIN, CSC_LAT_ACCEL_MAX)
    blended = weighted_isotonic(blended, counts + CSC_PRIOR_COUNT)

    self._curve_k = grid_k
    self._curve_a = blended

    if counts.sum() > 0:
      self.lateral_acceleration = float(np.average(blended, weights=counts))
    else:
      self.lateral_acceleration = DEFAULT_LATERAL_ACCELERATION

  def learned_lat_accel(self, curvature):
    """Comfort level learned for this curvature, before any control margin."""
    return float(np.interp(abs(curvature), self._curve_k, self._curve_a))

  def lat_accel_for_curvature(self, curvature):
    lat_accel = np.interp(np.abs(curvature), self._curve_k, self._curve_a) * CSC_COMFORT_MARGIN

    weather = self.starpilot_planner.starpilot_weather
    if weather.weather_id != 0:
      lat_accel = lat_accel * (1.0 - weather.reduce_lateral_acceleration)

    return lat_accel

  @staticmethod
  def _correct_far_field(curvatures, distances):
    """Undo the model's known under-read of distant curvature, where the reading is firm."""
    firm = (curvatures >= CSC_FARFIELD_MIN_CURVATURE) & (distances >= CSC_FARFIELD_MIN_DISTANCE)
    return np.minimum(np.where(firm, curvatures * CSC_FARFIELD_GAIN, curvatures), MAX_CURVATURE)

  def reset(self, v_cruise):
    self.target = float(v_cruise)
    self.release_timer = 0.0
    self.target_filter.x = float(v_cruise)
    self.target_filter.initialized = True
    self.seed_pending = True

  def update_target(self, v_ego, v_cruise):
    if not self.target_filter.initialized:
      self.reset(v_cruise)

    curvatures, distances = self.starpilot_planner.curve_profile
    if len(curvatures) == 0:
      raw_target = float(v_cruise)
      self.binding_distance = 0.0
    else:
      curvatures = self._correct_far_field(curvatures, distances)
      lat_accel = self.lat_accel_for_curvature(curvatures)
      point_speeds = np.sqrt(lat_accel / np.maximum(curvatures, 1e-4))
      point_speeds = np.maximum(point_speeds, CSC_MIN_SPEED)
      allowed_speeds = np.sqrt(point_speeds**2 + 2.0 * CSC_APPROACH_DECEL * np.maximum(distances, 0.0))
      binding_index = int(np.argmin(allowed_speeds))
      raw_target = min(float(allowed_speeds[binding_index]), float(v_cruise))
      self.binding_distance = float(distances[binding_index]) if raw_target < v_cruise else 0.0

    # a fresh activation starts at the envelope, or it spends seconds ramping down
    # toward a curve it already sees (engaging or launching into a turn)
    if self.seed_pending:
      seed = min(float(v_cruise), max(raw_target, v_ego + CSC_EGO_HEADROOM))
      self.target = seed
      self.target_filter.x = seed
      self.seed_pending = False

    if raw_target >= v_ego:
      self.release_timer += DT_MDL
    else:
      self.release_timer = 0.0

    # The headroom aim goes through the rate limiter with everything else; applying it
    # after the clamp let every upward jitter in raw_target reach the target unsmoothed.
    filtered = self.target_filter.update(raw_target)
    self.target = float(np.clip(max(filtered, min(raw_target, v_ego + CSC_EGO_HEADROOM)),
                                self.target - CSC_TARGET_DOWN_RATE * DT_MDL,
                                self.target + CSC_TARGET_UP_RATE * DT_MDL))

    # Once the envelope really has released, the target must not sit under the car or it
    # drags re-acceleration. Debounced, because a single jittery frame doing this yanks a
    # legitimate cut back up to v_ego and strobes the glow on sweepers.
    if self.release_timer >= CSC_RELEASE_DEBOUNCE:
      self.target = max(self.target, min(raw_target, v_ego))

    if self.target < v_cruise - CSC_ACTIVE_ON_DELTA:
      self.training_quiet_timer = CSC_TRAINING_QUIET_TIME
