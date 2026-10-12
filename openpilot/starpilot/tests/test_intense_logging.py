import gc

from openpilot.starpilot import intense_logging


def test_disabled_without_flag(monkeypatch, tmp_path):
  monkeypatch.setattr(intense_logging, 'FLAG_PATH', str(tmp_path / 'missing'))
  assert not intense_logging.enabled()
  assert intense_logging.loop_timing() is None
  assert intense_logging.start('test') is None


def test_loop_timing_uses_intense_limit(monkeypatch, tmp_path):
  flag = tmp_path / 'intense_logging'
  flag.touch()
  monkeypatch.setattr(intense_logging, 'FLAG_PATH', str(flag))
  timing = intense_logging.loop_timing(limit_ns=60_000_000)
  assert timing.detailed and timing.LIMIT_NS == 60_000_000
  assert intense_logging.loop_timing().LIMIT_NS == intense_logging.LOOP_LIMIT_NS


def test_gc_pauses_record_only_long_collections(monkeypatch):
  pauses = intense_logging.GcPauses()
  clock = iter([0, 1_000_000, 10_000_000, 20_000_000])
  monkeypatch.setattr(intense_logging.time, 'monotonic_ns', lambda: next(clock))
  pauses('start', {'generation': 0})
  pauses('stop', {'generation': 0, 'collected': 1})
  pauses('start', {'generation': 2})
  pauses('stop', {'generation': 2, 'collected': 7})
  assert len(pauses.pending) == 1
  _, pause_ns, generation, collected, _ = pauses.pending[0]
  assert (pause_ns, generation, collected) == (10_000_000, 2, 7)


def test_drain_logs_loop_and_gc_reports(monkeypatch):
  events = []
  monkeypatch.setattr(intense_logging.cloudlog, 'event', lambda name, **kw: events.append((name, kw)))
  timing = intense_logging.CardLoopTiming()
  timing.LIMIT_NS = 15_000_000
  clock = iter([(0, 0, 0, 0), (20_000_000, 1, 1, 0)])
  timing.clock = lambda: next(clock)
  timing.begin()
  timing.finish({'thread_id': 1}, enabled=True)
  logger = intense_logging.IntenseLogger('selfdrived', timing)
  logger.gc_pauses.pending.append((1, 6_000_000, 2, 3, 1))
  logger.drain()
  assert [name for name, _ in events] == ['selfdrived.loop_late', 'intense.gc_pause']
  assert events[1][1]['pause_ms'] == 6.0


def test_sched_waits_report_spikes_and_summary(monkeypatch):
  events = []
  monkeypatch.setattr(intense_logging.cloudlog, 'event', lambda name, **kw: events.append((name, kw)))
  stats = {'/a': [(100, 0), (5_000_000, 25_000_000)], '/b': [(0, 0), (1_000_000, 1_000_000)]}
  monkeypatch.setattr(intense_logging, '_read_schedstat', lambda path: stats[path].pop(0))
  sampler = intense_logging.SchedWaits()
  sampler.tasks = [('/a', 'selfdrived/selfdrived', 1), ('/b', 'card/card', 2)]
  sampler.next_refresh = sampler.next_summary = float('inf')
  sampler.sample()
  assert events == []
  sampler.next_summary = 0
  sampler.sample()
  spike, summary = events
  assert spike[0] == 'intense.sched_wait_spike'
  assert spike[1]['threads'] == [{'name': 'selfdrived/selfdrived', 'tid': 1, 'wait_ms': 25.0, 'cpu_ms': 5.0}]
  assert summary[0] == 'intense.sched_wait_summary'
  assert [t['name'] for t in summary[1]['threads']] == ['selfdrived/selfdrived', 'card/card']


def test_stop_removes_gc_callback():
  logger = intense_logging.IntenseLogger('test')
  gc.callbacks.append(logger.gc_pauses)
  logger.stop()
  assert logger.gc_pauses not in gc.callbacks


def test_set_enabled_round_trip(monkeypatch, tmp_path):
  monkeypatch.setattr(intense_logging, 'FLAG_PATH', str(tmp_path / 'intense_logging'))
  intense_logging.set_enabled(True)
  intense_logging.set_enabled(True)
  assert intense_logging.enabled()
  intense_logging.set_enabled(False)
  intense_logging.set_enabled(False)
  assert not intense_logging.enabled()
