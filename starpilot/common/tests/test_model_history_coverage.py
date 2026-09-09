import pytest
from openpilot.starpilot.common.model_stats import Reducer
from openpilot.starpilot.common.model_stats_store import Store, read_stats
from openpilot.starpilot.common.tests.test_model_stats import feed

@pytest.mark.parametrize('complete,gaps', [(True, 3), (False, 0), (True, 0)])
def test_history_coverage_independent_of_drive_closure(tmp_path, complete, gaps):
  reducer = Reducer()
  feed(reducer, 0, 101)
  snapshot = reducer.snapshot()
  snapshot['gaps'] = gaps
  path = tmp_path / 'stats.sqlite'
  store = Store(path)
  store.checkpoint('drive', 1700000000, snapshot, complete=complete)
  store.close()
  entry = read_stats(path)['history'][0]
  assert bool(entry['complete']) == complete
  assert entry['gaps'] == gaps
  assert entry['stats']['incomplete'] == (not complete or gaps > 0)
