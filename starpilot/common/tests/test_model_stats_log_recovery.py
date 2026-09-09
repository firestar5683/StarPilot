import json
import sqlite3
import pytest
from openpilot.starpilot.common.model_stats import Reducer
from openpilot.starpilot.common.model_stats_store import Store, read_stats
from openpilot.starpilot.common.model_stats_recovery import import_routes
from openpilot.starpilot.common.tests.test_model_stats import feed
from openpilot.starpilot.system.the_galaxy.backup import export_statistics, merge_statistics

def fixture(path, manual=False):
  reducer = Reducer()
  feed(reducer, 0, 51, enabled=not manual)
  store = Store(path)
  store.checkpoint('original',100,reducer.snapshot(),complete=True,now=101)
  store.close()
  old = export_statistics(path)
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
  assert len(export_statistics(path)['drives'])==2
  assert export_statistics(tmp_path/'before.sqlite')==old

@pytest.mark.parametrize('reverse',[True,False])
def test_backups_restored_in_either_order_do_not_revive_partial_counts(tmp_path,reverse):
  path=tmp_path/'source.sqlite'
  old,route=fixture(path)
  import_routes(path,[route],tmp_path/'before.sqlite')
  new=export_statistics(path)
  target=Store(tmp_path/'restored.sqlite')
  for data in ([old,new] if reverse else [new,old]):
    with target.db:merge_statistics(target.db,data)
  with target.db:assert merge_statistics(target.db,new)==0
  assert read_stats(target.path)==read_stats(path)
  target.close()

def test_partial_or_ambiguous_reconstruction_does_not_change_database(tmp_path):
  path=tmp_path/'stats.sqlite'
  old,route=fixture(path)
  bad=json.loads(json.dumps(route));bad['snapshot']['metrics'][0]['assistedMeters']=0
  with pytest.raises(ValueError,match='reduce'):
    import_routes(path,[bad],tmp_path/'bad.sqlite')
  other={**route,'routeName':'overlap'}
  with pytest.raises(ValueError,match='Ambiguous'):
    import_routes(path,[route,other],tmp_path/'bad.sqlite')
  assert export_statistics(path)==old
  assert not (tmp_path/'bad.sqlite').exists()
