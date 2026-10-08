"""Strict saved visibility choices shared by settings and onroad presentation."""

from dataclasses import dataclass
from enum import IntEnum
import os
import stat
from typing import Any

from openpilot.starpilot.saved_source import read_saved


class CameraViewChoice(IntEnum):
  AUTO = 0
  DRIVER = 1
  STANDARD = 2
  WIDE = 3
  NONE = 4


CAMERA_LABELS = ("Auto", "Driver", "Standard", "Wide", "None")


class LeadInfoMode(IntEnum):
  OFF = 0
  DISTANCE = 1
  SPEED = 2


LEAD_INFO_LABELS = ("Off", "Distance", "Speed")


@dataclass(frozen=True)
class SavedCameraView:
  raw: bytes | None
  value: CameraViewChoice | None
  readable: bool


def read_camera_view(params: Any) -> SavedCameraView:
  try:
    raw, readable = read_saved(params, "CameraView", 8)
  except (AttributeError, OSError, TypeError, ValueError):
    return SavedCameraView(None, None, False)
  if not readable:
    return SavedCameraView(raw, None, False)
  if raw is None:
    return SavedCameraView(None, CameraViewChoice.STANDARD, True)
  try:
    if raw not in (b"0", b"1", b"2", b"3", b"4"):
      raise ValueError("Invalid camera choice")
    return SavedCameraView(raw, CameraViewChoice(int(raw)), True)
  except (TypeError, ValueError):
    return SavedCameraView(raw, None, True)


DEFAULTS = {
  "HideSpeed": False,
  "HideMaxSpeed": False,
  "HideSteeringWheel": False,
  "HideDMIcon": False,
  "HidePersonalityAlerts": False,
  "ShowBrakeStatus": False,
  "PedalsOnUI": False,
  "DriverCamera": False,
  "StoppedTimer": False,
  "StockConfidenceBallWidget": False,
  "EnableTorqueBarWidget": True,
  "RainbowPath": False,
  "HideLeadMarker": True,
  "LeadInfo": False,
  "BlindSpotMetrics": True,
  "SignalMetrics": False,
  "ShowSpeedLimits": False,
  "UseVienna": False,
}
MAX_RAW_BYTES = 16


@dataclass(frozen=True)
class SavedVisibility:
  raw: bytes | None
  value: bool | None
  readable: bool = True


@dataclass(frozen=True)
class SavedLeadInfo:
  flag: SavedVisibility
  mode_raw: bytes | None
  mode: LeadInfoMode | None
  readable: bool


def read_lead_info(params: Any) -> SavedLeadInfo:
  flag = read_visibility(params, "LeadInfo")
  try:
    raw, readable = read_saved(params, "LeadInfoMode", 16)
  except (AttributeError, OSError, TypeError, ValueError):
    raw, readable = None, False
  if not flag.readable or not readable:
    return SavedLeadInfo(flag, raw, None, False)
  if flag.value is None or raw not in (None, b"0", b"1", b"2"):
    return SavedLeadInfo(flag, raw, None, True)
  if not flag.value:
    mode = LeadInfoMode.OFF
  elif raw in (None, b"0", b"2"):
    mode = LeadInfoMode.SPEED
  else:
    mode = LeadInfoMode.DISTANCE
  return SavedLeadInfo(flag, raw, mode, True)


def read_visibility(params: Any, key: str) -> SavedVisibility:
  if key not in DEFAULTS:
    raise KeyError(key)
  try:
    path = params.get_param_path(key)
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
  except FileNotFoundError:
    return SavedVisibility(None, DEFAULTS[key])
  except (AttributeError, OSError, TypeError, ValueError):
    return SavedVisibility(None, None, False)
  try:
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
      return SavedVisibility(None, None, False)
    raw = os.read(descriptor, MAX_RAW_BYTES + 1)
  except OSError:
    return SavedVisibility(None, None, False)
  finally:
    os.close(descriptor)
  if len(raw) > MAX_RAW_BYTES:
    return SavedVisibility(raw, None, False)
  return SavedVisibility(raw, False if raw == b"0" else True if raw == b"1" else None)


@dataclass(frozen=True)
class OnroadAppearance:
  hide_speed: bool = False
  hide_max_speed: bool = False
  hide_steering_wheel: bool = False
  show_torque_bar: bool = True
  show_blindspot_border: bool = True
  show_signal_border: bool = False
  show_speed_limit_sign: bool = False
  use_vienna_sign: bool = False
  show_stopped_timer: bool = False
  show_stock_confidence_ball: bool = False
  show_lead_indicator: bool = False
  lead_info_mode: LeadInfoMode = LeadInfoMode.OFF
  lead_info_metric: bool | None = False
  camera_view: CameraViewChoice = CameraViewChoice.STANDARD
  driver_camera_on_reverse: bool = False
  hide_dm_icon: bool = False
  hide_personality_alerts: bool = False
  wheel_pedal_feedback: bool = False


def onroad_appearance(params: Any) -> OnroadAppearance:
  """Bad saved bytes keep the visible baseline; no view writes during refresh."""
  values = {key: read_visibility(params, key).value for key in DEFAULTS}
  saved_lead_info = read_lead_info(params)
  camera_view = read_camera_view(params).value
  try:
    metric_raw, metric_readable = read_saved(params, "IsMetric", 8)
  except (AttributeError, OSError, TypeError, ValueError):
    metric_raw, metric_readable = None, False
  metric = False if metric_readable and metric_raw in (None, b"0") else True if metric_readable and metric_raw == b"1" else None
  return OnroadAppearance(
    hide_speed=values["HideSpeed"] is True,
    hide_max_speed=values["HideMaxSpeed"] is True,
    hide_steering_wheel=values["HideSteeringWheel"] is True,
    hide_dm_icon=values["HideDMIcon"] is True,
    hide_personality_alerts=values["HidePersonalityAlerts"] is True,
    wheel_pedal_feedback=values["ShowBrakeStatus"] is True or values["PedalsOnUI"] is True,
    show_torque_bar=values["EnableTorqueBarWidget"] is not False,
    show_blindspot_border=values["BlindSpotMetrics"] is True,
    show_signal_border=values["SignalMetrics"] is True,
    show_speed_limit_sign=values["ShowSpeedLimits"] is True,
    use_vienna_sign=values["UseVienna"] is True,
    show_stopped_timer=values["StoppedTimer"] is True,
    show_stock_confidence_ball=values["StockConfidenceBallWidget"] is True,
    show_lead_indicator=values["HideLeadMarker"] is False,
    lead_info_mode=saved_lead_info.mode if values["HideLeadMarker"] is False and saved_lead_info.mode is not None else LeadInfoMode.OFF,
    lead_info_metric=metric,
    camera_view=camera_view if camera_view is not None else CameraViewChoice.STANDARD,
    driver_camera_on_reverse=values["DriverCamera"] is True,
  )
