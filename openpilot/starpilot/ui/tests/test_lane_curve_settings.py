"""SP-016 Galaxy conditional controls and independent min/max persistence."""
import pytest
from openpilot.starpilot.ui.tests.test_lane_v4_settings import f,edit
from openpilot.starpilot.lateral.lane_runtime import read_settings
from openpilot.starpilot.galaxy.settings import SettingsChanged
from openpilot.starpilot.ui import lane_v4_menu
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest

def test_root_order_and_disabled_children(f):
  root=f.page('lane')
  keys=[r['label'] for r in root['rows']]
  assert keys[keys.index('Pause on signal')+1]=='Curve adaptation'
  edit(f,'lane','Curve adaptation','Off')
  for page,normal,child in [('lane/preferences/smoothing','Maximum correction response time','Minimum correction response time'),
                            ('lane/preferences','Maximum model path preference','Minimum model path preference')]:
    rows={r['label']:r for r in f.page(page)['rows']}
    assert rows[normal]['available'] and not rows[child]['available']
    assert 'Turn on Curve adaptation' in rows[child]['reason']
  rows=f.page('lane/preferences/curves')['rows']
  assert all(not r['available'] for r in rows if r['label'] in ('Maximum corner radius','Minimum corner radius'))
  with pytest.raises(SettingsChanged):edit(f,'lane/preferences/smoothing','Minimum correction response time',.2)

def test_split_clearance_and_persistence(f):
  edit(f,'lane/activation/geometry','Two-boundary minimum clearance',40)
  edit(f,'lane/activation/geometry','Single-boundary minimum clearance',20)
  s=read_settings(f.params)
  assert s.clearance==.4 and s.single_clearance==.2 and s.min_width==pytest.approx(2.65)

@pytest.mark.parametrize('page,label,value,message',[
 ('lane/preferences/smoothing','Minimum correction response time',.5,'cannot exceed'),
 ('lane/preferences/smoothing','Maximum correction response time',.05,'cannot exceed'),
 ('lane/preferences/curves','Minimum corner radius',1000,'must be below'),
 ('lane/preferences/curves','Maximum corner radius',250,'must be below')])
def test_invalid_pairs_explained(f,page,label,value,message):
  if label == 'Minimum corner radius':
    edit(f,page,'Maximum corner radius',1000)
  row=next(r for r in f.gateway._state(page,f.context.value).rows if r.label==label)
  request=FeatureSettingsRequest(row.key,row.source,str(value),dependencies=row.dependencies,display_unit=row.display_unit)
  assert message in lane_v4_menu.edit_error(f.gateway._owner(f.context.value),request)
  with pytest.raises(SettingsChanged,match='outside setting range'):edit(f,page,label,value)

def test_e2e_minmax_and_stale_toggle(f):
  edit(f,'lane/preferences','Minimum model path preference',50)
  with pytest.raises(SettingsChanged,match='outside setting range'):edit(f,'lane/preferences','Maximum model path preference',25)
  page=f.page('lane/preferences/smoothing');i=next(i for i,r in enumerate(page['rows']) if r['label']=='Minimum correction response time')
  intent=f.gateway.preview(page['view'],i,0,f.session,f.generation,value=.25)
  f.params.put_bool('LaneCenteringV4CurveAdaptation',False,block=True)
  assert not f.gateway.confirm(intent['intent'],f.session,f.generation)
  assert read_settings(f.params).response_min==.1

def test_values_survive_toggle_and_defaults_are_concrete(f):
  edit(f,'lane/preferences/smoothing','Minimum correction response time',.25)
  edit(f,'lane','Curve adaptation','Off')
  edit(f,'lane/preferences/smoothing','Maximum correction response time',.35)
  edit(f,'lane','Curve adaptation','On')
  s=read_settings(f.params)
  assert s.response_min==.25 and s.response_tau==.35
  assert s.curve_start_radius==2000 and s.curve_full_radius==250
