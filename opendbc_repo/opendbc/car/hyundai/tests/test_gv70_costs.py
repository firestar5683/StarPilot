from dataclasses import replace
from types import SimpleNamespace
import pytest
from opendbc.car.hyundai.gv70_costs import CostContext, eligible, project
from opendbc.car.hyundai.values import CAR


def context(**kwargs):
  return replace(CostContext(0., 50., 0., 'acc', 1., 1., 1., False, False, True), **kwargs)


def test_absolute_publisher_costs_and_stop_priority():
  assert project(context()).stage == (3., 0., 0., 0., 250., 5.5)
  assert project(context(tracked_lead=True)).stage[4] == 437.5
  assert project(context(stop_approach=True, tracked_lead=True)).stage[4] == 50.


def test_distance_and_uncertainty_costs():
  result = project(context(speed_mps=35 * 1.609344 / 3.6, lead_distance_m=5., uncertainty=.525))
  assert result.stage[4] == pytest.approx(310.)
  assert result.stage[5] == pytest.approx(5.5 * 1.24 * 1.35)
  assert result.constraints == pytest.approx((1e6, 1e6, 1e6, 124.))


def test_blended_mode_preserves_original_fixed_weights():
  assert project(context(mode='blended', stop_approach=True)).stage == (0., .1, .2, 5., 40., 1.)
  assert project(context(mode='blended', previous_accel_constraint=False)).stage[4] == 0.
  assert project(context(previous_accel_constraint=False)).stage[4] == 0.


def test_exact_vehicle_identity_and_stock_siblings():
  cp = SimpleNamespace(carFingerprint=CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN,
                       openpilotLongitudinalControl=True, passive=False, dashcamOnly=False, notCar=False)
  assert eligible(cp)
  cp.openpilotLongitudinalControl = False
  assert not eligible(cp)
  cp.openpilotLongitudinalControl = True
  cp.carFingerprint = CAR.HYUNDAI_IONIQ_6
  assert not eligible(cp)


def test_bad_context_refuses_projection():
  with pytest.raises(ValueError):
    project(context(uncertainty=float('nan')))
  with pytest.raises(ValueError):
    project(context(mode='unknown'))


class Inputs(dict):
  def __init__(self, now):
    from openpilot.starpilot.longitudinal.follow_jerk import SOURCES
    from openpilot.cereal import log
    super().__init__(carState=SimpleNamespace(vEgo=10.,canValid=True,canTimeout=False,gasPressed=False,brakePressed=False),
                     controlsState=SimpleNamespace(forceDecel=False),
                     radarState=log.RadarState.new_message(leadOne={'present':True,'dRel':10.}),
                     modelV2=SimpleNamespace(timestampEof=now,meta=SimpleNamespace(desirePrediction=[1.,0.],
                        disengagePredictions=SimpleNamespace(brakePressProbs=[0.]))))
    self.logMonoTime={name:now for name in SOURCES}
    self.valid={name:True for name in SOURCES}
    self.alive={name:True for name in SOURCES}


def sample(owner, sm, now):
  return owner.sample(sm,now,active=True,drive_id=1,mode='acc',acceleration_factor=1.,
                      speed_factor=1.,danger_factor=1.,stop_plan=SimpleNamespace(forcing=False,approach_distance_m=0.),
                      follow_scale=1.,prev_accel_constraint=True)


def test_actual_context_preserves_filtered_distance_and_resets_on_stale_source():
  from openpilot.starpilot.longitudinal.gv70_cost_context import GV70CostContext
  clock=[(950_000_000,950_000_000)]
  owner=GV70CostContext(clock_pair=lambda:clock[0])
  assert sample(owner,Inputs(950_000_000),950_000_000) is None
  clock[0]=(1_000_000_000,1_000_000_000)
  sm=Inputs(1_000_000_000)
  first=sample(owner,sm,1_000_000_000)
  assert first is not None
  sm=Inputs(1_050_000_000)
  sm['radarState'].leadOne.dRel=50.
  clock[0]=(1_050_000_000,1_050_000_000)
  second=sample(owner,sm,1_050_000_000)
  assert owner.distance == pytest.approx(12.8)
  assert second.stage[4] > 250.
  before=(owner.distance,owner.uncertainty.x)
  assert sample(owner,sm,1_050_000_000) == second
  assert (owner.distance,owner.uncertainty.x) == before
  sm.valid['radarState']=False
  assert sample(owner,sm,1_100_000_000) is None
  assert owner.distance is None
  assert owner.drive_id == 0


def test_actual_context_uncertainty_and_current_mode():
  from openpilot.starpilot.longitudinal.gv70_cost_context import GV70CostContext
  owner=GV70CostContext()
  sm=Inputs(1_000_000_000)
  sm['modelV2'].meta.desirePrediction=[.5,.5]
  result=owner.sample(sm,1_000_000_000,active=True,drive_id=1,mode='blended',acceleration_factor=1.,
                      speed_factor=1.,danger_factor=1.,stop_plan=SimpleNamespace(forcing=True,approach_distance_m=5.),
                      follow_scale=1.75,prev_accel_constraint=True)
  assert result is None
  assert owner.distance is None


def test_actual_solver_stage_and_terminal_weight_application():
  import numpy as np
  from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import LongitudinalMpc,N,T_IDXS
  owner=LongitudinalMpc.__new__(LongitudinalMpc)
  owner._cached_cost_weights=None
  rows={}
  owner.solver=SimpleNamespace(cost_set=lambda i,key,value:rows.__setitem__((i,key),np.array(value,copy=True)))
  weights=project(context(stop_approach=True))
  owner.set_cost_weights(weights.stage,weights.constraints)
  for i in range(N):
    assert rows[(i,'W')][4,4] == pytest.approx(50.*np.interp(T_IDXS[i],[0.,1.,2.],[1.,1.,0.]))
    assert tuple(rows[(i,'Zl')]) == weights.constraints
  assert rows[(N,'W')].shape == (5,5)
