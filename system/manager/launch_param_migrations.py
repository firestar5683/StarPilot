#!/usr/bin/env python3
from __future__ import annotations

import sys

from pathlib import Path
from typing import Protocol

LONG_PITCH_KEY = "LongPitch"
LANE_CHANGE_SMOOTHING_KEY = "LaneChangeSmoothing"
STEER_KP_KEY = "SteerKP"
STEER_KP_STOCK_KEY = "SteerKPStock"
LEGACY_UI_SELECTION_KEYS = ("UseOldUI", "TryRaylibUI")
VISION_SPEED_LIMIT_DETECTION_KEY = "VisionSpeedLimitDetection"
DEVELOPER_METRIC_DISPLAY_KEYS = (
  "FPSCounter",
  "ShowCPU",
  "ShowGPU",
  "NumericalTemp",
  "ShowMemoryUsage",
  "SidebarMetrics",
)
DEVICE_SHUTDOWN_KEY = "DeviceShutdown"
CAMERA_VIEW_KEY = "CameraView"
GALAXY_NEW_DEFAULT_KEY = "GalaxyMobileDefault"

DEFAULT_STEER_KP = 0.6
LEGACY_STEER_KP = 0.7
LEGACY_STEER_KP_STOCK_PLACEHOLDER = 1.0

LAUNCH_PARAM_MIGRATION_MARKER = ".starpilot_launch_param_migrations_v2"
BRANCH_DEFAULTS_MIGRATION_MARKER = ".starpilot_branch_defaults_migrations_v1"
ACCELERATION_PROFILE_MIGRATION_MARKER = ".starpilot_acceleration_profile_default_v1"
LEGACY_UI_SELECTION_MIGRATION_MARKER = ".starpilot_remove_legacy_ui_selection_v1"
LATERAL_METHOD_REBRAND_MIGRATION_MARKER = ".starpilot_lateral_method_rebrand_v1"
VISION_SPEED_LIMIT_DETECTION_MIGRATION_MARKER = ".starpilot_vision_speed_limit_detection_v1"
DEVELOPER_METRIC_DISPLAY_MIGRATION_MARKER = ".starpilot_developer_metric_display_off_v1"
LANE_CHANGE_SMOOTHING_MIGRATION_MARKER = ".starpilot_lane_change_smoothing_default_v1"
SPEED_LIMIT_VISIBILITY_MIGRATION_MARKER = ".starpilot_speed_limit_visibility_v1"
DEVICE_SHUTDOWN_HOURS_MIGRATION_MARKER = ".starpilot_device_shutdown_hours_v1"
CAMERA_VIEW_DEFAULT_MIGRATION_MARKER = ".starpilot_camera_view_default_v1"
REVERSE_CRUISE_RESTORE_MIGRATION_MARKER = ".starpilot_restore_reverse_cruise_v1"
GALAXY_NEW_DEFAULT_MIGRATION_MARKER = ".starpilot_galaxy_new_default_v1"
MARKER_DIRNAME = ".starpilot_param_migrations"

LATERAL_METHOD_PARAM_SUFFIXES = (
  "ActiveOverrides",
  "ActiveProfileId",
  "TrialBaseline",
  "TrialApplied",
)

LEGACY_CE_STOPPED_LEAD_DEFAULT = True
LEGACY_FORCE_STOPS_DEFAULT = False
LEGACY_AGGRESSIVE_FOLLOW_HIGH_DEFAULT = 1.25
LEGACY_STANDARD_FOLLOW_HIGH_DEFAULT = 1.45
LEGACY_RELAXED_FOLLOW_DEFAULT = 1.75
LEGACY_RELAXED_FOLLOW_HIGH_DEFAULT = 1.75
LEGACY_JERK_DEFAULT = 50.0
LEGACY_ACCELERATION_PROFILE_DEFAULT = 2
LEGACY_LANE_CHANGE_SMOOTHING_DEFAULT = 10
LEGACY_CAMERA_VIEW_DEFAULT = 3

STANDARD_ACCELERATION_PROFILE = 0
DEFAULT_LANE_CHANGE_SMOOTHING = 5
DEFAULT_CAMERA_VIEW = 2

BRANCH_BOOL_MIGRATIONS = {
  "CEStoppedLead": (LEGACY_CE_STOPPED_LEAD_DEFAULT, False),
  "ForceStops": (LEGACY_FORCE_STOPS_DEFAULT, True),
}

BRANCH_FLOAT_MIGRATIONS = {
  "AggressiveFollowHigh": (LEGACY_AGGRESSIVE_FOLLOW_HIGH_DEFAULT, 1.0),
  "StandardFollowHigh": (LEGACY_STANDARD_FOLLOW_HIGH_DEFAULT, 1.2),
  "StandardJerkAcceleration": (LEGACY_JERK_DEFAULT, 100.0),
  "StandardJerkDeceleration": (LEGACY_JERK_DEFAULT, 100.0),
  "StandardJerkSpeed": (LEGACY_JERK_DEFAULT, 100.0),
  "StandardJerkSpeedDecrease": (LEGACY_JERK_DEFAULT, 100.0),
  "RelaxedFollow": (LEGACY_RELAXED_FOLLOW_DEFAULT, 1.6),
  "RelaxedFollowHigh": (LEGACY_RELAXED_FOLLOW_HIGH_DEFAULT, 1.4),
  "RelaxedJerkAcceleration": (LEGACY_JERK_DEFAULT, 100.0),
  "RelaxedJerkDeceleration": (LEGACY_JERK_DEFAULT, 100.0),
  "RelaxedJerkSpeed": (LEGACY_JERK_DEFAULT, 100.0),
  "RelaxedJerkSpeedDecrease": (LEGACY_JERK_DEFAULT, 100.0),
}

ACCELERATION_PROFILE_MIGRATION = {
  "AccelerationProfile": (LEGACY_ACCELERATION_PROFILE_DEFAULT, STANDARD_ACCELERATION_PROFILE),
}


class ParamsLike(Protocol):
  def get_param_path(self, key: str = "") -> str: ...
  def get_bool(self, key: str) -> bool: ...
  def get_int(self, key: str) -> int: ...
  def get_float(self, key: str) -> float: ...
  def put_bool(self, key: str, value: bool) -> None: ...
  def put_int(self, key: str, value: int) -> None: ...
  def put_float(self, key: str, value: float) -> None: ...


def _approx_equal(lhs: float, rhs: float, tolerance: float = 1e-6) -> bool:
  return abs(lhs - rhs) <= tolerance


def _default_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / LAUNCH_PARAM_MIGRATION_MARKER


def _branch_defaults_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / BRANCH_DEFAULTS_MIGRATION_MARKER


def _acceleration_profile_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / ACCELERATION_PROFILE_MIGRATION_MARKER


def _legacy_ui_selection_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / LEGACY_UI_SELECTION_MIGRATION_MARKER


def _lateral_method_rebrand_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / LATERAL_METHOD_REBRAND_MIGRATION_MARKER


def _vision_speed_limit_detection_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / VISION_SPEED_LIMIT_DETECTION_MIGRATION_MARKER


def _developer_metric_display_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / DEVELOPER_METRIC_DISPLAY_MIGRATION_MARKER


def _lane_change_smoothing_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / LANE_CHANGE_SMOOTHING_MIGRATION_MARKER


def _speed_limit_visibility_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / SPEED_LIMIT_VISIBILITY_MIGRATION_MARKER


def _device_shutdown_hours_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / DEVICE_SHUTDOWN_HOURS_MIGRATION_MARKER


def _camera_view_default_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / CAMERA_VIEW_DEFAULT_MIGRATION_MARKER


def _reverse_cruise_restore_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / REVERSE_CRUISE_RESTORE_MIGRATION_MARKER


def _galaxy_new_default_marker_path(params: ParamsLike) -> Path:
  return _marker_dir_path(params) / GALAXY_NEW_DEFAULT_MIGRATION_MARKER


def _marker_dir_path(params: ParamsLike) -> Path:
  params_path = Path(params.get_param_path())
  # Params.clear_all() removes unknown files inside the params directory, so
  # one-time migration markers must live alongside it, not inside it.
  return params_path.parent / MARKER_DIRNAME / params_path.name


def _param_file_exists(params: ParamsLike, key: str) -> bool:
  return Path(params.get_param_path(key)).exists()


def _should_migrate_bool_param(params: ParamsLike, key: str, legacy_default: bool) -> bool:
  return not _param_file_exists(params, key) or params.get_bool(key) == legacy_default


def _should_migrate_int_param(params: ParamsLike, key: str, legacy_default: int) -> bool:
  return not _param_file_exists(params, key) or params.get_int(key) == legacy_default


def _should_migrate_float_param(params: ParamsLike, key: str, legacy_default: float) -> bool:
  return not _param_file_exists(params, key) or _approx_equal(params.get_float(key), legacy_default)


def _apply_legacy_launch_param_migrations(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  if not params.get_bool(LONG_PITCH_KEY):
    params.put_bool(LONG_PITCH_KEY, True)

  steer_kp = params.get_float(STEER_KP_KEY)
  if _approx_equal(steer_kp, 0.0) or _approx_equal(steer_kp, LEGACY_STEER_KP):
    params.put_float(STEER_KP_KEY, DEFAULT_STEER_KP)

  steer_kp_stock = params.get_float(STEER_KP_STOCK_KEY)
  if (_approx_equal(steer_kp_stock, 0.0) or
      _approx_equal(steer_kp_stock, LEGACY_STEER_KP) or
      _approx_equal(steer_kp_stock, LEGACY_STEER_KP_STOCK_PLACEHOLDER)):
    params.put_float(STEER_KP_STOCK_KEY, DEFAULT_STEER_KP)

  marker.touch()


def _apply_branch_default_migration(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  for key, (legacy_default, new_default) in BRANCH_BOOL_MIGRATIONS.items():
    if _should_migrate_bool_param(params, key, legacy_default):
      params.put_bool(key, new_default)

  for key, (legacy_default, new_default) in BRANCH_FLOAT_MIGRATIONS.items():
    if _should_migrate_float_param(params, key, legacy_default):
      params.put_float(key, new_default)

  marker.touch()


def _apply_acceleration_profile_default_migration(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  for key, (legacy_default, new_default) in ACCELERATION_PROFILE_MIGRATION.items():
    if _should_migrate_int_param(params, key, legacy_default):
      params.put_int(key, new_default)

  marker.touch()


def _remove_legacy_ui_selection(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  for key in LEGACY_UI_SELECTION_KEYS:
    Path(params.get_param_path(key)).unlink(missing_ok=True)

  marker.touch()


def _apply_lateral_method_rebrand_migration(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)
  legacy_prefix = "".join(("F", "T", "M"))

  for suffix in LATERAL_METHOD_PARAM_SUFFIXES:
    legacy_path = Path(params.get_param_path(f"{legacy_prefix}{suffix}"))
    current_path = Path(params.get_param_path(f"FLM{suffix}"))
    if legacy_path.is_file():
      current_path.parent.mkdir(parents=True, exist_ok=True)
      current_path.write_bytes(legacy_path.read_bytes())
      legacy_path.unlink()

  marker.touch()


def _apply_vision_speed_limit_detection_migration(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  params.put_bool(VISION_SPEED_LIMIT_DETECTION_KEY, True)

  marker.touch()


def _apply_developer_metric_display_migration(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  for key in DEVELOPER_METRIC_DISPLAY_KEYS:
    params.put_bool(key, False)

  marker.touch()


def _apply_lane_change_smoothing_default_migration(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  if params.get_int(LANE_CHANGE_SMOOTHING_KEY) == LEGACY_LANE_CHANGE_SMOOTHING_DEFAULT:
    params.put_int(LANE_CHANGE_SMOOTHING_KEY, DEFAULT_LANE_CHANGE_SMOOTHING)

  marker.touch()


def _apply_speed_limit_visibility_migration(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  # Preserve users who explicitly enabled the legacy hide control while making
  # ShowSpeedLimits the only visibility setting used by the raylib UIs.
  if params.get_bool("HideSpeedLimit"):
    params.put_bool("ShowSpeedLimits", False)
  params.put_bool("HideSpeedLimit", False)

  marker.touch()


def _apply_device_shutdown_hours_migration(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  if _param_file_exists(params, DEVICE_SHUTDOWN_KEY):
    legacy_value = params.get_int(DEVICE_SHUTDOWN_KEY)
    hours = max(1, min(30, legacy_value - 3 if legacy_value >= 4 else 1))
    params.put_int(DEVICE_SHUTDOWN_KEY, hours)

  marker.touch()


def _apply_camera_view_default_migration(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)

  if _should_migrate_int_param(params, CAMERA_VIEW_KEY, LEGACY_CAMERA_VIEW_DEFAULT):
    params.put_int(CAMERA_VIEW_KEY, DEFAULT_CAMERA_VIEW)

  marker.touch()


def _restore_reverse_cruise_param(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)
  if (not _param_file_exists(params, "ReverseCruise") and
      _approx_equal(params.get_float("CustomCruise"), 5.0) and
      _approx_equal(params.get_float("CustomCruiseLong"), 1.0)):
    params.put_bool("ReverseCruise", True)
  marker.touch()


def _enable_galaxy_new_default(params: ParamsLike, marker: Path) -> None:
  if marker.exists():
    return

  marker.parent.mkdir(parents=True, exist_ok=True)
  params.put_bool(GALAXY_NEW_DEFAULT_KEY, True)
  marker.touch()


def apply_launch_param_migrations(params: ParamsLike, marker_path: Path | None = None,
                                  branch_defaults_marker_path: Path | None = None,
                                  acceleration_profile_marker_path: Path | None = None,
                                  legacy_ui_selection_marker_path: Path | None = None,
                                  lateral_method_rebrand_marker_path: Path | None = None,
                                  vision_speed_limit_detection_marker_path: Path | None = None,
                                  developer_metric_display_marker_path: Path | None = None,
                                  lane_change_smoothing_marker_path: Path | None = None,
                                  speed_limit_visibility_marker_path: Path | None = None,
                                  device_shutdown_hours_marker_path: Path | None = None,
                                  camera_view_default_marker_path: Path | None = None,
                                  reverse_cruise_restore_marker_path: Path | None = None,
                                  galaxy_new_default_marker_path: Path | None = None) -> None:
  _apply_legacy_launch_param_migrations(params, marker_path or _default_marker_path(params))
  # Keep branch-default rollout on its own marker so older installs that already
  # have the legacy marker still receive this one-time param reset.
  _apply_branch_default_migration(params, branch_defaults_marker_path or _branch_defaults_marker_path(params))
  _apply_acceleration_profile_default_migration(
    params, acceleration_profile_marker_path or _acceleration_profile_marker_path(params)
  )
  _remove_legacy_ui_selection(
    params, legacy_ui_selection_marker_path or _legacy_ui_selection_marker_path(params)
  )
  _apply_lateral_method_rebrand_migration(
    params, lateral_method_rebrand_marker_path or _lateral_method_rebrand_marker_path(params)
  )
  _apply_vision_speed_limit_detection_migration(
    params, vision_speed_limit_detection_marker_path or _vision_speed_limit_detection_marker_path(params)
  )
  _apply_developer_metric_display_migration(
    params, developer_metric_display_marker_path or _developer_metric_display_marker_path(params)
  )
  _apply_lane_change_smoothing_default_migration(
    params, lane_change_smoothing_marker_path or _lane_change_smoothing_marker_path(params)
  )
  _apply_speed_limit_visibility_migration(
    params, speed_limit_visibility_marker_path or _speed_limit_visibility_marker_path(params)
  )
  _apply_device_shutdown_hours_migration(
    params, device_shutdown_hours_marker_path or _device_shutdown_hours_marker_path(params)
  )
  _apply_camera_view_default_migration(
    params, camera_view_default_marker_path or _camera_view_default_marker_path(params)
  )
  _restore_reverse_cruise_param(
    params, reverse_cruise_restore_marker_path or _reverse_cruise_restore_marker_path(params)
  )
  _enable_galaxy_new_default(
    params, galaxy_new_default_marker_path or _galaxy_new_default_marker_path(params)
  )


def main() -> int:
  try:
    from openpilot.common.params import Params

    apply_launch_param_migrations(Params())
  except Exception as exc:
    print(f"launch_param_migrations.py failed: {exc}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
