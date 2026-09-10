import sys
from types import SimpleNamespace
from test_dashboard_stats import _load_server_module


def test_monitor_works_without_optional_gpu_provider(monkeypatch):
  s = _load_server_module()
  assert s._import_galaxy_web_symbols()
  app = s.Flask("monitor_independent")
  s.setup(app)
  name = "openpilot.starpilot.system.the_galaxy.system_monitor"
  monkeypatch.setitem(sys.modules, name, SimpleNamespace(monitor=SimpleNamespace(sample=lambda: {"cpuPercent": 20})))
  monkeypatch.setitem(sys.modules, "openpilot.starpilot.system.the_galaxy.external_gpu_vitals", None)
  response = app.test_client().get("/api/system/monitor")
  assert response.status_code == 200
  assert response.get_json() == {"cpuPercent": 20, "vitals": {}}
  assert response.headers["Cache-Control"] == "no-store"
