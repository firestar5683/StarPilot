import json

from flask import Flask
import pytest

from openpilot.starpilot.common.tests.test_model_stats_store import recorded
from openpilot.starpilot.system.the_galaxy.model_stats_api import ModelStatsAPI, register_model_stats_api


def test_stats_endpoint_reads_persistent_totals_history_and_validation(tmp_path):
  path = tmp_path / 'stats.sqlite'
  recorded(path, complete=True)
  app = Flask(__name__)
  register_model_stats_api(app, path)
  client = app.test_client()
  response = client.get('/api/models/stats?model=rdf43&mode=full&limit=1')
  assert response.status_code == 200
  result = response.get_json()
  assert result['available'] and result['definitionVersion'] == 2
  assert result['models']['rdf43']['stats']['interventions'] == 1
  assert len(result['history']) == 1
  assert client.post('/api/models/stats').status_code == 405
  for query in ['period=7d', 'mode=unknown', 'limit=201', 'offset=-1', 'limit=abc', 'reset=true', 'model=']:
    assert client.get('/api/models/stats?' + query).status_code == 400


def test_catalog_statistics_keep_unrecorded_models_available(tmp_path):
  path = tmp_path / 'stats.sqlite'
  recorded(path, complete=True)
  models = [{'value': 'rdf43', 'builtin': True}, {'value': 'gpu', 'builtin': False}]
  service = ModelStatsAPI(path)
  result = service.annotate(models)
  assert result[0]['stats']['assistedMeters'] == pytest.approx(10.1)
  assert result[1]['stats']['available'] and result[1]['stats']['assistedMeters'] == 0
  assert not result[1]['stats']['incomplete']
  json.dumps(result, allow_nan=False)


def test_missing_or_failed_store_does_not_break_catalog_or_create_history(tmp_path):
  path = tmp_path / 'missing.sqlite'
  service = ModelStatsAPI(path)
  models = [{'value': 'rdf43', 'builtin': True}]
  result = service.annotate(models)
  assert not result[0]['stats']['available']
  assert result[0]['stats']['status'] == 'not_started'
  assert not path.exists()
  path.write_bytes(b'bad sqlite')
  service = ModelStatsAPI(path)
  assert service.annotate(models)[0]['stats']['status'] == 'unavailable'


def test_summary_cache_is_not_caller_mutable(tmp_path):
  service = ModelStatsAPI(tmp_path / 'no-db')
  summary = service.summary()
  summary['models']['fake'] = {}
  assert service.summary()['models'] == {}


@pytest.mark.parametrize('offset', [2**63, 10**100])
def test_oversized_history_offset_is_bad_request(tmp_path, offset):
  path = tmp_path / 'stats.sqlite'
  recorded(path, complete=True)
  app = Flask(__name__)
  app.config['TESTING'] = True
  register_model_stats_api(app, path)
  response = app.test_client().get(f'/api/models/stats?offset={offset}')
  assert response.status_code == 400
  assert 'offset' in response.get_json()['error']


def test_largest_sqlite_history_offset_is_empty_page(tmp_path):
  path = tmp_path / 'stats.sqlite'
  recorded(path, complete=True)
  app = Flask(__name__)
  register_model_stats_api(app, path)
  response = app.test_client().get(f'/api/models/stats?offset={2**63 - 1}')
  assert response.status_code == 200
  assert response.get_json()['history'] == []
