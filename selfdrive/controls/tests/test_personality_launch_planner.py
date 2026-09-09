import pytest
from openpilot.selfdrive.controls.tests.test_longitudinal_planner import (
  LongitudinalPlanner, LongCtrlState, make_sm, make_toggles, make_lead,
  set_model_launch_trajectory, CarInterface, CAR,
)
from opendbc.car.tesla.interface import CarInterface as TeslaInterface
from opendbc.car.tesla.values import CAR as TESLA
from openpilot.starpilot.common.longitudinal_personality_profiles import (
  default_personality_profiles, profile_document, update_personality_launch_boost,
)

def setup(level,experimental,vehicle="tesla",traffic=False,lead=True):
  CP=(TeslaInterface.get_non_essential_params(TESLA.TESLA_MODEL_3) if vehicle=="tesla"
      else CarInterface.get_non_essential_params(CAR.HONDA_CIVIC))
  planner=LongitudinalPlanner(CP,init_v=0)
  sm=make_sm(0,desired_accel=0.1,min_accel=-0.5,experimental_mode=experimental,tracking_lead=lead,
             lead_one=make_lead(status=lead,d_rel=7,v_lead=1.5,a_lead=0.8,radar=False,model_prob=1))
  sm["carState"].standstill=True
  sm["controlsState"].longControlState=LongCtrlState.stopping
  sm["selfdriveState"].personality=1
  sm["starpilotCarState"].trafficModeEnabled=traffic
  set_model_launch_trajectory(sm["modelV2"])
  toggles=make_toggles("v16")
  toggles.custom_personalities=True
  profiles=update_personality_launch_boost(default_personality_profiles(False),"traffic" if traffic else "standard",level)
  toggles.longitudinal_personality_profiles=profile_document(profiles,enabled=True)
  return planner,sm,toggles

@pytest.mark.parametrize("experimental",[False,True])
@pytest.mark.parametrize("vehicle",["tesla","honda"])
@pytest.mark.parametrize("traffic",[False,True])
def test_personality_launch_levels_reach_real_planner_in_both_modes(experimental,vehicle,traffic):
  outputs=[]
  for level in ["off","low","medium","high"]:
    planner,sm,toggles=setup(level,experimental,vehicle,traffic)
    # Compare identical initial planner state. Repeated fixed-speed updates
    # diverge through existing MPC feedback, so are not a level-order oracle.
    planner.update(sm,toggles)
    assert not planner.output_should_stop
    outputs.append(planner.output_a_target)
  assert outputs==sorted(outputs),outputs
  assert outputs[0]<outputs[-1]-0.1,outputs
  assert outputs[-1]>=0.8

@pytest.mark.parametrize("level",["off","low","medium","high"])
@pytest.mark.parametrize("veto",["brake","redLight","forcingStop","stopped_lead"])
def test_personality_launch_never_retains_boost_after_stop_veto(level,veto):
  planner,sm,toggles=setup(level,True)
  for _ in range(20):planner.update(sm,toggles)
  if veto=="brake":sm["carState"].brakePressed=True
  elif veto=="stopped_lead":
    sm["radarState"].leadOne=make_lead(status=True,d_rel=3.5,v_lead=0,a_lead=-0.8,radar=False,model_prob=1)
  else:setattr(sm["starpilotPlan"],veto,True)
  planner.update(sm,toggles)
  assert planner.launch_boost.extra==0
  if veto=="stopped_lead":
    assert planner.output_should_stop
    assert planner.output_a_target<=0

def test_personality_launch_off_does_not_disable_no_lead_normal_acceleration():
  planner,sm,toggles=setup("off",True,lead=False)
  sm["modelV2"].action.desiredAcceleration=0.45
  planner.update(sm,toggles)
  assert planner.output_a_target>=0
  assert planner.launch_boost.extra==0

def test_personality_launch_live_selection_and_master_disable():
  planner,sm,toggles=setup("medium",True)
  for _ in range(10):planner.update(sm,toggles)
  assert planner.launch_boost.extra>0
  toggles.longitudinal_personality_profiles["profiles"]["standard"]["launchBoost"]="off"
  planner.update(sm,toggles)
  off=planner.output_a_target
  assert planner.launch_boost.extra==0
  toggles.custom_personalities=False
  planner.update(sm,toggles)
  assert planner.output_a_target>off


@pytest.mark.parametrize("level",["low","medium"])
@pytest.mark.parametrize("override",["off","gas","accel_button"])
def test_personality_launch_ramp_does_not_precharge_during_override(level,override):
  planner,sm,toggles=setup(level,True)
  if override=="off":
    sm["controlsState"].longControlState=LongCtrlState.off
    sm["selfdriveState"].enabled=False
  elif override=="gas":sm["carState"].gasPressed=True
  else:sm["starpilotCarState"].accelPressed=True
  for _ in range(20):planner.update(sm,toggles)
  assert planner.launch_boost.extra==0
  sm["controlsState"].longControlState=LongCtrlState.stopping
  sm["selfdriveState"].enabled=True
  sm["carState"].gasPressed=False
  sm["starpilotCarState"].accelPressed=False
  planner.update(sm,toggles)
  assert planner.launch_boost.extra<=planner.launch_boost.RISE_RATES[level]*planner.dt+1e-9
