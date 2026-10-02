import io
import json
import zipfile

import pytest

from starpilot.system.the_galaxy.device_backup import create_backup, restore_backup


class Params:
  def __init__(self):
    self.values = {"IsMetric": b"1", "FLMActiveOverrides": b'\x00\xff'}

  def get(self, key):
    return self.values.get(key)

  def put(self, key, value):
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)


@pytest.fixture
def backup(tmp_path):
  root = tmp_path / "flm"
  root.mkdir()
  (root / "model.bin").write_bytes(b"model contents")
  params = Params()
  archive = io.BytesIO()
  create_backup(archive, {"flm": root}, params, {"IsMetric", "FLMActiveOverrides", "ScreenBrightness"})
  return archive, root, params


def test_round_trip(backup, tmp_path):
  archive, root, params = backup
  params.values = {"IsMetric": b"0", "ScreenBrightness": b"new"}
  (root / "model.bin").write_bytes(b"changed")
  assert restore_backup(archive, {"flm": root}, params, {"IsMetric", "FLMActiveOverrides", "ScreenBrightness"}, tmp_path, lambda: None) == (2, 1, [])
  assert params.values == {"IsMetric": b"1", "FLMActiveOverrides": b'\x00\xff'}
  assert (root / "model.bin").read_bytes() == b"model contents"


def test_history_merge_keeps_current_records_and_larger_lifetime_totals():
  from starpilot.system.the_galaxy.device_backup import merge_history_param

  saved_dashboard = {"version": 1, "routes": {"saved": {"duration": 2}, "shared": {"duration": 3}}}
  current_dashboard = {"version": 1, "routes": {"current": {"duration": 4}, "shared": {"duration": 5}}}
  dashboard = merge_history_param("GalaxyDashboardStats", saved_dashboard, current_dashboard)
  assert dashboard["routes"] == {
    "saved": {"duration": 2}, "current": {"duration": 4}, "shared": {"duration": 5},
  }

  saved_models = {"saved": {"Drives": 2, "Score": 80}, "shared": {"Drives": 3, "Score": 70}}
  current_models = {"current": {"Drives": 4, "Score": 90}, "shared": {"Drives": 5, "Score": 95}}
  models = merge_history_param("ModelDrivesAndScores", saved_models, current_models)
  assert models == {
    "saved": {"Drives": 2, "Score": 80},
    "current": {"Drives": 4, "Score": 90},
    "shared": {"Drives": 5, "Score": 95},
  }

  saved_stats = {"StarPilotMeters": 100, "StarPilotSeconds": 30, "Month": 8,
                 "CurrentMonthsMeters": 100, "ModelTimes": {"saved": 60, "shared": 20}}
  current_stats = {"StarPilotMeters": 200, "StarPilotSeconds": 10, "Month": 9,
                   "CurrentMonthsMeters": 20, "ModelTimes": {"current": 5, "shared": 50}}
  stats = merge_history_param("StarPilotStats", saved_stats, current_stats)
  assert stats == {"StarPilotMeters": 200, "StarPilotSeconds": 30, "Month": 9,
                   "CurrentMonthsMeters": 20, "ModelTimes": {"saved": 60, "current": 5, "shared": 50}}
  assert merge_history_param("StarPilotStats", saved_stats, stats) == stats


def test_silent_setting_write_is_detected_and_rolled_back(tmp_path):
  from starpilot.system.the_galaxy.device_backup import RestoreError

  source = Params()
  source.values = {"IsMetric": b"1", "ScreenBrightness": b"65"}
  archive = io.BytesIO()
  create_backup(archive, {}, source, set(source.values))

  class SilentOnce(Params):
    def __init__(self):
      super().__init__()
      self.values = {"IsMetric": b"0", "ScreenBrightness": b"20"}
      self.ignored = False

    def put(self, key, value):
      if key == "ScreenBrightness" and not self.ignored:
        self.ignored = True
        return
      super().put(key, value)

  params = SilentOnce()
  with pytest.raises(RestoreError, match="could not be verified"):
    restore_backup(archive, {}, params, set(source.values), tmp_path, lambda: None)
  assert params.values == {"IsMetric": b"0", "ScreenBrightness": b"20"}


@pytest.mark.parametrize("name", ["flm/../../escape", "/flm/escape", "unknown/file", "flm/model.bin"])
def test_rejects_paths_and_corruption(backup, tmp_path, name):
  archive, root, params = backup
  with zipfile.ZipFile(archive) as source:
    manifest = json.loads(source.read("manifest.json"))
  metadata = manifest["files"].pop("flm/model.bin")
  manifest["files"][name] = metadata
  damaged = io.BytesIO()
  with zipfile.ZipFile(damaged, "w") as output:
    output.writestr("manifest.json", json.dumps(manifest))
    output.writestr(name, b"corrupt")
  with pytest.raises(ValueError):
    restore_backup(damaged, {"flm": root}, params, set(params.values), tmp_path, lambda: None)
  assert (root / "model.bin").read_bytes() == b"model contents"


def test_rolls_back_when_vehicle_leaves_offroad(backup, tmp_path):
  archive, root, params = backup
  (root / "model.bin").write_bytes(b"before restore")
  checks = 0

  def parked():
    nonlocal checks
    checks += 1
    if checks == 3:
      raise ValueError("Vehicle is onroad")

  with pytest.raises(ValueError, match="onroad"):
    restore_backup(archive, {"flm": root}, params, set(params.values), tmp_path, parked)
  assert (root / "model.bin").read_bytes() == b"before restore"


def test_rejects_symlink_destination(backup, tmp_path):
  archive, root, params = backup
  (root / "model.bin").unlink()
  other = tmp_path / "other"
  other.write_bytes(b"untouched")
  (root / "model.bin").symlink_to(other)
  with pytest.raises(ValueError, match="symbolic link"):
    restore_backup(archive, {"flm": root}, params, set(params.values), tmp_path, lambda: None)
  assert other.read_bytes() == b"untouched"


SENSITIVE_KEYS = {
  "StarPilotApiToken", "StarPilotDongleId", "GalaxyPaired", "GalaxyUploadPending",
  "DongleId", "StockDongleId", "KonikDongleId", "HardwareSerial", "AccessToken",
  "AssistNowToken", "WeatherToken", "MapboxSecretKey", "MapboxPublicKey", "AMapKey1", "AMapKey2",
  "SecOCKey", "SecOCKeys", "GithubSshKeys", "GithubUsername", "SentryModeWebhook", "SentryModeNtfyUrl",
  "IsOnroad", "IsEngaged", "GitCommit", "LastGPSPosition", "NavDestination", "FavoriteDestinations",
  "FutureUnknownToken",
}


def test_export_filters_credentials_in_params_and_nested_profiles(tmp_path):
  params = Params()
  params.values.update(dict.fromkeys(SENSITIVE_KEYS, b"SECRET"))
  profiles = tmp_path / "profiles"
  auto = profiles / "2026-09-13_auto"
  auto.mkdir(parents=True)
  for key, value in params.values.items():
    (auto / key).write_bytes(value)
  slot = {"format": "starpilot-params-profile", "version": 1, "slot": "a", "settings": {
    "StarPilotApiToken": {"type": 1, "value": "SECRET"}, "IsMetric": {"type": 1, "value": "1"},
  }}
  (profiles / ".params-profile-a.json").write_text(json.dumps(slot))
  flm = tmp_path / "flm"
  flm.mkdir()
  (flm / "glxysession").write_text("SECRET")
  output = io.BytesIO()
  create_backup(output, {"profiles": profiles, "flm": flm}, params, set(params.values))
  with zipfile.ZipFile(output) as archive:
    manifest = json.loads(archive.read("manifest.json"))
    assert not set(manifest["params"]) & SENSITIVE_KEYS
    assert "FLMActiveOverrides" in manifest["params"]
    assert "flm/glxysession" not in archive.namelist()
    assert not any(name.split("/")[-1] in SENSITIVE_KEYS for name in archive.namelist())
    restored_slot = json.loads(archive.read("profiles/.params-profile-a.json"))
    assert set(restored_slot["settings"]) == {"IsMetric"}
    assert restored_slot["settingsCount"] == 1
    assert all(b"SECRET" not in archive.read(name) for name in archive.namelist())


def test_old_archive_cannot_restore_or_clear_credentials(tmp_path):
  import base64
  import hashlib

  params = Params()
  params.values.update(dict.fromkeys(SENSITIVE_KEYS, b"current"))
  profiles = tmp_path / "profiles"
  profiles.mkdir()
  flm = tmp_path / "flm"
  flm.mkdir()
  (flm / "glxysession").write_bytes(b"current-session")
  manifest = {"format": "starpilot-device-backup", "version": 1, "params": {
    key: base64.b64encode(b"old").decode() for key in SENSITIVE_KEYS | {"IsMetric"}
  }, "files": {}}
  # Older, broader archives could carry credentials in raw auto backups and slot JSON.
  files = {"profiles/2026-09-13_auto/StarPilotApiToken": b"old-secret", "flm/glxysession": b"old-session",
           "profiles/.params-profile-a.json": json.dumps({"format": "starpilot-params-profile", "settings": {
             "StarPilotApiToken": {"value": "old-secret"}, "IsMetric": {"value": "1"},
           }}).encode()}
  output = io.BytesIO()
  with zipfile.ZipFile(output, "w") as archive:
    for name, content in files.items():
      archive.writestr(name, content)
      manifest["files"][name] = {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    archive.writestr("manifest.json", json.dumps(manifest))
  restore_backup(output, {"profiles": profiles, "flm": flm}, params, set(params.values), tmp_path, lambda: None)
  assert all(params.get(key) == b"current" for key in SENSITIVE_KEYS)
  assert params.get("IsMetric") == b"old"
  assert (flm / "glxysession").read_bytes() == b"current-session"
  assert not (profiles / "2026-09-13_auto/StarPilotApiToken").exists()
  assert set(json.loads((profiles / ".params-profile-a.json").read_text())["settings"]) == {"IsMetric"}


def test_audited_policy_preserves_tunings_and_excludes_unreviewed_keys():
  from starpilot.system.the_galaxy.device_backup import BACKUP_KEYS
  assert not BACKUP_KEYS & SENSITIVE_KEYS
  assert {"FLMActiveOverrides", "FLMActiveProfileId", "FLMTrialBaseline", "FLMTrialApplied",
          "LongitudinalPersonalityProfiles", "SafeModeBackup", "ModelLabConfig", "CalibrationParams",
          "GalaxyMobileDefault", "GalaxyDeveloperMode"} <= BACKUP_KEYS


@pytest.mark.parametrize("ready,parked,busy,download,status", [
  (False, True, False, False, 409), (True, False, False, False, 403), (True, True, True, False, 409),
  (True, True, False, False, 200), (True, True, False, True, 200), (True, True, False, None, 400),
])
def test_restore_reboot_requires_completed_restore_and_parked_state(ready, parked, busy, download, status):
  # Execute the real route body without importing the device hardware/server stack.
  import ast
  from pathlib import Path
  import threading

  tree = ast.parse(Path(__file__).parents[1].joinpath("the_galaxy.py").read_text())
  route = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "reboot_after_device_restore")
  route.decorator_list = []
  lock = threading.Lock()
  if busy:
    lock.acquire()
  writes = []

  class RebootParams:
    def put_bool(self, key, value):
      writes.append((key, value))

  from types import SimpleNamespace
  workers = []

  class FakeThread:
    def __init__(self, **kwargs):
      workers.append(kwargs)

    def start(self):
      pass

  scope = {"device_backup_lock": lock, "device_restore_ready": ready, "_params_raw": RebootParams(),
           "_personality_settings_write_locked": lambda: not parked, "jsonify": lambda **kwargs: kwargs,
           "request": SimpleNamespace(get_json=lambda **kwargs: {"downloadModels": download}),
           "threading": SimpleNamespace(Thread=FakeThread), "run_restore_model_downloads": lambda: None,
           "_model_download_busy": lambda: False, "_MODEL_QUEUE_LOCK": threading.RLock(), "device_restore_state": {},
           "request_restore_reboot": lambda: writes.append(("DoReboot", True))}
  exec(compile(ast.Module(body=[route], type_ignores=[]), "<reboot-route>", "exec"), scope)
  result = scope["reboot_after_device_restore"]()
  assert (result[1] if isinstance(result, tuple) else 200) == status
  assert writes == ([("DoReboot", True)] if status == 200 and not download else [])
  worker_started = status == 200 and download
  assert bool(workers) == bool(worker_started)
  assert lock.locked() == bool(busy or worker_started)
  if lock.locked():
    lock.release()


def test_backup_records_inventory_without_model_files(tmp_path):
  from starpilot.system.the_galaxy.device_backup import saved_models
  models = tmp_path / "models"
  models.mkdir()
  (models / "large_model.pkl").write_bytes(b"MODEL BINARY CONTENT")
  inventory = saved_models([
    {"value": "stock", "builtin": True, "installed": True},
    {"value": "model-a", "version": "1", "installed": True, "modelLabArtifactInstalled": True},
    {"value": "not-installed", "installed": False},
  ])
  output = io.BytesIO()
  create_backup(output, {"models": models}, Params(), {"IsMetric"}, models=inventory)
  with zipfile.ZipFile(output) as archive:
    assert archive.namelist() == ["manifest.json"]
    assert json.loads(archive.read("manifest.json"))["models"] == [
      {"key": "model-a", "version": "1", "standard": True, "lab": True},
    ]
  restored_models = []
  restore_backup(output, {}, Params(), {"IsMetric"}, tmp_path, lambda: None, models_out=restored_models)
  assert restored_models == inventory


def test_model_inventory_validation_precedes_restore(tmp_path):
  output = io.BytesIO()
  with zipfile.ZipFile(output, "w") as archive:
    archive.writestr("manifest.json", json.dumps({"format": "starpilot-device-backup", "version": 2,
      "files": {}, "params": {}, "models": [{"key": "https://untrusted/model", "standard": True, "lab": False}]}))
  params = Params()
  with pytest.raises(ValueError, match="model identifier"):
    restore_backup(output, {}, params, {"IsMetric"}, tmp_path, lambda: None)
  assert params.get("IsMetric") == b"1"


@pytest.mark.parametrize("key", [True, 123, 1.5, None])
def test_model_inventory_rejects_non_string_keys(key):
  from starpilot.system.the_galaxy.device_backup import validate_models
  with pytest.raises(ValueError, match="model identifier"):
    validate_models([{"key": key, "standard": True, "lab": False}])


class TypedParams:
  """Native-like Params: typed get/put, file-backed store, cpp2python returns None on a bad cast."""
  decoders = {0: lambda v: v.decode(), 1: lambda v: v == b"1", 2: lambda v: int(v.decode()), 3: float, 5: json.loads}

  def __init__(self, store, types):
    self.store = store
    self.types = types
    self.values = {}

  def get_param_path(self, key):
    return str(self.store / key)

  def get_type(self, key):
    return self.types[key]

  def cpp2python(self, key, raw):
    try:
      return self.decoders[self.types[key]](raw)
    except ValueError:
      return None

  def get(self, key):
    return self.values.get(key)

  def put(self, key, value):
    assert type(value) in {0: (str,), 1: (bool,), 2: (int,), 3: (float,), 5: (dict, list)}[self.types[key]]
    self.values[key] = value

  def remove(self, key):
    self.values.pop(key, None)


def test_typed_params_round_trip_uses_serialized_store(tmp_path):
  params = TypedParams(tmp_path, {"IsMetric": 1, "ScreenBrightness": 2, "FLMActiveOverrides": 5})
  for key, value in {"IsMetric": b"1", "ScreenBrightness": b"70", "FLMActiveOverrides": b'{"tune":1}'}.items():
    (tmp_path / key).write_bytes(value)
  output = io.BytesIO()
  create_backup(output, {}, params, set(params.types))
  restore_backup(output, {}, params, set(params.types), tmp_path, lambda: None)
  assert params.values == {"IsMetric": True, "ScreenBrightness": 70, "FLMActiveOverrides": {"tune": 1}}


def test_setting_with_changed_type_keeps_current_value_instead_of_failing_restore(tmp_path):
  store = tmp_path / "store"
  store.mkdir()
  (store / "IsMetric").write_bytes(b"1")
  (store / "ScreenBrightness").write_bytes(b"bright")  # Saved while this key was a STRING.
  output = io.BytesIO()
  create_backup(output, {}, TypedParams(store, {"IsMetric": 1, "ScreenBrightness": 0}), {"IsMetric", "ScreenBrightness"})
  params = TypedParams(store, {"IsMetric": 1, "ScreenBrightness": 2})
  params.values = {"ScreenBrightness": 40}
  assert restore_backup(output, {}, params, {"IsMetric", "ScreenBrightness"}, tmp_path, lambda: None) == (1, 0, ["ScreenBrightness"])
  assert params.values == {"IsMetric": True, "ScreenBrightness": 40}


def test_validator_rejections_keep_current_values(tmp_path):
  archive, root, params = backup_archive(tmp_path)
  params.values = {"IsMetric": b"current", "FLMActiveOverrides": b"current"}
  result = restore_backup(archive, {"flm": root}, params, {"IsMetric", "FLMActiveOverrides"}, tmp_path, lambda: None,
                          validate=lambda values, _keys: {key: value for key, value in values.items() if key != "FLMActiveOverrides"})
  assert result == (1, 1, ["FLMActiveOverrides"])
  assert params.values == {"IsMetric": b"1", "FLMActiveOverrides": b"current"}


def backup_archive(tmp_path):
  root = tmp_path / "flm"
  root.mkdir()
  (root / "tune.json").write_bytes(b"{}")
  params = Params()
  archive = io.BytesIO()
  create_backup(archive, {"flm": root}, params, {"IsMetric", "FLMActiveOverrides"})
  return archive, root, params


def test_backup_skips_linked_theme_assets_instead_of_failing(tmp_path):
  themes = tmp_path / "themes"
  pack = themes / "theme_packs" / "space"
  pack.mkdir(parents=True)
  (pack / "colors.json").write_text("{}")
  # Theme manager symlinks active assets; only the real files are archived.
  (themes / "active_colors").symlink_to(pack, target_is_directory=True)
  (themes / "wheel.png").symlink_to(pack / "colors.json")
  output = io.BytesIO()
  create_backup(output, {"themes": themes}, Params(), set())
  with zipfile.ZipFile(output) as archive:
    assert sorted(archive.namelist()) == ["manifest.json", "themes/theme_packs/space/colors.json"]


def test_galaxy_backs_up_only_known_roots_and_not_the_linked_active_theme():
  import ast
  from pathlib import Path
  from starpilot.system.the_galaxy.device_backup import ROOT_LABELS

  tree = ast.parse(Path(__file__).parents[1].joinpath("the_galaxy.py").read_text())
  context = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "device_backup_context")
  roots = next(node.value for node in ast.walk(context) if isinstance(node, ast.Assign) and node.targets[0].id == "roots")
  assert {key.value for key in roots.keys} == set(ROOT_LABELS)
  assert "ACTIVE_THEME_PATH" not in ast.unparse(roots)


def test_user_named_toggle_backups_are_included_and_filtered(tmp_path):
  profiles = tmp_path / "profiles"
  for folder in ("2026-09-13_auto", "before_fork_switch", "2026-09-14_auto_in_progress"):
    (profiles / folder).mkdir(parents=True)
    (profiles / folder / "IsMetric").write_bytes(b"1")
    (profiles / folder / "StarPilotApiToken").write_bytes(b"SECRET")
  output = io.BytesIO()
  create_backup(output, {"profiles": profiles}, Params(), {"IsMetric"})
  with zipfile.ZipFile(output) as archive:
    assert sorted(archive.namelist()) == ["manifest.json", "profiles/2026-09-13_auto/IsMetric", "profiles/before_fork_switch/IsMetric"]


def test_flm_tuning_progress_is_backed_up(tmp_path):
  flm = tmp_path / "flm"
  (flm / "saved_tunes").mkdir(parents=True)
  (flm / "progress.json").write_text('{"version":1,"vehicles":{"car":{"minimumPathKey":"cleanup_pass"}}}')
  (flm / "saved_tunes" / "tune.json").write_text("{}")
  output = io.BytesIO()
  create_backup(output, {"flm": flm}, Params(), set())
  with zipfile.ZipFile(output) as archive:
    assert sorted(archive.namelist()) == ["flm/progress.json", "flm/saved_tunes/tune.json", "manifest.json"]


def test_every_persistent_param_is_explicitly_included_or_excluded():
  import re
  from pathlib import Path
  from starpilot.system.the_galaxy.device_backup import POLICY

  registry = Path(__file__).resolve().parents[4].joinpath("common/params_keys.h").read_text()
  persistent = {match.group(1) for match in re.finditer(r'^\s*\{"(\w+)",\s*\{([^,}]*)', registry, re.MULTILINE)
                if "PERSISTENT" in match.group(2)}
  include, exclude = set(POLICY["include"]), set(POLICY["exclude"])
  assert not include & exclude
  unreviewed = persistent - include - exclude
  assert not unreviewed, f"Add new persistent Params to device_backup_keys.json include or exclude: {sorted(unreviewed)}"
  assert include | exclude <= persistent, f"Remove deleted Params: {sorted((include | exclude) - persistent)}"


def test_restore_applies_galaxy_personality_validation():
  import ast
  from pathlib import Path
  from starpilot.common import longitudinal_personality_profiles as profiles

  tree = ast.parse(Path(__file__).parents[1].joinpath("the_galaxy.py").read_text())
  validator = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "validate_device_restore_params")
  scope = {name: getattr(profiles, name) for name in (
    "PERSONALITY_ADVANCED_PARAM_KEYS", "PERSONALITY_FOLLOW_PARAM_KEYS", "PERSONALITY_PROFILES_PARAM",
    "validate_personality_advanced_value", "validate_personality_follow_value",
    "is_unconfigured_profile_document", "migrate_profile_document", "PERSONALITY_PROFILE_ENABLE_PARAM_KEYS",
    "strict_profile_document", "synchronise_profile_document_enabled")}
  from types import SimpleNamespace
  scope.update(_params_raw=SimpleNamespace(get=lambda key: None, get_bool=lambda key: False),
               params=SimpleNamespace(get_bool=lambda key: False),
               _get_detected_ev_tuning=lambda: False, _get_detected_truck_tuning=lambda: False)
  exec(compile(ast.Module(body=[validator], type_ignores=[]), "<validator>", "exec"), scope)
  def validate(values):
    return scope["validate_device_restore_params"](values, set(values))
  assert validate({"AggressiveFollow": 9.0, "TrafficJerkAcceleration": 100.0, "IsMetric": True}) == {
    "TrafficJerkAcceleration": 100.0, "IsMetric": True}
  assert validate({profiles.PERSONALITY_PROFILES_PARAM: {"garbage": 1}, "CustomPersonalities": True}) == {}
  assert validate({profiles.PERSONALITY_PROFILES_PARAM: {}, "CustomPersonalities": False}) == {
    profiles.PERSONALITY_PROFILES_PARAM: {}, "CustomPersonalities": False}


def test_new_settings_absent_from_old_scope_are_not_cleared(tmp_path):
  params = Params()
  output = io.BytesIO()
  create_backup(output, {}, params, {"IsMetric"})
  params.values["ScreenBrightness"] = b"40"
  restore_backup(output, {}, params, {"IsMetric", "ScreenBrightness"}, tmp_path, lambda: None)
  assert params.values["ScreenBrightness"] == b"40"


def test_params_failure_rolls_back_replaced_files(tmp_path):
  archive, root, params = backup_archive(tmp_path)
  (root / "tune.json").write_text("before")
  params.values["IsMetric"] = b"0"
  put = params.put
  failed = False

  def fail_once(key, value):
    nonlocal failed
    if not failed:
      assert (root / "tune.json").read_text() == "{}", "must fail after live file replacement"
      failed = True
      raise OSError("Simulated Params write failure")
    put(key, value)

  params.put = fail_once
  with pytest.raises(OSError, match="Params write"):
    restore_backup(archive, {"flm": root}, params, {"IsMetric", "FLMActiveOverrides"}, tmp_path, lambda: None)
  assert (root / "tune.json").read_text() == "before"
  assert params.values["IsMetric"] == b"0"
  assert not list(tmp_path.glob("restore-*"))


def test_failed_rollback_retains_recovery_copies(tmp_path):
  archive, root, params = backup_archive(tmp_path)
  (root / "tune.json").write_text("before")

  def fail_put(_key, _value):
    raise OSError("Permanent write failure")

  params.put = fail_put
  with pytest.raises(RuntimeError, match="rollback was incomplete"):
    restore_backup(archive, {"flm": root}, params, {"IsMetric", "FLMActiveOverrides"}, tmp_path, lambda: None)
  recovery = next(tmp_path.glob("restore-*/recovery.json"))
  assert json.loads(recovery.read_text())["params"]["IsMetric"] == "MQ=="
  assert (recovery.parent / "old/flm/tune.json").read_text() == "before"


def test_disk_budget_accounts_for_larger_existing_files(tmp_path, monkeypatch):
  from collections import namedtuple
  from starpilot.system.the_galaxy import device_backup
  archive, root, params = backup_archive(tmp_path)
  (root / "tune.json").write_bytes(b"x" * 10000)
  usage = namedtuple("usage", "total used free")
  monkeypatch.setattr(device_backup.shutil, "disk_usage", lambda _: usage(1_000_000, 0, device_backup.RESTORE_MARGIN_BYTES + 1000))
  with pytest.raises(ValueError, match="free space"):
    restore_backup(archive, {"flm": root}, params, {"IsMetric"}, tmp_path, lambda: None)
  assert (root / "tune.json").stat().st_size == 10000


def interrupted_restore(tmp_path):
  """Simulate power loss mid-restore: files replaced and one setting written, then the process dies."""
  archive, root, params = backup_archive(tmp_path)
  (root / "tune.json").write_text("before")
  (root / "added-later.json").unlink(missing_ok=True)
  params.values = {"IsMetric": b"0", "FLMActiveOverrides": b"before"}
  put = params.put
  writes = []

  def lose_power(key, value):
    if writes:
      raise KeyboardInterrupt  # Not an Exception: the in-process rollback never runs, like a crash.
    writes.append(key)
    put(key, value)

  params.put = lose_power
  with pytest.raises(KeyboardInterrupt):
    restore_backup(archive, {"flm": root}, params, {"IsMetric", "FLMActiveOverrides"}, tmp_path, lambda: None)
  params.put = put
  return root, params


def test_interrupted_restore_is_rolled_back_from_its_recovery_record(tmp_path):
  from starpilot.system.the_galaxy.device_backup import pending_recoveries, recover_restore
  root, params = interrupted_restore(tmp_path)
  assert (root / "tune.json").read_text() == "{}", "the crash happened after files were replaced"
  [record] = pending_recoveries(tmp_path)
  recover_restore(record, params)
  assert (root / "tune.json").read_text() == "before"
  assert params.values == {"IsMetric": b"0", "FLMActiveOverrides": b"before"}
  assert not pending_recoveries(tmp_path)
  assert not list(tmp_path.glob("restore-*"))


def test_recovery_that_cannot_restore_a_file_keeps_its_copies(tmp_path):
  from starpilot.system.the_galaxy.device_backup import pending_recoveries, recover_restore
  root, params = interrupted_restore(tmp_path)
  [record] = pending_recoveries(tmp_path)
  (record.parent / "old/flm/tune.json").unlink()
  with pytest.raises(RuntimeError, match="Recovery copies kept"):
    recover_restore(record, params)
  assert record.exists()
  assert params.values == {"IsMetric": b"0", "FLMActiveOverrides": b"before"}, "settings are still rolled back"


@pytest.mark.parametrize("group,types,saved,bad", [
  ({"FLMActiveOverrides", "FLMActiveProfileId", "FLMTrialBaseline", "FLMTrialApplied"},
   {"FLMActiveOverrides": 5, "FLMActiveProfileId": 0, "FLMTrialBaseline": 5, "FLMTrialApplied": 1},
   {"FLMActiveOverrides": b'{"a":1}', "FLMActiveProfileId": b"saved", "FLMTrialBaseline": b'{"b":2}', "FLMTrialApplied": b"1"},
   ("FLMTrialApplied", b"yes")),
  ({"SafeMode", "SafeModeBackup"}, {"SafeMode": 1, "SafeModeBackup": 5},
   {"SafeMode": b"1", "SafeModeBackup": b'{"Model":"x"}'}, ("SafeModeBackup", b"not json")),
])
def test_coupled_settings_keep_current_values_together(tmp_path, group, types, saved, bad):
  import base64
  store = tmp_path / "store"
  store.mkdir()
  for key, value in {**saved, "IsMetric": b"1"}.items():
    (store / key).write_bytes(value)
  types = {**types, "IsMetric": 1}
  output = io.BytesIO()
  create_backup(output, {}, TypedParams(store, types), set(types))
  damaged = io.BytesIO()
  with zipfile.ZipFile(output) as source, zipfile.ZipFile(damaged, "w") as target:
    manifest = json.loads(source.read("manifest.json"))
    manifest["params"][bad[0]] = base64.b64encode(bad[1]).decode()
    target.writestr("manifest.json", json.dumps(manifest))
  params = TypedParams(store, types)
  params.values = {key: f"current {key}" for key in group}
  restored, _, skipped = restore_backup(damaged, {}, params, set(types), tmp_path, lambda: None)
  assert set(skipped) == group, "one undecodable member must not split its group"
  assert restored == 1
  assert params.values == {**{key: f"current {key}" for key in group}, "IsMetric": True}


def test_oversized_saved_profile_is_rejected_on_backup_and_restore(tmp_path, monkeypatch):
  import hashlib
  from starpilot.system.the_galaxy import device_backup
  monkeypatch.setattr(device_backup, "PROFILE_MAX_BYTES", 200)
  profiles = tmp_path / "profiles"
  profiles.mkdir()
  slot = json.dumps({"format": "starpilot-params-profile", "version": 1, "slot": "a",
                     "settings": {"IsMetric": {"type": 1, "value": "1" * 400}}}).encode()
  (profiles / ".params-profile-a.json").write_bytes(slot)
  with pytest.raises(ValueError, match="size limit"):
    create_backup(io.BytesIO(), {"profiles": profiles}, Params(), {"IsMetric"})
  archive = io.BytesIO()
  name = "profiles/.params-profile-a.json"
  with zipfile.ZipFile(archive, "w") as output:
    output.writestr(name, slot)
    output.writestr("manifest.json", json.dumps({"format": "starpilot-device-backup", "version": 3, "params": {}, "keys": [],
                                                 "files": {name: {"size": len(slot), "sha256": hashlib.sha256(slot).hexdigest()}}}))
  (profiles / ".params-profile-a.json").write_text("current")
  with pytest.raises(ValueError, match="size limit"):
    restore_backup(archive, {"profiles": profiles}, Params(), {"IsMetric"}, tmp_path, lambda: None)
  assert (profiles / ".params-profile-a.json").read_text() == "current"


def test_backup_larger_than_archive_limit_is_refused(tmp_path, monkeypatch):
  from starpilot.system.the_galaxy import device_backup
  monkeypatch.setattr(device_backup, "MAX_ARCHIVE_BYTES", 4096)
  flm = tmp_path / "flm"
  flm.mkdir()
  (flm / "report.html").write_bytes(b"x" * 8192)
  with pytest.raises(ValueError, match="limited to 8 GiB"):
    create_backup(io.BytesIO(), {"flm": flm}, Params(), set())


@pytest.mark.parametrize("kind,raw,expected", [
  (3, b"1.5", 1.5), (3, b"inf", None), (3, b"nan", None), (3, b"-inf", None),
  (1, b"1", True), (1, b"0", False), (1, b"true", None), (1, b"", None),
  (5, b'{"a":1}', {"a": 1}), (5, b"70", None), (5, b"not json", None),
  (2, b"70", 70), (2, b"seventy", None), (0, b"\xff", None),
])
def test_decode_rejects_non_finite_numbers_loose_booleans_and_wrong_json_shapes(tmp_path, kind, raw, expected):
  from starpilot.system.the_galaxy.device_backup import decode_param

  class StrictParams(TypedParams):
    def cpp2python(self, key, value):
      try:
        return self.decoders[self.types[key]](value)
      except (ValueError, UnicodeError):
        return None

  assert decode_param(StrictParams(tmp_path, {"Key": kind}), "Key", raw) == expected


def test_orphan_stage_cleanup_keeps_recovery_records(tmp_path):
  from starpilot.system.the_galaxy.device_backup import cleanup_stages, pending_recoveries

  orphan = tmp_path / "restore-orphan"
  (orphan / "new").mkdir(parents=True)
  keep = tmp_path / "restore-keep"
  keep.mkdir()
  (keep / "recovery.json").write_text("{}")
  (tmp_path / "unrelated").mkdir()
  cleanup_stages(tmp_path)
  assert not orphan.exists()
  assert keep.exists()
  assert pending_recoveries(tmp_path) == [keep / "recovery.json"]


def test_discard_recoveries_removes_every_record(tmp_path):
  from starpilot.system.the_galaxy.device_backup import discard_recoveries, pending_recoveries

  for name in ("restore-a", "restore-b"):
    (tmp_path / name).mkdir()
    (tmp_path / name / "recovery.json").write_text("{}")
  assert len(pending_recoveries(tmp_path)) == 2
  assert len(discard_recoveries(tmp_path)) == 2
  assert not pending_recoveries(tmp_path)


def test_cleanup_downloads_removes_stale_archives_only(tmp_path):
  from starpilot.system.the_galaxy.device_backup import cleanup_downloads

  downloads = tmp_path / "downloads"
  downloads.mkdir()
  (downloads / "starpilot-device-20260101-000000.zip").write_bytes(b"zip")
  (downloads / "keep.txt").write_text("note")
  cleanup_downloads(tmp_path)
  assert not (downloads / "starpilot-device-20260101-000000.zip").exists()
  assert (downloads / "keep.txt").exists()


def test_estimate_backup_bytes_counts_only_included_files(tmp_path):
  from starpilot.system.the_galaxy.device_backup import estimate_backup_bytes

  flm = tmp_path / "flm"
  flm.mkdir()
  (flm / "a.bin").write_bytes(b"x" * 100)
  profiles = tmp_path / "profiles"
  (profiles / "2026-01-01_auto").mkdir(parents=True)
  (profiles / "2026-01-01_auto" / "IsMetric").write_bytes(b"1")
  (profiles / "2026-01-01_auto" / "StarPilotApiToken").write_bytes(b"SECRET")
  themes = tmp_path / "themes"
  themes.mkdir()
  (themes / "linked").symlink_to(flm)
  assert estimate_backup_bytes({"flm": flm, "themes": themes, "profiles": profiles}, {"IsMetric"}) == 101


def test_check_backup_space_points_at_routes_then_allows_enough_room(tmp_path, monkeypatch):
  from collections import namedtuple
  from starpilot.system.the_galaxy import device_backup

  usage = namedtuple("usage", "total used free")
  monkeypatch.setattr(device_backup.shutil, "disk_usage", lambda _: usage(1, 0, device_backup.BACKUP_MARGIN_BYTES))
  with pytest.raises(ValueError, match="driving routes"):
    device_backup.check_backup_space(tmp_path, 1)
  with pytest.raises(ValueError, match="8 GiB limit"):
    device_backup.check_backup_space(tmp_path, device_backup.MAX_ARCHIVE_BYTES + 1)
  monkeypatch.setattr(device_backup.shutil, "disk_usage", lambda _: usage(1, 0, device_backup.BACKUP_MARGIN_BYTES + 1000))
  device_backup.check_backup_space(tmp_path, 1000)


def test_restore_upload_limit_caps_to_archive_size_then_free_space(tmp_path, monkeypatch):
  from collections import namedtuple
  from starpilot.system.the_galaxy import device_backup

  usage = namedtuple("usage", "total used free")
  huge = device_backup.RESTORE_MARGIN_BYTES + 3 * (device_backup.MAX_ARCHIVE_BYTES + 10)
  monkeypatch.setattr(device_backup.shutil, "disk_usage", lambda _: usage(1, 0, huge))
  assert device_backup.restore_upload_limit(tmp_path) == device_backup.MAX_ARCHIVE_BYTES
  monkeypatch.setattr(device_backup.shutil, "disk_usage", lambda _: usage(1, 0, device_backup.RESTORE_MARGIN_BYTES + 3000))
  assert device_backup.restore_upload_limit(tmp_path) == 1000
  monkeypatch.setattr(device_backup.shutil, "disk_usage", lambda _: usage(1, 0, 0))
  assert device_backup.restore_upload_limit(tmp_path) == 0
  assert device_backup.available_restore_bytes(tmp_path) == -device_backup.RESTORE_MARGIN_BYTES


def test_rollback_copies_and_replacements_fsync_their_directories(tmp_path, monkeypatch):
  from starpilot.system.the_galaxy import device_backup

  archive, root, params = backup_archive(tmp_path)
  synced = []
  real_fsync_dir = device_backup._fsync_dir
  monkeypatch.setattr(device_backup, "_fsync_dir", lambda path: (synced.append(str(path)), real_fsync_dir(path))[1])
  restore_backup(archive, {"flm": root}, params, {"IsMetric", "FLMActiveOverrides"}, tmp_path, lambda: None)
  assert any(path.endswith("old/flm") for path in synced), "rollback copies must be durable"
  assert any(path.endswith("flm") for path in synced), "atomic replacements must be durable"


def test_rollback_checks_parked_before_each_write(tmp_path):
  from starpilot.system.the_galaxy.device_backup import rollback
  params = Params()
  target = tmp_path / "tune.json"
  target.write_text("current")
  checks = []

  def parked():
    checks.append(True)
    if len(checks) >= 2:
      raise ValueError("ignition on")

  with pytest.raises(ValueError, match="ignition on"):
    rollback(params, {"IsMetric": b"0", "ScreenBrightness": b"20"}, [(target, None, False)], parked)
  assert params.values["IsMetric"] == b"0"
  assert "ScreenBrightness" not in params.values
  assert target.read_text() == "current"

  with pytest.raises(ValueError, match="ignition on"):
    rollback(params, {}, [(target, None, False)], parked)
