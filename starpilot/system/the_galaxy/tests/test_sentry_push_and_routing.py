import json
import time
from pathlib import Path
import pytest

from test_dashboard_stats import FakeParams, MODULE_DIR, _install_server_import_stubs


def _load_server_module():
  import importlib.util
  import sys

  _install_server_import_stubs()
  spec = importlib.util.spec_from_file_location("sentry_routing_server", MODULE_DIR / "the_galaxy.py")
  module = importlib.util.module_from_spec(spec)
  sys.modules["sentry_routing_server"] = module
  spec.loader.exec_module(module)
  return module


the_galaxy = _load_server_module()


@pytest.fixture
def client(monkeypatch, tmp_path):
  assert the_galaxy._import_galaxy_web_symbols()
  monkeypatch.setattr(the_galaxy, "params", FakeParams())
  monkeypatch.setattr(the_galaxy, "_get_galaxy_dir", lambda: tmp_path)

  app = the_galaxy.Flask(
    f"test_galaxy_{time.monotonic_ns()}",
    template_folder=str(MODULE_DIR / "templates"),
    static_folder=str(MODULE_DIR / "assets"),
  )
  the_galaxy.setup(app)
  return app.test_client()


def test_slug_middleware_strips_16_char_slug(client):
  # Slug-prefixed API call to sentry push config
  response = client.get("/df70390ca648d7c3/api/sentry/push/config")
  assert response.status_code == 200
  assert "application/json" in response.headers.get("Content-Type", "")
  data = response.get_json()
  assert data["enabled"] is True
  assert len(data["publicKey"]) > 20

  # Direct unslugged API call
  response_direct = client.get("/api/sentry/push/config")
  assert response_direct.status_code == 200
  assert response_direct.get_json()["publicKey"] == data["publicKey"]


def test_slug_middleware_service_worker_and_headers(client):
  with client.get("/df70390ca648d7c3/service-worker.js") as response:
    assert response.status_code == 200
    assert response.headers.get("Service-Worker-Allowed") == "/"
    assert "no-store" in response.headers.get("Cache-Control", "")

  with client.get("/service-worker.js") as response_direct:
    assert response_direct.status_code == 200
    assert response_direct.headers.get("Service-Worker-Allowed") == "/"


def test_404_api_returns_json_not_html(client):
  # Non-existent API route without slug
  res1 = client.get("/api/nonexistent")
  assert res1.status_code == 404
  assert "application/json" in res1.headers.get("Content-Type", "")
  assert res1.get_json() == {"error": "Not found"}

  # Non-existent API route with slug
  res2 = client.get("/df70390ca648d7c3/api/nonexistent")
  assert res2.status_code == 404
  assert "application/json" in res2.headers.get("Content-Type", "")
  assert res2.get_json() == {"error": "Not found"}

  # POST to non-existent route returns 404 JSON
  res3 = client.post("/random_post_route")
  assert res3.status_code == 404
  assert "application/json" in res3.headers.get("Content-Type", "")


def test_404_assets_returns_not_found_text(client):
  res = client.get("/assets/nonexistent_image.png")
  assert res.status_code == 404
  assert res.get_data(as_text=True) == "Not found"


def test_404_spa_client_routes_return_html(client):
  # SPA route without slug returns index.html
  res1 = client.get("/sentry")
  assert res1.status_code == 200
  assert "text/html" in res1.headers.get("Content-Type", "")

  # SPA route with slug returns index.html
  res2 = client.get("/df70390ca648d7c3/sentry")
  assert res2.status_code == 200
  assert "text/html" in res2.headers.get("Content-Type", "")


def test_sentry_push_subscribe_lifecycle(client):
  subscription_payload = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-id",
    "expirationTime": None,
    "keys": {
      "p256dh": "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-Skv60QVu3vW5PFGhmqazETUFAmeLbvDWP00n-5wViBRio5B-dQ31-10",
      "auth": "5KkU95j6j8gBsmVdYqC8pA",
    },
  }

  res = client.post(
    "/api/sentry/push/subscribe",
    data=json.dumps(subscription_payload),
    content_type="application/json",
  )
  assert res.status_code == 200
  assert res.get_json()["subscribed"] is True
  assert res.get_json()["subscriptionCount"] == 1

  # Check config shows count 1
  res_cfg = client.get("/api/sentry/push/config")
  assert res_cfg.get_json()["subscriptionCount"] == 1


def test_sentry_vapid_corrupt_file_self_healing(tmp_path, monkeypatch):
  monkeypatch.setattr(the_galaxy, "_get_galaxy_dir", lambda: tmp_path)
  key_path, _ = the_galaxy._sentry_push_paths()
  key_path.parent.mkdir(parents=True, exist_ok=True)

  # Write 0-byte corrupted file
  key_path.write_bytes(b"")
  assert key_path.stat().st_size == 0

  # Should self-heal and generate valid key
  vapid = the_galaxy._get_sentry_vapid()
  assert vapid is not None
  assert key_path.stat().st_size > 0
  pub_key = the_galaxy._sentry_vapid_public_key(vapid)
  assert len(pub_key) > 20
