"""Bounded observational Card timing; no logging or I/O on the control thread."""
from collections import deque
import time


class CardLoopTiming:
  LIMIT_NS = 30_000_000
  REPORT_INTERVAL_NS = 5_000_000_000
  MAX_MARKS = 32

  def __init__(self, clock=None):
    self.clock = clock or self._clock
    self.pending = deque(maxlen=2)
    self.points = []
    self.previous = None
    self.previous_end = None
    self.last_report_ns = None
    self.dropped_reports = 0

  @staticmethod
  def _clock():
    # The clocks are sequential snapshots, not atomic scheduling observations.
    return (time.monotonic_ns(), time.thread_time_ns(), time.process_time_ns(),
            time.clock_gettime_ns(time.CLOCK_BOOTTIME) if hasattr(time, 'CLOCK_BOOTTIME') else 0)

  def begin(self):
    self.points = [('loop_start', *self.clock())]

  def mark(self, name):
    if self.points and len(self.points) < self.MAX_MARKS - 1:
      self.points.append((name, *self.clock()))

  def finish(self, context, *, enabled):
    self.points.append(('loop_end', *self.clock()))
    points = tuple(self.points)
    start, end = points[0][1], points[-1][1]
    between = start - self.previous_end[1] if self.previous_end is not None else 0
    late = end - start > self.LIMIT_NS or between > self.LIMIT_NS
    if enabled and late and (self.last_report_ns is None or end - self.last_report_ns >= self.REPORT_INTERVAL_NS):
      if len(self.pending) == self.pending.maxlen:
        self.dropped_reports += 1
      # Detached immutable frame points; formatting and logging happen elsewhere.
      self.pending.append((dict(context), self.previous, points, between, self.dropped_reports))
      self.last_report_ns = end
    self.previous = (dict(context), points)
    self.previous_end = points[-1]
    self.points = []

  def take_report(self):
    try:
      context, previous, current, between, dropped = self.pending.popleft()
    except IndexError:
      return None
    frames = []
    for frame in (previous, (context, current)):
      if frame is None:
        continue
      frame_context, points = frame
      frames.append({**frame_context, 'start_ns': points[0][1], 'end_ns': points[-1][1],
        'start_boot_ns': points[0][4], 'end_boot_ns': points[-1][4], 'points': points,
        'phases': [{'from': a[0], 'to': b[0], 'wall_ns': b[1] - a[1],
                    'thread_cpu_ns': b[2] - a[2], 'process_cpu_ns': b[3] - a[3]}
                   for a, b in zip(points, points[1:], strict=False)]})
    return {**context, 'between_loops_ns': between, 'dropped_reports': dropped, 'frames': frames}
