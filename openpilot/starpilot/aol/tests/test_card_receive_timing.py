"""Focused Card caller tests for optional native CAN receive summaries."""

from contextlib import ExitStack
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.card_loop_timing import CardLoopTiming
from openpilot.starpilot.aol.tests.test_card_loop_timing import Clock
from openpilot.starpilot.aol.tests.test_ioniq_availability import IoniqAvailabilityTests, car_state

TOTALS = ('release', 'native', 'reacquire', 'copy', 'delete_release', 'delete_native', 'delete_reacquire')
BOUNDARIES = (
  'before_release',
  'native_entry',
  'native_return',
  'after_reacquire',
  'before_delete_release',
  'delete_entry',
  'delete_return',
  'after_delete_reacquire',
)


def summary(messages=0):
  return {
    'schema_version': 1,
    'clock': 'MONOTONIC',
    'enabled': True,
    'blocking_calls': 1,
    'nonblocking_calls': 1,
    'messages': messages,
    'nulls': 1,
    'invalid_clock_samples': 0,
    'totals_ns': dict.fromkeys(TOTALS, 10),
    'boundary_names': BOUNDARIES,
    'slowest_blocking_ns': tuple(range(100, 108)),
    'slowest_nonblocking_ns': (0,) * 8,
  }


class Socket:
  def __init__(self, trace=None, fault=None):
    self.trace = [] if trace is None else trace
    self.fault = fault
    self.calls = 0
    self.latest = None

  def set_receive_timing(self, enabled):
    self.trace.append(('set', enabled))
    if self.fault == 'setup' and enabled:
      raise RuntimeError

  def take_receive_timing(self):
    self.calls += 1
    self.trace.append(('take', self.calls))
    if self.fault == ('reset' if self.calls == 1 else 'snapshot'):
      raise RuntimeError
    self.latest = summary(0 if self.calls == 1 else 1)
    return self.latest


def test_receive_summary_is_detached_and_scoped_to_one_drain():
  socket = Socket()
  clock = Clock()
  timing = CardLoopTiming(clock)
  timing.configure_receive(socket)
  timing.begin()
  timing.capture_receive(reset=True)
  timing.mark('can_receive_start')
  clock.advance(40_000_000)
  timing.mark('can_receive_end')
  timing.capture_receive()
  expected = summary(1)
  assert timing.can_receive_timing == expected
  assert socket.trace == [('set', True), ('take', 1), ('take', 2)]
  assert socket.latest is not None
  socket.latest['totals_ns']['native'] = 999
  socket.latest['messages'] = 999
  timing.finish({'can_receive_timing': timing.can_receive_timing}, enabled=True)
  timing.capture_receive(reset=True)
  assert timing.can_receive_timing is None
  report = timing.take_report()
  assert report['can_receive_timing'] == expected
  assert report['frames'][0]['can_receive_timing'] == expected


def test_non_detailed_recorder_never_touches_optional_native_api():
  socket = Socket()
  timing = CardLoopTiming(detailed=False)
  timing.configure_receive(socket)
  timing.capture_receive(reset=True)
  timing.capture_receive()
  assert socket.trace == [] and timing.capture_errors == 0


def test_old_native_api_is_contained_and_not_retried():
  timing = CardLoopTiming()
  timing.configure_receive(object())
  timing.capture_receive(reset=True)
  timing.capture_receive()
  assert timing.receive_status == 'error' and timing.receive_error_stage == 'setup'
  assert timing.capture_errors == 1 and timing.capture_error_type == 'AttributeError'
  assert timing.can_receive_timing is None


@pytest.mark.parametrize('stage', ['setup', 'reset', 'snapshot'])
def test_accessor_failure_disables_only_capture(stage):
  socket = Socket(fault=stage)
  timing = CardLoopTiming()
  timing.configure_receive(socket)
  timing.capture_receive(reset=True)
  timing.capture_receive()
  calls = list(socket.trace)
  timing.capture_receive(reset=True)
  timing.capture_receive()
  assert socket.trace == calls
  assert socket.trace[-1] == ('set', False)
  assert timing.receive_status == 'error' and timing.receive_error_stage == stage
  assert timing.capture_errors == 1 and timing.capture_error_type == 'RuntimeError'
  assert timing.receive_set is timing.receive_take is timing.can_receive_timing is None


@pytest.mark.parametrize('malformation', ['too_many_fields', 'nested_total', 'unbounded_points', 'bad_count', 'disabled'])
def test_incompatible_summary_is_not_retained(malformation):
  socket = Socket()
  timing = CardLoopTiming()
  timing.configure_receive(socket)
  timing.capture_receive(reset=True)
  raw = summary(1)
  if malformation == 'too_many_fields':
    raw.update({str(i): i for i in range(50)})
  elif malformation == 'nested_total':
    raw['totals_ns']['native'] = {'bad': [1]}
  elif malformation == 'unbounded_points':
    raw['slowest_blocking_ns'] = (0,) * 100
  elif malformation == 'bad_count':
    raw['messages'] = -1
  else:
    raw['enabled'] = False
  timing.receive_take = lambda: raw
  timing.capture_receive()
  assert timing.can_receive_timing is None and timing.receive_status == 'error'
  assert timing.capture_errors == 1 and socket.trace[-1] == ('set', False)


@pytest.mark.parametrize('fault', [None, 'setup', 'reset', 'snapshot'])
@pytest.mark.parametrize('cancel', [False, True])
def test_actual_card_receive_preserves_can_and_intent_with_optional_capture(fault, cancel):
  case = IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    cleanup.enter_context(OpenpilotPrefix())
    sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=False)
    drive(2)
    socket = Socket(fault=fault)
    card.can_sock = socket
    card.loop_timing = CardLoopTiming()
    card.loop_timing.configure_receive(socket)
    state = car_state()
    if cancel:
      from opendbc.car.structs import car

      state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
    with mock.patch('openpilot.selfdrive.car.card.cloudlog.event', side_effect=AssertionError('control thread logged')):
      latch = receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'], state=state)
    assert latch is (not cancel)
    # receive's genuine caller asserts CI.update's exact returned CS identity;
    # the ordinary CAN drain/decode path and physical intent operation still run.
    assert card.timing_can_packet_count == 1
    assert card.loop_timing.capture_errors == (0 if fault is None else 1)
    assert card.loop_timing.receive_status == ('enabled' if fault is None else 'error')
    assert (card.loop_timing.can_receive_timing is not None) is (fault is None)


@pytest.mark.parametrize('detailed', [False, True])
def test_card_thread_configures_once_before_worker_and_passes_summary_to_finish(monkeypatch, detailed):
  from openpilot.selfdrive.car import card as module

  trace = []
  socket = Socket(trace)
  clock = Clock()
  timing = CardLoopTiming(clock, detailed=detailed)

  class StopLoop(Exception):
    pass

  class Worker:
    def __init__(self, **kwargs):
      pass

    def start(self):
      trace.append('worker_start')

    def join(self):
      trace.append('worker_join')

  daemon: Any = module.Car.__new__(module.Car)
  daemon.aol_replay = daemon.aol_qualified = True
  daemon.can_sock = socket
  daemon.CP = SimpleNamespace(carFingerprint='HYUNDAI IONIQ 6 2023')
  daemon.ioniq6_keepalive = None
  daemon.configure_conditional_settings_worker = lambda: None
  daemon.vehicle_startup = SimpleNamespace(check=lambda: None)
  daemon.sm = SimpleNamespace(logMonoTime={'carControl': 11})
  daemon.aol_sequence = 1
  daemon.slc_producer_session = 'producer'
  daemon.initialized_prev = True
  calls = []

  def step():
    if calls:
      raise StopLoop
    calls.append(1)
    timing.capture_receive(reset=True)
    timing.capture_receive()
    clock.advance(40_000_000)

  daemon.step = step
  daemon.rk = SimpleNamespace(monitor_time=lambda: None)
  monkeypatch.setattr(module, 'REPLAY', False)
  monkeypatch.setattr(module.threading, 'Thread', Worker)
  monkeypatch.setattr(module, 'CardLoopTiming', lambda **kwargs: timing)
  with pytest.raises(StopLoop):
    daemon.card_thread()
  assert trace.count(('set', True)) == (1 if detailed else 0)
  if detailed:
    assert trace.index(('set', True)) < trace.index('worker_start')
    report = timing.take_report()
    assert report['can_receive_timing'] == summary(1)
    assert report['can_receive_timing_status'] == 'enabled'
  else:
    assert all(isinstance(item, str) for item in trace)
    assert timing.take_report() is None
