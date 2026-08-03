from collections import deque
import gc
import weakref

import numpy as np
import pytest

import starpilot.system.speed_limit_vision as slv
from starpilot.system.speed_limit_vision import DetectorProposal, HistoryEntry, ProposalTrack, SpeedLimitVisionDaemon


class MemoryParams:
  def __init__(self):
    self.values = {}

  def put_float(self, key, value):
    self.values[key] = value

  def put_int(self, key, value):
    self.values[key] = value

  def put(self, key, value):
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)


class StaticClassifierNet:
  def __init__(self, probabilities):
    self.probabilities = np.array(probabilities, dtype=np.float32)

  def setInput(self, _blob):
    pass

  def forward(self):
    return self.probabilities


class ToggleParams:
  def __init__(self, enabled):
    self.enabled = enabled

  def get_bool(self, key):
    assert key == "VASMEnabled"
    return self.enabled


def daemon_with_history(current_speed, entries):
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.published_speed_limit_mph = current_speed
  daemon.history = deque(HistoryEntry(speed, confidence, float(index)) for index, (speed, confidence) in enumerate(entries))
  return daemon


def publishing_daemon(is_metric):
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.is_metric = is_metric
  daemon.published_speed_limit_mph = 0
  daemon.published_confidence = 0.0
  daemon.previous_published_speed_limit_mph = 0
  daemon.last_publish_change_at = 0.0
  daemon.last_published_support_at = 0.0
  daemon.current_frame_bgr = None
  daemon.params_memory = MemoryParams()
  daemon.history = deque()
  daemon._write_debug_event = lambda *_args, **_kwargs: None
  daemon._schedule_auto_bookmark = lambda *_args, **_kwargs: None
  daemon._publish_status = lambda status, **_kwargs: setattr(daemon, "published_status", status)
  return daemon


def test_debug_storage_failure_does_not_crash_detection(monkeypatch):
  class ReadOnlyPath:
    def __truediv__(self, _part):
      return self

    def exists(self):
      return False

    def mkdir(self, **_kwargs):
      raise OSError(30, "Read-only file system")

  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.use_runtime = True
  daemon.params_memory = MemoryParams()
  daemon.debug_session_id = ""
  daemon.debug_session_unavailable = False
  monkeypatch.setattr(slv, "DEBUG_BASE_DIR", ReadOnlyPath())

  assert not daemon._start_debug_session()
  assert daemon.debug_session_unavailable
  assert daemon.debug_session_id == ""
  assert daemon.params_memory.values["VisionSpeedLimitLastEvent"] == "debug storage unavailable: OSError"

  assert not daemon._start_debug_session()


def test_disconnect_camera_releases_client_state():
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.client = object()
  daemon.stream_type = object()
  daemon.stream_name = "road camera"

  daemon._disconnect_camera()

  assert daemon.client is None
  assert daemon.stream_type is None
  assert daemon.stream_name == ""


def test_vasm_coexistence_mode_is_conditional(monkeypatch):
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.params = ToggleParams(False)
  daemon.coexistence_mode = False
  daemon.last_coexistence_param_refresh_at = -float("inf")
  daemon.temporal_tracking_enabled = slv.TEMPORAL_TRACKING_ENABLED
  daemon.track_detector_interval = slv.TRACK_DETECTOR_INTERVAL
  daemon.detector_classifier_expansions = slv.DETECTOR_CLASSIFIER_EXPANSIONS
  daemon.latest_detector_proposal = None
  daemon.proposal_track = None
  monkeypatch.setattr(slv, "PC", True)

  daemon._update_coexistence_mode(0.0)
  assert not daemon.coexistence_mode
  assert daemon.detector_classifier_expansions == slv.DETECTOR_CLASSIFIER_EXPANSIONS
  assert daemon._detector_interval(slv.INFERENCE_INTERVAL) == slv.INFERENCE_INTERVAL

  daemon.params.enabled = True
  daemon._update_coexistence_mode(slv.COEXISTENCE_PARAM_REFRESH_SECONDS + 0.1)
  assert daemon.coexistence_mode
  assert daemon.temporal_tracking_enabled
  assert daemon.detector_classifier_expansions == slv.COEXISTENCE_DETECTOR_CLASSIFIER_EXPANSIONS
  assert daemon._detector_interval(slv.INFERENCE_INTERVAL) == slv.COEXISTENCE_TRACK_DETECTOR_INTERVAL

  daemon.params.enabled = False
  daemon._update_coexistence_mode(2 * slv.COEXISTENCE_PARAM_REFRESH_SECONDS + 0.2)
  assert not daemon.coexistence_mode
  assert daemon.temporal_tracking_enabled == slv.TEMPORAL_TRACKING_ENABLED
  assert daemon.detector_classifier_expansions == slv.DETECTOR_CLASSIFIER_EXPANSIONS


def test_enter_parked_preserves_published_limit_and_clears_transient_work():
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.current_frame_bgr = np.ones((2, 2, 3), dtype=np.uint8)
  daemon.latest_detector_proposal = object()
  daemon.proposal_track = object()
  daemon.pending_auto_bookmark = object()
  daemon.pending_training_capture = object()
  daemon.followup_until = 100.0
  daemon.published_speed_limit_mph = 55
  published = []
  telemetry = []
  daemon._publish_status = lambda status, clear_speed=False: published.append((status, clear_speed))
  daemon._publish_runtime_telemetry = lambda now, phase, force=False: telemetry.append((now, phase, force))

  daemon._enter_parked(10.0)

  assert daemon.current_frame_bgr is None
  assert daemon.latest_detector_proposal is None
  assert daemon.proposal_track is None
  assert daemon.pending_auto_bookmark is None
  assert daemon.pending_training_capture is None
  assert daemon.followup_until == 0.0
  assert daemon.published_speed_limit_mph == 55
  assert published == [("Idle - parked", False)]
  assert telemetry == [(10.0, "parked", True)]


def test_receive_frame_does_not_retain_vision_buffer(monkeypatch):
  buffer_refs = []

  class FakeBuffer:
    def __init__(self):
      self.data = np.ones(6, dtype=np.uint8)

  class FakeClient:
    width = 2
    height = 2
    stride = 2

    def recv(self):
      buffer = FakeBuffer()
      buffer_refs.append(weakref.ref(buffer))
      return buffer

  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.client = FakeClient()
  monkeypatch.setattr(slv.cv2, "cvtColor", lambda image, _conversion: np.array(image, copy=True))

  frame = daemon._receive_frame_bgr()
  gc.collect()

  assert frame.shape == (3, 2)
  assert buffer_refs[0]() is None


def test_published_sign_value_uses_configured_units():
  imperial_daemon = publishing_daemon(False)
  metric_daemon = publishing_daemon(True)

  imperial_daemon._publish_detection(50, 0.95, "Vision")
  metric_daemon._publish_detection(50, 0.95, "Vision")

  assert imperial_daemon.params_memory.values["VisionSpeedLimit"] == pytest.approx(22.352)
  assert imperial_daemon.published_status == "Vision 50 mph (95%)"
  assert metric_daemon.params_memory.values["VisionSpeedLimit"] == pytest.approx(50 / 3.6)
  assert metric_daemon.published_status == "Vision 50 km/h (95%)"


@pytest.mark.parametrize(("confidence", "expected"), ((0.89, None), (0.91, (80, 0.91))))
def test_extended_classifier_values_require_high_confidence(monkeypatch, confidence, expected):
  speed_values = (10, 100, 15, 20, 25, 30, 35, 40, 45, 5, 50, 55, 60, 65, 70, 75, 80, 90)
  probabilities = np.zeros(len(speed_values) + 1, dtype=np.float32)
  probabilities[speed_values.index(80)] = confidence
  probabilities[-1] = 1.0 - confidence
  method_globals = slv.SpeedLimitVisionDaemon._classify_speed_limit_from_model.__globals__
  monkeypatch.setitem(method_globals, "US_CLASSIFIER_SPEED_VALUES", speed_values)
  monkeypatch.setitem(method_globals, "EXTENDED_CLASSIFIER_SPEED_VALUES", frozenset((5, 10, 80, 90, 100)))
  monkeypatch.setitem(method_globals, "EXTENDED_CLASSIFIER_MIN_CONFIDENCE", 0.90)

  daemon = slv.SpeedLimitVisionDaemon.__new__(slv.SpeedLimitVisionDaemon)
  daemon.classifier_net = StaticClassifierNet(probabilities)
  daemon.reject_classifier_net = None
  daemon.classifier_input_size = 128
  daemon.last_classifier_forward_count = 0
  daemon.last_classifier_forward_duration_s = 0.0

  result = daemon._classify_speed_limit_from_model(np.ones((64, 48, 3), dtype=np.uint8))

  if expected is None:
    assert result is None
  else:
    assert result == pytest.approx(expected)


def test_five_mph_detection_is_publishable():
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.is_metric = False

  detection = daemon._publishable_detection(slv.Detection(5, 0.95))

  assert detection is not None
  assert detection.speed_limit_mph == 5


@pytest.mark.parametrize(("speed_limit", "expected"), ((80, 80), (90, None), (100, None)))
def test_imperial_detection_blocks_speeds_above_80(speed_limit, expected):
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.is_metric = False

  detection = daemon._publishable_detection(slv.Detection(speed_limit, 0.99))

  assert (detection.speed_limit_mph if detection else None) == expected


def test_metric_detection_allows_100():
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.is_metric = True

  detection = daemon._publishable_detection(slv.Detection(100, 0.99))

  assert detection is not None
  assert detection.speed_limit_mph == 100


def test_detection_support_counts_independent_frames():
  daemon = publishing_daemon(False)
  daemon.followup_until = 0.0
  daemon.last_detection_at = 0.0
  daemon.last_candidate_speed_limit_mph = 0
  daemon.last_candidate_confidence = 0.0
  daemon.last_candidate_at = 0.0
  daemon.last_logged_candidate = None
  daemon._schedule_training_capture = lambda *_args, **_kwargs: None

  for expected_count in range(1, 4):
    daemon._update_detection(slv.Detection(15, 0.99))
    assert daemon.params_memory.values["VisionSpeedLimitSupportCount"] == expected_count
    assert daemon.params_memory.values["VisionSpeedLimitSupportSpeed"] == pytest.approx(15 * slv.CV.MPH_TO_MS)


def test_speed_change_requires_two_matching_reads_below_single_read_threshold():
  daemon = daemon_with_history(40, [(55, 0.82)])
  assert daemon._confirm_detection() is None

  daemon.history.append(HistoryEntry(55, 0.76, 1.0))
  assert daemon._confirm_detection() == pytest.approx((55, 0.82))


def test_speed_change_rejects_weak_confirming_read():
  daemon = daemon_with_history(40, [(35, 0.78), (35, 0.48)])
  assert daemon._confirm_detection() is None


def test_speed_change_accepts_single_high_confidence_read():
  daemon = daemon_with_history(40, [(55, 0.84)])
  assert daemon._confirm_detection() == pytest.approx((55, 0.84))


def test_speed_change_accepts_single_strong_consensus_read():
  daemon = daemon_with_history(70, [])
  daemon.history.append(HistoryEntry(60, 0.74, 1.0, strong_consensus=True))
  assert daemon._confirm_detection() == pytest.approx((60, 0.74))


def test_low_speed_change_requires_two_reads_below_low_speed_threshold():
  daemon = daemon_with_history(40, [(25, 0.89)])
  assert daemon._confirm_detection() is None

  daemon.history.append(HistoryEntry(25, 0.96, 1.0))
  assert daemon._confirm_detection() == pytest.approx((25, 0.96))


def test_low_speed_change_accepts_single_high_confidence_read():
  daemon = daemon_with_history(40, [(25, 0.91)])
  assert daemon._confirm_detection() == pytest.approx((25, 0.91))


def test_low_speed_change_accepts_single_strong_consensus_read():
  daemon = daemon_with_history(40, [])
  daemon.history.append(HistoryEntry(25, 0.95, 1.0, strong_consensus=True))
  assert daemon._confirm_detection() == pytest.approx((25, 0.95))


def test_low_speed_change_rejects_low_confidence_sequence():
  daemon = daemon_with_history(40, [(25, 0.82), (25, 0.88), (25, 0.89)])
  assert daemon._confirm_detection() is None


def textured_track_frame(offset_x=0, offset_y=0):
  frame = np.zeros((120, 180, 3), dtype=np.uint8)
  x1, y1, x2, y2 = 90 + offset_x, 30 + offset_y, 130 + offset_x, 90 + offset_y
  frame[y1:y2, x1:x2] = 220
  cv2 = pytest.importorskip("cv2")
  cv2.rectangle(frame, (x1 + 3, y1 + 3), (x2 - 3, y2 - 3), (20, 20, 20), 2)
  cv2.putText(frame, "55", (x1 + 5, y1 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 10, 10), 2)
  return frame, (x1, y1, x2, y2)


def test_flow_track_bbox_follows_translation():
  cv2 = pytest.importorskip("cv2")
  first, bbox = textured_track_frame()
  second, expected_bbox = textured_track_frame(4, 3)
  first_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
  second_gray = cv2.cvtColor(second, cv2.COLOR_BGR2GRAY)
  points = SpeedLimitVisionDaemon._track_feature_points(first_gray, bbox)

  tracked_bbox, tracked_points = SpeedLimitVisionDaemon._flow_track_bbox(first_gray, second_gray, bbox, points)

  assert tracked_bbox == pytest.approx(expected_bbox, abs=1)
  assert tracked_points is not None and len(tracked_points) >= 4


def test_temporal_track_boosts_two_consistent_model_reads():
  cv2 = pytest.importorskip("cv2")
  frame, bbox = textured_track_frame()
  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  points = SpeedLimitVisionDaemon._track_feature_points(gray, bbox)
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon.proposal_track = ProposalTrack(DetectorProposal(0.20, 0, bbox), bbox, gray, points, 0.0, 0.0)
  daemon.track_inference_count = 0
  daemon.track_failure_count = 0
  daemon.last_classifier_forward_count = 0
  daemon.last_classifier_forward_duration_s = 0.0
  daemon._classify_speed_limit_from_model = lambda _crop: (55, 0.90)
  daemon._is_regulatory_speed_sign = lambda _crop: True

  first = daemon._classify_proposal_track(frame, 0.2)
  second = daemon._classify_proposal_track(frame, 0.4)

  assert first.speed_limit_mph == 55
  assert second.speed_limit_mph == 55
  assert first.confidence < slv.CHANGE_SINGLE_READ_MIN_CONFIDENCE
  assert second.confidence >= slv.CHANGE_SINGLE_READ_MIN_CONFIDENCE
  assert daemon.track_inference_count == 2


def detector_classifier_daemon(*, regulatory: bool, model_read, bbox=(700, 100, 780, 220), proposal_confidence=0.80):
  daemon = SpeedLimitVisionDaemon.__new__(SpeedLimitVisionDaemon)
  daemon._collect_detector_classifier_proposals = lambda _frame: [(proposal_confidence, 0, bbox)]
  daemon._is_regulatory_speed_sign = lambda _crop: regulatory
  daemon._classify_speed_limit_from_model = model_read if callable(model_read) else lambda _crop: model_read
  daemon._read_speed_limit_from_crop = lambda _crop: pytest.fail("detector/classifier runtime must not call OCR")
  return daemon


@pytest.fixture
def model_only_runtime(monkeypatch):
  monkeypatch.setattr(slv, "DETECTOR_CLASSIFIER_CROP_OCR_ENABLED", False)


def test_detector_classifier_runtime_reads_regulatory_sign_without_ocr(model_only_runtime):
  daemon = detector_classifier_daemon(regulatory=True, model_read=(55, 0.99))
  detection = daemon._detect_sign_from_detector_classifier(np.zeros((480, 960, 3), dtype=np.uint8))

  assert detection is not None
  assert detection.speed_limit_mph == 55


def test_detector_classifier_marks_two_strong_model_crops_as_consensus(model_only_runtime):
  reads = iter(((20, 0.96), (20, 0.97), None))
  daemon = detector_classifier_daemon(regulatory=True, model_read=lambda _crop: next(reads), proposal_confidence=0.80)
  detection = daemon._detect_sign_from_detector_classifier(np.zeros((480, 960, 3), dtype=np.uint8))

  assert detection is not None
  assert detection.speed_limit_mph == 20
  assert detection.strong_consensus


def test_detector_classifier_runtime_rejects_single_untrusted_non_regulatory_model_read_without_ocr(model_only_runtime):
  reads = iter(((55, 0.99), None, None, None))
  daemon = detector_classifier_daemon(regulatory=False, model_read=lambda _crop: next(reads))
  detection = daemon._detect_sign_from_detector_classifier(np.zeros((480, 960, 3), dtype=np.uint8))

  assert detection is None


def test_detector_classifier_runtime_accepts_repeated_model_only_consensus_without_ocr(model_only_runtime):
  daemon = detector_classifier_daemon(regulatory=False, model_read=(60, 0.99))
  detection = daemon._detect_sign_from_detector_classifier(np.zeros((480, 960, 3), dtype=np.uint8))

  assert detection is not None
  assert detection.speed_limit_mph == 60


def test_detector_classifier_runtime_rejects_tiny_model_only_consensus_without_ocr(model_only_runtime):
  daemon = detector_classifier_daemon(
    regulatory=True,
    model_read=(40, 0.99),
    bbox=(700, 100, 720, 125),
    proposal_confidence=0.14,
  )
  detection = daemon._detect_sign_from_detector_classifier(np.zeros((480, 960, 3), dtype=np.uint8))

  assert detection is None
