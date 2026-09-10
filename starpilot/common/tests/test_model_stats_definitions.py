import json
import sqlite3
import pytest
from openpilot.starpilot.common.model_stats_store import Store, read_stats
from openpilot.starpilot.common.tests.test_model_stats_store import recorded
from openpilot.starpilot.common.tests.test_model_stats_log_recovery import fixture
from openpilot.starpilot.common.model_stats_recovery import import_routes
from openpilot.starpilot.system.the_galaxy.backup import export_statistics


def set_policy(path, drive, version, release=None):
  with sqlite3.connect(path) as db:
    state=json.loads(db.execute('SELECT state FROM drives WHERE id=?',(drive,)).fetchone()[0])
    state.pop('definitionVersion',None)
    state.pop('interventionReleaseSeconds',None)
    if version is not None: state['definitionVersion']=version
    if release is not None: state['interventionReleaseSeconds']=release
    db.execute('UPDATE drives SET state=? WHERE id=?',(json.dumps(state),drive))


def test_mixed_definitions_keep_counters_and_distance_but_have_no_event_rates(tmp_path):
  path=tmp_path/'stats.sqlite'
  recorded(path,'v1',complete=True)
  set_policy(path,'v1',None)
  recorded(path,'v2',complete=True)
  before=export_statistics(path)
  result=read_stats(path)
  stats=result['models']['rdf43']['stats']
  assert stats['assistedMeters']==pytest.approx(20.2)
  assert stats['interventions']==stats['disengagements']==2
  assert stats['eventRatesComparable'] is False
  assert stats['definitionStatus']=='mixed'
  assert stats['milesPerIntervention'] is None
  assert stats['milesPerDisengagement'] is None
  assert result['definitionVersion'] is None
  assert result['currentDefinitionVersion']==2
  assert all(row['stats']['milesPerIntervention'] is None for row in result['comparisons'])
  assert {h['definitionVersion'] for h in result['history']}=={1,2}
  assert all(h['stats']['eventRatesComparable'] for h in result['history'])
  assert export_statistics(path)==before


@pytest.mark.parametrize('version,release,status,comparable',[(None,None,'historical',True),(2,2,'current',True),(7,2,'unknown',False),(2,.5,'unknown',False)])
def test_single_definition_provenance(tmp_path,version,release,status,comparable):
  path=tmp_path/'stats.sqlite'
  recorded(path,complete=True)
  set_policy(path,'drive1',version,release)
  result=read_stats(path)
  stats=result['models']['rdf43']['stats']
  assert stats['definitionStatus']==status
  assert stats['eventRatesComparable'] is comparable
  assert (stats['milesPerIntervention'] is not None)==comparable
  assert result['history'][0]['stats']['eventRatesComparable'] is comparable


def test_cross_definition_recovery_refused_without_changes(tmp_path):
  path=tmp_path/'stats.sqlite'
  _,route=fixture(path)
  set_policy(path,'original',None)
  before=export_statistics(path)
  with pytest.raises(ValueError,match='definition'):
    import_routes(path,[route],tmp_path/'backup.sqlite')
  assert export_statistics(path)==before
  assert not (tmp_path/'backup.sqlite').exists()


def test_same_historical_definition_recovery_preserves_policy(tmp_path):
  path=tmp_path/'stats.sqlite'
  _,route=fixture(path)
  set_policy(path,'original',None)
  route['snapshot'].pop('definitionVersion')
  route['snapshot'].pop('interventionReleaseSeconds')
  assert import_routes(path,[route],tmp_path/'backup.sqlite')['added']==1
  result=read_stats(path)
  assert result['history'][0]['definitionVersion']==1
  assert result['models']['rdf43']['stats']['definitionStatus']=='historical'


def test_different_revisions_still_mark_pooled_model_mixed(tmp_path):
  from openpilot.starpilot.common.tests.test_model_stats import OWNER
  path=tmp_path/'stats.sqlite'
  recorded(path,'old',complete=True)
  set_policy(path,'old',None)
  identity=json.loads(OWNER)
  identity['roles'][0]['artifact']='another-loaded-revision'
  recorded(path,'new',owner=json.dumps(identity),complete=True)
  result=read_stats(path)
  assert len(result['comparisons'])==2
  assert all(row['stats']['eventRatesComparable'] for row in result['comparisons'])
  assert result['models']['rdf43']['stats']['eventRatesComparable'] is False
  assert result['models']['rdf43']['stats']['assistedMeters']==pytest.approx(20.2)


def test_explicit_null_policy_is_unknown_not_legacy(tmp_path):
  path=tmp_path/'stats.sqlite'
  recorded(path,complete=True)
  with sqlite3.connect(path) as db:
    state=json.loads(db.execute('SELECT state FROM drives').fetchone()[0])
    state['definitionVersion']=None
    state['interventionReleaseSeconds']=None
    db.execute('UPDATE drives SET state=?',(json.dumps(state),))
  result=read_stats(path)
  assert result['models']['rdf43']['stats']['definitionStatus']=='unknown'
  assert result['history'][0]['stats']['definitionStatus']=='unknown'


@pytest.mark.parametrize('version,release', [(True, .5), (False, .5), (1.0, .5), ('1', .5), (2, True), (2, '2')])
def test_invalid_policy_scalar_types_remain_unknown_in_aggregates(tmp_path, version, release):
  path = tmp_path / 'stats.sqlite'
  recorded(path, complete=True)
  set_policy(path, 'drive1', version, release)
  before = export_statistics(path)
  result = read_stats(path)
  for stats in [result['models']['rdf43']['stats'], result['history'][0]['stats'], result['comparisons'][0]['stats']]:
    assert stats['definitionStatus'] == 'unknown'
    assert stats['eventRatesComparable'] is False
    assert stats['milesPerIntervention'] is None
    assert stats['assistedMeters'] == pytest.approx(10.1)
    assert stats['interventions'] == 1
  assert export_statistics(path) == before
