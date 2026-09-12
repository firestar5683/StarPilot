import math
import random
import pytest
from openpilot.selfdrive.controls.lib.launch_boost import LaunchBoost

def test_off_retains_normal_acceleration_and_clears_previous_extra():
  boost=LaunchBoost()
  for _ in range(20):boost.update(0.2,1.5,"medium",True,0.05)
  assert boost.update(0.2,1.5,"off",True,0.05)==0.2
  assert boost.extra==0
  assert boost.update(2.0,1.5,"off",True,0.05)==2.0

def test_high_is_exact_legacy_max_for_varied_planner_targets():
  rng=random.Random(71);boost=LaunchBoost()
  for _ in range(1000):
    target=rng.uniform(-3.5,3.5);launch=rng.uniform(0,1.5)
    assert boost.update(target,launch,"high",True,0.05)==max(target,launch)
    assert boost.update(target,launch,"high",False,0.05)==target

@pytest.mark.parametrize("level,fraction,rate",[("low",1/3,0.5),("medium",2/3,1.0)])
def test_extra_rises_gradually_and_only_scales_difference(level,fraction,rate):
  boost=LaunchBoost();last=0
  for _ in range(80):
    target=boost.update(0.2,1.5,level,True,0.05)
    assert 0<=boost.extra-last<=rate*0.05+1e-10
    assert 0.2<=target<=1.5
    last=boost.extra
  assert target==pytest.approx(0.2+1.3*fraction)
  assert boost.update(2.0,1.5,level,True,0.05)==2.0

@pytest.mark.parametrize("level",["low","medium","high"])
def test_lost_release_or_stop_veto_removes_boost_immediately(level):
  boost=LaunchBoost()
  for _ in range(80):boost.update(0.2,1.5,level,True,0.05)
  assert boost.update(-1.0,1.5,level,False,0.05)==-1.0
  assert boost.extra==0
  assert boost.update(-0.5,None,level,True,0.05)==-0.5

@pytest.mark.parametrize("level",["low","medium"])
def test_reduced_request_and_speed_taper_never_retain_old_boost(level):
  boost=LaunchBoost()
  for _ in range(80):boost.update(0.2,1.5,level,True,0.05)
  assert 0.2<=boost.update(0.2,0.3,level,True,0.05)<=0.3
  assert boost.update(0.2,0.0,level,True,0.05)==0.2
  assert boost.extra==0

def test_unknown_level_or_invalid_prediction_never_adds_boost():
  boost=LaunchBoost()
  assert boost.update(0.2,1.5,"invalid",True,0.05)==0.2
  assert boost.update(0.2,math.nan,"medium",True,0.05)==0.2
  assert boost.update(0.2,1.5,"medium",True,math.inf)==0.2
