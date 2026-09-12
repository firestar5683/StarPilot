import json
import sqlite3
import pytest
from openpilot.starpilot.common.model_stats import Reducer
from openpilot.starpilot.common.model_stats_store import Store, read_stats
from openpilot.starpilot.common.model_stats_recovery import import_routes
from openpilot.starpilot.common.tests.test_model_stats import feed
def database_rows(path):
  with sqlite3.connect(path) as db:
    return {table: db.execute('SELECT * FROM ' + table + ' ORDER BY 1, 2').fetchall()
            for table in ('drives', 'metrics')}


def fixture(path, manual=False):
  reducer = Reducer()
  feed(reducer, 0, 51, enabled=not manual)
  store = Store(path)
  store.checkpoint('original',100,reducer.snapshot(),complete=True,now=101)
  store.close()
  old = database_rows(path)
  feed(reducer,51,101,enabled=not manual)
  route = {'routeName':'route', 'started':100, 'updated':101.5, 'snapshot':reducer.snapshot()}
  return old, route

@pytest.mark.parametrize('manual',[True,False])
def test_recovery_keeps_original_but_counts_only_replay_and_repeats_safely(tmp_path,manual):
  path=tmp_path/'stats.sqlite'
  old, route=fixture(path,manual)
  report=import_routes(path,[route],tmp_path/'before.sqlite')
  assert report == {'added':1,'superseded':1}
  after=read_stats(path)
  assert after['driveSummaries'][0]['routeName']=='route'
  assert len(after['driveSummaries'])==1
  assert after['driveSummaries'][0]['stats']['interventions']==0
  if not manual:
    assert after['models']['rdf43']['stats']['assistedMeters']==pytest.approx(10)
  assert import_routes(path,[route],tmp_path/'never-created.sqlite')['added']==0
  assert not (tmp_path/'never-created.sqlite').exists()
  assert read_stats(path)==after
  assert len(database_rows(path)['drives'])==2
  assert database_rows(tmp_path/'before.sqlite')==old

def test_partial_or_ambiguous_reconstruction_does_not_change_database(tmp_path):
  path=tmp_path/'stats.sqlite'
  old,route=fixture(path)
  bad=json.loads(json.dumps(route));bad['snapshot']['metrics'][0]['assistedMeters']=0
  with pytest.raises(ValueError,match='reduce'):
    import_routes(path,[bad],tmp_path/'bad.sqlite')
  other={**route,'routeName':'overlap'}
  with pytest.raises(ValueError,match='Ambiguous'):
    import_routes(path,[route,other],tmp_path/'bad.sqlite')
  assert database_rows(path)==old
  assert not (tmp_path/'bad.sqlite').exists()
