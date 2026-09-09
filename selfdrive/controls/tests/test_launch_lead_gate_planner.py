import pytest
from openpilot.selfdrive.controls.tests.test_personality_launch_planner import setup,make_lead

@pytest.mark.parametrize('experimental',[False,True])
@pytest.mark.parametrize('level',['low','medium','high'])
@pytest.mark.parametrize('gap,speed,accel',[(6,1.5,.49),(7,.4,.1),(7,1.5,.1),(9,1.5,-.2)])
def test_launch_gate_only_removes_extra_boost(experimental,level,gap,speed,accel):
  outputs=[]
  for selection in ['off',level]:
    planner,sm,toggles=setup(selection,experimental)
    sm['radarState'].leadOne=make_lead(status=True,d_rel=gap,v_lead=speed,a_lead=accel,radar=False,model_prob=1)
    planner.update(sm,toggles)
    outputs.append(planner.output_a_target)
    assert planner.launch_boost.extra==0
  assert outputs[0]==pytest.approx(outputs[1])

def test_launch_extra_removed_when_lead_slows_and_dropout_clears_extra_gate():
  planner,sm,toggles=setup('medium',True)
  for _ in range(10):planner.update(sm,toggles)
  assert planner.launch_boost.extra>0
  sm['radarState'].leadOne=make_lead(status=True,d_rel=7,v_lead=1.5,a_lead=-.1,radar=False,model_prob=1)
  sm['carState'].standstill=False;sm['carState'].vEgo=.2
  planner.update(sm,toggles)
  assert planner.launch_boost.extra==0
  sm['radarState'].leadOne=make_lead(status=False)
  planner.update(sm,toggles)
  assert not planner.launch_lead_gate.blocked
  assert planner.launch_boost.extra>0

def test_launch_arming_and_new_stop_reset():
  planner,sm,toggles=setup('medium',True)
  sm['carState'].standstill=False;sm['carState'].vEgo=.2
  planner.update(sm,toggles)
  assert not planner.model_launch_armed
  sm['carState'].standstill=True;sm['carState'].vEgo=0
  planner.update(sm,toggles)
  assert planner.model_launch_armed
  sm['carState'].standstill=False;sm['carState'].vEgo=2.1
  planner.update(sm,toggles)
  assert not planner.model_launch_armed
  sm['radarState'].leadOne=make_lead(status=False)
  sm['carState'].standstill=True;sm['carState'].vEgo=0
  planner.update(sm,toggles)
  assert planner.model_launch_armed


@pytest.mark.parametrize('level',['low','medium','high'])
def test_crawling_never_arms_and_slowing_back_down_does_not_rearm(level):
  planner,sm,toggles=setup(level,True,lead=False)
  sm['carState'].standstill=False
  for speed in [.8,.3,.05]:
    sm['carState'].vEgo=speed;planner.update(sm,toggles)
    assert not planner.model_launch_armed
    assert planner.launch_boost.extra==0
  sm['carState'].standstill=True;sm['carState'].vEgo=0
  planner.update(sm,toggles);assert planner.model_launch_armed
  sm['carState'].standstill=False
  for speed in [2.1,.8,.05]:
    sm['carState'].vEgo=speed;planner.update(sm,toggles)
    assert not planner.model_launch_armed
    assert planner.launch_boost.extra==0

@pytest.mark.parametrize('gap,accel',[(7,.5),(12,0),(20,-.3)])
def test_near_fast_or_far_lead_matches_existing_planner_permissions(gap,accel,monkeypatch):
  outputs=[]
  for bypass in [False,True]:
    planner,sm,toggles=setup('high',True)
    sm['radarState'].leadOne=make_lead(status=True,d_rel=gap,v_lead=1.5,a_lead=accel,radar=False,model_prob=1)
    if bypass:monkeypatch.setattr(planner.launch_lead_gate,'allows',lambda leads:True)
    planner.update(sm,toggles)
    assert not planner.launch_lead_gate.blocked
    outputs.append(planner.output_a_target)
  assert outputs[0]==pytest.approx(outputs[1])
