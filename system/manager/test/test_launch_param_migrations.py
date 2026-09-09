from pathlib import Path

from openpilot.system.manager.launch_param_migrations import (
  ACCELERATION_PROFILE_MIGRATION_MARKER,
  BRANCH_DEFAULTS_MIGRATION_MARKER,
  CAMERA_VIEW_DEFAULT_MIGRATION_MARKER,
  DEFAULT_CAMERA_VIEW,
  DEVELOPER_METRIC_DISPLAY_KEYS,
  DEVELOPER_METRIC_DISPLAY_MIGRATION_MARKER,
  GALAXY_NEW_DEFAULT_MIGRATION_MARKER,
  DEFAULT_LANE_CHANGE_SMOOTHING,
  DEFAULT_STEER_KP,
  DEVICE_SHUTDOWN_HOURS_MIGRATION_MARKER,
  LANE_CHANGE_SMOOTHING_MIGRATION_MARKER,
  LAUNCH_PARAM_MIGRATION_MARKER,
  LATERAL_METHOD_REBRAND_MIGRATION_MARKER,
  MARKER_DIRNAME,
  REVERSE_CRUISE_RESTORE_MIGRATION_MARKER,
  STANDARD_ACCELERATION_PROFILE,
  SPEED_LIMIT_VISIBILITY_MIGRATION_MARKER,
  LEGACY_UI_SELECTION_MIGRATION_MARKER,
  VISION_SPEED_LIMIT_DETECTION_MIGRATION_MARKER,
  apply_launch_param_migrations,
)


class FileBackedFakeParams:
  def __init__(self, root: Path):
    self.root = root
    self.root.mkdir(parents=True, exist_ok=True)

  def get_param_path(self, key=""):
    if key:
      return str(self.root / (key.decode() if isinstance(key, bytes) else str(key)))
    return str(self.root)

  def get(self, key):
    path = Path(self.get_param_path(key))
    if not path.is_file():
      return None
    return path.read_text(encoding="utf-8")

  def get_bool(self, key):
    value = self.get(key)
    return value == "1"

  def get_float(self, key):
    value = self.get(key)
    return float(value) if value is not None else 0.0

  def get_int(self, key):
    value = self.get(key)
    return int(float(value)) if value is not None else 0

  def put_bool(self, key, value):
    Path(self.get_param_path(key)).write_text("1" if value else "0", encoding="utf-8")

  def put_int(self, key, value):
    Path(self.get_param_path(key)).write_text(str(int(value)), encoding="utf-8")

  def put_float(self, key, value):
    Path(self.get_param_path(key)).write_text(str(float(value)), encoding="utf-8")

  def put(self, key, value):
    Path(self.get_param_path(key)).write_text(str(value), encoding="utf-8")


def marker_path(tmp_path: Path, marker_name: str) -> Path:
  path = tmp_path / MARKER_DIRNAME / "params" / marker_name
  path.parent.mkdir(parents=True, exist_ok=True)
  return path


def test_apply_launch_param_migrations_sets_branch_defaults_once(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")

  params.put_bool("LongPitch", False)
  params.put_float("SteerKP", 0.7)
  params.put_float("SteerKPStock", 1.0)

  apply_launch_param_migrations(params)

  assert params.get_bool("LongPitch")
  assert params.get_float("SteerKP") == DEFAULT_STEER_KP
  assert params.get_float("SteerKPStock") == DEFAULT_STEER_KP
  assert marker_path(tmp_path, LAUNCH_PARAM_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_does_not_reapply_after_marker(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  marker = marker_path(tmp_path, LAUNCH_PARAM_MIGRATION_MARKER)

  params.put_bool("LongPitch", False)
  params.put_float("SteerKP", 0.65)
  params.put_float("SteerKPStock", DEFAULT_STEER_KP)
  marker.touch()

  apply_launch_param_migrations(params, marker)

  assert not params.get_bool("LongPitch")
  assert params.get_float("SteerKP") == 0.65
  assert params.get_float("SteerKPStock") == DEFAULT_STEER_KP


def test_apply_launch_param_migrations_converts_legacy_speed_limit_hide_once(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_bool("ShowSpeedLimits", True)
  params.put_bool("HideSpeedLimit", True)

  apply_launch_param_migrations(params)

  assert not params.get_bool("ShowSpeedLimits")
  assert not params.get_bool("HideSpeedLimit")
  assert marker_path(tmp_path, SPEED_LIMIT_VISIBILITY_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_preserves_speed_limit_visibility_choice(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_bool("ShowSpeedLimits", False)
  params.put_bool("HideSpeedLimit", False)
  marker = marker_path(tmp_path, SPEED_LIMIT_VISIBILITY_MIGRATION_MARKER)

  apply_launch_param_migrations(params)

  assert not params.get_bool("ShowSpeedLimits")
  assert not params.get_bool("HideSpeedLimit")
  assert marker.is_file()

  params.put_bool("ShowSpeedLimits", True)
  apply_launch_param_migrations(params)
  assert params.get_bool("ShowSpeedLimits")


def test_apply_launch_param_migrations_converts_device_shutdown_index_to_hours(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_int("DeviceShutdown", 9)

  apply_launch_param_migrations(params)

  assert params.get_int("DeviceShutdown") == 6
  assert marker_path(tmp_path, DEVICE_SHUTDOWN_HOURS_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_rounds_legacy_minute_shutdown_up_to_one_hour(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_int("DeviceShutdown", 2)

  apply_launch_param_migrations(params)

  assert params.get_int("DeviceShutdown") == 1


def test_apply_launch_param_migrations_does_not_reapply_device_shutdown_conversion(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_int("DeviceShutdown", 9)
  marker_path(tmp_path, DEVICE_SHUTDOWN_HOURS_MIGRATION_MARKER).touch()

  apply_launch_param_migrations(params)

  assert params.get_int("DeviceShutdown") == 9


def test_apply_launch_param_migrations_updates_legacy_camera_view_default_once(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_int("CameraView", 3)

  apply_launch_param_migrations(params)

  assert params.get_int("CameraView") == DEFAULT_CAMERA_VIEW
  assert marker_path(tmp_path, CAMERA_VIEW_DEFAULT_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_preserves_custom_camera_view(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_int("CameraView", 0)

  apply_launch_param_migrations(params)

  assert params.get_int("CameraView") == 0


def test_apply_launch_param_migrations_restores_reverse_cruise_from_swapped_intervals(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_float("CustomCruise", 5.0)
  params.put_float("CustomCruiseLong", 1.0)

  apply_launch_param_migrations(params)

  assert params.get_bool("ReverseCruise")
  assert marker_path(tmp_path, REVERSE_CRUISE_RESTORE_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_preserves_explicit_reverse_cruise_choice(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_float("CustomCruise", 5.0)
  params.put_float("CustomCruiseLong", 1.0)
  params.put_bool("ReverseCruise", False)

  apply_launch_param_migrations(params)

  assert not params.get_bool("ReverseCruise")


def test_apply_launch_param_migrations_enables_galaxy_new_default_once(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_bool("GalaxyMobileDefault", False)

  apply_launch_param_migrations(params)

  assert params.get_bool("GalaxyMobileDefault")
  marker = marker_path(tmp_path, GALAXY_NEW_DEFAULT_MIGRATION_MARKER)
  assert marker.is_file()

  params.put_bool("GalaxyMobileDefault", False)
  apply_launch_param_migrations(params)

  assert not params.get_bool("GalaxyMobileDefault")


def test_apply_launch_param_migrations_applies_branch_defaults_for_existing_installs(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")

  params.put_bool("LongPitch", False)
  params.put_bool("CEStoppedLead", True)
  params.put_bool("ForceStops", False)
  params.put_float("AggressiveFollowHigh", 1.25)
  params.put_float("StandardFollowHigh", 1.45)
  params.put_float("StandardJerkAcceleration", 50.0)
  params.put_float("RelaxedFollow", 1.75)
  params.put_float("RelaxedFollowHigh", 1.75)
  params.put_float("RelaxedJerkSpeed", 50.0)
  marker_path(tmp_path, LAUNCH_PARAM_MIGRATION_MARKER).touch()

  apply_launch_param_migrations(params)

  assert not params.get_bool("LongPitch")
  assert not params.get_bool("CEStoppedLead")
  assert params.get_bool("ForceStops")
  assert params.get_float("AggressiveFollowHigh") == 1.0
  assert params.get_float("StandardFollowHigh") == 1.2
  assert params.get_float("StandardJerkAcceleration") == 100.0
  assert params.get_float("RelaxedFollow") == 1.6
  assert params.get_float("RelaxedFollowHigh") == 1.4
  assert params.get_float("RelaxedJerkSpeed") == 100.0
  assert marker_path(tmp_path, BRANCH_DEFAULTS_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_does_not_reapply_branch_defaults_after_marker(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  branch_defaults_marker = marker_path(tmp_path, BRANCH_DEFAULTS_MIGRATION_MARKER)

  params.put_bool("ConditionalExperimental", False)
  params.put_bool("CEStoppedLead", True)
  params.put_bool("ForceStops", False)
  params.put_float("AggressiveFollowHigh", 2.0)
  params.put_float("StandardJerkAcceleration", 25.0)
  params.put_float("RelaxedFollow", 2.0)
  branch_defaults_marker.touch()

  apply_launch_param_migrations(params)

  assert not params.get_bool("ConditionalExperimental")
  assert params.get_bool("CEStoppedLead")
  assert not params.get_bool("ForceStops")
  assert params.get_float("AggressiveFollowHigh") == 2.0
  assert params.get_float("StandardJerkAcceleration") == 25.0
  assert params.get_float("RelaxedFollow") == 2.0


def test_apply_launch_param_migrations_preserves_custom_branch_defaults_without_marker(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")

  params.put_bool("CEStoppedLead", True)
  params.put_bool("ForceStops", True)
  params.put_float("AggressiveFollowHigh", 2.0)
  params.put_float("StandardJerkAcceleration", 25.0)
  params.put_float("RelaxedFollow", 2.0)

  apply_launch_param_migrations(params)

  assert not params.get_bool("CEStoppedLead")
  assert params.get_bool("ForceStops")
  assert params.get_float("AggressiveFollowHigh") == 2.0
  assert params.get_float("StandardJerkAcceleration") == 25.0
  assert params.get_float("RelaxedFollow") == 2.0


def test_apply_launch_param_migrations_updates_acceleration_profile_for_existing_installs(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")

  params.put_int("AccelerationProfile", 2)
  marker_path(tmp_path, LAUNCH_PARAM_MIGRATION_MARKER).touch()
  marker_path(tmp_path, BRANCH_DEFAULTS_MIGRATION_MARKER).touch()

  apply_launch_param_migrations(params)

  assert params.get_int("AccelerationProfile") == STANDARD_ACCELERATION_PROFILE
  assert marker_path(tmp_path, ACCELERATION_PROFILE_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_does_not_reapply_acceleration_profile_after_marker(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  acceleration_profile_marker = marker_path(tmp_path, ACCELERATION_PROFILE_MIGRATION_MARKER)

  params.put_int("AccelerationProfile", 3)
  acceleration_profile_marker.touch()

  apply_launch_param_migrations(params)

  assert params.get_int("AccelerationProfile") == 3


def test_apply_launch_param_migrations_preserves_custom_acceleration_profile_without_marker(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")

  params.put_int("AccelerationProfile", 1)

  apply_launch_param_migrations(params)

  assert params.get_int("AccelerationProfile") == 1


def test_apply_launch_param_migrations_removes_legacy_ui_selection(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_bool("UseOldUI", True)
  params.put_bool("TryRaylibUI", False)

  apply_launch_param_migrations(params)

  assert not Path(params.get_param_path("UseOldUI")).exists()
  assert not Path(params.get_param_path("TryRaylibUI")).exists()
  assert marker_path(tmp_path, LEGACY_UI_SELECTION_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_removes_legacy_ui_selection_once(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  marker = marker_path(tmp_path, LEGACY_UI_SELECTION_MIGRATION_MARKER)

  apply_launch_param_migrations(params)
  params.put_bool("UseOldUI", True)
  marker.touch()
  apply_launch_param_migrations(params)

  assert Path(params.get_param_path("UseOldUI")).exists()


def test_apply_launch_param_migrations_preserves_active_lateral_method_trial(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  legacy_prefix = "".join(("F", "T", "M"))
  legacy_values = {
    "ActiveOverrides": '{"vehicleKnobs":{"generic.ff_gain_left":0.12}}',
    "ActiveProfileId": "report:cleanup:recommended",
    "TrialBaseline": '{"params":{"SteerLatAccel":1.8}}',
    "TrialApplied": "1",
  }
  for suffix, value in legacy_values.items():
    params.put(f"{legacy_prefix}{suffix}", value)

  apply_launch_param_migrations(params)

  for suffix, value in legacy_values.items():
    assert params.get(f"FLM{suffix}") == value
    assert not Path(params.get_param_path(f"{legacy_prefix}{suffix}")).exists()
  assert marker_path(tmp_path, LATERAL_METHOD_REBRAND_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_enables_vision_speed_limit_detection_once(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_bool("VisionSpeedLimitDetection", False)
  params.put("SLCPriority1", "Dashboard")
  params.put("SLCPriority2", "Map Data")

  apply_launch_param_migrations(params)

  assert params.get_bool("VisionSpeedLimitDetection")
  assert params.get("SLCPriority1") == "Dashboard"
  assert params.get("SLCPriority2") == "Map Data"
  assert marker_path(tmp_path, VISION_SPEED_LIMIT_DETECTION_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_does_not_reenable_vision_speed_limit_detection_after_marker(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_bool("VisionSpeedLimitDetection", False)
  marker_path(tmp_path, VISION_SPEED_LIMIT_DETECTION_MIGRATION_MARKER).touch()

  apply_launch_param_migrations(params)

  assert not params.get_bool("VisionSpeedLimitDetection")


def test_apply_launch_param_migrations_disables_developer_metric_display_once(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  for key in DEVELOPER_METRIC_DISPLAY_KEYS:
    params.put_bool(key, True)

  apply_launch_param_migrations(params)

  for key in DEVELOPER_METRIC_DISPLAY_KEYS:
    assert not params.get_bool(key)
  assert marker_path(tmp_path, DEVELOPER_METRIC_DISPLAY_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_preserves_developer_metric_display_after_marker(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  for key in DEVELOPER_METRIC_DISPLAY_KEYS:
    params.put_bool(key, True)
  marker_path(tmp_path, DEVELOPER_METRIC_DISPLAY_MIGRATION_MARKER).touch()

  apply_launch_param_migrations(params)

  for key in DEVELOPER_METRIC_DISPLAY_KEYS:
    assert params.get_bool(key)


def test_apply_launch_param_migrations_updates_legacy_lane_change_smoothing_once(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_int("LaneChangeSmoothing", 10)

  apply_launch_param_migrations(params)

  assert params.get_int("LaneChangeSmoothing") == DEFAULT_LANE_CHANGE_SMOOTHING
  assert marker_path(tmp_path, LANE_CHANGE_SMOOTHING_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_preserves_custom_lane_change_smoothing(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_int("LaneChangeSmoothing", 7)

  apply_launch_param_migrations(params)

  assert params.get_int("LaneChangeSmoothing") == 7
  assert marker_path(tmp_path, LANE_CHANGE_SMOOTHING_MIGRATION_MARKER).is_file()


def test_apply_launch_param_migrations_does_not_reapply_lane_change_smoothing_after_marker(tmp_path):
  params = FileBackedFakeParams(tmp_path / "params")
  params.put_int("LaneChangeSmoothing", 10)
  marker_path(tmp_path, LANE_CHANGE_SMOOTHING_MIGRATION_MARKER).touch()

  apply_launch_param_migrations(params)

  assert params.get_int("LaneChangeSmoothing") == 10
