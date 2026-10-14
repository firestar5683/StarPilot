

def test_actual_recorder_compact_report_preserves_every_original_phase():
  from openpilot.common.realtime import Ratekeeper
  from openpilot.starpilot.selfdrive_loop_timing import SelfdriveLoopTiming
  from openpilot.starpilot.aol.tests.test_selfdrive_loop_timing import Clock, cycle
  clock = Clock()
  timing = SelfdriveLoopTiming(clock)
  rk = Ratekeeper(100)
  for _ in range(105):
    cycle(timing, clock, rk)
  cycle(timing, clock, rk, 16_000_000)
  original_history = tuple(timing.history)
  metadata = dict(timing.pending[0][0])
  report = timing.take_report()
  assert report is not None and report['phases_derived_from_points']
  assert len(report['window_cycle_totals']) == report['window_cycles'] == 100
  for key, value in metadata.items():
    if key != 'rate_window':
      assert report[key] == value
  size, index, count, buffer = metadata['rate_window']
  assert report['rate_window_size'] == size
  assert report['rate_intervals_s'] == ((buffer[index:]+buffer[:index]) if count == size else buffer[:count])
  assert report['window_cycle_totals'] == [
    (context[0], points[0][1], points[-1][1]-points[0][1],
     points[-1][2]-points[0][2], context[-1], between)
    for context, points, between, before, after in original_history]

  for frame in report['frames']:
    original = next(row for row in original_history if row[0][0] == frame['cycle_sequence'])
    context, points, between, before, after = original
    names = ('cycle_sequence', 'selected_source_ns', 'decision_ns', 'recv_one_source_ns',
             'intent_sm_ns', 'native_sm_ns', 'raw_intent_latest_ns', 'intent_step_drain_count',
             'axis_deferred', 'decision_source_ns', 'prior_output_proof', 'cycle_process_cpu_ns')
    expected = dict(zip(names, context, strict=True))
    expected.update(points=points, between_loops_ns=between,
                    rate_before=timing._rate_dict(before), rate_after=timing._rate_dict(after))
    assert frame == expected
    assert frame['points'] == original[1]
    assert 'phases' not in frame
    assert [(b[1]-a[1], b[2]-a[2]) for a, b in zip(frame['points'], frame['points'][1:], strict=False)] == [
      (b[1]-a[1], b[2]-a[2]) for a, b in zip(original[1], original[1][1:], strict=False)]
