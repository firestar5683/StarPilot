"""On-demand metrics from one immutable, closed local full rlog segment."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
import math
import os
from pathlib import Path
import stat
import threading
import time

from openpilot.starpilot.flm.local_logs import (DIR_FLAGS, FILE_FLAGS, LocalLogUnavailable, RLOGS,
                                                read_closed_rlog)
from openpilot.starpilot.flm.log_decode import LogDecodeError, decode_segment
from openpilot.starpilot.galaxy.drive_history import MAX_SEGMENT_ENTRIES, SEGMENT_NAME


MAX_ANALYSIS_SECONDS = 8.0
MAX_PAIR_SECONDS = 1.0
MAX_SPEED_MPS = 70.0


class SegmentSummaryUnavailable(Exception):
  pass


class SegmentSummaryChanged(SegmentSummaryUnavailable):
  pass


def _revision(info: os.stat_result) -> tuple[int, int, int, int, int]:
  return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


@contextmanager
def _source_guard(root: Path, segment_name: str):
  matched = SEGMENT_NAME.fullmatch(segment_name) if type(segment_name) is str and len(segment_name) <= 180 else None
  if matched is None or len(matched.group('number')) > 6 or not root.is_absolute() or '..' in root.parts:
    raise ValueError('Invalid local segment selection')
  fds: list[int] = []
  try:
    root_fd = os.open(root, DIR_FLAGS)
    fds.append(root_fd)
    segment_fd = os.open(segment_name, DIR_FLAGS, dir_fd=root_fd)
    fds.append(segment_fd)
    names: list[str] = []
    with os.scandir(segment_fd) as entries:
      for count, entry in enumerate(entries, 1):
        if count > MAX_SEGMENT_ENTRIES or entry.name.endswith('.lock'):
          raise SegmentSummaryChanged('Segment is open or unavailable')
        if entry.name in RLOGS:
          names.append(entry.name)
    if len(names) != 1:
      raise SegmentSummaryUnavailable('One closed full log is required')
    filename = names[0]
    source_fd = os.open(filename, FILE_FLAGS, dir_fd=segment_fd)
    fds.append(source_fd)
    root_identity = os.fstat(root_fd).st_dev, os.fstat(root_fd).st_ino
    segment_identity = os.fstat(segment_fd).st_dev, os.fstat(segment_fd).st_ino
    initial = _revision(os.fstat(source_fd))
    if not stat.S_ISREG(os.fstat(source_fd).st_mode):
      raise SegmentSummaryUnavailable('Full log is not a regular file')

    def current() -> bool:
      try:
        root_now = os.stat(root, follow_symlinks=False)
        segment_now = os.stat(segment_name, dir_fd=root_fd, follow_symlinks=False)
        source_now = os.stat(filename, dir_fd=segment_fd, follow_symlinks=False)
        if (not stat.S_ISDIR(root_now.st_mode) or not stat.S_ISDIR(segment_now.st_mode) or
            not stat.S_ISREG(source_now.st_mode) or
            (root_now.st_dev, root_now.st_ino) != root_identity or
            (segment_now.st_dev, segment_now.st_ino) != segment_identity or
            _revision(source_now) != initial or _revision(os.fstat(source_fd)) != initial):
          return False
        with os.scandir(segment_fd) as entries:
          return all(count <= MAX_SEGMENT_ENTRIES and not entry.name.endswith('.lock')
                     for count, entry in enumerate(entries, 1))
      except OSError:
        return False

    if not current():
      raise SegmentSummaryChanged('Local recording identity changed')
    yield filename, current
  except OSError as error:
    raise SegmentSummaryUnavailable('Local recording is unavailable') from error
  finally:
    for fd in reversed(fds):
      os.close(fd)


def _project(events, permitted: Callable[[], bool]) -> dict:
  previous_car: tuple[int, float] | None = None
  previous_control: tuple[int, bool, bool] | None = None
  car_high_water = control_high_water = 0
  first_car = last_car = first_control = last_control = None
  distance = lat_seconds = long_seconds = 0.0
  car_pairs = control_pairs = car_gaps = control_gaps = 0
  for event in events:
    if not permitted():
      raise SegmentSummaryUnavailable('Summary is no longer available')
    kind = event.which()
    if kind == 'carState':
      stamp = int(event.logMonoTime)
      speed = float(event.carState.vEgo)
      if not event.valid or stamp <= 0 or not math.isfinite(speed) or not 0 <= speed <= MAX_SPEED_MPS:
        car_high_water = max(car_high_water, stamp)
        previous_car = None
        car_gaps += 1
        continue
      if stamp <= car_high_water:
        previous_car = None
        car_gaps += 1
        continue
      car_high_water = stamp
      if previous_car is not None:
        delta = (stamp - previous_car[0]) / 1e9
        if 0 < delta <= MAX_PAIR_SECONDS:
          distance += (previous_car[1] + speed) * .5 * delta
          car_pairs += 1
        else:
          car_gaps += 1
      first_car = stamp if first_car is None else min(first_car, stamp)
      last_car = stamp if last_car is None else max(last_car, stamp)
      previous_car = stamp, speed
    elif kind == 'carControl':
      stamp = int(event.logMonoTime)
      if not event.valid or stamp <= 0:
        control_high_water = max(control_high_water, stamp)
        previous_control = None
        control_gaps += 1
        continue
      if stamp <= control_high_water:
        previous_control = None
        control_gaps += 1
        continue
      control_high_water = stamp
      lat, long = bool(event.carControl.latActive), bool(event.carControl.longActive)
      first_control = stamp if first_control is None else min(first_control, stamp)
      last_control = stamp if last_control is None else max(last_control, stamp)
      if previous_control is not None:
        delta = (stamp - previous_control[0]) / 1e9
        if 0 < delta <= MAX_PAIR_SECONDS:
          lat_seconds += delta if previous_control[1] else 0.0
          long_seconds += delta if previous_control[2] else 0.0
          control_pairs += 1
        else:
          control_gaps += 1
      previous_control = stamp, lat, long
  return {
    'observedCarSpanSeconds': (last_car - first_car) / 1e9 if first_car is not None and last_car is not None and last_car > first_car else None,
    'estimatedDistanceMeters': round(distance, 2) if car_pairs else None,
    'observedLatActiveSeconds': round(lat_seconds, 2) if control_pairs else None,
    'observedLongActiveSeconds': round(long_seconds, 2) if control_pairs else None,
    'gaps': {'carState': car_gaps, 'carControl': control_gaps},
    'sampleCoverageComplete': bool(car_pairs and control_pairs and not car_gaps and not control_gaps and
                                   first_control is not None and last_control is not None and
                                   first_car is not None and last_car is not None and
                                   first_control <= first_car and last_control >= last_car),
  }


class SegmentSummary:
  def __init__(self, root: Path):
    self.root = root
    self._lock = threading.Lock()

  def snapshot(self, segment_name: str, *, permitted: Callable[[], bool]) -> dict:
    if not self._lock.acquire(blocking=False):
      raise SegmentSummaryUnavailable('Another segment is being read')
    deadline = time.monotonic() + MAX_ANALYSIS_SECONDS
    def allowed() -> bool:
      return time.monotonic() <= deadline and permitted()
    try:
      if not allowed():
        raise SegmentSummaryUnavailable('Summary is no longer available')
      with _source_guard(self.root, segment_name) as (filename, current):
        closed = read_closed_rlog(self.root, segment_name, permitted=allowed)
        if filename not in RLOGS or closed.codec != RLOGS[filename] or not current():
          raise SegmentSummaryChanged('Local recording identity changed')
        events = decode_segment(closed.compressed, closed.codec, cancelled=lambda: not allowed())
        result = _project(events, allowed)
        if not allowed() or not current():
          raise SegmentSummaryChanged('Local recording identity changed')
        return {'schemaVersion': 1, 'source': 'closed_local_rlog', 'segmentName': segment_name,
                'sourceSha256': closed.sha256, **result}
    except (LocalLogUnavailable, LogDecodeError) as error:
      raise SegmentSummaryUnavailable('Closed full log is unavailable') from error
    finally:
      self._lock.release()
