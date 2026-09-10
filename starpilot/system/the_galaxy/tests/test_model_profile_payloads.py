"""Exercise shipped Flask handler with the existing isolated Params harness."""
import pytest
from test_dashboard_stats import _load_server_module, FakeParams


@pytest.mark.parametrize('payload', [
  {'profile': 'big'}, {'profile': 'big', 'model': None},
  {'profile': 'big', 'model': False}, {'profile': 'big', 'model': 0},
  {'profile': 'big', 'model': []}, {'profile': 'big', 'model': {}},
  [], ['big'], True, 1,
])
def test_malformed_selection_never_disables_big(monkeypatch, payload):
  server = _load_server_module()
  assert server._import_galaxy_web_symbols()
  app = server.Flask('model_payload_test')
  server.setup(app)
  params = FakeParams({'IsOnroad': False, 'ActiveBigModel': 'installed-big',
                       'ActiveBigModelName': 'Installed Big', 'ActiveBigModelVersion': 'v16'})
  monkeypatch.setattr(server, 'params', params)
  before = params.values.copy()
  response = app.test_client().put('/api/models/active', json=payload)
  assert response.status_code == 400
  assert params.values == before
