"""SP-016 v4 behaviour with real modelV2 messages and the complete controller."""
from dataclasses import replace
import math
import pytest
from openpilot.starpilot.lateral.lane_centering import LaneCenteringController, LaneCenteringSettings, MAX_CORRECTION
from openpilot.starpilot.lateral.tests.test_lane_centering import model, observation, XS


def scene(left=-1.5, right=2.1, lp=.9, rp=.9, ls=.1, rs=.1, le=-2., re=2.5, les=2., res=2., path=0.):
  m=model(left=left,right=right,path=path)
  m.laneLineProbs=[0.,lp,rp,0.];m.laneLineStds=[0.,ls,rs,0.]
  m.init('roadEdges',2)
  for edge,y in zip(m.roadEdges,(le,re)):
    edge.x=XS;edge.y=[y]*len(XS)
  m.roadEdgeStds=[les,res]
  return m


def tick(c,m=None,frame=1,dt=.05,**settings):
  # Fixed regression tune: changing user defaults must not move these test boundaries.
  for key,value in dict(strength=1.5,max_correction=.0012,min_speed_mps=4.4704,confidence_split=.30,low_std=.5,clearance=.35,smoothing_distance=.2,smoothing_tau=.3).items():
    settings.setdefault(key,value)
  settings.setdefault("response_min", 0.)
  settings.setdefault("single_clearance", settings.get("clearance", .35))
  settings.setdefault("single_deadband", .08)  # Historical behavior fixtures stay fixed.
  settings.setdefault("curve_adaptation", False)
  return c.update(observation(m if m is not None else scene(),model_sample_id=frame,elapsed_seconds=dt,
                             settings=replace(LaneCenteringSettings(True,e2e_authority=0.),**settings)))


@pytest.mark.parametrize('prob,std,accepted',[(.30,.999,True),(.30,1.,False),(.299,.499,True),(.299,.5,False),(.10,.49,True),(.099,.1,False),(1.,.1,True),(1.01,.1,False),(.9,-.1,False),(.9,float('nan'),False)])
def test_tier_boundaries(prob,std,accepted):
  c=LaneCenteringController();tick(c,scene(lp=prob,ls=std),mode2=False,mode3=False)
  assert (c.selected_mode==1)==accepted


def test_high_tier_failure_does_not_fall_through():
  c=LaneCenteringController();tick(c,scene(lp=.8,ls=.6),high_std=.5,low_std=1.,mode2=False,mode3=False)
  assert c.selected_mode==0


@pytest.mark.parametrize('std,accepted',[(.999,True),(1.,False),(-.1,False),(float('nan'),False)])
def test_edge_acceptance(std,accepted):
  c=LaneCenteringController();tick(c,scene(lp=0.,les=std))
  assert (c.selected_mode==2)==accepted


@pytest.mark.parametrize('width,mode',[(2.54,0),(2.55,1),(4.8,1),(4.81,3)])
def test_width_boundaries(width,mode):
  m=scene(left=0.,right=width)
  limits={"car_width": float(m.laneLines[2].y[0]) - .7} if width==2.55 else {"max_width": float(m.laneLines[2].y[0])} if width==4.8 else {}
  c=LaneCenteringController();tick(c,m,**limits)
  assert c.selected_mode==mode


def test_narrow_edge_veto_and_wide_line_veto():
  c=LaneCenteringController();r=tick(c,scene(le=-.2,les=.1))
  assert c.selected_mode==0 and r.correction==0
  tick(c,scene(left=-3.,right=3.,le=-1.,les=.1),frame=2)
  assert c.selected_mode==3  # mixed width4m cannot override wide lines


def test_mode_toggles_mixed_narrower_and_tie():
  c=LaneCenteringController();m=scene(le=-1.6,re=2.8,les=.1,res=.1)
  tick(c,m);assert c.selected_mode==1
  tick(c,m,frame=2,mode1=False);assert c.selected_sources==((0,'edge'),(1,'line'))
  tick(c,scene(left=-1.5,right=1.5,le=-2.,re=2.,les=.1,res=.1),frame=3,mode1=False)
  assert c.selected_sources==((0,'line'),(1,'edge'))
  tick(c,m,frame=4,mode1=False,mode2=False,mode3=False);assert c.selected_mode==0


@pytest.mark.parametrize('side',[0,1])
def test_single_boundary_unknown_width_away_only(side):
  c=LaneCenteringController()
  m=scene(left=-.9,right=.9,lp=.9 if side==0 else 0.,rp=.9 if side==1 else 0.)
  r=tick(c,m)
  assert c.selected_mode==3 and (r.correction>0)==(side==0)
  c2=LaneCenteringController();r2=tick(c2,m,offset_m=-.3 if side==0 else .3)
  assert r==r2


def test_mode3_deadband_zero_and_conflict():
  c=LaneCenteringController();r=tick(c,scene(left=-1.23,rp=0.))
  assert c.selected_mode==3 and r.correction==0
  r=tick(c,scene(left=-2.,rp=0.),frame=2);assert r.correction==0
  tick(c,scene(left=-1.4,right=1.4),frame=3,mode1=False,mode2=False,clearance=.6)
  assert c.selected_mode==0


def test_mode3_both_raw_and_smoothed_must_need_clearance_and_tail_is_retained():
  c=LaneCenteringController();a=tick(c,scene(left=-.9,rp=0.))
  b=tick(c,scene(left=-1.4,rp=0.),frame=2,smoothing_distance=.5)
  assert c._raw==0 and 0<b.correction<a.correction
  # Change side: existing positive output may briefly remain toward the right boundary.
  d=tick(c,scene(lp=0.,right=1.19),frame=3,dt=.01)
  assert c.selected_sources==((1,'line'),) and d.correction>0 and c._raw<0


def test_smoothed_mode3_target_opposite_conflict():
  c=LaneCenteringController()
  tick(c,scene(lp=0.,rp=0.,le=-1.1,re=1.6,les=.1,res=.1,path=-.2))
  r=tick(c,scene(lp=0.,rp=0.,le=-1.4,re=1.3,les=.1,res=.1,path=-.2),frame=2)
  assert c.selected_mode==3 and c._raw is None and r.reason=='unqualified_model'


def test_exact_filter_lag_cap_held_frames_and_source_switch():
  c=LaneCenteringController();tick(c)
  tick(c,scene(right=2.2),frame=2)
  expected=2.1+.1*(1-math.exp(-.05/.3))
  assert c._smoothed[1]==pytest.approx(expected)
  before=list(c._smoothed)
  for _ in range(4):tick(c,scene(right=20.),frame=2,dt=.01)
  assert c._smoothed==before
  tick(c,scene(rp=0.,re=2.4,res=.1),frame=3,dt=.01)
  assert c.selected_mode==2 and c._smoothed[1]>=2.4-.2
  assert c._smoothed[0]==pytest.approx(-1.5)


@pytest.mark.parametrize('setting', ['smoothing_tau','smoothing_distance'])
def test_zero_bypass_and_live_edit_preserves_history(setting):
  c=LaneCenteringController();tick(c);tick(c,scene(right=2.2),frame=2,smoothing_tau=.6)
  assert c._smoothed[1]==pytest.approx(2.1+.1*(1-math.exp(-.05/.6)))
  tick(c,scene(right=2.4),frame=3,**{setting:0.});assert c._smoothed[1]==pytest.approx(2.4)


def test_unused_side_pause_and_narrow_clear_history():
  c=LaneCenteringController();tick(c)
  tick(c,scene(rp=0.),frame=2);assert c._smoothed[1] is None
  tick(c,scene(right=2.3),frame=3);assert c._smoothed[1]==pytest.approx(2.3)
  c.update(observation(scene(),model_sample_id=4,turn_signal_active=True));assert c._smoothed==[None,None]
  tick(c,frame=5);tick(c,scene(left=-.5,right=.5),frame=6);assert c._smoothed==[None,None]


def test_filtered_pair_width_failure_keeps_tracking_without_mode_fallback():
  c=LaneCenteringController();tick(c,scene(left=-1.275,right=1.275))
  # A missing side re-seeds at raw while the other side lags a translation.
  tick(c,scene(left=-1.275,rp=0.),frame=2)
  tick(c,scene(left=-1.5,right=1.06),frame=3)
  assert c.selected_mode==1 and c._raw is None and c._smoothed[0] is not None
  for i in range(4,55):tick(c,scene(left=-1.5,right=1.07),frame=i)
  assert c._raw is not None


@pytest.mark.parametrize('change',[{'driver_override':True},{'lateral_active':False},{'model_valid':False},{'time_discontinuity':True},{'speed_mps':4.4}])
def test_stock_resets_clear_boundaries(change):
  c=LaneCenteringController();tick(c)
  r=c.update(observation(scene(),**change))
  assert r.correction==0 and c._smoothed==[None,None]


def test_mode3_smoothed_clearance_never_attracts():
  c=LaneCenteringController();tick(c,scene(left=-1.5,rp=0.))
  r=tick(c,scene(left=-1.2,rp=0.),frame=2,smoothing_distance=.5)
  assert c.selected_mode==3 and c._raw==0 and r.correction==0


def test_strength_e2e_and_absolute_cap_preserved():
  for strength in (.5,1.5,3.):
    c=LaneCenteringController()
    for i in range(200):
      r=tick(c,scene(left=-.1,rp=0.),frame=i,strength=strength)
      assert abs(r.correction)<=MAX_CORRECTION
  c=LaneCenteringController();r=tick(c,scene(left=-.1,rp=0.),e2e_authority=1.)
  assert r.correction==0


def test_opposite_conflict_fades_even_when_raw_selected_boundary_is_clear():
  c=LaneCenteringController();tick(c,scene(left=-.9,rp=0.))
  r=tick(c,scene(left=-1.4,right=1.3,path=-.1),frame=2,mode1=False,mode2=False)
  assert c.selected_mode==3 and c._raw is None and r.reason=='unqualified_model'


@pytest.mark.parametrize('value',[True,'0.3',float('nan'),float('inf'),1<<4096])
def test_invalid_new_settings_reject_without_exception(value):
  c=LaneCenteringController();r=tick(c,smoothing_tau=value)
  assert r.reason=='invalid_input' and r.correction==0


@pytest.mark.parametrize('tau',[0.,.01,.2,.4,1.])
def test_response_time_controls_acquisition_and_reversal(tau):
  target=tick(LaneCenteringController(),response_tau=0.).correction
  c=LaneCenteringController();r=tick(c,response_tau=tau)
  alpha=1.-math.exp(-.05/tau) if tau else 1.
  assert r.correction==pytest.approx(target*alpha)
  # Live edits preserve output history; response zero applies the new request immediately.
  r=tick(c,scene(left=-2.1,right=1.5),frame=2,response_tau=0.,smoothing_tau=0.)
  assert r.correction==pytest.approx(-target)

@pytest.mark.parametrize('tau',[0.,.01,.2,.4,1.])
@pytest.mark.parametrize('cause',['signal','geometry'])
def test_release_time_only_controls_fallback(tau,cause):
  c=LaneCenteringController();start=tick(c,response_tau=0.).correction
  kwargs={'turn_signal_active':True} if cause=='signal' else {}
  m=scene() if cause=='signal' else scene(lp=0.,rp=0.)
  r=c.update(observation(m,model_sample_id=2,elapsed_seconds=.05,**kwargs,
      settings=replace(LaneCenteringSettings(True,e2e_authority=0.),response_tau=0.,response_min=0.,release_tau=tau)))
  assert r.correction==pytest.approx(start*(math.exp(-.05/tau) if tau else 0.))
  assert r.reason==('signal_release' if cause=='signal' else 'unqualified_model')

def test_valid_zero_request_uses_response_and_override_still_resets():
  c=LaneCenteringController();start=tick(c,response_tau=0.).correction
  r=tick(c,scene(left=-1.8,right=1.8),frame=2,smoothing_tau=0.,response_tau=.4,release_tau=0.)
  assert r.correction==pytest.approx(start*math.exp(-.05/.4))
  r=c.update(observation(scene(),driver_override=True,settings=LaneCenteringSettings(True,response_tau=1.,release_tau=1.)))
  assert r.correction==0. and r.reason=='driver_override'


@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("deadband", [0., .02, .08, .15])
def test_single_deadband_exact_clearance_request(side, deadband):
  c = LaneCenteringController()
  m = scene(left=-1.275, right=1.275, lp=.9 if side == 0 else 0., rp=.9 if side == 1 else 0.)
  r = tick(c, m, single_clearance=.45, single_deadband=deadband, response_tau=0.)
  distance = abs(float(m.laneLines[side + 1].y[0]))
  expected = (1 if side == 0 else -1) * 2 * max(0., .925 + .45 - distance - deadband) / 20**2
  assert c.selected_mode == 3
  assert c._raw == pytest.approx(expected)
  assert r.correction == pytest.approx(expected * .30 * 1.5)


def test_deadband_live_edit_and_all_modes():
  c = LaneCenteringController(); m = scene(left=-1.275, rp=0.)
  tick(c, m, single_clearance=.45, single_deadband=.08)
  first = c._raw
  tick(c, m, frame=2, single_clearance=.45, single_deadband=.02)
  assert c._raw > first
  # A deadband edit cannot turn a sufficient-clearance target into attraction.
  tick(c, scene(left=-1.6, rp=0.), frame=3, single_clearance=.45, single_deadband=0.)
  assert c._raw == 0
  for mode in (1, 2):
    m = scene() if mode == 1 else scene(rp=0., re=2.1, res=.1)
    a,b = LaneCenteringController(),LaneCenteringController()
    tick(a,m,single_deadband=0.);tick(b,m,single_deadband=.15)
    assert a.selected_mode == b.selected_mode == mode and a._raw > b._raw


@pytest.mark.parametrize("deadband", [-.01, .151, float("nan"), float("inf"), True])
def test_invalid_single_deadband_fails_closed(deadband):
  c=LaneCenteringController()
  r=tick(c,scene(rp=0.),single_deadband=deadband)
  assert r.reason == "invalid_input" and r.correction == 0


@pytest.mark.parametrize("mode", [1, 2, 3])
@pytest.mark.parametrize("deadband", [0., .02, .08, .15])
def test_all_modes_share_deadband(mode, deadband):
  m = scene() if mode == 1 else scene(rp=0., re=2.1, res=.1) if mode == 2 else scene(left=-1.275, rp=0.)
  c=LaneCenteringController();tick(c,m,single_clearance=.45,single_deadband=deadband,response_tau=0.)
  assert c.selected_mode==mode
  error = (float(m.laneLines[1].y[0]) + (float(m.laneLines[2].y[0]) if mode==1 else float(m.roadEdges[1].y[0]))) / 2 if mode!=3 else 1.375 + float(m.laneLines[1].y[0])
  assert c._raw==pytest.approx(2*max(0.,error-deadband)/400)


@pytest.mark.parametrize("speed,seconds,distance", [(0.,.5,8.),(10.,.5,8.),(20.,1.,20.),(20.,1.5,30.),(30.,2.,35.)])
def test_lookahead_samples_and_conversion_use_same_bounded_distance(speed,seconds,distance):
  from unittest.mock import patch
  import numpy as np
  from openpilot.starpilot.lateral import lane_centering as module
  m=scene()
  for line,offset in ((m.laneLines[1],-1.8),(m.laneLines[2],1.8)):
    line.y=[offset+.01*x for x in XS]
  m.position.y=[.002*x for x in XS]
  settings=LaneCenteringSettings(True,e2e_authority=0.,lookahead_time=seconds,response_tau=0.,response_min=0.,smoothing_tau=0.)
  c=LaneCenteringController()
  with patch.object(module,'_bend_target',wraps=module._bend_target) as bend:
    c.update(observation(m,speed_mps=speed,settings=settings))
    assert bend.call_args.args[2]==distance
  midpoint=(np.interp(distance,XS,m.laneLines[1].y)+np.interp(distance,XS,m.laneLines[2].y))/2
  error=midpoint-np.interp(distance,XS,m.position.y)
  assert c.selected_mode==1 and c._raw==pytest.approx(2*max(0.,error-.02)/distance**2)


@pytest.mark.parametrize("authority,std,expected_factor",[(1.,.1,.5),(.5,.1,.75),(0.,.1,1.),(1.,.6,1.)])
def test_override_threshold_ramp_and_model_confidence_gate(authority,std,expected_factor):
  from openpilot.starpilot.lateral.lane_centering import _error_correction
  m=scene();m.position.yStd=[std]*len(XS)
  raw=_error_correction(m,20.,.3,authority,20.,.02,.2,.4)
  assert raw==pytest.approx(2*(.3-.02)/400*expected_factor)
  assert _error_correction(m,20.,.1,authority,20.,.02,.2,.4)==pytest.approx(2*.08/400)


def test_new_live_edits_apply_on_next_frame_without_filter_reset():
  c=LaneCenteringController();m=scene()
  tick(c,m,single_deadband=.02,e2e_authority=1.)
  raw=c._raw;history=list(c._smoothed)
  tick(c,m,lookahead_time=.5,override_start=.3,override_full=.6,single_deadband=.02,e2e_authority=1.)
  assert c._raw==raw and c._smoothed==history
  tick(c,m,frame=2,lookahead_time=.5,override_start=.3,override_full=.6,single_deadband=.02,e2e_authority=1.)
  assert c._smoothed==history and c._raw>raw


@pytest.mark.parametrize("changes",[dict(lookahead_time=0.),dict(lookahead_time=2.01),dict(lookahead_time=float('nan')),dict(override_start=.5,override_full=.5),dict(override_start=.6,override_full=.5),dict(override_full=1.01),dict(override_start=-.01)])
def test_invalid_new_tuning_fails_closed(changes):
  r=tick(LaneCenteringController(),**changes)
  assert r.reason=='invalid_input' and r.correction==0.
