"""Real Params/runtime/owner/Galaxy integration for v4 settings."""
from dataclasses import replace
from pathlib import Path
import pytest
from openpilot.starpilot.galaxy.tests import test_settings as fixtures
from openpilot.starpilot.galaxy.settings import SettingsChanged
from openpilot.starpilot.ui import lane_v4_menu
from openpilot.starpilot.ui.feature_settings_state import feature_parent_page
from openpilot.starpilot.lateral.lane_tuning import NUMBERS,PREFIX,KEYS
from openpilot.starpilot.lateral.lane_runtime import read_settings
from openpilot.starpilot.lateral.lane_centering import LaneCenteringSettings

@pytest.fixture
def f():
  v=fixtures.SettingsGatewayTest();v.setUp()
  yield v
  v.doCleanups()

def edit(f,page,label,value=None,reset=False):
  p=f.page(page);i=next(i for i,r in enumerate(p['rows']) if r['label']==label)
  intent=f.gateway.preview(p['view'],i,0,f.session,f.generation,**({'reset_default':True} if reset else {'value':value}))
  assert f.gateway.confirm(intent['intent'],f.session,f.generation)

def test_registered_defaults_runtime_and_native_rows(f):
  assert read_settings(f.params)==replace(LaneCenteringSettings(), enabled=True)
  for field,row in NUMBERS.items():
    assert f.params.get_default_value(PREFIX+row[0])==pytest.approx(row[1])
    assert getattr(read_settings(f.params),field)==row[1]
  owner=f.gateway._owner(f.context.value)
  native=owner.snapshot('lane',parked=True,system_long=True,lateral_context=True,metric=False)
  assert [r.key for r in native.rows]==['LaneCentering','LaneCenteringPauseOnSignal','LaneCenterOffset','LaneCenteringE2EAuthority','LaneCenteringStrength']
  root=f.gateway._state('lane',f.context.value)
  enable = next(r for r in root.rows if r.key == 'LaneCentering')
  assert enable.value == enable.default_value == 'On'
  assert {r.page for r in root.rows if r.page}=={'lane/activation','lane/preferences'}
  collected=[r for r in root.rows if r.key]
  for page in lane_v4_menu.PAGES:
    assert feature_parent_page(page)==page.rsplit('/',1)[0]
    collected.extend(r for r in f.gateway._state(page,f.context.value).rows if r.key)
  assert len(collected)==len(KEYS)+5
  assert len({r.key for r in collected})==len(collected)
  assert all(r.reason for r in collected)

def test_live_tuning_and_conversions(f):
  edit(f,'lane','Enable Lane Centering','On')
  edit(f,'lane/preferences/smoothing','Boundary smoothing time',.61)
  edit(f,'lane/preferences/smoothing','Maximum boundary smoothing distance',12)
  edit(f,'lane/activation/acceptance/higher_confidence','Minimum confidence',40)
  edit(f,'lane/activation/geometry','Two-boundary minimum clearance',45)
  s=read_settings(f.params)
  assert s.enabled and s.smoothing_tau==.61 and s.smoothing_distance==.12 and s.confidence_split==.4 and s.clearance==.45
  f.context.value=replace(f.context.value,parked=False)
  edit(f,'lane/preferences/smoothing','Boundary smoothing time',.32)
  assert read_settings(f.params).smoothing_tau==.32

@pytest.mark.parametrize('metric,unit,value,expected',[(False,'mph',20,20*.44704),(True,'km/h',36,10.)])
def test_minimum_speed_units_and_exact_default(f,metric,unit,value,expected):
  f.params.put_bool('IsMetric',metric,block=True)
  p=f.page('lane/activation');r=next(r for r in p['rows'] if r['label']=='Minimum speed')
  assert r['unit']==unit and r['step']==1
  edit(f,'lane/activation','Minimum speed',value)
  assert read_settings(f.params).min_speed_mps==pytest.approx(expected,abs=.00005)
  edit(f,'lane/activation','Minimum speed',reset=True)
  assert read_settings(f.params).min_speed_mps==pytest.approx(0.)

@pytest.mark.parametrize('page,label,value,message',[
 ('lane/activation/geometry','Car body width',3.,'below maximum'),
 ('lane/activation/geometry','Maximum lane width',2.55,'below maximum'),
 ('lane/activation/acceptance/lower_confidence','Minimum confidence',31,'cannot exceed'),
 ('lane/activation/acceptance/higher_confidence','Minimum confidence',9,'cannot exceed')])
def test_contradictory_edits_rejected_with_explanation(f,page,label,value,message):
  if label == 'Car body width':
    edit(f,page,'Maximum lane width',3.)
  elif label == 'Maximum lane width':
    edit(f,page,'Two-boundary minimum clearance',35)
  before = read_settings(f.params)
  with pytest.raises(SettingsChanged,match=message):edit(f,page,label,value)
  assert read_settings(f.params)==before

def test_independent_uncertainty_and_clearance_allowed(f):
  edit(f,'lane/activation/acceptance/lower_confidence','Maximum position uncertainty',2.)
  edit(f,'lane/activation/geometry','Two-boundary minimum clearance',100)
  edit(f,'lane/activation/geometry','Maximum lane width',6.)
  edit(f,'lane/activation/geometry','Car body width',3.)
  assert read_settings(f.params).low_std==2. and read_settings(f.params).clearance==1.

def test_dependency_change_prevents_confirmation(f):
  p=f.page('lane/activation/geometry');i=next(i for i,r in enumerate(p['rows']) if r['label']=='Car body width')
  intent=f.gateway.preview(p['view'],i,0,f.session,f.generation,value=3.)
  f.params.put(PREFIX+'MaxWidth',2.9,block=True)
  assert not f.gateway.confirm(intent['intent'],f.session,f.generation)
  assert f.params.get(PREFIX+'CarWidth') is None

@pytest.mark.parametrize('key,value',[(PREFIX+'SmoothingTime',b'nan'),(PREFIX+'MaxCorrection',b'.0025'),(PREFIX+'MinConfidence',b'.9')])
def test_malformed_stored_settings_disable(f,key,value):
  f.params.put_bool('LaneCentering',True,block=True)
  Path(f.params.get_param_path(key)).write_bytes(value)
  assert not read_settings(f.params).enabled

def test_vehicle_and_unit_change_reject_stale_intent(f):
  for change in ('vehicle','units'):
    p=f.page('lane/activation');i=next(i for i,r in enumerate(p['rows']) if r['label']=='Minimum speed')
    intent=f.gateway.preview(p['view'],i,0,f.session,f.generation,value=20)
    if change=='vehicle':f.context.value=replace(f.context.value,cp_raw=b'changed')
    else:f.params.put_bool('IsMetric',True,block=True)
    if change=='vehicle':
      with pytest.raises(SettingsChanged,match='Vehicle changed'):
        f.gateway.confirm(intent['intent'],f.session,f.generation)
    else:
      assert not f.gateway.confirm(intent['intent'],f.session,f.generation)


@pytest.mark.parametrize('field,label,suffix,default', [('response_tau','Maximum correction response time','ResponseTime',.35),('release_tau','Return-to-model time','ReleaseTime',.2)])
def test_controller_time_persistence_reset_and_validation(f,field,label,suffix,default):
  page='lane/preferences/smoothing'
  row=next(r for r in f.page(page)['rows'] if r['label']==label)
  assert row['unit']=='s' and row['step']==.01
  if field == 'response_tau':
    edit(f,page,'Minimum correction response time',0.)
  for value in (0.,.17,1.):
    edit(f,page,label,value)
    assert getattr(read_settings(f.params),field)==value
    assert float(Path(f.params.get_param_path(PREFIX+suffix)).read_text())==value
  edit(f,page,label,reset=True)
  assert getattr(read_settings(f.params),field)==default
  f.params.put_bool('LaneCentering',True,block=True)
  for invalid in (b'nan',b'-0.01',b'1.01'):
    Path(f.params.get_param_path(PREFIX+suffix)).write_bytes(invalid)
    assert not read_settings(f.params).enabled


def test_acceptance_group_navigation_and_persistence(f):
  parent = 'lane/activation/acceptance'
  rows = f.page(parent)['rows']
  assert [r['label'] for r in rows] == ['Higher-confidence lane lines', 'Lower-confidence lane lines', 'Road edge maximum position uncertainty']
  assert [r['page'] for r in rows[:2]] == [parent + '/higher_confidence', parent + '/lower_confidence']
  before = read_settings(f.params)
  for group in ('higher_confidence', 'lower_confidence'):
    rows = f.page(parent + '/' + group)['rows']
    assert [r['label'] for r in rows] == ['Minimum confidence', 'Maximum position uncertainty']
    assert rows[0]['unit'] == '%' and rows[0]['step'] == 1
    assert rows[1]['unit'] == 'm' and rows[1]['step'] == .05
  assert read_settings(f.params) == before
  edit(f, parent + '/higher_confidence', 'Maximum position uncertainty', .85)
  edit(f, parent + '/lower_confidence', 'Maximum position uncertainty', .4)
  edit(f, parent, 'Road edge maximum position uncertainty', .75)
  settings = read_settings(f.params)
  assert (settings.high_std, settings.low_std, settings.edge_std) == (.85, .4, .75)


def test_single_deadband_slider_defaults_persistence_and_reset(f):
  page=f.page('lane/preferences')
  row=next(r for r in page['rows'] if r['label']=='Deadband')
  assert row['unit']=='cm' and row['minimum']==0 and row['maximum']==15 and row['step']==1
  assert float(row['value'])==2
  assert read_settings(f.params).single_clearance == .45
  edit(f,'lane/preferences','Deadband',5)
  assert read_settings(f.params).single_deadband == .05
  # Existing saved clearance survives the new missing/reset default.
  edit(f,'lane/activation/geometry','Single-boundary minimum clearance',30)
  assert read_settings(f.params).single_clearance == .30
  edit(f,'lane/preferences','Deadband',reset=True)
  assert read_settings(f.params).single_deadband == .02
  with pytest.raises(SettingsChanged):edit(f,'lane/preferences','Deadband',16)
  edit(f,'lane/activation/geometry','Single-boundary minimum clearance',reset=True)
  assert read_settings(f.params).single_clearance == .45
  f.context.value=replace(f.context.value,cp=None,cp_raw=None)
  row=next(r for r in f.page('lane/preferences')['rows'] if r['label']=='Deadband')
  assert not row['available']


@pytest.mark.parametrize('adaptation',[False,True])
def test_override_pair_independent_of_curve_toggle_and_order(f,adaptation):
  f.params.put_bool(PREFIX+'CurveAdaptation',adaptation,block=True)
  rows=f.page('lane/preferences')['rows']
  assert [r['label'] for r in rows[:4]]==['Lane Centering Strength','Maximum correction','Deadband','Lookahead time']
  pair=[r for r in rows if (r.get('rangePair') or {}).get('group')=='override']
  assert len(pair)==2 and all(r['available'] and r['rangePair']['enabled'] for r in pair)
  assert all(r['step']==1 and r['minimum']==0 and r['maximum']==100 and r['unit']=='cm' for r in pair)
  assert [float(r['value']) for r in pair]==[15.,50.]
  edit(f,'lane/preferences','Start model override',20)
  edit(f,'lane/preferences','Full model override',60)
  settings=read_settings(f.params);assert (settings.override_start,settings.override_full)==(.2,.6)
  for label,value in [('Start model override',60),('Full model override',20)]:
    with pytest.raises(SettingsChanged,match='must be below'):edit(f,'lane/preferences',label,value)
    assert read_settings(f.params)==settings
  edit(f,'lane/preferences','Start model override',reset=True)
  edit(f,'lane/preferences','Full model override',reset=True)
  assert (read_settings(f.params).override_start,read_settings(f.params).override_full)==(.15,.5)


def test_lookahead_persistence_bounds_reset_and_authority(f):
  row=next(r for r in f.page('lane/preferences')['rows'] if r['label']=='Lookahead time')
  assert (row['minimum'],row['maximum'],row['step'],row['unit'])==(.5,2.,.05,'s')
  for value in (.5,1.25,2.):
    edit(f,'lane/preferences','Lookahead time',value)
    assert read_settings(f.params).lookahead_time==value
  with pytest.raises(SettingsChanged):edit(f,'lane/preferences','Lookahead time',2.05)
  edit(f,'lane/preferences','Lookahead time',reset=True)
  assert read_settings(f.params).lookahead_time==1.
  f.context.value=replace(f.context.value,cp=None,cp_raw=None)
  assert all(not r['available'] for r in f.page('lane/preferences')['rows'] if r['label'] in ['Lookahead time','Start model override','Full model override'])


def test_override_peer_change_rejects_stale_confirmation(f):
  p=f.page('lane/preferences');i=next(i for i,r in enumerate(p['rows']) if r['label']=='Start model override')
  intent=f.gateway.preview(p['view'],i,0,f.session,f.generation,value=30)
  f.params.put(PREFIX+'OverrideFull',.25,block=True)
  assert not f.gateway.confirm(intent['intent'],f.session,f.generation)
  assert f.params.get(PREFIX+'OverrideStart') is None


@pytest.mark.parametrize('key,value', [('LookaheadTime',b'nan'),('LookaheadTime',b'.49'),('OverrideStart',b'.5'),('OverrideFull',b'.1')])
def test_invalid_saved_new_tuning_disables(f,key,value):
  f.params.put_bool('LaneCentering',True,block=True)
  Path(f.params.get_param_path(PREFIX+key)).write_bytes(value)
  assert not read_settings(f.params).enabled
