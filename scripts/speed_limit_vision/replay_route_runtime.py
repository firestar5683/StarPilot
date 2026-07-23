#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import bz2
import csv

from dataclasses import dataclass
from pathlib import Path

import cv2
import zstandard as zstd
from cereal import log

from openpilot.starpilot.common.starpilot_utilities import device_cpu_throttle_factor
import starpilot.system.speed_limit_vision as slv

if __package__ in (None, ""):
  import sys
  sys.path.insert(0, str(Path(__file__).resolve().parent))
  from common import source_video_fps  # type: ignore  # noqa: TID251
else:
  from .common import source_video_fps


@dataclass(frozen=True)
class RouteSummary:
  route: str
  segments: int
  qlog_context: bool
  sampled_frames: int
  inference_frames: int
  candidate_events: int
  publish_events: int
  stale_clear_events: int
  road_change_events: int


@dataclass
class QlogRuntimeContext:
  cpu_times: list[float]
  cpu_busy: list[bool]
  live_pose_times: list[float]
  live_pose_inputs_ok: list[bool]
  road_times: list[float]
  road_names: list[str]
  started_times: list[float]
  started: list[bool]

  def _last_index(self, times: list[float], now: float) -> int:
    return bisect.bisect_right(times, now) - 1

  def device_cpu_busy_at(self, now: float) -> bool:
    index = self._last_index(self.cpu_times, now)
    return index >= 0 and self.cpu_busy[index]

  def live_pose_inputs_ok_at(self, now: float) -> bool:
    index = self._last_index(self.live_pose_times, now)
    return index < 0 or self.live_pose_inputs_ok[index]

  def road_name_at(self, now: float) -> str:
    index = self._last_index(self.road_times, now)
    return self.road_names[index] if index >= 0 else ""

  def started_at(self, now: float) -> bool:
    index = self._last_index(self.started_times, now)
    return index < 0 or self.started[index]


class RouteReplayDaemon(slv.SpeedLimitVisionDaemon):
  def __init__(
    self,
    runtime_context: QlogRuntimeContext | None,
    measured_inference_seconds: float,
    measured_base_inference_seconds: float | None = None,
    measured_classifier_forward_seconds: float = 0.0,
    measured_tracking_base_seconds: float = 0.012,
  ):
    super().__init__(use_runtime=False)
    self.runtime_context = runtime_context
    self.measured_inference_seconds = max(float(measured_inference_seconds), 0.0)
    self.measured_base_inference_seconds = (
      max(float(measured_base_inference_seconds), 0.0) if measured_base_inference_seconds is not None else None
    )
    self.measured_classifier_forward_seconds = max(float(measured_classifier_forward_seconds), 0.0)
    self.measured_tracking_base_seconds = max(float(measured_tracking_base_seconds), 0.0)
    self.next_available_at = -float("inf")
    self.now = 0.0
    self.sampled_frames = 0
    self.inference_frames = 0
    self.events: list[dict[str, str]] = []

  def _write_debug_event(self, event_type, frame_bgr=None, snapshot_prefix=None, **fields):
    if event_type not in ("candidate", "publish", "stale_clear", "road_change"):
      return
    record = {
      "time_s": f"{self.now:.3f}",
      "event": event_type,
    }
    for key, value in fields.items():
      record[key] = str(value)
    self.events.append(record)

  def _publish_status(self, status, clear_speed=False):
    if clear_speed:
      self._clear_detection()

  def _device_cpu_busy(self):
    if self.runtime_context is None:
      return False
    return self.runtime_context.device_cpu_busy_at(self.now)

  def prepare_tick(self, now: float) -> bool:
    self.now = now
    slv.time.monotonic = lambda now=now: now

    if self.runtime_context is None:
      return True

    if not self.runtime_context.started_at(now):
      if self.published_speed_limit_mph > 0:
        self._clear_detection()
      self.last_road_name = ""
      return False

    if not self.runtime_context.live_pose_inputs_ok_at(now):
      self.last_live_pose_inputs_not_ok_at = now

    road_name = self.runtime_context.road_name_at(now)
    if self.last_road_name and road_name and road_name != self.last_road_name:
      self._write_debug_event("road_change", previousRoadName=self.last_road_name, roadName=road_name)
      self._clear_detection()
    self.last_road_name = road_name or self.last_road_name
    return True

  def process_frame(self, now: float, frame_bgr):
    self.sampled_frames += 1
    if not self.prepare_tick(now):
      return
    if now < self.next_available_at:
      return
    self.current_frame_bgr = frame_bgr

    track_due = self._track_classification_due(now)
    inference_interval = self._inference_interval(now)
    detector_interval = max(inference_interval, slv.TRACK_DETECTOR_INTERVAL) if self.proposal_track is not None else inference_interval
    detector_due = now >= self.last_inference_at + detector_interval
    if not track_due and not detector_due:
      if self.published_speed_limit_mph > 0 and self._published_detection_stale(now):
        self._write_debug_event("stale_clear", reason="inference_interval")
        self._clear_detection()
      return

    self.inference_frames += 1
    self.last_detector_forward_count = 0
    self.last_detector_forward_duration_s = 0.0
    self.last_classifier_forward_count = 0
    self.last_classifier_forward_duration_s = 0.0
    if detector_due:
      self.detector_inference_count += 1
      self.last_inference_at = now
      detection = self._detect_sign(frame_bgr)
      self._start_latest_detector_track(frame_bgr, now)
      inference_seconds = self.measured_inference_seconds
      if self.measured_base_inference_seconds is not None:
        inference_seconds = (
          self.measured_base_inference_seconds +
          self.last_classifier_forward_count * self.measured_classifier_forward_seconds
        )
    else:
      detection = self._classify_proposal_track(frame_bgr, now)
      inference_seconds = self.measured_tracking_base_seconds + self.last_classifier_forward_count * self.measured_classifier_forward_seconds
    self.next_available_at = now + inference_seconds
    if detection is not None:
      self._update_detection(detection)
    elif self.published_speed_limit_mph > 0 and self._published_detection_stale(now):
      self._write_debug_event("stale_clear", reason="no_detection")
      self._clear_detection()

  def next_processing_due(self, now: float) -> float:
    if self.proposal_track is not None:
      if now - self.proposal_track.started_at > slv.TRACK_MAX_AGE_SECONDS:
        self._clear_proposal_track()
      else:
        track_due = self.proposal_track.last_classified_at + self._track_classification_interval(now)
        detector_due = self.last_inference_at + max(self._inference_interval(now), slv.TRACK_DETECTOR_INTERVAL)
        return max(self.next_available_at, min(track_due, detector_due))
    return max(self.next_available_at, self.last_inference_at + self._inference_interval(now))


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Replay downloaded route camera segments through the runtime speed-limit vision cadence.")
  parser.add_argument("routes", nargs="+", help="Route log ids like 00000004--0da2db69c7 or dongle/logid.")
  parser.add_argument("--clip-root", type=Path, default=Path("/Volumes/T5/starpilot_speed_limit/realdata"), help="Downloaded segment root.")
  parser.add_argument("--models-dir", type=Path, default=Path("starpilot/assets/vision_models"), help="Directory containing runtime ONNX models.")
  parser.add_argument("--output-csv", type=Path, help="Optional CSV of candidate/publish/stale_clear events.")
  parser.add_argument("--start", type=float, default=0.0, help="Skip route time before this second.")
  parser.add_argument("--end", type=float, help="Stop once route time exceeds this second.")
  parser.add_argument("--progress", action="store_true", help="Print a one-line progress update after each segment.")
  parser.add_argument("--fast-seek", action="store_true", help="Use VideoCapture seeks when skipping frames. Faster, but less faithful for HEVC.")
  parser.add_argument("--qlog-context", action="store_true", help="Replay with logged deviceState/livePose/mapdOut context for closer runtime cadence.")
  parser.add_argument("--measured-inference-seconds", type=float, default=0.0, help="Simulate wall-clock time spent inside one runtime inference on the comma.")
  parser.add_argument(
    "--measured-base-inference-seconds",
    type=float,
    help="Simulate a measured no-proposal inference cost; enables the dynamic comma cost model.",
  )
  parser.add_argument(
    "--measured-classifier-forward-seconds",
    type=float,
    default=0.0,
    help="Additional measured comma cost per classifier forward when the dynamic cost model is enabled.",
  )
  parser.add_argument(
    "--measured-tracking-base-seconds",
    type=float,
    default=0.012,
    help="Measured optical-flow and crop-preparation cost for one tracked frame.",
  )
  parser.add_argument("--disable-temporal-tracking", action="store_true", help="Disable proposal tracking for an A/B replay.")
  parser.add_argument("--track-unreadable-min-proposal-confidence", type=float, help="Override confidence required to track an unreadable proposal.")
  parser.add_argument("--track-detector-interval", type=float, help="Override detector cadence while tracking a proposal.")
  parser.add_argument(
    "--detector-region-mode",
    choices=("full", "right_roi", "full_and_right_roi"),
    help="Override the detector/classifier region mode used by speed_limit_vision.py.",
  )
  parser.add_argument("--right-roi-bounds", help="Override the right ROI as left,top,right,bottom ratios, for example 0.45,0,1,0.82.")
  parser.add_argument("--right-roi-min-confidence", type=float, help="Override the right ROI detector minimum confidence.")
  parser.add_argument("--classifier-min-confidence", type=float, help="Override the value classifier confidence threshold.")
  parser.add_argument("--full-frame-ocr", action="store_true", help="Enable the expensive full-frame OCR fallback during replay.")
  crop_ocr_group = parser.add_mutually_exclusive_group()
  crop_ocr_group.add_argument("--crop-ocr", action="store_true", dest="crop_ocr", default=None, help="Enable crop OCR confirmation during replay.")
  crop_ocr_group.add_argument("--no-crop-ocr", action="store_false", dest="crop_ocr", help="Replay the model-only detector/classifier path.")
  parser.add_argument("--low-speed-change-consistent-detections", type=int, help="Override reads required to change from 30+ mph to below 30 mph.")
  parser.add_argument(
    "--allow-low-speed-strong-consensus",
    action="store_true",
    help="Permit a strong multi-crop consensus to publish a low-speed change from one frame.",
  )
  parser.add_argument(
    "--enable-strong-model-consensus",
    action="store_true",
    help="Mark three agreeing high-confidence regulatory model crops as strong consensus.",
  )
  parser.add_argument("--initial-speed-limit", type=int, default=0, help="Seed route replay with a currently published speed limit.")
  return parser.parse_args()


def route_log_id(route: str) -> str:
  text = route.strip().strip("'\"")
  if "/" in text:
    text = text.rsplit("/", 1)[1]
  return text


def segment_index(path: Path) -> int:
  try:
    return int(path.parent.name.rsplit("--", 1)[1])
  except (IndexError, ValueError):
    return -1


def segment_paths(clip_root: Path, log_id: str) -> list[Path]:
  return sorted(
    (path for path in clip_root.glob(f"{log_id}--*/fcamera.hevc") if not path.name.startswith("._")),
    key=segment_index,
  )


def qlog_paths(clip_root: Path, log_id: str) -> list[Path]:
  paths: list[Path] = []
  for name in ("qlog.zst", "qlog.bz2", "qlog"):
    paths.extend(clip_root.glob(f"{log_id}--*/{name}"))
  return sorted((path for path in paths if not path.name.startswith("._")), key=segment_index)


def read_qlog(path: Path):
  if path.suffix == ".zst":
    with path.open("rb") as qlog_file, zstd.ZstdDecompressor().stream_reader(qlog_file) as reader:
      return log.Event.read_multiple_bytes(reader.read())
  if path.suffix == ".bz2":
    return log.Event.read_multiple_bytes(bz2.decompress(path.read_bytes()))
  return log.Event.read_multiple_bytes(path.read_bytes())


def build_runtime_context(qlogs: list[Path]) -> QlogRuntimeContext:
  cpu_times: list[float] = []
  cpu_busy: list[bool] = []
  live_pose_times: list[float] = []
  live_pose_inputs_ok: list[bool] = []
  road_times: list[float] = []
  road_names: list[str] = []
  started_times: list[float] = []
  started: list[bool] = []

  for qlog_path in qlogs:
    events = list(read_qlog(qlog_path))
    if not events:
      continue

    segment_start_s = max(segment_index(qlog_path), 0) * 60.0
    segment_first_time_ns = events[0].logMonoTime

    for event in events:
      now = segment_start_s + (event.logMonoTime - segment_first_time_ns) / 1e9
      event_type = event.which()
      if event_type == "deviceState":
        device_state = event.deviceState
        usage = list(device_state.cpuUsagePercent)
        busy = device_cpu_throttle_factor(usage) > 1.05
        cpu_times.append(now)
        cpu_busy.append(busy)
        started_times.append(now)
        started.append(bool(device_state.started))
      elif event_type == "livePose":
        live_pose_times.append(now)
        live_pose_inputs_ok.append(bool(event.livePose.inputsOK))
      elif event_type == "mapdOut":
        road_name = str(event.mapdOut.roadName or "")
        if road_name:
          road_times.append(now)
          road_names.append(road_name)

  return QlogRuntimeContext(
    cpu_times=cpu_times,
    cpu_busy=cpu_busy,
    live_pose_times=live_pose_times,
    live_pose_inputs_ok=live_pose_inputs_ok,
    road_times=road_times,
    road_names=road_names,
    started_times=started_times,
    started=started,
  )


def configure_models(models_dir: Path) -> None:
  models_dir = models_dir.expanduser().resolve()
  slv.US_DETECTOR_MODEL_PATH = models_dir / "speed_limit_us_detector.onnx"
  slv.US_CLASSIFIER_MODEL_PATH = models_dir / "speed_limit_us_value_classifier.onnx"
  slv.US_REJECT_CLASSIFIER_MODEL_PATH = models_dir / "speed_limit_us_reject_classifier.onnx"


def configure_runtime_options(args: argparse.Namespace) -> None:
  if args.detector_region_mode:
    slv.DETECTOR_CLASSIFIER_REGION_MODE = args.detector_region_mode

  if args.classifier_min_confidence is not None:
    slv.US_CLASSIFIER_MIN_CONFIDENCE = args.classifier_min_confidence

  if args.full_frame_ocr:
    slv.FULL_FRAME_OCR_FALLBACK_ENABLED = True
  if args.crop_ocr is not None:
    slv.DETECTOR_CLASSIFIER_CROP_OCR_ENABLED = args.crop_ocr
  if args.low_speed_change_consistent_detections is not None:
    slv.LOW_SPEED_CHANGE_CONSISTENT_DETECTIONS = args.low_speed_change_consistent_detections
  if args.allow_low_speed_strong_consensus:
    slv.LOW_SPEED_CHANGE_ALLOW_STRONG_CONSENSUS = True
  if args.enable_strong_model_consensus:
    slv.DETECTOR_CLASSIFIER_STRONG_MODEL_CONSENSUS_ENABLED = True
  if args.disable_temporal_tracking:
    slv.TEMPORAL_TRACKING_ENABLED = False
  if args.track_unreadable_min_proposal_confidence is not None:
    slv.TRACK_UNREADABLE_MIN_PROPOSAL_CONFIDENCE = args.track_unreadable_min_proposal_confidence
  if args.track_detector_interval is not None:
    slv.TRACK_DETECTOR_INTERVAL = args.track_detector_interval

  if args.right_roi_bounds:
    parts = [float(part.strip()) for part in args.right_roi_bounds.split(",")]
    if len(parts) != 4:
      raise ValueError("--right-roi-bounds must contain four comma-separated ratios")
    left, top, right, bottom = parts
    if not (0.0 <= left < right <= 1.0 and 0.0 <= top < bottom <= 1.0):
      raise ValueError("--right-roi-bounds must be normalized as 0 <= left < right <= 1 and 0 <= top < bottom <= 1")

    min_confidence = args.right_roi_min_confidence
    if min_confidence is None:
      min_confidence = float(slv.ROI_WINDOWS[-1]["min_confidence"]) if slv.ROI_WINDOWS else slv.US_DETECTOR_MIN_CONFIDENCE
    right_roi = {"bounds": (left, top, right, bottom), "min_confidence": float(min_confidence)}
    slv.ROI_WINDOWS = (*slv.ROI_WINDOWS[:-1], right_roi) if slv.ROI_WINDOWS else (right_roi,)
  elif args.right_roi_min_confidence is not None:
    if not slv.ROI_WINDOWS:
      right_roi = {"bounds": (0.72, 0.05, 1.00, 0.82), "min_confidence": float(args.right_roi_min_confidence)}
      slv.ROI_WINDOWS = (right_roi,)
    else:
      right_roi = dict(slv.ROI_WINDOWS[-1])
      right_roi["min_confidence"] = float(args.right_roi_min_confidence)
      slv.ROI_WINDOWS = (*slv.ROI_WINDOWS[:-1], right_roi)


def skip_to_frame(capture, frame_index: int, target_index: int, fast_seek: bool) -> int:
  if target_index <= frame_index:
    return frame_index
  if fast_seek:
    capture.set(cv2.CAP_PROP_POS_FRAMES, target_index)
    return target_index
  while frame_index < target_index:
    if not capture.grab():
      return target_index
    frame_index += 1
  return frame_index


def replay_route(
  log_id: str,
  segments: list[Path],
  runtime_context: QlogRuntimeContext | None,
  start_s: float,
  end_s: float | None,
  progress: bool,
  fast_seek: bool,
  measured_inference_seconds: float,
  measured_base_inference_seconds: float | None = None,
  measured_classifier_forward_seconds: float = 0.0,
  measured_tracking_base_seconds: float = 0.012,
  initial_speed_limit_mph: int = 0,
) -> tuple[RouteSummary, list[dict[str, str]]]:
  daemon = RouteReplayDaemon(
    runtime_context,
    measured_inference_seconds,
    measured_base_inference_seconds,
    measured_classifier_forward_seconds,
    measured_tracking_base_seconds,
  )
  daemon.published_speed_limit_mph = initial_speed_limit_mph
  for segment_path in segments:
    segment = segment_index(segment_path)
    capture = cv2.VideoCapture(str(segment_path))
    fps = source_video_fps(segment_path, capture.get(cv2.CAP_PROP_FPS))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    segment_start_s = segment * 60.0
    frame_index = max(int(round(max(start_s - segment_start_s, 0.0) * fps)), 0)
    if frame_index > 0:
      if fast_seek:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
      else:
        frame_index = skip_to_frame(capture, 0, frame_index, fast_seek=False)

    while total_frames <= 0 or frame_index < total_frames:
      now = segment_start_s + frame_index / fps
      if end_s is not None and now > end_s:
        capture.release()
        summary = summarize(log_id, len(segments), runtime_context is not None, daemon)
        return summary, daemon.events

      if not daemon.prepare_tick(now):
        frame_index = skip_to_frame(capture, frame_index, frame_index + 1, fast_seek)
        continue

      next_due = daemon.next_processing_due(now)
      if now < next_due:
        target_index = max(frame_index + 1, int(round((next_due - segment_start_s) * fps)))
        if total_frames > 0:
          target_index = min(target_index, total_frames)
        if target_index <= frame_index:
          target_index = frame_index + 1
        frame_index = skip_to_frame(capture, frame_index, target_index, fast_seek)
        continue

      ok, frame_bgr = capture.read()
      if not ok:
        break
      frame_index += 1
      daemon.process_frame(now, frame_bgr)

    capture.release()
    if progress:
      counts = f"sampled={daemon.sampled_frames} inference={daemon.inference_frames} events={len(daemon.events)}"
      print(f"  seg {segment:02d}: {counts}", flush=True)

  return summarize(log_id, len(segments), runtime_context is not None, daemon), daemon.events


def summarize(route: str, segment_count: int, qlog_context: bool, daemon: RouteReplayDaemon) -> RouteSummary:
  event_counts = {
    event_name: sum(1 for event in daemon.events if event["event"] == event_name)
    for event_name in ("candidate", "publish", "stale_clear", "road_change")
  }
  return RouteSummary(
    route=route,
    segments=segment_count,
    qlog_context=qlog_context,
    sampled_frames=daemon.sampled_frames,
    inference_frames=daemon.inference_frames,
    candidate_events=event_counts["candidate"],
    publish_events=event_counts["publish"],
    stale_clear_events=event_counts["stale_clear"],
    road_change_events=event_counts["road_change"],
  )


def write_events(path: Path, route_events: list[tuple[str, dict[str, str]]]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  fieldnames = [
    "route", "time_s", "event", "candidateSpeedLimitMph", "candidateConfidence", "speedLimitMph", "confidence", "reason",
    "previousRoadName", "roadName",
  ]
  with path.open("w", encoding="utf-8", newline="") as output_file:
    writer = csv.DictWriter(output_file, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for route, event in route_events:
      row = {"route": route}
      row.update(event)
      writer.writerow(row)


def publish_speed_changes(events: list[dict[str, str]]) -> list[tuple[float, str]]:
  changes: list[tuple[float, str]] = []
  last_speed = ""
  for event in events:
    if event["event"] in ("stale_clear", "road_change"):
      last_speed = ""
      continue
    if event["event"] != "publish":
      continue

    speed = event.get("speedLimitMph", "")
    if not speed or speed == last_speed:
      continue
    changes.append((float(event["time_s"]), speed))
    last_speed = speed
  return changes


def main() -> int:
  args = parse_args()
  configure_models(args.models_dir)
  configure_runtime_options(args)
  clip_root = args.clip_root.expanduser().resolve()
  all_events: list[tuple[str, dict[str, str]]] = []

  for route_input in args.routes:
    log_id = route_log_id(route_input)
    paths = segment_paths(clip_root, log_id)
    if not paths:
      print(f"{log_id}: no fcamera.hevc segments found under {clip_root}")
      continue

    runtime_context = None
    if args.qlog_context:
      qlogs = qlog_paths(clip_root, log_id)
      if not qlogs:
        print(f"{log_id}: no qlogs found under {clip_root}; replaying without qlog context")
      else:
        runtime_context = build_runtime_context(qlogs)

    summary, events = replay_route(
      log_id,
      paths,
      runtime_context,
      args.start,
      args.end,
      args.progress,
      args.fast_seek,
      args.measured_inference_seconds,
      args.measured_base_inference_seconds,
      args.measured_classifier_forward_seconds,
      args.measured_tracking_base_seconds,
      args.initial_speed_limit,
    )
    all_events.extend((log_id, event) for event in events)
    summary_line = "".join((
      f"{summary.route}: segments={summary.segments} qlog_context={int(summary.qlog_context)} sampled={summary.sampled_frames} ",
      f"inference={summary.inference_frames} candidate={summary.candidate_events} ",
      f"publish={summary.publish_events} stale_clear={summary.stale_clear_events} road_change={summary.road_change_events} ",
      f"measured_inference_s={args.measured_inference_seconds:.3f} ",
      f"measured_base_s={args.measured_base_inference_seconds if args.measured_base_inference_seconds is not None else 'off'} ",
      f"measured_classifier_forward_s={args.measured_classifier_forward_seconds:.3f} ",
      f"region={slv.DETECTOR_CLASSIFIER_REGION_MODE}",
    ))
    print(summary_line, flush=True)
    publish_values = [event.get("speedLimitMph") for event in events if event["event"] == "publish"]
    if publish_values:
      print(f"  publishes: {', '.join(publish_values)}", flush=True)
    speed_changes = publish_speed_changes(events)
    if speed_changes:
      print("  speed changes: " + ", ".join(f"{time_s:.1f}s={speed}" for time_s, speed in speed_changes), flush=True)

  if args.output_csv:
    write_events(args.output_csv.expanduser().resolve(), all_events)
    print(f"Wrote {args.output_csv.expanduser().resolve()}", flush=True)

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
