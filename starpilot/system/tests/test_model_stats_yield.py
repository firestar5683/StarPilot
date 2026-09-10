"""Budget exhaustion must preserve brief pedal edges and bounded work."""
from collections import deque
from types import SimpleNamespace as NS
from pathlib import Path
import json
import pytest
from openpilot.starpilot.system import model_statsd as m
from openpilot.starpilot.common.model_stats import Reducer
from openpilot.starpilot.common.tests.test_model_stats import OWNER, sample

class Socket:
  def __init__(self, events):
    self.events = deque(events)
  def receive(self, non_blocking=True):
    return self.events.popleft() if self.events else None

def test_scheduling_pause_keeps_just_received_pedal_edge():
  clock = [0.0]
  events = {str(i).encode(): NS(logMonoTime=i, sample=sample(i / 100, brake=i == 2, enabled=i < 2)) for i in range(5)}
  socket = Socket(events)
  queue, reducer = m.BoundedEvents(), Reducer()
  def decode(raw):
    clock[0] += .03  # scheduling/decoding crossed the 5 ms cooperative deadline
    return events[raw]
  for _ in range(5):
    assert not queue.receive({socket:'carState'}, decode, clock=lambda: clock[0])
    assert len(queue.pending) == 1
    reducer.update(queue.pop()[3].sample)
  totals = {k:sum(r[k] for r in reducer.metrics.values()) for k in ('interventions','disengagements','brake')}
  assert totals == {'interventions':1,'disengagements':1,'brake':1}
  assert reducer.gaps == 0

def test_many_ticks_resume_fairly_without_growth_or_loss():
  total = 12000
  socket = Socket(str(i).encode() for i in range(total))
  queue = m.BoundedEvents()
  seen = []
  while socket.events:
    assert not queue.receive({socket:'carState'}, lambda raw:NS(logMonoTime=int(raw)), clock=lambda:0)
    assert len(queue.pending) <= m.MAX_TICK_MESSAGES
    assert queue.bytes <= m.MAX_PENDING_BYTES
    while queue.pending:
      seen.append(queue.pop()[0])
  assert seen == list(range(total))
  assert queue.bytes == 0

def test_byte_budget_yields_before_consuming_an_unretainable_event():
  socket = Socket([b'x' * m.MAX_EVENT_BYTES] * 30)
  queue = m.BoundedEvents()
  assert not queue.receive({socket:'carState'},lambda raw:NS(logMonoTime=1),clock=lambda:0)
  assert queue.yield_reason == 'byte_budget'
  assert queue.bytes <= m.MAX_TICK_BYTES
  assert len(socket.events) + len(queue.pending) == 30

def test_route_read_is_bounded_validated_and_optional(tmp_path):
  p = tmp_path/'CurrentRoute'
  assert m.current_route(p) is None
  p.write_text('0000013e--0520bd8368')
  assert m.current_route(p) == '0000013e--0520bd8368'
  for value in ('../wrong', 'x' * 10000, 'old route', ''):
    p.write_text(value)
    assert m.current_route(p) is None

def test_diagnostics_separate_cpu_from_waiting():
  d = m.Diagnostics()
  d.timing('receive', .030, .001)
  d.timing('receive', .002, .002)
  state = d.snapshot(m.BoundedEvents())
  assert state['receiveWallMs'] == 30
  assert state['receiveCpuMs'] == 2
  assert state['receiveWaitingMs'] == 29
