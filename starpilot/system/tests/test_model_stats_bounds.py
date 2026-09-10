"""Finite synthetic review regressions; no native daemon/device required."""
import json
from types import SimpleNamespace as NS
from unittest.mock import patch

import pytest
from openpilot.starpilot.common.model_stats import Reducer, Sample, parse_identity
from openpilot.starpilot.common.model_stats_store import Store, read_stats
from openpilot.starpilot.system import model_statsd as observer

OWNER = parse_identity(json.dumps({'version': 1, 'roles': [{'modelId': 'test', 'artifact': 'test', 'backend': 'comma'}]}))

@pytest.mark.parametrize('complete', [False, True])
def test_gap_finalizes_without_sample(tmp_path, complete):
  r = Reducer()
  r.update(Sample(1, OWNER, 10, enabled=True, lat=True))
  r.update(Sample(1.1, OWNER, 10, enabled=True, lat=True))
  store = Store(tmp_path / 'stats.sqlite')
  store.checkpoint('drive', 100, r.snapshot(), now=101)
  revision, freshness = r.sequence, r.last_t
  r.break_stream()
  r.break_stream()
  assert r.sequence == revision + 1
  assert r.last_t == freshness
  store.checkpoint('drive', 100, r.snapshot(), complete=complete, now=102)
  row = store.db.execute('SELECT gaps, state, updated FROM drives').fetchone()
  assert row[0] == 1 and json.loads(row[1])['previous'] is None
  assert row[2] == 101  # a state revision is not fresh telemetry
  assert read_stats(store.path)['models']['test']['stats']['incomplete']
  store.close()

@pytest.mark.parametrize('before,after,count', [
  ((False, True), (True, False), 0), ((False, True), (True, True), 0),
  ((False, True), (False, False), 1), ((True, False), (False, True), 1),
  ((True, True), (False, True), 1), ((True, False), (False, False), 1),
])
def test_assistance_transition_matrix(before, after, count):
  r = Reducer()
  for t, (enabled, aol) in zip((1, 1.1), (before, after)):
    r.update(Sample(t, OWNER, 10, enabled=enabled, aol=aol, lat=True))
  assert sum(row['disengagements'] for row in r.metrics.values()) == count


@pytest.mark.parametrize('flags,expected', [
  ([(False, True), (True, True), (True, False)], 0),
  # If services actually expose an off sample before full engagement, policy
  # counts that observed off transition; do not invent handover smoothing.
  ([(False, True), (False, False), (True, False)], 1),
])
def test_asynchronously_observed_handover(flags, expected):
  r = Reducer()
  for i, (enabled, aol) in enumerate(flags):
    r.update(Sample(1 + i * .1, OWNER, 10, enabled=enabled, aol=aol, lat=True))
  assert sum(row['disengagements'] for row in r.metrics.values()) == expected


class Socket:
  def __init__(self, count=None, size=64):
    self.remaining, self.size, self.calls = count, size, 0
  def receive(self, non_blocking):
    assert non_blocking
    self.calls += 1
    if self.remaining == 0:
      return None
    if self.remaining is not None:
      self.remaining -= 1
    return b'x' * self.size

@pytest.mark.parametrize('count', [12001, None])
def test_transport_bounded_and_fair(count):
  buffer = observer.BoundedEvents()
  sockets = {Socket(count): name for name in observer.SERVICES}
  decoded = []
  def decode(raw):
    decoded.append(len(raw))
    return NS(logMonoTime=10**18)
  assert not buffer.receive(sockets, decode, clock=lambda: 1)
  assert buffer.yield_reason == "message_budget"
  assert sum(s.calls for s in sockets) <= observer.MAX_TICK_MESSAGES
  assert max(s.calls for s in sockets) - min(s.calls for s in sockets) <= 1
  assert len(decoded) <= observer.MAX_TICK_MESSAGES
  assert len(buffer.pending) <= observer.MAX_PENDING_EVENTS
  assert buffer.bytes <= observer.MAX_PENDING_BYTES


def test_oversize_is_rejected_before_decode():
  buffer = observer.BoundedEvents()
  sock = Socket(1, observer.MAX_EVENT_BYTES + 1)
  assert buffer.receive({sock: 'carState'}, lambda _: pytest.fail('oversize decoded'))
  assert not buffer.pending and buffer.bytes == 0


def test_deadline_returns_and_rotates_first_socket():
  buffer = observer.BoundedEvents()
  sockets = {Socket(): name for name in observer.SERVICES}
  for _ in range(len(sockets)):
    times = iter([0, 0, 1])
    assert not buffer.receive(sockets, lambda _: NS(logMonoTime=1), clock=lambda: next(times))
    assert buffer.yield_reason == "time_budget"
  assert all(s.calls == 1 for s in sockets)


def test_many_drive_outage_is_bounded_and_reported(tmp_path):
  def fail():
    raise OSError('synthetic outage')
  q = observer.Checkpoints(fail)
  r = Reducer()
  with patch('logging.exception'):
    for i in range(300):
      q.submit(str(i), i, r.snapshot(), complete=True)
      q.flush(i * 31)
  assert len(q.pending) <= observer.MAX_CHECKPOINTS
  assert q.pending_bytes <= observer.MAX_CHECKPOINT_BYTES
  assert q.suspended
  q.factory = lambda: Store(tmp_path / 'stats.sqlite')
  assert q.flush(10000)
  summary = read_stats(tmp_path / 'stats.sqlite')
  assert summary['coverageLoss']
  assert summary['trackingStatus'] == 'resource_limited'
  q.store.close()


def test_checkpoint_byte_cap_and_coalescing():
  q = observer.Checkpoints()
  r = Reducer()
  assert q.submit('drive', 1, r.snapshot())
  assert q.submit('drive', 1, r.snapshot())
  assert len(q.pending) == 1
  huge = r.snapshot() | {'extra': 'x' * observer.MAX_CHECKPOINT_BYTES}
  assert not q.submit('drive', 1, huge)
  assert q.pending_bytes <= observer.MAX_CHECKPOINT_BYTES
  assert q.suspended and len(q.pending) == 1


def test_heap_high_water_and_byte_budget_before_cleanup():
  real_push = observer.heapq.heappush
  maximum = [0, 0]
  buffer = observer.BoundedEvents()
  def push(heap, item):
    real_push(heap, item)
    maximum[0] = max(maximum[0], len(heap))
    maximum[1] = max(maximum[1], sum(row[4] for row in heap))
  sockets = {Socket(12001): 'carState'}
  with patch.object(observer.heapq, 'heappush', push):
    assert not buffer.receive(sockets, lambda _: NS(logMonoTime=1), clock=lambda: 1)
  assert maximum[0] == observer.MAX_TICK_MESSAGES
  assert maximum[1] <= observer.MAX_PENDING_BYTES
  # Across ticks, future timestamps cannot evade the retained heap cap.
  maximum[:] = [0, 0]
  with patch.object(observer.heapq, 'heappush', push):
    for _ in range(30):
      buffer.receive({Socket(100): 'carState'}, lambda _: NS(logMonoTime=10**18), clock=lambda: 1)
  assert maximum[0] <= observer.MAX_PENDING_EVENTS
  assert maximum[1] <= observer.MAX_PENDING_BYTES
  calls = []
  buffer.clear()
  assert not buffer.receive({Socket(size=observer.MAX_EVENT_BYTES): 'carState'},
                        lambda raw: (calls.append(len(raw)), NS(logMonoTime=1))[1], clock=lambda: 1)
  assert sum(calls) <= observer.MAX_TICK_BYTES


def test_decoded_size_budget_before_heap_insertion():
  buffer = observer.BoundedEvents()
  assert buffer.receive({Socket(1): 'carState'}, lambda _: NS(logMonoTime=1, text='x' * observer.MAX_EVENT_BYTES))
  assert not buffer.pending


@pytest.mark.parametrize('offroad', [False, True])
@pytest.mark.parametrize('outage', [False, True])
def test_main_overflow_then_finalize_without_carstate(tmp_path, monkeypatch, offroad, outage):
  import sys
  import types
  import openpilot.starpilot.common.model_stats_store as store_module
  from collections import deque
  queues, messages, handlers, writers = {}, {}, {}, []
  clock = [100.0]
  ticks = [0]
  class QueuedSocket:
    def __init__(self, name):
      self.queue = queues[name] = deque()
    def receive(self, non_blocking):
      return self.queue.popleft() if self.queue else None
  def put(name, data):
    key = str(len(messages)).encode().ljust(64, b' ')
    messages[key] = NS(logMonoTime=round((clock[0] - .15) * 1e9) + int(name == 'carState'), valid=True, **{name: data})
    queues[name].append(key)
  def frame():
    for name, data in {
      'deviceState': NS(started=True), 'carControl': NS(latActive=True, longActive=True),
      'selfdriveState': NS(enabled=True), 'starpilotCarState': NS(alwaysOnLateralEnabled=False),
      'modelV2': NS(), 'starpilotModelV2': NS(modelMonoTime=round((clock[0] - .15) * 1e9), runtimeIdentity=OWNER),
      'carState': NS(vEgo=10, canValid=True, gearShifter='drive', steeringPressed=False, brakePressed=False, gasPressed=False),
    }.items():
      put(name, data)
    if outage:
      put('carState', NS(vEgo=10, canValid=True, gearShifter='drive', steeringPressed=False, brakePressed=False, gasPressed=False))
      messages[queues['carState'][-1]].logMonoTime += 10_000_000
  class Poller:
    def poll(self, timeout):
      ticks[0] += 1
      clock[0] += .2
      if ticks[0] <= 2:
        frame()
      elif ticks[0] == 3:
        queues['carState'].append(b'x' * (observer.MAX_EVENT_BYTES + 1))
      elif ticks[0] == 4 and offroad:
        put('deviceState', NS(started=False))
      else:
        handlers[observer.signal.SIGTERM]()
      assert ticks[0] <= 5
      return list(queues)
  fake = types.ModuleType('cereal.messaging')
  fake.Poller = Poller
  fake.sub_sock = lambda name, **kwargs: QueuedSocket(name)
  cereal = types.ModuleType('cereal')
  cereal.messaging = fake
  monkeypatch.setitem(sys.modules, 'cereal', cereal)
  monkeypatch.setitem(sys.modules, 'cereal.messaging', fake)
  path = tmp_path / 'stats.sqlite'
  monkeypatch.setattr(store_module, 'DEFAULT_PATH', path)
  original = observer.Checkpoints
  def writer():
    result = original(lambda: Store(path))
    if outage:
      monkeypatch.setattr(observer, 'MAX_CHECKPOINTS', 1)
      def unavailable():
        raise OSError('synthetic storage outage')
      result.factory = unavailable
      result.submit('earlier', 1, Reducer().snapshot(), complete=True)
    writers.append(result)
    return result
  sleeps = [0]
  def sleep(_):
    sleeps[0] += 1
    assert sleeps[0] <= 3
    clock[0] += 31
    writers[0].factory = lambda: Store(path)
    if sleeps[0] == 3:
      handlers[observer.signal.SIGTERM]()
  monkeypatch.setattr(observer.time, 'sleep', sleep)
  monkeypatch.setattr(observer, 'Checkpoints', writer)
  monkeypatch.setattr(observer, 'decode_event', lambda raw: messages[raw])
  monkeypatch.setattr(observer.time, 'monotonic', lambda: clock[0])
  # receive's default captured the real monotonic at import time. Keep this
  # synthetic main-loop scenario on one clock, including its receive budget.
  receive = observer.BoundedEvents.receive
  monkeypatch.setattr(observer.BoundedEvents, 'receive',
                      lambda self, sockets, decode: receive(self, sockets, decode, clock=lambda: clock[0]))
  monkeypatch.setattr(observer.os, 'nice', lambda _: None)
  monkeypatch.setattr(observer.signal, 'signal', lambda sig, handler: handlers.update({sig: handler}))
  observer.main()
  store = Store(path)
  if outage:
    assert ticks[0] == 1  # saturation stopped polling/new collection, but not stop/retry checks
    assert writers[0].suspended and not writers[0].pending
    rows = store.db.execute('SELECT id, gaps, state FROM drives').fetchall()
    assert len(rows) == 3  # prior snapshot + explicit loss marker + frozen active drive
    active = next(json.loads(state) for drive_id, _, state in rows
                  if drive_id != 'earlier' and not json.loads(state).get('coverageLoss'))
    assert active['sequence'] == 3 and active['lastTime'] is not None and active['previous'] is None
    assert read_stats(path)['coverageLoss']
    assert read_stats(path)['models']['test']['stats']['assistedMeters'] == pytest.approx(.1)
    store.close()
    return
  complete, gaps, state = store.db.execute('SELECT complete, gaps, state FROM drives').fetchone()
  assert bool(complete) == offroad
  assert gaps == 1 and json.loads(state)['previous'] is None
  assert json.loads(state)['sequence'] == 3
  assert read_stats(path)['models']['test']['stats']['incomplete']
  store.close()


def test_bounded_decoder_real_event_roundtrip():
  from cereal import log
  event = log.Event.new_message(logMonoTime=123, valid=True)
  event.init('carState')
  event.carState.vEgo = 10
  event.carState.canValid = True
  event.carState.gearShifter = 'drive'
  decoded = observer.decode_event(event.to_bytes())
  assert decoded.logMonoTime == 123 and decoded.valid
  assert decoded.carState.vEgo == 10 and decoded.carState.gearShifter == 'drive'
  event = log.Event.new_message(logMonoTime=456, valid=True)
  event.init('starpilotModelV2')
  event.starpilotModelV2.runtimeIdentity = OWNER
  event.starpilotModelV2.modelMonoTime = 123
  decoded = observer.decode_event(event.to_bytes())
  assert decoded.starpilotModelV2.runtimeIdentity == OWNER
  assert decoded.starpilotModelV2.modelMonoTime == 123
