"""Catalogue sizes stay available without importing model statistics."""
from test_dashboard_stats import _load_server_module, FakeParams


def test_catalog_status_has_independent_sizes(monkeypatch, tmp_path):
  server = _load_server_module()
  assert server._import_galaxy_web_symbols()
  app = server.Flask('model_sizes_test')
  server.setup(app)
  class CatalogParams(FakeParams):
    def get_default_value(self, key):
      return {'Model': 'fixture-default', 'ModelName': 'Fixture default'}.get(key)
  monkeypatch.setattr(server, 'params', CatalogParams({'IsOnroad': False}))
  monkeypatch.setattr(server, 'params_memory', FakeParams({}))
  monkeypatch.setattr(server, 'MODELS_PATH', tmp_path)
  response = app.test_client().get('/api/models/status')
  assert response.status_code == 200, response.get_json()
  result = response.get_json()
  assert result['models']
  assert 'statistics' not in result
  for model in result['models']:
    assert {'fileSizeBytes', 'declaredSizeBytes', 'downloadedBytes', 'sizeSource', 'sizeStatus'} <= model.keys()
    assert 'stats' not in model
