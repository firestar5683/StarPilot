"""Temporary, bounded observations of Card publication gaps.

This observer never supplies control data. MONOTONIC and thread CPU are paired
sequential samples, not atomic observations. Backend-return to GIL-reacquired
also includes scheduler delay; it does not prove contention on Python's lock.
"""
from collections import deque
import threading
import time


class CardStallTiming:
  LIMIT_NS = 30_000_000
  INTERVAL_NS = 5_000_000_000
  MAX_MARKS = 32
  MARKS = frozenset(('can_receive_start', 'can_receive_end', 'can_decode_end', 'interface_update_end',
                    'radar_update_start', 'radar_update_end', 'submaster_end', 'permission_and_cruise_end',
                    'conditional_params_end', 'wheel_params_start', 'wheel_params_end', 'state_update_end',
                    'startup_maintain_end', 'car_state_send_start', 'car_state_send_end', 'state_publish_end',
                    'controller_apply_start', 'controller_apply_end', 'sendcan_start', 'sendcan_end',
                    'controls_update_end'))

  def __init__(self, socket, *, clock=None):
    self.clock = clock or self._clock
    self.socket = socket
    self.frames = [[None] * self.MAX_MARKS for _ in range(2)]
    self.lengths = [0, 0]
    self.can_summaries = [None, None]
    self.index = 0
    self.generation = 0
    self.previous = False
    self.last_publication = None
    self.last_capture = None
    self.last_attempt = None
    self.pending = deque(maxlen=1)
    self.late_count = 0
    self.throttled_count = 0
    self.queue_full_count = 0
    self.omitted_marks = 0
    self.errors = 0
    self.log_errors = 0
    self.worker = None
    self.thread_id = threading.get_native_id()
    self.native_available = False
    try:
      socket.enable_receive_timing(True)
      self.native_available = True
    except Exception:
      self.errors += 1
    self.status_pending = True
    self.last_counters = None

  @staticmethod
  def _clock():
    return time.monotonic_ns(), time.thread_time_ns()

  def begin(self):
    try:
      self.generation += 1
      self.index = 1 - self.index
      self.previous = self.lengths[1 - self.index] > 0
      self.lengths[self.index] = 0
      self.can_summaries[self.index] = None
      self._mark('loop_start')
    except Exception:
      self.errors += 1

  def _mark(self, name):
    length = self.lengths[self.index]
    if length == self.MAX_MARKS:
      self.omitted_marks += 1
      return
    self.frames[self.index][length] = (name, *self.clock())
    self.lengths[self.index] = length + 1

  def mark(self, name):
    try:
      if name in self.MARKS:
        self._mark(name)
    except Exception:
      self.errors += 1

  def observe_can(self, raw, decoded):
    try:
      # Bound observer work even if the ordinary drain returned an unusually
      # large batch. No additional envelope decode or CAN payload copying.
      count = min(len(raw), len(decoded), 64)
      frames = byte_count = 0
      first = last = None
      for i in range(count):
        stamp, messages = decoded[i]
        frames += len(messages)
        byte_count += len(raw[i])
        first = stamp if first is None else min(first, stamp)
        last = stamp if last is None else max(last, stamp)
      self.can_summaries[self.index] = (len(raw), count, frames, byte_count, first, last)
    except Exception:
      self.errors += 1

  def finish(self):
    try:
      self._mark('loop_end')
    except Exception:
      self.errors += 1

  def published(self, source_ns, session):
    try:
      now, cpu = self.clock()
      last = self.last_publication
      self.last_publication = (source_ns, now, session, self.generation)
      if source_ns <= 0 or last is None or last[0] <= 0 or last[2] != session or source_ns <= last[0] or now <= last[1]:
        return
      source_gap, send_gap = source_ns - last[0], now - last[1]
      if max(source_gap, send_gap) <= self.LIMIT_NS:
        return
      self.late_count += 1
      if self.last_capture is not None and now - self.last_capture < self.INTERVAL_NS:
        self.throttled_count += 1
        return
      if self.pending:
        self.queue_full_count += 1
        return
      self.last_capture = now
      # Snapshot only on a bounded late event. No formatting, logging, Params,
      # file I/O or locks on Card; the sole consumer runs in params_thread.
      previous = tuple(self.frames[1 - self.index][:self.lengths[1 - self.index]]) if self.previous else ()
      current = tuple(self.frames[self.index][:self.lengths[self.index]])
      native = self.socket.take_receive_timing() if self.native_available else None
      clock_mapping = (time.monotonic_ns(), time.clock_gettime_ns(time.CLOCK_BOOTTIME), time.monotonic_ns())
      self.pending.append((source_ns, now, cpu, session, last, source_gap, send_gap,
                           previous, current, native, self.worker, self.generation, clock_mapping,
                           self.can_summaries[1 - self.index], self.can_summaries[self.index]))
    except Exception:
      self.errors += 1

  def worker_mark(self, phase):
    try:
      self.worker = (phase, threading.get_native_id(), *self.clock())
    except Exception:
      self.errors += 1

  def flush(self, emit):
    """Called only by the existing non-realtime worker, at most once per 5s.

    This Python work still uses the GIL. Native ring/phase sizes and report
    frequency bound it; formatting is not evidence of zero observer effect.
    """
    try:
      now = time.monotonic_ns()
      if self.last_attempt is not None and now - self.last_attempt < self.INTERVAL_NS:
        return
      counter_values = (self.late_count, self.throttled_count, self.queue_full_count, self.omitted_marks, self.errors, self.log_errors)
      if not self.pending and not self.status_pending and counter_values == self.last_counters:
        return
      self.last_attempt = now
      self.last_counters = counter_values
      status = self.status_pending
      self.status_pending = False
      sample = self.pending.popleft() if self.pending else None
      counters = {'late_count': self.late_count, 'throttled_count': self.throttled_count,
                  'queue_full_count': self.queue_full_count, 'omitted_marks': self.omitted_marks,
                  'capture_errors': self.errors, 'log_errors': self.log_errors}
      report = {'version': 1, 'native_available': self.native_available, 'thread_id': self.thread_id,
                'clock': 'CLOCK_MONOTONIC', 'source_clock': 'CLOCK_MONOTONIC', 'cpu_clock': 'CLOCK_THREAD_CPUTIME_ID',
                'native_fields': ('sequence', 'non_blocking', 'returned_message', 'byte_length', 'before_wall', 'before_cpu',
                                  'backend_return_wall', 'backend_return_cpu', 'gil_reacquired_wall',
                                  'gil_reacquired_cpu', 'python_return_wall', 'python_return_cpu'),
                'counters': counters, 'status': status}
      if sample is not None:
        source, send, cpu, session, last, source_gap, send_gap, previous, current, native, worker, generation, mapping, prev_can, current_can = sample
        report.update(source_ns=source, send_return_observed_ns=send, send_thread_cpu_ns=cpu,
                      producer_session=session, previous_publication=last,
                      source_gap_ns=source_gap, send_gap_ns=send_gap, previous_frame=previous,
                      current_frame=current, current_frame_complete=False, native=native,
                      native_capacity=64, native_omitted_is_cumulative=True, generation=generation,
                      previous_publication_frame_retained=last[3] == generation - 1,
                      nonpublishing_frames=max(0, generation - last[3] - 1),
                      clock_mapping_mono_boot_mono=mapping,
                      can_summary_fields=('total_envelopes', 'summarized_envelopes', 'summarized_frames',
                                          'summarized_bytes', 'min_source_ns', 'max_source_ns'),
                      can_source_clock='CLOCK_BOOTTIME', previous_can=prev_can, current_can=current_can,
                      worker_progress=worker)
      emit('card.stall_timing', error=sample is not None or not self.native_available, **report)
    except Exception:
      self.log_errors += 1
