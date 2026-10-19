"""Physical goal coordinates only; actual controllers replay unchanged.

No physical fit/profile/grant is supplied. Tracking-error unit rows explicitly
represent coordinate equality; they are not a fabricated vehicle response proof.
"""
from dataclasses import replace
import math
import pickle
from types import SimpleNamespace

import pytest
from opendbc.car import structs
from openpilot.starpilot.flm.controller_replay import (
  SelectedControllerFactory, capture_snapshot, restore_snapshot, frame_input, _run, final_command,
)
from openpilot.starpilot.flm.event_episodes import tracking_episodes
from openpilot.starpilot.flm.event_windows import whole_event_windows
from openpilot.starpilot.flm.learner_factory import _frame
from openpilot.starpilot.flm.physical_response import desired_force_accel, request_force_accel
from openpilot.starpilot.flm.pid_controller_replay import PidControllerFactory
from openpilot.starpilot.flm.pid_stages import PidObservation
from openpilot.starpilot.flm.torque_adapter import Objective
from openpilot.starpilot.flm.torque_observation import TorqueObservation
from openpilot.starpilot.flm.runtime_adapter_registry import baseline_values
from openpilot.starpilot.flm.tests.test_event_lazy_native import TOYOTA, HYUNDAI, HONDA, make_interface
from openpilot.starpilot.flm.tests.test_fullrate_pipeline import snapshots


def actual_rows(domain, roll, *, ticks=220, waveform='sine'):
  platform={'torque':TOYOTA.TOYOTA_COROLLA_TSS2,'starpilot':HYUNDAI.HYUNDAI_IONIQ_6,'pid':HONDA.HONDA_CIVIC}[domain]
  ci=make_interface(platform)
  factory=PidControllerFactory(ci.CP,'native') if domain=='pid' else SelectedControllerFactory(
    ci.CP,'starpilot' if domain=='starpilot' else 'standard')
  actual,vm=factory.create()
  cp_before=factory.cp.as_builder().to_bytes()
  baseline=baseline_values(actual)
  observer=PidObservation() if domain=='pid' else TorqueObservation()
  actual.automatic_flm_observation=observer
  cs=structs.CarState.new_message(vEgo=20.,vEgoRaw=20.,canValid=True,gearShifter='drive')
  params=SimpleNamespace(angleOffsetDeg=.01,roll=roll)
  objective=Objective('feedforward','high','steady')
  rows,evidences=[],[]
  for tick in range(ticks):
    stamp=400_000_000_000+tick*10_000_000
    curvature=(0. if tick<30 else .002 if tick<75 else -.002) if waveform=='step' else .0006*math.sin(2*math.pi*tick/60)
    before=capture_snapshot(actual,vm)
    values=frame_input(cs,vm,params,active=True,safety_limited=False,
      desired_curvature=curvature,curvature_limited=False,lat_delay=.2)
    values+=(('control_frame',float(tick+1)),('raw_model_curvature',curvature))
    observer.begin_frame()
    raw,_,log=actual.update(True,cs,vm,params,False,curvature,False,.2)
    captured=observer.finish_frame(actual,log,selected_command=raw)
    assert captured is not None
    schema,stage,coordinates=captured
    if domain!='pid':
      stage+=(('actual_delta_ff',0.),('actual_delta_threshold',0.))
    evidence=replace(snapshots(stamp)[0],stage_schema_revision=schema,stage_values=stage,
      replay_inputs=values,applied_coordinates=coordinates,requested=final_command(raw))
    frame=_frame(evidence)
    recorded=dict(evidence.stage_values)['setpoint']
    assert frame.inputs is evidence.replay_inputs
    assert frame.desired_kinematic_accel == recorded
    current_request=dict(values)['desired_curvature']*dict(values)['vEgo']**2
    assert frame.desired_physical_accel == current_request-9.81*math.sin(roll)
    if roll==0.:
      assert pickle.dumps(frame.desired_physical_accel)==pickle.dumps(current_request)
    clone,clone_vm=factory.create()
    restore_snapshot(clone,clone_vm,before)
    replay,_=_run(clone,clone_vm,frame.inputs,objective,frame.applied_coordinates,frame.torque_values,
      actual_stage_residual=frame.actual_stage_residual)
    assert pickle.dumps(replay)==pickle.dumps(float(raw))
    rows.append(frame)
    evidences.append(evidence)
  assert factory.cp.as_builder().to_bytes()==cp_before and baseline_values(actual)==baseline
  return rows,evidences


@pytest.mark.parametrize('domain',('torque','starpilot','pid'))
@pytest.mark.parametrize('roll',(-.02,0.,.02))
def test_same_control_roll_corrects_force_goal_without_changing_actual_controller_or_tune(domain,roll):
  rows,_=actual_rows(domain,roll)
  assert any(abs(row.desired_kinematic_accel)>.03 for row in rows)
  engine=SimpleNamespace(records=rows,replay_windows=((rows[0].control_ns,rows[-1].control_ns),),
    _frame_context=lambda row:True)
  corrected=whole_event_windows(engine)
  assert corrected
  legacy=[replace(row,desired_physical_accel=row.desired_kinematic_accel,desired_kinematic_accel=None) for row in rows]
  engine.records=legacy
  assert whole_event_windows(engine)==corrected


@pytest.mark.parametrize('domain',('torque','starpilot','pid'))
@pytest.mark.parametrize('roll',(None,True,float('nan'),float('inf'),float('-inf')))
def test_missing_or_nonfinite_recorded_roll_never_defaults_to_zero_or_future_pose(domain,roll):
  _,rows=actual_rows(domain,.02,ticks=2)
  original=rows[-1]
  values=tuple((name,value) for name,value in original.replay_inputs if name!='roll')
  if roll is not None:
    values+=(('roll',roll),)
  with pytest.raises((KeyError,ValueError)):
    _frame(replace(original,replay_inputs=values))


def test_physical_tracking_error_uses_force_goal_while_geometry_keeps_original_setpoint():
  # Declared coordinate unit case, not measured data or a fitted plant.
  rows=[]
  points=[]
  roll=.02
  first=500_000_000_000
  for index in range(301):
    stamp=first+index*10_000_000
    goal=.3 if index<100 or index>=200 else -.3
    force=desired_force_accel(goal,roll)
    rows.append(SimpleNamespace(control_ns=stamp,desired_kinematic_accel=goal,desired_physical_accel=force,
      inputs=(('vEgo',20.),),healthy=True))
    if index%5==0:
      points.append({'control_ns':stamp,'control':{'stage_values':(('setpoint',goal),)},
        'physical':{'lateral_accel':force,'roll_rad':-.2}})
  engine=SimpleNamespace(records=rows,replay_windows=((first,rows[-1].control_ns),),
    _frame_context=lambda frame:True,identity='a'*64,baseline_revision='b'*64)
  objective=SimpleNamespace(group='ff.left',names=('ff_gain_left',),anchor_digest='c'*64,context_key='d'*64)
  assert tracking_episodes(engine,({'block_id':'unit','samples':points},),SimpleNamespace(heldout_rmse=.001),objective)==()
  assert abs(.3-desired_force_accel(.3,roll))>.10  # Old coordinate falsely looked like tracking error.


@pytest.mark.parametrize('domain',('torque','starpilot','pid'))
def test_transient_target_uses_current_request_before_plant_lag_not_delayed_stage(domain):
  rows,evidence=actual_rows(domain,.02,ticks=110,waveform='step')
  assert dict(rows[30].inputs)['desired_curvature']*dict(rows[30].inputs)['vEgo']**2 == .8
  assert dict(rows[75].inputs)['desired_curvature']*dict(rows[75].inputs)['vEgo']**2 == -.8
  for index in (30,75):
    current=dict(rows[index].inputs)['desired_curvature']*dict(rows[index].inputs)['vEgo']**2
    assert rows[index].desired_physical_accel == desired_force_accel(current,.02)
    assert rows[index].desired_kinematic_accel == dict(evidence[index].stage_values)['setpoint']
  if domain=='torque':
    # Standard controller's request buffer still contains the OLD request.
    assert rows[30].desired_kinematic_accel == 0.
    assert rows[75].desired_kinematic_accel == .8
  elif domain=='starpilot':
    from openpilot.starpilot.lateral.torque_shaping import MAX_LAT_JERK_UP
    # I6 uses clipped/filtered jerk to approximate lead, not exact current goal.
    assert rows[30].desired_kinematic_accel <= MAX_LAT_JERK_UP*.2 < .8
    assert rows[75].desired_kinematic_accel >= .8-MAX_LAT_JERK_UP*.2 > 0.
  else:
    # Native PID has no delayed stage setpoint; its force goal is unchanged.
    for row in rows:
      current=dict(row.inputs)['desired_curvature']*dict(row.inputs)['vEgo']**2
      assert row.desired_kinematic_accel == current


@pytest.mark.parametrize('field',('desired_curvature','vEgo','roll'))
@pytest.mark.parametrize('value',(None,True,float('nan'),float('inf'),float('-inf')))
def test_every_original_request_field_must_exist_be_numeric_and_finite(field,value):
  inputs=(('desired_curvature',.002),('vEgo',20.),('roll',.02))
  changed=tuple((name,number) for name,number in inputs if name!=field)
  if value is not None:
    changed+=((field,value),)
  with pytest.raises((KeyError,ValueError)):
    request_force_accel(changed)


def test_duplicate_request_keys_never_choose_a_convenient_target():
  inputs=(('desired_curvature',.002),('vEgo',20.),('roll',.02),('desired_curvature',0.))
  with pytest.raises(ValueError,match='duplicate'):
    request_force_accel(inputs)
