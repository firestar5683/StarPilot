import copy
import json
import pytest

from openpilot.starpilot.system.the_galaxy import backup
pytest.importorskip('openpilot.starpilot.common.model_stats_store', reason='Requires optional statistics recorder')
from openpilot.starpilot.common.model_stats_store import read_stats
from openpilot.starpilot.common.tests.test_model_stats_store import recorded


class Params:
  def __init__(self, values=None):
    self.values = dict(values or {})
    self.fail = None
  def get(self, key):
    return self.values.get(key)
  def put(self, key, value):
    if key == self.fail:
      self.fail = None
      raise OSError('Injected write failure')
    self.values[key] = value
  def remove(self, key):
    self.values.pop(key, None)


def test_roundtrip_and_repeat_keeps_all_metrics(tmp_path):
  source, target = tmp_path/'source.sqlite', tmp_path/'target.sqlite'
  recorded(source, complete=True)
  data = backup.export_statistics(source)
  params = Params({'GalaxyDashboardStats': {'version': 1, 'routes': {'new': {'duration': 4}}}})
  history = {'GalaxyDashboardStats': {'version': 1, 'routes': {'old': {'duration': 2}}}}
  result = backup.apply_restore(params, {'GpuModelReadySound': False}, history, data, target, tmp_path/'recovery1', lambda: None)
  assert result['addedDrives'] == 1
  assert read_stats(source)['models'] == read_stats(target)['models']
  assert read_stats(source)['history'] == read_stats(target)['history']
  assert set(params.values['GalaxyDashboardStats']['routes']) == {'new', 'old'}
  result = backup.apply_restore(params, {}, history, data, target, tmp_path/'recovery2', lambda: None)
  assert result['addedDrives'] == 0
  assert read_stats(source)['models'] == read_stats(target)['models']


def test_existing_drive_is_never_overwritten(tmp_path):
  source, target = tmp_path/'source.sqlite', tmp_path/'target.sqlite'
  recorded(source, complete=False)
  recorded(target, complete=True)
  before = backup.export_statistics(target)
  backup.apply_restore(Params(), {}, {}, backup.export_statistics(source), target, tmp_path/'recovery', lambda: None)
  assert backup.export_statistics(target) == before


def test_failed_settings_write_rolls_back_both_stores(tmp_path):
  source, target = tmp_path/'source.sqlite', tmp_path/'target.sqlite'
  recorded(source, complete=True)
  params = Params({'a': b'original'})
  params.fail = 'b'
  with pytest.raises(OSError):
    backup.apply_restore(params, {'a': 'changed', 'b': 'fail'}, {}, backup.export_statistics(source), target, tmp_path/'recovery', lambda: None)
  assert params.values == {'a': b'original'}
  assert backup.export_statistics(target)['drives'] == []
  assert (tmp_path/'recovery/settings-before.json').exists()


@pytest.mark.parametrize('change', ['schema', 'nan', 'negative', 'duplicate', 'orphan', 'identity', 'fractional'])
def test_rejects_corrupt_statistics(tmp_path, change):
  path = tmp_path/'source.sqlite'
  recorded(path, complete=True)
  data = backup.export_statistics(path)
  if change == 'schema': data['schemaVersion'] = 99
  elif change == 'nan': data['metrics'][0]['assistedMeters'] = float('nan')
  elif change == 'negative': data['metrics'][0]['interventions'] = -1
  elif change == 'duplicate': data['drives'].append(copy.deepcopy(data['drives'][0]))
  elif change == 'orphan': data['metrics'][0]['drive'] = 'missing'
  elif change == 'identity': data['metrics'][0]['owner'] = '{}'
  elif change == 'fractional': data['metrics'][0]['interventions'] = .5
  with pytest.raises(ValueError): backup.validate_statistics(data)


def test_onroad_refusal_writes_nothing(tmp_path):
  def parked(): raise ValueError('onroad')
  with pytest.raises(ValueError):
    backup.apply_restore(Params(), {}, {}, {}, tmp_path/'db', tmp_path/'recovery', parked)
  assert list(tmp_path.iterdir()) == []


def test_lifetime_totals_keep_larger_values_without_summing(tmp_path):
  params = Params({'StarPilotStats': {'StarPilotMeters': 200, 'StarPilotSeconds': 10, 'Month': 9, 'CurrentMonthsMeters': 20, 'ModelTimes': {'a': 50}}})
  history = {'StarPilotStats': {'StarPilotMeters': 100, 'StarPilotSeconds': 30, 'Month': 8, 'CurrentMonthsMeters': 100, 'ModelTimes': {'a': 60, 'b': 5}}}
  empty = {'schemaVersion': 1, 'drives': [], 'metrics': []}
  backup.apply_restore(params, {}, history, empty, tmp_path/'db', tmp_path/'r1', lambda: None)
  expected = {'StarPilotMeters': 200, 'StarPilotSeconds': 30, 'Month': 9, 'CurrentMonthsMeters': 20, 'ModelTimes': {'a': 60, 'b': 5}}
  assert params.values['StarPilotStats'] == expected
  backup.apply_restore(params, {}, history, empty, tmp_path/'db', tmp_path/'r2', lambda: None)
  assert params.values['StarPilotStats'] == expected
