"""Bounded observational Card timing; no logging or I/O on the control thread."""
from collections import deque
from collections.abc import Callable
from functools import wraps
from itertools import islice
import time


def _capture_only(method):
  """A diagnostic failure must not replace the control operation it observes."""
  @wraps(method)
  def capture(self, *args, **kwargs):
    try:
      return method(self, *args, **kwargs)
    except Exception as error:
      self.capture_errors += 1
      self.capture_error_type = type(error).__name__
      if method.__name__ in ('begin', 'mark', 'finish'):
        self.points = []
        self.previous = self.previous_end = None
        self.last_car_state_send_ns = None
      return None
  return capture


class CardLoopTiming:
  LIMIT_NS = 30_000_000
  REPORT_INTERVAL_NS = 5_000_000_000
  MAX_MARKS = 40
  INTENT_REPORT_INTERVAL_NS = 1_000_000_000
  MAX_INPUT_EVENTS = 16
  COMPACT_MARKS = frozenset(('can_receive_start', 'can_receive_end', 'can_decode_end', 'interface_update_end',
    'submaster_start', 'submaster_end', 'permission_and_cruise_end', 'state_update_end',
    'intent_send_start', 'intent_send_end', 'car_state_send_start', 'car_state_send_end',
    'controller_apply_start', 'controller_apply_end', 'sendcan_start', 'sendcan_end'))

  def __init__(self, clock=None, *, detailed=True, compact=False):
    self.capture_errors = 0
    self.receive_set: Callable[[bool], None] | None = None
    self.receive_take: Callable[[], dict] | None = None
    self.receive_status = 'disabled'
    self.receive_error_stage = ''
    self.can_receive_timing = None
    self.capture_error_type = ''
    self.capture_error_reported = (0, 0)
    self.capture_error_report_ns = None
    self.detailed = detailed
    self.compact = compact
    self.clock = clock or self._clock
    self.phase_clock = clock or (self._phase_clock if compact else self._clock)
    self.sink_errors = 0
    self.pending = deque(maxlen=2)
    self.output_pending = deque(maxlen=2)
    self.output_was_valid = False
    self.output_last_report_ns = None
    self.output_dropped = 0
    self.points = []
    self.loop_sequence = 0
    self.current_car_state_send_ns = self.last_car_state_send_ns = None
    self.previous = None
    self.previous_end = None
    self.last_report_ns = None
    self.dropped_reports = 0
    self.late_count = 0
    self.rate_suppressed = 0
    self.report_sequence = 0
    self.intent_pending = deque(maxlen=4)
    self.intent_sequence = 0
    self.intent_queue_full = 0
    self.intent_last_report_ns = None
    self.worker_current = None
    self.worker_previous = None
    self.worker_recent = deque(maxlen=2)

  def configure_receive(self, sock):
    """Optional native CAN capture; enable once before the settings worker."""
    if not self.detailed:
      return
    try:
      self.receive_set = sock.set_receive_timing
      self.receive_take = sock.take_receive_timing
      if not callable(self.receive_set) or not callable(self.receive_take):
        raise TypeError
      self.receive_set(True)
      self.receive_status = 'enabled'
    except Exception as error:
      self._receive_error(error, 'setup')

  def _receive_error(self, error, stage):
    self.capture_errors += 1
    self.capture_error_type = type(error).__name__
    self.receive_error_stage = stage
    self.receive_status = 'error'
    self.can_receive_timing = None
    if self.receive_set is not None:
      try:
        self.receive_set(False)
      except Exception as disable_error:
        self.capture_errors += 1
        self.capture_error_type = type(disable_error).__name__
    self.receive_set = self.receive_take = None

  def capture_receive(self, *, reset=False):
    """One reset before drain and one detached summary after; never receive CAN."""
    if reset:
      self.can_receive_timing = None
    if not self.detailed or self.receive_status != 'enabled':
      return
    try:
      take = self.receive_take
      if take is None:
        raise TypeError
      raw = take()
      if reset:
        return
      # The native API has fixed storage. Reject an incompatible shape rather
      # than retain an unbounded/mutable object on the control thread.
      counts = ('blocking_calls', 'nonblocking_calls', 'messages', 'nulls', 'invalid_clock_samples')
      totals = ('release', 'native', 'reacquire', 'copy', 'delete_release', 'delete_native', 'delete_reacquire')
      boundaries = ('before_release', 'native_entry', 'native_return', 'after_reacquire',
                    'before_delete_release', 'delete_entry', 'delete_return', 'after_delete_reacquire')
      if (not isinstance(raw, dict) or
          set(raw) != {*counts, 'schema_version', 'clock', 'enabled', 'totals_ns', 'boundary_names',
                       'slowest_blocking_ns', 'slowest_nonblocking_ns'} or
          raw['schema_version'] != 1 or raw['clock'] != 'MONOTONIC' or raw['enabled'] is not True or
          any(type(raw[name]) is not int or raw[name] < 0 for name in counts) or
          not isinstance(raw['totals_ns'], dict) or set(raw['totals_ns']) != set(totals) or
          any(type(raw['totals_ns'][name]) is not int or raw['totals_ns'][name] < 0 for name in totals) or
          tuple(raw['boundary_names']) != boundaries or
          any(not isinstance(raw[name], (tuple, list)) or len(raw[name]) != 8 or
              any(type(value) is not int or value < 0 for value in raw[name])
              for name in ('slowest_blocking_ns', 'slowest_nonblocking_ns'))):
        raise ValueError
      self.can_receive_timing = {**raw, 'totals_ns': dict(raw['totals_ns']),
        'boundary_names': boundaries, 'slowest_blocking_ns': tuple(raw['slowest_blocking_ns']),
        'slowest_nonblocking_ns': tuple(raw['slowest_nonblocking_ns'])}
    except Exception as error:
      self._receive_error(error, 'reset' if reset else 'snapshot')

  @staticmethod
  def _clock():
    # The clocks are sequential snapshots, not atomic scheduling observations.
    return (time.monotonic_ns(), time.thread_time_ns(), time.process_time_ns(),
            time.clock_gettime_ns(time.CLOCK_BOOTTIME) if hasattr(time, 'CLOCK_BOOTTIME') else 0)

  @staticmethod
  def _phase_clock():
    # Only the two clocks needed to separate work from off-CPU time at each phase.
    # Process/boot clocks remain available at frame boundaries, never interpolated.
    return time.monotonic_ns(), time.thread_time_ns(), None, None

  @_capture_only
  def begin(self):
    if not self.detailed:
      return
    self.current_car_state_send_ns = None
    self.loop_sequence += 1
    self.points = [('loop_start', *self.clock())]

  @_capture_only
  def mark(self, name):
    if self.detailed and (not self.compact or name in self.COMPACT_MARKS) and self.points and len(self.points) < self.MAX_MARKS - 1:
      point = (name, *self.phase_clock())
      self.points.append(point)
      if name == 'car_state_send_end':
        self.current_car_state_send_ns = point[1]

  @_capture_only
  def finish(self, context, *, enabled):
    if not self.detailed or not self.points:
      return
    context = {**context, 'loop_sequence': self.loop_sequence, 'capture_errors': self.capture_errors}
    self.points.append(('loop_end', *self.clock()))
    points = tuple(self.points)
    start, end = points[0][1], points[-1][1]
    between = start - self.previous_end[1] if self.previous_end is not None else 0
    send_interval = (self.current_car_state_send_ns - self.last_car_state_send_ns
                     if self.current_car_state_send_ns is not None and self.last_car_state_send_ns is not None else 0)
    previous_source = self.previous[0].get('source_car_state_ns', 0) if self.previous is not None else 0
    source = context.get('source_car_state_ns', 0)
    source_interval = source - previous_source if source and previous_source else 0
    context.update(car_state_send_interval_ns=send_interval, car_state_source_interval_ns=source_interval)
    late = max(end - start, between, send_interval, source_interval) > self.LIMIT_NS
    if self.current_car_state_send_ns is not None:
      self.last_car_state_send_ns = self.current_car_state_send_ns
    if enabled and late:
      self.late_count += 1
    eligible = self.last_report_ns is None or end - self.last_report_ns >= self.REPORT_INTERVAL_NS
    if enabled and late and not eligible:
      self.rate_suppressed += 1
    if enabled and late and eligible:
      self.report_sequence += 1
      if len(self.pending) == self.pending.maxlen:
        self.dropped_reports += 1
      # Detached immutable frame points; formatting and logging happen elsewhere.
      self.pending.append((context, self.previous, points, between,
        self.dropped_reports, self.report_sequence, self.late_count, self.rate_suppressed))
      self.last_report_ns = end
    self.previous = (context, points)
    self.previous_end = points[-1]
    self.points = []

  def take_report(self):
    try:
      context, previous, current, between, dropped, sequence, late_count, suppressed = self.pending.popleft()
    except IndexError:
      return None
    frames = []
    for frame in (previous, (context, current)):
      if frame is None:
        continue
      frame_context, points = frame
      frames.append({**frame_context, 'start_ns': points[0][1], 'end_ns': points[-1][1],
        'start_boot_ns': points[0][4], 'end_boot_ns': points[-1][4],
        'process_cpu_ns': points[-1][3] - points[0][3], 'points': points,
        'phases': [{'from': a[0], 'to': b[0], 'wall_ns': b[1] - a[1],
                    'thread_cpu_ns': b[2] - a[2],
                    'process_cpu_ns': b[3] - a[3] if a[3] is not None and b[3] is not None else None}
                   for a, b in zip(points, points[1:], strict=False)]})
    return {**context, 'between_loops_ns': between, 'dropped_reports': dropped,
            'queue_full_observations': dropped, 'report_sequence': sequence, 'late_cycles': late_count,
            'rate_suppressed': suppressed, 'frames': frames,
            'point_clock_order': ('MONOTONIC', 'THREAD_CPUTIME', 'PROCESS_CPUTIME', 'BOOTTIME'),
            'clock_pair_is_sequential': True, 'sink_errors': self.sink_errors, 'compact': self.compact}

  @_capture_only
  def observe_output(self, valid, co_ns, cs_ns, sm):
    previous = self.output_was_valid
    self.output_was_valid = valid
    if valid or not previous:
      return
    now = time.monotonic_ns()
    if self.output_last_report_ns is not None and now - self.output_last_report_ns < self.REPORT_INTERVAL_NS:
      self.output_dropped += 1
      return
    tracker = sm.freq_tracker['carControl']
    if len(self.output_pending) == self.output_pending.maxlen:
      self.output_dropped += 1
    # Scalar tuple detached from mutable receiver state; no formatting or I/O.
    self.output_pending.append((now, co_ns, cs_ns, sm.logMonoTime['carControl'],
      sm.seen['carControl'], sm.valid['carControl'], sm.alive['carControl'], sm.freq_ok['carControl'],
      sm.recv_time['carControl'], tracker.prev_time, tracker.min_freq, tracker.max_freq,
      tracker.avg_dt.count, tracker.avg_dt.get_average() if tracker.avg_dt.count else None,
      tracker.recent_avg_dt.count, tracker.recent_avg_dt.get_average() if tracker.recent_avg_dt.count else None,
      self.output_dropped))
    self.output_last_report_ns = now

  def take_output_report(self):
    try:
      values = self.output_pending.popleft()
    except IndexError:
      return None
    names = ('snapshot_ns', 'car_output_ns', 'source_car_state_ns', 'source_control_ns',
      'seen', 'valid', 'alive', 'freq_ok', 'receiver_time_s', 'previous_receiver_time_s',
      'min_frequency', 'max_frequency', 'average_count', 'average_dt_s',
      'recent_count', 'recent_average_dt_s', 'dropped_reports')
    report = dict(zip(names, values, strict=True))
    report['receiver_age_ns'] = report['snapshot_ns'] - int(report['receiver_time_s'] * 1e9)
    return report

  @_capture_only
  def worker_begin(self, stage):
    if not self.detailed:
      return
    self.worker_current = (stage, time.monotonic_ns(), time.thread_time_ns())

  @_capture_only
  def worker_end(self):
    current = self.worker_current
    if current is not None:
      self.worker_previous = (*current, time.monotonic_ns(), time.thread_time_ns())
      self.worker_recent.append(self.worker_previous)
      self.worker_current = None

  @_capture_only
  def intent_snapshot(self, intent):
    return (bool(intent.allowed_latch), bool(intent.pause_lateral), bool(intent.pause_longitudinal),
            getattr(intent, 'latch_clear_count', 0), getattr(intent, '_last_latch_edge_ns', 0),
            getattr(intent, '_main_held', False), getattr(intent, '_lkas_held', False),
            getattr(intent, '_gesture_neutral_seen', False))

  @_capture_only
  def observe_intent(self, intent, before, CS, sm, *, now_ns, source_can_ns, can_received_ns,
                     producer_session, intent_sequence, stage, fault_active, transport_reset,
                     native_rejection_ns, native_reset, native):
    after = self.intent_snapshot(intent)
    # Only state changes/actual clears retain inputs; no per-cycle serialization.
    if before[:4] == after[:4]:
      return
    self.intent_sequence += 1
    if len(self.intent_pending) == self.intent_pending.maxlen:
      self.intent_queue_full += 1
    buttons = CS.buttonEvents
    events = sm['onroadEvents']
    # Primitive, bounded snapshots only. No borrowed readers, Params reads or I/O.
    self.intent_pending.append({
      'transition_sequence': self.intent_sequence, 'snapshot_mono_ns': now_ns,
      'stage': stage, 'before': before, 'after': after,
      'state_field_order': ('allowed_latch', 'pause_lateral', 'pause_longitudinal', 'clear_count',
                            'last_edge_mono_ns', 'main_held', 'lkas_held', 'gesture_neutral_seen'),
      'clear_reason': getattr(intent, 'latch_clear_reason', '') if after[3] != before[3] else '',
      'source_can_boot_ns': source_can_ns, 'can_received_mono_ns': can_received_ns,
      'producer_session': producer_session, 'next_intent_sequence': intent_sequence,
      'source_control_ns': int(sm.logMonoTime['carControl']),
      'source_event_ns': int(sm.logMonoTime['onroadEvents']),
      'source_native_ns': int(sm.logMonoTime['aolSafetyWire']),
      'source_axis_ns': int(sm.logMonoTime['aolAxisState']),
      'event_updated': bool(sm.updated['onroadEvents']), 'event_valid': bool(sm.valid['onroadEvents']),
      'fault_active': fault_active, 'transport_reset': transport_reset,
      'native_reset': native_reset, 'native_rejection_ns': native_rejection_ns,
      'native': None if native is None else (int(native.observedMonoTime), bool(native.requestedLateral), bool(native.lateralAllowed)),
      'can_valid': bool(CS.canValid), 'can_timeout': bool(CS.canTimeout),
      'acc_faulted': bool(CS.accFaulted), 'steer_fault_permanent': bool(CS.steerFaultPermanent),
      'brake_pressed': bool(CS.brakePressed), 'gas_pressed': bool(CS.gasPressed),
      'steering_pressed': bool(CS.steeringPressed), 'cruise_available': bool(CS.cruiseState.available),
      'cruise_enabled': bool(CS.cruiseState.enabled), 'observed_settings_enabled': bool(intent.settings.enabled),
      'button_count': len(buttons), 'buttons': tuple((int(b.type.raw), bool(b.pressed)) for b in islice(buttons, self.MAX_INPUT_EVENTS)),
      'event_count': len(events), 'events': tuple((int(e.name.raw), bool(e.immediateDisable), bool(e.softDisable))
                                                for e in islice(events, self.MAX_INPUT_EVENTS)),
      'queue_full_observations': self.intent_queue_full,
    })

  def take_intent_report(self):
    if not self.intent_pending:
      return None
    now = time.monotonic_ns()
    if self.intent_last_report_ns is not None and now - self.intent_last_report_ns < self.INTENT_REPORT_INTERVAL_NS:
      return None
    try:
      report = self.intent_pending.popleft()
    except IndexError:
      return None
    self.intent_last_report_ns = now
    return report

  def take_capture_error_report(self):
    if (self.capture_errors, self.sink_errors) == self.capture_error_reported:
      return None
    now = time.monotonic_ns()
    if self.capture_error_report_ns is not None and now - self.capture_error_report_ns < self.REPORT_INTERVAL_NS:
      return None
    self.capture_error_report_ns = now
    self.capture_error_reported = (self.capture_errors, self.sink_errors)
    return {'capture_errors': self.capture_errors, 'sink_errors': self.sink_errors, 'last_error_type': self.capture_error_type,
            'snapshot_mono_ns': now}

  def flush_reports(self, emit):
    # Only called by the settings worker. A broken diagnostic sink must never
    # stop settings refresh, and no exception message or traceback is retained.
    try:
      for name, take in (('card.loop_late', self.take_report),
                         ('card.output_invalid', self.take_output_report),
                         ('card.aol_intent_transition', self.take_intent_report),
                         ('card.diagnostic_capture_error', self.take_capture_error_report)):
        report = take()
        if report is not None:
          emit(name, error=name != 'card.aol_intent_transition', **report)
    except Exception:
      self.sink_errors += 1
