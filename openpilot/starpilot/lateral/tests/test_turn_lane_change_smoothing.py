import json
from pathlib import Path

from openpilot.cereal import log
from openpilot.selfdrive.controls.lib.desire_helper import LANE_CHANGE_SPEED_MIN
from openpilot.selfdrive.controls.lib.drive_helpers import clip_curvature
from openpilot.starpilot.lateral.lane_change_smoothing import LaneChangeSmoother, limit_rate


def factor(smoother, speed, state, previous=0., desired=.01, assist=True):
  return smoother.factor(active=True, lane_change_state=state, speed=speed, minimum_speed=0., duration=5.777777777777778,
                         previous=previous, desired=desired, turn_assist=assist)


def test_turn_assist_releases_intersection_curve_and_prior_lane_change_tail():
  smoother = LaneChangeSmoother()
  assert factor(smoother, 20., log.LaneChangeState.laneChangeStarting) < 1.
  for speed in (0., .8, 2., 4., 8.2, LANE_CHANGE_SPEED_MIN - 1e-6):
    assert factor(smoother, speed, log.LaneChangeState.laneChangeStarting) == 1.
    assert smoother.release == 0.
    assert smoother.entry_sign == 0.
    assert smoother.previous_factor == 1.
  # An intersection stays exempt until the model ends that lane-change state.
  assert factor(smoother, LANE_CHANGE_SPEED_MIN, log.LaneChangeState.laneChangeStarting) == 1.
  assert factor(smoother, LANE_CHANGE_SPEED_MIN, log.LaneChangeState.off) == 1.
  assert factor(smoother, LANE_CHANGE_SPEED_MIN, log.LaneChangeState.laneChangeStarting) < 1.


def test_manual_and_highway_lane_change_shaping_stays_exact():
  for speed, assist in ((1., False), (8.2, False), (LANE_CHANGE_SPEED_MIN, True), (30., True)):
    baseline, candidate = LaneChangeSmoother(), LaneChangeSmoother()
    previous = 0.
    for tick in range(700):
      state = log.LaneChangeState.laneChangeStarting if tick < 400 else log.LaneChangeState.off
      desired = .01 if tick < 250 else -.01
      expected = factor(baseline, speed, state, previous, desired, False)
      actual = factor(candidate, speed, state, previous, desired, assist)
      assert actual == expected
      previous, _ = clip_curvature(speed, previous, limit_rate(speed, previous, desired, actual), 0.)


def test_recorded_intersection_requests_retain_native_curvature_envelope():
  recorded = json.loads((Path(__file__).parent / 'fixtures/oct2_turns.json').read_text())
  for sequence in recorded['turns']:
    smoother = LaneChangeSmoother()
    previous = sequence[0][3]
    exercised = 0
    for _, speed, desired, _, state_name in sequence:
      state = getattr(log.LaneChangeState, state_name)
      shaping = factor(smoother, speed, state, previous, desired)
      limited = limit_rate(speed, previous, desired, shaping)
      output, _ = clip_curvature(speed, previous, limited, 0.)
      native, _ = clip_curvature(speed, previous, desired, 0.)
      if speed < LANE_CHANGE_SPEED_MIN:
        assert shaping == 1.
        assert output == native
        exercised += 1
      assert abs(output) <= .2
      assert abs(output) <= 3. / max(speed, 1.) ** 2 + 1e-12
      previous = output
    assert exercised > 500


def test_recorded_turn_onset_and_exit_are_not_delayed_by_lane_change_pacing():
  recorded = json.loads((Path(__file__).parent / 'fixtures/oct2_turns.json').read_text())
  results = []
  # The recorded sustained curvature-rate factor is 0.0863065, matching this
  # supported duration. This is a fixed-input response, not a vehicle simulation.
  duration = 6.888888888888889
  for sequence in recorded['turns']:
    tracks = []
    for assist in (False, True):
      smoother = LaneChangeSmoother()
      previous = sequence[0][3]
      trace = []
      for time, speed, desired, _, state_name in sequence:
        shaping = smoother.factor(active=True, lane_change_state=getattr(log.LaneChangeState, state_name),
                                  speed=speed, minimum_speed=0., duration=duration,
                                  previous=previous, desired=desired, turn_assist=assist)
        previous, _ = clip_curvature(speed, previous, limit_rate(speed, previous, desired, shaping), 0.)
        trace.append((time, previous))
      onset = next(time for time, curvature in trace if curvature < -.02)
      peak = min(range(len(trace)), key=lambda index: trace[index][1])
      exit_time = next(time for time, curvature in trace[peak:] if abs(curvature) < .01)
      tracks.append((onset, exit_time))
    results.append(tracks)
  # First bookmark is the unwind complaint; second is late turn initiation.
  assert results[0][0][1] - results[0][1][1] > 1.
  assert results[1][0][0] - results[1][1][0] > 2.
