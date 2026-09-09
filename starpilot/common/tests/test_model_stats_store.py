import json
import sqlite3

import pytest

from openpilot.starpilot.common.model_stats import Reducer
from openpilot.starpilot.common.model_stats_store import Store, read_stats
from openpilot.starpilot.common.tests.test_model_stats import OWNER, OTHER, feed, sample


def recorded(path, drive='drive1', owner=OWNER, complete=False):
  r = Reducer()
  feed(r, 0, 101, owner=owner)
  r.update(sample(1.01, owner=owner, brake=True, enabled=False))
  store = Store(path)
  store.checkpoint(drive, 1700000000, r.snapshot(), complete=complete, now=1700000010)
  store.close()
  return r


def test_checkpoint_idempotent_atomic_cursor_and_restart(tmp_path):
  path = tmp_path / 'stats.sqlite'
  r = recorded(path)
  before = read_stats(path)
  store = Store(path)
  store.checkpoint('drive1', 1700000000, r.snapshot(), now=1700000010)
  store.checkpoint('drive1', 1700000000, {'sequence': 0}, now=1700000010)
  state = json.loads(store.db.execute('SELECT state FROM drives').fetchone()[0])
  assert state['sequence'] == r.sequence
  assert state['previous']['brake']
  assert read_stats(path) == before
  store.close()
  assert before['incompleteDrives'] == 1
  assert before['models']['rdf43']['stats']['incomplete']
  # Restart is a separate incomplete fragment; an input held at startup adds no edge.
  restarted = Reducer()
  feed(restarted, 0, 20, brake=True)
  store = Store(path)
  store.checkpoint('restart', 1700000020, restarted.snapshot(), complete=True)
  store.close()
  assert read_stats(path)['models']['rdf43']['stats']['interventions'] == 1


def test_all_time_multiple_drives_no_average_of_ratios(tmp_path):
  path = tmp_path / 'stats.sqlite'
  recorded(path, complete=True)
  r = Reducer()
  feed(r, 0, 201)
  store = Store(path)
  store.checkpoint('drive2', 1700000040, r.snapshot(), complete=True)
  store.close()
  result = read_stats(path, model='rdf43', limit=1)
  stats = result['models']['rdf43']['stats']
  assert stats['assistedMeters'] == pytest.approx(30.1)
  assert stats['interventions'] == stats['disengagements'] == 1
  assert stats['milesPerDisengagement'] == pytest.approx(stats['disengagementMeters'] / 1609.344)
  assert result['historyTotal'] == 2 and result['hasMore']
  assert len(read_stats(path, offset=1)['history']) == 1


def test_pair_never_duplicated_into_standalone(tmp_path):
  identity = json.loads(OWNER)
  identity['roles'].append(json.loads(OTHER)['roles'][0])
  path = tmp_path / 'stats.sqlite'
  recorded(path, owner=json.dumps(identity), complete=True)
  result = read_stats(path, model='rdf43')
  assert result['models'] == {}
  assert result['pairs'][0]['modelIds'] == ['rdf43', 'gpu']
  assert result['pairs'][0]['stats']['assistedMeters'] == pytest.approx(10.1)
  assert len(result['history']) == 1
  assert read_stats(path, model='not-present')['historyTotal'] == 0


def test_completed_snapshot_cannot_be_overwritten(tmp_path):
  path = tmp_path / 'stats.sqlite'
  r = recorded(path, complete=True)
  before = read_stats(path)
  feed(r, 102, 200)
  store = Store(path)
  store.checkpoint('drive1', 1700000000, r.snapshot())
  store.close()
  assert read_stats(path) == before


def test_missing_corrupt_unknown_schema_never_reset(tmp_path):
  path = tmp_path / 'stats.sqlite'
  assert read_stats(path)['status'] == 'not_started'
  assert not path.exists()
  path.write_bytes(b'broken database')
  assert read_stats(path)['status'] == 'unavailable'
  with pytest.raises(sqlite3.Error):
    Store(path)
  assert path.read_bytes() == b'broken database'
  path.unlink()
  with sqlite3.connect(path) as db:
    db.execute('PRAGMA user_version=99')
  with pytest.raises(ValueError):
    Store(path)
  assert read_stats(path)['status'] == 'unavailable'
  with sqlite3.connect(path) as db:
    assert db.execute('PRAGMA user_version').fetchone()[0] == 99


def test_failed_checkpoint_rolls_back_cursor_and_counters(tmp_path):
  path = tmp_path / 'stats.sqlite'
  r = recorded(path)
  store = Store(path)
  before = read_stats(path)
  feed(r, 102, 120)
  snapshot = r.snapshot()
  snapshot['metrics'][0]['assistedMeters'] = None  # NOT NULL constraint fails after drive upsert
  with pytest.raises(sqlite3.IntegrityError):
    store.checkpoint('drive1', 1700000000, snapshot)
  assert read_stats(path) == before
  store.close()


def test_read_only_api_cannot_change_database(tmp_path):
  path = tmp_path / 'stats.sqlite'
  recorded(path, complete=True)
  before = path.read_bytes()
  result = read_stats(path, model="' OR 1=1 --")
  assert result['available'] and result['models'] == {}
  assert path.read_bytes() == before


@pytest.mark.parametrize('kwargs', [{'mode': 'invalid'}, {'limit': 0}, {'limit': 201}, {'offset': -1}])
def test_invalid_query_rejected(tmp_path, kwargs):
  with pytest.raises(ValueError):
    read_stats(tmp_path / 'no-db', **kwargs)


def test_history_preserves_legacy_and_two_second_grouping_without_recounting(tmp_path):
  path=tmp_path/'stats.sqlite'
  r=recorded(path,complete=True)
  current=read_stats(path)['history'][0]
  assert current['definitionVersion']==2 and current['interventionReleaseSeconds']==2.0
  store=Store(path)
  snapshot=r.snapshot()
  snapshot.pop('definitionVersion');snapshot.pop('interventionReleaseSeconds')
  store.checkpoint('legacy',1600000000,snapshot,complete=True,now=1600000001)
  store.close()
  legacy=next(row for row in read_stats(path)['history'] if row['drive']=='legacy')
  assert legacy['definitionVersion']==1 and legacy['interventionReleaseSeconds']==0.5
  assert legacy['stats']['interventions']==current['stats']['interventions']
