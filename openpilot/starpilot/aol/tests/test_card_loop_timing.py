"""Deterministic clocks for late events, ownership of snapshots and bounded emission."""
from typing import Any

from openpilot.starpilot.card_loop_timing import CardLoopTiming


class Clock:
  def __init__(self):
    self.wall = self.thread = self.process = 1

  def __call__(self):
    return self.wall, self.thread, self.process, self.wall + 1000

  def advance(self, wall, thread=0, process=0):
    self.wall += wall
    self.thread += thread
    self.process += process


def finish(timing, clock, duration, *, enabled=True, sequence=1):
  timing.begin()
  clock.advance(duration)
  timing.finish({'intent_sequence': sequence, 'source_car_state_ns': clock.wall + 1000}, enabled=enabled)


def test_exact_lease_threshold_and_initialization_do_not_emit():
  clock = Clock()
  timing = CardLoopTiming(clock)
  finish(timing, clock, timing.LIMIT_NS)
  finish(timing, clock, timing.LIMIT_NS + 1, enabled=False)
  assert timing.take_report() is None
  finish(timing, clock, timing.LIMIT_NS + 1)
  assert timing.take_report() is not None


def test_named_block_preserves_independent_clock_deltas_and_source_context():
  clock = Clock()
  timing = CardLoopTiming(clock)
  timing.begin()
  timing.mark('controller_apply_start')
  clock.advance(80_877_165, thread=3_000_000, process=9_000_000)
  timing.mark('controller_apply_end')
  timing.finish({'source_car_state_ns': 123, 'intent_sequence': 4}, enabled=True)
  report = timing.take_report()
  phase = next(p for p in report['frames'][0]['phases'] if p['to'] == 'controller_apply_end')
  assert phase == {'from': 'controller_apply_start', 'to': 'controller_apply_end',
                   'wall_ns': 80_877_165, 'thread_cpu_ns': 3_000_000, 'process_cpu_ns': 9_000_000}
  assert report['source_car_state_ns'] == 123 and report['intent_sequence'] == 4
  assert report['frames'][0]['start_boot_ns'] - report['frames'][0]['start_ns'] == 1000


def test_between_loops_pause_retains_both_source_frames():
  clock = Clock()
  timing = CardLoopTiming(clock)
  finish(timing, clock, 10_000_000, sequence=1)
  clock.advance(80_877_165)
  finish(timing, clock, 10_000_000, sequence=2)
  report = timing.take_report()
  assert report['between_loops_ns'] == 80_877_165
  assert [f['intent_sequence'] for f in report['frames']] == [1, 2]
  assert report['frames'][1]['end_ns'] - report['frames'][1]['start_ns'] == 10_000_000


def test_reporting_is_rate_limited_and_queue_is_bounded_if_logger_stalls():
  clock = Clock()
  timing = CardLoopTiming(clock)
  finish(timing, clock, 80_877_165, sequence=1)
  finish(timing, clock, 80_877_165, sequence=2)
  assert len(timing.pending) == 1
  clock.advance(timing.REPORT_INTERVAL_NS)
  finish(timing, clock, 80_877_165, sequence=3)
  clock.advance(timing.REPORT_INTERVAL_NS)
  finish(timing, clock, 80_877_165, sequence=4)
  assert len(timing.pending) == 2
  assert [timing.take_report()['intent_sequence'], timing.take_report()['intent_sequence']] == [3, 4]
  assert timing.dropped_reports == 1 and timing.take_report() is None


def test_frame_and_context_are_detached_before_worker_formatting():
  clock = Clock()
  timing = CardLoopTiming(clock)
  context = {'intent_sequence': 7}
  timing.begin()
  clock.advance(80_877_165)
  timing.finish(context, enabled=True)
  context['intent_sequence'] = 99
  finish(timing, clock, 10_000_000, sequence=8)
  report = timing.take_report()
  assert report['intent_sequence'] == report['frames'][0]['intent_sequence'] == 7
  assert report['frames'][0]['end_ns'] - report['frames'][0]['start_ns'] == 80_877_165


def test_mark_storage_is_bounded_but_end_clock_is_always_retained():
  clock = Clock()
  timing = CardLoopTiming(clock)
  timing.begin()
  for i in range(100):
    clock.advance(1_000_000)
    timing.mark(str(i))
  timing.finish({}, enabled=True)
  frame = timing.take_report()['frames'][0]
  assert len(frame['points']) == timing.MAX_MARKS
  assert frame['points'][-1][0] == 'loop_end'
  assert frame['end_ns'] - frame['start_ns'] == 100_000_000


def test_actual_card_thread_preserves_step_order_and_replay_disables_recorder(monkeypatch):
  from types import SimpleNamespace
  from openpilot.selfdrive.car import card as module

  class StopLoop(Exception):
    pass

  class SM(dict):
    seen = {'onroadEvents': True}
    logMonoTime = {'carControl': 11}

  class Worker:
    def __init__(self, **kwargs):
      pass

    def start(self):
      pass

    def join(self):
      pass

  for replay in (False, True):
    trace = []
    clock = Clock()
    timing = CardLoopTiming(clock)
    daemon: Any = module.Car.__new__(module.Car)
    daemon.aol_replay = True
    daemon.ioniq6_keepalive = None
    daemon.vehicle_startup = SimpleNamespace(owner=None, check=lambda trace=trace: trace.append('check'))
    daemon.CP = SimpleNamespace(passive=False)
    daemon.sm = SM(onroadEvents=[], carControl='command')
    daemon.aol_sequence = 1
    daemon.slc_producer_session = 'session'
    state = object()
    daemon.state_update = lambda trace=trace, state=state: (trace.append('receive') or state, None)
    daemon.state_publish = lambda cs, rd, trace=trace: trace.append('publish')

    def control(cs, command, *, state=state, trace=trace, daemon=daemon, clock=clock):
      assert cs is state and command == 'command'
      trace.append('apply')
      daemon.timing_mark('controller_apply_start')
      clock.advance(80_877_165)
      daemon.timing_mark('controller_apply_end')

    def monitor(trace=trace):
      trace.append('monitor')
      if trace.count('monitor') == 2:
        raise StopLoop

    daemon.controls_update = control
    daemon.rk = SimpleNamespace(monitor_time=monitor)
    monkeypatch.setattr(module, 'REPLAY', replay)
    monkeypatch.setattr(module, 'CardLoopTiming', lambda timing=timing: timing)
    monkeypatch.setattr(module.threading, 'Thread', Worker)
    monkeypatch.setattr(module.cloudlog, 'event', lambda *a, **k: (_ for _ in ()).throw(AssertionError('control-thread logging')))
    try:
      daemon.card_thread()
    except StopLoop:
      pass
    else:
      raise AssertionError('loop did not stop')
    assert trace == ['check', 'receive', 'publish', 'apply', 'monitor'] * 2
    assert daemon.CS_prev is state and daemon.initialized_prev is True
    assert (daemon.loop_timing is None) is replay
    report = timing.take_report()
    if replay:
      assert report is None
    else:
      assert report['source_control_ns'] == 11 and report['intent_sequence'] == 1
      assert any(p['to'] == 'controller_apply_end' and p['wall_ns'] == 80_877_165
                 for p in report['frames'][0]['phases'])


def test_actual_params_worker_emits_after_recorder_releases_frame(monkeypatch):
  from types import SimpleNamespace
  from openpilot.selfdrive.car import card as module

  class Once:
    calls = 0

    def is_set(self):
      self.calls += 1
      return self.calls > 1

  clock = Clock()
  timing = CardLoopTiming(clock)
  finish(timing, clock, 80_877_165)
  daemon: Any = module.Car.__new__(module.Car)
  daemon.loop_timing = timing
  daemon.params = SimpleNamespace(get_bool=lambda key: False)
  daemon.CP = SimpleNamespace(openpilotLongitudinalControl=False, pcmCruise=False)
  daemon.aol_card_intent = None
  daemon.v_cruise_helper = SimpleNamespace(intervals=None)
  daemon.read_slc_configuration = lambda: 'configuration'
  emitted = []
  monkeypatch.setattr(module.cloudlog, 'event', lambda name, **report: emitted.append((name, report)))
  monkeypatch.setattr(module, 'read_cruise_intervals', lambda *a, **k: 'intervals')
  monkeypatch.setattr(module.time, 'sleep', lambda _: None)
  daemon.params_thread(Once())
  assert len(emitted) == 1 and emitted[0][0] == 'card.loop_late'
  assert emitted[0][1]['frames'][0]['end_ns'] - emitted[0][1]['frames'][0]['start_ns'] == 80_877_165
  assert timing.take_report() is None
  assert daemon.slc_requested_configuration == 'configuration'
  assert daemon.v_cruise_helper.intervals == 'intervals'


def test_actual_recorder_cost_is_bounded_and_report_worker_formatting_is_measured():
  import json
  import os
  from pathlib import Path
  import time
  from openpilot.selfdrive.car.card import Car

  daemon = Car.__new__(Car)
  context = {'source_car_state_ns': 1, 'source_control_ns': 1, 'intent_sequence': 1}
  samples = {'disabled': [], 'enabled': []}
  for enabled in (False, True):
    timing = CardLoopTiming() if enabled else None
    daemon.loop_timing = timing
    for _ in range(20_000):
      start = time.perf_counter_ns()
      if timing is not None:
        timing.begin()
      for _ in range(32):
        daemon.timing_mark('cost')
      if timing is not None:
        timing.finish(context, enabled=True)
      samples['enabled' if enabled else 'disabled'].append(time.perf_counter_ns() - start)
  metrics = {}
  for name, rows in samples.items():
    rows.sort()
    metrics[name] = {str(p): rows[min(len(rows) - 1, int(len(rows) * p))] for p in (0.5, 0.95, 0.99)}
    metrics[name]['max'] = rows[-1]
  added = metrics['enabled']['0.99'] - metrics['disabled']['0.99']
  clock = Clock()
  timing = CardLoopTiming(clock)
  timing.begin()
  for _ in range(30):
    clock.advance(3_000_000)
    timing.mark('format')
  timing.finish(context, enabled=True)
  start = time.perf_counter_ns()
  payload = json.dumps(timing.take_report())
  metrics.update(added_p99_ns=added, worker_format_ns=time.perf_counter_ns() - start,
                 worker_payload_bytes=len(payload.encode()), iterations=20_000,
                 physical_scheduler_proof=False)
  output = os.environ.get('GM_PUBLIC_QUALIFICATION_OUTPUT')
  if output:
    (Path(output) / 'card-loop-overhead.json').write_text(json.dumps(metrics, indent=2) + '\n')
  assert added <= 500_000, metrics
  assert metrics['worker_payload_bytes'] <= 20_000, metrics
