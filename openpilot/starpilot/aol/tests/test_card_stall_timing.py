"""Bounded, exception-isolated Card observations never grant authority."""
from contextlib import ExitStack
from types import SimpleNamespace
from typing import Any

import pytest

from openpilot.starpilot.card_stall_timing import CardStallTiming

BASE = 10_000_000_000
MS = 1_000_000


class Clock:
  def __init__(self):
    self.wall = BASE
    self.cpu = 0
    self.calls = 0

  def __call__(self):
    self.calls += 1
    return self.wall, self.cpu

  def advance(self, delta, cpu=0):
    self.wall += delta
    self.cpu += cpu


class Socket:
  def __init__(self):
    self.enabled = False
    self.takes = 0

  def enable_receive_timing(self, enabled):
    self.enabled = enabled

  def take_receive_timing(self):
    self.takes += 1
    return (), 0


def recorder():
  clock = Clock()
  return CardStallTiming(Socket(), clock=clock), clock


def frame(timing, clock, delta, source=None, session='producer'):
  timing.begin()
  clock.advance(delta)
  timing.mark('car_state_send_end')
  timing.published(clock.wall if source is None else source, session)
  timing.finish()


def report(timing):
  result = []
  timing.last_attempt = None
  timing.flush(lambda *args, **kwargs: result.append(kwargs))
  assert len(result) == 1
  return result[0]


def test_cross_loop_tail_and_head_gap_is_captured_before_loop_end():
  timing, clock = recorder()
  timing.begin()
  clock.advance(MS)
  timing.published(clock.wall, 'producer')
  clock.advance(19 * MS)
  timing.mark('controller_apply_end')
  timing.finish()
  timing.begin()
  clock.advance(18 * MS, cpu=2 * MS)
  timing.mark('submaster_end')
  timing.published(clock.wall, 'producer')
  result = report(timing)
  assert result['source_gap_ns'] == result['send_gap_ns'] == 37 * MS
  assert result['previous_publication_frame_retained'] and not result['current_frame_complete']
  assert result['previous_frame'][-1][0] == 'loop_end'
  assert result['current_frame'][-1][0] == 'submaster_end'
  assert result['current_frame'][-1][2] - result['current_frame'][0][2] == 2 * MS
  saved = result['current_frame']
  for _ in range(4):
    frame(timing, clock, MS)
  assert result['current_frame'] == saved and timing.socket.takes == 1


@pytest.mark.parametrize('extra, emitted', [(0, False), (1, True)])
def test_strict_threshold(extra, emitted):
  timing, clock = recorder()
  frame(timing, clock, MS)
  frame(timing, clock, 30 * MS + extra)
  assert bool(timing.pending) == emitted


@pytest.mark.parametrize('source_gap, send_gap', [(37 * MS, 21 * MS), (14 * MS, 33 * MS)])
def test_source_and_send_clocks_remain_separate(source_gap, send_gap):
  timing, clock = recorder()
  frame(timing, clock, MS, source=BASE)
  frame(timing, clock, send_gap, source=BASE + source_gap)
  result = report(timing)
  assert result['source_gap_ns'] == source_gap and result['send_gap_ns'] == send_gap
  assert result['source_clock'] == 'CLOCK_MONOTONIC' and result['clock'] == 'CLOCK_MONOTONIC'
  assert len(result['clock_mapping_mono_boot_mono']) == 3


def test_sessions_missing_sources_and_clock_reversal_reset_baseline():
  timing, clock = recorder()
  frame(timing, clock, MS)
  frame(timing, clock, 40 * MS, session='replacement')
  frame(timing, clock, 40 * MS, source=0, session='replacement')
  frame(timing, clock, 40 * MS, session='replacement')
  clock.wall -= 100 * MS
  frame(timing, clock, MS, session='replacement')
  assert not timing.pending
  frame(timing, clock, 31 * MS, session='replacement')
  assert report(timing)['source_gap_ns'] == 31 * MS


def test_bounds_throttle_queue_full_and_quiet_loss_summary():
  timing, clock = recorder()
  frame(timing, clock, MS)
  frame(timing, clock, 31 * MS)
  frame(timing, clock, 31 * MS)
  frame(timing, clock, timing.INTERVAL_NS)
  assert len(timing.pending) == 1
  assert timing.late_count == 3 and timing.throttled_count == 1 and timing.queue_full_count == 1
  for _ in range(100):
    timing.mark('can_receive_end')
  assert max(timing.lengths) == timing.MAX_MARKS and timing.omitted_marks > 0
  result = report(timing)
  assert result['counters']['queue_full_count'] == 1
  timing.errors += 1
  result = report(timing)
  assert 'source_gap_ns' not in result and result['counters']['capture_errors'] == 1
  assert len(timing.frames) == 2 and all(len(f) == timing.MAX_MARKS for f in timing.frames)


def test_nonpublishing_frames_and_worker_snapshot_are_explicit():
  timing, clock = recorder()
  frame(timing, clock, MS)
  timing.worker_mark('settings_start')
  for _ in range(3):
    timing.begin()
    clock.advance(10 * MS)
    timing.finish()
  frame(timing, clock, MS)
  old = timing.worker
  timing.worker_mark('settings_end')
  result = report(timing)
  assert result['nonpublishing_frames'] == 3 and not result['previous_publication_frame_retained']
  assert result['worker_progress'] == old


def test_missing_native_api_is_reported_and_python_capture_remains_honest():
  clock = Clock()
  timing = CardStallTiming(object(), clock=clock)
  assert not timing.native_available
  result = report(timing)
  assert not result['native_available'] and result['error']
  frame(timing, clock, MS)
  frame(timing, clock, 31 * MS)
  result = report(timing)
  assert result['native'] is None and not result['native_available']


def test_clock_snapshot_and_logging_failures_do_not_escape(monkeypatch):
  timing, clock = recorder()
  def fail(*args, **kwargs):
    raise RuntimeError('observer failure')
  timing.clock = fail
  timing.begin()
  timing.mark('can_receive_end')
  timing.finish()
  timing.published(BASE, 'producer')
  timing.worker_mark('settings_start')
  assert timing.errors == 5
  timing.clock = clock
  frame(timing, clock, MS)
  timing.socket.take_receive_timing = fail
  frame(timing, clock, 31 * MS)
  assert timing.errors == 6
  monkeypatch.setattr('openpilot.starpilot.card_stall_timing.time.monotonic_ns', lambda: clock.wall)
  for _ in range(100):
    timing.flush(fail)
  assert timing.log_errors == 1
  clock.advance(timing.INTERVAL_NS)
  timing.flush(fail)
  assert timing.log_errors == 2


def test_unselected_marks_do_not_read_clocks():
  timing, clock = recorder()
  before = clock.calls
  for _ in range(100):
    timing.mark('unselected')
  assert clock.calls == before


@pytest.mark.parametrize('full_op', [False, True])
def test_actual_card_publication_bytes_and_order_are_unchanged(full_op):
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup, OpenpilotPrefix():
    cleanup.callback(case.doCleanups)
    sd, _, step, daemon, _ = case._ioniq_availability_callers(full_op=full_op)
    axis, _, command = step(2)
    assert axis.lateralActive and command.latActive and axis.longitudinalActive == full_op
    state = fixture.car_state()
    daemon.car_params_published = True
    daemon.wheel_commands = ()
    daemon.initialized_prev = True
    daemon.timing_thread_id = 7
    initial_sequence = daemon.aol_sequence
    results = []
    for active in (False, True):
      timing, clock = recorder()
      clock.wall = BASE + 20 * MS
      daemon.stall_timing = timing if active else None
      daemon.aol_sequence = initial_sequence
      output = []
      daemon.pm = SimpleNamespace(send=lambda name, msg, output=output: output.append((name, msg.to_bytes())))
      timing.begin()
      daemon.state_publish(state, None)
      timing.finish()
      results.append(output)
      if active:
        assert timing.last_publication[1] == BASE + 20 * MS
    assert results[0] == results[1]
    services = [name for name, _ in results[1]]
    assert services.index('carOutput') < services.index('aolIntentWire') < services.index('carState')
    assert sd.aol_axis_decision.lateral_active and sd.aol_axis_decision.longitudinal_active == full_op


def test_failed_send_does_not_advance_successful_publication_baseline():
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup, OpenpilotPrefix():
    cleanup.callback(case.doCleanups)
    _, _, _, daemon, _ = case._ioniq_availability_callers(full_op=False)
    timing, clock = recorder()
    daemon.stall_timing = timing
    daemon.car_params_published = True
    daemon.timing_thread_id = 7
    timing.begin()
    def send(name, unused):
      if name == 'carState':
        raise RuntimeError('send failed')
    daemon.pm = SimpleNamespace(send=send)
    with pytest.raises(RuntimeError, match='send failed'):
      daemon.state_publish(fixture.car_state(), None)
    assert timing.last_publication is None and not timing.pending




@pytest.mark.parametrize('replay, aol, long_profile, expected', [
  (False, True, True, True), (True, True, True, False),
  (False, False, True, False), (False, True, False, False),
])
def test_actual_card_thread_gate_uses_configured_profile_not_active_long(replay, aol, long_profile, expected, monkeypatch):
  import threading
  from openpilot.selfdrive.car import card as module
  from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate
  class StopLoop(Exception):
    pass
  class Worker:
    def __init__(self, **unused):
      pass
    def start(self):
      pass
    def join(self):
      pass
  _, cp = candidate(True)
  cp.safetyConfigs[-1].safetyParam |= 0x0800
  if not long_profile:
    cp.openpilotLongitudinalControl = False
  daemon: Any = module.Car.__new__(module.Car)
  daemon.CP, daemon.aol_replay = cp, aol
  daemon.can_sock = Socket()
  daemon.ioniq6_keepalive = None
  daemon.vehicle_startup = SimpleNamespace(check=lambda: None)
  def stop():
    raise StopLoop
  daemon.step = stop
  monkeypatch.setattr(module, 'REPLAY', replay)
  monkeypatch.setattr(module, 'threading', SimpleNamespace(Thread=Worker, Event=threading.Event, get_native_id=lambda: 7))
  with pytest.raises(StopLoop):
    daemon.card_thread()
  assert (daemon.stall_timing is not None) == expected


def test_existing_card_worker_continues_settings_after_diagnostic_logger_error(monkeypatch):
  import threading
  from openpilot.selfdrive.car import card as module
  timing, clock = recorder()
  frame(timing, clock, MS)
  frame(timing, clock, 31 * MS)
  daemon: Any = module.Car.__new__(module.Car)
  daemon.stall_timing, daemon.loop_timing = timing, None
  daemon.CP = SimpleNamespace(openpilotLongitudinalControl=True, pcmCruise=False)
  daemon.aol_card_intent = SimpleNamespace(settings=None)
  daemon.v_cruise_helper = SimpleNamespace(intervals=None)
  reads = []
  daemon.params = SimpleNamespace(get_bool=lambda key: reads.append(key) or False)
  daemon.read_slc_configuration = lambda: 'configuration'
  stopped = threading.Event()
  def fail(*unused, **kwargs):
    raise RuntimeError('diagnostic logger unavailable')
  monkeypatch.setattr(module, 'cloudlog', SimpleNamespace(event=fail))
  monkeypatch.setattr(module, 'drop_realtime', lambda: None)
  monkeypatch.setattr(module, 'set_core_affinity', lambda cores: None)
  monkeypatch.setattr(module, 'read_settings', lambda params: 'aol')
  monkeypatch.setattr(module, 'read_cruise_intervals', lambda *args, **kwargs: 'intervals')
  monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=lambda: 10., sleep=lambda duration: stopped.set()))
  daemon.params_thread(stopped)
  assert reads == ['IsMetric', 'ExperimentalMode']
  assert daemon.aol_card_intent.settings == 'aol' and daemon.v_cruise_helper.intervals == 'intervals'
  assert timing.log_errors == 1 and timing.worker[0] == 'settings_end'




@pytest.mark.parametrize('hook', ['mark', 'published'])
def test_added_publication_hooks_cannot_stop_original_outputs(hook):
  from openpilot.common.prefix import OpenpilotPrefix
  from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  def fail(*args, **kwargs):
    raise RuntimeError('injected observer failure')
  with ExitStack() as cleanup, OpenpilotPrefix():
    cleanup.callback(case.doCleanups)
    _, _, _, daemon, _ = case._ioniq_availability_callers(full_op=False)
    daemon.car_params_published = True
    daemon.wheel_commands = ()
    daemon.stall_timing = SimpleNamespace(mark=lambda name: None, published=lambda *args: None)
    setattr(daemon.stall_timing, hook, fail)
    output = []
    daemon.pm = SimpleNamespace(send=lambda name, msg: output.append(name))
    daemon.state_publish(fixture.car_state(), None)
    assert 'carState' in output and 'carOutput' in output


@pytest.mark.parametrize('hook', ['begin', 'finish', 'constructor'])
def test_added_loop_hooks_cannot_interrupt_control_order(hook, monkeypatch):
  import threading
  from openpilot.selfdrive.car import card as module
  class StopLoop(Exception):
    pass
  class Worker:
    def __init__(self, **kwargs):
      pass
    def start(self):
      pass
    def join(self):
      pass
  trace = []
  daemon: Any = module.Car.__new__(module.Car)
  daemon.aol_replay = True
  daemon.ioniq6_keepalive = None
  daemon.CP = object()
  daemon.can_sock = Socket()
  daemon.vehicle_startup = SimpleNamespace(check=lambda: trace.append('check'))
  daemon.step = lambda: trace.append('step')
  def monitor():
    trace.append('monitor')
    if trace.count('monitor') == 2:
      raise StopLoop
  daemon.rk = SimpleNamespace(monitor_time=monitor)
  def fail(*args):
    raise RuntimeError('observer failure')
  timing = SimpleNamespace(begin=lambda: None, finish=lambda: None, mark=lambda name: None)
  if hook != 'constructor':
    setattr(timing, hook, fail)
  monkeypatch.setattr(module, 'REPLAY', False)
  monkeypatch.setattr(module, 'ioniq6_long_eligible', lambda cp: True)
  monkeypatch.setattr(module, 'CardStallTiming', fail if hook == 'constructor' else lambda socket: timing)
  monkeypatch.setattr(module, 'CardLoopTiming', lambda **kwargs: SimpleNamespace(detailed=False))
  monkeypatch.setattr(module, 'threading', SimpleNamespace(Thread=Worker, Event=threading.Event, get_native_id=lambda: 7))
  with pytest.raises(StopLoop):
    daemon.card_thread()
  assert trace == ['check', 'step', 'monitor'] * 2


@pytest.mark.parametrize('hook', ['worker_mark', 'flush'])
def test_worker_hooks_cannot_stop_settings(hook, monkeypatch):
  import threading
  from openpilot.selfdrive.car import card as module
  daemon: Any = module.Car.__new__(module.Car)
  def fail(*args):
    raise RuntimeError('observer failure')
  daemon.stall_timing = SimpleNamespace(worker_mark=lambda *args: None, flush=lambda *args: None)
  setattr(daemon.stall_timing, hook, fail)
  daemon.loop_timing = None
  daemon.CP = SimpleNamespace(openpilotLongitudinalControl=False, pcmCruise=False)
  daemon.aol_card_intent = None
  daemon.v_cruise_helper = SimpleNamespace(intervals=None)
  reads = []
  daemon.params = SimpleNamespace(get_bool=lambda key: reads.append(key) or False)
  daemon.read_slc_configuration = lambda: 'configuration'
  stopped = threading.Event()
  monkeypatch.setattr(module, 'drop_realtime', lambda: None)
  monkeypatch.setattr(module, 'set_core_affinity', lambda cores: None)
  monkeypatch.setattr(module, 'read_cruise_intervals', lambda *args, **kwargs: 'intervals')
  monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=lambda: 10., sleep=lambda duration: stopped.set()))
  daemon.params_thread(stopped)
  assert reads == ['IsMetric', 'ExperimentalMode'] and daemon.v_cruise_helper.intervals == 'intervals'


def test_can_summary_is_bounded_and_detached_without_payload_copy():
  timing, clock = recorder()
  timing.begin()
  raw = [b'can'] * 100
  decoded = [(i + BASE, [(1, b'abc', 0)] * 3) for i in range(100)]
  timing.observe_can(raw, decoded)
  assert timing.can_summaries[timing.index] == (100, 64, 192, 192, BASE, BASE + 63)
  timing.published(BASE, 'producer')
  timing.finish()
  frame(timing, clock, 31 * MS)
  result = report(timing)
  raw.clear()
  decoded.clear()
  assert result['previous_can'] == (100, 64, 192, 192, BASE, BASE + 63)
  assert result['can_source_clock'] == 'CLOCK_BOOTTIME'


def test_actual_receive_observer_failure_preserves_can_and_original_interface_error(monkeypatch):
  from openpilot.selfdrive.car import card as module
  daemon: Any = module.Car.__new__(module.Car)
  daemon.can_sock = object()
  raw = [b'raw']
  decoded = [(BASE, [(1, b'data', 0)])]
  seen = []
  def observer_fail(*args):
    raise RuntimeError('observer failure')
  def original_update(batch):
    seen.append(batch)
    raise ValueError('original interface exception')
  daemon.stall_timing = SimpleNamespace(mark=lambda name: None, observe_can=observer_fail)
  daemon.CI = SimpleNamespace(update=original_update)
  monkeypatch.setattr(module.messaging, 'drain_sock_raw', lambda socket, **kwargs: raw)
  monkeypatch.setattr(module, 'can_capnp_to_list', lambda batch: decoded if batch is raw else None)
  with pytest.raises(ValueError, match='original interface exception'):
    daemon.state_update()
  assert seen == [decoded] and seen[0] is decoded
