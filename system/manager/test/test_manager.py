import os
import pytest
import signal
import time
from pathlib import Path
import json

from cereal import car
from openpilot.common.params import Params
import openpilot.system.manager.manager as manager
from openpilot.system.manager.process import ensure_running
from openpilot.system.manager.process_config import big_device_ui_process, managed_processes, procs
from openpilot.system.hardware import HARDWARE

os.environ['FAKEUPLOAD'] = "1"

MAX_STARTUP_TIME = 3
BLACKLIST_PROCS = ['manage_athenad', 'pandad', 'pigeond']


class FileBackedFakeParams:
  def __init__(self, root: Path, values: dict[str, object] | None = None):
    self.root = root
    self.root.mkdir(parents=True, exist_ok=True)
    for key, value in (values or {}).items():
      self.put(key, value)

  def get_param_path(self, key):
    return str(self.root / (key.decode() if isinstance(key, bytes) else str(key)))

  def get(self, key):
    path = Path(self.get_param_path(key))
    if not path.is_file():
      return None

    raw = path.read_bytes()
    try:
      return raw.decode("utf-8")
    except UnicodeDecodeError:
      return raw

  def get_bool(self, key):
    value = self.get(key)
    if value is None:
      return False
    if isinstance(value, bytes):
      value = value.decode("utf-8", errors="ignore")
    return str(value).strip().lower() in ("1", "true", "yes", "on")

  def put(self, key, value):
    path = Path(self.get_param_path(key))
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(value, bytes):
      raw = value
    elif isinstance(value, bool):
      raw = b"1" if value else b"0"
    elif isinstance(value, float):
      raw = str(float(value)).encode("utf-8")
    elif isinstance(value, (dict, list)):
      raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
    else:
      raw = str(value).encode("utf-8")

    path.write_bytes(raw)

  def put_bool(self, key, value):
    self.put(key, bool(value))

  def put_float(self, key, value):
    self.put(key, float(value))

  def remove(self, key):
    Path(self.get_param_path(key)).unlink(missing_ok=True)


def test_navigation_selected_while_already_offroad_is_not_tracked_for_cleanup(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params", {
    "ClearNavOnOffroad": True,
    "ClearNavOnOffroadTimeoutMinutes": 0,
  })

  state = manager.update_nav_offroad_clear_state(
    params, False, None, None, 10.0, offroad_transition=False
  )
  assert state == (None, None)

  destination = {"name": "Home", "latitude": 1.0, "longitude": 2.0}
  params.put("NavDestination", destination)
  state = manager.update_nav_offroad_clear_state(
    params, False, *state, 20.0, offroad_transition=False
  )

  assert state == (None, None)
  assert json.loads(params.get("NavDestination")) == destination

  state = manager.update_nav_offroad_clear_state(
    params, True, *state, 30.0, offroad_transition=False
  )
  assert state == (None, None)
  assert json.loads(params.get("NavDestination")) == destination

  state = manager.update_nav_offroad_clear_state(
    params, False, *state, 40.0, offroad_transition=True
  )
  assert state == (None, None)
  assert params.get("NavDestination") is None


def test_replacement_destination_disarms_delayed_cleanup(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params", {
    "ClearNavOnOffroad": True,
    "ClearNavOnOffroadTimeoutMinutes": 15,
    "NavDestination": {"name": "Old", "latitude": 1.0, "longitude": 2.0},
  })

  tracked = manager.update_nav_offroad_clear_state(
    params, False, None, None, 10.0, offroad_transition=True
  )
  replacement = {"name": "New", "latitude": 3.0, "longitude": 4.0}
  params.put("NavDestination", replacement)

  state = manager.update_nav_offroad_clear_state(
    params, False, *tracked, 20.0, offroad_transition=False
  )

  assert state == (None, None)
  assert json.loads(params.get("NavDestination")) == replacement


def test_active_navigation_clears_on_offroad_transition(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params", {
    "ClearNavOnOffroad": True,
    "ClearNavOnOffroadTimeoutMinutes": 0,
    "NavDestination": {"name": "Home", "latitude": 1.0, "longitude": 2.0},
  })

  state = manager.update_nav_offroad_clear_state(
    params, False, None, None, 10.0, offroad_transition=True
  )

  assert state == (None, None)
  assert params.get("NavDestination") is None


def test_active_navigation_clears_after_offroad_timeout(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params", {
    "ClearNavOnOffroad": True,
    "ClearNavOnOffroadTimeoutMinutes": 15,
    "NavDestination": {"name": "Home", "latitude": 1.0, "longitude": 2.0},
  })

  tracked = manager.update_nav_offroad_clear_state(
    params, False, None, None, 10.0, offroad_transition=True
  )
  tracked = manager.update_nav_offroad_clear_state(
    params, False, *tracked, 909.0, offroad_transition=False
  )
  assert params.get("NavDestination") is not None

  state = manager.update_nav_offroad_clear_state(
    params, False, *tracked, 910.0, offroad_transition=False
  )

  assert state == (None, None)
  assert params.get("NavDestination") is None


def test_offroad_cleanup_does_not_remove_destination_replaced_after_snapshot(tmp_path):
  old_destination = json.dumps({"name": "Old", "latitude": 1.0, "longitude": 2.0})
  replacement_destination = {
    "name": "Home",
    "place_name": "Home",
    "latitude": 3.0,
    "longitude": 4.0,
  }

  class SnapshotRaceParams(FileBackedFakeParams):
    def __init__(self, root, values):
      self._first_nav_read = old_destination
      self.removed = []
      super().__init__(root, values)

    def get(self, key):
      if key == "NavDestination" and self._first_nav_read is not None:
        value, self._first_nav_read = self._first_nav_read, None
        return value
      return super().get(key)

    def remove(self, key):
      self.removed.append(key)
      super().remove(key)

  params = SnapshotRaceParams(tmp_path / "params", {
    "ClearNavOnOffroad": True,
    "ClearNavOnOffroadTimeoutMinutes": 0,
    "NavDestination": replacement_destination,
  })

  state = manager.update_nav_offroad_clear_state(
    params, False, None, None, 10.0, offroad_transition=True
  )

  assert state == (None, None)
  assert "NavDestination" not in params.removed


def test_reboot_guard_only_defers_automatic_requests():
  assert manager.should_defer_reboot("DoReboot", started=True, ignition=False)
  assert manager.should_defer_reboot("DoReboot", started=False, ignition=True)
  assert not manager.should_defer_reboot("DoReboot", started=False, ignition=False)
  assert not manager.should_defer_reboot("DoUserReboot", started=True, ignition=True)


def test_big_device_ui_process_always_launches_c3_ui():
  ui_process = big_device_ui_process()

  assert ui_process.cwd == "."
  assert ui_process.cmdline[0:2] == ["/usr/bin/env", "BIG=1"]
  assert ui_process.cmdline[-2:] == ["-m", "openpilot.selfdrive.ui.ui"]


class TestManager:
  @pytest.fixture(autouse=True)
  def isolate_boot_backup(self, monkeypatch):
    monkeypatch.setattr(manager, "starpilot_boot_functions", lambda *_args, **_kwargs: None)

  def setup_method(self):
    HARDWARE.set_power_save(False)

    # ensure clean CarParams
    params = Params()
    params.clear_all()

  def teardown_method(self):
    manager.manager_cleanup()

  def test_manager_prepare(self):
    os.environ['PREPAREONLY'] = '1'
    manager.main()

  def test_duplicate_procs(self):
    assert len(procs) == len(managed_processes), "Duplicate process names"

  def test_remote_access_procs_start_before_ui(self):
    names = [p.name for p in procs]
    ui_idx = names.index("ui")

    assert names.index("the_galaxy") < ui_idx
    assert names.index("galaxy") < ui_idx

  def test_blacklisted_procs(self):
    # TODO: ensure there are blacklisted procs until we have a dedicated test
    assert len(BLACKLIST_PROCS), "No blacklisted procs to test not_run"

  def test_set_params_with_default_value(self):
    params = Params()
    params.clear_all()

    os.environ['PREPAREONLY'] = '1'
    manager.main()
    for k in params.all_keys():
      default_value = params.get_default_value(k)
      if default_value not in (None, "", b""):
        assert params.get(k) is not None
    assert params.get("OpenpilotEnabledToggle")
    assert params.get("RouteCount") == 0

  def test_migrate_legacy_experimental_longitudinal(self):
    class FakeParams:
      def __init__(self, values):
        self.values = dict(values)

      def get(self, key):
        return self.values.get(key)

      def get_bool(self, key):
        value = self.values.get(key)
        if value is None:
          return False
        if isinstance(value, bytes):
          value = value.decode("utf-8", errors="ignore")
        if isinstance(value, str):
          return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)

      def put_bool(self, key, value):
        self.values[key] = b"1" if value else b"0"

      def remove(self, key):
        self.values.pop(key, None)

    params = FakeParams({"ExperimentalLongitudinalEnabled": b"1"})
    params_cache = FakeParams({})

    manager.migrate_legacy_experimental_longitudinal(params, params_cache)

    assert params.get_bool("AlphaLongitudinalEnabled")
    assert params_cache.get_bool("AlphaLongitudinalEnabled")
    assert params.get("ExperimentalLongitudinalEnabled") is None
    assert params_cache.get("ExperimentalLongitudinalEnabled") is None

  def test_migrate_starpilot_default_parity_preserves_existing_values(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG", tmp_path / "starpilot_defaults_parity_v1")

    params = FileBackedFakeParams(tmp_path / "params", {
      "AdvancedLateralTune": False,
      "ForceAutoTuneOff": False,
      "CEModelStopTime": 3.5,
    })
    params_cache = FileBackedFakeParams(tmp_path / "cache", {
      "NNFF": True,
    })

    manager.migrate_starpilot_default_parity(params, params_cache)

    assert not params.get_bool("AdvancedLateralTune")
    assert not params.get_bool("ForceAutoTuneOff")
    assert params.get("CEModelStopTime") == "3.5"
    assert params_cache.get_bool("NNFF")

  def test_migrate_starpilot_default_parity_seeds_new_model_stop_time_default(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG", tmp_path / "starpilot_defaults_parity_v1")

    params = FileBackedFakeParams(tmp_path / "params")
    params_cache = FileBackedFakeParams(tmp_path / "cache")

    manager.migrate_starpilot_default_parity(params, params_cache)

    assert params.get("CEModelStopTime") == "7.7"
    assert params_cache.get("CEModelStopTime") == "7.7"

  def test_migrate_starpilot_default_model(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_DEFAULT_MODEL_MIGRATION_FLAG", tmp_path / "starpilot_default_model_rdf_v4")

    params = FileBackedFakeParams(tmp_path / "params", {
      "Model": "sc2",
      "DrivingModel": "sc2",
      "DrivingModelName": "South Carolina",
      "ModelVersion": "v11",
      "DrivingModelVersion": "v11",
    })
    params_cache = FileBackedFakeParams(tmp_path / "cache")

    manager.migrate_starpilot_default_model(params, params_cache)

    assert params.get("Model") == "rdf43"
    assert params.get("DrivingModel") == "rdf43"
    assert params.get("DrivingModelName") == "Regret Driven Framework V4"
    assert params.get("ModelVersion") == "v15"
    assert params_cache.get("DrivingModel") == "rdf43"
    assert manager.STARPILOT_DEFAULT_MODEL_MIGRATION_FLAG.exists()

  def test_migrate_starpilot_ce_model_stop_time(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_CE_MODEL_STOP_TIME_MIGRATION_FLAG", tmp_path / "starpilot_ce_model_stop_time_v2")

    params = FileBackedFakeParams(tmp_path / "params", {"CEModelStopTime": 9.0})
    params_cache = FileBackedFakeParams(tmp_path / "cache")

    manager.migrate_starpilot_ce_model_stop_time(params, params_cache)

    assert params.get("CEModelStopTime") == "7.7"
    assert params_cache.get("CEModelStopTime") == "7.7"
    assert manager.STARPILOT_CE_MODEL_STOP_TIME_MIGRATION_FLAG.exists()

  def test_migrate_starpilot_ce_model_stop_time_preserves_custom_value(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_CE_MODEL_STOP_TIME_MIGRATION_FLAG", tmp_path / "starpilot_ce_model_stop_time_v2")

    params = FileBackedFakeParams(tmp_path / "params", {"CEModelStopTime": 8.0})
    params_cache = FileBackedFakeParams(tmp_path / "cache", {"CEModelStopTime": 8.0})

    manager.migrate_starpilot_ce_model_stop_time(params, params_cache)

    assert params.get("CEModelStopTime") == "8.0"
    assert params_cache.get("CEModelStopTime") == "8.0"

  def test_migrate_disable_humanlike_defaults(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_HUMANLIKE_DISABLE_MIGRATION_FLAG", tmp_path / "starpilot_humanlike_disable_v1")

    params = FileBackedFakeParams(tmp_path / "params", {})
    params_cache = FileBackedFakeParams(tmp_path / "cache", {
      "HumanLaneChanges": True,
    })

    manager.migrate_disable_humanlike_defaults(params, params_cache)

    assert not params.get_bool("HumanLaneChanges")
    assert not params_cache.get_bool("HumanLaneChanges")

  def test_cleanup_removed_starpilot_params(self, tmp_path):
    params = FileBackedFakeParams(tmp_path / "params", {
      "CoastUpToLeads": True,
      "HumanAcceleration": True,
      "HumanFollowing": True,
      "ReverseCruise": True,
    })
    params_cache = FileBackedFakeParams(tmp_path / "cache", {
      "HumanFollowing": False,
      "PrioritizeSmoothFollowing": True,
    })

    manager.cleanup_removed_starpilot_params(params, params_cache)

    assert not Path(params.get_param_path("CoastUpToLeads")).exists()
    assert not Path(params.get_param_path("HumanAcceleration")).exists()
    assert not Path(params.get_param_path("HumanFollowing")).exists()
    assert params.get_bool("ReverseCruise")
    assert not Path(params_cache.get_param_path("HumanFollowing")).exists()
    assert not Path(params_cache.get_param_path("PrioritizeSmoothFollowing")).exists()

  def test_migrate_legacy_starpilot_params_cache_copies_marker_sources(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_PARAMS_CACHE_MIGRATION_FLAG", tmp_path / "starpilot_params_cache_v1")

    params = FileBackedFakeParams(tmp_path / "params")
    legacy_cache = tmp_path / "legacy_cache"
    new_cache = tmp_path / "new_cache"
    legacy_store = manager._params_store_path(legacy_cache)
    legacy_store.mkdir(parents=True)
    (legacy_store / "RemapCancelToDistance").write_text("0")
    (legacy_store / "ClusterOffset").write_text("1.02")

    manager.migrate_legacy_starpilot_params_cache(params, legacy_cache, new_cache)

    new_store = manager._params_store_path(new_cache)
    assert (new_store / "RemapCancelToDistance").read_text() == "0"
    assert (new_store / "ClusterOffset").read_text() == "1.02"
    assert manager.STARPILOT_PARAMS_CACHE_MIGRATION_FLAG.exists()

  def test_migrate_legacy_starpilot_params_cache_skips_without_marker(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_PARAMS_CACHE_MIGRATION_FLAG", tmp_path / "starpilot_params_cache_v1")

    params = FileBackedFakeParams(tmp_path / "params")
    legacy_cache = tmp_path / "legacy_cache"
    new_cache = tmp_path / "new_cache"
    legacy_store = manager._params_store_path(legacy_cache)
    legacy_store.mkdir(parents=True)
    (legacy_store / "ClusterOffset").write_text("1.02")

    manager.migrate_legacy_starpilot_params_cache(params, legacy_cache, new_cache)

    assert not (manager._params_store_path(new_cache) / "ClusterOffset").exists()
    assert manager.STARPILOT_PARAMS_CACHE_MIGRATION_FLAG.exists()

  def test_migrate_legacy_starpilot_params_cache_does_not_overwrite_new_cache(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_PARAMS_CACHE_MIGRATION_FLAG", tmp_path / "starpilot_params_cache_v1")

    params = FileBackedFakeParams(tmp_path / "params")
    legacy_cache = tmp_path / "legacy_cache"
    new_cache = tmp_path / "new_cache"
    legacy_store = manager._params_store_path(legacy_cache)
    new_store = manager._params_store_path(new_cache)
    legacy_store.mkdir(parents=True)
    new_store.mkdir(parents=True)
    (legacy_store / "RemapCancelToDistance").write_text("0")
    (legacy_store / "ClusterOffset").write_text("1.02")
    (new_store / "ClusterOffset").write_text("1.0")

    manager.migrate_legacy_starpilot_params_cache(params, legacy_cache, new_cache)

    assert (new_store / "ClusterOffset").read_text() == "1.0"
    assert (new_store / "RemapCancelToDistance").read_text() == "0"

  @pytest.mark.parametrize("direct_backup", [False, True])
  def test_migrate_legacy_secoc_key_without_starpilot_marker(self, tmp_path, direct_backup):
    params = FileBackedFakeParams(tmp_path / "params")
    params_cache = FileBackedFakeParams(tmp_path / "cache")
    legacy_cache = tmp_path / "legacy_cache"
    legacy_cache.mkdir()
    legacy_store = legacy_cache if direct_backup else manager._params_store_path(legacy_cache)
    legacy_store.mkdir(exist_ok=True)
    (legacy_store / "SecOCKey").write_text("00112233445566778899aabbccddeeff")

    manager.migrate_legacy_secoc_key(params, params_cache, legacy_cache)

    assert params.get("SecOCKey") == "00112233445566778899aabbccddeeff"
    assert params_cache.get("SecOCKey") == "00112233445566778899aabbccddeeff"

  def test_migrate_legacy_secoc_key_rejects_invalid_key(self, tmp_path):
    params = FileBackedFakeParams(tmp_path / "params")
    params_cache = FileBackedFakeParams(tmp_path / "cache")
    legacy_cache = tmp_path / "legacy_cache"
    legacy_cache.mkdir()
    (legacy_cache / "SecOCKey").write_text("not-a-valid-key")

    manager.migrate_legacy_secoc_key(params, params_cache, legacy_cache)

    assert params.get("SecOCKey") is None
    assert params_cache.get("SecOCKey") is None

  def test_migrate_cluster_offset_default_resets_legacy_default_only(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_CLUSTER_OFFSET_MIGRATION_FLAG", tmp_path / "starpilot_cluster_offset_v1")

    params = FileBackedFakeParams(tmp_path / "params", {
      "ClusterOffset": 1.015,
    })
    params_cache = FileBackedFakeParams(tmp_path / "cache", {})

    manager.migrate_cluster_offset_default(params, params_cache)

    assert params.get("ClusterOffset") == "1.0"
    assert params_cache.get("ClusterOffset") == "1.0"

  def test_migrate_cluster_offset_default_preserves_custom_values(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_CLUSTER_OFFSET_MIGRATION_FLAG", tmp_path / "starpilot_cluster_offset_v1")

    params = FileBackedFakeParams(tmp_path / "params", {
      "ClusterOffset": 1.02,
    })
    params_cache = FileBackedFakeParams(tmp_path / "cache", {})

    manager.migrate_cluster_offset_default(params, params_cache)

    assert params.get("ClusterOffset") == "1.02"
    assert params_cache.get("ClusterOffset") is None

  def test_migrate_traffic_mode_smooth_defaults_resets_legacy_default_only(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_TRAFFIC_SMOOTH_MIGRATION_FLAG", tmp_path / "starpilot_traffic_smooth_v1")

    params = FileBackedFakeParams(tmp_path / "params", {
      "TrafficJerkAcceleration": 50.0,
      "TrafficJerkDeceleration": 50.0,
      "TrafficJerkSpeed": 50.0,
    })
    params_cache = FileBackedFakeParams(tmp_path / "cache", {})

    manager.migrate_traffic_mode_smooth_defaults(params, params_cache)

    for key in ("TrafficJerkAcceleration", "TrafficJerkDeceleration", "TrafficJerkSpeed"):
      assert params.get(key) == "100.0"
      assert params_cache.get(key) == "100.0"
    # unset keys stay unset so the new compiled default applies on its own
    assert params.get("TrafficJerkSpeedDecrease") is None
    assert manager.STARPILOT_TRAFFIC_SMOOTH_MIGRATION_FLAG.exists()

  def test_migrate_traffic_mode_smooth_defaults_preserves_custom_values(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_TRAFFIC_SMOOTH_MIGRATION_FLAG", tmp_path / "starpilot_traffic_smooth_v1")

    params = FileBackedFakeParams(tmp_path / "params", {
      "TrafficJerkAcceleration": 80.0,
    })
    params_cache = FileBackedFakeParams(tmp_path / "cache", {})

    manager.migrate_traffic_mode_smooth_defaults(params, params_cache)

    assert params.get("TrafficJerkAcceleration") == "80.0"
    assert params_cache.get("TrafficJerkAcceleration") is None

  def test_migrate_traffic_follow_default_resets_legacy_default_only(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_TRAFFIC_FOLLOW_MIGRATION_FLAG", tmp_path / "starpilot_traffic_follow_v1")

    params = FileBackedFakeParams(tmp_path / "params", {
      "TrafficFollow": 0.5,
    })
    params_cache = FileBackedFakeParams(tmp_path / "cache", {})

    manager.migrate_traffic_follow_default(params, params_cache)

    assert params.get("TrafficFollow") == "0.75"
    assert params_cache.get("TrafficFollow") == "0.75"
    assert manager.STARPILOT_TRAFFIC_FOLLOW_MIGRATION_FLAG.exists()

  def test_migrate_traffic_follow_default_preserves_custom_values(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_TRAFFIC_FOLLOW_MIGRATION_FLAG", tmp_path / "starpilot_traffic_follow_v1")

    params = FileBackedFakeParams(tmp_path / "params", {
      "TrafficFollow": 1.2,
    })
    params_cache = FileBackedFakeParams(tmp_path / "cache", {})

    manager.migrate_traffic_follow_default(params, params_cache)

    assert params.get("TrafficFollow") == "1.2"
    assert params_cache.get("TrafficFollow") is None

  def test_migrate_traffic_mode_smooth_defaults_runs_once(self, tmp_path, monkeypatch):
    monkeypatch.setattr(manager, "STARPILOT_TRAFFIC_SMOOTH_MIGRATION_FLAG", tmp_path / "starpilot_traffic_smooth_v1")

    params = FileBackedFakeParams(tmp_path / "params", {"TrafficJerkAcceleration": 50.0})
    params_cache = FileBackedFakeParams(tmp_path / "cache", {})

    manager.migrate_traffic_mode_smooth_defaults(params, params_cache)
    params.put_float("TrafficJerkAcceleration", 50.0)
    manager.migrate_traffic_mode_smooth_defaults(params, params_cache)

    assert params.get("TrafficJerkAcceleration") == "50.0"

  def test_cleanup_inaccessible_msgq_files_removes_only_blocked_files(self, tmp_path, monkeypatch):
    healthy = tmp_path / "msgq_deviceState"
    blocked = tmp_path / "msgq_gpsLocation"
    unrelated = tmp_path / "not_msgq_gpsLocation"
    healthy.write_bytes(b"healthy")
    blocked.write_bytes(b"blocked")
    unrelated.write_bytes(b"unrelated")

    def fake_open_probe(path):
      if path == blocked:
        raise PermissionError("blocked")
      return True

    monkeypatch.setattr(manager, "_msgq_file_is_readwrite_openable", fake_open_probe)

    assert manager.cleanup_inaccessible_msgq_files(tmp_path) == 1
    assert healthy.read_bytes() == b"healthy"
    assert not blocked.exists()
    assert unrelated.read_bytes() == b"unrelated"

  def test_cleanup_inaccessible_msgq_files_ignores_msgq_directories(self, tmp_path, monkeypatch):
    msgq_dir = tmp_path / "msgq_desktop"
    msgq_dir.mkdir()
    child = msgq_dir / "gpsLocation"
    child.write_bytes(b"child")

    def fake_open_probe(path):
      raise AssertionError(f"directories and non-msgq children should not be probed: {path}")

    monkeypatch.setattr(manager, "_msgq_file_is_readwrite_openable", fake_open_probe)

    assert manager.cleanup_inaccessible_msgq_files(tmp_path) == 0
    assert child.read_bytes() == b"child"

  @pytest.mark.skip("this test is flaky the way it's currently written, should be moved to test_onroad")
  def test_clean_exit(self, subtests):
    """
      Ensure all processes exit cleanly when stopped.
    """
    HARDWARE.set_power_save(False)
    manager.manager_init()

    CP = car.CarParams.new_message()
    procs = ensure_running(managed_processes.values(), True, Params(), CP, not_run=BLACKLIST_PROCS)

    time.sleep(10)

    for p in procs:
      with subtests.test(proc=p.name):
        state = p.get_process_state_msg()
        assert state.running, f"{p.name} not running"
        exit_code = p.stop(retry=False)

        assert p.name not in BLACKLIST_PROCS, f"{p.name} was started"

        assert exit_code is not None, f"{p.name} failed to exit"

        # TODO: interrupted blocking read exits with 1 in cereal. use a more unique return code
        exit_codes = [0, 1]
        if p.sigkill:
          exit_codes = [-signal.SIGKILL]
        assert exit_code in exit_codes, f"{p.name} died with {exit_code}"
