"""Bounded observational SelfdriveD timing; formatting and logging stay off-thread."""
from collections import deque
import time


class SelfdriveLoopTiming:
  SLOW_NS = 15_000_000
  REPORT_INTERVAL_NS = 5_000_000_000
  MAX_MARKS = 40
  WINDOW = 100

  def __init__(self, clock=None):
    self.clock = clock or self._clock
    self.pending = deque(maxlen=2)
    self.history = deque(maxlen=self.WINDOW)
    self.points = []
    self.before_rate = None
    self.before_proof = None
    self.previous_end = None
    self.last_report_ns = None
    self.cycle_sequence = 0
    self.report_sequence = 0
    self.delivered_sequence = 0
    self.trigger_count = 0
    self.rate_suppressed = 0
    self.queue_full_observations = 0
    self.truncated_marks = 0
    self.capture_errors = 0
    self.sink_errors = 0
    self.worker_capture_errors = 0
    self.worker_window = None
    self.suppressed_peak = None

  @staticmethod
  def _clock():
    # Sequential snapshots. These do not measure OS runnable time or GIL ownership.
    # Do not alter the monotonic_ns samples used by control/authority decisions.
    return (time.clock_gettime_ns(time.CLOCK_MONOTONIC), time.thread_time_ns())

  @staticmethod
  def _rate(rk):
    avg = rk.avg_dt
    return (rk.frame, rk._interval, avg.count, avg.sum, avg.get_average(), rk.lagging, rk._last_monitor_time, rk.remaining, rk._next_frame_time)

  def begin(self, rk, proof=None):
    try:
      self.cycle_sequence += 1
      self.before_rate = self._rate(rk)
      self.before_proof = proof
      self.points = [('cycle_start', *self.clock())]
      self.process_start_ns = time.process_time_ns()
    except Exception:
      self.capture_errors += 1
      self.points = []

  def mark(self, name):
    if not self.points:
      return
    if len(self.points) >= self.MAX_MARKS - 1:
      self.truncated_marks += 1
      return
    try:
      self.points.append((name, *self.clock()))
    except Exception:
      self.capture_errors += 1
      self.points = []

  def worker_mark(self, started):
    try:
      point = self.clock()
      self.worker_window = (point, None) if started else (
        self.worker_window[0] if self.worker_window is not None else None, point)
    except Exception:
      self.worker_capture_errors += 1

  def finish(self, owner, rk):
    if not self.points:
      return
    try:
      self._finish(owner, rk)
    except Exception:
      # An observational recorder must never prevent the next control iteration.
      self.capture_errors += 1
    finally:
      self.points = []

  def _finish(self, owner, rk):
    before_rate = self.before_rate
    if before_rate is None:
      return
    self.points.append(('ratekeeper_return', *self.clock()))
    points = tuple(self.points)
    start, end = points[0][1], points[-1][1]
    between = start - self.previous_end if self.previous_end is not None else 0
    self.previous_end = end
    sm = owner.sm
    companion = getattr(owner, 'aol_intent_companion', None)
    latest = getattr(companion, 'latest', None)
    rate = self._rate(rk)
    context = (self.cycle_sequence, int(getattr(owner, 'aol_car_state_log_ns', 0)),
      int(getattr(owner, '_loop_decision_ns', 0)), int(getattr(owner, '_loop_received_source_ns', 0)),
      int(sm.logMonoTime.get('aolIntentWire', 0)), int(sm.logMonoTime.get('aolSafetyWire', 0)),
      int(latest[0]) if latest is not None else 0, int(getattr(owner, 'aol_step_intent_drain_count', 0)),
      bool(getattr(owner, 'aol_axis_publication_deferred', False)),
      int(getattr(owner, '_loop_decision_source_ns', 0)), self.before_proof,
      time.process_time_ns() - self.process_start_ns)
    self.history.append((context, points, between, before_rate, rate))
    slow = end - start > self.SLOW_NS or between > self.SLOW_NS
    lag = bool(before_rate[5] or rate[5])
    triggered = slow or lag
    if triggered:
      self.trigger_count += 1
    if not triggered and self.suppressed_peak is None:
      return
    if self.last_report_ns is not None and end - self.last_report_ns < self.REPORT_INTERVAL_NS:
      if triggered:
        self.rate_suppressed += 1
        score = max(end - start, between)
        if self.suppressed_peak is None or score > self.suppressed_peak[0]:
          self.suppressed_peak = (score, self.history[-1])
      return
    self.last_report_ns = end
    self.report_sequence += 1
    if len(self.pending) == self.pending.maxlen:
      # The worker can popleft between this check and append. Sequence gaps,
      # rather than this observation count, identify overwritten queued reports.
      self.queue_full_observations += 1
    proof = getattr(owner, 'aol_published_input_proof', None)
    snapshot = dict(getattr(companion, 'last_snapshot', {}))
    native = getattr(owner, 'aol_decision_native', None)
    avg = rk.avg_dt
    metadata = {
      'version': 1, 'report_sequence': self.report_sequence,
      'trigger_slow': slow, 'trigger_lagging': lag, 'suppressed_summary': not triggered,
      'suppressed_peak_frame': self.suppressed_peak, 'diagnostic_slow_ns': self.SLOW_NS,
      'trigger_count': self.trigger_count, 'rate_suppressed': self.rate_suppressed,
      'queue_full_observations': self.queue_full_observations, 'truncated_marks': self.truncated_marks,
      'capture_errors': self.capture_errors, 'sink_errors': self.sink_errors,
      'worker_capture_errors': self.worker_capture_errors,
      'axis_session': str(getattr(owner, 'aol_session_id', '')), 'enabled': bool(owner.enabled),
      'active': bool(owner.active), 'initialized': bool(owner.initialized),
      'fault_reason': str(getattr(owner, 'aol_fault_reason', 'none')),
      'events': tuple(int(event) for event in owner.events.names),
      'intent_snapshot': snapshot, 'intent_snapshot_matches_decision': snapshot.get('now_ns') == context[2],
      'native_decision': {name: getattr(native, name) for name in (
        'observedMonoTime', 'validUntilMonoTime', 'requestedLateral', 'requestedLongitudinal',
        'lateralAllowed', 'longitudinalAllowed', 'axisSessionId')} if native is not None else None,
      'intent_rejection': getattr(companion, 'last_rejection', None),
      'intent_last_drain_count': int(getattr(companion, 'last_drain_count', 0)),
      'intent_last_drain_ok': bool(getattr(companion, 'last_drain_ok', False)),
      'car_state_sources': tuple(int(frame.logMonoTime) for frame in getattr(owner, 'car_state_envelopes', ())),
      'car_state_queue_invalid': bool(getattr(owner, 'car_state_queue_invalid', False)),
      'intent_sm_update_time_s': float(sm.recv_time.get('aolIntentWire', 0)),
      'native_sm_update_time_s': float(sm.recv_time.get('aolSafetyWire', 0)),
      'current_proof': tuple(proof) if proof is not None else None,
      'rate_window': (avg.window_size, avg.index, avg.count, tuple(avg.buffer)),
      'worker_window': self.worker_window,
      'clock_alignment': (time.clock_gettime_ns(time.CLOCK_MONOTONIC),
                          time.clock_gettime_ns(time.CLOCK_BOOTTIME) if hasattr(time, 'CLOCK_BOOTTIME') else None,
                          time.clock_gettime_ns(time.CLOCK_MONOTONIC)),
    }
    # Only detached numeric/string/tuple/dict values enter the cross-thread queue.
    self.pending.append((metadata, tuple(self.history)))
    self.suppressed_peak = None

  @staticmethod
  def _rate_dict(values):
    names = ('frame', 'interval_s', 'count', 'sum_s', 'average_s', 'lagging', 'last_monitor_time_s', 'remaining_s', 'next_frame_time_s')
    result = dict(zip(names, values, strict=True))
    result['lag_threshold_s'] = result['interval_s'] * (1 / 0.9)
    return result

  def take_report(self):
    try:
      report, history = self.pending.popleft()
    except IndexError:
      return None
    sequence = report['report_sequence']
    report['queue_sequence_gap'] = max(0, sequence - self.delivered_sequence - 1)
    self.delivered_sequence = sequence
    frames = []
    totals = []
    worst = max(range(len(history)), key=lambda index: max(
      history[index][1][-1][1] - history[index][1][0][1], history[index][2]))
    for index, (context, points, between, before, after) in enumerate(history):
      totals.append((context[0], points[0][1], points[-1][1] - points[0][1],
                     points[-1][2] - points[0][2], context[-1], between))
      if index < len(history) - 3 and index != worst:
        continue
      phases = [(a[0] + '->' + b[0], b[1] - a[1], b[2] - a[2])
                for a, b in zip(points, points[1:], strict=False)]
      names = ('cycle_sequence', 'selected_source_ns', 'decision_ns', 'recv_one_source_ns',
               'intent_sm_ns', 'native_sm_ns', 'raw_intent_latest_ns', 'intent_step_drain_count',
               'axis_deferred', 'decision_source_ns', 'prior_output_proof', 'cycle_process_cpu_ns')
      frame = dict(zip(names, context, strict=True))
      frame.update(points=points, phases=phases, between_loops_ns=between,
                   rate_before=self._rate_dict(before), rate_after=self._rate_dict(after))
      frames.append(frame)
    report['frames'] = frames
    report['window_cycles'] = len(history)
    report['window_cycle_totals'] = totals
    report['window_cycle_columns'] = ('cycle_sequence', 'start_ns', 'wall_ns',
      'main_thread_cpu_ns', 'process_cpu_ns', 'between_loops_ns')
    size, index, count, buffer = report.pop('rate_window')
    report['rate_window_size'] = size
    report['rate_intervals_s'] = (buffer[index:] + buffer[:index]) if count == size else buffer[:count]
    report['phase_clock_columns'] = ('name', 'monotonic_ns', 'main_thread_cpu_ns')
    report['worker_clock_columns'] = ('monotonic_ns', 'worker_thread_cpu_ns')
    report['clock_alignment_columns'] = ('monotonic_before_ns', 'boottime_ns', 'monotonic_after_ns')
    report['proof_columns'] = ('session', 'source_ns', 'published_ns', 'deadline_ns', 'producer', 'epoch',
                               'desired_lateral', 'desired_longitudinal', 'active_lateral', 'active_longitudinal')
    report['phase_columns'] = ('from_to', 'wall_ns', 'main_thread_cpu_ns')
    return report


_PARAM_PHASES = {
  'ChestnutLoading': ('chestnut_loading_start', 'chestnut_loading_return'),
  'ChestnutActive': ('chestnut_active_start', 'chestnut_active_return'),
  'PrimeType': ('bookmark_prime_start', 'bookmark_prime_return'),
}


def timed_params_read(owner, key, boolean=False):
  """Observe one existing Params read without changing its value or failure."""
  read = owner.params.get_bool if boolean else owner.params.get
  timing = getattr(owner, 'loop_timing', None)
  phases = _PARAM_PHASES.get(key) if timing is not None else None
  if phases is None:
    return read(key)
  timing.mark(phases[0])
  value = read(key)
  timing.mark(phases[1])
  return value
