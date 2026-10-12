from contextlib import ExitStack
import json
from types import SimpleNamespace
from unittest import mock

from openpilot.common.prefix import OpenpilotPrefix
from openpilot.common.realtime import Ratekeeper
from openpilot.starpilot.selfdrive_loop_timing import SelfdriveLoopTiming
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture


class Clock:
  def __init__(self):
    self.now = 1_000_000_000
    self.cpu = 0

  def __call__(self):
    self.cpu += 100
    return self.now, self.cpu


def owner():
  return SimpleNamespace(sm=SimpleNamespace(logMonoTime={'aolIntentWire': 900, 'aolSafetyWire': 800},
    recv_time={'aolIntentWire': .000_000_901, 'aolSafetyWire': .000_000_802}),
    enabled=True, active=True, initialized=True, aol_car_state_log_ns=700,
    _loop_decision_ns=1000, _loop_decision_source_ns=700, events=SimpleNamespace(names=[]))


def cycle(timing, clock, rk, duration=1_000_000):
  timing.begin(rk)
  clock.now += duration
  timing.mark('step_return')
  timing.finish(owner(), rk)


def test_slow_cycle_is_detached_bounded_and_worker_formatted():
  clock = Clock()
  timing = SelfdriveLoopTiming(clock)
  rk = Ratekeeper(100)
  for _ in range(105):
    cycle(timing, clock, rk)
  assert not timing.pending and len(timing.history) == 100
  cycle(timing, clock, rk, 16_000_000)
  assert len(timing.pending) == 1
  report = timing.take_report()
  assert report['trigger_slow'] and not report['trigger_lagging']
  assert len(report['frames']) == 3 and report['window_cycles'] == 100
  assert report['frames'][-1]['decision_ns'] == 1000
  assert report['frames'][-1]['decision_source_ns'] == 700
  assert report['frames'][-1]['intent_sm_ns'] == 900
  assert report['clock_alignment'][0] <= report['clock_alignment'][2]
  assert report['phase_clock_columns'][2] == 'main_thread_cpu_ns'
  json.dumps(report, allow_nan=False)
  assert timing.take_report() is None


def test_actual_ratekeeper_window_triggers_without_a_slow_current_cycle():
  clock = Clock()
  timing = SelfdriveLoopTiming(clock)
  rk = Ratekeeper(100)
  for _ in range(100):
    rk.avg_dt.add_value(.0112)
  cycle(timing, clock, rk)
  report = timing.take_report()
  frame = report['frames'][-1]
  assert report['trigger_lagging'] and not report['trigger_slow']
  assert frame['rate_before']['lagging'] and frame['rate_after']['lagging']
  assert frame['rate_after']['lag_threshold_s'] == .01 * (1 / .9)
  assert len(report['rate_intervals_s']) == 100
  assert abs(sum(report['rate_intervals_s']) - frame['rate_after']['sum_s']) < 1e-12
  assert 'remaining_s' in frame['rate_after'] and 'next_frame_time_s' in frame['rate_after']


def test_suppression_reports_even_when_late_condition_clears():
  clock = Clock()
  timing = SelfdriveLoopTiming(clock)
  rk = Ratekeeper(100)
  cycle(timing, clock, rk, 16_000_000)
  timing.take_report()
  cycle(timing, clock, rk, 25_000_000)
  assert timing.rate_suppressed == 1 and not timing.pending
  # Keep cycling normally until the report interval elapses, with no new slow
  # cycle. The buffered peak and suppression count must still be observable.
  for _ in range(501):
    cycle(timing, clock, rk, 10_000_000)
  report = timing.take_report()
  assert report['suppressed_summary'] and report['rate_suppressed'] == 1
  assert report['suppressed_peak_frame'][0] == 25_000_000


def test_queue_sequence_gaps_and_mark_truncation_are_visible():
  clock = Clock()
  timing = SelfdriveLoopTiming(clock)
  rk = Ratekeeper(100)
  for _ in range(3):
    clock.now += timing.REPORT_INTERVAL_NS
    timing.begin(rk)
    for _ in range(80):
      timing.mark('many')
    clock.now += 16_000_000
    timing.finish(owner(), rk)
  assert len(timing.pending) == 2
  report = timing.take_report()
  assert report['queue_sequence_gap'] == 1
  assert report['truncated_marks'] > 0
  assert max(len(frame['points']) for frame in report['frames']) <= timing.MAX_MARKS
  assert timing.take_report()['queue_full_observations'] >= 1


def test_capture_failure_never_mutates_owner_or_ratekeeper():
  clock = Clock()
  timing = SelfdriveLoopTiming(clock)
  rk = Ratekeeper(100)
  before = rk.avg_dt.buffer.copy(), rk.avg_dt.sum, rk.avg_dt.index
  timing.begin(rk)
  timing.finish(SimpleNamespace(), rk)
  assert timing.capture_errors == 1 and timing.points == []
  assert before == (rk.avg_dt.buffer, rk.avg_dt.sum, rk.avg_dt.index)
  with mock.patch.object(timing, 'clock', side_effect=RuntimeError('diagnostic clock unavailable')):
    timing.begin(rk)
  assert timing.capture_errors == 2 and timing.points == []


def test_real_owner_markers_preserve_output_and_distinguish_clock_provenance():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, step, _, _ = case._ioniq_availability_callers(full_op=True)
      assert sd.loop_timing is not None
      timing = sd.loop_timing
      clock = Clock()
      def phase_clock():
        clock.now += 1_000_000
        return clock()
      timing.clock = phase_clock
      actual_step = sd.step
      def timed_step():
        timing.begin(sd.rk, sd.aol_published_input_proof)
        actual_step()
        sd.mark_loop_phase('step_return')
        sd.rk.monitor_time()
        timing.finish(sd, sd.rk)
      with mock.patch.object(sd, 'step', side_effect=timed_step):
        axis, state, command = step(2)
      assert axis.lateralActive and axis.longitudinalActive and state.enabled
      assert command.latActive and command.longActive and not sd.aol_authority_lost
      report = timing.take_report()
      frame = report['frames'][-1]
      names = [point[0] for point in frame['points']]
      for earlier, later in [('recv_one_start', 'recv_one_return'), ('raw_batch_before_sm', 'submaster_return'),
                             ('intent_drain_start', 'intent_drain_return'), ('native_validation_start', 'native_validation_return'),
                             ('state_machine_return', 'axis_send_return'), ('axis_send_return', 'selfdrive_send_return'),
                             ('selfdrive_send_return', 'step_return'), ('step_return', 'ratekeeper_return')]:
        assert names.index(earlier) < names.index(later)
      assert frame['decision_ns'] == axis.observedMonoTime == 10_020_000_000
      assert frame['recv_one_source_ns'] == axis.sourceCarStateMonoTime
      assert frame['prior_output_proof'][3] == 10_040_000_000
      assert report['intent_snapshot_matches_decision']
      assert report['native_decision']['requestedLateral'] and report['native_decision']['lateralAllowed']
      assert len(frame['points']) <= timing.MAX_MARKS and not report['truncated_marks']


def test_worker_sink_failure_does_not_stop_settings_refresh():
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, _, _, _ = case._ioniq_availability_callers(full_op=True)
      sd.params.put_bool('IsMetric', True, block=True)
      evt = mock.Mock()
      evt.is_set.side_effect = [False, True]
      with mock.patch.object(sd.loop_timing, 'take_report', return_value={'sample': 1}), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.cloudlog.event', side_effect=RuntimeError('sink unavailable')), \
           mock.patch('openpilot.selfdrive.selfdrived.selfdrived.time.sleep'):
        sd.params_thread(evt)
      assert sd.loop_timing.sink_errors == 1 and sd.is_metric
      assert sd.loop_timing.worker_window[0] is not None and sd.loop_timing.worker_window[1] is not None
