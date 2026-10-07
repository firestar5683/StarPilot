"""Bounded Ioniq 6 torque tracking analysis of explicitly supplied Cereal events.

This module has no route discovery, file, Params, network, tune, or control owner.
It reports observed tracking only; a small error is not a safety qualification.
"""

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from bisect import bisect_left
import hashlib
import math

from opendbc.car.hyundai.values import CAR


MAX_SEGMENTS = 5
MAX_MESSAGES_PER_SEGMENT = 400_000
MAX_SAMPLES_PER_SEGMENT = 100_000
MAX_SERIES_POINTS = 160
MAX_WINDOWS = 128
JOIN_MAX_AGE_NS = 250_000_000
GAP_NS = 250_000_000
OVERRIDE_PRE_NS = 350_000_000
OVERRIDE_POST_NS = 1_000_000_000


@dataclass(frozen=True)
class SegmentInput:
  route: str
  number: int
  events: Iterable[object]


@dataclass(frozen=True)
class TrackingSample:
  mono_ns: int
  speed_mps: float
  desired_lat_accel: float
  actual_lat_accel: float
  saturated: bool
  steering_pressed: bool
  epoch: int = 0


@dataclass(frozen=True)
class PlotPoint:
  mono_ns: int
  desired_lat_accel: float
  actual_lat_accel: float
  continuity_id: int


@dataclass(frozen=True)
class TrackingWindow:
  start_mono_ns: int
  end_mono_ns: int
  sample_count: int
  mean_speed_mps: float
  peak_abs_error: float
  direction: str


@dataclass(frozen=True)
class SegmentReport:
  route: str
  number: int
  status: str
  car_params_sha256: str | None
  messages: int
  torque_frames: int
  eligible_samples: int
  exclusions: tuple[tuple[str, int], ...]
  mean_abs_error: float | None
  root_mean_square_error: float | None
  series: tuple[PlotPoint, ...]
  windows: tuple[TrackingWindow, ...]
  windows_truncated: bool


@dataclass(frozen=True)
class AnalysisReport:
  segments: tuple[SegmentReport, ...]


def _finite_number(value: float) -> float | None:
  try:
    number = float(value)
  except (TypeError, ValueError, OverflowError):
    return None
  return number if math.isfinite(number) else None


def _timestamp(event: object) -> int | None:
  value = getattr(event, 'logMonoTime', None)
  return value if type(value) is int and 0 < value <= (1 << 64) - 1 else None


def _source(latest: dict[str, tuple[int, object]], name: str, sample_ns: int) -> object | None:
  entry = latest.get(name)
  if entry is None or not 0 <= sample_ns - entry[0] <= JOIN_MAX_AGE_NS:
    return None
  return entry[1]


def _downsample(samples: list[TrackingSample]) -> tuple[PlotPoint, ...]:
  if len(samples) <= MAX_SERIES_POINTS:
    chosen = samples
  else:
    chosen = [samples[i * (len(samples) - 1) // (MAX_SERIES_POINTS - 1)] for i in range(MAX_SERIES_POINTS)]
  return tuple(PlotPoint(s.mono_ns, s.desired_lat_accel, s.actual_lat_accel, s.epoch) for s in chosen)


def _eligible(samples: list[TrackingSample], overrides: list[int] | None = None) -> list[bool]:
  """Match frozen 0.35 s before / 1 s after driver override per gap group."""
  presses = sorted(overrides if overrides is not None else [s.mono_ns for s in samples if s.steering_pressed])
  result = [True] * len(samples)
  start = 0
  while start < len(samples):
    end = start + 1
    while end < len(samples) and samples[end].epoch == samples[start].epoch and samples[end].mono_ns - samples[end - 1].mono_ns <= GAP_NS:
      end += 1
    for i in range(start, end):
      stamp = samples[i].mono_ns
      next_index = bisect_left(presses, stamp)
      if next_index > 0 and stamp - presses[next_index - 1] <= OVERRIDE_POST_NS:
        result[i] = False
      if next_index < len(presses) and presses[next_index] - stamp <= OVERRIDE_PRE_NS:
        result[i] = False
    result[start] = False
    result[end - 1] = False
    start = end
  return result


def _windows(samples: list[TrackingSample], eligible: list[bool]) -> tuple[tuple[TrackingWindow, ...], bool]:
  windows = []
  truncated = False
  start = None
  for index in range(len(samples) + 1):
    active = index < len(samples) and eligible[index] and (
      start is None or (samples[index].epoch == samples[index - 1].epoch and samples[index].mono_ns - samples[index - 1].mono_ns <= GAP_NS))
    if active and start is None:
      start = index
    if active:
      continue
    if start is not None and index - start >= 5:
      group = samples[start:index]
      if len(windows) == MAX_WINDOWS:
        truncated = True
      else:
        mean_desired = sum(s.desired_lat_accel for s in group) / len(group)
        direction = 'left' if mean_desired > .02 else 'right' if mean_desired < -.02 else 'center'
        windows.append(TrackingWindow(group[0].mono_ns, group[-1].mono_ns, len(group),
                                      sum(s.speed_mps for s in group) / len(group),
                                      max(abs(s.actual_lat_accel - s.desired_lat_accel) for s in group), direction))
    start = index if index < len(samples) and eligible[index] else None
  return tuple(windows), truncated


def analyze_segments(segments: tuple[SegmentInput, ...], *, cancelled: Callable[[], bool] = lambda: False,
                     gm_context: dict | None = None, evidence: list | None = None) -> AnalysisReport:
  if not 1 <= len(segments) <= MAX_SEGMENTS:
    raise ValueError('segment_count')
  if len({(s.route, s.number) for s in segments}) != len(segments):
    raise ValueError('duplicate_segment')
  return AnalysisReport(tuple(_analyze(segment, cancelled, gm_context=gm_context, evidence=evidence) for segment in segments))


def _analyze(segment: SegmentInput, cancelled: Callable[[], bool], *,
             gm_context: dict | None = None, evidence: list | None = None) -> SegmentReport:
  if not segment.route or len(segment.route) > 128 or type(segment.number) is not int or not 0 <= segment.number <= 9999:
    raise ValueError('segment_identity')
  latest: dict[str, tuple[int, object]] = {}
  source_highwater: dict[str, int] = {}
  counts: Counter[str] = Counter()
  samples: list[TrackingSample] = []
  override_ns: list[int] = []
  gm_samples: dict[int, object] = {}
  messages = torque_frames = 0
  cp_seen = cp_ok = False
  cp_digest = None
  epoch = 0
  last_control_ns = 0
  ordered: list[tuple[int, int, int, str, object]] = []
  priority = {'carParams': 0, 'carState': 1, 'carControl': 2, 'controlsState': 3}
  for event in segment.events:
    messages += 1
    if messages > MAX_MESSAGES_PER_SEGMENT:
      raise ValueError('message_limit')
    if messages % 128 == 0 and cancelled():
      raise RuntimeError('cancelled')
    stamp = _timestamp(event)
    try:
      kind = event.which()
    except (AttributeError, ValueError, RuntimeError):
      counts['malformed_event'] += 1
      continue
    if kind not in ('carParams', 'carState', 'carControl', 'controlsState'):
      continue
    if kind == 'carParams':
      # CarParams describes this closed segment's static controller context,
      # not a time-varying sensor. Validate every publication before joining
      # any samples, including a context first published late in the segment.
      if stamp is None or not getattr(event, 'valid', False):
        raise ValueError('invalid_car_params')
      try:
        cp = event.carParams
        digest = hashlib.sha256(cp.as_builder().to_bytes()).hexdigest()
        supported = (cp.carFingerprint == CAR.HYUNDAI_IONIQ_6 and cp.lateralTuning.which() == 'torque' and
                     cp.steerControlType == 'torque' and not cp.dashcamOnly)
        if gm_context is not None:
          from openpilot.starpilot.flm.gm_recommend import matches_recording
          supported = matches_recording(cp, gm_context)
      except (AttributeError, ValueError, RuntimeError, TypeError) as error:
        raise ValueError('invalid_car_params') from error
      if cp_seen and digest != cp_digest:
        raise ValueError('inconsistent_car_params')
      cp_seen, cp_ok, cp_digest = True, supported, digest
      continue
    if stamp is None or stamp <= source_highwater.get(kind, 0):
      counts['invalid_or_reordered_timestamp'] += 1
      continue
    source_highwater[kind] = stamp
    ordered.append((stamp, priority[kind], messages, kind, event))
  # Publisher IPC order is not original sample order. A bounded per-source
  # chronology guard runs above; this join uses original producer timestamps.
  ordered.sort()
  for stamp, _, _, kind, event in ordered:
    if cancelled():
      raise RuntimeError('cancelled')
    if kind == 'controlsState':
      if last_control_ns and stamp - last_control_ns > GAP_NS:
        epoch += 1
      last_control_ns = stamp
    if not getattr(event, 'valid', False):
      counts['invalid_event'] += 1
      latest.pop(kind, None)
      epoch += 1
      continue
    if kind == 'carState':
      if not event.carState.canValid:
        counts['invalid_car_state'] += 1
        latest.pop(kind, None)
        epoch += 1
      else:
        latest[kind] = (stamp, event.carState)
        if event.carState.steeringPressed:
          override_ns.append(stamp)
    elif kind == 'carControl':
      latest[kind] = (stamp, event.carControl)
    elif kind == 'controlsState':
      try:
        lateral = event.controlsState.lateralControlState
        if lateral.which() != 'torqueState':
          counts['other_controller'] += 1
          epoch += 1
          continue
        torque = lateral.torqueState
      except (AttributeError, ValueError, RuntimeError):
        counts['malformed_torque_state'] += 1
        epoch += 1
        continue
      torque_frames += 1
      if not cp_ok:
        counts['missing_or_unsupported_car_params'] += 1
        epoch += 1
        continue
      car_state = _source(latest, 'carState', stamp)
      car_control = _source(latest, 'carControl', stamp)
      if car_state is None or car_control is None:
        counts['missing_or_stale_source'] += 1
        epoch += 1
        continue
      if not car_control.latActive or not torque.active:
        counts['lateral_inactive'] += 1
        epoch += 1
        continue
      speed = _finite_number(car_state.vEgo)
      desired = _finite_number(torque.desiredLateralAccel)
      actual = _finite_number(torque.actualLateralAccel)
      if speed is None or not 0 <= speed <= 100 or desired is None or abs(desired) > 100 or actual is None or abs(actual) > 100:
        counts['invalid_numeric'] += 1
        epoch += 1
        continue
      if len(samples) >= MAX_SAMPLES_PER_SEGMENT:
        raise ValueError('sample_limit')
      samples.append(TrackingSample(stamp, speed, desired, actual, bool(torque.saturated), bool(car_state.steeringPressed), epoch))
      if gm_context is not None:
        # Only fields used by original GM classification must be measured.
        # Unused legacy output/roll placeholders remain explicitly unavailable;
        # no carOutput/native/physical receipt is invented from carControl.
        from openpilot.starpilot.flm.gm_evidence import FLMSample
        jerk = _finite_number(torque.desiredLateralJerk)
        angle = _finite_number(car_state.steeringAngleDeg)
        output = _finite_number(torque.output)
        if jerk is not None and abs(jerk) <= 1000 and angle is not None and abs(angle) <= 2000 and output is not None and abs(output) <= 2:
          gm_samples[len(samples) - 1] = FLMSample(segment.route, segment.number, stamp / 1e9, speed,
            True, bool(car_state.steeringPressed), bool(torque.saturated), actual, desired, jerk,
            _finite_number(torque.error), _finite_number(torque.errorRate), _finite_number(torque.p),
            _finite_number(torque.i), _finite_number(torque.d), _finite_number(torque.f), output, angle,
            _finite_number(car_state.steeringTorque), _finite_number(car_control.actuators.torque), None, None)
        else:
          counts['missing_gm_evidence_numeric'] += 1

  if cancelled():
    raise RuntimeError('cancelled')
  eligibility = _eligible(samples, override_ns)
  windows, windows_truncated = _windows(samples, eligibility)
  accepted = [sample for sample, eligible in zip(samples, eligibility, strict=True) if eligible]
  counts['driver_override_or_boundary'] += len(samples) - len(accepted)
  if gm_context is not None and evidence is not None:
    group = []
    previous = None
    for index, sample in enumerate(samples):
      measured = gm_samples.get(index) if eligibility[index] else None
      continuous = (previous is not None and sample.epoch == previous.epoch and
                    0 < sample.mono_ns - previous.mono_ns <= GAP_NS)
      if measured is None or not continuous:
        if group:
          evidence.append(group)
        group = []
      if measured is not None:
        group.append(measured)
      previous = sample if measured is not None else None
    if group:
      evidence.append(group)

  error = [s.actual_lat_accel - s.desired_lat_accel for s in accepted]
  if cp_seen and not cp_ok:
    status = 'unsupported_car'
  elif not cp_seen:
    status = 'missing_car_params'
  elif torque_frames == 0 and counts['other_controller']:
    status = 'unsupported_controller'
  elif not accepted:
    status = 'insufficient_samples'
  else:
    status = 'measured'
  return SegmentReport(segment.route, segment.number, status, cp_digest, messages, torque_frames, len(accepted), tuple(sorted(counts.items())),
                       sum(abs(x) for x in error) / len(error) if error else None,
                       math.sqrt(sum(x * x for x in error) / len(error)) if error else None,
                       _downsample(accepted), windows, windows_truncated)
