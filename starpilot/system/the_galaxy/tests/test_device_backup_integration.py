"""Exercise actual Galaxy routes with native Params and temporary device-data roots."""
import base64
import io
import json
from pathlib import Path
import zipfile

import pytest

from openpilot.common.params import Params
from test_navigation_params import the_galaxy as server


@pytest.fixture
def device_client(monkeypatch, tmp_path):
  raw = Params(str(tmp_path / "params"))
  memory = Params(str(tmp_path / "memory"))
  raw.put_bool("IsOffroad", True)
  raw.put_bool("IsOnroad", False)
  for name, value in (("_params_raw", raw), ("_params_memory_raw", memory),
                      ("params", server.ParamsCompat(raw)), ("params_memory", server.ParamsCompat(memory)),
                      ("MODELS_PATH", tmp_path / "models"), ("THEME_SAVE_PATH", tmp_path / "themes"),
                      ("TOGGLE_BACKUPS", tmp_path / "toggle_backups")):
    monkeypatch.setattr(server, name, value)
  monkeypatch.setattr(server.flm_workspace, "get_flm_workspace_root", lambda: tmp_path / "flm", raising=False)
  monkeypatch.setattr(server.flm_workspace, "flm_analyzer_running", lambda: False, raising=False)
  monkeypatch.setattr(server, "_get_detected_ev_tuning", lambda: False)
  monkeypatch.setattr(server, "_get_detected_truck_tuning", lambda: False)
  assert server._import_galaxy_web_symbols()
  app = server.Flask("full-backup-integration")
  app.config["TESTING"] = True
  server.setup(app)
  return app.test_client(), raw, tmp_path


def export(client):
  prepared = client.post("/api/device_backup/download")
  assert prepared.status_code == 200, prepared.get_data(as_text=True)
  payload = prepared.json
  assert payload["success"] is True
  response = client.get(payload["downloadUrl"])
  assert response.status_code == 200, response.get_data(as_text=True)
  content = response.data
  response.close()
  return content


def rewrite_manifest(content, edit):
  result = io.BytesIO()
  with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(result, "w") as output:
    manifest = json.loads(source.read("manifest.json"))
    edit(manifest)
    for name in source.namelist():
      output.writestr(name, json.dumps(manifest) if name == "manifest.json" else source.read(name))
  return result.getvalue()


def test_real_routes_round_trip_with_repository_theme_layout(device_client):
  client, params, root = device_client
  # The shipped active-theme symlinks once broke every backup.
  active = Path(__file__).resolve().parents[3] / "assets" / "active_theme"
  assert (active / "colors").is_symlink()
  params.put_bool("IsMetric", True)
  params.put_int("ScreenBrightness", 65)
  params.put("FLMActiveOverrides", {"test": 1})
  params.put("StarPilotApiToken", "original-secret")
  for name, content in {
    "themes/theme_packs/space/colors.json": '{"background":"#000"}',
    "flm/saved_tunes/my-car.json": '{"name":"My Car"}',
    "flm/progress.json": '{"version":1,"vehicles":{"my-car":{"minimumPathKey":"cleanup_pass"}}}',
    "toggle_backups/Before switching/IsMetric": "1",
    "toggle_backups/Before switching/StarPilotApiToken": "original-secret",
  }.items():
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
  (root / "themes" / "active").symlink_to(active, target_is_directory=True)
  content = export(client)
  with zipfile.ZipFile(io.BytesIO(content)) as archive:
    assert not any(name.startswith(("active_theme/", "models/")) for name in archive.namelist())
    assert "profiles/Before switching/IsMetric" in archive.namelist()
    assert "flm/progress.json" in archive.namelist()
    assert all(b"original-secret" not in archive.read(name) for name in archive.namelist())
  params.put_bool("IsMetric", False)
  params.put_int("ScreenBrightness", 20)
  params.put("StarPilotApiToken", "current-secret")
  (root / "flm/saved_tunes/my-car.json").write_text("changed")
  response = client.post("/api/device_backup/restore", data=content, content_type="application/zip")
  assert response.status_code == 200, response.json
  assert response.json["success"]
  assert params.get_bool("IsMetric") is True
  assert params.get_int("ScreenBrightness") == 65
  assert params.get("FLMActiveOverrides") == {"test": 1}
  assert params.get("StarPilotApiToken") == "current-secret"
  assert (root / "flm/saved_tunes/my-car.json").read_text() == '{"name":"My Car"}'
  assert not params.get_bool("DoReboot")
  assert client.get("/api/device_backup/status").json["stage"] == "awaiting_choice"
  assert client.post("/api/device_backup/reboot", json={"downloadModels": False}).status_code == 200
  assert params.get_bool("DoReboot") is True  # Only a temporary Params store, never hardware reboot.


def test_restore_merges_history_and_repeated_import_is_idempotent(device_client):
  client, params, _ = device_client
  saved = {
    "GalaxyDashboardStats": {"version": 1, "routes": {"saved": {"duration": 2}, "shared": {"duration": 3}}},
    "ModelDrivesAndScores": {"saved": {"Drives": 2, "Score": 80}, "shared": {"Drives": 3, "Score": 70}},
    "StarPilotStats": {"StarPilotMeters": 100, "StarPilotSeconds": 30, "Month": 8,
                       "CurrentMonthsMeters": 100, "ModelTimes": {"saved": 60, "shared": 20}},
  }
  for key, value in saved.items():
    params.put(key, value)
  content = export(client)

  current = {
    "GalaxyDashboardStats": {"version": 1, "routes": {"current": {"duration": 4}, "shared": {"duration": 5}}},
    "ModelDrivesAndScores": {"current": {"Drives": 4, "Score": 90}, "shared": {"Drives": 5, "Score": 95}},
    "StarPilotStats": {"StarPilotMeters": 200, "StarPilotSeconds": 10, "Month": 9,
                       "CurrentMonthsMeters": 20, "ModelTimes": {"current": 5, "shared": 50}},
  }
  for key, value in current.items():
    params.put(key, value)

  for _ in range(2):
    response = client.post("/api/device_backup/restore", data=content, content_type="application/zip")
    assert response.status_code == 200, response.json
    assert params.get("GalaxyDashboardStats")["routes"] == {
      "saved": {"duration": 2}, "current": {"duration": 4}, "shared": {"duration": 5},
    }
    assert params.get("ModelDrivesAndScores") == {
      "saved": {"Drives": 2, "Score": 80},
      "current": {"Drives": 4, "Score": 90},
      "shared": {"Drives": 5, "Score": 95},
    }
    assert params.get("StarPilotStats") == {
      "StarPilotMeters": 200, "StarPilotSeconds": 30, "Month": 9,
      "CurrentMonthsMeters": 20, "ModelTimes": {"saved": 60, "current": 5, "shared": 50},
    }


def test_restore_rejects_safe_mode_and_pending_safe_mode_restore(device_client):
  client, params, _ = device_client
  content = export(client)
  params.put_int("ScreenBrightness", 20)

  params.put_bool("SafeMode", True)
  response = client.post("/api/device_backup/restore", data=content, content_type="application/zip")
  assert response.status_code == 400
  assert "Safe Mode" in response.json["message"]
  assert params.get_int("ScreenBrightness") == 20

  params.put_bool("SafeMode", False)
  params.put("SafeModeBackup", {"Model": {"present": True, "value": "current"}})
  response = client.post("/api/device_backup/restore", data=content, content_type="application/zip")
  assert response.status_code == 400
  assert "Safe Mode" in response.json["message"]
  assert params.get("SafeModeBackup") == {"Model": {"present": True, "value": "current"}}
  assert params.get_int("ScreenBrightness") == 20


def test_restore_stops_dashboard_analyzer_and_clears_stats_cache(device_client, monkeypatch):
  client, _, _ = device_client
  content = export(client)
  stopped = []
  monkeypatch.setattr(server.utilities, "stop_dashboard_background_analysis", lambda: stopped.append(True))
  server._STATS_RESPONSE_CACHE.update({"payload": {"stale": True}, "updated_at": 123.0})

  response = client.post("/api/device_backup/restore", data=content, content_type="application/zip")
  assert response.status_code == 200, response.json
  assert stopped == [True]
  assert server._STATS_RESPONSE_CACHE == {"payload": None, "updated_at": 0.0}


def test_incompatible_type_and_bad_boolean_keep_current_values(device_client):
  client, params, _ = device_client
  params.put_bool("IsMetric", True)
  params.put_int("ScreenBrightness", 65)
  content = export(client)

  def damage(manifest):
    manifest["types"]["ScreenBrightness"] = int(server.ParamKeyType.STRING)
    manifest["params"]["ScreenBrightness"] = base64.b64encode(b"55").decode()
    manifest["params"]["IsMetric"] = base64.b64encode(b"not-a-boolean").decode()

  params.put_int("ScreenBrightness", 20)
  response = client.post("/api/device_backup/restore", data=rewrite_manifest(content, damage), content_type="application/zip")
  assert response.status_code == 200, response.json
  assert {"ScreenBrightness", "IsMetric"} <= set(response.json["skipped"])
  assert params.get_int("ScreenBrightness") == 20
  assert params.get_bool("IsMetric") is True


def test_personality_master_and_document_are_synchronized(device_client):
  client, params, _ = device_client
  params.put_bool("CustomPersonalities", True)
  params.put("LongitudinalPersonalityProfiles", {})
  response = client.post("/api/device_backup/restore", data=export(client), content_type="application/zip")
  assert response.status_code == 200, response.json
  document = server.strict_profile_document(params.get("LongitudinalPersonalityProfiles"))
  assert document and document["enabled"] is True
  assert params.get_bool("CustomPersonalities") is True


def test_upload_limit_and_chunked_body(device_client, monkeypatch):
  client, params, root = device_client
  content = export(client)
  monkeypatch.setattr(server.device_backup, "MAX_ARCHIVE_BYTES", len(content) - 1)
  response = client.post("/api/device_backup/restore", data=content, content_type="application/zip")
  assert response.status_code == 400
  assert "limit" in response.json["message"]
  assert not list((root / "device_backup_work").glob("restore-*")), "a rejected upload must leave no staging"
  monkeypatch.setattr(server.device_backup, "MAX_ARCHIVE_BYTES", len(content) + 1)
  response = client.open("/api/device_backup/restore", method="POST", content_type="application/zip",
                         environ_overrides={"wsgi.input": io.BytesIO(content), "wsgi.input_terminated": True,
                                            "CONTENT_LENGTH": "", "HTTP_TRANSFER_ENCODING": "chunked"})
  assert response.status_code == 200, response.json
  assert not params.get_bool("DoReboot")


def test_model_queue_cancellation_cannot_cancel_a_newer_request(device_client, monkeypatch):
  _, _, _ = device_client
  monkeypatch.setattr(server, "_MODEL_RESTORE_ACTIVE", False)
  monkeypatch.setattr(server, "model_uses_external_gpu", lambda _: False)
  old = server._queue_model_download("test-model")
  server.params_memory.remove(server.MODEL_DOWNLOAD_PARAM)
  newer = server._queue_model_download("test-model")
  server._cancel_owned_model_download(old)
  assert not server.params_memory.get_bool(server.MODEL_CANCEL_DOWNLOAD_PARAM)
  server._cancel_owned_model_download(newer)
  assert server.params_memory.get_bool(server.MODEL_CANCEL_DOWNLOAD_PARAM)


def test_restore_reservation_and_gpu_guard_apply_to_existing_model_api(device_client, monkeypatch):
  client, _, _ = device_client
  monkeypatch.setattr(server, "_MODEL_RESTORE_ACTIVE", True)
  assert client.post("/api/models/download", json={"model": "a"}).status_code == 409
  assert client.post("/api/models/download_all", json={}).status_code == 409
  assert client.post("/api/models/refresh_manifest").status_code == 409
  monkeypatch.setattr(server, "_MODEL_RESTORE_ACTIVE", False)
  monkeypatch.setattr(server, "model_uses_external_gpu", lambda _: True)
  monkeypatch.setattr(server, "external_gpu_available", lambda: False)
  with pytest.raises(ValueError, match="external GPU"):
    server._queue_model_download("a", restore_job=True)
  assert not server.params_memory.get(server.MODEL_DOWNLOAD_PARAM)


def test_completion_report_survives_server_restart(device_client):
  client, _, _ = device_client
  content = export(client)
  assert client.post("/api/device_backup/restore", data=content, content_type="application/zip").status_code == 200
  assert client.post("/api/device_backup/reboot", json={"downloadModels": False}).status_code == 200
  restarted_app = server.Flask("backup-result-after-restart")
  server.setup(restarted_app)
  status = restarted_app.test_client().get("/api/device_backup/status").json
  assert status["stage"] == "complete"
  assert "Restored" in status["message"]
  # Once read, the report is not repeated after later restarts.
  assert not list(Path(server.MODELS_PATH.parent).glob("device_backup_work/last_restore.json"))
  later_app = server.Flask("backup-result-after-second-restart")
  server.setup(later_app)
  assert later_app.test_client().get("/api/device_backup/status").json["stage"] == "idle"


class LosePower:
  """Delegates to real Params but dies after the first setting write, like a power cut mid-restore."""

  def __init__(self, params):
    self.params = params
    self.writes = 0

  def __getattr__(self, name):
    return getattr(self.params, name)

  def put(self, key, value):
    self.writes += 1
    if self.writes > 1:
      raise KeyboardInterrupt
    self.params.put(key, value)


def interrupt_restore(client, params, root):
  params.put_bool("IsMetric", True)
  params.put_int("ScreenBrightness", 65)
  tune = root / "flm/saved_tunes/my-car.json"
  tune.parent.mkdir(parents=True, exist_ok=True)
  tune.write_text("saved")
  content = export(client)
  params.put_bool("IsMetric", False)
  params.put_int("ScreenBrightness", 20)
  tune.write_text("before restore")
  roots = {"flm": root / "flm", "themes": root / "themes", "profiles": root / "toggle_backups"}
  keys = server.device_backup.eligible_keys(key.decode() if isinstance(key, bytes) else key for key in params.all_keys())
  with pytest.raises(KeyboardInterrupt):
    server.device_backup.restore_backup(io.BytesIO(content), roots, LosePower(params), keys, root / "device_backup_work", lambda: None)
  assert tune.read_text() == "saved", "the power cut happened after files were replaced"
  assert params.get_bool("IsMetric") is True, "and after the first setting was written"
  return tune


def wait_for_stage(client, stage, timeout=5.0):
  import time
  deadline = time.monotonic() + timeout
  while time.monotonic() < deadline:
    status = client.get("/api/device_backup/status").json
    if status["stage"] == stage:
      return status
    time.sleep(0.02)
  pytest.fail(f"stage stayed {status}")


def wait_for_message(client, text, timeout=5.0):
  import time
  deadline = time.monotonic() + timeout
  while time.monotonic() < deadline:
    message = client.get("/api/device_backup/status").json["message"]
    if text in message:
      return message
    time.sleep(0.02)
  pytest.fail(f"message stayed {message!r}")


def test_interrupted_restore_is_rolled_back_on_next_start(device_client):
  client, params, root = device_client
  tune = interrupt_restore(client, params, root)
  restarted = server.Flask("after-power-loss")
  server.setup(restarted)
  restarted_client = restarted.test_client()
  status = wait_for_stage(restarted_client, "rolled_back")
  assert "Restore the backup again" in status["message"]
  assert tune.read_text() == "before restore"
  assert params.get_bool("IsMetric") is False
  assert params.get_int("ScreenBrightness") == 20
  assert not server.device_backup.pending_recoveries(root / "device_backup_work")
  assert export(restarted_client)


def test_interrupted_restore_rollback_waits_until_parked(device_client, monkeypatch):
  client, params, root = device_client
  tune = interrupt_restore(client, params, root)
  monkeypatch.setattr(server, "_RESTORE_RECOVERY_POLL_SECONDS", 0.02)
  params.put_bool("IsOnroad", True)
  params.put_bool("IsOffroad", False)
  restarted = server.Flask("after-power-loss-onroad")
  server.setup(restarted)
  restarted_client = restarted.test_client()
  wait_for_stage(restarted_client, "restore_error")
  assert "once the vehicle is parked" in wait_for_message(restarted_client, "once the vehicle is parked")
  assert tune.read_text() == "saved", "nothing is written while driving"
  assert server.device_backup.pending_recoveries(root / "device_backup_work")
  params.put_bool("IsOnroad", False)
  params.put_bool("IsOffroad", True)
  wait_for_stage(restarted_client, "rolled_back")
  assert tune.read_text() == "before restore"
  assert params.get_bool("IsMetric") is False


def test_failed_startup_rollback_blocks_backup_and_restore(device_client):
  client, params, root = device_client
  interrupt_restore(client, params, root)
  [record] = server.device_backup.pending_recoveries(root / "device_backup_work")
  data = json.loads(record.read_text())
  old = next(item["copy"] for item in data["files"] if item["existed"])
  Path(old).unlink()
  restarted = server.Flask("failed-recovery")
  server.setup(restarted)
  restarted_client = restarted.test_client()
  wait_for_message(restarted_client, "could not be fully rolled back")
  for route in ("download", "restore"):
    response = restarted_client.post(f"/api/device_backup/{route}")
    assert response.status_code in (400, 409)
  assert record.exists()


def test_discard_recovery_unblocks_after_failed_rollback(device_client):
  client, params, root = device_client
  interrupt_restore(client, params, root)
  [record] = server.device_backup.pending_recoveries(root / "device_backup_work")
  data = json.loads(record.read_text())
  old = next(item["copy"] for item in data["files"] if item["existed"])
  Path(old).unlink()
  restarted = server.Flask("discard-recovery")
  server.setup(restarted)
  restarted_client = restarted.test_client()
  wait_for_message(restarted_client, "could not be fully rolled back")
  assert restarted_client.get("/api/device_backup/status").json["recoveryPending"] is True
  assert restarted_client.delete("/api/device_backup/recovery").status_code == 400, "confirm is required"
  response = restarted_client.delete("/api/device_backup/recovery", json={"confirm": True})
  assert response.status_code == 200, response.json
  assert response.json["removed"] == 1
  assert not server.device_backup.pending_recoveries(root / "device_backup_work")
  assert restarted_client.get("/api/device_backup/status").json["recoveryPending"] is False
  assert export(restarted_client)


def test_restore_without_reboot_keeps_final_choice_after_restart(device_client):
  client, _, _ = device_client
  response = client.post("/api/device_backup/restore", data=export(client), content_type="application/zip")
  assert response.status_code == 200, response.json
  assert client.get("/api/device_backup/status").json["stage"] == "awaiting_choice"
  restarted = server.Flask("pending-restore")
  server.setup(restarted)
  restarted_client = restarted.test_client()
  status = restarted_client.get("/api/device_backup/status").json
  assert status["stage"] == "awaiting_choice", "the final choice must survive a Galaxy restart"
  assert restarted_client.post("/api/device_backup/reboot", json={"downloadModels": False}).status_code == 200
  later = server.Flask("pending-cleared")
  server.setup(later)
  assert later.test_client().get("/api/device_backup/status").json["stage"] == "complete"


def test_orphan_restore_stages_are_swept_on_start(device_client):
  client, _, root = device_client
  workdir = root / "device_backup_work"
  orphan = workdir / "restore-orphan"
  (orphan / "new/flm").mkdir(parents=True)
  recovery = workdir / "restore-recovery"
  recovery.mkdir(parents=True)
  (recovery / "recovery.json").write_text("{}")  # Unreadable record: rollback fails and the copies stay.
  server.setup(server.Flask("sweep-stages"))
  assert not orphan.exists(), "a stage that died before any live change is discarded"
  assert recovery.exists(), "recovery copies are kept for rollback"


def test_backup_download_url_is_single_use_and_validated(device_client):
  client, _, _ = device_client
  prepared = client.post("/api/device_backup/download").json
  assert client.get("/api/device_backup/download/not-a-backup.zip").status_code == 404
  response = client.get(prepared["downloadUrl"])
  assert response.status_code == 200
  response.close()
  assert client.get(prepared["downloadUrl"]).status_code == 404, "the streamed file is removed after download"


def test_backup_refuses_and_returns_no_file_when_space_is_short(device_client, monkeypatch):
  from collections import namedtuple
  client, _, root = device_client
  downloads = root / "device_backup_work/downloads"
  downloads.mkdir(parents=True, exist_ok=True)
  (downloads / "starpilot-device-20200101-000000.zip").write_bytes(b"stale")
  monkeypatch.setattr(server.device_backup.shutil, "disk_usage",
                      lambda _: namedtuple("usage", "total used free")(1, 0, 0))
  response = client.post("/api/device_backup/download")
  assert response.status_code == 400
  assert "driving routes" in response.json["message"]
  assert not list(downloads.glob("starpilot-device-*.zip")), "a refused backup leaves no prepared file"


def test_prepared_backup_is_removed_after_it_is_downloaded(device_client):
  client, _, root = device_client
  prepared = client.post("/api/device_backup/download").json
  path = root / "device_backup_work/downloads" / prepared["filename"]
  assert path.is_file()
  response = client.get(prepared["downloadUrl"])
  assert response.status_code == 200
  assert response.data, "the staged archive is streamed to the client"
  response.close()
  assert not path.exists(), "the download removes the staged backup"
