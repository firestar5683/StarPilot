from unittest.mock import patch

import numpy as np
import pytest

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.cereal import log
from openpilot.selfdrive.controls.lib import longitudinal_planner
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib import long_mpc
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages
from openpilot.starpilot.longitudinal.upstream import mpc as stock_mpc, planner as stock_planner


PERSONALITIES = (log.LongitudinalPersonality.relaxed, log.LongitudinalPersonality.standard,
                 log.LongitudinalPersonality.aggressive)
REVERSE_PLAN = np.array([
  [0., 20.65, 1.05], [1.436, 20.72, 1.05], [5.776, 20.94, 1.05], [13.108, 21.29, .95],
  [23.554, 21.66, .59], [37.173, 21.86, .034], [53.812, 21.62, -.67], [72.856, 20.35, -2.13],
  [92.651, 17.42, -3.5], [110.775, 13.29, -3.5], [125.258, 8.67, -3.5], [134.177, 3.56, -3.5],
  [127.994, -15.95, -20.93],
])


def seed_reverse_plan(mpc):
  mpc.set_cur_state(20.65, 1.05)
  for stage, state in enumerate(REVERSE_PLAN):
    mpc.solver.set(stage, 'x', state)
  mpc.a_prev = np.interp(long_mpc.T_IDXS + mpc.dt, long_mpc.T_IDXS, REVERSE_PLAN[:, 2])


def assert_bounded_terminal(mpc):
  assert mpc.solution_status == 0
  assert np.isfinite(mpc.x_sol).all()
  assert np.min(mpc.v_solution) >= -.01
  assert mpc.params[-1, 0] - .01 <= mpc.a_solution[-1] <= mpc.params[-1, 1] + .01


@pytest.mark.parametrize('personality', PERSONALITIES)
@pytest.mark.parametrize('mode', ('stock', 'starpilot', 'stop_line'))
def test_native_reverse_terminal_plan_recovers_for_both_planners(mode, personality):
  module = stock_mpc if mode == 'stock' else long_mpc
  mpc = module.LongitudinalMpc()
  seed_reverse_plan(mpc)
  radar = log.RadarState.new_message()
  if mode != 'stop_line':
    for lead in (radar.leadOne, radar.leadTwo):
      lead.present, lead.dRel, lead.vLead, lead.aLeadK = True, 76., 0., 0.
      lead.aLeadTau, lead.modelProb = 1.5, 1.
  with patch.object(mpc, 'reset', side_effect=AssertionError('native solver unexpectedly reset')):
    for _ in range(20):
      mpc.set_weights(personality=personality)
      mpc.set_cur_state(20.65, 1.05)
      mpc.update(radar, personality=personality, **({'stop_line_m': 70., 'acceleration_max': 1.05}
                                                 if mode == 'stop_line' else {}))
      assert mpc.solution_status == 0
  assert_bounded_terminal(mpc)
  assert np.interp(.2, long_mpc.T_IDXS, mpc.a_solution) < 0.


@pytest.mark.parametrize('planner_class', (stock_planner.LongitudinalPlanner, longitudinal_planner.LongitudinalPlanner))
@pytest.mark.parametrize('personality', PERSONALITIES)
@pytest.mark.parametrize('speed', (0., 10., 20.65, 30.))
def test_native_terminal_bounds_through_real_planner_transitions(planner_class, personality, speed):
  cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
  planner = planner_class(cp, init_v=speed)
  with patch.object(planner.mpc, 'reset', side_effect=AssertionError('native solver unexpectedly reset')):
    for tick in range(80):
      sm, _ = messages(lead=20 <= tick < 50, e2e=50 <= tick < 60, off=tick < 10)
      sm['carState'].vEgo = speed
      sm['carState'].standstill = speed == 0.
      sm['carControl'].longActive = tick >= 10
      sm['selfdriveState'].personality = personality
      sm['carState'].vCruise = 55.
      for lead in (sm['radarState'].leadOne, sm['radarState'].leadTwo):
        lead.dRel, lead.vLead, lead.vRel = 150., max(0., speed - 3.), -min(3., speed)
      planner.update(sm)
      assert_bounded_terminal(planner.mpc)
      assert np.isfinite(planner.output_a_target)

