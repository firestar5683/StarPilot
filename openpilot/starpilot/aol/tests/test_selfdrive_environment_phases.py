from contextlib import ExitStack
from unittest import mock

import pytest

from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.aol.tests import test_ioniq_availability as fixture


class PhaseClock:
  def __init__(self):
    self.wall = 1_000_000_000
    self.cpu = 0

  def __call__(self):
    self.wall += 1_000
    self.cpu += 100
    return self.wall, self.cpu

  def delay(self, wall, cpu):
    self.wall += wall
    self.cpu += cpu


def run_owner(*, bookmark, observe):
  case = fixture.IoniqAvailabilityTests(methodName='runTest')
  with ExitStack() as cleanup:
    cleanup.callback(case.doCleanups)
    with OpenpilotPrefix():
      sd, _, drive, _, _ = case._ioniq_availability_callers(full_op=True)
      sd.params.put('PrimeType', 0, block=True)
      timing = sd.loop_timing
      assert timing is not None
      clock = PhaseClock()
      timing.clock = clock
      original_params = sd.params
      reads = []
      phases = {'ChestnutLoading': ('chestnut_loading_start', 8_000_000, 10_000),
                'ChestnutActive': ('chestnut_active_start', 9_000_000, 20_000),
                'PrimeType': ('bookmark_prime_start', 10_000_000, 30_000)}

      class ObservedParams:
        def __getattr__(self, name):
          return getattr(original_params, name)

        def record(self, key):
          if key in phases:
            name, wall, cpu = phases[key]
            reads.append((key, timing.points[-1][0] if timing.points else None))
            if observe:
              assert timing.points[-1][0] == name
              clock.delay(wall, cpu)

        def get(self, key, *args, **kwargs):
          self.record(key)
          return original_params.get(key, *args, **kwargs)

        def get_bool(self, key, *args, **kwargs):
          self.record(key)
          return original_params.get_bool(key, *args, **kwargs)

      sd.params = ObservedParams()
      actual_events = sd.update_events
      actual_step = sd.step

      def update_events(cs):
        sd.sm.updated['userBookmark'] = bookmark
        return actual_events(cs)

      def step():
        if observe:
          timing.begin(sd.rk, sd.aol_published_input_proof)
        actual_step()
        if observe:
          sd.mark_loop_phase('step_return')
          sd.rk.monitor_time()
          timing.finish(sd, sd.rk)

      if not observe:
        sd.loop_timing = None
      with mock.patch.object(sd, 'update_events', side_effect=update_events), \
           mock.patch.object(sd, 'step', side_effect=step):
        axis, state, command = drive(2)
      assert axis.lateralActive and axis.longitudinalActive and command.latActive and command.longActive
      assert state.enabled and not sd.aol_authority_lost
      assert axis.observedMonoTime == 10_020_000_000
      assert axis.validUntilMonoTime == axis.observedMonoTime + 30_000_000
      report = timing.take_report() if observe else None
      return axis.to_dict(), command.to_dict(), tuple(sd.events.names), reads, report


@pytest.mark.parametrize('bookmark', [False, True])
def test_actual_environment_read_boundaries_and_authority_are_unchanged(bookmark):
  plain = run_owner(bookmark=bookmark, observe=False)
  observed = run_owner(bookmark=bookmark, observe=True)
  assert observed[:3] == plain[:3]
  assert [key for key, _ in observed[3]] == ['ChestnutLoading', 'ChestnutActive'] + (['PrimeType'] if bookmark else [])
  report = observed[4]
  assert report is not None
  frame = report['frames'][-1]
  points = {name: (wall, cpu) for name, wall, cpu in frame['points']}
  expected = [('chestnut_loading', 8_000_000, 10_000), ('chestnut_active', 9_000_000, 20_000)]
  if bookmark:
    expected.append(('bookmark_prime', 10_000_000, 30_000))
  else:
    assert 'bookmark_prime_start' not in points and 'bookmark_prime_return' not in points
  for phase, wall, cpu in expected:
    start, end = points[phase + '_start'], points[phase + '_return']
    assert end[0] - start[0] == wall + 1_000
    assert end[1] - start[1] == cpu + 100
  assert len(frame['points']) <= timing_capacity() and not report['truncated_marks']
  assert frame['decision_ns'] == 10_020_000_000
  assert frame['recv_one_source_ns'] == observed[0]['sourceCarStateMonoTime']
  assert report['intent_snapshot_matches_decision']


def timing_capacity():
  from openpilot.starpilot.selfdrive_loop_timing import SelfdriveLoopTiming
  return SelfdriveLoopTiming.MAX_MARKS


@pytest.mark.parametrize('boolean', [False, True])
def test_disabled_read_uses_one_exact_accessor_and_preserves_value(boolean):
  from types import SimpleNamespace
  from openpilot.starpilot.selfdrive_loop_timing import timed_params_read
  result = object()
  params = SimpleNamespace(get=mock.Mock(return_value=result), get_bool=mock.Mock(return_value=result))
  assert timed_params_read(SimpleNamespace(params=params, loop_timing=None), 'ChestnutLoading', boolean) is result
  used, unused = (params.get_bool, params.get) if boolean else (params.get, params.get_bool)
  used.assert_called_once_with('ChestnutLoading')
  unused.assert_not_called()


@pytest.mark.parametrize('boolean', [False, True])
def test_read_failure_propagates_without_return_mark_or_retry(boolean):
  from types import SimpleNamespace
  from openpilot.starpilot.selfdrive_loop_timing import timed_params_read
  error = OSError('original Params read failure')
  params = SimpleNamespace(get=mock.Mock(side_effect=error), get_bool=mock.Mock(side_effect=error))
  timing = SimpleNamespace(mark=mock.Mock())
  with pytest.raises(OSError) as caught:
    timed_params_read(SimpleNamespace(params=params, loop_timing=timing), 'ChestnutLoading', boolean)
  assert caught.value is error
  used, unused = (params.get_bool, params.get) if boolean else (params.get, params.get_bool)
  used.assert_called_once_with('ChestnutLoading')
  unused.assert_not_called()
  timing.mark.assert_called_once_with('chestnut_loading_start')
