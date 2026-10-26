"""SP-016 independent clearance and curve scheduling with real model messages."""
from dataclasses import replace
import math
import pytest
from openpilot.starpilot.lateral.lane_centering import LaneCenteringController, LaneCenteringSettings, _bend_target
from openpilot.starpilot.lateral.tests.test_lane_centering import observation, XS
from openpilot.starpilot.lateral.tests.test_lane_v4 import scene

def curved(k=.005):
  m=scene(left=-1.5,right=1.5)
  for path,offset in ((m.laneLines[1],-1.5),(m.laneLines[2],1.5)):
    path.y=[offset + .5*k*x*x for x in XS]
  return m

def tick(c,m=None,frame=1,dt=.05,**changes):
  s=replace(LaneCenteringSettings(enabled=True,response_tau=.35,response_min=.30,clearance=.2,single_clearance=.2,e2e_authority=0.,curve_start_radius=1000.),**changes)
  return c.update(observation(m if m is not None else curved(),model_sample_id=frame,elapsed_seconds=dt,settings=s))

def test_curve_equation_cadence_and_hold():
  c=LaneCenteringController();tick(c)
  assert c._bend_weight==pytest.approx(1-math.exp(-.05/.2))
  assert c._response_tau==pytest.approx(.35-.05*c._bend_weight)
  before=c._bend_weight
  tick(c,dt=.01);assert c._bend_weight==before
  tick(c,frame=2,dt=.04);assert c._bend_weight==pytest.approx(1-math.exp(-.10/.2))
  one=scene(left=-.6,rp=0.)
  weight=c._bend_weight;effective=c._response_tau
  for frame in range(3,30):tick(c,one,frame=frame)
  assert c.selected_mode==3 and c._bend_weight==weight and c._response_tau==effective
  tick(c,scene(left=-1.5,right=1.5),frame=30)
  assert c._bend_weight<weight

def test_fresh_single_mode_uses_normal_values():
  c=LaneCenteringController();tick(c,scene(left=-.6,rp=0.))
  assert c.selected_mode==3 and c._response_tau==.35 and c._bend_weight==0.

def test_pair_minimum_does_not_veto_independently_valid_single():
  c=LaneCenteringController()
  r=tick(c,scene(left=-.8,right=1.6),clearance=.4,single_clearance=.2)
  assert c.selected_mode==3 and r.reason=='qualified'
  r=tick(c,scene(left=-.8,right=1.6),frame=2,clearance=.4,single_clearance=.4)
  assert c.selected_mode==0 and r.reason=='unqualified_model'
  tick(c,scene(left=-1.4,right=1.4),frame=3,clearance=.2,single_clearance=.8)
  assert c.selected_mode==1  # single clearance does not constrain centring pairs

def test_model_preference_blends_using_same_weight():
  c=LaneCenteringController();tick(c,e2e_authority=1.)
  assert c._e2e_authority==pytest.approx(1-c._bend_weight)
  one=scene(left=-.6,rp=0.);value=c._e2e_authority
  tick(c,one,frame=2,e2e_authority=1.)
  assert c._e2e_authority==value
  tick(c,frame=3,curve_adaptation=False,e2e_authority=1.)
  assert c._e2e_authority==1. and c._response_tau==.35 and c._bend_weight==0.

@pytest.mark.parametrize('update',[{'lateral_active':False},{'driver_override':True},{'turn_signal_active':True},{'time_discontinuity':True},{'model_valid':False}])
def test_existing_resets_clear_bend_history(update):
  c=LaneCenteringController();tick(c)
  assert c._bend_weight>0
  c.update(observation(curved(),settings=LaneCenteringSettings(enabled=True),**update))
  assert c._bend_weight==0.

def test_bad_fit_holds_without_inventing_a_straight():
  c=LaneCenteringController();tick(c)
  w=c._bend_weight;m=curved()
  m.laneLines[2].y=[1.5-.0025*x*x for x in XS]
  tick(c,m,frame=2)
  assert c._bend_weight==w
  assert _bend_target(m,[(0,'line',-1.5),(1,'line',1.5)],20.,LaneCenteringSettings()) is None

def test_live_endpoint_changes_apply_without_resetting_boundaries():
  c=LaneCenteringController();tick(c)
  previous=c._smoothed.copy();w=c._bend_weight
  tick(c,frame=1,response_min=.1)
  assert c._smoothed==previous and c._bend_weight==w
  tick(c,frame=2,response_min=.1)
  assert c._bend_weight>w and c._response_tau < .35-.05*c._bend_weight

@pytest.mark.parametrize('changes',[{'response_min':.36},{'e2e_min':.1},{'curve_full_radius':1000.},{'curve_adaptation':1},{'single_clearance':float('nan')}])
def test_invalid_tuning_disables(changes):
  c=LaneCenteringController();r=tick(c,**changes)
  assert r.reason=='invalid_input' and r.correction==0.


@pytest.mark.parametrize('maximum,minimum',[(1.,0.),(.8,.2)])
def test_independent_preference_rise_and_response_timing(maximum,minimum):
  c=LaneCenteringController()
  c._bend_weight=c._preference_weight=1.
  for frame in range(1,21):
    tick(c,scene(left=-1.5,right=1.5),frame=frame,e2e_authority=maximum,e2e_min=minimum)
  assert c._e2e_authority==pytest.approx(minimum+.95*(maximum-minimum))
  assert c._response_tau==pytest.approx(.35-.05*math.exp(-5))
  c._bend_weight=c._preference_weight=0.
  for frame in range(21,25):tick(c,frame=frame,e2e_authority=maximum,e2e_min=minimum)
  assert c._e2e_authority==pytest.approx(minimum+(maximum-minimum)*math.exp(-1))


def test_unknown_pair_holds_both_weights_and_resumes_without_catchup():
  c=LaneCenteringController();tick(c,e2e_authority=1.)
  m=curved();m.laneLines[2].y=[1.5-.0025*x*x for x in XS]
  previous=(c._bend_weight,c._preference_weight,c._response_tau,c._e2e_authority)
  for frame in range(2,102):
    tick(c,m,frame=frame,e2e_authority=1.)
    assert (c._bend_weight,c._preference_weight,c._response_tau,c._e2e_authority)==previous
  tick(c,scene(left=-1.5,right=1.5),frame=102,e2e_authority=1.)
  assert c._preference_weight==pytest.approx(previous[1]*math.exp(-.05/(-1/math.log(.05))))
  before=(c._bend_weight,c._preference_weight)
  tick(c,frame=102,dt=.01,e2e_authority=1.)
  assert (c._bend_weight,c._preference_weight)==before


def test_preference_history_clears_on_disable_and_reset():
  c=LaneCenteringController();tick(c,e2e_authority=1.)
  assert c._preference_weight>0
  tick(c,frame=2,curve_adaptation=False,e2e_authority=.8,e2e_min=.2)
  assert c._preference_weight==0 and c._e2e_authority==.8
  tick(c,frame=3,e2e_authority=1.);c.reset()
  tick(c,scene(left=-.6,rp=0.),frame=4,e2e_authority=.8,e2e_min=.2)
  assert c._preference_weight==0 and c._e2e_authority==.8 and c._response_tau==.35
