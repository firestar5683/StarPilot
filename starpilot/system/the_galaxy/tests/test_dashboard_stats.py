import importlib.util
import json
import os
import sys

import pytest

from pathlib import Path
from types import ModuleType, SimpleNamespace


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
  sys.path.insert(0, str(MODULE_DIR))

_INITIAL_STUB_NAMES = (
  "openpilot.system.loggerd.config",
  "openpilot.system.loggerd.deleter",
  "openpilot.system.loggerd.uploader",
  "openpilot.starpilot.assets.model_manager",
  "openpilot.starpilot.common.starpilot_variables",
  "openpilot.starpilot.assets.theme_manager",
)
_INITIAL_MODULES = {name: sys.modules.get(name) for name in _INITIAL_STUB_NAMES}

loggerd_config = ModuleType("openpilot.system.loggerd.config")
loggerd_config.get_available_bytes = lambda default=0: default
loggerd_config.get_used_bytes = lambda default=0: default
sys.modules.setdefault("openpilot.system.loggerd.config", loggerd_config)

loggerd_deleter = ModuleType("openpilot.system.loggerd.deleter")
loggerd_deleter.PRESERVE_ATTR_NAME = "preserve"
loggerd_deleter.PRESERVE_ATTR_VALUE = b"1"
loggerd_deleter.PRESERVE_COUNT = 0
sys.modules.setdefault("openpilot.system.loggerd.deleter", loggerd_deleter)

loggerd_uploader = ModuleType("openpilot.system.loggerd.uploader")
loggerd_uploader.listdir_by_creation = lambda path: [
  entry.name for entry in sorted(Path(path).iterdir(), key=lambda entry: entry.stat().st_ctime)
]
sys.modules.setdefault("openpilot.system.loggerd.uploader", loggerd_uploader)

model_manager = ModuleType("openpilot.starpilot.assets.model_manager")
model_manager.canonical_model_key = lambda value: str(value or "").strip().lower().replace(" ", "-")
sys.modules.setdefault("openpilot.starpilot.assets.model_manager", model_manager)

starpilot_variables = ModuleType("openpilot.starpilot.common.starpilot_variables")
starpilot_variables.THEME_SAVE_PATH = Path("/tmp/dashboard-test-themes")
starpilot_variables.VIDEO_CACHE_PATH = Path("/tmp/dashboard-test-video-cache")
sys.modules.setdefault("openpilot.starpilot.common.starpilot_variables", starpilot_variables)

theme_manager = ModuleType("openpilot.starpilot.assets.theme_manager")
theme_manager.HOLIDAY_THEME_PATH = Path("/tmp/dashboard-test-holiday-themes")
sys.modules.setdefault("openpilot.starpilot.assets.theme_manager", theme_manager)

import utilities

for _module_name, _module in _INITIAL_MODULES.items():
  if _module is None:
    sys.modules.pop(_module_name, None)
  else:
    sys.modules[_module_name] = _module

_SERVER_MODULE_SNAPSHOTS = []


@pytest.fixture(autouse=True)
def restore_server_import_stubs():
  yield
  while _SERVER_MODULE_SNAPSHOTS:
    snapshot = _SERVER_MODULE_SNAPSHOTS.pop()
    for name in set(sys.modules) - set(snapshot):
      sys.modules.pop(name, None)
    sys.modules.update(snapshot)


def _simple_module(name, **attrs):
  module = ModuleType(name)
  for attr, value in attrs.items():
    setattr(module, attr, value)
  return module


def _install_server_import_stubs():
  sys.modules["openpilot.system.loggerd.config"] = loggerd_config
  sys.modules["openpilot.system.loggerd.deleter"] = loggerd_deleter
  sys.modules["openpilot.system.loggerd.uploader"] = loggerd_uploader
  sys.modules["openpilot.starpilot.assets.model_manager"] = model_manager
  sys.modules["openpilot.starpilot.common.starpilot_variables"] = starpilot_variables
  sys.modules["openpilot.starpilot.assets.theme_manager"] = theme_manager

  cereal_module = _simple_module("cereal")
  car_module = _simple_module("cereal.car", CarParams=SimpleNamespace(from_bytes=lambda _: SimpleNamespace(__enter__=lambda self: self, __exit__=lambda *args: None)))
  custom_module = _simple_module("cereal.custom", StarPilotCarParams=object)
  log_module = _simple_module(
    "cereal.log",
    Event=object,
    DeviceState=SimpleNamespace(NetworkType=SimpleNamespace(none=0)),
    LiveDelayData=SimpleNamespace(Status=SimpleNamespace(estimated=1, unestimated=2, invalid=3)),
  )
  messaging_module = _simple_module(
    "cereal.messaging",
    SubMaster=lambda *args, **kwargs: {},
    PubMaster=lambda *args, **kwargs: SimpleNamespace(send=lambda *send_args, **send_kwargs: None),
    new_message=lambda *args, **kwargs: SimpleNamespace(),
    log_from_bytes=lambda *args, **kwargs: SimpleNamespace(liveDelay=SimpleNamespace(status=0)),
    sub_sock=lambda *args, **kwargs: None,
  )
  cereal_module.car = car_module
  cereal_module.custom = custom_module
  cereal_module.log = log_module
  cereal_module.messaging = messaging_module

  sys.modules["cereal"] = cereal_module
  sys.modules["cereal.car"] = car_module
  sys.modules["cereal.custom"] = custom_module
  sys.modules["cereal.log"] = log_module
  sys.modules["cereal.messaging"] = messaging_module

  sys.modules["opendbc.can.parser"] = _simple_module("opendbc.can.parser", CANParser=lambda *args, **kwargs: SimpleNamespace())
  sys.modules["opendbc.car.gm.values"] = _simple_module("opendbc.car.gm.values", GMFlags=SimpleNamespace(SASCM=SimpleNamespace(value=1)))
  sys.modules["opendbc.car.toyota.carcontroller"] = _simple_module("opendbc.car.toyota.carcontroller", LOCK_CMD=b"", UNLOCK_CMD=b"")
  sys.modules["opendbc.car.toyota.values"] = _simple_module(
    "opendbc.car.toyota.values",
    ToyotaStarPilotFlags=SimpleNamespace(SMART_DSU=SimpleNamespace(value=1), ZSS=SimpleNamespace(value=2)),
  )

  sys.modules["openpilot.common.realtime"] = _simple_module("openpilot.common.realtime", DT_HW=0.01)
  sys.modules["openpilot.common.time_helpers"] = _simple_module("openpilot.common.time_helpers", system_time_valid=lambda: True)
  sys.modules["openpilot.system.hardware"] = _simple_module(
    "openpilot.system.hardware",
    HARDWARE=SimpleNamespace(reboot=lambda: None, get_device_type=lambda: "pc", get_network_type=lambda: 1),
    PC=True,
  )
  sys.modules["openpilot.system.hardware.hw"] = _simple_module(
    "openpilot.system.hardware.hw",
    Paths=SimpleNamespace(
      comma_home=lambda: "/tmp/dashboard-test-comma-home",
      log_root=lambda **kwargs: "/tmp/dashboard-test-routes/",
    ),
  )
  sys.modules["openpilot.system.version"] = _simple_module("openpilot.system.version", get_build_metadata=lambda: SimpleNamespace())
  sys.modules["openpilot.tools.longitudinal_maneuvers.capabilities"] = _simple_module(
    "openpilot.tools.longitudinal_maneuvers.capabilities",
    get_longitudinal_maneuver_support=lambda *args, **kwargs: {},
  )
  sys.modules["panda"] = _simple_module("panda", Panda=lambda *args, **kwargs: SimpleNamespace(can_send=lambda *send_args, **send_kwargs: None))

  model_manager.is_builtin_model_key = lambda value: False
  model_manager.model_key_aliases = lambda value: [value]
  theme_manager.THEME_COMPONENT_PARAMS = {}

  sys.modules["openpilot.starpilot.common.accel_profile"] = _simple_module(
    "openpilot.starpilot.common.accel_profile",
    CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY="CustomAccelProfileInitialized",
    CUSTOM_ACCEL_PROFILE_PARAM_KEYS=[],
    build_custom_accel_profile_defaults=lambda *args, **kwargs: {},
    custom_accel_profile_is_initialized=lambda *args, **kwargs: False,
    normalize_acceleration_profile=lambda value: value,
  )
  sys.modules["openpilot.starpilot.common.maps_catalog"] = _simple_module(
    "openpilot.starpilot.common.maps_catalog",
    MAPS_CATALOG=[],
    MAP_SCHEDULE_OPTIONS=[],
    get_selected_map_entries=lambda *args, **kwargs: [],
    sanitize_selected_locations_csv=lambda value: value,
    schedule_label=lambda value: value,
    schedule_param_value=lambda value: value,
  )
  sys.modules["openpilot.starpilot.common.model_versions"] = _simple_module(
    "openpilot.starpilot.common.model_versions",
    is_tinygrad_model_version=lambda *args, **kwargs: False,
    uses_combined_driving_artifacts=lambda *args, **kwargs: False,
    uses_split_off_policy_artifacts=lambda *args, **kwargs: False,
  )
  sys.modules["openpilot.starpilot.common.experimental_state"] = _simple_module(
    "openpilot.starpilot.common.experimental_state",
    sync_persist_chill_state=lambda *args, **kwargs: None,
    sync_persist_experimental_state=lambda *args, **kwargs: None,
  )
  def _trigger_stub_favorite_action(key, params_memory=None):
    if params_memory is None:
      return False
    counter_key = (
      "FavoriteVirtualAccelCruiseCounter"
      if str(key or "").endswith("distance_increase")
      else "FavoriteVirtualDecelCruiseCounter"
    )
    params_memory.put_int(counter_key, params_memory.get_int(counter_key) + 1)
    return True

  sys.modules["openpilot.starpilot.common.favorite_slots"] = _simple_module(
    "openpilot.starpilot.common.favorite_slots",
    FAVORITE_ACTION_OPTIONS=(
      {
        "key": "__starpilot_favorite_action__:distance_decrease",
        "label": "Distance - / SET",
        "description": "Acts like a short press of the car's SET/- cruise button.",
        "section": "Actions",
        "action": "decelCruise",
      },
      {
        "key": "__starpilot_favorite_action__:distance_increase",
        "label": "Distance + / RES",
        "description": "Acts like a short press of the car's RES/+ cruise button.",
        "section": "Actions",
        "action": "accelCruise",
      },
    ),
    FAVORITE_SLOTS_PARAM="FavoriteSlots",
    is_favorite_action_key=lambda key: str(key or "").startswith("__starpilot_favorite_action__:"),
    normalize_favorite_slots=lambda *args, **kwargs: "",
    trigger_favorite_action=_trigger_stub_favorite_action,
  )
  sys.modules["openpilot.starpilot.common.starpilot_utilities"] = _simple_module(
    "openpilot.starpilot.common.starpilot_utilities",
    delete_file=lambda *args, **kwargs: None,
    get_lock_status=lambda *args, **kwargs: {},
    run_cmd=lambda *args, **kwargs: None,
  )
  for name, value in {
    "ACTIVE_THEME_PATH": Path("/tmp/dashboard-test-active-theme"),
    "ERROR_LOGS_PATH": "/tmp/dashboard-test-errors",
    "EXCLUDED_KEYS": set(),
    "LEGACY_STARPILOT_PARAM_RENAMES": {},
    "MAPS_PATH": Path("/tmp/dashboard-test-maps"),
    "MODELS_PATH": Path("/tmp/dashboard-test-models"),
    "RESOURCES_REPO": "resources",
    "SCREEN_RECORDINGS_PATH": Path("/tmp/dashboard-test-recordings"),
    "STOCK_THEME_PATH": Path("/tmp/dashboard-test-stock-theme"),
    "THEME_SAVE_PATH": Path("/tmp/dashboard-test-themes"),
  }.items():
    setattr(starpilot_variables, name, value)
  starpilot_variables.default_ev_tuning_enabled = lambda *args, **kwargs: False
  starpilot_variables.migrate_cancel_button_controls = lambda *args, **kwargs: False
  starpilot_variables.update_starpilot_toggles = lambda *args, **kwargs: None

  sys.modules["openpilot.starpilot.common.testing_grounds"] = _simple_module(
    "openpilot.starpilot.common.testing_grounds",
    DEFAULT_TESTING_GROUND_VARIANT="standard",
    TESTING_GROUND_VARIANT_LABELS={},
    TESTING_GROUND_VARIANTS=("standard",),
    TESTING_GROUNDS_SCHEMA_VERSION=1,
    TESTING_GROUNDS_SLOT_DEFINITIONS=(),
    TESTING_GROUNDS_STATE_PATH=Path("/tmp/dashboard-test-testing-grounds.json"),
  )
  sys.modules["openpilot.starpilot.navigation.destination_store"] = _simple_module(
    "openpilot.starpilot.navigation.destination_store",
    normalize_destination_payload=lambda payload: payload,
    update_recent_destinations=lambda *args, **kwargs: [],
  )
  sys.modules["openpilot.starpilot.system.the_galaxy.factory_reset"] = _simple_module(
    "openpilot.starpilot.system.the_galaxy.factory_reset",
    remove_path=lambda *args, **kwargs: None,
  )
  sys.modules["openpilot.starpilot.system.the_galaxy.flm_workspace"] = _simple_module(
    "openpilot.starpilot.system.the_galaxy.flm_workspace",
  )
  sys.modules["openpilot.starpilot.system.the_galaxy.utilities"] = utilities


class FakeParams:
  def __init__(self, values=None):
    self.values = values or {}

  def get(self, key, encoding=None, default=None, block=False):
    del block
    value = self.values.get(key, default)
    if encoding and isinstance(value, bytes):
      return value.decode(encoding, errors="replace")
    return value

  def get_bool(self, key):
    value = self.values.get(key, False)
    if isinstance(value, bool):
      return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")

  def put(self, key, value):
    self.values[key] = value


class FailingPutParams(FakeParams):
  def put(self, key, value):
    raise RuntimeError("unknown key")


class FakeDashboardAnalyzerProcess:
  def __init__(self):
    self.terminated = False

  def poll(self):
    return None

  def terminate(self):
    self.terminated = True


def test_route_inventory_counts_segments_without_video_probing(monkeypatch):
  segments = [
    SimpleNamespace(route_name=SimpleNamespace(time_str="route-new")),
    SimpleNamespace(route_name=SimpleNamespace(time_str="route-new")),
    SimpleNamespace(route_name=SimpleNamespace(time_str="route-new")),
    SimpleNamespace(route_name=SimpleNamespace(time_str="route-old")),
  ]
  monkeypatch.setattr(utilities, "get_all_segment_names", lambda _path: segments)

  assert utilities.get_routes_with_segment_counts("/tmp/routes") == [
    ("route-old", 1),
    ("route-new", 3),
  ]


def test_dashboard_background_analysis_does_not_start_onroad(monkeypatch):
  def fail_if_started(*args, **kwargs):
    raise AssertionError("worker started onroad")

  monkeypatch.setattr(utilities, "params", FakeParams({"IsOnroad": True}))
  monkeypatch.setattr(utilities.subprocess, "Popen", fail_if_started)

  started = utilities._start_dashboard_background_analysis(
    ["/tmp/routes"],
    [{"name": "route"}],
    {},
    [{"name": "route"}],
  )

  assert started is False


def test_dashboard_analysis_worker_exits_onroad_before_scanning(monkeypatch):
  def fail_if_scanned(*args, **kwargs):
    raise AssertionError("routes scanned onroad")

  monkeypatch.setattr(utilities, "params", FakeParams({"IsOnroad": True}))
  monkeypatch.setattr(utilities, "_list_dashboard_routes", fail_if_scanned)

  utilities.warm_dashboard_stats(["/tmp/routes"])


def test_stop_dashboard_background_analysis_terminates_owned_worker(monkeypatch, tmp_path):
  process = FakeDashboardAnalyzerProcess()
  status_path = tmp_path / "dashboard_analyzer_status.json"
  status_path.write_text('{"pid":123}')
  monkeypatch.setattr(utilities, "_DASHBOARD_ANALYZER_PROCESS", process)
  monkeypatch.setattr(utilities, "DASHBOARD_ANALYZER_STATUS_PATH", status_path)

  stopped = utilities.stop_dashboard_background_analysis()

  assert stopped is True
  assert process.terminated is True
  assert utilities._DASHBOARD_ANALYZER_PROCESS is None
  assert not status_path.exists()


class FakeMessage:
  def __init__(self, kind, log_mono_time, payload):
    self._kind = kind
    self.logMonoTime = log_mono_time
    setattr(self, kind, payload)

  def which(self):
    return self._kind


def msg(kind, seconds, payload):
  return FakeMessage(kind, int(seconds * 1e9), payload)


def events(*names):
  return [SimpleNamespace(name=name) for name in names]


def test_drive_stats_cloud_distances_match_native_imperial_units(monkeypatch):
  monkeypatch.setattr(utilities, "params", FakeParams({
    "IsMetric": False,
    "ApiCache_DriveStats": {
      "all": {"distance": 100.0, "routes": 12, "minutes": 360},
      "week": {"distance": 25.0, "routes": 3, "minutes": 90},
    },
    "StarPilotStats": {
      "StarPilotMeters": 1609.344,
      "StarPilotSeconds": 3600,
      "StarPilotDrives": 2,
    },
  }))

  stats = utilities.get_drive_stats()

  assert stats["all"]["distance"] == 100.0
  assert stats["all"]["drives"] == 12
  assert stats["all"]["hours"] == 6
  assert stats["week"]["distance"] == 25.0
  assert stats["starpilot"]["distance"] == 1.0
  assert stats["starpilot"]["hours"] == 1
  assert stats["starpilot"]["drives"] == 2


def test_drive_stats_cloud_distances_match_native_metric_units(monkeypatch):
  monkeypatch.setattr(utilities, "params", FakeParams({
    "IsMetric": True,
    "ApiCache_DriveStats": {
      "all": {"distance": 10.0, "routes": 2, "minutes": 60},
      "week": {"distance": 5.0, "routes": 1, "minutes": 30},
    },
    "StarPilotStats": {
      "StarPilotMeters": 1000.0,
      "StarPilotSeconds": 1800,
      "StarPilotDrives": 1,
    },
  }))

  stats = utilities.get_drive_stats()

  assert round(stats["all"]["distance"], 3) == 16.093
  assert round(stats["week"]["distance"], 3) == 8.047
  assert stats["starpilot"]["distance"] == 1.0
  assert stats["starpilot"]["hours"] == 0.5
  assert stats["starpilot"]["drives"] == 1


def test_route_metrics_count_selected_attention_events():
  route = {
    "name": "route-a",
    "segmentCount": 1,
    "startedAt": None,
  }
  messages = [
    msg("initData", 0, SimpleNamespace(params={"DrivingModelName": b"North Star"})),
    msg("carState", 0, SimpleNamespace(vEgo=10.0)),
    msg("selfdriveState", 0, SimpleNamespace(enabled=True)),
    msg("onroadEvents", 1, events("driverDistracted2")),
    msg("onroadEvents", 2, events("driverDistracted2")),
    msg("onroadEvents", 3, events()),
    msg("onroadEvents", 4, events("driverDistracted2")),
    msg("onroadEvents", 5, events("driverUnresponsive3")),
    msg("onroadEvents", 6, events("driverUnresponsive3")),
    msg("carState", 10, SimpleNamespace(vEgo=10.0)),
    msg("selfdriveState", 10, SimpleNamespace(enabled=False)),
  ]

  drive = utilities._analyze_route_messages(messages, route, {}, is_metric=False)

  assert drive["distance"] == 0.1
  assert drive["duration"] == 10
  assert drive["avgSpeed"] == 22
  assert drive["engagedPercent"] == 100
  assert drive["model"] == "North Star"
  assert drive["distractedMoments"] == 2
  assert drive["unresponsiveMoments"] == 1


def test_route_model_falls_back_to_catalog_key():
  route = {"name": "route-a", "segmentCount": 1, "startedAt": None}
  messages = [
    msg("initData", 0, SimpleNamespace(params={"Model": b"orion"})),
  ]
  model_names = {"orion": {"name": "Orion", "series": "City", "key": "orion"}}

  drive = utilities._analyze_route_messages(messages, route, model_names, is_metric=True)

  assert drive["model"] == "Orion"


def test_route_model_reads_logged_param_entries():
  route = {"name": "route-a", "segmentCount": 1, "startedAt": None}
  params = SimpleNamespace(entries=[
    SimpleNamespace(key="Model", value=b"orion"),
  ])
  messages = [
    msg("initData", 0, SimpleNamespace(params=params)),
  ]
  model_names = {"orion": {"name": "Orion", "series": "City", "key": "orion"}}

  drive = utilities._analyze_route_messages(messages, route, model_names, is_metric=True)

  assert drive["model"] == "Orion"


def test_route_date_uses_logged_wall_time_before_directory_mtime():
  route = {
    "name": "route-a",
    "segmentCount": 1,
    "startedAt": utilities.datetime(2026, 6, 18, 9, 24, 0),
    "modifiedAt": utilities.datetime(2026, 6, 18, 9, 24, 0).timestamp(),
  }
  logged_start = utilities.datetime(2026, 6, 17, 21, 53, 0)
  messages = [
    msg("initData", 100, SimpleNamespace(params={"Model": b"orion"}, wallTimeNanos=int(logged_start.timestamp() * 1e9))),
    msg("carState", 100, SimpleNamespace(vEgo=10.0)),
    msg("selfdriveState", 100, SimpleNamespace(enabled=True)),
    msg("carState", 700, SimpleNamespace(vEgo=10.0)),
    msg("selfdriveState", 700, SimpleNamespace(enabled=False)),
  ]
  model_names = {"orion": {"name": "Orion", "series": "City", "key": "orion"}}

  drive = utilities._analyze_route_messages(messages, route, model_names, is_metric=False)

  assert drive["date"].startswith("2026-06-17T21:53:00")
  assert drive["endDate"].startswith("2026-06-17T22:03:00")
  assert drive["duration"] == 600


def test_week_and_record_summaries_use_analyzed_drives():
  now = utilities.datetime(2026, 6, 16, 12, 0, 0)
  drives = [
    {"date": "2026-06-15T08:00:00", "distance": 10.0, "duration": 1200, "engagedSeconds": 900, "distractedMoments": 0, "unresponsiveMoments": 0},
    {"date": "2026-06-16T08:00:00", "distance": 4.0, "duration": 600, "engagedSeconds": 600, "distractedMoments": 1, "unresponsiveMoments": 0},
    {"date": "2026-06-08T08:00:00", "distance": 25.0, "duration": 1800, "engagedSeconds": 900, "distractedMoments": 0, "unresponsiveMoments": 0},
  ]

  week = utilities._build_week_summary(drives, now, is_metric=False)
  records = utilities._build_records(drives, is_metric=False)

  assert week["distance"] == 14.0
  assert week["drives"] == 2
  assert week["engagedPercent"] == 83
  assert records["longestDrive"]["value"] == "25.0"
  assert records["highestStreak"]["value"] == "2 days"
  assert records["longestUndistractedDrive"]["value"] == "0.5 hours"
  assert records["cleanDriveStreak"]["value"] == "3 drives"


def test_attention_records_use_distracted_for_undistracted_and_unresponsive_for_clean_streak():
  drives = [
    {"date": "2026-06-15T08:00:00", "distance": 10.0, "duration": 1200, "engagedSeconds": 900, "distractedMoments": 0, "unresponsiveMoments": 0},
    {"date": "2026-06-16T08:00:00", "distance": 4.0, "duration": 3600, "engagedSeconds": 600, "distractedMoments": 1, "unresponsiveMoments": 0},
    {"date": "2026-06-17T08:00:00", "distance": 6.0, "duration": 600, "engagedSeconds": 400, "distractedMoments": 0, "unresponsiveMoments": 1},
    {"date": "2026-06-18T08:00:00", "distance": 8.0, "duration": 900, "engagedSeconds": 800, "distractedMoments": 0, "unresponsiveMoments": 0},
  ]

  records = utilities._build_records(drives, is_metric=False)

  assert records["longestUndistractedDrive"]["value"] == "0.3 hours"
  assert records["cleanDriveStreak"]["value"] == "2 drives"


def test_route_sampling_bounds_analyzed_segments():
  route = {
    "name": "route-a",
    "segmentCount": 10,
    "segments": [{"num": idx, "path": Path(f"/tmp/segment-{idx}")} for idx in range(10)],
  }

  sampled = utilities._sample_route_info(route, limit=3)

  assert sampled["segmentCount"] == 10
  assert sampled["analysisSegmentCount"] == 3
  assert [segment["num"] for segment in sampled["segments"]] == [0, 4, 9]


def test_route_listing_prefers_segment_candidates_with_logs(tmp_path):
  hd_root = tmp_path / "realdata_HD"
  standard_root = tmp_path / "realdata"
  hd_segment = hd_root / "00000001--abcdef1234--0"
  standard_segment = standard_root / "00000001--abcdef1234--0"
  hd_segment.mkdir(parents=True)
  standard_segment.mkdir(parents=True)
  (standard_segment / "qlog.zst").write_bytes(b"")

  routes = utilities._list_dashboard_routes([hd_root, standard_root])

  assert routes[0]["segments"][0]["path"] == standard_segment


def test_route_listing_uses_all_segment_times_when_segment_zero_was_touched(tmp_path):
  route_start = utilities.datetime(2026, 7, 18, 7, 19, 0)
  route_name = "000011e3--6e01289631"
  for segment_num in range(2):
    segment = tmp_path / f"{route_name}--{segment_num}"
    segment.mkdir()
    segment_end = route_start.timestamp() + (segment_num + 1) * 60
    os.utime(segment, (segment_end, segment_end))

  touched_segment = tmp_path / f"{route_name}--0"
  touched_time = utilities.datetime(2026, 7, 20, 12, 8, 38).timestamp()
  os.utime(touched_segment, (touched_time, touched_time))

  routes = utilities._list_dashboard_routes([tmp_path])

  assert routes[0]["startedAt"] == route_start
  start, end = utilities._route_time_range(routes[0], 180)
  assert start == "2026-07-18T07:19:00"
  assert end == "2026-07-18T07:22:00"


def test_top_models_are_ranked_from_persisted_usage_not_favorites():
  params = FakeParams({
    "AvailableModels": "orion,vega,atlas,nova",
    "AvailableModelNames": "Orion,Vega,Atlas,Nova",
    "AvailableModelSeries": "City,Highway,Experimental,Custom",
    "UserFavorites": "orion",
    "CommunityFavorites": "vega",
  })
  persistent = {
    "modelUsage": {
      "orion": {"name": "Orion", "drives": 3},
      "vega": {"name": "Vega", "drives": 1},
      "atlas": {"name": "Atlas", "drives": 9},
      "nova": {"name": "Nova", "drives": 4},
    },
  }

  favorites = utilities._build_favorite_models(params, persistent)

  assert [model["name"] for model in favorites] == ["Atlas", "Nova", "Orion"]
  assert len(favorites) == 3
  assert favorites[0]["userFavorite"] is False
  assert favorites[0]["drives"] == 9
  assert favorites[2]["userFavorite"] is True


def test_persistent_personal_records_and_model_usage_survive_empty_routes():
  params = FakeParams({"AvailableModels": "orion", "AvailableModelNames": "Orion", "CommunityFavorites": "orion"})
  drives = [
    {
      "name": "route-1",
      "date": "2026-06-15T08:00:00",
      "distanceMeters": 10000.0,
      "duration": 1200,
      "engagedSeconds": 900.0,
      "model": "Orion",
      "distractedMoments": 0,
      "unresponsiveMoments": 0,
      "routeModifiedAt": 100,
      "analysisComplete": True,
    },
    {
      "name": "route-2",
      "date": "2026-06-16T08:00:00",
      "distanceMeters": 5000.0,
      "duration": 600,
      "engagedSeconds": 600.0,
      "model": "Orion",
      "distractedMoments": 1,
      "unresponsiveMoments": 0,
      "routeModifiedAt": 100,
      "analysisComplete": True,
    },
    {
      "name": "route-3",
      "date": "2026-06-17T08:00:00",
      "distanceMeters": 20000.0,
      "duration": 1800,
      "engagedSeconds": 900.0,
      "model": "Orion",
      "distractedMoments": 0,
      "unresponsiveMoments": 0,
      "routeModifiedAt": 100,
      "analysisComplete": True,
    },
  ]

  persistent = utilities._update_dashboard_persistent_stats(params, drives, wall_now=1000)
  records = utilities._display_personal_records(persistent, is_metric=False)
  favorites = utilities._build_favorite_models(params, persistent)

  assert records["longestDrive"]["value"] == "12.4"
  assert records["mostEngagedDay"]["value"] == "100%"
  assert records["bestWeek"]["value"] == "21.7"
  assert records["highestStreak"]["value"] == "3 days"
  assert records["longestUndistractedDrive"]["value"] == "0.5 hours"
  assert records["cleanDriveStreak"]["value"] == "3 drives"
  assert favorites[0]["drives"] == 3

  restored = utilities._update_dashboard_persistent_stats(params, [], wall_now=2000)
  restored_records = utilities._display_personal_records(restored, is_metric=False)

  assert restored_records["longestDrive"]["value"] == "12.4"
  assert restored_records["mostEngagedDay"]["value"] == "100%"
  assert restored_records["bestWeek"]["value"] == "21.7"
  assert restored_records["highestStreak"]["value"] == "3 days"
  assert restored_records["longestUndistractedDrive"]["value"] == "0.5 hours"
  assert restored_records["cleanDriveStreak"]["value"] == "3 drives"


def test_model_usage_ignores_pending_route_shells():
  params = FakeParams({"AvailableModels": "orion,vega", "AvailableModelNames": "Orion,Vega"})
  drives = [
    {
      "name": "route-1",
      "date": "2026-06-15T08:00:00",
      "distanceMeters": 10000.0,
      "duration": 1200,
      "engagedSeconds": 900.0,
      "model": "Orion",
      "routeModifiedAt": 100,
      "analysisComplete": True,
    },
    {
      "name": "route-2",
      "date": "2026-06-16T08:00:00",
      "distanceMeters": 0.0,
      "duration": 600,
      "engagedSeconds": 0.0,
      "model": "Vega",
      "routeModifiedAt": 100,
      "analysisComplete": False,
      "attentionKnown": False,
    },
  ]

  persistent = utilities._update_dashboard_persistent_stats(params, drives, wall_now=1000)
  favorites = utilities._build_favorite_models(params, persistent)

  assert [model["name"] for model in favorites] == ["Orion"]
  assert favorites[0]["drives"] == 1


def test_ignored_drive_stays_recent_but_is_removed_from_local_stats(monkeypatch):
  utilities._invalidate_dashboard_cache()
  first_route = "00000001--abcdef0001"
  shared_route = "00000002--abcdef0002"
  third_route = "00000003--abcdef0003"
  params = FakeParams({
    "AvailableModels": "orion",
    "AvailableModelNames": "Orion",
  })
  drives = [
    {
      "name": first_route,
      "date": "2026-06-15T08:00:00",
      "endDate": "2026-06-15T08:20:00",
      "distanceMeters": 10000.0,
      "duration": 1200,
      "engagedSeconds": 900.0,
      "model": "Orion",
      "distractedMoments": 0,
      "unresponsiveMoments": 0,
      "routeModifiedAt": 100,
      "attentionKnown": True,
      "analysisComplete": True,
    },
    {
      "name": shared_route,
      "date": "2026-06-16T08:00:00",
      "endDate": "2026-06-16T09:00:00",
      "distanceMeters": 50000.0,
      "duration": 3600,
      "engagedSeconds": 100.0,
      "model": "Orion",
      "distractedMoments": 4,
      "unresponsiveMoments": 1,
      "routeModifiedAt": 100,
      "attentionKnown": True,
      "analysisComplete": True,
    },
    {
      "name": third_route,
      "date": "2026-06-17T08:00:00",
      "endDate": "2026-06-17T08:15:00",
      "distanceMeters": 5000.0,
      "duration": 900,
      "engagedSeconds": 800.0,
      "model": "Orion",
      "distractedMoments": 0,
      "unresponsiveMoments": 0,
      "routeModifiedAt": 100,
      "attentionKnown": True,
      "analysisComplete": True,
    },
  ]
  utilities._update_dashboard_persistent_stats(params, drives, wall_now=1000)

  ignored = utilities.ignore_dashboard_routes(params, [shared_route])

  assert ignored == [shared_route]
  monkeypatch.setattr(utilities, "_list_dashboard_routes", lambda paths: [])
  monkeypatch.setattr(utilities, "_start_dashboard_background_analysis", lambda *args: False)
  monkeypatch.setattr(utilities, "_build_storage_summary", lambda paths: {
    "freeBytes": 0,
    "usedBytes": 0,
    "totalBytes": 0,
    "usedPercent": 0,
    "segmentCounts": {},
  })

  dashboard = utilities.get_dashboard_stats([], params, now=utilities.datetime(2026, 6, 18, 12, 0, 0))
  recent_by_name = {drive["name"]: drive for drive in dashboard["recentDrives"]}

  assert recent_by_name[shared_route]["ignored"] is True
  assert recent_by_name[first_route]["ignored"] is False
  assert dashboard["week"]["drives"] == 2
  assert dashboard["week"]["distance"] == 9.3
  assert dashboard["records"]["longestDrive"]["value"] == "6.2"
  assert dashboard["records"]["cleanDriveStreak"]["value"] == "2 drives"
  assert dashboard["favoriteModels"][0]["drives"] == 2

  utilities.include_dashboard_routes(params, [shared_route])
  restored = utilities.get_dashboard_stats([], params, now=utilities.datetime(2026, 6, 18, 12, 0, 0))
  restored_by_name = {drive["name"]: drive for drive in restored["recentDrives"]}
  assert restored_by_name[shared_route]["ignored"] is False
  assert restored["week"]["drives"] == 3
  assert restored["records"]["longestDrive"]["value"] == "31.1"
  assert restored["favoriteModels"][0]["drives"] == 3
  utilities._invalidate_dashboard_cache()


def test_ignored_route_is_not_queued_for_analysis():
  ignored_route = "00000001--abcdef0001"
  active_route = "00000002--abcdef0002"
  route_infos = [
    {"name": ignored_route, "modifiedAt": 100, "segmentCount": 1},
    {"name": active_route, "modifiedAt": 100, "segmentCount": 1},
  ]
  stats = {
    "routes": {},
    "ignoredRoutes": [ignored_route],
  }

  assert utilities._analysis_candidates(route_infos, stats) == [route_infos[1]]


def test_ignore_dashboard_routes_rejects_arbitrary_names():
  params = FakeParams()

  try:
    utilities.ignore_dashboard_routes(params, ["../../data/params"])
  except ValueError as exception:
    assert "No valid dashboard routes" in str(exception)
  else:
    raise AssertionError("invalid route name was accepted")


def test_cpu_temp_reader_uses_hardware_cpu_values(monkeypatch):
  hardware_module = _simple_module(
    "openpilot.system.hardware",
    HARDWARE=SimpleNamespace(
      get_thermal_config=lambda: SimpleNamespace(
        get_msg=lambda: {"cpuTempC": [55.1, 56.6], "memoryTempC": 75.0}
      )
    ),
  )
  monkeypatch.setitem(sys.modules, "openpilot.system.hardware", hardware_module)

  assert utilities._read_cpu_temp_c() == 57


def test_cpu_temp_reader_ignores_non_cpu_thermal_zones(tmp_path):
  cpu_zone = tmp_path / "thermal_zone0"
  cpu_zone.mkdir()
  (cpu_zone / "type").write_text("cpu0-silver-usr", encoding="utf-8")
  (cpu_zone / "temp").write_text("61000", encoding="utf-8")

  pmic_zone = tmp_path / "thermal_zone1"
  pmic_zone.mkdir()
  (pmic_zone / "type").write_text("pm8998_tz", encoding="utf-8")
  (pmic_zone / "temp").write_text("75000", encoding="utf-8")

  assert utilities._read_cpu_temp_c(tmp_path) == 61


def test_network_name_uses_wifi_ssid(monkeypatch):
  monkeypatch.setattr(utilities, "HARDWARE", SimpleNamespace(get_network_type=lambda: 1))
  monkeypatch.setattr(utilities, "_read_active_wifi_ssid", lambda: "Garage Wi-Fi")
  utilities._NETWORK_STATUS_CACHE.update({"updated_at": 0.0, "value": None})

  assert utilities.get_current_network_name() == "Garage Wi-Fi"


def test_wifi_ssid_reader_uses_active_nmcli_row(monkeypatch):
  result = SimpleNamespace(
    returncode=0,
    stdout=" :Nearby Network\n*:Garage:Main Wi-Fi\n",
  )
  monkeypatch.setattr(utilities.subprocess, "run", lambda *args, **kwargs: result)

  assert utilities._read_active_wifi_ssid() == "Garage:Main Wi-Fi"


def test_network_name_labels_cellular_generations(monkeypatch):
  network_type = {"value": 4}
  monkeypatch.setattr(utilities, "HARDWARE", SimpleNamespace(get_network_type=lambda: network_type["value"]))
  monkeypatch.setattr(utilities, "_read_active_wifi_ssid", lambda: None)

  utilities._NETWORK_STATUS_CACHE.update({"updated_at": 0.0, "value": None})
  assert utilities.get_current_network_name() == "Cellular (LTE)"

  network_type["value"] = 5
  utilities._NETWORK_STATUS_CACHE.update({"updated_at": 0.0, "value": None})
  assert utilities.get_current_network_name() == "Cellular (5G)"


def test_network_name_reports_no_wireless_connectivity(monkeypatch):
  monkeypatch.setattr(utilities, "HARDWARE", SimpleNamespace(get_network_type=lambda: 0))
  monkeypatch.setattr(utilities, "_read_active_wifi_ssid", lambda: None)
  utilities._NETWORK_STATUS_CACHE.update({"updated_at": 0.0, "value": None})

  assert utilities.get_current_network_name() == "No wireless connectivity"


def test_device_summary_includes_network_name(monkeypatch):
  monkeypatch.setattr(utilities, "_read_uptime_seconds", lambda: 120)
  monkeypatch.setattr(utilities, "_read_cpu_temp_c", lambda: 55)
  monkeypatch.setattr(utilities, "get_current_lan_ip", lambda: "192.168.1.10")
  monkeypatch.setattr(utilities, "get_current_network_name", lambda: "Home Network")

  summary = utilities._build_device_summary(FakeParams({"IsOnroad": False}))

  assert summary["networkName"] == "Home Network"
  assert summary["lanIp"] == "192.168.1.10"


def test_persistent_loader_accepts_decoded_param_dict():
  params = FakeParams({
    utilities.DASHBOARD_PERSISTENT_STATS_PARAM: {
      "routes": {
        "route-1": {
          "date": "2026-06-15T08:00:00",
          "distanceMeters": 1000,
          "duration": 60,
          "model": "Orion",
          "attentionKnown": False,
        },
      },
    },
  })

  stats = utilities._load_dashboard_persistent_stats(params)

  assert stats["routes"]["route-1"]["distanceMeters"] == 1000
  assert stats["routes"]["route-1"]["attentionKnown"] is False


def test_dashboard_persistent_stats_fallback_to_file_when_param_put_fails(tmp_path, monkeypatch):
  monkeypatch.setattr(utilities, "DASHBOARD_PARAMS_DIR", tmp_path)
  params = FailingPutParams()
  drive = {
    "name": "route-1",
    "date": "2026-06-15T08:00:00",
    "distanceMeters": 1000.0,
    "duration": 60,
    "engagedSeconds": 30.0,
    "model": "Orion",
    "routeModifiedAt": 100,
    "attentionKnown": True,
    "analysisComplete": True,
  }

  utilities._update_dashboard_persistent_stats(params, [drive], wall_now=1000)
  stats = utilities._load_dashboard_persistent_stats(params)

  assert (tmp_path / utilities.DASHBOARD_PERSISTENT_STATS_PARAM).is_file()
  assert stats["routes"]["route-1"]["distanceMeters"] == 1000
  assert stats["routes"]["route-1"]["analysisComplete"] is True


def test_lightweight_routes_surface_recent_drives_without_log_analysis(monkeypatch):
  utilities._invalidate_dashboard_cache()
  now = utilities.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
  week_start = utilities._start_of_week(now)
  route_infos = [
    {
      "name": "route-new",
      "segments": [],
      "segmentCount": 3,
      "startedAt": week_start + utilities.timedelta(days=1, hours=9),
      "modifiedAt": (week_start + utilities.timedelta(days=1, hours=9, minutes=3)).timestamp(),
    },
    {
      "name": "route-old",
      "segments": [],
      "segmentCount": 2,
      "startedAt": week_start + utilities.timedelta(hours=9),
      "modifiedAt": (week_start + utilities.timedelta(hours=9, minutes=2)).timestamp(),
    },
  ]
  params = FakeParams({
    "IsMetric": False,
    "Model": "orion",
    "AvailableModels": "orion",
    "AvailableModelNames": "Orion",
    "AvailableModelSeries": "City",
  })
  monkeypatch.setattr(utilities, "_list_dashboard_routes", lambda paths: route_infos)
  monkeypatch.setattr(utilities, "_start_dashboard_background_analysis", lambda *args: None)
  monkeypatch.setattr(utilities, "_build_storage_summary", lambda paths: {"freeBytes": 0, "usedBytes": 0, "totalBytes": 0, "usedPercent": 0, "segmentCounts": {}})

  dashboard = utilities.get_dashboard_stats(["/tmp/missing"], params, now=now)

  assert [drive["name"] for drive in dashboard["recentDrives"]] == ["route-new", "route-old"]
  assert dashboard["lastDrive"]["model"] == "Unknown model"
  assert dashboard["week"]["drives"] == 2
  assert dashboard["favoriteModels"] == []
  assert dashboard["analysis"]["pendingRoutes"] == 2
  assert dashboard["analysis"]["batchSize"] == 2
  utilities._invalidate_dashboard_cache()


def test_recent_drives_coalesce_exact_duplicate_time_ranges_only():
  drives = [
    {
      "name": "route-a",
      "date": "2026-06-18T09:24:10",
      "endDate": "2026-06-18T09:34:10",
      "distanceMeters": 1609.344,
      "distance": 1.0,
      "duration": 600,
      "engagedSeconds": 300.0,
      "model": "Orion",
      "segmentCount": 10,
      "distractedMoments": 1,
      "unresponsiveMoments": 0,
      "routeModifiedAt": 100,
      "attentionKnown": True,
      "analysisComplete": True,
    },
    {
      "name": "route-b",
      "date": "2026-06-18T09:24:10",
      "endDate": "2026-06-18T09:34:10",
      "distanceMeters": 3218.688,
      "distance": 2.0,
      "duration": 300,
      "engagedSeconds": 300.0,
      "model": "Orion",
      "segmentCount": 5,
      "distractedMoments": 0,
      "unresponsiveMoments": 1,
      "routeModifiedAt": 110,
      "attentionKnown": True,
      "analysisComplete": True,
    },
    {
      "name": "route-c",
      "date": "2026-06-18T09:24:30",
      "endDate": "2026-06-18T09:27:30",
      "distanceMeters": 804.672,
      "distance": 0.5,
      "duration": 120,
      "engagedSeconds": 0.0,
      "model": "Orion",
      "segmentCount": 2,
      "distractedMoments": 0,
      "unresponsiveMoments": 0,
      "routeModifiedAt": 120,
      "attentionKnown": True,
      "analysisComplete": True,
    },
  ]

  coalesced = utilities._coalesce_display_drives(drives, is_metric=False)

  assert len(coalesced) == 2
  duplicate_group = next(drive for drive in coalesced if drive["date"] == "2026-06-18T09:24:10")
  short_drive = next(drive for drive in coalesced if drive["date"] == "2026-06-18T09:24:30")
  assert duplicate_group["distance"] == 3.0
  assert duplicate_group["duration"] == 900
  assert duplicate_group["engagedPercent"] == 67
  assert duplicate_group["distractedMoments"] == 1
  assert duplicate_group["unresponsiveMoments"] == 1
  assert short_drive["distance"] == 0.5


def test_completed_routes_with_old_analysis_version_are_refreshed_once():
  route = {"name": "route-1", "modifiedAt": 100, "segmentCount": 1}
  stale_stats = {
    "routes": {
      "route-1": {
        "modifiedAt": 100,
        "attentionKnown": True,
        "analysisComplete": True,
        "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION - 1,
      },
    },
  }
  current_stats = {
    "routes": {
      "route-1": {
        "modifiedAt": 100,
        "attentionKnown": True,
        "analysisComplete": True,
        "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION,
      },
    },
  }

  assert utilities._analysis_candidates([route], stale_stats) == [route]
  assert utilities._analysis_candidates([route], current_stats) == []


def test_shell_update_preserves_old_analysis_version_for_reparse():
  params = FakeParams({
    utilities.DASHBOARD_PERSISTENT_STATS_PARAM: {
      "routes": {
        "route-1": {
          "date": "2026-06-18T09:24:00",
          "endDate": "2026-06-18T09:34:00",
          "distanceMeters": 1000.0,
          "duration": 600,
          "engagedSeconds": 400.0,
          "model": "Orion",
          "modifiedAt": 100,
          "attentionKnown": True,
          "analysisComplete": True,
          "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION - 1,
        },
      },
    },
  })
  shell_drive = {
    "name": "route-1",
    "date": "2026-06-18T09:23:00",
    "endDate": "2026-06-18T09:34:00",
    "distanceMeters": 0.0,
    "duration": 660,
    "engagedSeconds": 0.0,
    "model": "Vega",
    "routeModifiedAt": 100,
    "attentionKnown": False,
    "analysisComplete": False,
    "analysisVersion": 0,
  }

  stats = utilities._update_dashboard_persistent_stats(params, [shell_drive], wall_now=1000)

  assert stats["routes"]["route-1"]["date"] == "2026-06-18T09:24:00"
  assert stats["routes"]["route-1"]["model"] == "Orion"
  assert stats["routes"]["route-1"]["analysisVersion"] == utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION - 1
  assert utilities._analysis_candidates([{"name": "route-1", "modifiedAt": 100}], stats)


def test_route_shell_does_not_assign_the_current_model():
  route_info = {
    "name": "route-1",
    "segments": [],
    "segmentCount": 1,
    "startedAt": utilities.datetime(2026, 6, 18, 9, 24, 0),
    "modifiedAt": utilities.datetime(2026, 6, 18, 9, 25, 0).timestamp(),
  }
  params = FakeParams({"DrivingModelName": "Vega"})

  shell_drive = utilities._route_shell_drive(route_info, params, {}, is_metric=False)

  assert shell_drive["model"] == "Unknown model"


def test_reanalysis_replaces_the_shell_model_and_recalculates_usage():
  params = FakeParams({
    utilities.DASHBOARD_PERSISTENT_STATS_PARAM: {
      "routes": {
        "route-1": {
          "date": "2026-07-17T16:58:00",
          "endDate": "2026-07-17T17:51:00",
          "distanceMeters": 57000.0,
          "duration": 3180,
          "engagedSeconds": 1800.0,
          "model": "Pop Model V2",
          "modelKey": "Pop Model V2",
          "modifiedAt": 100,
          "attentionKnown": True,
          "analysisComplete": True,
          "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION - 1,
        },
      },
    },
  })
  analyzed_drive = {
    "name": "route-1",
    "date": "2026-07-17T16:58:00",
    "endDate": "2026-07-17T17:51:00",
    "distanceMeters": 57000.0,
    "duration": 3180,
    "engagedSeconds": 1800.0,
    "model": "Michael RL",
    "routeModifiedAt": 100,
    "attentionKnown": True,
    "analysisComplete": True,
    "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION,
  }

  stats = utilities._update_dashboard_persistent_stats(params, [analyzed_drive], wall_now=1000)

  assert stats["routes"]["route-1"]["model"] == "Michael RL"
  assert list(stats["modelUsage"]) == ["michael-rl"]
  assert stats["modelUsage"]["michael-rl"]["drives"] == 1


def test_week_summary_ignores_stale_premigration_route_rows(monkeypatch):
  utilities._invalidate_dashboard_cache()
  route_infos = [
    {
      "name": "route-stale",
      "segments": [],
      "segmentCount": 1,
      "startedAt": utilities.datetime(2026, 6, 15, 8, 0, 0),
      "modifiedAt": 100,
    },
    {
      "name": "route-current",
      "segments": [],
      "segmentCount": 1,
      "startedAt": utilities.datetime(2026, 6, 17, 8, 0, 0),
      "modifiedAt": 200,
    },
  ]
  params = FakeParams({
    utilities.DASHBOARD_PERSISTENT_STATS_PARAM: {
      "routes": {
        "route-stale": {
          "date": "2026-06-15T08:00:00",
          "endDate": "2026-06-15T08:20:00",
          "distanceMeters": 160934.4,
          "duration": 1200,
          "engagedSeconds": 600.0,
          "model": "Orion",
          "modifiedAt": 100,
          "attentionKnown": True,
          "analysisComplete": True,
          "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION - 1,
        },
        "route-current": {
          "date": "2026-06-17T08:00:00",
          "endDate": "2026-06-17T08:20:00",
          "distanceMeters": 32186.88,
          "duration": 1200,
          "engagedSeconds": 900.0,
          "model": "Orion",
          "modifiedAt": 200,
          "attentionKnown": True,
          "analysisComplete": True,
          "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION,
        },
      },
    },
  })
  monkeypatch.setattr(utilities, "_list_dashboard_routes", lambda paths: route_infos)
  monkeypatch.setattr(utilities, "_start_dashboard_background_analysis", lambda *args: False)
  monkeypatch.setattr(utilities, "_build_storage_summary", lambda paths: {"freeBytes": 0, "usedBytes": 0, "totalBytes": 0, "usedPercent": 0, "segmentCounts": {}})

  dashboard = utilities.get_dashboard_stats(["/tmp/missing"], params, now=utilities.datetime(2026, 6, 18, 12, 0, 0))

  assert dashboard["week"]["distance"] == 20.0
  assert dashboard["week"]["dailyDistance"][0]["distance"] == 0.0
  assert dashboard["week"]["dailyDistance"][2]["distance"] == 20.0
  assert dashboard["analysis"]["pendingRoutes"] == 1
  utilities._invalidate_dashboard_cache()


def test_week_summary_keeps_persisted_rows_when_raw_route_is_gone(monkeypatch):
  utilities._invalidate_dashboard_cache()
  params = FakeParams({
    utilities.DASHBOARD_PERSISTENT_STATS_PARAM: {
      "routes": {
        "route-pruned": {
          "date": "2026-06-15T08:00:00",
          "endDate": "2026-06-15T08:20:00",
          "distanceMeters": 16093.44,
          "duration": 1200,
          "engagedSeconds": 600.0,
          "model": "Orion",
          "modifiedAt": 100,
          "attentionKnown": True,
          "analysisComplete": True,
          "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION - 1,
        },
      },
    },
  })
  monkeypatch.setattr(utilities, "_list_dashboard_routes", lambda paths: [])
  monkeypatch.setattr(utilities, "_start_dashboard_background_analysis", lambda *args: False)
  monkeypatch.setattr(utilities, "_build_storage_summary", lambda paths: {"freeBytes": 0, "usedBytes": 0, "totalBytes": 0, "usedPercent": 0, "segmentCounts": {}})

  dashboard = utilities.get_dashboard_stats(["/tmp/missing"], params, now=utilities.datetime(2026, 6, 18, 12, 0, 0))

  assert dashboard["week"]["distance"] == 10.0
  assert dashboard["week"]["dailyDistance"][0]["distance"] == 10.0
  assert dashboard["analysis"]["pendingRoutes"] == 0
  utilities._invalidate_dashboard_cache()


def test_week_summary_resets_at_monday_midnight():
  drives = [
    {"date": "2026-06-21T23:59:00", "distance": 30.0, "duration": 1800, "engagedSeconds": 900},
    {"date": "2026-06-22T00:00:00", "distance": 4.0, "duration": 600, "engagedSeconds": 300},
  ]

  week = utilities._build_week_summary(drives, utilities.datetime(2026, 6, 22, 0, 1, 0), is_metric=False)

  assert week["distance"] == 4.0
  assert week["drives"] == 1
  assert week["dailyDistance"][0]["distance"] == 4.0


def test_unknown_attention_rows_do_not_reset_persisted_clean_records():
  params = FakeParams()
  known_drive = {
    "name": "route-1",
    "date": "2026-06-15T08:00:00",
    "distanceMeters": 10000.0,
    "duration": 3600,
    "engagedSeconds": 3000.0,
    "model": "Orion",
    "distractedMoments": 0,
    "unresponsiveMoments": 0,
    "routeModifiedAt": 100,
    "attentionKnown": True,
  }
  shell_drive = {
    "name": "route-2",
    "date": "2026-06-16T08:00:00",
    "distanceMeters": 0.0,
    "duration": 120,
    "engagedSeconds": 0.0,
    "model": "Orion",
    "distractedMoments": 0,
    "unresponsiveMoments": 0,
    "routeModifiedAt": 100,
    "attentionKnown": False,
  }

  utilities._update_dashboard_persistent_stats(params, [known_drive], wall_now=1000)
  stats = utilities._update_dashboard_persistent_stats(params, [shell_drive], wall_now=1000)
  records = utilities._display_personal_records(stats, is_metric=False)

  assert records["longestUndistractedDrive"]["value"] == "1.0 hour"
  assert records["cleanDriveStreak"]["value"] == "1 drive"


def test_lightweight_route_update_preserves_parsed_duration():
  params = FakeParams()
  parsed_drive = {
    "name": "route-1",
    "date": "2026-06-15T08:00:00",
    "distanceMeters": 10000.0,
    "duration": 58,
    "engagedSeconds": 30.0,
    "model": "Orion",
    "routeModifiedAt": 100,
    "attentionKnown": True,
    "analysisComplete": True,
  }
  shell_drive = {
    "name": "route-1",
    "date": "2026-06-15T08:00:00",
    "distanceMeters": 0.0,
    "duration": 60,
    "engagedSeconds": 0.0,
    "model": "Orion",
    "routeModifiedAt": 100,
    "attentionKnown": False,
    "analysisComplete": False,
  }

  utilities._update_dashboard_persistent_stats(params, [parsed_drive], wall_now=1000)
  stats = utilities._update_dashboard_persistent_stats(params, [shell_drive], wall_now=1000)

  assert stats["routes"]["route-1"]["duration"] == 58
  assert stats["routes"]["route-1"]["analysisComplete"] is True


def test_log_wall_time_overrides_bad_filesystem_route_time():
  bad_modified = utilities.datetime(2025, 7, 2, 12, 0, 0).timestamp()
  wall_start = utilities.datetime(2026, 6, 20, 2, 55, 15).timestamp()
  route_info = {
    "name": "00000764--badtime--0",
    "segments": [],
    "segmentCount": 1,
    "analysisSegmentCount": 1,
    "modifiedAt": bad_modified,
  }
  messages = [
    msg("initData", 10.0, SimpleNamespace(
      params={"DrivingModelName": b"Pop Model V2"},
      wallTimeNanos=int(wall_start * 1e9),
    )),
    msg("carState", 11.0, SimpleNamespace(vEgo=10.0)),
    msg("carState", 13.0, SimpleNamespace(vEgo=10.0)),
  ]

  drive = utilities._analyze_route_messages(messages, route_info, {}, is_metric=False)

  assert drive["date"].startswith("2026-06-20T02:55:15")
  assert drive["timeSource"] == utilities.DASHBOARD_TIME_SOURCE_LOG
  assert drive["model"] == "Pop Model V2"


def test_invalid_filesystem_route_time_is_not_persisted():
  params = FakeParams()
  route_info = {
    "name": "00000764--badtime--0",
    "segments": [],
    "segmentCount": 1,
    "startedAt": utilities.datetime(2025, 7, 2, 12, 0, 0),
    "modifiedAt": utilities.datetime(2025, 7, 2, 12, 1, 0).timestamp(),
  }

  shell_drive = utilities._route_shell_drive(route_info, params, {}, is_metric=False)
  stats = utilities._update_dashboard_persistent_stats(params, [shell_drive], wall_now=utilities.datetime(2026, 6, 20, 12, 0, 0).timestamp())

  assert shell_drive["date"] == ""
  assert stats["routes"] == {}


def test_invalid_persisted_record_dates_are_not_kept():
  current = {
    "longestDrive": {"distanceMeters": 0.0, "date": ""},
    "mostEngagedDay": {"percent": 0, "date": ""},
    "bestWeek": {"distanceMeters": 0.0, "weekDate": ""},
    "highestStreak": {"days": 0},
    "longestUndistractedDrive": {"duration": 3600, "date": "2026-06-19T09:00:00"},
    "cleanDriveStreak": {"drives": 1, "startDate": "2026-06-19T09:00:00", "endDate": "2026-06-19T09:00:00"},
  }
  previous = {
    "longestUndistractedDrive": {"duration": 7200, "date": "2025-07-02T09:00:00"},
    "cleanDriveStreak": {"drives": 4, "startDate": "2025-07-02T09:00:00", "endDate": "2025-07-02T12:00:00"},
  }

  merged = utilities._merge_personal_records(current, previous)

  assert merged["longestUndistractedDrive"] == current["longestUndistractedDrive"]
  assert merged["cleanDriveStreak"] == current["cleanDriveStreak"]


def test_invalid_persisted_route_dates_are_removed():
  params = FakeParams({
    utilities.DASHBOARD_PERSISTENT_STATS_PARAM: {
      "routes": {
        "bad-route": {
          "date": "2025-07-02T09:00:00",
          "distanceMeters": 1000.0,
          "duration": 600,
          "engagedSeconds": 600.0,
          "model": "Orion",
          "modifiedAt": 100,
          "attentionKnown": True,
          "analysisComplete": True,
          "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION,
        },
        "good-route": {
          "date": "2026-06-19T09:00:00",
          "distanceMeters": 1000.0,
          "duration": 600,
          "engagedSeconds": 600.0,
          "model": "Orion",
          "modifiedAt": 200,
          "attentionKnown": True,
          "analysisComplete": True,
          "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION,
        },
      },
    },
  })

  stats = utilities._load_dashboard_persistent_stats(params)

  assert "bad-route" not in stats["routes"]
  assert "good-route" in stats["routes"]


def test_invalid_filesystem_time_requests_reanalysis():
  route = {"name": "route-1", "modifiedAt": 100, "segmentCount": 1}
  stats = {
    "routes": {
      "route-1": {
        "date": "2025-07-02T09:00:00",
        "modifiedAt": 100,
        "timeSource": utilities.DASHBOARD_TIME_SOURCE_FILESYSTEM,
        "attentionKnown": True,
        "analysisComplete": True,
        "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION,
      },
    },
  }

  assert utilities._analysis_candidates([route], stats) == [route]


def test_corrected_filesystem_time_replaces_touched_persisted_time_without_losing_stats():
  params = FakeParams({
    utilities.DASHBOARD_PERSISTENT_STATS_PARAM: {
      "routes": {
        "000011e5--92dc4759b2": {
          "date": "2026-07-20T11:33:49",
          "endDate": "2026-07-20T12:08:38",
          "distanceMeters": 45919.2,
          "duration": 2089,
          "engagedSeconds": 1200.0,
          "model": "Pop Model V2",
          "modifiedAt": 100.0,
          "timeSource": utilities.DASHBOARD_TIME_SOURCE_FILESYSTEM,
          "attentionKnown": True,
          "analysisComplete": True,
          "analysisVersion": utilities.DASHBOARD_ROUTE_ANALYSIS_VERSION,
        },
      },
    },
  })
  corrected_shell = {
    "name": "000011e5--92dc4759b2",
    "date": "2026-07-19T04:55:02",
    "endDate": "2026-07-19T05:30:02",
    "distanceMeters": 0.0,
    "duration": 2100,
    "engagedSeconds": 0.0,
    "model": "Unknown model",
    "segmentCount": 35,
    "routeModifiedAt": 100.0,
    "timeSource": utilities.DASHBOARD_TIME_SOURCE_FILESYSTEM,
    "attentionKnown": False,
    "analysisComplete": False,
    "analysisVersion": 0,
  }

  stats = utilities._update_dashboard_persistent_stats(params, [corrected_shell], wall_now=1000.0)
  corrected = stats["routes"]["000011e5--92dc4759b2"]

  assert corrected["date"] == "2026-07-19T04:55:02"
  assert corrected["endDate"] == "2026-07-19T05:29:51"
  assert corrected["distanceMeters"] == 45919.2
  assert corrected["duration"] == 2089
  assert corrected["model"] == "Pop Model V2"


def test_github_urls_accept_owner_repo_origin():
  assert utilities.get_github_changelog_url("owner/repo", "main") == "https://github.com/owner/repo/commits/main/"
  assert utilities.get_github_changelog_url("github.com/owner/repo", "main") == "https://github.com/owner/repo/commits/main/"
  assert utilities.get_github_commit_url("owner/repo", "abcdef") == "https://github.com/owner/repo/commit/abcdef"


def _load_server_module():
  _SERVER_MODULE_SNAPSHOTS.append(dict(sys.modules))
  _install_server_import_stubs()
  spec = importlib.util.spec_from_file_location("dashboard_server", MODULE_DIR / "the_galaxy.py")
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def test_troubleshoot_steer_delay_normalizes_vehicle_delay_for_display():
  server = _load_server_module()

  assert server._normalize_troubleshoot_current_display_value("SteerDelay", 0.1, 0.3) == 0.3
  assert server._normalize_troubleshoot_current_display_value("SteerDelay", 0.3, 0.3) == 0.3


def test_troubleshoot_steer_delay_preserves_real_custom_values():
  server = _load_server_module()

  assert server._normalize_troubleshoot_current_display_value("SteerDelay", 0.2, 0.3) == 0.2
  assert server._normalize_troubleshoot_current_display_value("LongitudinalActuatorDelay", 0.1, 0.3) == 0.1


def test_stats_endpoint_keeps_existing_keys_and_adds_dashboard(monkeypatch):
  server = _load_server_module()
  assert server._import_galaxy_web_symbols()

  app = server.Flask(
    "dashboard_test",
    template_folder=str(MODULE_DIR / "templates"),
    static_folder=str(MODULE_DIR / "assets"),
  )
  server.setup(app)

  fake_metadata = SimpleNamespace(
    channel="test-branch",
    release_channel=False,
    tested_channel=False,
    openpilot=SimpleNamespace(
      git_commit="abcdef123456",
      git_normalized_origin="owner/repo",
      git_commit_date="'1700000000 2023-11-14 00:00:00 -0000'",
    ),
  )
  monkeypatch.setattr(server, "get_build_metadata", lambda: fake_metadata)
  monkeypatch.setattr(server, "FOOTAGE_PATHS", [])
  monkeypatch.setattr(server, "params", FakeParams({"UpdaterFetchAvailable": False, "IsMetric": False}))
  monkeypatch.setattr(server.utilities, "get_disk_usage", lambda: [{"free": "1 GB", "size": "2 GB", "used": "1 GB", "usedPercentage": "50.00%"}])
  monkeypatch.setattr(server.utilities, "get_drive_stats", lambda: {"all": {"drives": 0, "distance": 0, "hours": 0, "unit": "miles"}})
  monkeypatch.setattr(server.utilities, "get_dashboard_stats", lambda footage_paths, params_obj: {"lastDrive": {}, "recentDrives": []})
  ignored_calls = []
  included_calls = []
  monkeypatch.setattr(server.utilities, "ignore_dashboard_routes", lambda params_obj, route_names: ignored_calls.extend(route_names) or route_names)
  monkeypatch.setattr(server.utilities, "include_dashboard_routes", lambda params_obj, route_names: included_calls.extend(route_names) or route_names)

  client = app.test_client()
  response = client.get("/api/stats")
  payload = response.get_json()

  assert response.status_code == 200
  assert "diskUsage" in payload
  assert "driveStats" in payload
  assert "softwareInfo" in payload
  assert payload["softwareInfo"]["buildEnvironment"] == "Experimental"
  assert payload["dashboard"]["recentDrives"] == []

  route_name = "00000001--abcdef0001"
  ignore_response = client.post("/api/stats/ignore_drive", json={"routeNames": [route_name]})
  include_response = client.post("/api/stats/include_drive", json={"routeNames": [route_name]})

  assert ignore_response.status_code == 200
  assert include_response.status_code == 200
  assert ignored_calls == [route_name]
  assert included_calls == [route_name]


def test_toggle_backup_restore_round_trip_filters_non_settings(monkeypatch):
  server = _load_server_module()
  assert server._import_galaxy_web_symbols()

  persistent = server.ParamKeyFlag.PERSISTENT
  dont_log = server.ParamKeyFlag.DONT_LOG
  definitions = {
    "EnabledSetting": (True, server.ParamKeyType.BOOL, persistent),
    "AdbEnabled": (None, server.ParamKeyType.BOOL, persistent),
    "NumericSetting": (1.5, server.ParamKeyType.FLOAT, persistent),
    "JsonSetting": ({"mode": "default"}, server.ParamKeyType.JSON, persistent),
    "SensitiveSetting": ("", server.ParamKeyType.STRING, persistent | dont_log),
    "TransientSetting": (False, server.ParamKeyType.BOOL, server.ParamKeyFlag.CLEAR_ON_MANAGER_START),
    "NoDefaultSetting": (None, server.ParamKeyType.STRING, persistent),
    "StatsSetting": ({}, server.ParamKeyType.JSON, persistent),
  }

  class ToggleParams:
    def __init__(self):
      self.values = {
        "EnabledSetting": False,
        "AdbEnabled": True,
        "NumericSetting": 2.75,
        "JsonSetting": {"mode": "custom"},
        "SensitiveSetting": "secret",
        "TransientSetting": True,
        "NoDefaultSetting": "runtime",
        "StatsSetting": {"drives": 10},
      }

    def all_keys(self):
      return list(definitions)

    def get(self, key, block=False):
      del block
      default = definitions[key][0]
      return self.values.get(key, default)

    def get_default_value(self, key):
      return definitions[key][0]

    def get_key_flag(self, key):
      return definitions[key][2]

    def get_type(self, key):
      return definitions[key][1]

    def get_tuning_level(self, key):
      del key
      return 0

    def put(self, key, value):
      self.values[key] = value

  raw_params = ToggleParams()
  server.starpilot_default_params = [
    (key, default, value_type, 0)
    for key, (default, value_type, _) in definitions.items()
  ]
  server._cached_static_default_values = None
  monkeypatch.setattr(server, "_params_raw", raw_params)
  monkeypatch.setattr(server, "params", server.ParamsCompat(raw_params))
  monkeypatch.setattr(server, "EXCLUDED_KEYS", {"StatsSetting"})
  update_calls = []
  monkeypatch.setattr(server, "update_starpilot_toggles", lambda: update_calls.append(True))

  app = server.Flask(
    "toggle_backup_test",
    template_folder=str(MODULE_DIR / "templates"),
    static_folder=str(MODULE_DIR / "assets"),
  )
  server.setup(app)
  client = app.test_client()

  backup_response = client.post("/api/toggles/backup")
  backup_payload = json.loads(backup_response.data)
  backed_up_values = utilities.decode_parameters(backup_payload["data"])

  assert backup_response.status_code == 200
  assert backup_payload["format"] == server.TOGGLE_BACKUP_FORMAT
  assert backup_payload["version"] == server.TOGGLE_BACKUP_VERSION
  assert backup_payload["settingsCount"] == 4
  assert backed_up_values == {
    "AdbEnabled": True,
    "EnabledSetting": False,
    "JsonSetting": {"mode": "custom"},
    "NumericSetting": 2.75,
  }

  raw_params.values.update({
    "EnabledSetting": True,
    "AdbEnabled": False,
    "NumericSetting": 9.0,
    "JsonSetting": {"mode": "changed"},
    "SensitiveSetting": "new-secret",
    "TransientSetting": False,
    "NoDefaultSetting": "new-runtime",
    "StatsSetting": {"drives": 99},
  })
  restore_response = client.post("/api/toggles/restore", json={"data": backup_payload["data"]})
  restore_payload = restore_response.get_json()

  assert restore_response.status_code == 200
  assert restore_payload["restoredCount"] == 4
  assert restore_payload["skippedCount"] == 0
  assert raw_params.values["AdbEnabled"] is True
  assert raw_params.values["EnabledSetting"] is False
  assert raw_params.values["NumericSetting"] == 2.75
  assert raw_params.values["JsonSetting"] == {"mode": "custom"}
  assert raw_params.values["SensitiveSetting"] == "new-secret"
  assert raw_params.values["TransientSetting"] is False
  assert raw_params.values["NoDefaultSetting"] == "new-runtime"
  assert raw_params.values["StatsSetting"] == {"drives": 99}
  assert update_calls == [True]


def test_toggle_restore_reports_invalid_and_unavailable_settings(monkeypatch):
  server = _load_server_module()
  assert server._import_galaxy_web_symbols()

  class ToggleParams:
    def __init__(self):
      self.values = {"EnabledSetting": False}

    def get_key_flag(self, key):
      del key
      return server.ParamKeyFlag.PERSISTENT

    def get_type(self, key):
      del key
      return server.ParamKeyType.BOOL

    def put(self, key, value):
      self.values[key] = value

  raw_params = ToggleParams()
  server.starpilot_default_params = [("EnabledSetting", True, server.ParamKeyType.BOOL, 0)]
  monkeypatch.setattr(server, "_params_raw", raw_params)
  monkeypatch.setattr(server, "EXCLUDED_KEYS", set())
  monkeypatch.setattr(server, "update_starpilot_toggles", lambda: None)

  app = server.Flask(
    "toggle_restore_validation_test",
    template_folder=str(MODULE_DIR / "templates"),
    static_folder=str(MODULE_DIR / "assets"),
  )
  server.setup(app)
  client = app.test_client()

  mixed_data = utilities.encode_parameters({
    "EnabledSetting": "true",
    "RemovedSetting": "1",
  })
  mixed_response = client.post("/api/toggles/restore", json={"data": mixed_data})
  mixed_payload = mixed_response.get_json()

  assert mixed_response.status_code == 200
  assert mixed_payload["restoredCount"] == 1
  assert mixed_payload["skippedCount"] == 1
  assert raw_params.values["EnabledSetting"] is True

  damaged_response = client.post("/api/toggles/restore", json={"data": "not-a-backup"})
  wrong_format_response = client.post("/api/toggles/restore", json={
    "format": "different-format",
    "data": mixed_data,
  })

  assert damaged_response.status_code == 400
  assert damaged_response.get_json()["success"] is False
  assert wrong_format_response.status_code == 400
  assert wrong_format_response.get_json()["success"] is False
