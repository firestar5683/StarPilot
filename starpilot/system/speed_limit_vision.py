#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import time

from collections import Counter, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

from openpilot.common.constants import CV
from openpilot.common.realtime import set_core_affinity
from openpilot.common.swaglog import cloudlog
from openpilot.starpilot.common.cpu_throttle import device_cpu_throttle_factor
from openpilot.system.hardware import PC

RUNTIME_LOOP_HZ = 20
INFERENCE_INTERVAL = 0.15
FOLLOWUP_INFERENCE_INTERVAL = 0.10
FOLLOWUP_WINDOW_SECONDS = 2.0
TEMPORAL_TRACKING_ENABLED = False
TRACK_CONFIRMED_PROPOSALS_ENABLED = False
TRACK_CLASSIFICATION_INTERVAL = 0.12
TRACK_BUSY_CLASSIFICATION_INTERVAL = 0.35
TRACK_DETECTOR_INTERVAL = 0.55
TRACK_MAX_AGE_SECONDS = 2.0
TRACK_MIN_PROPOSAL_CONFIDENCE = 0.10
TRACK_UNREADABLE_MIN_PROPOSAL_CONFIDENCE = 0.22
TRACK_MAX_CONSECUTIVE_FAILED_READS = 2
TRACK_MIN_FEATURE_COUNT = 4
TRACK_MAX_AREA_RATIO = 0.18
TRACK_CROP_PADDING_RATIO = 0.06
TRACK_REPEAT_CONFIDENCE_BONUS = 0.12
BUSY_INFERENCE_INTERVAL = 1.0
LIVE_POSE_RECOVERY_THROTTLE_SECONDS = 2.0
LIVE_POSE_RECOVERY_INFERENCE_INTERVAL = 1.0
RUNTIME_TELEMETRY_INTERVAL_SECONDS = 2.0
DEBUG_HEARTBEAT_INTERVAL_SECONDS = 30.0
DEFAULT_DETECTOR_INPUT_SIZE = 640
DETECTOR_INPUT_SIZE_CANDIDATES = (640, 512, 448, 416, 384, 320, 288, 256, 224, 192)
DEFAULT_CLASSIFIER_INPUT_SIZE = 128
CLASSIFIER_INPUT_SIZE_CANDIDATES = (128, 112, 96, 80, 64)
FULL_FRAME_OCR_FALLBACK_ENABLED = False
DETECTOR_CLASSIFIER_CROP_OCR_ENABLED = False
DETECTOR_CLASSIFIER_REGION_MODE = "right_roi"  # full, right_roi, full_and_right_roi
DEVICE_BUSY_AVG_CPU_USAGE_PERCENT = 78.0
DEVICE_BUSY_MAX_CPU_USAGE_PERCENT = 92.0
DEVICE_BUSY_HOT_CORE_COUNT = 4
MIN_DETECTION_CONFIDENCE = 0.2
STRONG_DETECTION_CONFIDENCE = 0.72
OCR_MIN_CONFIDENCE = 0.35
VALUE_TEMPLATE_MIN_CONFIDENCE = 0.55
HISTORY_SECONDS = 2.0
CONSISTENT_DETECTIONS = 2
# These counts must remain achievable at the measured 1.5 Hz onroad cadence.
CHANGE_CONSISTENT_DETECTIONS = 2
CHANGE_SINGLE_READ_MIN_CONFIDENCE = 0.83
CHANGE_REPEAT_MIN_CONFIDENCE = 0.70
LOW_SPEED_CHANGE_CONSISTENT_DETECTIONS = 2
LOW_SPEED_CHANGE_MIN_CONFIDENCE = 0.90
LOW_SPEED_CHANGE_ALLOW_STRONG_CONSENSUS = True
MODEL_DETECTION_SHORT_CIRCUIT_CONFIDENCE = 0.65
PUBLISHED_HOLD_SECONDS = 300.0
PUBLISHED_CHANGE_COOLDOWN_SECONDS = 1.4
PUBLISHED_REVERT_CONFIDENCE = 0.97
AUTO_BOOKMARK_CONFIRM_DELAY_SECONDS = 0.9
AUTO_BOOKMARK_COOLDOWN_SECONDS = 8.0
AUTO_BOOKMARK_MIN_CONFIDENCE = 0.62
TRAINING_COLLECTOR_CONFIRM_DELAY_SECONDS = 0.7
TRAINING_COLLECTOR_COOLDOWN_SECONDS = 2.5
TRAINING_COLLECTOR_MIN_CONFIDENCE = 0.40
MAP_NEXT_REVIEW_DISTANCE_METERS = 120.0
MAP_TRANSITION_MISS_CAPTURE_COOLDOWN_SECONDS = 8.0
MAP_VISION_MATCH_WINDOW_SECONDS = 2.5
MODEL_PROPOSAL_MIN_CONFIDENCE = 0.0001
MODEL_PROPOSAL_MAX_COUNT = 4
MODEL_PROPOSAL_MAX_AREA_RATIO = 0.18
MODEL_PROPOSAL_MIN_WIDTH = 10
MODEL_PROPOSAL_MIN_HEIGHT = 18
MODEL_PROPOSAL_MIN_X_RATIO = 0.35
MODEL_PROPOSAL_MAX_Y_RATIO = 0.82
MODEL_PROPOSAL_EXPANSIONS = (
  (1.2, 1.6, 1.2, 1.8),
)
MODEL_PROPOSAL_TRIM_BOTTOM_RATIOS = (1.0, 0.78)

ROI_WINDOWS = (
  {"bounds": (0.48, 0.00, 0.98, 0.42), "min_confidence": MIN_DETECTION_CONFIDENCE},
  {"bounds": (0.52, 0.02, 0.97, 0.58), "min_confidence": 0.22},
  {"bounds": (0.62, 0.02, 0.99, 0.68), "min_confidence": 0.18},
  {"bounds": (0.45, 0.00, 1.00, 0.82), "min_confidence": 0.06},
)
EDGE_MARGIN_RATIO = 0.03
MAX_BOX_AREA_RATIO = 0.22

OCR_SEARCH_WINDOWS = (
  (0.45, 0.05, 0.92, 0.86),
  (0.65, 0.08, 0.98, 0.76),
)
OCR_SEARCH_THRESHOLDS = (130,)
OCR_SEARCH_CROP_VARIANTS = (
  (0.08, 0.06, 0.10),
)
OCR_SEARCH_UPSCALE = 3
OCR_FALLBACK_MIN_CONFIDENCE = 0.55
VALUE_TEMPLATE_ROIS = (
  (0.35, 0.82, 0.15, 0.78),
  (0.45, 0.85, 0.18, 0.78),
  (0.40, 0.84, 0.18, 0.75),
)
REGULATORY_WHITE_VALUE_MIN = 135
REGULATORY_WHITE_SAT_MAX = 70
REGULATORY_DARK_VALUE_MAX = 115
REGULATORY_DARK_SAT_MAX = 110
REGULATORY_YELLOW_HUE_MIN = 12
REGULATORY_YELLOW_HUE_MAX = 45
REGULATORY_YELLOW_SAT_MIN = 70
REGULATORY_YELLOW_VALUE_MIN = 85
REGULATORY_RED_LOW_HUE_MAX = 12
REGULATORY_RED_HIGH_HUE_MIN = 168
REGULATORY_RED_SAT_MIN = 80
REGULATORY_RED_VALUE_MIN = 60
REGULATORY_GREEN_HUE_MIN = 45
REGULATORY_GREEN_HUE_MAX = 90
REGULATORY_BLUE_HUE_MIN = 90
REGULATORY_BLUE_HUE_MAX = 135
REGULATORY_COLORED_SAT_MIN = 70
REGULATORY_COLORED_VALUE_MIN = 70
REGULATORY_MIN_WHITE_RATIO = 0.08
REGULATORY_MIN_DARK_RATIO = 0.01
REGULATORY_MAX_YELLOW_RATIO = 0.12
REGULATORY_MAX_RED_RATIO = 0.10
REGULATORY_MAX_GREEN_RATIO = 0.35
REGULATORY_MAX_BLUE_RATIO = 0.35
REGULATORY_MIN_WHITE_COMPONENT_RATIO = 0.012
REGULATORY_MIN_COMPONENT_FILL = 0.36
REGULATORY_MIN_COMPONENT_HEIGHT_RATIO = 0.2
REGULATORY_MIN_COMPONENT_WIDTH_RATIO = 0.12
REGULATORY_MIN_ASPECT_RATIO = 0.28
REGULATORY_MAX_ASPECT_RATIO = 1.25

SPEED_LIMIT_CLASSES = {
  2: 10,
  3: 100,
  4: 110,
  5: 120,
  6: 20,
  7: 30,
  8: 40,
  9: 50,
  10: 60,
  11: 70,
  12: 80,
  13: 90,
}

VALID_SPEED_LIMITS_MPH = set(range(5, 125, 5))
MIN_PUBLISHABLE_SPEED_LIMIT_MPH = 5
MAX_IMPERIAL_PUBLISHABLE_SPEED_LIMIT_MPH = 80
LEGACY_MODEL_PATH = Path(__file__).resolve().parents[1] / "assets" / "vision_models" / "speed_limit_vision.onnx"
US_DETECTOR_MODEL_PATH = Path(__file__).resolve().parents[1] / "assets" / "vision_models" / "speed_limit_us_detector.onnx"
US_CLASSIFIER_MODEL_PATH = Path(__file__).resolve().parents[1] / "assets" / "vision_models" / "speed_limit_us_value_classifier.onnx"
US_REJECT_CLASSIFIER_MODEL_PATH = Path(__file__).resolve().parents[1] / "assets" / "vision_models" / "speed_limit_us_reject_classifier.onnx"
US_DETECTOR_CLASSES = {
  0: "regulatory_speed_limit",
  1: "advisory_speed_limit",
  2: "school_zone_speed_limit",
}
US_CLASSIFIER_SPEED_VALUES = (10, 100, 15, 20, 25, 30, 35, 40, 45, 5, 50, 55, 60, 65, 70, 75, 80, 90)
EXTENDED_CLASSIFIER_SPEED_VALUES = frozenset((5, 10, 80, 90, 100))
SCHOOL_ZONE_SPEED_VALUES = frozenset((15, 20, 25))
US_DETECTOR_MIN_CONFIDENCE = 0.06
US_CLASSIFIER_MIN_CONFIDENCE = 0.60
EXTENDED_CLASSIFIER_MIN_CONFIDENCE = 0.90
US_CLASSIFIER_REJECT_MIN_CONFIDENCE = 0.85
SEPARATE_REJECT_CLASSIFIER_ENABLED = False
US_REJECT_CLASSIFIER_MIN_CONFIDENCE = 0.85
DETECTOR_CLASSIFIER_EXPANSIONS = (
  (0.00, 0.00, 0.00, 0.00, 1.10),
  (0.10, 0.06, 0.10, 0.12, 1.00),
  (0.00, 0.00, 0.18, 0.18, 0.55),
)
SCHOOL_ZONE_DIRECT_EXPANSIONS = (
  (0.00, 0.00, 0.18, 0.18),
  (0.00, 0.00, 0.22, 0.18),
)
SCHOOL_ZONE_READ_VARIANTS = (
  (0.00, 0.00, 1.00, 1.00, 0.80),
  (0.00, 0.35, 1.00, 1.00, 0.88),
  (0.00, 0.45, 1.00, 1.00, 0.96),
  (0.12, 0.38, 0.88, 1.00, 1.00),
)
DETECTOR_CLASSIFIER_SUPPORT_BONUS = 0.06
DETECTOR_CLASSIFIER_REGULATORY_BONUS = 0.05
DETECTOR_CLASSIFIER_NON_REGULATORY_PENALTY = 0.03
DETECTOR_CLASSIFIER_SMALL_BOX_AREA_RATIO = 0.004
DETECTOR_CLASSIFIER_TINY_LOW_CONF_AREA_RATIO = 0.002
DETECTOR_CLASSIFIER_TINY_LOW_CONF_MIN_CONFIDENCE = 0.16
DETECTOR_CLASSIFIER_MIN_ACCEPT_WIDTH = 28
DETECTOR_CLASSIFIER_MIN_ACCEPT_HEIGHT = 40
DETECTOR_CLASSIFIER_RESCUE_MIN_WIDTH = 14
DETECTOR_CLASSIFIER_RESCUE_MIN_HEIGHT = 18
DETECTOR_CLASSIFIER_RESCUE_MIN_X_RATIO = 0.52
DETECTOR_CLASSIFIER_RESCUE_MIN_SUPPORT = 2
DETECTOR_CLASSIFIER_RESCUE_MIN_CONFIDENCE = 0.90
DETECTOR_CLASSIFIER_RESCUE_MAX_SCORE = 0.64
DETECTOR_CLASSIFIER_STRONG_RESCUE_MIN_SUPPORT = 3
DETECTOR_CLASSIFIER_STRONG_RESCUE_MIN_PROPOSAL_CONFIDENCE = 0.60
DETECTOR_CLASSIFIER_STRONG_RESCUE_MIN_READ_CONFIDENCE = 0.995
DETECTOR_CLASSIFIER_STRONG_RESCUE_MAX_SCORE = 0.74
DETECTOR_CLASSIFIER_TRUSTED_MODEL_MAX_HEIGHT = 55
DETECTOR_CLASSIFIER_TRUSTED_MODEL_MAX_AREA_RATIO = 0.002
DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_PROPOSAL_CONFIDENCE = 0.18
DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_X_RATIO = 0.52
DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_READ_CONFIDENCE = 0.65
DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_SUPPORT = 2
DETECTOR_CLASSIFIER_STRONG_MODEL_MIN_PROPOSAL_CONFIDENCE = 0.60
DETECTOR_CLASSIFIER_STRONG_MODEL_MIN_READ_CONFIDENCE = 0.995
DETECTOR_CLASSIFIER_STRONG_MODEL_CONSENSUS_MIN_READ_CONFIDENCE = 0.95
DETECTOR_CLASSIFIER_STRONG_MODEL_CONSENSUS_ENABLED = True
DETECTOR_CLASSIFIER_STRONG_MODEL_CONSENSUS_MIN_SUPPORT = 2
DETECTOR_CLASSIFIER_MODEL_ONLY_CONSENSUS_MIN_CONFIDENCE = 0.90
DETECTOR_CLASSIFIER_MODEL_ONLY_CONSENSUS_MIN_SUPPORT = 2
SCHOOL_ZONE_SPEED_PRIOR = 0.12
SCHOOL_ZONE_SUPPORT_BONUS = 0.08
SCHOOL_ZONE_MIN_SUPPORT = 2
SCHOOL_ZONE_MIN_CONFIDENCE = 0.70
SCHOOL_ZONE_SINGLE_READ_CONFIDENCE = 0.975
SCHOOL_ZONE_SHORT_CIRCUIT_CONFIDENCE = 0.78
SCHOOL_ZONE_FALLBACK_MIN_CONFIDENCE = 0.35
NON_SCHOOL_LOW_SPEED_COMPETING_MIN_CONFIDENCE = 0.95
DEBUG_BASE_DIR = Path("/data/media/0/vision_speed_limit_debug")
DEBUG_RUNTIME_STATUS_PATH = DEBUG_BASE_DIR / "runtime_status.json"
DEBUG_CAPTURE_DIRNAME = "captures"
SNAPSHOT_JPEG_QUALITY = 85
SPEED_LIMIT_VISION_AFFINITY_CORES = [0, 1, 2]
SPEED_LIMIT_VISION_COEXISTENCE_AFFINITY_CORES = [0, 1]
COEXISTENCE_PARAM_REFRESH_SECONDS = 2.0
COEXISTENCE_TRACK_DETECTOR_INTERVAL = 0.80
COEXISTENCE_DETECTOR_CLASSIFIER_EXPANSIONS = (
  (0.00, 0.00, 0.00, 0.00, 1.10),
  (0.10, 0.06, 0.10, 0.12, 1.00),
)


def device_cpu_usage_busy(cpu_usage):
  usage = list(cpu_usage)
  if not usage:
    return False
  return (
    sum(usage) / len(usage) >= DEVICE_BUSY_AVG_CPU_USAGE_PERCENT or
    sum(core_usage >= DEVICE_BUSY_MAX_CPU_USAGE_PERCENT for core_usage in usage) >= DEVICE_BUSY_HOT_CORE_COUNT
  )


@dataclass
class Detection:
  speed_limit_mph: int
  confidence: float
  strong_consensus: bool = False


@dataclass(frozen=True)
class DetectorProposal:
  confidence: float
  class_id: int
  bbox: tuple[int, int, int, int]
  speed_limit_mph: int = 0


@dataclass
class ProposalTrack:
  proposal: DetectorProposal
  bbox: tuple[int, int, int, int]
  previous_gray: np.ndarray
  points: np.ndarray
  started_at: float
  last_classified_at: float
  last_speed_limit_mph: int = 0
  consistent_reads: int = 0
  consecutive_failed_reads: int = 0


@dataclass
class HistoryEntry:
  speed_limit_mph: int
  confidence: float
  created_at: float
  strong_consensus: bool = False


class SpeedLimitVisionDaemon:
  def __init__(self, use_runtime=True):
    self.use_runtime = use_runtime
    self.params = None
    self.params_memory = None
    self.Ratekeeper = None
    self.messaging = None
    self.pm = None
    self.VisionIpcClient = None
    self.VisionStreamType = None
    self.sm = None
    self.is_metric = False

    if self.use_runtime:
      from cereal import messaging
      from msgq.visionipc import VisionIpcClient, VisionStreamType
      from openpilot.common.params import Params
      from openpilot.common.realtime import Ratekeeper

      self.messaging = messaging
      self.pm = messaging.PubMaster(["userBookmark"])
      self.params = Params(return_defaults=True)
      self.params_memory = Params(memory=True)
      self.is_metric = self.params.get_bool("IsMetric")
      self.Ratekeeper = Ratekeeper
      self.VisionIpcClient = VisionIpcClient
      self.VisionStreamType = VisionStreamType
      self.sm = messaging.SubMaster(["deviceState", "mapdOut", "userBookmark", "livePose", "starpilotCarState"])

    self.client = None
    self.stream_name = ""
    self.stream_type = None

    self.net = None
    self.classifier_net = None
    self.model_mode = "legacy"
    self.detector_input_size = DEFAULT_DETECTOR_INPUT_SIZE
    self.classifier_input_size = DEFAULT_CLASSIFIER_INPUT_SIZE
    self.last_error = ""
    self.last_inference_at = -float("inf")
    self.last_detection_at = 0.0
    self.last_live_pose_inputs_not_ok_at = -float("inf")
    self.last_road_name = ""
    self.followup_until = 0.0
    self.latest_detector_proposal = None
    self.proposal_track = None
    self.track_inference_count = 0
    self.track_failure_count = 0
    self.track_start_count = 0
    self.max_track_proposal_confidence = 0.0
    self.started_prev = False
    self.parked_prev = False

    self.history: deque[HistoryEntry] = deque()
    self.published_speed_limit_mph = 0
    self.published_confidence = 0.0
    self.previous_published_speed_limit_mph = 0
    self.last_publish_change_at = 0.0
    self.last_published_support_at = 0.0
    self.last_candidate_speed_limit_mph = 0
    self.last_candidate_confidence = 0.0
    self.last_candidate_at = 0.0
    self.last_auto_bookmark_at = 0.0
    self.last_auto_bookmark_speed_limit_mph = 0
    self.last_auto_bookmark_publish_at = 0.0
    self.pending_auto_bookmark = None
    self.last_training_capture_at = 0.0
    self.last_training_capture_speed_limit_mph = 0
    self.pending_training_capture = None
    self.last_map_speed_limit_mph = 0
    self.last_map_transition_miss_at = 0.0
    self.last_map_transition_miss_speed_limit_mph = 0
    self.ignore_next_user_bookmark = False
    self.current_frame_bgr = None

    self.debug_session_id = ""
    self.debug_dir = None
    self.debug_capture_dir = None
    self.debug_log_path = None
    self.debug_bookmark_count = 0
    self.debug_session_started_at = 0.0
    self.debug_session_unavailable = False
    self.last_logged_status = ""
    self.last_logged_candidate = None
    self.last_runtime_telemetry_at = 0.0
    self.last_debug_heartbeat_at = 0.0
    self.loop_count = 0
    self.inference_count = 0
    self.detector_inference_count = 0
    self.interval_skip_count = 0
    self.busy_skip_count = 0
    self.camera_unavailable_count = 0
    self.empty_frame_count = 0
    self.detection_count = 0
    self.last_inference_interval = INFERENCE_INTERVAL
    self.last_inference_interval_reason = "steady"
    self.last_cpu_busy = False
    self.coexistence_mode = False
    self.last_coexistence_param_refresh_at = -float("inf")
    self.temporal_tracking_enabled = TEMPORAL_TRACKING_ENABLED
    self.track_detector_interval = TRACK_DETECTOR_INTERVAL
    self.detector_classifier_expansions = DETECTOR_CLASSIFIER_EXPANSIONS
    self.last_frame_process_duration_s = 0.0
    self.last_detector_forward_count = 0
    self.last_detector_forward_duration_s = 0.0
    self.last_classifier_forward_count = 0
    self.last_classifier_forward_duration_s = 0.0

    self.digit_templates = self._build_digit_templates()
    self.speed_value_templates = self._build_speed_value_templates()
    self._load_model()

  def _start_debug_session(self) -> bool:
    if not self.use_runtime or self.params_memory is None or self.debug_session_id or self.debug_session_unavailable:
      return False

    timestamp = datetime.now(UTC)
    session_id = timestamp.strftime("%Y%m%d_%H%M%S")
    debug_dir = DEBUG_BASE_DIR / session_id
    try:
      suffix = 1
      while debug_dir.exists():
        suffix += 1
        session_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{suffix}"
        debug_dir = DEBUG_BASE_DIR / session_id

      debug_dir.mkdir(parents=True, exist_ok=True)
      capture_dir = debug_dir / DEBUG_CAPTURE_DIRNAME
      capture_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
      self.debug_session_unavailable = True
      cloudlog.warning(f"Vision speed-limit debug storage unavailable: {exc}")
      try:
        self.params_memory.put("VisionSpeedLimitLastEvent", f"debug storage unavailable: {type(exc).__name__}"[:160])
      except Exception:
        pass
      return False

    self.debug_session_id = session_id
    self.debug_dir = debug_dir
    self.debug_capture_dir = capture_dir
    self.debug_log_path = debug_dir / "events.jsonl"
    self.debug_bookmark_count = 0
    self.debug_session_started_at = time.monotonic()
    self.last_logged_status = ""
    self.last_logged_candidate = None

    self.params_memory.put("VisionSpeedLimitDebugSession", self.debug_session_id)
    self.params_memory.put_int("VisionSpeedLimitBookmarkCount", self.debug_bookmark_count)
    self.params_memory.put("VisionSpeedLimitLastEvent", "")
    self._write_debug_event("session_start", reason="onroad")
    return True

  def _close_debug_session(self):
    self.debug_session_id = ""
    self.debug_dir = None
    self.debug_capture_dir = None
    self.debug_log_path = None
    self.debug_bookmark_count = 0
    self.debug_session_started_at = 0.0
    self.debug_session_unavailable = False
    self.last_logged_status = ""
    self.last_logged_candidate = None
    self.last_debug_heartbeat_at = 0.0

  def _speed_value_unit(self):
    return "km/h" if self.is_metric else "mph"

  def _speed_value_to_ms(self, speed_value):
    conversion = CV.KPH_TO_MS if self.is_metric else CV.MPH_TO_MS
    return speed_value * conversion

  def _speed_value_from_ms(self, speed_ms):
    conversion = CV.MS_TO_KPH if self.is_metric else CV.MS_TO_MPH
    return int(round(speed_ms * conversion)) if speed_ms > 0.0 else 0

  def _format_speed_value(self, speed_value):
    return f"{speed_value} {self._speed_value_unit()}"

  def _read_next_map_speed_limit(self):
    if self.params_memory is None:
      return {}

    next_map_speed_limit = self.params_memory.get("NextMapSpeedLimit") or {}
    if isinstance(next_map_speed_limit, (bytes, str)):
      try:
        next_map_speed_limit = json.loads(next_map_speed_limit)
      except Exception:
        next_map_speed_limit = {}
    return next_map_speed_limit if isinstance(next_map_speed_limit, dict) else {}

  def _get_map_context(self):
    current_limit_ms = 0.0
    next_limit_ms = 0.0
    next_distance_m = 0.0
    source = "none"

    if self.sm is not None:
      try:
        current_limit_ms = float(self.sm["mapdOut"].speedLimit or 0.0)
        next_limit_ms = float(self.sm["mapdOut"].nextSpeedLimit or 0.0)
        next_distance_m = float(self.sm["mapdOut"].nextSpeedLimitDistance or 0.0)
        if current_limit_ms > 0.0 or next_limit_ms > 0.0:
          source = "mapd"
      except Exception:
        current_limit_ms = 0.0
        next_limit_ms = 0.0
        next_distance_m = 0.0

    if self.params_memory is not None:
      filler_current_limit_ms = float(self.params_memory.get_float("MapSpeedLimit") or 0.0)
      next_map_speed_limit = self._read_next_map_speed_limit()
      filler_next_limit_ms = float(next_map_speed_limit.get("speedlimit") or 0.0)
      filler_next_distance_m = float(next_map_speed_limit.get("distance") or 0.0)
      if filler_current_limit_ms > 0.0 or filler_next_limit_ms > 0.0:
        current_limit_ms = filler_current_limit_ms if filler_current_limit_ms > 0.0 else current_limit_ms
        next_limit_ms = filler_next_limit_ms if filler_next_limit_ms > 0.0 else next_limit_ms
        next_distance_m = filler_next_distance_m if filler_next_distance_m > 0.0 else next_distance_m
        source = "filler"

    # Historical *_mph fields contain the numeric value printed on the sign.
    current_limit_mph = self._speed_value_from_ms(current_limit_ms)
    next_limit_mph = self._speed_value_from_ms(next_limit_ms)
    next_distance_m = round(next_distance_m, 1) if next_distance_m > 0.0 else 0.0

    return {
      "source": source,
      "current_speed_limit_mph": current_limit_mph,
      "next_speed_limit_mph": next_limit_mph,
      "next_speed_limit_distance_m": next_distance_m,
    }

  def _map_fields(self, speed_limit_mph=0):
    map_context = self._get_map_context()
    current_limit_mph = int(map_context["current_speed_limit_mph"])
    next_limit_mph = int(map_context["next_speed_limit_mph"])
    next_distance_m = float(map_context["next_speed_limit_distance_m"])
    map_source = str(map_context["source"])

    expected_speed_limit_mph = current_limit_mph if current_limit_mph > 0 else 0
    map_relation = "no_map"
    review_bucket = "vision_only"

    next_is_relevant = next_limit_mph > 0 and next_limit_mph != current_limit_mph and 0.0 < next_distance_m <= MAP_NEXT_REVIEW_DISTANCE_METERS

    if current_limit_mph > 0:
      if speed_limit_mph > 0 and speed_limit_mph == current_limit_mph:
        map_relation = "agree_current"
        review_bucket = "map_agreement"
      else:
        map_relation = "disagree_current"
        review_bucket = "map_disagreement"

    if next_is_relevant:
      if speed_limit_mph > 0 and speed_limit_mph == next_limit_mph:
        expected_speed_limit_mph = next_limit_mph
        map_relation = "agree_next"
        review_bucket = "map_agreement"
      elif current_limit_mph <= 0:
        expected_speed_limit_mph = next_limit_mph
        map_relation = "disagree_next"
        review_bucket = "map_disagreement"

    if speed_limit_mph <= 0:
      if next_is_relevant:
        expected_speed_limit_mph = next_limit_mph
        map_relation = "map_transition_pending"
        review_bucket = "map_transition_review"
      elif current_limit_mph > 0:
        map_relation = "map_present"
        review_bucket = "map_context_only"

    return {
      "mapSource": map_source,
      "mapCurrentSpeedLimitMph": current_limit_mph,
      "mapNextSpeedLimitMph": next_limit_mph,
      "mapNextSpeedLimitDistanceM": next_distance_m,
      "mapExpectedSpeedLimitMph": expected_speed_limit_mph,
      "mapSpeedLimitUnit": self._speed_value_unit(),
      "mapRelation": map_relation,
      "reviewBucket": review_bucket,
    }

  def _vision_recently_supported(self, speed_limit_mph, now):
    if speed_limit_mph <= 0:
      return False
    if self.last_candidate_speed_limit_mph == speed_limit_mph and now - self.last_candidate_at <= MAP_VISION_MATCH_WINDOW_SECONDS:
      return True
    if self.published_speed_limit_mph == speed_limit_mph and now - self.last_detection_at <= MAP_VISION_MATCH_WINDOW_SECONDS:
      return True
    return any(
      entry.speed_limit_mph == speed_limit_mph and now - entry.created_at <= MAP_VISION_MATCH_WINDOW_SECONDS
      for entry in self.history
    )

  def _write_debug_event(self, event_type, frame_bgr=None, snapshot_prefix=None, **fields):
    if not self.use_runtime or self.params_memory is None:
      return
    if not self.debug_log_path:
      return

    wall_time_ns = time.time_ns()
    event = {
      "event": event_type,
      "wallTimeNs": wall_time_ns,
      "wallTime": datetime.fromtimestamp(wall_time_ns / 1e9, UTC).isoformat(),
      "monoTimeNs": time.monotonic_ns(),
      "roadName": self.last_road_name,
      "stream": self.stream_name,
      "publishedSpeedLimitMph": self.published_speed_limit_mph,
      "speedLimitUnit": self._speed_value_unit(),
      "publishedConfidence": round(self.published_confidence, 4),
      "bookmarkCount": self.debug_bookmark_count,
      "status": self.params_memory.get("VisionSpeedLimitStatus", encoding="utf-8") or "",
    }
    if self.debug_session_started_at > 0.0:
      event["sessionSeconds"] = round(max(time.monotonic() - self.debug_session_started_at, 0.0), 3)
    event.update(self._map_fields(int(fields.get("speedLimitMph") or fields.get("candidateSpeedLimitMph") or 0)))
    event.update(fields)

    if frame_bgr is not None and self.debug_capture_dir is not None and snapshot_prefix:
      snapshot_name = f"{wall_time_ns}_{snapshot_prefix}.jpg"
      snapshot_path = self.debug_capture_dir / snapshot_name
      try:
        cv2.imwrite(str(snapshot_path), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, SNAPSHOT_JPEG_QUALITY])
        event["snapshot"] = f"{DEBUG_CAPTURE_DIRNAME}/{snapshot_name}"
      except Exception:
        pass

    try:
      with self.debug_log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(event, separators=(",", ":")) + "\n")
    except Exception:
      pass

    summary_parts = [event_type.replace("_", " ")]
    if "speedLimitMph" in fields:
      summary_parts.append(self._format_speed_value(fields["speedLimitMph"]))
    elif "candidateSpeedLimitMph" in fields:
      summary_parts.append(self._format_speed_value(fields["candidateSpeedLimitMph"]))
    summary = " ".join(summary_parts)
    self.params_memory.put("VisionSpeedLimitLastEvent", summary[:160])

  def _record_bookmark(self):
    if not self.use_runtime or self.params_memory is None or not self.debug_log_path:
      return

    self.debug_bookmark_count += 1
    self.params_memory.put_int("VisionSpeedLimitBookmarkCount", self.debug_bookmark_count)

    fields = {
      "candidateSpeedLimitMph": self.last_candidate_speed_limit_mph,
      "candidateConfidence": round(self.last_candidate_confidence, 4),
      "publishedSpeedLimitMph": self.published_speed_limit_mph,
      "publishedConfidence": round(self.published_confidence, 4),
    }
    self._write_debug_event(
      "bookmark",
      frame_bgr=self.current_frame_bgr,
      snapshot_prefix=f"bookmark_{self.debug_bookmark_count:03d}",
      **fields,
    )

  def _record_auto_bookmark(self, speed_limit_mph, confidence):
    if not self.use_runtime or self.params_memory is None or not self.debug_log_path:
      return

    self.debug_bookmark_count += 1
    self.params_memory.put_int("VisionSpeedLimitBookmarkCount", self.debug_bookmark_count)

    self._write_debug_event(
      "auto_bookmark",
      frame_bgr=self.current_frame_bgr,
      snapshot_prefix=f"auto_bookmark_{self.debug_bookmark_count:03d}",
      candidateSpeedLimitMph=self.last_candidate_speed_limit_mph,
      candidateConfidence=round(self.last_candidate_confidence, 4),
      publishedSpeedLimitMph=self.published_speed_limit_mph,
      publishedConfidence=round(self.published_confidence, 4),
      speedLimitMph=speed_limit_mph,
      confidence=round(confidence, 4),
      bookmarkCount=self.debug_bookmark_count,
    )

  def _record_training_candidate(self, speed_limit_mph, confidence, source_confidence, source_event):
    if not self.use_runtime or self.params_memory is None or not self.debug_log_path:
      return

    self._write_debug_event(
      "training_candidate",
      frame_bgr=self.current_frame_bgr,
      snapshot_prefix=f"training_candidate_{speed_limit_mph:03d}",
      candidateSpeedLimitMph=self.last_candidate_speed_limit_mph,
      candidateConfidence=round(self.last_candidate_confidence, 4),
      publishedSpeedLimitMph=self.published_speed_limit_mph,
      publishedConfidence=round(self.published_confidence, 4),
      speedLimitMph=speed_limit_mph,
      confidence=round(confidence, 4),
      sourceConfidence=round(source_confidence, 4),
      sourceEvent=source_event,
    )

  def _record_map_transition_miss(self, speed_limit_mph, previous_speed_limit_mph):
    if not self.use_runtime or self.params_memory is None or not self.debug_log_path:
      return

    self._write_debug_event(
      "map_transition_miss",
      frame_bgr=self.current_frame_bgr,
      snapshot_prefix=f"map_transition_miss_{speed_limit_mph:03d}",
      speedLimitMph=speed_limit_mph,
      previousMapSpeedLimitMph=previous_speed_limit_mph,
      candidateSpeedLimitMph=self.last_candidate_speed_limit_mph,
      candidateConfidence=round(self.last_candidate_confidence, 4),
      publishedSpeedLimitMph=self.published_speed_limit_mph,
      publishedConfidence=round(self.published_confidence, 4),
      reason="map_change_without_vision_support",
      reviewBucket="map_transition_miss",
    )

  def _schedule_auto_bookmark(self, speed_limit_mph, confidence, published_at):
    if not self.use_runtime or self.params is None:
      return
    if not self.params.get_bool("VisionSpeedLimitAutoBookmark"):
      return
    if confidence < AUTO_BOOKMARK_MIN_CONFIDENCE:
      return
    if published_at - self.last_auto_bookmark_at < AUTO_BOOKMARK_COOLDOWN_SECONDS and speed_limit_mph == self.last_auto_bookmark_speed_limit_mph:
      return

    self.pending_auto_bookmark = {
      "due_at": published_at + AUTO_BOOKMARK_CONFIRM_DELAY_SECONDS,
      "published_at": published_at,
      "speed_limit_mph": speed_limit_mph,
      "confidence": confidence,
    }

  def _schedule_training_capture(self, speed_limit_mph, confidence, detected_at):
    if not self.use_runtime or self.params is None:
      return
    if not self.params.get_bool("VisionSpeedLimitTrainingCollector", default=True):
      self.pending_training_capture = None
      return
    if confidence < TRAINING_COLLECTOR_MIN_CONFIDENCE:
      return
    if detected_at - self.last_training_capture_at < TRAINING_COLLECTOR_COOLDOWN_SECONDS and speed_limit_mph == self.last_training_capture_speed_limit_mph:
      return

    pending = self.pending_training_capture
    if pending is not None:
      if pending["speed_limit_mph"] == speed_limit_mph:
        pending["confidence"] = max(float(pending["confidence"]), confidence)
        pending["last_seen_at"] = detected_at
        return
      if detected_at < pending["due_at"] and confidence <= float(pending["confidence"]) + 0.08:
        return

    self.pending_training_capture = {
      "due_at": detected_at + TRAINING_COLLECTOR_CONFIRM_DELAY_SECONDS,
      "detected_at": detected_at,
      "last_seen_at": detected_at,
      "speed_limit_mph": speed_limit_mph,
      "confidence": confidence,
    }

  def _emit_preserve_bookmark(self):
    if not self.use_runtime or self.pm is None or self.messaging is None:
      return
    self.ignore_next_user_bookmark = True
    msg = self.messaging.new_message("userBookmark", valid=True)
    self.pm.send("userBookmark", msg)

  def _maybe_commit_auto_bookmark(self, now):
    pending = self.pending_auto_bookmark
    if pending is None or now < pending["due_at"]:
      return
    if self.params is not None and not self.params.get_bool("VisionSpeedLimitAutoBookmark"):
      self.pending_auto_bookmark = None
      return

    self.pending_auto_bookmark = None
    speed_limit_mph = int(pending["speed_limit_mph"])
    confidence = float(pending["confidence"])
    published_at = float(pending["published_at"])

    if self.published_speed_limit_mph != speed_limit_mph:
      return
    if self.published_confidence + 0.02 < confidence:
      return
    if self.current_frame_bgr is None:
      return

    self.last_auto_bookmark_at = now
    self.last_auto_bookmark_speed_limit_mph = speed_limit_mph
    self.last_auto_bookmark_publish_at = published_at
    self._record_auto_bookmark(speed_limit_mph, max(confidence, self.published_confidence))

    if self.params is not None and self.params.get_bool("VisionSpeedLimitAutoPreserveSegment"):
      self._emit_preserve_bookmark()

  def _maybe_commit_training_capture(self, now):
    pending = self.pending_training_capture
    if pending is None or now < pending["due_at"]:
      return
    if self.params is not None and not self.params.get_bool("VisionSpeedLimitTrainingCollector", default=True):
      self.pending_training_capture = None
      return

    self.pending_training_capture = None
    if self.current_frame_bgr is None:
      return

    speed_limit_mph = int(pending["speed_limit_mph"])
    source_confidence = float(pending["confidence"])
    if now - self.last_candidate_at > FOLLOWUP_WINDOW_SECONDS and self.published_speed_limit_mph != speed_limit_mph:
      return

    confidence = source_confidence
    source_event = "candidate"
    if self.last_candidate_speed_limit_mph == speed_limit_mph:
      confidence = max(confidence, self.last_candidate_confidence)
    if self.published_speed_limit_mph == speed_limit_mph:
      confidence = max(confidence, self.published_confidence)
      source_event = "publish"
    if confidence < TRAINING_COLLECTOR_MIN_CONFIDENCE:
      return
    if now - self.last_training_capture_at < TRAINING_COLLECTOR_COOLDOWN_SECONDS and speed_limit_mph == self.last_training_capture_speed_limit_mph:
      return

    self.last_training_capture_at = now
    self.last_training_capture_speed_limit_mph = speed_limit_mph
    self._record_training_candidate(speed_limit_mph, confidence, source_confidence, source_event)

  def _maybe_capture_map_transition_miss(self, now):
    map_context = self._get_map_context()
    current_speed_limit_mph = int(map_context["current_speed_limit_mph"])
    previous_speed_limit_mph = self.last_map_speed_limit_mph

    if current_speed_limit_mph != previous_speed_limit_mph:
      self.last_map_speed_limit_mph = current_speed_limit_mph

    if current_speed_limit_mph <= 0 or current_speed_limit_mph == previous_speed_limit_mph or previous_speed_limit_mph <= 0:
      return
    if self.current_frame_bgr is None:
      return
    capture_in_cooldown = now - self.last_map_transition_miss_at < MAP_TRANSITION_MISS_CAPTURE_COOLDOWN_SECONDS
    if capture_in_cooldown and current_speed_limit_mph == self.last_map_transition_miss_speed_limit_mph:
      return
    if self._vision_recently_supported(current_speed_limit_mph, now):
      return

    self.last_map_transition_miss_at = now
    self.last_map_transition_miss_speed_limit_mph = current_speed_limit_mph
    self._record_map_transition_miss(current_speed_limit_mph, previous_speed_limit_mph)

  def _published_detection_stale(self, now):
    support_at = self.last_published_support_at or self.last_detection_at
    return self.published_speed_limit_mph > 0 and now - support_at > PUBLISHED_HOLD_SECONDS

  def _clear_published_detection_if_stale(self, now, reason):
    if not self._published_detection_stale(now):
      return False
    stale_speed_limit_mph = self.published_speed_limit_mph
    self._write_debug_event("stale_clear", reason=reason, speedLimitMph=stale_speed_limit_mph)
    self._clear_detection()
    return True

  def _device_cpu_busy(self):
    if self.sm is None:
      return False
    return device_cpu_usage_busy(self.sm["deviceState"].cpuUsagePercent)

  def _update_coexistence_mode(self, now):
    if self.params is None or now - self.last_coexistence_param_refresh_at < COEXISTENCE_PARAM_REFRESH_SECONDS:
      return
    self.last_coexistence_param_refresh_at = now

    coexistence_mode = self.params.get_bool("VASMEnabled")
    if coexistence_mode == self.coexistence_mode:
      return

    self.coexistence_mode = coexistence_mode
    self.latest_detector_proposal = None
    self._clear_proposal_track()
    if coexistence_mode:
      self.temporal_tracking_enabled = True
      self.track_detector_interval = COEXISTENCE_TRACK_DETECTOR_INTERVAL
      self.detector_classifier_expansions = COEXISTENCE_DETECTOR_CLASSIFIER_EXPANSIONS
      affinity_cores = SPEED_LIMIT_VISION_COEXISTENCE_AFFINITY_CORES
    else:
      self.temporal_tracking_enabled = TEMPORAL_TRACKING_ENABLED
      self.track_detector_interval = TRACK_DETECTOR_INTERVAL
      self.detector_classifier_expansions = DETECTOR_CLASSIFIER_EXPANSIONS
      affinity_cores = SPEED_LIMIT_VISION_AFFINITY_CORES

    if not PC:
      set_core_affinity(affinity_cores)

  def _inference_interval(self, now):
    in_followup = now < self.followup_until
    interval = FOLLOWUP_INFERENCE_INTERVAL if in_followup else INFERENCE_INTERVAL
    reason = "followup" if in_followup else "steady"
    self.last_cpu_busy = False
    if now - self.last_live_pose_inputs_not_ok_at < LIVE_POSE_RECOVERY_THROTTLE_SECONDS:
      interval = max(interval, LIVE_POSE_RECOVERY_INFERENCE_INTERVAL)
      reason = "live_pose_recovery"
    elif self.coexistence_mode:
      cpu_usage = list(self.sm["deviceState"].cpuUsagePercent) if self.sm is not None and self.sm.valid.get("deviceState", False) else []
      factor = device_cpu_throttle_factor(cpu_usage, name="SpeedLimit")
      if factor > 1.05:
        self.last_cpu_busy = True
        interval *= factor
        reason = f"cpu_{factor:.1f}x"
    elif self._device_cpu_busy():
      self.last_cpu_busy = True
      interval = max(interval, BUSY_INFERENCE_INTERVAL)
      reason = "cpu_busy"
    self.last_inference_interval = interval
    self.last_inference_interval_reason = reason
    return interval

  @staticmethod
  def _read_onnx_square_input_size(model_path, default_size=DEFAULT_DETECTOR_INPUT_SIZE, candidates=DETECTOR_INPUT_SIZE_CANDIDATES):
    try:
      import onnx

      model = onnx.load(str(model_path), load_external_data=False)
      if not model.graph.input:
        return default_size

      shape = model.graph.input[0].type.tensor_type.shape.dim
      if len(shape) < 4:
        return default_size

      height = int(shape[2].dim_value)
      width = int(shape[3].dim_value)
      if height == width and height in candidates:
        return height
    except Exception:
      pass
    return default_size

  def _load_model(self):
    self.net = None
    self.classifier_net = None
    self.reject_classifier_net = None
    self.model_mode = "legacy"
    self.detector_input_size = DEFAULT_DETECTOR_INPUT_SIZE
    self.classifier_input_size = DEFAULT_CLASSIFIER_INPUT_SIZE

    if US_DETECTOR_MODEL_PATH.is_file() and US_CLASSIFIER_MODEL_PATH.is_file():
      try:
        self.detector_input_size = self._read_onnx_square_input_size(US_DETECTOR_MODEL_PATH)
        self.net = cv2.dnn.readNetFromONNX(str(US_DETECTOR_MODEL_PATH))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.classifier_input_size = self._read_onnx_square_input_size(
          US_CLASSIFIER_MODEL_PATH,
          DEFAULT_CLASSIFIER_INPUT_SIZE,
          CLASSIFIER_INPUT_SIZE_CANDIDATES,
        )
        self.classifier_net = cv2.dnn.readNetFromONNX(str(US_CLASSIFIER_MODEL_PATH))
        self.classifier_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.classifier_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        if SEPARATE_REJECT_CLASSIFIER_ENABLED and US_REJECT_CLASSIFIER_MODEL_PATH.is_file():
          try:
            self.reject_classifier_net = cv2.dnn.readNetFromONNX(str(US_REJECT_CLASSIFIER_MODEL_PATH))
            self.reject_classifier_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.reject_classifier_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
          except Exception:
            self.reject_classifier_net = None
        self.model_mode = "detector_classifier"
        self.last_error = ""
        return
      except Exception as exc:
        self.net = None
        self.classifier_net = None
        self.reject_classifier_net = None
        self.model_mode = "legacy"
        self.last_error = f"Failed to load U.S. vision models: {exc}"

    if not LEGACY_MODEL_PATH.is_file():
      if not self.last_error:
        self.last_error = f"Missing vision model: {LEGACY_MODEL_PATH.name}"
      self._publish_status(self.last_error, clear_speed=True)
      return

    try:
      self.detector_input_size = self._read_onnx_square_input_size(LEGACY_MODEL_PATH)
      self.net = cv2.dnn.readNetFromONNX(str(LEGACY_MODEL_PATH))
      self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
      self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
      self.last_error = ""
    except Exception as exc:
      self.last_error = f"Failed to load vision model: {exc}"
      self._publish_status(self.last_error, clear_speed=True)

  def _build_digit_templates(self):
    templates = {str(digit): [] for digit in range(10)}
    fonts = [
      cv2.FONT_HERSHEY_SIMPLEX,
      cv2.FONT_HERSHEY_DUPLEX,
      cv2.FONT_HERSHEY_COMPLEX,
      cv2.FONT_HERSHEY_TRIPLEX,
    ]

    for digit in templates:
      for font in fonts:
        for scale, thickness in ((1.5, 2), (1.7, 3), (1.9, 3), (2.1, 4)):
          canvas = np.full((120, 80), 255, dtype=np.uint8)
          text_size, baseline = cv2.getTextSize(digit, font, scale, thickness)
          x = max((canvas.shape[1] - text_size[0]) // 2, 0)
          y = max((canvas.shape[0] + text_size[1]) // 2 - baseline, text_size[1])
          cv2.putText(canvas, digit, (x, y), font, scale, 0, thickness, cv2.LINE_AA)
          _, binary = cv2.threshold(canvas, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
          normalized = self._normalize_binary_digit(binary)
          if normalized is not None:
            templates[digit].append(normalized)

    return templates

  def _build_speed_value_templates(self):
    templates = {str(speed_limit): [] for speed_limit in VALID_SPEED_LIMITS_MPH}
    fonts = [
      cv2.FONT_HERSHEY_SIMPLEX,
      cv2.FONT_HERSHEY_DUPLEX,
      cv2.FONT_HERSHEY_COMPLEX,
      cv2.FONT_HERSHEY_TRIPLEX,
    ]

    for speed_limit in templates:
      for font in fonts:
        for scale, thickness in ((1.2, 2), (1.4, 2), (1.6, 3), (1.8, 3), (2.0, 4)):
          canvas = np.full((120, 100), 255, dtype=np.uint8)
          text_size, baseline = cv2.getTextSize(speed_limit, font, scale, thickness)
          x = max((canvas.shape[1] - text_size[0]) // 2, 0)
          y = max((canvas.shape[0] + text_size[1]) // 2 - baseline, text_size[1])
          cv2.putText(canvas, speed_limit, (x, y), font, scale, 0, thickness, cv2.LINE_AA)
          _, binary = cv2.threshold(canvas, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
          normalized = self._normalize_binary_digit(binary, size=(72, 96))
          if normalized is not None:
            templates[speed_limit].append(normalized)

    return templates

  def _normalize_binary_digit(self, binary, size=(48, 72), padding=6):
    points = cv2.findNonZero(binary)
    if points is None:
      return None

    x, y, w, h = cv2.boundingRect(points)
    digit = binary[y:y + h, x:x + w]
    target_w, target_h = size
    scale = min((target_w - padding * 2) / max(w, 1), (target_h - padding * 2) / max(h, 1))
    resized_w = max(int(round(w * scale)), 1)
    resized_h = max(int(round(h * scale)), 1)
    resized = cv2.resize(digit, (resized_w, resized_h), interpolation=cv2.INTER_NEAREST)

    canvas = np.zeros((target_h, target_w), dtype=np.uint8)
    offset_x = (target_w - resized_w) // 2
    offset_y = (target_h - resized_h) // 2
    canvas[offset_y:offset_y + resized_h, offset_x:offset_x + resized_w] = resized
    return canvas

  def _connect_camera(self):
    if not self.use_runtime or self.VisionIpcClient is None or self.VisionStreamType is None:
      return False

    try:
      available_streams = self.VisionIpcClient.available_streams("camerad", block=False)
    except Exception:
      available_streams = []

    desired_stream = None
    stream_name = ""
    if self.VisionStreamType.VISION_STREAM_ROAD in available_streams:
      desired_stream = self.VisionStreamType.VISION_STREAM_ROAD
      stream_name = "road camera"
    elif self.VisionStreamType.VISION_STREAM_WIDE_ROAD in available_streams:
      desired_stream = self.VisionStreamType.VISION_STREAM_WIDE_ROAD
      stream_name = "wide camera"

    if desired_stream is None:
      self._disconnect_camera()
      return False

    if self.client is None or self.stream_type != desired_stream:
      self.client = self.VisionIpcClient("camerad", desired_stream, True)
      self.stream_type = desired_stream
      self.stream_name = stream_name

    if not self.client.is_connected():
      self.client.connect(True)

    return self.client.is_connected()

  def _disconnect_camera(self):
    # Dropping the client closes its imported VisionIPC buffer FDs. Keeping the
    # client alive offroad pins the previous camerad allocation between drives.
    self.client = None
    self.stream_type = None
    self.stream_name = ""

  def _receive_frame_bgr(self):
    # Keep VisionBuf and its NumPy view inside this short-lived scope. A local
    # in run() survives loop iterations and can otherwise retain the old
    # VisionIpcClient, including all imported camera buffers, while offroad.
    client = self.client
    if client is None:
      return None

    buffer = client.recv()
    if buffer is None:
      return None

    data = buffer.data
    if not data.any():
      return None

    image = np.frombuffer(data, dtype=np.uint8).reshape((len(data) // client.stride, client.stride))
    return cv2.cvtColor(image[:client.height * 3 // 2, :client.width], cv2.COLOR_YUV2BGR_NV12)

  @staticmethod
  def _letterbox(image, shape=(640, 640), color=(114, 114, 114)):
    image_height, image_width = image.shape[:2]
    ratio = min(shape[0] / image_height, shape[1] / image_width)
    resized_width = int(round(image_width * ratio))
    resized_height = int(round(image_height * ratio))
    pad_width = (shape[1] - resized_width) / 2
    pad_height = (shape[0] - resized_height) / 2

    if (image_width, image_height) != (resized_width, resized_height):
      image = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)

    top = int(round(pad_height - 0.1))
    bottom = int(round(pad_height + 0.1))
    left = int(round(pad_width - 0.1))
    right = int(round(pad_width + 0.1))
    image = cv2.copyMakeBorder(image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return image, ratio, pad_width, pad_height

  @staticmethod
  def _clamp_track_bbox(bbox, width, height):
    x1, y1, x2, y2 = bbox
    result = (
      max(int(round(x1)), 0),
      max(int(round(y1)), 0),
      min(int(round(x2)), width),
      min(int(round(y2)), height),
    )
    return result if result[2] > result[0] and result[3] > result[1] else None

  @staticmethod
  def _track_feature_points(gray, bbox):
    height, width = gray.shape[:2]
    x1, y1, x2, y2 = bbox
    box_width = x2 - x1
    box_height = y2 - y1
    pad_x = max(int(box_width * 0.20), 2)
    pad_y = max(int(box_height * 0.20), 2)
    mask = np.zeros_like(gray)
    mask[max(y1 - pad_y, 0):min(y2 + pad_y, height), max(x1 - pad_x, 0):min(x2 + pad_x, width)] = 255
    return cv2.goodFeaturesToTrack(gray, mask=mask, maxCorners=40, qualityLevel=0.005, minDistance=3, blockSize=5)

  @classmethod
  def _flow_track_bbox(cls, previous_gray, current_gray, bbox, points):
    if points is None or len(points) < TRACK_MIN_FEATURE_COUNT:
      points = cls._track_feature_points(previous_gray, bbox)
    if points is None or len(points) < TRACK_MIN_FEATURE_COUNT:
      return None, None

    next_points, status, errors = cv2.calcOpticalFlowPyrLK(
      previous_gray,
      current_gray,
      points,
      None,
      winSize=(25, 25),
      maxLevel=3,
      criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 20, 0.03),
    )
    if next_points is None or status is None:
      return None, None
    good = status.reshape(-1).astype(bool)
    if errors is not None:
      good &= errors.reshape(-1) < 35.0
    old = points.reshape(-1, 2)[good]
    new = next_points.reshape(-1, 2)[good]
    if len(old) < TRACK_MIN_FEATURE_COUNT:
      return None, None

    transform, inliers = cv2.estimateAffinePartial2D(old, new, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    if transform is None or inliers is None or int(inliers.sum()) < TRACK_MIN_FEATURE_COUNT:
      return None, None
    scale = math.hypot(float(transform[0, 0]), float(transform[0, 1]))
    if not 0.84 <= scale <= 1.24:
      return None, None

    x1, y1, x2, y2 = bbox
    corners = np.float32(((x1, y1), (x2, y1), (x2, y2), (x1, y2))).reshape(-1, 1, 2)
    moved = cv2.transform(corners, transform).reshape(-1, 2)
    tracked = cls._clamp_track_bbox(
      (moved[:, 0].min(), moved[:, 1].min(), moved[:, 0].max(), moved[:, 1].max()),
      current_gray.shape[1],
      current_gray.shape[0],
    )
    if tracked is None:
      return None, None
    inlier_points = new[inliers.reshape(-1).astype(bool)].reshape(-1, 1, 2)
    return tracked, inlier_points

  def _remember_detector_proposal(self, confidence, class_id, bbox, speed_limit_mph=0, preferred=False):
    min_confidence = TRACK_MIN_PROPOSAL_CONFIDENCE if speed_limit_mph else TRACK_UNREADABLE_MIN_PROPOSAL_CONFIDENCE
    if not getattr(self, "temporal_tracking_enabled", TEMPORAL_TRACKING_ENABLED) or class_id == 1 or confidence < min_confidence:
      return
    proposal = DetectorProposal(float(confidence), int(class_id), bbox, int(speed_limit_mph))
    latest_proposal = getattr(self, "latest_detector_proposal", None)
    if preferred or latest_proposal is None or proposal.confidence > latest_proposal.confidence:
      self.latest_detector_proposal = proposal

  def _start_latest_detector_track(self, frame_bgr, now):
    proposal = self.latest_detector_proposal
    self.latest_detector_proposal = None
    if (
      not getattr(self, "temporal_tracking_enabled", TEMPORAL_TRACKING_ENABLED) or
      proposal is None or
      (proposal.speed_limit_mph and not TRACK_CONFIRMED_PROPOSALS_ENABLED)
    ):
      return False
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    points = self._track_feature_points(gray, proposal.bbox)
    if points is None or len(points) < TRACK_MIN_FEATURE_COUNT:
      self.track_failure_count += 1
      return False
    self.proposal_track = ProposalTrack(
      proposal=proposal,
      bbox=proposal.bbox,
      previous_gray=gray,
      points=points,
      started_at=now,
      last_classified_at=now,
    )
    self.track_start_count += 1
    self.max_track_proposal_confidence = max(self.max_track_proposal_confidence, proposal.confidence)
    return True

  def _clear_proposal_track(self, failed=False):
    if failed and self.proposal_track is not None:
      self.track_failure_count += 1
    self.proposal_track = None

  def _track_classification_interval(self, now):
    interval = TRACK_CLASSIFICATION_INTERVAL
    if now - self.last_live_pose_inputs_not_ok_at < LIVE_POSE_RECOVERY_THROTTLE_SECONDS:
      return max(interval, LIVE_POSE_RECOVERY_INFERENCE_INTERVAL)
    if self.coexistence_mode:
      cpu_usage = list(self.sm["deviceState"].cpuUsagePercent) if self.sm is not None and self.sm.valid.get("deviceState", False) else []
      if device_cpu_throttle_factor(cpu_usage, name="SpeedLimit") > 1.05:
        return max(interval, TRACK_BUSY_CLASSIFICATION_INTERVAL)
    elif self._device_cpu_busy():
      return max(interval, TRACK_BUSY_CLASSIFICATION_INTERVAL)
    return interval

  def _track_classification_due(self, now):
    track = self.proposal_track
    if track is None:
      return False
    if now - track.started_at > TRACK_MAX_AGE_SECONDS:
      self._clear_proposal_track()
      return False
    return now - track.last_classified_at >= self._track_classification_interval(now)

  def _detector_interval(self, inference_interval):
    if self.coexistence_mode:
      return max(inference_interval, self.track_detector_interval)
    if self.proposal_track is not None:
      return max(inference_interval, TRACK_DETECTOR_INTERVAL)
    return inference_interval

  def _classify_proposal_track(self, frame_bgr, now):
    track = self.proposal_track
    if track is None:
      return None
    current_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    bbox, points = self._flow_track_bbox(track.previous_gray, current_gray, track.bbox, track.points)
    if bbox is None or points is None:
      self._clear_proposal_track(failed=True)
      return None

    frame_height, frame_width = frame_bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    box_width = x2 - x1
    box_height = y2 - y1
    area_ratio = box_width * box_height / max(frame_width * frame_height, 1)
    if (
      box_width < MODEL_PROPOSAL_MIN_WIDTH or
      box_height < MODEL_PROPOSAL_MIN_HEIGHT or
      area_ratio > TRACK_MAX_AREA_RATIO or
      (x1 + x2) / 2 < frame_width * MODEL_PROPOSAL_MIN_X_RATIO
    ):
      self._clear_proposal_track(failed=True)
      return None

    track.bbox = bbox
    track.previous_gray = current_gray
    track.points = points
    track.last_classified_at = now
    self.track_inference_count += 1

    pad_x = int(box_width * TRACK_CROP_PADDING_RATIO)
    pad_y = int(box_height * TRACK_CROP_PADDING_RATIO)
    crop_x1 = max(x1 - pad_x, 0)
    crop_y1 = max(y1 - pad_y, 0)
    crop_x2 = min(x2 + pad_x, frame_width)
    crop_y2 = min(y2 + pad_y, frame_height)
    sign_crop = frame_bgr[crop_y1:crop_y2, crop_x1:crop_x2]
    if sign_crop.size == 0:
      self._clear_proposal_track(failed=True)
      return None

    read_result = self._classify_speed_limit_from_model(sign_crop)
    if read_result is None:
      track.consecutive_failed_reads += 1
      track.last_speed_limit_mph = 0
      track.consistent_reads = 0
      if track.consecutive_failed_reads >= TRACK_MAX_CONSECUTIVE_FAILED_READS:
        self._clear_proposal_track()
      return None
    speed_limit_mph, read_confidence = read_result
    if track.proposal.speed_limit_mph and speed_limit_mph != track.proposal.speed_limit_mph:
      self._clear_proposal_track()
      return None
    if track.proposal.class_id == 2 and speed_limit_mph not in SCHOOL_ZONE_SPEED_VALUES:
      track.last_speed_limit_mph = 0
      track.consistent_reads = 0
      return None

    track.consecutive_failed_reads = 0

    if speed_limit_mph == track.last_speed_limit_mph:
      track.consistent_reads += 1
    else:
      track.last_speed_limit_mph = speed_limit_mph
      track.consistent_reads = 1

    regulatory_bonus = 0.04 if self._is_regulatory_speed_sign(sign_crop) or track.proposal.class_id == 2 else 0.0
    repeat_bonus = TRACK_REPEAT_CONFIDENCE_BONUS if track.consistent_reads >= 2 else 0.0
    score = min(
      read_confidence * 0.78 +
      track.proposal.confidence * 0.12 +
      regulatory_bonus +
      repeat_bonus,
      0.95,
    )
    return self._publishable_detection(Detection(speed_limit_mph, score))

  def _detect_sign(self, frame_bgr):
    self.latest_detector_proposal = None
    if self.net is None:
      if FULL_FRAME_OCR_FALLBACK_ENABLED:
        return self._publishable_detection(self._detect_sign_from_ocr_candidates(frame_bgr))
      return None

    if self.model_mode == "detector_classifier" and self.classifier_net is not None:
      detector_detection = self._detect_sign_from_detector_classifier(frame_bgr)
      if detector_detection is not None:
        return self._publishable_detection(detector_detection)
      if FULL_FRAME_OCR_FALLBACK_ENABLED:
        return self._publishable_detection(self._detect_sign_from_ocr_candidates(frame_bgr))
      return None

    model_detection = self._detect_sign_from_model_proposals(frame_bgr)
    if model_detection is not None and model_detection.confidence >= MODEL_DETECTION_SHORT_CIRCUIT_CONFIDENCE:
      return self._publishable_detection(model_detection)

    if FULL_FRAME_OCR_FALLBACK_ENABLED:
      ocr_detection = self._detect_sign_from_ocr_candidates(frame_bgr)
      if ocr_detection is not None and (model_detection is None or ocr_detection.confidence > model_detection.confidence):
        return self._publishable_detection(ocr_detection)

    return self._publishable_detection(model_detection)

  def _publishable_detection(self, detection):
    if detection is None:
      return None
    if detection.speed_limit_mph < MIN_PUBLISHABLE_SPEED_LIMIT_MPH:
      return None
    if not getattr(self, "is_metric", False) and detection.speed_limit_mph > MAX_IMPERIAL_PUBLISHABLE_SPEED_LIMIT_MPH:
      return None
    return detection

  def _is_regulatory_speed_sign(self, sign_crop):
    if sign_crop.size == 0:
      return False

    crop_height, crop_width = sign_crop.shape[:2]
    crop_area = crop_height * crop_width
    if crop_area <= 0:
      return False

    hsv = cv2.cvtColor(sign_crop, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]

    white_mask = ((value >= REGULATORY_WHITE_VALUE_MIN) & (saturation <= REGULATORY_WHITE_SAT_MAX)).astype(np.uint8)
    dark_mask = ((value <= REGULATORY_DARK_VALUE_MAX) & (saturation <= REGULATORY_DARK_SAT_MAX)).astype(np.uint8)
    yellow_mask = (
      (hue >= REGULATORY_YELLOW_HUE_MIN) &
      (hue <= REGULATORY_YELLOW_HUE_MAX) &
      (saturation >= REGULATORY_YELLOW_SAT_MIN) &
      (value >= REGULATORY_YELLOW_VALUE_MIN)
    ).astype(np.uint8)
    red_mask = (
      (((hue <= REGULATORY_RED_LOW_HUE_MAX) | (hue >= REGULATORY_RED_HIGH_HUE_MIN))) &
      (saturation >= REGULATORY_RED_SAT_MIN) &
      (value >= REGULATORY_RED_VALUE_MIN)
    ).astype(np.uint8)
    green_mask = (
      (hue >= REGULATORY_GREEN_HUE_MIN) &
      (hue <= REGULATORY_GREEN_HUE_MAX) &
      (saturation >= REGULATORY_COLORED_SAT_MIN) &
      (value >= REGULATORY_COLORED_VALUE_MIN)
    ).astype(np.uint8)
    blue_mask = (
      (hue >= REGULATORY_BLUE_HUE_MIN) &
      (hue <= REGULATORY_BLUE_HUE_MAX) &
      (saturation >= REGULATORY_COLORED_SAT_MIN) &
      (value >= REGULATORY_COLORED_VALUE_MIN)
    ).astype(np.uint8)

    white_ratio = float(white_mask.mean())
    dark_ratio = float(dark_mask.mean())
    yellow_ratio = float(yellow_mask.mean())
    red_ratio = float(red_mask.mean())
    green_ratio = float(green_mask.mean())
    blue_ratio = float(blue_mask.mean())

    if white_ratio < REGULATORY_MIN_WHITE_RATIO or dark_ratio < REGULATORY_MIN_DARK_RATIO:
      return False
    if yellow_ratio > REGULATORY_MAX_YELLOW_RATIO and yellow_ratio > white_ratio * 0.45:
      return False
    if red_ratio > REGULATORY_MAX_RED_RATIO and red_ratio > white_ratio * 0.35:
      return False
    if green_ratio > REGULATORY_MAX_GREEN_RATIO and green_ratio > white_ratio * 0.60:
      return False
    if blue_ratio > REGULATORY_MAX_BLUE_RATIO and blue_ratio > white_ratio * 0.60:
      return False

    white_binary = (white_mask * 255).astype(np.uint8)
    contours, _ = cv2.findContours(white_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_component_area = crop_area * REGULATORY_MIN_WHITE_COMPONENT_RATIO

    for contour in contours:
      area = cv2.contourArea(contour)
      if area < min_component_area:
        continue

      x, y, width, height = cv2.boundingRect(contour)
      if height < crop_height * REGULATORY_MIN_COMPONENT_HEIGHT_RATIO:
        continue
      if width < crop_width * REGULATORY_MIN_COMPONENT_WIDTH_RATIO:
        continue

      aspect_ratio = width / max(height, 1)
      if aspect_ratio < REGULATORY_MIN_ASPECT_RATIO or aspect_ratio > REGULATORY_MAX_ASPECT_RATIO:
        continue

      fill_ratio = area / max(width * height, 1)
      if fill_ratio < REGULATORY_MIN_COMPONENT_FILL:
        continue

      return True

    return False

  @staticmethod
  def _softmax(scores):
    scores = scores.astype(np.float32)
    scores = scores - np.max(scores)
    exp_scores = np.exp(scores)
    denominator = np.sum(exp_scores)
    if denominator <= 0:
      return exp_scores
    return exp_scores / denominator

  @staticmethod
  def _normalize_classifier_output(scores):
    scores = scores.astype(np.float32)
    if scores.size == 0:
      return scores

    # Ultralytics classifier ONNX exports may already emit normalized probabilities.
    if np.all(scores >= 0.0) and np.all(scores <= 1.0):
      total = float(np.sum(scores))
      if 0.99 <= total <= 1.01:
        return scores

    return SpeedLimitVisionDaemon._softmax(scores)

  @staticmethod
  def _square_resize(image, size=128, color=(114, 114, 114)):
    image_height, image_width = image.shape[:2]
    ratio = min(size / max(image_height, 1), size / max(image_width, 1))
    resized_width = max(int(round(image_width * ratio)), 1)
    resized_height = max(int(round(image_height * ratio)), 1)
    image = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)

    canvas = np.full((size, size, image.shape[2]), color, dtype=image.dtype)
    offset_x = (size - resized_width) // 2
    offset_y = (size - resized_height) // 2
    canvas[offset_y:offset_y + resized_height, offset_x:offset_x + resized_width] = image
    return canvas

  @staticmethod
  def _crop_by_ratio(image, left_ratio, top_ratio, right_ratio, bottom_ratio):
    image_height, image_width = image.shape[:2]
    x1 = max(int(image_width * left_ratio), 0)
    y1 = max(int(image_height * top_ratio), 0)
    x2 = min(int(image_width * right_ratio), image_width)
    y2 = min(int(image_height * bottom_ratio), image_height)
    if x2 <= x1 or y2 <= y1:
      return None
    crop = image[y1:y2, x1:x2]
    return crop if crop.size > 0 else None

  def _iter_school_zone_read_crops(self, sign_crop):
    yielded = set()
    for left_ratio, top_ratio, right_ratio, bottom_ratio, weight in SCHOOL_ZONE_READ_VARIANTS:
      crop = self._crop_by_ratio(sign_crop, left_ratio, top_ratio, right_ratio, bottom_ratio)
      if crop is None:
        continue
      key = (crop.shape[1], crop.shape[0], left_ratio, top_ratio, right_ratio, bottom_ratio)
      if key in yielded:
        continue
      yielded.add(key)
      yield crop, weight

  def _collect_model_proposals(self, frame_bgr):
    if self.net is None:
      return []

    frame_height, frame_width = frame_bgr.shape[:2]
    detector_shape = (self.detector_input_size, self.detector_input_size)
    letterboxed, ratio, pad_width, pad_height = self._letterbox(frame_bgr, shape=detector_shape)
    blob = cv2.dnn.blobFromImage(letterboxed, scalefactor=1 / 255.0, size=detector_shape, swapRB=True, crop=False)
    self.net.setInput(blob)

    predictions = np.squeeze(self.net.forward())
    if predictions.ndim != 2:
      return []
    if predictions.shape[0] < predictions.shape[1]:
      predictions = predictions.T

    max_box_area = frame_width * frame_height * MODEL_PROPOSAL_MAX_AREA_RATIO
    candidates = []
    for prediction in predictions:
      class_scores = prediction[4:]
      class_id = int(np.argmax(class_scores))
      confidence = float(class_scores[class_id])
      if class_id not in SPEED_LIMIT_CLASSES:
        continue
      if confidence < MODEL_PROPOSAL_MIN_CONFIDENCE:
        continue

      center_x, center_y, width, height = prediction[:4]
      x1 = max(int((center_x - width / 2 - pad_width) / ratio), 0)
      y1 = max(int((center_y - height / 2 - pad_height) / ratio), 0)
      x2 = min(int((center_x + width / 2 - pad_width) / ratio), frame_width)
      y2 = min(int((center_y + height / 2 - pad_height) / ratio), frame_height)
      if x2 <= x1 or y2 <= y1:
        continue

      box_width = x2 - x1
      box_height = y2 - y1
      if box_width < MODEL_PROPOSAL_MIN_WIDTH or box_height < MODEL_PROPOSAL_MIN_HEIGHT:
        continue
      if box_width * box_height > max_box_area:
        continue
      if (x1 + x2) / 2 < frame_width * MODEL_PROPOSAL_MIN_X_RATIO:
        continue
      if y1 > frame_height * MODEL_PROPOSAL_MAX_Y_RATIO:
        continue

      candidates.append((confidence, class_id, (x1, y1, x2, y2)))

    return sorted(candidates, reverse=True)[:MODEL_PROPOSAL_MAX_COUNT]

  def _collect_detector_classifier_proposals_from_region(self, frame_bgr, origin_x, origin_y, full_frame_width, full_frame_height, min_confidence):
    if self.net is None:
      return []

    region_height, region_width = frame_bgr.shape[:2]
    detector_shape = (self.detector_input_size, self.detector_input_size)
    letterboxed, ratio, pad_width, pad_height = self._letterbox(frame_bgr, shape=detector_shape)
    blob = cv2.dnn.blobFromImage(letterboxed, scalefactor=1 / 255.0, size=detector_shape, swapRB=True, crop=False)
    self.net.setInput(blob)

    forward_started_at = time.monotonic()
    predictions = np.squeeze(self.net.forward())
    self.last_detector_forward_count += 1
    self.last_detector_forward_duration_s += time.monotonic() - forward_started_at
    if predictions.ndim != 2:
      return []
    if predictions.shape[0] < predictions.shape[1]:
      predictions = predictions.T

    candidates = []
    for prediction in predictions:
      class_scores = prediction[4:]
      class_id = int(np.argmax(class_scores))
      confidence = float(class_scores[class_id])
      if class_id not in US_DETECTOR_CLASSES:
        continue
      if confidence < min_confidence:
        continue

      center_x, center_y, width, height = prediction[:4]
      x1 = max(int((center_x - width / 2 - pad_width) / ratio), 0)
      y1 = max(int((center_y - height / 2 - pad_height) / ratio), 0)
      x2 = min(int((center_x + width / 2 - pad_width) / ratio), region_width)
      y2 = min(int((center_y + height / 2 - pad_height) / ratio), region_height)
      if x2 <= x1 or y2 <= y1:
        continue

      x1 += origin_x
      y1 += origin_y
      x2 += origin_x
      y2 += origin_y

      box_width = x2 - x1
      box_height = y2 - y1
      if box_width < MODEL_PROPOSAL_MIN_WIDTH or box_height < MODEL_PROPOSAL_MIN_HEIGHT:
        continue
      if box_width * box_height > full_frame_width * full_frame_height * MODEL_PROPOSAL_MAX_AREA_RATIO:
        continue
      if (x1 + x2) / 2 < full_frame_width * MODEL_PROPOSAL_MIN_X_RATIO:
        continue
      if y1 > full_frame_height * MODEL_PROPOSAL_MAX_Y_RATIO:
        continue

      candidates.append((confidence, class_id, (x1, y1, x2, y2)))

    return candidates

  def _collect_detector_classifier_proposals(self, frame_bgr):
    if self.net is None:
      return []

    frame_height, frame_width = frame_bgr.shape[:2]
    candidates = []
    if DETECTOR_CLASSIFIER_REGION_MODE in ("full", "full_and_right_roi"):
      candidates.extend(self._collect_detector_classifier_proposals_from_region(
        frame_bgr,
        0,
        0,
        frame_width,
        frame_height,
        US_DETECTOR_MIN_CONFIDENCE,
      ))

    # A second pass on a focused right-side ROI materially improves small U.S. sign reads.
    if DETECTOR_CLASSIFIER_REGION_MODE in ("right_roi", "full_and_right_roi") and ROI_WINDOWS:
      left_ratio, top_ratio, right_ratio, bottom_ratio = ROI_WINDOWS[-1]["bounds"]
      left = int(frame_width * left_ratio)
      top = int(frame_height * top_ratio)
      right = int(frame_width * right_ratio)
      bottom = int(frame_height * bottom_ratio)
      roi = frame_bgr[top:bottom, left:right]
      if roi.size > 0:
        candidates.extend(self._collect_detector_classifier_proposals_from_region(
          roi,
          left,
          top,
          frame_width,
          frame_height,
          max(float(ROI_WINDOWS[-1]["min_confidence"]), US_DETECTOR_MIN_CONFIDENCE),
        ))

    return sorted(candidates, reverse=True)[:MODEL_PROPOSAL_MAX_COUNT]

  def _classify_speed_limit_from_model(self, sign_crop):
    if self.classifier_net is None or sign_crop.size == 0:
      return None

    speed_class_count = len(US_CLASSIFIER_SPEED_VALUES)

    if self.reject_classifier_net is not None:
      normalized_mask = self._extract_value_template_mask(sign_crop)
      if normalized_mask is not None:
        reject_input = cv2.cvtColor(normalized_mask, cv2.COLOR_GRAY2BGR)
        reject_crop = self._square_resize(reject_input, size=128)
        reject_blob = cv2.dnn.blobFromImage(reject_crop, scalefactor=1 / 255.0, size=(128, 128), swapRB=True, crop=False)
        self.reject_classifier_net.setInput(reject_blob)
        reject_scores = np.array(self.reject_classifier_net.forward()).reshape(-1)
        if reject_scores.size == speed_class_count + 1:
          reject_probabilities = self._normalize_classifier_output(reject_scores)
          if float(reject_probabilities[speed_class_count]) >= US_REJECT_CLASSIFIER_MIN_CONFIDENCE:
            return None

    input_size = self.classifier_input_size
    padded_crop = self._square_resize(sign_crop, size=input_size)
    blob = cv2.dnn.blobFromImage(padded_crop, scalefactor=1 / 255.0, size=(input_size, input_size), swapRB=True, crop=False)
    self.classifier_net.setInput(blob)

    forward_started_at = time.monotonic()
    scores = np.array(self.classifier_net.forward()).reshape(-1)
    self.last_classifier_forward_count += 1
    self.last_classifier_forward_duration_s += time.monotonic() - forward_started_at
    has_reject_class = scores.size == speed_class_count + 1
    if scores.size != speed_class_count and not has_reject_class:
      return None

    probabilities = self._normalize_classifier_output(scores)
    speed_probabilities = probabilities[:speed_class_count]
    class_index = int(np.argmax(speed_probabilities))
    confidence = float(speed_probabilities[class_index])
    speed_limit = US_CLASSIFIER_SPEED_VALUES[class_index]
    if has_reject_class and float(probabilities[speed_class_count]) >= max(confidence, US_CLASSIFIER_REJECT_MIN_CONFIDENCE):
      return None
    minimum_confidence = (
      EXTENDED_CLASSIFIER_MIN_CONFIDENCE if speed_limit in EXTENDED_CLASSIFIER_SPEED_VALUES else US_CLASSIFIER_MIN_CONFIDENCE
    )
    if confidence < minimum_confidence:
      return None

    return speed_limit, confidence

  def _detect_sign_from_detector_classifier(self, frame_bgr):
    frame_height, frame_width = frame_bgr.shape[:2]
    best_detection = None
    best_score = 0.0

    for proposal_confidence, class_id, (x1, y1, x2, y2) in self._collect_detector_classifier_proposals(frame_bgr):
      if class_id == 1:
        continue

      box_width = x2 - x1
      box_height = y2 - y1
      if box_width <= 0 or box_height <= 0:
        continue
      is_small_box = box_width < DETECTOR_CLASSIFIER_MIN_ACCEPT_WIDTH or box_height < DETECTOR_CLASSIFIER_MIN_ACCEPT_HEIGHT
      # Tiny far-away proposals are the main nighttime false-positive source.
      # Keep a narrow rescue path for right-side high-confidence reads,
      # then let temporal confirmation decide whether they are real.
      if is_small_box and (
        box_width < DETECTOR_CLASSIFIER_RESCUE_MIN_WIDTH or
        box_height < DETECTOR_CLASSIFIER_RESCUE_MIN_HEIGHT or
        x1 < frame_width * DETECTOR_CLASSIFIER_RESCUE_MIN_X_RATIO
      ):
        continue

      proposal_area_ratio = (box_width * box_height) / max(frame_width * frame_height, 1)
      is_tiny_low_conf_box = (
        class_id != 2 and
        proposal_area_ratio < DETECTOR_CLASSIFIER_TINY_LOW_CONF_AREA_RATIO and
        proposal_confidence < DETECTOR_CLASSIFIER_TINY_LOW_CONF_MIN_CONFIDENCE
      )
      self._remember_detector_proposal(proposal_confidence, class_id, (x1, y1, x2, y2))

      if class_id == 2:
        school_scores: dict[int, float] = {}
        competing_scores: dict[int, float] = {}
        school_best_confidences: dict[int, float] = {}
        school_support_counts: dict[int, int] = {}
        for expand_left, expand_top, expand_right, expand_bottom in SCHOOL_ZONE_DIRECT_EXPANSIONS:
          expanded_x1 = max(int(x1 - box_width * expand_left), 0)
          expanded_y1 = max(int(y1 - box_height * expand_top), 0)
          expanded_x2 = min(int(x2 + box_width * expand_right), frame_width)
          expanded_y2 = min(int(y2 + box_height * expand_bottom), frame_height)
          sign_crop = frame_bgr[expanded_y1:expanded_y2, expanded_x1:expanded_x2]
          if sign_crop.size == 0:
            continue

          for school_crop, crop_weight in self._iter_school_zone_read_crops(sign_crop):
            read_result = self._classify_speed_limit_from_model(school_crop)
            if read_result is None and DETECTOR_CLASSIFIER_CROP_OCR_ENABLED:
              read_result = self._read_speed_limit_from_crop(school_crop)
            if read_result is None:
              continue

            speed_limit_mph, read_confidence = read_result
            if speed_limit_mph not in SCHOOL_ZONE_SPEED_VALUES:
              competing_scores[speed_limit_mph] = competing_scores.get(speed_limit_mph, 0.0) + read_confidence * crop_weight
              continue

            school_scores[speed_limit_mph] = school_scores.get(speed_limit_mph, 0.0) + read_confidence * crop_weight
            school_best_confidences[speed_limit_mph] = max(school_best_confidences.get(speed_limit_mph, 0.0), read_confidence)
            school_support_counts[speed_limit_mph] = school_support_counts.get(speed_limit_mph, 0) + 1

        if school_scores:
          speed_limit_mph = max(
            school_scores,
            key=lambda speed: (
              school_scores[speed] + max(school_support_counts[speed] - 1, 0) * SCHOOL_ZONE_SUPPORT_BONUS,
              school_best_confidences[speed],
            ),
          )
          read_confidence = school_best_confidences[speed_limit_mph]
          support_count = school_support_counts[speed_limit_mph]
          if school_scores[speed_limit_mph] > max(competing_scores.values(), default=0.0):
            if (
              (support_count >= SCHOOL_ZONE_MIN_SUPPORT and read_confidence >= SCHOOL_ZONE_MIN_CONFIDENCE) or
              read_confidence >= SCHOOL_ZONE_SINGLE_READ_CONFIDENCE
            ):
              score = min(
                read_confidence * 0.72 +
                proposal_confidence * 0.22 +
                max(support_count - 1, 0) * SCHOOL_ZONE_SUPPORT_BONUS +
                0.04,
                0.95,
              )
              if score >= SCHOOL_ZONE_SHORT_CIRCUIT_CONFIDENCE:
                self._remember_detector_proposal(
                  proposal_confidence, class_id, (x1, y1, x2, y2), speed_limit_mph, preferred=True,
                )
                return Detection(speed_limit_mph, score)

      speed_scores: dict[int, float] = {}
      speed_best_confidences: dict[int, float] = {}
      speed_support_counts: dict[int, int] = {}
      speed_regulatory_support: dict[int, int] = {}
      speed_trusted_model_support: dict[int, int] = {}
      speed_model_only_rescue_support: dict[int, int] = {}
      speed_direct_model_support: dict[int, int] = {}
      speed_strong_model_support: dict[int, int] = {}

      expansions = getattr(self, "detector_classifier_expansions", DETECTOR_CLASSIFIER_EXPANSIONS)
      for expand_left, expand_top, expand_right, expand_bottom, expansion_weight in expansions:
        expanded_x1 = max(int(x1 - box_width * expand_left), 0)
        expanded_y1 = max(int(y1 - box_height * expand_top), 0)
        expanded_x2 = min(int(x2 + box_width * expand_right), frame_width)
        expanded_y2 = min(int(y2 + box_height * expand_bottom), frame_height)
        sign_crop = frame_bgr[expanded_y1:expanded_y2, expanded_x1:expanded_x2]
        if sign_crop.size == 0:
          continue

        raw_is_regulatory = self._is_regulatory_speed_sign(sign_crop)
        is_regulatory = raw_is_regulatory
        if class_id == 2:
          is_regulatory = True

        model_read = self._classify_speed_limit_from_model(sign_crop)
        ocr_read = None
        trusted_model_read = (
          class_id == 0 and
          model_read is not None and
          x1 >= frame_width * DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_X_RATIO and
          box_height <= DETECTOR_CLASSIFIER_TRUSTED_MODEL_MAX_HEIGHT and
          proposal_area_ratio <= DETECTOR_CLASSIFIER_TRUSTED_MODEL_MAX_AREA_RATIO and
          proposal_confidence >= DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_PROPOSAL_CONFIDENCE and
          model_read[1] >= DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_READ_CONFIDENCE
        )
        strong_model_read = (
          class_id == 0 and
          model_read is not None and
          not is_small_box and
          proposal_confidence >= DETECTOR_CLASSIFIER_STRONG_MODEL_MIN_PROPOSAL_CONFIDENCE and
          model_read[1] >= DETECTOR_CLASSIFIER_STRONG_MODEL_MIN_READ_CONFIDENCE
        )
        strong_model_consensus_read = (
          class_id == 0 and
          model_read is not None and
          not is_small_box and
          proposal_confidence >= DETECTOR_CLASSIFIER_STRONG_MODEL_MIN_PROPOSAL_CONFIDENCE and
          model_read[1] >= DETECTOR_CLASSIFIER_STRONG_MODEL_CONSENSUS_MIN_READ_CONFIDENCE
        )
        model_only_consensus_read = (
          not DETECTOR_CLASSIFIER_CROP_OCR_ENABLED and
          class_id == 0 and
          model_read is not None and
          not is_small_box and
          model_read[1] >= DETECTOR_CLASSIFIER_MODEL_ONLY_CONSENSUS_MIN_CONFIDENCE and
          (is_regulatory or proposal_confidence >= DETECTOR_CLASSIFIER_STRONG_MODEL_MIN_PROPOSAL_CONFIDENCE)
        )
        needs_ocr_confirmation = (
          class_id != 2 and
          (not is_regulatory or is_tiny_low_conf_box) and
          not trusted_model_read and
          not strong_model_read
        )
        if DETECTOR_CLASSIFIER_CROP_OCR_ENABLED and (model_read is None or needs_ocr_confirmation):
          ocr_read = self._read_speed_limit_from_crop(sign_crop)
        read_result = model_read or ocr_read
        if read_result is None:
          continue

        if needs_ocr_confirmation:
          if DETECTOR_CLASSIFIER_CROP_OCR_ENABLED:
            if model_read is None or ocr_read is None or model_read[0] != ocr_read[0]:
              continue
            read_result = (model_read[0], min(model_read[1], ocr_read[1]))
          elif not trusted_model_read and not strong_model_read and not model_only_consensus_read:
            continue

        speed_limit_mph, read_confidence = read_result
        score_is_regulatory = is_regulatory or trusted_model_read or strong_model_read
        if (
          class_id == 2 and
          proposal_confidence < SCHOOL_ZONE_FALLBACK_MIN_CONFIDENCE and
          not raw_is_regulatory
        ):
          continue

        score = read_confidence * expansion_weight
        if score_is_regulatory:
          score += DETECTOR_CLASSIFIER_REGULATORY_BONUS
        elif proposal_area_ratio >= DETECTOR_CLASSIFIER_SMALL_BOX_AREA_RATIO:
          score -= DETECTOR_CLASSIFIER_NON_REGULATORY_PENALTY
        if class_id == 2:
          score += SCHOOL_ZONE_SPEED_PRIOR if speed_limit_mph in SCHOOL_ZONE_SPEED_VALUES else -SCHOOL_ZONE_SPEED_PRIOR

        speed_scores[speed_limit_mph] = speed_scores.get(speed_limit_mph, 0.0) + score
        speed_best_confidences[speed_limit_mph] = max(speed_best_confidences.get(speed_limit_mph, 0.0), read_confidence)
        speed_support_counts[speed_limit_mph] = speed_support_counts.get(speed_limit_mph, 0) + 1
        if is_regulatory or class_id == 2 or strong_model_read:
          speed_regulatory_support[speed_limit_mph] = speed_regulatory_support.get(speed_limit_mph, 0) + 1
        if trusted_model_read:
          speed_trusted_model_support[speed_limit_mph] = speed_trusted_model_support.get(speed_limit_mph, 0) + 1
        if strong_model_consensus_read:
          speed_strong_model_support[speed_limit_mph] = speed_strong_model_support.get(speed_limit_mph, 0) + 1
        if needs_ocr_confirmation and model_only_consensus_read:
          speed_model_only_rescue_support[speed_limit_mph] = speed_model_only_rescue_support.get(speed_limit_mph, 0) + 1
        elif model_read is not None:
          speed_direct_model_support[speed_limit_mph] = speed_direct_model_support.get(speed_limit_mph, 0) + 1

      if not speed_scores:
        continue

      speed_limit_mph = max(
        speed_scores,
        key=lambda speed: (
          speed_scores[speed] + max(speed_support_counts[speed] - 1, 0) * DETECTOR_CLASSIFIER_SUPPORT_BONUS,
          speed_best_confidences[speed],
        ),
      )
      if class_id == 2 and speed_limit_mph not in SCHOOL_ZONE_SPEED_VALUES:
        continue
      model_only_rescue_support = speed_model_only_rescue_support.get(speed_limit_mph, 0)
      if (
        speed_direct_model_support.get(speed_limit_mph, 0) < 1 and
        0 < model_only_rescue_support < DETECTOR_CLASSIFIER_MODEL_ONLY_CONSENSUS_MIN_SUPPORT
      ):
        continue
      if (
        speed_regulatory_support.get(speed_limit_mph, 0) < 1 and
        0 < speed_trusted_model_support.get(speed_limit_mph, 0) < DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_SUPPORT
      ):
        continue
      if class_id != 2 and speed_limit_mph in SCHOOL_ZONE_SPEED_VALUES:
        competing_speed_limit_mph = max(
          (speed for speed in speed_scores if speed not in SCHOOL_ZONE_SPEED_VALUES),
          key=lambda speed: (speed_best_confidences[speed], speed_scores[speed]),
          default=None,
        )
        if competing_speed_limit_mph is not None:
          read_confidence = speed_best_confidences[speed_limit_mph]
          competing_confidence = speed_best_confidences[competing_speed_limit_mph]
          if (
            competing_confidence >= NON_SCHOOL_LOW_SPEED_COMPETING_MIN_CONFIDENCE and
            competing_confidence >= read_confidence
          ):
            speed_limit_mph = competing_speed_limit_mph
      read_confidence = speed_best_confidences[speed_limit_mph]
      support_count = speed_support_counts[speed_limit_mph]
      strong_rescue = (
        DETECTOR_CLASSIFIER_STRONG_MODEL_CONSENSUS_ENABLED and
        speed_strong_model_support.get(speed_limit_mph, 0) >= DETECTOR_CLASSIFIER_STRONG_MODEL_CONSENSUS_MIN_SUPPORT
      )
      score = min(
        read_confidence * 0.72 +
        proposal_confidence * 0.24 +
        max(support_count - 1, 0) * DETECTOR_CLASSIFIER_SUPPORT_BONUS,
        0.95,
      )
      selection_score = score
      published_score = score
      if class_id == 2:
        if speed_limit_mph in SCHOOL_ZONE_SPEED_VALUES:
          selection_score = min(score + 0.06, 0.95)
          published_score = selection_score
        else:
          selection_score = max(score - 0.06, 0.0)
          published_score = selection_score
      elif is_small_box:
        if (
          speed_regulatory_support.get(speed_limit_mph, 0) < 1 and
          speed_trusted_model_support.get(speed_limit_mph, 0) < DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_SUPPORT
        ):
          continue
        if support_count < DETECTOR_CLASSIFIER_RESCUE_MIN_SUPPORT:
          continue
        if read_confidence < DETECTOR_CLASSIFIER_RESCUE_MIN_CONFIDENCE:
          continue
        strong_rescue = strong_rescue or (
          speed_trusted_model_support.get(speed_limit_mph, 0) >= DETECTOR_CLASSIFIER_STRONG_RESCUE_MIN_SUPPORT and
          proposal_confidence >= DETECTOR_CLASSIFIER_STRONG_RESCUE_MIN_PROPOSAL_CONFIDENCE and
          read_confidence >= DETECTOR_CLASSIFIER_STRONG_RESCUE_MIN_READ_CONFIDENCE
        )
        rescue_max_score = (
          DETECTOR_CLASSIFIER_STRONG_RESCUE_MAX_SCORE if strong_rescue else DETECTOR_CLASSIFIER_RESCUE_MAX_SCORE
        )
        published_score = min(score, rescue_max_score)
        if speed_trusted_model_support.get(speed_limit_mph, 0) < DETECTOR_CLASSIFIER_TRUSTED_MODEL_MIN_SUPPORT:
          selection_score = published_score
      if selection_score > best_score:
        best_score = selection_score
        best_detection = Detection(speed_limit_mph, published_score, strong_rescue)
        self._remember_detector_proposal(
          proposal_confidence, class_id, (x1, y1, x2, y2), speed_limit_mph, preferred=True,
        )
      if best_detection is not None and best_detection.confidence >= MODEL_DETECTION_SHORT_CIRCUIT_CONFIDENCE:
        return best_detection

    return best_detection

  def _detect_sign_from_model_proposals(self, frame_bgr):
    frame_height, frame_width = frame_bgr.shape[:2]
    best_detection = None
    best_score = 0.0

    for proposal_confidence, class_id, (x1, y1, x2, y2) in self._collect_model_proposals(frame_bgr):
      proposal_crop = frame_bgr[y1:y2, x1:x2]
      if proposal_crop.size == 0 or not self._is_regulatory_speed_sign(proposal_crop):
        continue

      box_width = x2 - x1
      box_height = y2 - y1

      for expand_left, expand_top, expand_right, expand_bottom in MODEL_PROPOSAL_EXPANSIONS:
        expanded_x1 = max(int(x1 - box_width * expand_left), 0)
        expanded_y1 = max(int(y1 - box_height * expand_top), 0)
        expanded_x2 = min(int(x2 + box_width * expand_right), frame_width)
        expanded_y2 = min(int(y2 + box_height * expand_bottom), frame_height)
        if expanded_x2 <= expanded_x1 or expanded_y2 <= expanded_y1:
          continue

        for trim_bottom_ratio in MODEL_PROPOSAL_TRIM_BOTTOM_RATIOS:
          trimmed_y2 = expanded_y1 + int((expanded_y2 - expanded_y1) * trim_bottom_ratio)
          if trimmed_y2 <= expanded_y1:
            continue

          sign_crop = frame_bgr[expanded_y1:trimmed_y2, expanded_x1:expanded_x2]
          if sign_crop.size == 0:
            continue

          read_result = self._read_speed_limit_from_crop(sign_crop)
          if read_result is None:
            continue

          speed_limit_mph, read_confidence = read_result
          score = read_confidence + min(proposal_confidence * 8.0, 0.08)
          if class_id in SPEED_LIMIT_CLASSES and SPEED_LIMIT_CLASSES[class_id] == speed_limit_mph:
            score += 0.03

          if score > best_score:
            best_score = score
            best_detection = Detection(speed_limit_mph, min(score, 0.85))
          if best_score >= MODEL_DETECTION_SHORT_CIRCUIT_CONFIDENCE:
              return best_detection

    return best_detection

  def _detect_sign_from_ocr_candidates(self, frame_bgr):
    frame_height, frame_width = frame_bgr.shape[:2]
    best_detection = None
    best_score = 0.0

    for left_ratio, top_ratio, right_ratio, bottom_ratio in OCR_SEARCH_WINDOWS:
      left = int(frame_width * left_ratio)
      top = int(frame_height * top_ratio)
      right = int(frame_width * right_ratio)
      bottom = int(frame_height * bottom_ratio)
      roi = frame_bgr[top:bottom, left:right]
      if roi.size == 0:
        continue

      gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
      gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
      upscaled = cv2.resize(gray, None, fx=OCR_SEARCH_UPSCALE, fy=OCR_SEARCH_UPSCALE, interpolation=cv2.INTER_CUBIC)
      roi_area = upscaled.shape[0] * upscaled.shape[1]
      if roi_area <= 0:
        continue

      for threshold in OCR_SEARCH_THRESHOLDS:
        _, binary = cv2.threshold(upscaled, threshold, 255, cv2.THRESH_BINARY)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), dtype=np.uint8))
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
          x, y, w, h = cv2.boundingRect(contour)
          area = w * h
          aspect = w / max(h, 1)
          if area < roi_area * 0.002 or area > roi_area * 0.08:
            continue
          if aspect < 0.45 or aspect > 1.4:
            continue
          if y > upscaled.shape[0] * 0.82:
            continue

          for inset_left_ratio, inset_right_ratio, pad_ratio in OCR_SEARCH_CROP_VARIANTS:
            inset_x = x + int(w * inset_left_ratio)
            inset_width = max(int(w * (1 - inset_left_ratio - inset_right_ratio)), 20)
            pad_x = int(inset_width * pad_ratio)
            pad_y = int(h * pad_ratio)

            x1 = max(inset_x - pad_x, 0)
            y1 = max(y - pad_y, 0)
            x2 = min(inset_x + inset_width + pad_x, upscaled.shape[1])
            y2 = min(y + h + pad_y, upscaled.shape[0])
            candidate_crop = upscaled[y1:y2, x1:x2]
            if candidate_crop.size == 0:
              continue
            candidate_crop_bgr = cv2.cvtColor(candidate_crop, cv2.COLOR_GRAY2BGR)
            if not self._is_regulatory_speed_sign(candidate_crop_bgr):
              continue

            ocr_result = self._read_speed_limit_from_crop(candidate_crop_bgr)
            if ocr_result is None:
              continue

            speed_limit_mph, confidence = ocr_result
            if confidence < OCR_FALLBACK_MIN_CONFIDENCE:
              continue

            score = confidence + min(area / roi_area, 0.03)
            if score > best_score:
              best_score = score
              best_detection = Detection(speed_limit_mph, confidence)

    return best_detection

  def _read_speed_limit_from_crop(self, sign_crop):
    gray = cv2.cvtColor(sign_crop, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    roi = gray[int(height * 0.22):int(height * 0.92), int(width * 0.1):int(width * 0.9)]
    if roi.size == 0:
      return None

    blurred = cv2.GaussianBlur(roi, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((2, 2), dtype=np.uint8))

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    digit_boxes = []
    min_area = roi.shape[0] * roi.shape[1] * 0.01
    min_height = roi.shape[0] * 0.35
    min_width = roi.shape[1] * 0.05

    for contour in contours:
      x, y, w, h = cv2.boundingRect(contour)
      area = cv2.contourArea(contour)
      if area < min_area or h < min_height or w < min_width:
        continue
      if w / max(h, 1) > 1.1:
        continue
      if y + h < roi.shape[0] * 0.35:
        continue
      digit_boxes.append((x, y, w, h))

    digit_boxes.sort(key=lambda box: box[0])
    if len(digit_boxes) < 2:
      return self._read_speed_limit_from_value_template(sign_crop)
    if len(digit_boxes) > 3:
      digit_boxes = sorted(digit_boxes, key=lambda box: box[3], reverse=True)[:3]
      digit_boxes.sort(key=lambda box: box[0])

    digits = []
    confidences = []
    for x, y, w, h in digit_boxes:
      digit_mask = binary[y:y + h, x:x + w]
      normalized = self._normalize_binary_digit(digit_mask)
      if normalized is None:
        return self._read_speed_limit_from_value_template(sign_crop)
      digit, confidence = self._classify_digit(normalized)
      if digit is None or confidence < OCR_MIN_CONFIDENCE:
        return self._read_speed_limit_from_value_template(sign_crop)
      digits.append(digit)
      confidences.append(confidence)

    if not 2 <= len(digits) <= 3:
      return self._read_speed_limit_from_value_template(sign_crop)

    speed_limit_mph = int("".join(digits))
    if speed_limit_mph not in VALID_SPEED_LIMITS_MPH:
      return self._read_speed_limit_from_value_template(sign_crop)

    return speed_limit_mph, float(sum(confidences) / len(confidences))

  def _read_speed_limit_from_value_template(self, sign_crop):
    normalized = self._extract_value_template_mask(sign_crop)
    if normalized is None:
      return None

    candidate = normalized > 0
    best_match = None
    for speed_limit, templates in self.speed_value_templates.items():
      for template in templates:
        template_mask = template > 0
        union = np.logical_or(candidate, template_mask).sum()
        if union == 0:
          continue
        intersection = np.logical_and(candidate, template_mask).sum()
        iou = intersection / union
        if best_match is None or iou > best_match[1]:
          best_match = (int(speed_limit), iou)

    if best_match is None or best_match[1] < VALUE_TEMPLATE_MIN_CONFIDENCE:
      return None
    return best_match

  def _extract_value_template_mask(self, sign_crop):
    gray = cv2.cvtColor(sign_crop, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    best_mask = None
    best_fill = 0.0

    for top_ratio, bottom_ratio, left_ratio, right_ratio in VALUE_TEMPLATE_ROIS:
      roi = gray[int(height * top_ratio):int(height * bottom_ratio), int(width * left_ratio):int(width * right_ratio)]
      if roi.size == 0:
        continue

      clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(roi)
      _, binary = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
      binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((2, 2), dtype=np.uint8))

      num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
      mask = np.zeros_like(binary)
      for label_idx in range(1, num_labels):
        x, y, w, h, area = stats[label_idx]
        if area < roi.shape[0] * roi.shape[1] * 0.01:
          continue
        if y < binary.shape[0] * 0.08:
          continue
        if h < binary.shape[0] * 0.18:
          continue
        if w > binary.shape[1] * 0.75:
          continue
        mask[labels == label_idx] = 255

      normalized = self._normalize_binary_digit(mask, size=(72, 96))
      if normalized is None:
        continue

      fill_ratio = float(np.count_nonzero(normalized)) / normalized.size
      if fill_ratio <= 0.02:
        continue
      if fill_ratio > best_fill:
        best_fill = fill_ratio
        best_mask = normalized

    return best_mask

  def _classify_digit(self, normalized_digit):
    best_digit = None
    best_iou = 0.0

    candidate = normalized_digit > 0
    for digit, templates in self.digit_templates.items():
      for template in templates:
        template_mask = template > 0
        union = np.logical_or(candidate, template_mask).sum()
        if union == 0:
          continue
        intersection = np.logical_and(candidate, template_mask).sum()
        iou = intersection / union
        if iou > best_iou:
          best_iou = iou
          best_digit = digit

    return best_digit, best_iou

  def _prune_history(self, now):
    while self.history and now - self.history[0].created_at > HISTORY_SECONDS:
      self.history.popleft()

  def _confirm_detection(self):
    if not self.history:
      return None

    counts = Counter(entry.speed_limit_mph for entry in self.history)
    candidate_speed_limit, candidate_count = counts.most_common(1)[0]
    matching_entries = [entry for entry in self.history if entry.speed_limit_mph == candidate_speed_limit]
    matching_confidences = sorted((entry.confidence for entry in matching_entries), reverse=True)
    best_confidence = max(entry.confidence for entry in matching_entries)
    has_strong_consensus = any(entry.strong_consensus for entry in matching_entries)
    current_speed_limit = self.published_speed_limit_mph
    current_count = counts.get(current_speed_limit, 0) if current_speed_limit > 0 else 0

    if current_speed_limit > 0 and candidate_speed_limit != current_speed_limit:
      required_count = CHANGE_CONSISTENT_DETECTIONS
      allow_single_frame_confirmation = (
        has_strong_consensus or best_confidence >= CHANGE_SINGLE_READ_MIN_CONFIDENCE
      )
      if current_speed_limit >= 30 and candidate_speed_limit < 30:
        required_count = LOW_SPEED_CHANGE_CONSISTENT_DETECTIONS
        allow_single_frame_confirmation = (
          best_confidence >= CHANGE_SINGLE_READ_MIN_CONFIDENCE or
          (has_strong_consensus and LOW_SPEED_CHANGE_ALLOW_STRONG_CONSENSUS)
        )
        if best_confidence < LOW_SPEED_CHANGE_MIN_CONFIDENCE:
          return None
      if candidate_count < required_count and not allow_single_frame_confirmation:
        return None
      if (
        not allow_single_frame_confirmation and
        matching_confidences[required_count - 1] < CHANGE_REPEAT_MIN_CONFIDENCE
      ):
        return None
      if candidate_count <= current_count:
        return None
      return candidate_speed_limit, best_confidence

    if has_strong_consensus or best_confidence >= STRONG_DETECTION_CONFIDENCE or candidate_count >= CONSISTENT_DETECTIONS:
      return candidate_speed_limit, best_confidence
    return None

  def _clear_detection(self):
    self.history.clear()
    self.followup_until = 0.0
    self._clear_proposal_track()
    self.pending_auto_bookmark = None
    self.pending_training_capture = None
    self.previous_published_speed_limit_mph = self.published_speed_limit_mph
    self.published_speed_limit_mph = 0
    self.published_confidence = 0.0
    self.last_publish_change_at = 0.0
    self.last_published_support_at = 0.0
    self.last_candidate_speed_limit_mph = 0
    self.last_candidate_confidence = 0.0
    self.last_candidate_at = 0.0
    self.last_logged_candidate = None
    if self.params_memory is not None:
      self.params_memory.remove("VisionSpeedLimit")
      self.params_memory.remove("VisionSpeedLimitConfidence")
      self.params_memory.remove("VisionSpeedLimitSupportCount")
      self.params_memory.remove("VisionSpeedLimitSupportSpeed")

  def _enter_parked(self, now):
    self.current_frame_bgr = None
    self.latest_detector_proposal = None
    self._clear_proposal_track()
    self.pending_auto_bookmark = None
    self.pending_training_capture = None
    self.followup_until = 0.0
    self._publish_status("Idle - parked", clear_speed=False)
    self._publish_runtime_telemetry(now, "parked", force=True)

  def _publish_detection_support(self, speed_limit_mph, support_count):
    if self.params_memory is None:
      return
    self.params_memory.put_int("VisionSpeedLimitSupportCount", support_count)
    self.params_memory.put_float("VisionSpeedLimitSupportSpeed", self._speed_value_to_ms(speed_limit_mph))

  def _publish_status(self, status, clear_speed=False):
    if clear_speed:
      self._clear_detection()
    if self.params_memory is None:
      return
    self.params_memory.put("VisionSpeedLimitStatus", status)
    if self.stream_name:
      self.params_memory.put("VisionSpeedLimitStream", self.stream_name)
    else:
      self.params_memory.remove("VisionSpeedLimitStream")
    if status != self.last_logged_status:
      self.last_logged_status = status
      self._write_debug_event("status", statusText=status)

  def _publish_runtime_telemetry(self, now, phase, force=False, **fields):
    if not self.use_runtime:
      return
    if not force and now - self.last_runtime_telemetry_at < RUNTIME_TELEMETRY_INTERVAL_SECONDS:
      return

    self.last_runtime_telemetry_at = now
    try:
      DEBUG_BASE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
      if self.params_memory is not None:
        try:
          self.params_memory.put("VisionSpeedLimitLastEvent", f"runtime telemetry mkdir error: {type(exc).__name__}"[:160])
        except Exception:
          pass
      return

    try:
      live_pose_inputs_ok = True
      started = False
      cpu_usage = []
      if self.sm is not None:
        try:
          started = bool(self.sm["deviceState"].started)
          cpu_usage = [round(float(value), 1) for value in self.sm["deviceState"].cpuUsagePercent]
        except Exception:
          started = False
          cpu_usage = []
        try:
          live_pose_inputs_ok = bool(self.sm["livePose"].inputsOK)
        except Exception:
          live_pose_inputs_ok = True

      camera_connected = False
      try:
        camera_connected = bool(self.client is not None and self.client.is_connected())
      except Exception:
        camera_connected = False

      telemetry = {
        "phase": phase,
        "wallTimeNs": time.time_ns(),
        "monoTimeNs": time.monotonic_ns(),
        "started": started,
        "startedPrev": self.started_prev,
        "modelMode": self.model_mode,
        "detectorInputSize": self.detector_input_size,
        "classifierInputSize": self.classifier_input_size,
        "detectorRegionMode": DETECTOR_CLASSIFIER_REGION_MODE,
        "separateRejectClassifierEnabled": SEPARATE_REJECT_CLASSIFIER_ENABLED,
        "stream": self.stream_name,
        "cameraConnected": camera_connected,
        "debugSession": self.debug_session_id,
        "loopCount": self.loop_count,
        "inferenceCount": self.inference_count,
        "detectorInferenceCount": self.detector_inference_count,
        "intervalSkipCount": self.interval_skip_count,
        "busySkipCount": self.busy_skip_count,
        "cameraUnavailableCount": self.camera_unavailable_count,
        "emptyFrameCount": self.empty_frame_count,
        "detectionCount": self.detection_count,
        "trackInferenceCount": self.track_inference_count,
        "trackFailureCount": self.track_failure_count,
        "trackStartCount": self.track_start_count,
        "maxTrackProposalConfidence": round(self.max_track_proposal_confidence, 4),
        "proposalTrackActive": self.proposal_track is not None,
        "lastInferenceAgeS": round(max(now - self.last_inference_at, 0.0), 3),
        "lastInferenceIntervalS": round(float(self.last_inference_interval), 3),
        "lastInferenceIntervalReason": self.last_inference_interval_reason,
        "cpuBusy": self.last_cpu_busy,
        "lastFrameProcessDurationS": round(self.last_frame_process_duration_s, 3),
        "lastDetectorForwardCount": self.last_detector_forward_count,
        "lastDetectorForwardDurationS": round(self.last_detector_forward_duration_s, 3),
        "lastClassifierForwardCount": self.last_classifier_forward_count,
        "lastClassifierForwardDurationS": round(self.last_classifier_forward_duration_s, 3),
        "cpuUsagePercent": cpu_usage,
        "livePoseInputsOK": live_pose_inputs_ok,
        "publishedSpeedLimitMph": self.published_speed_limit_mph,
        "speedLimitUnit": self._speed_value_unit(),
        "publishedConfidence": round(self.published_confidence, 4),
        "lastCandidateSpeedLimitMph": self.last_candidate_speed_limit_mph,
        "lastCandidateConfidence": round(self.last_candidate_confidence, 4),
        "lastError": self.last_error,
      }
      telemetry.update(fields)
      encoded = json.dumps(telemetry, separators=(",", ":")) + "\n"
    except Exception as exc:
      telemetry = {
        "phase": phase,
        "wallTimeNs": time.time_ns(),
        "monoTimeNs": time.monotonic_ns(),
        "loopCount": self.loop_count,
        "telemetryError": f"{type(exc).__name__}: {exc}",
      }
      encoded = json.dumps(telemetry, separators=(",", ":")) + "\n"
      if self.params_memory is not None:
        try:
          self.params_memory.put("VisionSpeedLimitLastEvent", f"runtime telemetry error: {type(exc).__name__}"[:160])
        except Exception:
          pass

    try:
      tmp_path = DEBUG_RUNTIME_STATUS_PATH.with_name(f"{DEBUG_RUNTIME_STATUS_PATH.name}.tmp")
      tmp_path.write_text(encoded, encoding="utf-8")
      tmp_path.replace(DEBUG_RUNTIME_STATUS_PATH)
    except Exception as exc:
      if self.params_memory is not None:
        try:
          self.params_memory.put("VisionSpeedLimitLastEvent", f"runtime telemetry write error: {type(exc).__name__}"[:160])
        except Exception:
          pass
      return

    if self.debug_log_path and now - self.last_debug_heartbeat_at >= DEBUG_HEARTBEAT_INTERVAL_SECONDS:
      self.last_debug_heartbeat_at = now
      self._write_debug_event("heartbeat", runtime=telemetry)

  def _publish_detection(self, speed_limit_mph, confidence, status_prefix):
    if speed_limit_mph != self.published_speed_limit_mph or abs(confidence - self.published_confidence) >= 0.05:
      published_changed = speed_limit_mph != self.published_speed_limit_mph
      if speed_limit_mph != self.published_speed_limit_mph:
        self.previous_published_speed_limit_mph = self.published_speed_limit_mph
        self.last_publish_change_at = time.monotonic()
        self.last_published_support_at = self.last_publish_change_at
      self.published_speed_limit_mph = speed_limit_mph
      self.published_confidence = confidence
      self._write_debug_event(
        "publish",
        frame_bgr=self.current_frame_bgr,
        snapshot_prefix=f"publish_{speed_limit_mph:03d}",
        speedLimitMph=speed_limit_mph,
        confidence=round(confidence, 4),
      )
      if self.params_memory is not None:
        self.params_memory.put_float("VisionSpeedLimit", self._speed_value_to_ms(speed_limit_mph))
        self.params_memory.put_float("VisionSpeedLimitConfidence", confidence)
      if published_changed:
        self.history.clear()
        self.history.append(HistoryEntry(speed_limit_mph, confidence, time.monotonic()))
        self._schedule_auto_bookmark(speed_limit_mph, confidence, self.last_publish_change_at)

    status = f"{status_prefix} {self._format_speed_value(speed_limit_mph)} ({confidence * 100:.0f}%)"
    self._publish_status(status, clear_speed=False)

  def _should_hold_current_publish(self, speed_limit_mph, confidence, now):
    if self.published_speed_limit_mph <= 0:
      return False
    if speed_limit_mph == self.published_speed_limit_mph:
      return False
    if speed_limit_mph != self.previous_published_speed_limit_mph:
      return False
    if now - self.last_publish_change_at >= PUBLISHED_CHANGE_COOLDOWN_SECONDS:
      return False
    return confidence < PUBLISHED_REVERT_CONFIDENCE

  def _update_detection(self, detection):
    now = time.monotonic()
    self.last_detection_at = now
    self.followup_until = max(self.followup_until, now + FOLLOWUP_WINDOW_SECONDS)
    self.last_candidate_speed_limit_mph = detection.speed_limit_mph
    self.last_candidate_confidence = detection.confidence
    self.last_candidate_at = now
    if detection.speed_limit_mph == self.published_speed_limit_mph:
      self.last_published_support_at = now
    self._schedule_training_capture(detection.speed_limit_mph, detection.confidence, now)

    candidate_signature = (detection.speed_limit_mph, round(detection.confidence, 2))
    if candidate_signature != self.last_logged_candidate:
      self.last_logged_candidate = candidate_signature
      self._write_debug_event(
        "candidate",
        candidateSpeedLimitMph=detection.speed_limit_mph,
        candidateConfidence=round(detection.confidence, 4),
        candidateStrongConsensus=detection.strong_consensus,
      )

    self.history.append(HistoryEntry(detection.speed_limit_mph, detection.confidence, now, detection.strong_consensus))
    self._prune_history(now)

    confirmed = self._confirm_detection()
    if confirmed is not None:
      speed_limit_mph, confidence = confirmed
      support_count = sum(entry.speed_limit_mph == speed_limit_mph for entry in self.history)
      if self._should_hold_current_publish(speed_limit_mph, confidence, now):
        self._publish_status(
          f"Candidate {self._format_speed_value(speed_limit_mph)} ({confidence * 100:.0f}%)",
          clear_speed=False,
        )
      else:
        self._publish_detection(speed_limit_mph, confidence, "Holding")
        self._publish_detection_support(speed_limit_mph, support_count)
    else:
      self._publish_status(
        f"Candidate {self._format_speed_value(detection.speed_limit_mph)} ({detection.confidence * 100:.0f}%)",
        clear_speed=False,
      )

  def run(self):
    if not self.use_runtime or self.sm is None:
      raise RuntimeError("SpeedLimitVisionDaemon runtime loop requires use_runtime=True")

    ratekeeper = self.Ratekeeper(RUNTIME_LOOP_HZ, None)

    while True:
      now = time.monotonic()
      self.loop_count += 1
      self.sm.update(0)

      if self.sm.updated["userBookmark"]:
        if self.ignore_next_user_bookmark:
          self.ignore_next_user_bookmark = False
        else:
          self._record_bookmark()

      if self.net is None:
        self._publish_status(self.last_error or "Vision model unavailable", clear_speed=True)
        self._publish_runtime_telemetry(now, "model_unavailable")
        ratekeeper.keep_time()
        continue

      if not self.sm["deviceState"].started:
        if self.started_prev:
          self._write_debug_event("session_end", reason="offroad")
          self._close_debug_session()
          self._disconnect_camera()
        self.last_road_name = ""
        self.started_prev = False
        self.parked_prev = False
        self.current_frame_bgr = None
        self.pending_auto_bookmark = None
        self._publish_status("Idle - offroad", clear_speed=True)
        self._publish_runtime_telemetry(now, "offroad")
        ratekeeper.keep_time()
        continue

      if self.sm.updated["livePose"] and not self.sm["livePose"].inputsOK:
        self.last_live_pose_inputs_not_ok_at = now

      if not self.started_prev:
        self.started_prev = True
        self._start_debug_session()
        self._publish_runtime_telemetry(now, "onroad_start", force=True)
      elif not self.debug_session_id and self._start_debug_session():
        self._write_debug_event("session_recovered", reason="missing_debug_session_while_onroad")
        self._publish_runtime_telemetry(now, "session_recovered", force=True)

      parked = self.sm["starpilotCarState"].isParked if self.sm.valid.get("starpilotCarState", False) else False
      if parked:
        if not self.parked_prev:
          self._enter_parked(now)
        else:
          self._publish_runtime_telemetry(now, "parked")
        self.parked_prev = True
        ratekeeper.keep_time()
        continue
      if self.parked_prev:
        self.parked_prev = False
        self.last_inference_at = -float("inf")
        self._publish_runtime_telemetry(now, "parked_exit", force=True)

      road_name = self.sm["mapdOut"].roadName
      if self.last_road_name and road_name and road_name != self.last_road_name:
        self._write_debug_event("road_change", previousRoadName=self.last_road_name, roadName=road_name)
        self._clear_detection()
      self.last_road_name = road_name or self.last_road_name

      if not self._connect_camera():
        self.camera_unavailable_count += 1
        stale_cleared = self._clear_published_detection_if_stale(now, "camera_unavailable")
        status = "Waiting for camera stream"
        if self.published_speed_limit_mph > 0 and not stale_cleared:
          status = f"{status}, holding {self._format_speed_value(self.published_speed_limit_mph)}"
        self._publish_status(status, clear_speed=False)
        self._publish_runtime_telemetry(now, "camera_unavailable")
        ratekeeper.keep_time()
        continue

      self._update_coexistence_mode(now)
      inference_interval = self._inference_interval(now)
      track_due = self._track_classification_due(now)
      detector_interval = self._detector_interval(inference_interval)
      detector_due = now - self.last_inference_at >= detector_interval
      if not track_due and not detector_due:
        self.interval_skip_count += 1
        if self.last_cpu_busy:
          self.busy_skip_count += 1
        stale_cleared = self._clear_published_detection_if_stale(now, "inference_interval")
        if self.published_speed_limit_mph > 0 and not stale_cleared:
          self._publish_detection(self.published_speed_limit_mph, self.published_confidence, "Holding")
        else:
          self._publish_status(f"Scanning {self.stream_name}", clear_speed=False)
        self._publish_runtime_telemetry(now, "interval_skip")
        ratekeeper.keep_time()
        continue

      frame_bgr = self._receive_frame_bgr()
      self.inference_count += 1
      inference_started_at = time.monotonic()
      self.last_frame_process_duration_s = 0.0
      self.last_detector_forward_count = 0
      self.last_detector_forward_duration_s = 0.0
      self.last_classifier_forward_count = 0
      self.last_classifier_forward_duration_s = 0.0
      if frame_bgr is None:
        self.empty_frame_count += 1
        stale_cleared = self._clear_published_detection_if_stale(now, "empty_frame")
        if self.published_speed_limit_mph > 0 and not stale_cleared:
          self._publish_status(
            f"Waiting for {self.stream_name}, holding {self._format_speed_value(self.published_speed_limit_mph)}",
            clear_speed=False,
          )
        else:
          self._publish_status(f"Waiting for {self.stream_name}", clear_speed=False)
        self._publish_runtime_telemetry(now, "empty_frame")
        ratekeeper.keep_time()
        continue

      self.current_frame_bgr = frame_bgr

      if detector_due:
        self.detector_inference_count += 1
        self.last_inference_at = now
        detection = self._detect_sign(frame_bgr)
        self._start_latest_detector_track(frame_bgr, now)
      else:
        detection = self._classify_proposal_track(frame_bgr, now)
      self.last_frame_process_duration_s = time.monotonic() - inference_started_at
      if detection is not None:
        self.detection_count += 1
        self._update_detection(detection)
        self._publish_runtime_telemetry(now, "detection")
      elif self._clear_published_detection_if_stale(now, "no_detection"):
        self._publish_status(f"Scanning {self.stream_name}", clear_speed=False)
        self._publish_runtime_telemetry(now, "stale_clear")
      elif self.published_speed_limit_mph > 0:
        self._publish_detection(self.published_speed_limit_mph, self.published_confidence, "Holding")
        self._publish_runtime_telemetry(now, "holding")
      else:
        self._publish_status(f"Scanning {self.stream_name}", clear_speed=False)
        self._publish_runtime_telemetry(now, "scanning")

      self._maybe_commit_auto_bookmark(now)
      self._maybe_commit_training_capture(now)
      self._maybe_capture_map_transition_miss(now)

      ratekeeper.keep_time()


def main():
  # Keep this best-effort helper off the critical control/model/camera cores.
  if not PC:
    set_core_affinity(SPEED_LIMIT_VISION_AFFINITY_CORES)

  # OpenCV may otherwise fan out across many worker threads and starve more
  # important daemons during detection bursts.
  cv2.setNumThreads(1)

  daemon = SpeedLimitVisionDaemon()
  daemon.run()


if __name__ == "__main__":
  main()
