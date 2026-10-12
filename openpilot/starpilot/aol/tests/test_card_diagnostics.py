"""Observational Card diagnostics: exact branches, bounded snapshots and real caller wiring."""
from dataclasses import replace
import json
from unittest import mock
from typing import Any

import pytest

from openpilot.cereal import messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from openpilot.starpilot.aol.intent import AolCardIntent, AolSettings
from openpilot.starpilot.card_loop_timing import CardLoopTiming
from openpilot.starpilot.aol.tests.test_card_loop_timing import Clock, finish
from openpilot.starpilot.aol.tests.test_ioniq_availability import IoniqAvailabilityTests, car_state


def owner():
  intent = AolCardIntent(AolSettings(True, 0., 9, 9, (0, 0, 0), (0, 0, 0)), explicit_latch=True)
  intent.allowed_latch = True
  intent._gesture_neutral_seen = True
  return intent


@pytest.mark.parametrize('cause', ['native_rejection', 'disarming_fault', 'can_invalid_or_timeout', 'settings_disabled',
                                   'acc_fault', 'cancel_press', 'physical_toggle'])
def test_exact_first_clear_branch_without_changing_intent(cause):
  intent, cs = owner(), car_state()
  cs.cruiseState.available = True
  kwargs = {'now_ns': 100}
  if cause == 'native_rejection':
    kwargs['native_rejection_ns'] = 99
  elif cause == 'disarming_fault':
    kwargs['fault_active'] = True
  elif cause == 'can_invalid_or_timeout':
    cs.canTimeout = True
  elif cause == 'settings_disabled':
    intent.settings = replace(intent.settings, enabled=False)
  elif cause == 'acc_fault':
    cs.accFaulted = True
  else:
    button = car.CarState.ButtonEvent.Type.cancel if cause == 'cancel_press' else car.CarState.ButtonEvent.Type.lkas
    cs.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=True)]
  intent.update(cs, **kwargs)
  assert not intent.allowed_latch
  assert intent.latch_clear_count == 1 and intent.latch_clear_reason == cause
  intent.update(cs, **kwargs)
  assert intent.latch_clear_count == 1


def test_first_clear_attribution_and_same_tick_rearm_are_visible():
  intent, cs = owner(), car_state()
  before = CardLoopTiming().intent_snapshot(intent)
  # Native rejection clears first; a genuinely new physical press rearms later.
  cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
  intent.update(cs, now_ns=100, native_rejection_ns=99)
  after = CardLoopTiming().intent_snapshot(intent)
  assert before[0] and after[0] and after[3] == before[3] + 1
  assert intent.latch_clear_reason == 'native_rejection'


def receiver():
  services = ['onroadEvents', 'carControl', 'aolSafetyWire', 'aolAxisState']
  sm = messaging.SubMaster(services)
  events = messaging.new_message('onroadEvents', 20, valid=True, logMonoTime=77)
  for e in events.onroadEvents:
    e.name = 'selfdrivedLagging'
    e.softDisable = True
  sm.update_msgs(1., [events])
  return sm


def observe(timing, intent, before, cs, sm):
  timing.observe_intent(intent, before, cs, sm, now_ns=100, source_can_ns=88, can_received_ns=99,
    producer_session='session', intent_sequence=10, stage='update_auxiliary_calibration', fault_active=True,
    transport_reset=False, native_rejection_ns=0, native_reset=False, native=None)


def test_snapshot_is_bounded_detached_and_has_distinct_source_clocks(monkeypatch):
  timing, intent, cs, sm = CardLoopTiming(), owner(), car_state(), receiver()
  before = timing.intent_snapshot(intent)
  cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True) for _ in range(20)]
  intent.update(cs, now_ns=100, fault_active=True)
  observe(timing, intent, before, cs, sm)
  intent.allowed_latch = True
  cs.canValid = False
  cs.buttonEvents = []
  report = timing.take_intent_report()
  assert report['before'][0] and not report['after'][0] and report['clear_reason'] == 'disarming_fault'
  assert report['source_can_boot_ns'] == 88 and report['can_received_mono_ns'] == 99
  assert report['snapshot_mono_ns'] == 100 and report['source_event_ns'] == 77
  assert report['can_valid'] and len(report['buttons']) == len(report['events']) == 16
  assert report['button_count'] == report['event_count'] == 20
  assert len(json.dumps(report).encode()) < 6000


def test_unchanged_intent_never_captures_inputs_or_reads_clock(monkeypatch):
  timing, intent = CardLoopTiming(), owner()
  def fail(*args):
    raise AssertionError('unchanged state touched inputs or clock')
  monkeypatch.setattr('openpilot.starpilot.card_loop_timing.time.monotonic_ns', fail)
  observe(timing, intent, timing.intent_snapshot(intent), None, None)
  assert not timing.intent_pending


def test_transition_queue_sequence_gaps_and_worker_rate_bound(monkeypatch):
  timing, intent, cs, sm = CardLoopTiming(), owner(), car_state(), receiver()
  clock = Clock()
  monkeypatch.setattr('openpilot.starpilot.card_loop_timing.time.monotonic_ns', lambda: clock.wall)
  for _ in range(10):
    before = timing.intent_snapshot(intent)
    intent.pause_lateral = not intent.pause_lateral
    observe(timing, intent, before, cs, sm)
  assert len(timing.intent_pending) == 4 and timing.intent_queue_full == 6
  assert timing.take_intent_report()['transition_sequence'] == 7
  assert timing.take_intent_report() is None
  clock.advance(timing.INTENT_REPORT_INTERVAL_NS - 1)
  assert timing.take_intent_report() is None
  clock.advance(1)
  assert timing.take_intent_report()['transition_sequence'] == 8


def test_late_suppression_is_visible_and_worker_overlap_is_only_a_snapshot():
  clock = Clock()
  timing = CardLoopTiming(clock)
  finish(timing, clock, 40_000_000)
  first = timing.take_report()
  assert first['late_cycles'] == first['report_sequence'] == 1 and first['rate_suppressed'] == 0
  finish(timing, clock, 40_000_000)
  assert timing.take_report() is None
  clock.advance(timing.REPORT_INTERVAL_NS)
  finish(timing, clock, 40_000_000)
  report = timing.take_report()
  assert report['late_cycles'] == 3 and report['report_sequence'] == 2 and report['rate_suppressed'] == 1
  assert report['clock_pair_is_sequential']
  assert report['point_clock_order'] == ('MONOTONIC', 'THREAD_CPUTIME', 'PROCESS_CPUTIME', 'BOOTTIME')
  timing.worker_begin('settings_read')
  active = timing.worker_current
  timing.worker_end()
  assert active is not None and timing.worker_previous is not None
  assert timing.worker_current is None and timing.worker_previous[:3] == active
  assert timing.worker_previous[3] >= active[1] and timing.worker_previous[4] >= active[2]


@pytest.mark.parametrize('full_op', [False, True])
def test_actual_card_records_physical_clear_with_exact_input_identity(full_op):
  case = IoniqAvailabilityTests(methodName='runTest')
  try:
    with OpenpilotPrefix():
      sd, _, drive, card, receive = case._ioniq_availability_callers(full_op=full_op)
      card.loop_timing = CardLoopTiming()
      drive(2)
      state = car_state()
      state.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.cancel, pressed=True)]
      with mock.patch('openpilot.selfdrive.car.card.cloudlog.event', side_effect=AssertionError('control-thread logging')):
        assert not receive(10_020_000_000, axis=sd.pm.messages['aolAxisState'], event=sd.pm.messages['onroadEvents'], state=state)
      report = card.loop_timing.take_intent_report()
      assert report['clear_reason'] == 'cancel_press' and report['before'][0] and not report['after'][0]
      assert report['source_event_ns'] == sd.pm.messages['onroadEvents'].logMonoTime
      assert report['source_axis_ns'] == sd.pm.messages['aolAxisState'].logMonoTime
      assert report['producer_session'] == 'authority-card'
      assert report['buttons'] == ((int(car.CarState.ButtonEvent.Type.cancel), True),)
  finally:
    case.doCleanups()


def test_capture_exceptions_are_counted_nonfatal_and_rate_limited(monkeypatch):
  timing, intent, cs = CardLoopTiming(), owner(), car_state()
  before = timing.intent_snapshot(intent)
  intent.pause_lateral = True
  # Bad diagnostic receiver, while the real owner already made its decision.
  observe(timing, intent, before, cs, None)
  assert intent.allowed_latch and intent.pause_lateral and timing.capture_errors == 1
  assert not timing.intent_pending
  report = timing.take_capture_error_report()
  assert report['capture_errors'] == 1 and report['last_error_type'] == 'TypeError'
  def bad_clock():
    raise RuntimeError('capture clock failure')
  timing.clock = bad_clock
  timing.begin()
  assert timing.capture_errors == 2 and timing.capture_error_type == 'RuntimeError'
  assert timing.take_capture_error_report() is None


@pytest.mark.parametrize('qualified,ioniq,flag,replay,expected', [
  (True, True, None, False, True), (True, True, '0', False, False),
  (True, False, None, False, False), (False, True, None, False, False),
  (True, False, '1', False, True), (True, True, '1', True, None),
])
def test_default_phase_recording_is_qualified_ioniq_even_when_latch_off(monkeypatch, qualified, ioniq, flag, replay, expected):
  from types import SimpleNamespace
  from openpilot.selfdrive.car import card as module
  from opendbc.car.hyundai.values import CAR
  class StopLoop(Exception):
    pass
  class Worker:
    def __init__(self, **kwargs):
      pass
    def start(self):
      pass
    def join(self):
      pass
  daemon: Any = module.Car.__new__(module.Car)
  daemon.aol_replay, daemon.aol_qualified = True, qualified
  daemon.aol_card_intent = owner()
  daemon.aol_card_intent.allowed_latch = False
  daemon.CP = SimpleNamespace(carFingerprint=CAR.HYUNDAI_IONIQ_6 if ioniq else CAR.HYUNDAI_SONATA)
  daemon.ioniq6_keepalive = None
  daemon.vehicle_startup = SimpleNamespace(check=lambda: None)
  def stop():
    raise StopLoop
  daemon.step = stop
  monkeypatch.setattr(module, 'REPLAY', replay)
  monkeypatch.setattr(module.threading, 'Thread', Worker)
  if flag is None:
    monkeypatch.delenv('CARD_PHASE_TIMING', raising=False)
  else:
    monkeypatch.setenv('CARD_PHASE_TIMING', flag)
  with pytest.raises(StopLoop):
    daemon.card_thread()
  assert (None if daemon.loop_timing is None else daemon.loop_timing.detailed) is expected
  if daemon.loop_timing is not None:
    assert daemon.loop_timing.compact is (flag != '1')


def test_failed_phase_frame_is_discarded_before_next_context():
  clock = Clock()
  timing = CardLoopTiming(clock)
  finish(timing, clock, 10_000_000, sequence=1)
  timing.begin()
  def bad_clock():
    raise RuntimeError('phase failed')
  timing.phase_clock = bad_clock
  timing.mark('broken')
  timing.finish({'intent_sequence': 2}, enabled=True)
  assert not timing.points and timing.previous is None and timing.previous_end is None
  assert timing.capture_errors == 1 and timing.take_report() is None
  timing.clock = bad_clock
  timing.begin()  # A second failed capture must not resurrect old points.
  assert timing.capture_errors == 2
  timing.clock = timing.phase_clock = clock
  finish(timing, clock, 40_000_000, sequence=3)
  report = timing.take_report()
  assert len(report['frames']) == 1 and report['frames'][0]['intent_sequence'] == 3
  assert report['capture_errors'] == 2 and report['loop_sequence'] == 4
  assert report['between_loops_ns'] == 0


def test_real_settings_worker_continues_after_diagnostic_sink_failure(monkeypatch):
  from types import SimpleNamespace
  from openpilot.selfdrive.car import card as module
  class Once:
    calls = 0
    def is_set(self):
      self.calls += 1
      return self.calls > 1
  clock = Clock()
  timing = CardLoopTiming(clock)
  finish(timing, clock, 40_000_000)
  daemon: Any = module.Car.__new__(module.Car)
  daemon.loop_timing = timing
  reads = []
  daemon.params = SimpleNamespace(get_bool=lambda key: reads.append(key) or True)
  daemon.CP = SimpleNamespace(openpilotLongitudinalControl=True, pcmCruise=False)
  daemon.aol_card_intent = None
  daemon.v_cruise_helper = SimpleNamespace(intervals=None)
  daemon.read_slc_configuration = lambda: 'settings'
  def broken_sink(*args, **kwargs):
    raise OSError('unavailable logging sink')
  monkeypatch.setattr(module.cloudlog, 'event', broken_sink)
  monkeypatch.setattr(module, 'read_cruise_intervals', lambda *a, **k: 'intervals')
  monkeypatch.setattr(module.time, 'sleep', lambda _: None)
  daemon.params_thread(Once())
  assert reads == ['IsMetric', 'ExperimentalMode']
  assert daemon.slc_requested_configuration == 'settings' and daemon.v_cruise_helper.intervals == 'intervals'
  assert timing.sink_errors == 1 and timing.worker_current is None
  assert timing.take_capture_error_report()['sink_errors'] == 1


def test_live_phase_clocks_do_not_invent_unsampled_process_or_boot_times():
  timing = CardLoopTiming(compact=True)
  timing.begin()
  timing.mark('can_receive_end')
  point = timing.points[-1]
  assert point[1] > 0 and point[2] > 0 and point[3:] == (None, None)
  assert timing.points[0][3] > 0 and timing.points[0][4] > 0


def test_publication_gap_emits_when_both_individual_cycles_are_short():
  clock = Clock()
  timing = CardLoopTiming(clock, compact=True)
  timing.begin()
  first_source = clock.wall
  timing.mark('car_state_send_end')
  clock.advance(20_000_000)
  timing.finish({'source_car_state_ns': first_source}, enabled=True)
  assert timing.take_report() is None
  timing.begin()
  clock.advance(20_000_000)
  second_source = clock.wall
  timing.mark('car_state_send_end')
  timing.finish({'source_car_state_ns': second_source}, enabled=True)
  report = timing.take_report()
  assert report['between_loops_ns'] == 0
  assert all(f['end_ns'] - f['start_ns'] == 20_000_000 for f in report['frames'])
  assert report['car_state_send_interval_ns'] == report['car_state_source_interval_ns'] == 40_000_000


def test_source_gap_emits_independently_of_send_return_interval():
  clock = Clock()
  timing = CardLoopTiming(clock, compact=True)
  timing.begin()
  clock.advance(20_000_000)
  timing.mark('car_state_send_end')
  timing.finish({'source_car_state_ns': 1}, enabled=True)
  timing.begin()
  clock.advance(20_000_000)
  timing.mark('car_state_send_end')
  timing.finish({'source_car_state_ns': 40_000_001}, enabled=True)
  report = timing.take_report()
  assert report['car_state_send_interval_ns'] == 20_000_000
  assert report['car_state_source_interval_ns'] == 40_000_000
