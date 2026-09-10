import copy
import json
import sqlite3

import pytest

from openpilot.starpilot.system.the_galaxy import backup
pytest.importorskip('openpilot.starpilot.common.model_stats_store', reason='Requires optional statistics recorder')
from openpilot.starpilot.common.model_stats_store import read_stats
from openpilot.starpilot.common.model_stats_recovery import import_routes
from openpilot.starpilot.common.tests.test_model_stats_log_recovery import fixture
from openpilot.starpilot.common.tests.test_model_stats_store import recorded
from test_backup import Params


def test_silent_setting_failure_rolls_back_statistics_and_prior_settings(tmp_path):
  class SilentFailure(Params):
    def put(self, key, value):
      if key != 'GpuModelReadySound':
        super().put(key, value)
  source, target = tmp_path/'source.sqlite', tmp_path/'target.sqlite'
  recorded(source, complete=True)
  params = SilentFailure({'GpuModelReadySound': True, 'a': 'before'})
  with pytest.raises(OSError, match='GpuModelReadySound'):
    backup.apply_restore(params, {'a': 'after', 'GpuModelReadySound': False}, {}, backup.export_statistics(source),
                         target, tmp_path/'recovery', lambda: None)
  assert params.values == {'GpuModelReadySound': True, 'a': 'before'}
  assert backup.export_statistics(target)['drives'] == []


def test_rollback_attempts_every_setting_and_reports_incomplete_recovery(tmp_path):
  class BrokenRollback(Params):
    def put(self, key, value):
      if key == 'fail' or (key == 'a' and value == 'old-a'):
        raise OSError('Injected write failure')
      super().put(key, value)
  source, target = tmp_path/'source.sqlite', tmp_path/'target.sqlite'
  recorded(source, complete=True)
  params = BrokenRollback({'a': 'old-a', 'b': 'old-b'})
  with pytest.raises(OSError, match='(?i)rollback incomplete.*a'):
    backup.apply_restore(params, {'a': 'new-a', 'b': 'new-b', 'fail': 'x'}, {}, backup.export_statistics(source),
                         target, tmp_path/'recovery', lambda: None)
  assert params.get('b') == 'old-b'
  assert params.get('fail') is None
  assert backup.export_statistics(target)['drives'] == []


@pytest.mark.parametrize('damage', ['count', 'checkpoint_count', 'checkpoint_bool', 'extra_metric', 'missing_metric', 'duplicate_checkpoint'])
def test_checkpoint_and_table_must_agree(tmp_path, damage):
  source = tmp_path/'source.sqlite'
  recorded(source, complete=True)
  data = backup.export_statistics(source)
  state = json.loads(data['drives'][0]['state'])
  if damage == 'count': data['metrics'][0]['interventions'] += 1000
  elif damage == 'checkpoint_count': state['metrics'][0]['interventions'] += 1000
  elif damage == 'checkpoint_bool': state['sequence'] = True; data['drives'][0]['sequence'] = 1
  elif damage == 'extra_metric': data['metrics'].append({**data['metrics'][0], 'mode': 'manual'})
  elif damage == 'missing_metric': data['metrics'] = []
  elif damage == 'duplicate_checkpoint': state['metrics'].append(copy.deepcopy(state['metrics'][0]))
  data['drives'][0]['state'] = json.dumps(state)
  with pytest.raises(ValueError): backup.validate_statistics(data)


def test_supersession_cannot_reference_history_outside_backup(tmp_path):
  source = tmp_path/'source.sqlite'
  recorded(source, drive='incoming', complete=True)
  data = backup.export_statistics(source)
  state = json.loads(data['drives'][0]['state'])
  state['supersedes'] = ['unrelated-existing-drive']
  data['drives'][0]['state'] = json.dumps(state)
  with pytest.raises(ValueError): backup.validate_statistics(data)


@pytest.mark.parametrize('damage', ['provenance', 'decreased', 'cycle', 'policy', 'coverage_loss'])
def test_recovery_relationships_must_be_consistent(tmp_path, damage):
  source = tmp_path/'source.sqlite'
  _, route = fixture(source)
  import_routes(source, [route], tmp_path/'before.sqlite')
  data = backup.export_statistics(source)
  old = next(row for row in data['drives'] if row['id'] == 'original')
  replacement = next(row for row in data['drives'] if row['id'].startswith('recovered:'))
  state = json.loads(replacement['state'])
  if damage == 'provenance': state.pop('recovery')
  elif damage == 'decreased':
    state['metrics'][0]['assistedMeters'] = 0
    next(row for row in data['metrics'] if row['drive'] == replacement['id'])['assistedMeters'] = 0
  elif damage == 'cycle':
    old_state = json.loads(old['state']); old_state['supersedes'] = [replacement['id']]; old['state'] = json.dumps(old_state)
  elif damage == 'policy': state['definitionVersion'] = 1; state['interventionReleaseSeconds'] = 0.5
  elif damage == 'coverage_loss':
    old_state = json.loads(old['state']); old_state['coverageLoss'] = True; old['state'] = json.dumps(old_state)
  replacement['state'] = json.dumps(state)
  with pytest.raises(ValueError): backup.validate_statistics(data)


def test_recovery_cannot_supersede_a_different_retained_collision(tmp_path):
  source, target = tmp_path/'source.sqlite', tmp_path/'target.sqlite'
  _, route = fixture(source)
  old = backup.export_statistics(source)
  import_routes(source, [route], tmp_path/'before.sqlite')
  incoming = backup.export_statistics(source)
  backup.apply_restore(Params(), {}, {}, old, target, tmp_path/'first', lambda: None)
  with sqlite3.connect(target) as db:
    db.execute('UPDATE drives SET software=? WHERE id=?', ('different-retained-record', 'original'))
  before = backup.export_statistics(target)
  with pytest.raises(ValueError, match='(?i)retained|collision'):
    backup.apply_restore(Params(), {}, {}, incoming, target, tmp_path/'second', lambda: None)
  assert backup.export_statistics(target) == before


def test_valid_recovered_backup_roundtrip_is_idempotent(tmp_path):
  source, target = tmp_path/'source.sqlite', tmp_path/'target.sqlite'
  _, route = fixture(source)
  old = backup.export_statistics(source)
  import_routes(source, [route], tmp_path/'before.sqlite')
  recovered = backup.export_statistics(source)
  for i, data in enumerate([old, recovered, recovered, old]):
    backup.apply_restore(Params(), {}, {}, data, target, tmp_path/f'restore-{i}', lambda: None)
  assert read_stats(target) == read_stats(source)


def test_native_params_readback_uses_registered_types_and_empty_values(tmp_path):
  from openpilot.common.params import Params as NativeParams
  params = NativeParams(str(tmp_path/'params'))
  empty = {'schemaVersion': 1, 'drives': [], 'metrics': []}
  values = {'IsMetric': True, 'LongitudinalPersonality': 2, 'DrivingModelName': '',
            'GalaxyDashboardStats': {'version': 1, 'routes': {}}}
  report = backup.apply_restore(params, values, {}, empty, tmp_path/'stats.sqlite', tmp_path/'before', lambda: None)
  assert report['restoredCount'] == 4
  assert params.get('IsMetric') is True
  assert params.get('LongitudinalPersonality') == 2
  assert params.get('DrivingModelName') is None
  assert params.get('GalaxyDashboardStats') == {'version': 1, 'routes': {}}


def test_silent_removal_failure_is_reported_after_other_keys_rollback(tmp_path):
  class FailedRemoval(Params):
    def remove(self, key):
      if key != 'new': super().remove(key)
  params = FailedRemoval({'last': 'original'})
  params.fail = 'fail'
  empty = {'schemaVersion': 1, 'drives': [], 'metrics': []}
  with pytest.raises(OSError, match='rollback incomplete for new'):
    backup.apply_restore(params, {'new': 'value', 'last': 'changed', 'fail': 'x'}, {}, empty,
                         tmp_path/'db', tmp_path/'before', lambda: None)
  assert params.get('last') == 'original'
  assert params.get('new') == 'value'


def test_guard_transition_during_restore_rolls_back_each_setting(tmp_path):
  params = Params({'a': 'original'})
  def guard():
    if params.get('a') == 'changed': raise ValueError('state changed')
  with pytest.raises(ValueError, match='state changed'):
    backup.apply_restore(params, {'a': 'changed', 'b': 'other'}, {}, {'schemaVersion': 1, 'drives': [], 'metrics': []},
                         tmp_path/'db', tmp_path/'before', guard)
  assert params.values == {'a': 'original'}


def test_restore_rejects_second_replacement_of_retained_fragment(tmp_path):
  first, second, target = tmp_path/'first.sqlite', tmp_path/'second.sqlite', tmp_path/'target.sqlite'
  _, first_route = fixture(first)
  _, second_route = fixture(second)
  first_route['routeName'] = 'route-a'
  second_route['routeName'] = 'route-b'
  # Each reconstruction is valid in isolation and refers to the same original
  # unnamed fragment. The retained replacement must win when histories merge.
  import_routes(first, [first_route], tmp_path/'first-before.sqlite')
  import_routes(second, [second_route], tmp_path/'second-before.sqlite')
  initial, incoming = backup.export_statistics(first), backup.export_statistics(second)
  backup.apply_restore(Params(), {}, {}, initial, target, tmp_path/'restore-first', lambda: None)
  before = backup.export_statistics(target)
  with pytest.raises(ValueError, match='(?i)supersed|replacement|retained'):
    backup.apply_restore(Params(), {}, {}, incoming, target, tmp_path/'restore-second', lambda: None)
  assert backup.export_statistics(target) == before
  assert read_stats(target) == read_stats(first)
