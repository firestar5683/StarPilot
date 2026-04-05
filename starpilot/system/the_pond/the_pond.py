#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import importlib
import os
import sys
import tarfile

from io import BytesIO
from pathlib import Path

import base64
import errno
import hashlib
import json
import re
import requests
import secrets
import selectors
import shutil
import signal
import subprocess
import threading
import time
import traceback
from urllib.parse import quote

from cereal import car, log, messaging
from opendbc.can.parser import CANParser
from opendbc.car.gm.values import GMFlags
from opendbc.car.toyota.carcontroller import LOCK_CMD, UNLOCK_CMD
from openpilot.common.constants import CV
from openpilot.common.params import ParamKeyType, Params
from openpilot.common.realtime import DT_HW
from openpilot.common.time_helpers import system_time_valid
from openpilot.system.hardware import HARDWARE, PC
from openpilot.system.hardware.hw import Paths
from openpilot.system.loggerd.deleter import PRESERVE_ATTR_NAME, PRESERVE_ATTR_VALUE, PRESERVE_COUNT
from openpilot.system.version import get_build_metadata
from panda import Panda

from openpilot.starpilot.assets.theme_manager import HOLIDAY_THEME_PATH, THEME_COMPONENT_PARAMS
from openpilot.starpilot.common.accel_profile import (
  CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY,
  CUSTOM_ACCEL_PROFILE_PARAM_KEYS,
  build_custom_accel_profile_defaults,
  custom_accel_profile_is_initialized,
  normalize_acceleration_profile,
)
from openpilot.starpilot.common.maps_catalog import (
  MAPS_CATALOG,
  MAP_SCHEDULE_OPTIONS,
  get_selected_map_entries,
  sanitize_selected_locations_csv,
  schedule_label,
  schedule_param_value,
)
from openpilot.starpilot.common.starpilot_utilities import delete_file, get_lock_status, run_cmd
from openpilot.starpilot.common.starpilot_variables import ACTIVE_THEME_PATH, ERROR_LOGS_PATH, EXCLUDED_KEYS, LEGACY_STARPILOT_PARAM_RENAMES, MAPS_PATH, RESOURCES_REPO, SCREEN_RECORDINGS_PATH, STOCK_THEME_PATH, THEME_SAVE_PATH,\
                                                           default_ev_tuning_enabled, update_starpilot_toggles
from openpilot.starpilot.common.testing_grounds import (
  DEFAULT_TESTING_GROUND_VARIANT as SHARED_DEFAULT_TESTING_GROUND_VARIANT,
  TESTING_GROUND_VARIANT_LABELS as SHARED_TESTING_GROUND_VARIANT_LABELS,
  TESTING_GROUND_VARIANTS as SHARED_TESTING_GROUND_VARIANTS,
  TESTING_GROUNDS_SCHEMA_VERSION as SHARED_TESTING_GROUNDS_SCHEMA_VERSION,
  TESTING_GROUNDS_SLOT_DEFINITIONS as SHARED_TESTING_GROUNDS_SLOT_DEFINITIONS,
  TESTING_GROUNDS_STATE_PATH as SHARED_TESTING_GROUNDS_STATE_PATH,
)
from openpilot.starpilot.system.the_pond import utilities

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

GITLAB_API = "https://gitlab.com/api/v4"
GITLAB_SUBMISSIONS_PROJECT_ID = "71992109"
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", "")

POND_DEPS_PATH = "/data/pond_deps"
if os.path.isdir(POND_DEPS_PATH) and POND_DEPS_PATH not in sys.path:
  sys.path.insert(0, POND_DEPS_PATH)

REPO_THIRD_PARTY_PATH = Path(__file__).resolve().parents[2] / "third_party"
if REPO_THIRD_PARTY_PATH.is_dir() and str(REPO_THIRD_PARTY_PATH) not in sys.path:
  sys.path.insert(0, str(REPO_THIRD_PARTY_PATH))

Flask = None
Response = None
jsonify = None
make_response = None
render_template = None
request = None
send_file = None
send_from_directory = None

_POND_WEB_DEPS_READY = False
_POND_WEB_DEPS_ERROR = None


def _is_comma_device_runtime() -> bool:
  """Robust runtime device check.

  `PC` is derived from `/TICI`, which can be missing in edge boot/update states.
  For Galaxy routing we must keep on-device Pond on 8082.
  """
  if not PC:
    return True

  if os.path.isfile("/TICI") or os.path.isfile("/AGNOS"):
    return True

  model_path = "/sys/firmware/devicetree/base/model"
  try:
    with open(model_path) as f:
      model = f.read().strip("\x00").lower()
    return "comma " in model
  except Exception:
    return False


def _get_param_key_type(params_obj, key):
  getter = getattr(params_obj, "get_key_type", None)
  if getter is None:
    getter = getattr(params_obj, "get_type", None)
  if getter is None:
    return ParamKeyType.STRING
  return getter(key)


def _import_pond_web_symbols():
  global Flask, Response, jsonify, make_response, render_template, request, send_file, send_from_directory, _POND_WEB_DEPS_ERROR

  try:
    from flask import Flask as _Flask
    from flask import Response as _Response
    from flask import jsonify as _jsonify
    from flask import make_response as _make_response
    from flask import render_template as _render_template
    from flask import request as _request
    from flask import send_file as _send_file
    from flask import send_from_directory as _send_from_directory
  except ModuleNotFoundError as error:
    _POND_WEB_DEPS_ERROR = error
    return False

  Flask = _Flask
  Response = _Response
  jsonify = _jsonify
  make_response = _make_response
  render_template = _render_template
  request = _request
  send_file = _send_file
  send_from_directory = _send_from_directory
  _POND_WEB_DEPS_ERROR = None
  return True


def _install_pond_web_deps():
  global _POND_WEB_DEPS_ERROR

  if not _is_comma_device_runtime():
    return False

  # Local-only dependency policy: prefer bundled repo deps, then existing /data/pond_deps.
  # Do not hit pip/network at runtime.
  if REPO_THIRD_PARTY_PATH.is_dir() and str(REPO_THIRD_PARTY_PATH) not in sys.path:
    sys.path.insert(0, str(REPO_THIRD_PARTY_PATH))
  if os.path.isdir(POND_DEPS_PATH) and POND_DEPS_PATH not in sys.path:
    sys.path.insert(0, POND_DEPS_PATH)

  importlib.invalidate_caches()
  if _import_pond_web_symbols():
    return True

  _POND_WEB_DEPS_ERROR = RuntimeError(
    "Missing local Flask deps (expected in starpilot/third_party or /data/pond_deps)."
  )
  return False


def _ensure_pond_web_deps():
  global _POND_WEB_DEPS_READY

  if _POND_WEB_DEPS_READY:
    return True
  if _import_pond_web_symbols():
    _POND_WEB_DEPS_READY = True
    return True
  if _install_pond_web_deps() and _import_pond_web_symbols():
    _POND_WEB_DEPS_READY = True
    return True
  return False


def extract_tar(archive_path, destination):
  destination_path = Path(destination).resolve()

  with tarfile.open(archive_path, "r:gz") as tar:
    for member in tar.getmembers():
      member_path = (destination_path / member.name).resolve()
      if destination_path not in member_path.parents and member_path != destination_path:
        raise RuntimeError(f"Unsafe tar member path: {member.name}")
    tar.extractall(destination_path)

class ParamsCompat:
  MODEL_KEY_ALIASES = {
    "Model": "DrivingModel",
    "ModelVersion": "DrivingModelVersion",
    "SecOCKey": "SecOCKeys",
  }
  MIRRORED_PARAM_GROUPS = {
    "Model": ("Model", "DrivingModel"),
    "DrivingModel": ("Model", "DrivingModel"),
    "ModelVersion": ("ModelVersion", "DrivingModelVersion"),
    "DrivingModelVersion": ("ModelVersion", "DrivingModelVersion"),
  }

  def __init__(self, params_obj):
    self._params = params_obj

  def _key(self, key):
    return self.MODEL_KEY_ALIASES.get(key, key)

  @staticmethod
  def _to_text(value):
    if value is None:
      return ""
    if isinstance(value, bytes):
      return value.decode("utf-8", errors="replace")
    return str(value)

  def _default_text(self, key):
    try:
      return self._to_text(self._params.get_default_value(key)).strip()
    except Exception:
      return ""

  def _get_raw(self, key, block=False):
    try:
      return self._params.get(key, block=block)
    except TypeError:
      try:
        return self._params.get(key)
      except Exception:
        return None
    except Exception:
      return None

  def _resolve_mirrored_text(self, primary_key, secondary_key, block=False):
    primary_raw = self._get_raw(primary_key, block=block)
    secondary_raw = self._get_raw(secondary_key, block=block)

    if primary_raw is None and secondary_raw is None:
      return None

    primary_val = self._to_text(primary_raw).strip()
    secondary_val = self._to_text(secondary_raw).strip()

    if primary_val == secondary_val:
      return secondary_val or primary_val

    primary_default = self._default_text(primary_key)
    secondary_default = self._default_text(secondary_key)
    primary_non_default = bool(primary_val) and primary_val != primary_default
    secondary_non_default = bool(secondary_val) and secondary_val != secondary_default

    if secondary_non_default and not primary_non_default:
      return secondary_val
    if primary_non_default and not secondary_non_default:
      return primary_val

    # Prefer DrivingModel* values on conflicts since runtime reads those keys.
    return secondary_val or primary_val

  def _put_single(self, key, value):
    expected_type = _get_param_key_type(self._params, key)

    typed_value = value
    if expected_type == ParamKeyType.BOOL:
      if isinstance(value, bool):
        typed_value = value
      elif isinstance(value, (int, float)):
        typed_value = value != 0
      else:
        typed_value = str(value).strip().lower() in ("1", "true", "yes", "on")
    elif expected_type == ParamKeyType.INT:
      typed_value = int(float(value)) if value not in (None, "", b"") else 0
    elif expected_type == ParamKeyType.FLOAT:
      typed_value = float(value) if value not in (None, "", b"") else 0.0
    elif expected_type == ParamKeyType.STRING:
      if isinstance(value, bytes):
        typed_value = value.decode("utf-8", errors="replace")
      elif value is None:
        typed_value = ""
      else:
        typed_value = str(value)

    self._params.put(key, typed_value)

  @staticmethod
  def _coerce_legacy(value, encoding=None):
    # Preserve legacy Params.get behavior:
    # - no encoding => bytes-like payload
    # - encoding set => decoded string payload
    if isinstance(value, bytes):
      if encoding is None:
        return value
      return value.decode(encoding, errors="replace")

    if isinstance(value, (dict, list)):
      serialized = json.dumps(value, separators=(",", ":"))
      if encoding is None:
        return serialized.encode("utf-8")
      return serialized

    if isinstance(value, str):
      if encoding is None:
        return value.encode("utf-8")
      return value

    if isinstance(value, (bool, int, float)):
      text = str(value)
      if encoding is None:
        return text.encode("utf-8")
      return text

    return value

  def get(self, key, encoding=None, default=None, block=False):
    mirrored_keys = self.MIRRORED_PARAM_GROUPS.get(key)
    if mirrored_keys:
      value = self._resolve_mirrored_text(mirrored_keys[0], mirrored_keys[1], block=block)
      if value is None:
        return default
      return self._coerce_legacy(value, encoding)

    resolved_key = self._key(key)
    value = self._get_raw(resolved_key, block=block)

    if value is None:
      return default
    return self._coerce_legacy(value, encoding)

  def get_bool(self, key):
    return self._params.get_bool(self._key(key))

  def put(self, key, value):
    mirrored_keys = self.MIRRORED_PARAM_GROUPS.get(key)
    if mirrored_keys:
      for mirrored_key in dict.fromkeys(mirrored_keys):
        self._put_single(mirrored_key, value)
      return

    self._put_single(self._key(key), value)

  def put_bool(self, key, value):
    self._params.put_bool(self._key(key), bool(value))

  def remove(self, key):
    mirrored_keys = self.MIRRORED_PARAM_GROUPS.get(key)
    if mirrored_keys:
      for mirrored_key in dict.fromkeys(mirrored_keys):
        self._params.remove(mirrored_key)
      return

    self._params.remove(self._key(key))

  def __getattr__(self, attr):
    return getattr(self._params, attr)

_params_raw = Params(return_defaults=True)
_params_live_raw = Params()
_params_memory_raw = Params(memory=True)

def _normalize_default_value(value):
  if isinstance(value, bytes):
    try:
      return value.decode("utf-8")
    except Exception:
      return value
  return value

def _build_default_params():
  defaults = []
  for raw_key in _params_raw.all_keys():
    key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
    defaults.append((
      key,
      _normalize_default_value(_params_raw.get_default_value(raw_key)),
      _get_param_key_type(_params_raw, raw_key),
      _params_raw.get_tuning_level(raw_key),
    ))
  return defaults

starpilot_default_params = _build_default_params()

params = ParamsCompat(_params_raw)
params_memory = ParamsCompat(_params_memory_raw)

try:
  FOOTAGE_PATHS = [
    Paths.log_root(HD=True, raw=True),
    Paths.log_root(konik=True, raw=True),
    Paths.log_root(raw=True),
  ]
except TypeError:
  FOOTAGE_PATHS = [
    "/data/media/0/realdata_HD/",
    "/data/media/0/realdata_konik/",
    str(Paths.log_root()),
  ]

KEYS = {
  "amap1": ("amap1", "", "AMapKey1", "Amap key #1", 39),
  "amap2": ("amap2", "", "AMapKey2", "Amap key #2", 39),
  "public": ("public", "pk.", "MapboxPublicKey", "Public key", 80),
  "secret": ("secret", "sk.", "MapboxSecretKey", "Secret key", 80),
}

TMUX_LOGS_PATH = Path("/data/tmux_logs")

MODEL_DOWNLOAD_PARAM = "ModelToDownload"
MODEL_DOWNLOAD_ALL_PARAM = "DownloadAllModels"
MODEL_DOWNLOAD_PROGRESS_PARAM = "ModelDownloadProgress"
MODEL_CANCEL_DOWNLOAD_PARAM = "CancelModelDownload"
MODEL_SORT_MODE_PARAM = "ModelSortMode"
MODEL_USER_FAVORITES_PARAM = "UserFavorites"
MAPS_DOWNLOAD_PARAM = "DownloadMaps"
MAPS_CANCEL_DOWNLOAD_PARAM = "CancelDownloadMaps"

FINGERPRINT_MAKE_LABELS = [
  "Acura",
  "Audi",
  "Buick",
  "Cadillac",
  "Chevrolet",
  "Chrysler",
  "CUPRA",
  "Dodge",
  "Ford",
  "Genesis",
  "GMC",
  "Holden",
  "Honda",
  "Hyundai",
  "Jeep",
  "Kia",
  "Lexus",
  "Lincoln",
  "MAN",
  "Mazda",
  "Nissan",
  "Peugeot",
  "Ram",
  "Rivian",
  "SEAT",
  "\u0160koda",
  "Subaru",
  "Tesla",
  "Toyota",
  "Volkswagen",
]

FINGERPRINT_MAKE_TO_VALUES_DIR = {
  "acura": "honda",
  "audi": "volkswagen",
  "buick": "gm",
  "cadillac": "gm",
  "chevrolet": "gm",
  "chrysler": "chrysler",
  "cupra": "volkswagen",
  "dodge": "chrysler",
  "ford": "ford",
  "genesis": "hyundai",
  "gmc": "gm",
  "holden": "gm",
  "honda": "honda",
  "hyundai": "hyundai",
  "jeep": "chrysler",
  "kia": "hyundai",
  "lexus": "toyota",
  "lincoln": "ford",
  "man": "volkswagen",
  "mazda": "mazda",
  "nissan": "nissan",
  "peugeot": "psa",
  "ram": "chrysler",
  "rivian": "rivian",
  "seat": "volkswagen",
  "\u0161koda": "volkswagen",
  "subaru": "subaru",
  "tesla": "tesla",
  "toyota": "toyota",
  "volkswagen": "volkswagen",
}

_FINGERPRINT_CARDOCS_RE = re.compile(r'\w*CarDocs\(\s*"([^"]+)"')
_FINGERPRINT_PLATFORM_RE = re.compile(r'(\w+)\s*=\s*\w+\s*\(\s*\[([\s\S]*?)\]\s*,')
_FINGERPRINT_PLATFORM_NAME_RE = re.compile(r'^[A-Z0-9_]+$')
_FINGERPRINT_VALID_NAME_RE = re.compile(r'^[A-Za-z0-9 \u0160.()\-]+$')

_openpilot_root_cache = None
_fingerprint_catalog_cache = None

_fast_update_lock = threading.Lock()
_FAST_UPDATE_TOTAL_STEPS = 5
_FAST_UPDATE_PROGRESS_UPDATE_INTERVAL_S = 5.0
_FAST_UPDATE_REBOOT_NOTICE_SECONDS = 6.0
_FAST_UPDATE_FETCH_TIMEOUT_S = 60
_FAST_BRANCH_SWITCH_FETCH_TIMEOUT_S = 60
_GIT_PROGRESS_PERCENT_RE = re.compile(r'([A-Za-z][A-Za-z /_-]+):\s*([0-9]{1,3})%')
_GIT_SUBMODULE_SECTION_RE = re.compile(r'^\s*\[submodule\s+"[^"]+"\]\s*$', re.MULTILINE)
_TESTING_GROUNDS_SCHEMA_VERSION = SHARED_TESTING_GROUNDS_SCHEMA_VERSION
_TESTING_GROUNDS_SLOT_COUNT = len(SHARED_TESTING_GROUNDS_SLOT_DEFINITIONS)
_TESTING_GROUNDS_DEFAULT_VARIANT = SHARED_DEFAULT_TESTING_GROUND_VARIANT
_TESTING_GROUNDS_VARIANTS = set(SHARED_TESTING_GROUND_VARIANTS) or {_TESTING_GROUNDS_DEFAULT_VARIANT}
_TESTING_GROUNDS_LOCK = threading.Lock()
_TESTING_GROUNDS_STATE_PATH = SHARED_TESTING_GROUNDS_STATE_PATH
# Slot labels live in starpilot/common/testing_grounds.py.
_TESTING_GROUNDS_SLOT_DEFINITIONS = [dict(slot) for slot in SHARED_TESTING_GROUNDS_SLOT_DEFINITIONS]
_TESTING_GROUNDS_VARIANT_LABELS_BY_SLOT = {
  str(slot_id or "").strip(): dict(labels or {})
  for slot_id, labels in SHARED_TESTING_GROUND_VARIANT_LABELS.items()
}
_fast_update_state = {
  "running": False,
  "stage": "idle",
  "message": "",
  "lastError": "",
  "lastBranch": "",
  "lastMode": "",
  "startedAt": 0.0,
  "finishedAt": 0.0,
  "progressStep": 0,
  "progressTotalSteps": _FAST_UPDATE_TOTAL_STEPS,
  "progressStepPercent": 0.0,
  "progressPercent": 0.0,
  "progressLabel": "Idle",
  "progressDetail": "",
}

_PLOTS_POLL_INTERVAL_S = 0.75
_PLOTS_BOOT_STABILIZATION_WINDOW_S = 45.0
_PLOTS_BOOT_POLL_INTERVAL_S = 1.0
_PLOTS_CLIENT_IDLE_TIMEOUT_S = 6.0
_PLOTS_SAMPLE_STALE_AFTER_S = 1.5

_plots_lock = threading.Lock()
_plots_worker_thread = None
_plots_last_client_request_ts = 0.0
_plots_state = {
  "timestamp": 0.0,
  "desiredLateralAccel": 0.0,
  "actualLateralAccel": 0.0,
  "desiredLongitudinalAccel": 0.0,
  "actualLongitudinalAccel": 0.0,
  "controlsActive": False,
  "longitudinalControlActive": False,
  "lateralP": 0.0,
  "lateralI": 0.0,
  "lateralD": 0.0,
  "lateralF": 0.0,
  "longitudinalUpAccelCmd": 0.0,
  "longitudinalUiAccelCmd": 0.0,
  "longitudinalUfAccelCmd": 0.0,
  "speed": 0.0,
  "lateralSource": "curvature",
  "longitudinalSource": "controlsState + livePose",
  "lateralTermsSource": "unknown",
  "longitudinalTermsSource": "controlsState",
  "sampleIndex": 0,
  "lastError": "",
}

_TROUBLESHOOT_PERSONALITY_KEYS = [
  "CustomPersonalities",
  "TrafficPersonalityProfile",
  "TrafficFollow",
  "TrafficJerkAcceleration",
  "TrafficJerkDeceleration",
  "TrafficJerkDanger",
  "TrafficJerkSpeedDecrease",
  "TrafficJerkSpeed",
  "AggressivePersonalityProfile",
  "AggressiveFollow",
  "AggressiveFollowHigh",
  "AggressiveJerkAcceleration",
  "AggressiveJerkDeceleration",
  "AggressiveJerkDanger",
  "AggressiveJerkSpeedDecrease",
  "AggressiveJerkSpeed",
  "StandardPersonalityProfile",
  "StandardFollow",
  "StandardFollowHigh",
  "StandardJerkAcceleration",
  "StandardJerkDeceleration",
  "StandardJerkDanger",
  "StandardJerkSpeedDecrease",
  "StandardJerkSpeed",
  "RelaxedPersonalityProfile",
  "RelaxedFollow",
  "RelaxedFollowHigh",
  "RelaxedJerkAcceleration",
  "RelaxedJerkDeceleration",
  "RelaxedJerkDanger",
  "RelaxedJerkSpeedDecrease",
  "RelaxedJerkSpeed",
]

_TROUBLESHOOT_CEM_KEYS = [
  "ConditionalExperimental",
  "CESpeed",
  "CESpeedLead",
  "CECurves",
  "CELead",
  "CESlowerLead",
  "CEStoppedLead",
  "CEModelStopTime",
  "CESignalSpeed",
  "ShowCEMStatus",
]

_TROUBLESHOOT_ADVANCED_LATERAL_KEYS = [
  "AdvancedLateralTune",
  "SteerDelay",
  "SteerFriction",
  "SteerOffset",
  "SteerKP",
  "SteerLatAccel",
  "SteerRatio",
  "ForceAutoTune",
  "ForceAutoTuneOff",
  "ForceTorqueController",
]

_TROUBLESHOOT_ADVANCED_LONGITUDINAL_KEYS = [
  "AdvancedLongitudinalTune",
  "EVTuning",
  "TruckTuning",
  "CustomAccelProfile",
  *CUSTOM_ACCEL_PROFILE_PARAM_KEYS,
  "LongitudinalActuatorDelay",
  "StartAccel",
  "VEgoStarting",
  "StopAccel",
  "StoppingDecelRate",
  "VEgoStopping",
]

_RUNTIME_DEFAULT_STOCK_KEYS = {
  "SteerDelay": "SteerDelayStock",
  "SteerFriction": "SteerFrictionStock",
  "SteerOffset": "SteerOffsetStock",
  "SteerKP": "SteerKPStock",
  "SteerLatAccel": "SteerLatAccelStock",
  "SteerRatio": "SteerRatioStock",
  "LongitudinalActuatorDelay": "LongitudinalActuatorDelayStock",
  "StartAccel": "StartAccelStock",
  "StopAccel": "StopAccelStock",
  "StoppingDecelRate": "StoppingDecelRateStock",
  "VEgoStarting": "VEgoStartingStock",
  "VEgoStopping": "VEgoStoppingStock",
}

_RUNTIME_DEFAULT_ZERO_OK_KEYS = {
  "SteerOffset",
}

_TROUBLESHOOT_SECTION_DEFINITIONS = [
  {
    "id": "personality_settings",
    "title": "Personality Profile Settings",
    "keys": _TROUBLESHOOT_PERSONALITY_KEYS,
  },
  {
    "id": "model_stop_distance",
    "title": "Model Stop Distance",
    "keys": ["StopDistance"],
  },
  {
    "id": "cem_settings",
    "title": "CEM Settings",
    "keys": _TROUBLESHOOT_CEM_KEYS,
  },
  {
    "id": "advanced_lateral_tuning",
    "title": "Advanced Lateral Tuning",
    "keys": _TROUBLESHOOT_ADVANCED_LATERAL_KEYS,
  },
  {
    "id": "advanced_longitudinal_tuning",
    "title": "Advanced Longitudinal Tuning",
    "keys": _TROUBLESHOOT_ADVANCED_LONGITUDINAL_KEYS,
  },
]

_TROUBLESHOOT_SECTION_BY_ID = {
  section["id"]: section
  for section in _TROUBLESHOOT_SECTION_DEFINITIONS
}

_TROUBLESHOOT_NON_RESETTABLE_SECTION_KEYS = {
  "CustomPersonalities",
  "TrafficPersonalityProfile",
  "AggressivePersonalityProfile",
  "StandardPersonalityProfile",
  "RelaxedPersonalityProfile",
}

def _normalize_fingerprint_make_key(make_value):
  return str(make_value or "").strip().lower()

def _safe_float(value, default=0.0):
  try:
    return float(value)
  except Exception:
    return float(default)

def _get_param_int_value(key, default=0):
  try:
    raw_value = params.get(key)
    if isinstance(raw_value, bytes):
      raw_value = raw_value.decode("utf-8", errors="replace")
    return int(float(str(raw_value or default)))
  except Exception:
    return int(default)

def _enforce_cancel_remap_lkas_lock():
  if not params.get_bool("RemapCancelToDistance"):
    return False

  if _get_param_int_value("LKASButtonControl", 0) == 0:
    return False

  params.put("LKASButtonControl", "0")
  update_starpilot_toggles()
  return True

def _get_system_uptime_seconds():
  try:
    with open("/proc/uptime", "r", encoding="utf-8") as uptime_file:
      return _safe_float((uptime_file.read().split() or ["0"])[0], 0.0)
  except Exception:
    return 0.0

def _is_plots_boot_stabilizing():
  if not params.get_bool("IsOnroad"):
    return False
  return _get_system_uptime_seconds() < _PLOTS_BOOT_STABILIZATION_WINDOW_S

def _extract_plots_speed_mps(controls_state, live_pose):
  try:
    velocity_device = getattr(live_pose, "velocityDevice", None)
    if velocity_device and getattr(velocity_device, "valid", False):
      # Use forward device-frame velocity for plot gating without adding any new subscriptions.
      return abs(_safe_float(getattr(velocity_device, "x", 0.0), 0.0))
  except Exception:
    pass

  return abs(_safe_float(getattr(controls_state, "vPid", 0.0), 0.0))

def _extract_lateral_accel_values(controls_state, speed_mps):
  v_ego = max(0.0, _safe_float(speed_mps))
  speed_sq = v_ego * v_ego

  try:
    lateral_state = controls_state.lateralControlState
    if lateral_state.which() == "torqueState":
      torque_state = lateral_state.torqueState
      desired = _safe_float(getattr(torque_state, "desiredLateralAccel", 0.0))
      actual = _safe_float(getattr(torque_state, "actualLateralAccel", 0.0))
      if abs(desired) > 1e-3 or abs(actual) > 1e-3:
        return desired, actual, "torqueState"
  except Exception:
    pass

  desired_curvature = _safe_float(getattr(controls_state, "desiredCurvature", 0.0))
  actual_curvature = _safe_float(getattr(controls_state, "curvature", 0.0))
  return desired_curvature * speed_sq, actual_curvature * speed_sq, "curvature"

def _extract_longitudinal_accel_values(controls_state, live_pose):
  desired = _safe_float(getattr(controls_state, "aTarget", 0.0))
  source = "controlsState.aTarget + livePose"

  actual = 0.0
  try:
    acceleration_device = getattr(live_pose, "accelerationDevice", None)
    if acceleration_device and getattr(acceleration_device, "valid", False):
      actual = _safe_float(getattr(acceleration_device, "x", 0.0), 0.0)
  except Exception:
    source = "controlsState.aTarget"

  # Fallback only if aTarget is unavailable/legacy-zero while PID terms are present.
  if abs(desired) < 1e-6:
    up = _safe_float(getattr(controls_state, "upAccelCmd", 0.0))
    ui = _safe_float(getattr(controls_state, "uiAccelCmd", 0.0))
    uf = _safe_float(getattr(controls_state, "ufAccelCmd", 0.0))
    pid_sum = up + ui + uf
    if abs(pid_sum) > 1e-6:
      desired = pid_sum
      source = "controlsState PID sum + livePose"

  return desired, actual, source

def _extract_lateral_controller_terms(controls_state):
  terms = {
    "lateralP": 0.0,
    "lateralI": 0.0,
    "lateralD": 0.0,
    "lateralF": 0.0,
  }
  source = "unknown"

  try:
    lateral_state = controls_state.lateralControlState
    which = lateral_state.which()
    if which == "torqueState":
      torque_state = lateral_state.torqueState
      terms["lateralP"] = _safe_float(getattr(torque_state, "p", 0.0))
      terms["lateralI"] = _safe_float(getattr(torque_state, "i", 0.0))
      terms["lateralD"] = _safe_float(getattr(torque_state, "d", 0.0))
      terms["lateralF"] = _safe_float(getattr(torque_state, "f", 0.0))
      source = "torqueState"
    elif which == "pidState":
      pid_state = lateral_state.pidState
      terms["lateralP"] = _safe_float(getattr(pid_state, "p", 0.0))
      terms["lateralI"] = _safe_float(getattr(pid_state, "i", 0.0))
      terms["lateralF"] = _safe_float(getattr(pid_state, "f", 0.0))
      source = "pidState"
    elif which:
      source = which
  except Exception:
    pass

  return terms, source

def _extract_longitudinal_controller_terms(controls_state):
  terms = {
    "longitudinalUpAccelCmd": _safe_float(getattr(controls_state, "upAccelCmd", 0.0)),
    "longitudinalUiAccelCmd": _safe_float(getattr(controls_state, "uiAccelCmd", 0.0)),
    "longitudinalUfAccelCmd": _safe_float(getattr(controls_state, "ufAccelCmd", 0.0)),
  }
  return terms, "controlsState"

def _plots_worker():
  global _plots_worker_thread

  try:
    sm = messaging.SubMaster(["controlsState", "livePose"], poll="controlsState")
  except Exception as exception:
    with _plots_lock:
      _plots_state["lastError"] = str(exception)
      _plots_worker_thread = None
    return

  while True:
    with _plots_lock:
      idle_for = time.monotonic() - _plots_last_client_request_ts

    if idle_for >= _PLOTS_CLIENT_IDLE_TIMEOUT_S:
      break

    try:
      sm.update(0)

      controls_state = sm["controlsState"]
      live_pose = sm["livePose"]
      speed = _extract_plots_speed_mps(controls_state, live_pose)
      controls_active = bool(getattr(controls_state, "active", False))
      long_control_state = int(_safe_float(getattr(controls_state, "longControlState", 0)))
      longitudinal_control_active = controls_active and long_control_state != 0

      desired_lateral, actual_lateral, lateral_source = _extract_lateral_accel_values(controls_state, speed)
      desired_longitudinal, actual_longitudinal, longitudinal_source = _extract_longitudinal_accel_values(controls_state, live_pose)
      lateral_terms, lateral_terms_source = _extract_lateral_controller_terms(controls_state)
      longitudinal_terms, longitudinal_terms_source = _extract_longitudinal_controller_terms(controls_state)

      with _plots_lock:
        _plots_state.update({
          "timestamp": time.time(),
          "desiredLateralAccel": round(desired_lateral, 4),
          "actualLateralAccel": round(actual_lateral, 4),
          "desiredLongitudinalAccel": round(desired_longitudinal, 4),
          "actualLongitudinalAccel": round(actual_longitudinal, 4),
          "controlsActive": controls_active,
          "longitudinalControlActive": longitudinal_control_active,
          "lateralP": round(lateral_terms["lateralP"], 4),
          "lateralI": round(lateral_terms["lateralI"], 4),
          "lateralD": round(lateral_terms["lateralD"], 4),
          "lateralF": round(lateral_terms["lateralF"], 4),
          "longitudinalUpAccelCmd": round(longitudinal_terms["longitudinalUpAccelCmd"], 4),
          "longitudinalUiAccelCmd": round(longitudinal_terms["longitudinalUiAccelCmd"], 4),
          "longitudinalUfAccelCmd": round(longitudinal_terms["longitudinalUfAccelCmd"], 4),
          "speed": round(speed, 4),
          "lateralSource": lateral_source,
          "longitudinalSource": longitudinal_source,
          "lateralTermsSource": lateral_terms_source,
          "longitudinalTermsSource": longitudinal_terms_source,
          "sampleIndex": int(_plots_state.get("sampleIndex", 0)) + 1,
          "lastError": "",
        })
    except Exception as exception:
      with _plots_lock:
        _plots_state["lastError"] = str(exception)

    sleep_interval = _PLOTS_POLL_INTERVAL_S
    if _is_plots_boot_stabilizing():
      sleep_interval = max(_PLOTS_POLL_INTERVAL_S, _PLOTS_BOOT_POLL_INTERVAL_S)
    time.sleep(sleep_interval)

  with _plots_lock:
    _plots_worker_thread = None

def _ensure_plots_worker():
  global _plots_worker_thread, _plots_last_client_request_ts

  with _plots_lock:
    _plots_last_client_request_ts = time.monotonic()
    if _plots_worker_thread and _plots_worker_thread.is_alive():
      return
    _plots_worker_thread = threading.Thread(target=_plots_worker, daemon=True)
    _plots_worker_thread.start()

def _set_fast_update_state(**kwargs):
  with _fast_update_lock:
    _fast_update_state.update(kwargs)

def _get_fast_update_state():
  with _fast_update_lock:
    return dict(_fast_update_state)

def _set_fast_update_progress(step, label, step_percent=0.0, detail=""):
  safe_step = max(1, min(_FAST_UPDATE_TOTAL_STEPS, int(step)))
  safe_step_percent = float(max(0.0, min(100.0, step_percent)))
  overall_percent = (((safe_step - 1) + (safe_step_percent / 100.0)) / _FAST_UPDATE_TOTAL_STEPS) * 100.0

  _set_fast_update_state(
    progressStep=safe_step,
    progressTotalSteps=_FAST_UPDATE_TOTAL_STEPS,
    progressStepPercent=round(safe_step_percent, 1),
    progressPercent=round(overall_percent, 1),
    progressLabel=label,
    progressDetail=detail,
  )

def _parse_git_progress_line(raw_line):
  text = str(raw_line or "").replace("\x1b", "").strip()
  while text.startswith("remote:"):
    text = text[len("remote:"):].strip()

  if not text:
    return None, "", ""

  match = _GIT_PROGRESS_PERCENT_RE.search(text)
  if not match:
    return None, text, ""

  try:
    percent = float(match.group(2))
  except Exception:
    percent = None

  phase = str(match.group(1) or "").strip().lower()
  return percent, text, phase

def _normalize_git_phase_percent(phase, percent):
  safe_percent = max(0.0, min(100.0, float(percent)))
  phase_text = str(phase or "").strip().lower()

  # Git progress lines are per-phase and can hit 100% multiple times before the
  # command actually exits. Map known phases to a monotonic 0..99% envelope.
  if "counting objects" in phase_text:
    return min(20.0, safe_percent * 0.20)
  if "compressing objects" in phase_text:
    return min(45.0, 20.0 + (safe_percent * 0.25))
  if "receiving objects" in phase_text:
    return min(85.0, 45.0 + (safe_percent * 0.40))
  if "resolving deltas" in phase_text:
    return min(99.0, 85.0 + (safe_percent * 0.14))

  # Unknown phase: keep below 100 until the process exits.
  return min(99.0, safe_percent)

_GIT_CA_BUNDLE_CANDIDATES = (
  "/etc/ssl/certs/ca-certificates.crt",
  "/etc/ssl/cert.pem",
  "/usr/local/etc/openssl/cert.pem",
  "/opt/homebrew/etc/openssl@3/cert.pem",
)

def _resolve_git_ca_bundle():
  for env_key in ("GIT_SSL_CAINFO", "SSL_CERT_FILE", "CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE"):
    candidate = os.environ.get(env_key, "")
    if candidate and os.path.isfile(candidate):
      return candidate

  for candidate in _GIT_CA_BUNDLE_CANDIDATES:
    if os.path.isfile(candidate):
      return candidate

  try:
    import certifi  # type: ignore
    candidate = certifi.where()
    if candidate and os.path.isfile(candidate):
      return candidate
  except Exception:
    pass

  return ""

def _git_base_cmd():
  cmd = ["git"]
  ca_bundle = _resolve_git_ca_bundle()
  if ca_bundle:
    cmd += ["-c", f"http.sslCAInfo={ca_bundle}", "-c", "http.sslVerify=true"]
  return cmd

def _git_command_env():
  env = os.environ.copy()
  env["GIT_TERMINAL_PROMPT"] = "0"
  env["GIT_ASKPASS"] = "/bin/false"
  env["SSH_ASKPASS"] = "/bin/false"
  env["GCM_INTERACTIVE"] = "Never"
  if not env.get("GIT_SSH_COMMAND"):
    env["GIT_SSH_COMMAND"] = "ssh -oBatchMode=yes"
  ca_bundle = _resolve_git_ca_bundle()
  if ca_bundle:
    env["GIT_SSL_CAINFO"] = ca_bundle
    env["SSL_CERT_FILE"] = ca_bundle
    env["CURL_CA_BUNDLE"] = ca_bundle
  return env

def _remote_git_check_allowed():
  try:
    return system_time_valid()
  except Exception:
    return True

def _is_deferred_tls_error(exception):
  error_text = str(exception or "").lower()
  if not error_text:
    return False

  tls_markers = (
    "certificate verification failed",
    "ssl certificate problem",
    "x509",
    "cafile",
    "ca cert",
  )
  if any(marker in error_text for marker in tls_markers):
    return not _remote_git_check_allowed()

  return False

def _build_shallow_fetch_args(branch):
  return [
    "-c", "gc.auto=0",
    "-c", "maintenance.auto=false",
    "fetch",
    "--progress",
    "--depth=1",
    "--no-recurse-submodules",
    "origin",
    branch,
  ]

def _run_git_with_progress(repo_path, args, timeout, step, label):
  cmd = [*_git_base_cmd(), *args]

  process = subprocess.Popen(
    cmd,
    cwd=repo_path,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    env=_git_command_env(),
  )

  if process.stdout is None:
    raise RuntimeError("Failed to open git output stream")

  fd = process.stdout.fileno()
  os.set_blocking(fd, False)

  selector = selectors.DefaultSelector()
  selector.register(fd, selectors.EVENT_READ)

  started_at = time.monotonic()
  last_activity_at = started_at
  last_emit_at = 0.0
  last_percent = None
  last_detail = ""
  output_tail = []
  buffer = ""

  def consume_text(text):
    nonlocal buffer
    for char in text:
      if char in ("\r", "\n"):
        if buffer:
          handle_line(buffer)
          buffer = ""
      else:
        buffer += char

  def append_tail(text):
    if not text:
      return
    output_tail.append(text)
    if len(output_tail) > 180:
      del output_tail[:-180]

  def handle_line(text):
    nonlocal last_activity_at, last_emit_at, last_percent, last_detail

    percent, detail, phase = _parse_git_progress_line(text)
    append_tail(detail or text)

    now = time.monotonic()
    last_activity_at = now
    should_emit = False

    if percent is not None:
      safe_percent = _normalize_git_phase_percent(phase, percent)
      if safe_percent in (0.0, 99.0):
        should_emit = True
      elif now - last_emit_at >= _FAST_UPDATE_PROGRESS_UPDATE_INTERVAL_S:
        should_emit = last_percent is None or abs(safe_percent - last_percent) >= 1.0

      if should_emit:
        _set_fast_update_progress(step, label, safe_percent, detail or label)
        last_emit_at = now
        last_percent = safe_percent
        last_detail = detail or label
      else:
        if last_percent is None:
          last_percent = safe_percent
    else:
      if detail and now - last_emit_at >= _FAST_UPDATE_PROGRESS_UPDATE_INTERVAL_S and detail != last_detail:
        fallback_percent = last_percent if last_percent is not None else 0.0
        _set_fast_update_progress(step, label, fallback_percent, detail)
        last_emit_at = now
        last_detail = detail

  try:
    while True:
      now = time.monotonic()
      if timeout and (now - last_activity_at) > timeout:
        try:
          process.kill()
        except Exception:
          pass
        tail = output_tail[-1] if output_tail else ""
        suffix = f" (last output: {tail})" if tail else ""
        raise TimeoutError(f"git {' '.join(args)} stalled for {int(timeout)}s without output{suffix}")

      events = selector.select(timeout=0.5)
      if not events:
        if process.poll() is not None:
          try:
            trailing = os.read(fd, 4096)
          except BlockingIOError:
            trailing = b""
          if trailing:
            last_activity_at = time.monotonic()
            consume_text(trailing.decode("utf-8", errors="replace"))
            continue
          break

        # Heartbeat: if git is quiet (no progress lines), still surface activity.
        now = time.monotonic()
        if now - last_emit_at >= _FAST_UPDATE_PROGRESS_UPDATE_INTERVAL_S:
          if timeout:
            inferred_percent = min(95.0, max(0.0, ((now - started_at) / timeout) * 95.0))
          else:
            inferred_percent = min(95.0, (last_percent or 0.0) + 1.0)
          if last_percent is None or inferred_percent > last_percent:
            last_percent = inferred_percent
          heartbeat_detail = last_detail or f"{label}..."
          _set_fast_update_progress(step, label, last_percent or 0.0, heartbeat_detail)
          last_emit_at = now
        continue

      reached_eof = False
      for _, _ in events:
        try:
          chunk = os.read(fd, 4096)
        except BlockingIOError:
          chunk = b""

        if not chunk:
          # Selector can keep reporting readability on EOF; exit once process ended.
          if process.poll() is not None:
            reached_eof = True
            break
          continue

        last_activity_at = time.monotonic()
        consume_text(chunk.decode("utf-8", errors="replace"))

      if reached_eof:
        break

    if buffer:
      handle_line(buffer)

    return_code = process.wait(timeout=2)
  finally:
    try:
      selector.unregister(fd)
    except Exception:
      pass
    selector.close()
    try:
      process.stdout.close()
    except Exception:
      pass

  if return_code == 0:
    _set_fast_update_progress(step, label, 100.0, last_detail or "Done")

  return return_code, "\n".join(output_tail[-40:])

def _run_git(repo_path, args, timeout=30):
  return subprocess.run(
    [*_git_base_cmd(), *args],
    cwd=repo_path,
    capture_output=True,
    text=True,
    timeout=timeout,
    check=False,
    env=_git_command_env(),
  )

def _git_stdout(repo_path, args, timeout=15):
  result = _run_git(repo_path, args, timeout=timeout)
  if result.returncode != 0:
    stderr = (result.stderr or "").strip() or (result.stdout or "").strip() or "git command failed"
    raise RuntimeError(stderr)
  return (result.stdout or "").strip()

def _is_valid_git_branch_name(repo_path, branch_name):
  branch = str(branch_name or "").strip()
  if not branch or branch.startswith("-") or "\x00" in branch:
    return False

  result = _run_git(repo_path, ["check-ref-format", "--branch", branch], timeout=10)
  return result.returncode == 0

def _list_origin_branches(repo_path, include_remote=True):
  branches = set()
  remote_error = ""

  if include_remote and _remote_git_check_allowed():
    try:
      remote_heads = _git_stdout(repo_path, ["ls-remote", "--heads", "origin"], timeout=25)
      for line in remote_heads.splitlines():
        parts = line.split()
        if len(parts) < 2:
          continue

        ref = parts[1].strip()
        if not ref.startswith("refs/heads/"):
          continue

        branch = ref[len("refs/heads/"):].strip()
        if branch:
          branches.add(branch)
    except Exception as exception:
      if not _is_deferred_tls_error(exception):
        remote_error = str(exception)

  if not branches:
    try:
      local_refs = _git_stdout(
        repo_path,
        ["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"],
        timeout=15,
      )
      for line in local_refs.splitlines():
        ref = line.strip()
        if not ref or ref in ("origin/HEAD",):
          continue
        if ref.startswith("origin/"):
          ref = ref[len("origin/"):]
        if ref.endswith("/HEAD"):
          continue
        if ref:
          branches.add(ref)
    except Exception as exception:
      if not remote_error:
        remote_error = str(exception)

  return sorted(branches, key=lambda branch: branch.lower()), remote_error

def _repo_has_submodule_entries(repo_path):
  gitmodules_path = Path(repo_path) / ".gitmodules"
  if not gitmodules_path.is_file():
    return False

  try:
    content = gitmodules_path.read_text(encoding="utf-8", errors="replace")
  except Exception:
    # If we cannot inspect .gitmodules, stay conservative and try syncing.
    return True

  return bool(_GIT_SUBMODULE_SECTION_RE.search(content))

def _run_submodule_update_if_needed(repo_path, step=4):
  if not _repo_has_submodule_entries(repo_path):
    _set_fast_update_progress(step, "Updating submodules", 100.0, "No submodules configured.")
    return

  _set_fast_update_progress(step, "Updating submodules", 0.0, "Syncing submodules...")
  submodule_rc, submodule_output = _run_git_with_progress(
    repo_path,
    ["submodule", "update", "--init", "--recursive", "--depth=1", "--progress"],
    timeout=240,
    step=step,
    label="Updating submodules",
  )
  if submodule_rc != 0:
    raise RuntimeError(submodule_output.strip() or "git submodule update failed")

def _finish_update_and_reboot(message):
  _set_fast_update_progress(5, "Rebooting device", 100.0, "Update complete. Please wait for device to reboot.")
  _set_fast_update_state(
    running=False,
    stage="rebooting",
    message=message,
    finishedAt=time.time(),
  )
  # Keep the service online briefly so the UI can fetch and render the reboot notice.
  time.sleep(_FAST_UPDATE_REBOOT_NOTICE_SECONDS)
  HARDWARE.reboot()

def _set_fast_update_error_state(message, exception):
  error_text = str(exception).strip() or "Unknown error"
  _set_fast_update_state(
    running=False,
    stage="error",
    message=message,
    lastError=error_text,
    finishedAt=time.time(),
    progressStep=0,
    progressTotalSteps=_FAST_UPDATE_TOTAL_STEPS,
    progressStepPercent=0.0,
    progressPercent=0.0,
    progressLabel="Failed",
    progressDetail="Update failed. See Last Error below.",
  )

def _collect_fast_update_info(include_remote=True):
  repo_path = str(_get_openpilot_root())

  branch = ""
  local_commit = ""
  remote_commit = ""
  update_available = False
  remote_error = ""
  origin_remote = ""
  commits_url = ""

  try:
    branch = _git_stdout(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    local_commit = _git_stdout(repo_path, ["rev-parse", "HEAD"])
    try:
      origin_remote = _git_stdout(repo_path, ["config", "--get", "remote.origin.url"])
    except Exception:
      origin_remote = ""
  except Exception as exception:
    return {
      "repoPath": repo_path,
      "branch": branch,
      "localCommit": local_commit,
      "remoteCommit": remote_commit,
      "updateAvailable": False,
      "remoteError": str(exception),
      "originRemote": origin_remote,
      "commitsUrl": commits_url,
    }

  if origin_remote:
    remote = origin_remote.strip()
    if remote.startswith("git@github.com:"):
      remote = "https://github.com/" + remote.split(":", 1)[1]
    elif remote.startswith("ssh://git@github.com/"):
      remote = "https://github.com/" + remote.split("ssh://git@github.com/", 1)[1]
    elif remote.startswith("http://github.com/"):
      remote = "https://github.com/" + remote.split("http://github.com/", 1)[1]

    if remote.startswith("https://github.com/"):
      remote = remote.rstrip("/")
      if remote.endswith(".git"):
        remote = remote[:-4]
      if branch:
        commits_url = f"{remote}/commits/{quote(branch, safe='')}/"

  if branch and include_remote and _remote_git_check_allowed():
    try:
      remote_raw = _git_stdout(repo_path, ["ls-remote", "--heads", "origin", branch], timeout=20)
      if remote_raw:
        remote_commit = remote_raw.split()[0]
        update_available = bool(local_commit and remote_commit and local_commit != remote_commit)
    except Exception as exception:
      if not _is_deferred_tls_error(exception):
        remote_error = str(exception)

  return {
    "repoPath": repo_path,
    "branch": branch,
    "localCommit": local_commit,
    "remoteCommit": remote_commit,
    "updateAvailable": update_available,
    "remoteError": remote_error,
    "originRemote": origin_remote,
    "commitsUrl": commits_url,
  }

def _fast_update_worker():
  started_at = time.time()
  repo_path = str(_get_openpilot_root())

  try:
    _set_fast_update_progress(1, "Preparing update", 10.0, "Resolving active branch...")
    branch = _git_stdout(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    _set_fast_update_progress(1, "Preparing update", 100.0, f"Branch: {branch}")
    _set_fast_update_state(
      running=True,
      stage="updating",
      message=f"Applying shallow update on '{branch}'...",
      lastError="",
      lastBranch=branch,
      lastMode="fetch-reset",
      startedAt=started_at,
      finishedAt=0.0,
    )

    _set_fast_update_progress(2, "Fetching branch snapshot", 0.0, "Fetching latest shallow commit...")
    fetch_rc, fetch_output = _run_git_with_progress(
      repo_path,
      _build_shallow_fetch_args(branch),
      timeout=_FAST_UPDATE_FETCH_TIMEOUT_S,
      step=2,
      label="Fetching branch snapshot",
    )
    if fetch_rc != 0:
      raise RuntimeError(fetch_output.strip() or "git fetch failed")

    _set_fast_update_progress(3, "Applying fetched commit", 20.0, "Resetting repository to fetched head...")
    reset = _run_git(repo_path, ["reset", "--hard", "FETCH_HEAD"], timeout=120)
    if reset.returncode != 0:
      raise RuntimeError((reset.stderr or reset.stdout or "git reset failed").strip())
    _set_fast_update_progress(3, "Applying fetched commit", 100.0, "Repository reset complete.")

    _run_submodule_update_if_needed(repo_path, step=4)
    _finish_update_and_reboot(
      "Update successful. Device is rebooting now. Please wait for reconnection."
    )
  except Exception as exception:
    _set_fast_update_error_state("Fast update failed.", exception)

def _branch_switch_worker(target_branch):
  started_at = time.time()
  repo_path = str(_get_openpilot_root())

  try:
    _set_fast_update_progress(1, "Preparing branch switch", 10.0, f"Target: {target_branch}")
    current_branch = _git_stdout(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    _set_fast_update_progress(1, "Preparing branch switch", 100.0, f"{current_branch} -> {target_branch}")
    _set_fast_update_state(
      running=True,
      stage="switching",
      message=f"Switching to '{target_branch}' with shallow fetch...",
      lastError="",
      lastBranch=target_branch,
      lastMode="branch-switch",
      startedAt=started_at,
      finishedAt=0.0,
    )

    _set_fast_update_progress(2, "Fetching branch snapshot", 0.0, f"Fetching '{target_branch}' from origin...")
    fetch_rc, fetch_output = _run_git_with_progress(
      repo_path,
      _build_shallow_fetch_args(target_branch),
      timeout=_FAST_BRANCH_SWITCH_FETCH_TIMEOUT_S,
      step=2,
      label="Fetching branch snapshot",
    )
    if fetch_rc != 0:
      raise RuntimeError(fetch_output.strip() or f"git fetch failed for '{target_branch}'")

    _set_fast_update_progress(3, "Switching branch", 20.0, f"Checking out '{target_branch}'...")
    checkout = _run_git(repo_path, ["checkout", "--force", "-B", target_branch, "FETCH_HEAD"], timeout=120)
    if checkout.returncode != 0:
      raise RuntimeError((checkout.stderr or checkout.stdout or "git checkout failed").strip())

    reset = _run_git(repo_path, ["reset", "--hard", "FETCH_HEAD"], timeout=120)
    if reset.returncode != 0:
      raise RuntimeError((reset.stderr or reset.stdout or "git reset failed").strip())

    _run_git(repo_path, ["branch", "--set-upstream-to", f"origin/{target_branch}", target_branch], timeout=30)
    _set_fast_update_progress(3, "Switching branch", 100.0, f"Now on '{target_branch}'.")

    _run_submodule_update_if_needed(repo_path, step=4)
    _finish_update_and_reboot(
      f"Switched to '{target_branch}'. Device is rebooting now. Please wait for reconnection."
    )
  except Exception as exception:
    _set_fast_update_error_state("Fast branch switch failed.", exception)

def _get_openpilot_root():
  global _openpilot_root_cache
  if _openpilot_root_cache is not None:
    return _openpilot_root_cache

  for parent in Path(__file__).resolve().parents:
    if (parent / "opendbc" / "car").is_dir() or (parent / "selfdrive" / "car").is_dir():
      _openpilot_root_cache = parent
      return _openpilot_root_cache

  # Fallback to repo root shape used in this tree.
  _openpilot_root_cache = Path(__file__).resolve().parents[3]
  return _openpilot_root_cache

def _extract_fingerprint_models_for_make(make_key):
  source_make = FINGERPRINT_MAKE_TO_VALUES_DIR.get(make_key, make_key)
  root = _get_openpilot_root()
  values_candidates = [
    root / "opendbc" / "car" / source_make / "values.py",
    root / "selfdrive" / "car" / source_make / "values.py",
  ]
  values_path = next((path for path in values_candidates if path.is_file()), None)
  if values_path is None:
    return []

  try:
    content = values_path.read_text(encoding="utf-8", errors="replace")
  except Exception:
    return []

  content = re.sub(r'#[^\n]*', "", content)
  content = re.sub(r'footnotes=\[[^\]]*\],\s*', "", content)

  models = []
  seen = set()

  for platform_match in _FINGERPRINT_PLATFORM_RE.finditer(content):
    platform_name = platform_match.group(1)
    if not _FINGERPRINT_PLATFORM_NAME_RE.match(platform_name):
      continue

    platform_section = platform_match.group(2)
    for name_match in _FINGERPRINT_CARDOCS_RE.finditer(platform_section):
      car_name = name_match.group(1).strip()
      if " " not in car_name:
        continue
      if not _FINGERPRINT_VALID_NAME_RE.match(car_name):
        continue

      if car_name.split(" ", 1)[0].lower() != make_key:
        continue

      dedupe_key = (car_name, platform_name)
      if dedupe_key in seen:
        continue
      seen.add(dedupe_key)
      models.append({"value": platform_name, "label": car_name})

  models.sort(key=lambda entry: entry["label"].lower())
  return models

def _get_fingerprint_catalog():
  global _fingerprint_catalog_cache
  if _fingerprint_catalog_cache is not None:
    return _fingerprint_catalog_cache

  make_options = [{"value": label, "label": label} for label in FINGERPRINT_MAKE_LABELS]
  make_keys = [_normalize_fingerprint_make_key(label) for label in FINGERPRINT_MAKE_LABELS]
  make_label_by_key = {key: label for key, label in zip(make_keys, FINGERPRINT_MAKE_LABELS)}

  models_by_make = {}
  all_models = []
  seen_all = set()
  model_to_label = {}
  model_to_make = {}
  label_to_model = {}

  for make_key in make_keys:
    make_label = make_label_by_key.get(make_key, make_key.title())
    entries = _extract_fingerprint_models_for_make(make_key)

    models_by_make[make_key] = entries
    for entry in entries:
      model_value = entry["value"]
      model_label = entry["label"]

      model_to_label.setdefault(model_value, model_label)
      model_to_make.setdefault(model_value, make_label)
      label_to_model.setdefault(model_label, model_value)

      dedupe_key = (model_label, model_value)
      if dedupe_key in seen_all:
        continue
      seen_all.add(dedupe_key)

      all_models.append({
        "value": model_value,
        "label": model_label,
        "make": make_label,
      })

  all_models.sort(key=lambda entry: entry["label"].lower())

  _fingerprint_catalog_cache = {
    "makes": make_options,
    "models_by_make": models_by_make,
    "all_models": all_models,
    "make_label_by_key": make_label_by_key,
    "model_to_label": model_to_label,
    "model_to_make": model_to_make,
    "label_to_model": label_to_model,
  }
  return _fingerprint_catalog_cache

def read_legacy_param_file(key, default_value=""):
  try:
    value_path = Path(params.get_param_path(key))
    if value_path.is_file():
      return value_path.read_text(encoding="utf-8").strip() or default_value
  except Exception:
    pass
  return default_value

def write_legacy_param_file(key, value):
  value_path = Path(params.get_param_path(key))
  value_path.parent.mkdir(parents=True, exist_ok=True)
  tmp_path = value_path.with_name(f".tmp_{value_path.name}")
  tmp_path.write_text(str(value), encoding="utf-8")
  os.replace(tmp_path, value_path)

_layout_type_overrides = None
_layout_param_metadata = None

def _get_layout_param_metadata():
  global _layout_param_metadata
  if _layout_param_metadata is None:
    try:
      layout_path = os.path.join(os.path.dirname(__file__), "assets", "components", "tools", "device_settings_layout.json")
      with open(layout_path) as f:
        layout_data = json.load(f)
      _layout_param_metadata = {
        p["key"]: p
        for section in layout_data
        for p in section.get("params", [])
        if "key" in p
      }
    except Exception:
      _layout_param_metadata = {}
  return _layout_param_metadata

def _get_layout_type_overrides():
  global _layout_type_overrides
  if _layout_type_overrides is None:
    layout_param_metadata = _get_layout_param_metadata()
    _layout_type_overrides = {
      key: param_data.get("data_type")
      for key, param_data in layout_param_metadata.items()
      if param_data.get("data_type")
    }
  return _layout_type_overrides

_cached_allowed_keys = None
_cached_param_types = None
_cached_default_values = None
_cached_static_default_values = None

def _get_param_type_info():
  global _cached_allowed_keys, _cached_param_types
  if _cached_allowed_keys is None:
    _cached_allowed_keys = {k for k, _, _, _ in starpilot_default_params if k not in EXCLUDED_KEYS}

    types = {}
    for k, default_val, _, _ in starpilot_default_params:
      if k in _cached_allowed_keys:
        if default_val in ("0", "1", b"0", b"1") or isinstance(default_val, bool):
          types[k] = bool
        elif isinstance(default_val, float) or (isinstance(default_val, str) and "." in default_val and default_val.replace(".", "", 1).isdigit()):
          types[k] = float
        elif isinstance(default_val, int) or (isinstance(default_val, str) and default_val.isdigit()):
          types[k] = int
        else:
          types[k] = str

    for k, dt in _get_layout_type_overrides().items():
      if k in types and dt in ("int", "float") and types[k] == bool:
        types[k] = float if dt == "float" else int

    # Keep legacy aliases editable for older payloads/UI clients.
    alias_to_key = {
      "Model": "DrivingModel",
      "ModelVersion": "DrivingModelVersion",
      "SecOCKey": "SecOCKeys",
    }
    for alias_key, real_key in alias_to_key.items():
      if real_key in _cached_allowed_keys:
        _cached_allowed_keys.add(alias_key)
        types[alias_key] = types.get(real_key, str)

    _cached_param_types = types
  return _cached_allowed_keys, _cached_param_types

def _get_static_default_param_values():
  global _cached_static_default_values
  if _cached_static_default_values is None:
    _cached_static_default_values = {
      key: default_val
      for key, default_val, _, _ in starpilot_default_params
      if key not in EXCLUDED_KEYS
    }
  return _cached_static_default_values

def _get_default_param_values():
  default_values = dict(_get_static_default_param_values())
  default_values.update(_get_runtime_default_param_overrides())
  return default_values

def _coerce_param_value(raw_value, value_type):
  safe_type = value_type or str

  if safe_type == bool:
    if isinstance(raw_value, bool):
      return raw_value
    if isinstance(raw_value, bytes):
      raw_value = raw_value.decode("utf-8", errors="replace")
    return str(raw_value or "").strip() in ("1", "true", "True")

  if safe_type == float:
    if raw_value in (None, "", b""):
      return 0.0
    try:
      if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8", errors="replace")
      return float(str(raw_value).strip())
    except Exception:
      return 0.0

  if safe_type == int:
    if raw_value in (None, "", b""):
      return 0
    try:
      if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8", errors="replace")
      return int(float(str(raw_value).strip()))
    except Exception:
      return 0

  if isinstance(raw_value, bytes):
    return raw_value.decode("utf-8", errors="replace")
  return str(raw_value or "")

def _safe_params_get(key, encoding=None, default=None):
  try:
    if encoding is not None:
      return params.get(key, encoding=encoding)
    return params.get(key)
  except Exception:
    return default

def _safe_params_get_live_raw(key, default=None, block=False):
  try:
    return _params_live_raw.get(key, block=block)
  except Exception:
    return default

def _safe_params_get_bool(key, default=False):
  try:
    return params.get_bool(key)
  except Exception:
    return bool(default)

def _is_blank_param_raw(raw_value):
  if raw_value is None:
    return True
  if isinstance(raw_value, bytes):
    return len(raw_value.strip()) == 0
  if isinstance(raw_value, str):
    return len(raw_value.strip()) == 0
  return False

def _has_runtime_default_value(key, raw_value):
  if _is_blank_param_raw(raw_value):
    return False

  if key in _RUNTIME_DEFAULT_ZERO_OK_KEYS:
    return True

  try:
    if isinstance(raw_value, bytes):
      raw_value = raw_value.decode("utf-8", errors="replace")
    return float(str(raw_value).strip()) != 0.0
  except Exception:
    return True

def _get_runtime_default_param_overrides():
  overrides = {}
  static_defaults = _get_static_default_param_values()

  for key, stock_key in _RUNTIME_DEFAULT_STOCK_KEYS.items():
    stock_raw = _safe_params_get_live_raw(stock_key)
    if _has_runtime_default_value(key, stock_raw):
      overrides[key] = stock_raw
      overrides[stock_key] = stock_raw

  cp_bytes = _safe_params_get_live_raw("CarParamsPersistent")
  if cp_bytes:
    try:
      with car.CarParams.from_bytes(cp_bytes) as cp:
        overrides["EVTuning"] = default_ev_tuning_enabled(cp)

        car_param_defaults = {
          "SteerDelay": getattr(cp, "steerActuatorDelay", None),
          "SteerRatio": getattr(cp, "steerRatio", None),
          "LongitudinalActuatorDelay": getattr(cp, "longitudinalActuatorDelay", None),
          "StartAccel": getattr(cp, "startAccel", None),
          "StopAccel": getattr(cp, "stopAccel", None),
          "StoppingDecelRate": getattr(cp, "stoppingDecelRate", None),
          "VEgoStarting": getattr(cp, "vEgoStarting", None),
          "VEgoStopping": getattr(cp, "vEgoStopping", None),
        }

        for key, value in car_param_defaults.items():
          if key in overrides or value is None:
            continue
          if key not in _RUNTIME_DEFAULT_ZERO_OK_KEYS and float(value) == 0.0:
            continue
          overrides[key] = value
    except Exception:
      pass

  ev_tuning_raw = _safe_params_get_live_raw("EVTuning")
  truck_tuning_raw = _safe_params_get_live_raw("TruckTuning")
  acceleration_profile_raw = _safe_params_get_live_raw("AccelerationProfile")

  ev_tuning = _coerce_param_value(
    ev_tuning_raw if not _is_blank_param_raw(ev_tuning_raw) else overrides.get("EVTuning", static_defaults.get("EVTuning", "0")),
    bool,
  )
  truck_tuning = _coerce_param_value(
    truck_tuning_raw if not _is_blank_param_raw(truck_tuning_raw) else static_defaults.get("TruckTuning", "0"),
    bool,
  )
  if truck_tuning:
    ev_tuning = False

  acceleration_profile = normalize_acceleration_profile(
    acceleration_profile_raw if not _is_blank_param_raw(acceleration_profile_raw) else static_defaults.get("AccelerationProfile", "0")
  )
  overrides.update(build_custom_accel_profile_defaults(acceleration_profile, ev_tuning, truck_tuning))

  return overrides

def _get_current_param_value(key, value_type, defaults_lookup=None):
  if key == CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY:
    return _get_custom_accel_profile_initialized()

  if key in CUSTOM_ACCEL_PROFILE_PARAM_KEYS and not _get_custom_accel_profile_initialized():
    if defaults_lookup is None:
      defaults_lookup = _get_default_param_values()
    return _coerce_param_value(defaults_lookup.get(key), value_type)

  raw_value = _safe_params_get_live_raw(key)
  if _is_blank_param_raw(raw_value):
    if defaults_lookup is None:
      defaults_lookup = _get_default_param_values()
    raw_value = defaults_lookup.get(key)
  return _coerce_param_value(raw_value, value_type)


def _get_custom_accel_profile_initialized():
  raw_values = {
    key: _safe_params_get_live_raw(key)
    for key in CUSTOM_ACCEL_PROFILE_PARAM_KEYS
  }
  return custom_accel_profile_is_initialized(
    _safe_params_get_live_raw(CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY),
    raw_values,
  )

def _serialize_param_write_value(raw_value):
  if isinstance(raw_value, bool):
    return "1" if raw_value else "0"
  if isinstance(raw_value, bytes):
    return raw_value.decode("utf-8", errors="replace")
  return str(raw_value or "")

def _apply_cellular_metered_setting(metered_enabled):
  """Apply GsmMetered changes to active NetworkManager GSM profiles."""
  if not shutil.which("nmcli"):
    return {"profiles": [], "warnings": ["nmcli not found; parameter saved but modem profile was not updated."]}

  metered_mode = "unknown" if bool(metered_enabled) else "no"
  updated_profiles = []
  warnings = []

  try:
    list_result = subprocess.run(
      ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
      capture_output=True, text=True, timeout=10, check=False
    )
  except Exception as error:
    return {"profiles": [], "warnings": [f"Failed to list network profiles: {error}"]}

  if list_result.returncode != 0:
    stderr = (list_result.stderr or "").strip()
    return {"profiles": [], "warnings": [f"Failed to list network profiles: {stderr or 'unknown error'}"]}

  gsm_profiles = []
  for line in (list_result.stdout or "").splitlines():
    line = line.strip()
    if not line:
      continue

    try:
      name, conn_type = line.rsplit(":", 1)
    except ValueError:
      continue

    if conn_type.strip() == "gsm" and name.strip():
      gsm_profiles.append(name.strip())

  for profile_name in gsm_profiles:
    try:
      result = subprocess.run(
        ["nmcli", "connection", "modify", profile_name, "connection.metered", metered_mode],
        capture_output=True, text=True, timeout=10, check=False
      )
      if result.returncode == 0:
        updated_profiles.append(profile_name)
      else:
        stderr = (result.stderr or "").strip()
        warnings.append(f"Failed to update '{profile_name}': {stderr or 'unknown error'}")
    except Exception as error:
      warnings.append(f"Failed to update '{profile_name}': {error}")

  # Re-activate active GSM profiles so the new metered setting takes effect immediately.
  try:
    active_result = subprocess.run(
      ["nmcli", "-t", "-f", "NAME,TYPE,STATE", "connection", "show", "--active"],
      capture_output=True, text=True, timeout=10, check=False
    )

    if active_result.returncode == 0:
      for line in (active_result.stdout or "").splitlines():
        line = line.strip()
        if not line:
          continue
        try:
          name, conn_type, state = line.rsplit(":", 2)
        except ValueError:
          continue

        if conn_type.strip() != "gsm" or state.strip() != "activated":
          continue

        profile_name = name.strip()
        if not profile_name:
          continue

        subprocess.run(["nmcli", "connection", "down", profile_name], capture_output=True, text=True, timeout=10, check=False)
        subprocess.run(["nmcli", "connection", "up", profile_name], capture_output=True, text=True, timeout=20, check=False)
  except Exception as error:
    warnings.append(f"Failed to cycle active GSM connection: {error}")

  return {"profiles": updated_profiles, "warnings": warnings}

def _format_longitudinal_personality(value):
  mapping = {
    "0": "Aggressive",
    "1": "Standard",
    "2": "Relaxed",
  }
  text = str(value or "").strip()
  if text in mapping:
    return mapping[text]
  return f"Unknown ({text})" if text else "Unknown"

def _resolve_troubleshoot_current_value(key, value_type, default_values):
  safe_type = value_type or str

  if safe_type == bool:
    raw_value = _safe_params_get_live_raw(key)
    if not _is_blank_param_raw(raw_value):
      return _coerce_param_value(raw_value, safe_type)

    default_raw_value = default_values.get(key)
    if not _is_blank_param_raw(default_raw_value):
      return _coerce_param_value(default_raw_value, safe_type)

    return _safe_params_get_bool(key)

  raw_value = _safe_params_get_live_raw(key)
  if not _is_blank_param_raw(raw_value):
    return _coerce_param_value(raw_value, safe_type)

  stock_key = f"{key}Stock"
  if stock_key in default_values:
    stock_raw_value = _safe_params_get_live_raw(stock_key)
    if not _is_blank_param_raw(stock_raw_value):
      return _coerce_param_value(stock_raw_value, safe_type)

  default_raw_value = default_values.get(key)
  if not _is_blank_param_raw(default_raw_value):
    return _coerce_param_value(default_raw_value, safe_type)

  return _coerce_param_value(raw_value, safe_type)

def _resolve_troubleshoot_default_value(key, value_type, default_values):
  safe_type = value_type or str
  default_raw_value = default_values.get(key)
  if not _is_blank_param_raw(default_raw_value):
    return _coerce_param_value(default_raw_value, safe_type)

  stock_key = f"{key}Stock"
  if stock_key in default_values:
    stock_current_raw = _safe_params_get_live_raw(stock_key)
    if not _is_blank_param_raw(stock_current_raw):
      return _coerce_param_value(stock_current_raw, safe_type)

    stock_default_raw = default_values.get(stock_key)
    if not _is_blank_param_raw(stock_default_raw):
      return _coerce_param_value(stock_default_raw, safe_type)

  return _coerce_param_value(default_raw_value, safe_type)

def _normalize_live_delay_status(status):
  status_text = str(status or "").strip().lower()
  if status_text in {"estimated", "unestimated", "invalid"}:
    return status_text

  try:
    if status == log.LiveDelayData.Status.estimated:
      return "estimated"
    if status == log.LiveDelayData.Status.unestimated:
      return "unestimated"
    if status == log.LiveDelayData.Status.invalid:
      return "invalid"
  except Exception:
    pass

  return status_text

def _get_steer_delay_learned_text():
  live_delay_bytes = _safe_params_get_live_raw("LiveDelay")
  if not live_delay_bytes:
    return "Unavailable"

  current_cp_bytes = _safe_params_get_live_raw("CarParamsPersistent")
  previous_cp_bytes = _safe_params_get_live_raw("CarParamsPrevRoute")
  if current_cp_bytes and previous_cp_bytes:
    try:
      with car.CarParams.from_bytes(current_cp_bytes) as current_cp, car.CarParams.from_bytes(previous_cp_bytes) as previous_cp:
        current_fingerprint = str(getattr(current_cp, "carFingerprint", "") or "")
        previous_fingerprint = str(getattr(previous_cp, "carFingerprint", "") or "")
        if current_fingerprint and previous_fingerprint and current_fingerprint != previous_fingerprint:
          return "Unavailable"
    except Exception:
      pass

  try:
    live_delay = messaging.log_from_bytes(live_delay_bytes, log.Event).liveDelay
  except Exception:
    return "Unavailable"

  estimate = _safe_float(getattr(live_delay, "lateralDelayEstimate", 0.0), 0.0)
  cal_perc = int(max(0, min(100, _safe_float(getattr(live_delay, "calPerc", 0), 0))))
  status = _normalize_live_delay_status(getattr(live_delay, "status", ""))

  if status == "estimated":
    return f"Complete ({estimate:.2f}s)"
  if status == "invalid":
    return f"Invalid ({estimate:.2f}s)"
  if status == "unestimated":
    return f"Learning {cal_perc}% ({estimate:.2f}s)"

  return f"{estimate:.2f}s"

def _get_troubleshoot_learned_values():
  return {
    "SteerDelay": _get_steer_delay_learned_text(),
  }

def _get_safety_snapshot_text():
  cp_bytes = params.get("CarParamsPersistent")
  if not cp_bytes:
    return "Unavailable"

  try:
    with car.CarParams.from_bytes(cp_bytes) as cp:
      safety_configs = list(getattr(cp, "safetyConfigs", []))
      if not safety_configs:
        return "Unavailable"

      entries = []
      for config in safety_configs:
        model = str(getattr(config, "safetyModel", "unknown"))
        safety_param = int(getattr(config, "safetyParam", 0))
        entries.append(f"{model} ({safety_param} / 0x{safety_param:X})")

      return ", ".join(entries) if entries else "Unavailable"
  except Exception:
    return "Unavailable"

def _get_fingerprint_snapshot_text():
  cp_bytes = params.get("CarParamsPersistent")
  cp_fingerprint = ""
  try:
    if cp_bytes:
      with car.CarParams.from_bytes(cp_bytes) as cp:
        cp_fingerprint = str(getattr(cp, "carFingerprint", "") or "").strip()
  except Exception:
    cp_fingerprint = ""

  model_name = str(params.get("CarModelName", encoding="utf-8") or "").strip()
  model_value = str(params.get("CarModel", encoding="utf-8") or "").strip()

  if model_name and model_value:
    return f"{model_name} ({model_value})"
  if model_name:
    return model_name
  if model_value:
    return model_value
  if cp_fingerprint:
    return cp_fingerprint
  return "Unknown"

def _snapshot_bool_text(value):
  if value is True:
    return "Yes"
  if value is False:
    return "No"
  return "Unavailable"

def _build_vehicle_fault_status():
  unavailable_items = [
    {"label": "Cruise Fault", "value": "Unavailable", "severity": "neutral"},
    {"label": "LKAS Fault", "value": "Unavailable", "severity": "neutral"},
    {"label": "CAN Valid", "value": "Unavailable", "severity": "neutral"},
    {"label": "Cruise Available", "value": "Unavailable", "severity": "neutral"},
    {"label": "Cruise Engaged", "value": "Unavailable", "severity": "neutral"},
  ]

  is_onroad = params.get_bool("IsOnroad")
  unavailable_summary = "Vehicle fault status is unavailable while offroad."
  unavailable_severity = "neutral"
  if is_onroad:
    unavailable_summary = "Waiting for live vehicle fault status..."
    unavailable_severity = "warn"

  try:
    sm = messaging.SubMaster(["carState"], poll="carState")
    sm.update(100)
    has_live_car_state = sm.seen["carState"] and sm.alive["carState"] and sm.valid["carState"]
    if not has_live_car_state:
      return {
        "available": False,
        "summary": unavailable_summary,
        "summarySeverity": unavailable_severity,
        "items": unavailable_items,
      }

    car_state = sm["carState"]
    cruise_state = getattr(car_state, "cruiseState", None)

    cruise_faulted = bool(getattr(car_state, "accFaulted", False))
    steer_fault_temporary = bool(getattr(car_state, "steerFaultTemporary", False))
    steer_fault_permanent = bool(getattr(car_state, "steerFaultPermanent", False))
    can_valid = bool(getattr(car_state, "canValid", False))
    cruise_available = bool(getattr(cruise_state, "available", False)) if cruise_state is not None else None
    cruise_enabled = bool(getattr(cruise_state, "enabled", False)) if cruise_state is not None else None

    if steer_fault_permanent:
      lkas_fault_value = "Permanent"
      lkas_fault_severity = "fault"
    elif steer_fault_temporary:
      lkas_fault_value = "Temporary"
      lkas_fault_severity = "warn"
    else:
      lkas_fault_value = "Clear"
      lkas_fault_severity = "ok"

    active_statuses = []
    if cruise_faulted:
      active_statuses.append("cruise fault")
    if steer_fault_permanent:
      active_statuses.append("permanent LKAS fault")
    elif steer_fault_temporary:
      active_statuses.append("temporary LKAS fault")
    if not can_valid:
      active_statuses.append("CAN invalid")

    if active_statuses:
      summary = "Active status: " + ", ".join(active_statuses) + "."
      summary_severity = "fault" if ("cruise fault" in active_statuses or "permanent LKAS fault" in active_statuses or "CAN invalid" in active_statuses) else "warn"
    else:
      summary = "No active cruise or LKAS faults detected."
      summary_severity = "ok"

    return {
      "available": True,
      "summary": summary,
      "summarySeverity": summary_severity,
      "items": [
        {"label": "Cruise Fault", "value": "Faulted" if cruise_faulted else "Clear", "severity": "fault" if cruise_faulted else "ok"},
        {"label": "LKAS Fault", "value": lkas_fault_value, "severity": lkas_fault_severity},
        {"label": "CAN Valid", "value": "Yes" if can_valid else "No", "severity": "ok" if can_valid else "fault"},
        {"label": "Cruise Available", "value": "Yes" if cruise_available else "No", "severity": "ok" if cruise_available else "neutral"},
        {"label": "Cruise Engaged", "value": "Yes" if cruise_enabled else "No", "severity": "ok" if cruise_enabled else "neutral"},
      ],
    }
  except Exception:
    return {
      "available": False,
      "summary": unavailable_summary,
      "summarySeverity": unavailable_severity,
      "items": unavailable_items,
    }

def _get_starpilot_toggles_snapshot():
  raw_toggles = _safe_params_get_live_raw("StarPilotToggles")
  if not raw_toggles:
    return {}

  try:
    if isinstance(raw_toggles, bytes):
      raw_toggles = raw_toggles.decode("utf-8", errors="replace")
    parsed = json.loads(str(raw_toggles) or "{}")
    return parsed if isinstance(parsed, dict) else {}
  except Exception:
    return {}

def _get_hardware_snapshot_items():
  starpilot_toggles = _get_starpilot_toggles_snapshot()

  has_bsm = None
  has_openpilot_longitudinal = None
  has_pedal = False
  has_sascm = bool(starpilot_toggles.get("has_sascm", False))
  has_radar = None
  has_sdsu = bool(starpilot_toggles.get("has_sdsu", False))
  has_sng = None
  has_zss = bool(starpilot_toggles.get("has_zss", False))
  can_use_pedal = None
  can_use_sdsu = None
  is_bolt = False

  cp_bytes = _safe_params_get_live_raw("CarParamsPersistent")
  if cp_bytes:
    try:
      with car.CarParams.from_bytes(cp_bytes) as cp:
        car_fingerprint = str(getattr(cp, "carFingerprint", "") or "")
        car_make = str(getattr(cp, "brand", "") or getattr(cp, "carName", "") or "")

        has_bsm = bool(getattr(cp, "enableBsm", False))
        has_openpilot_longitudinal = bool(getattr(cp, "openpilotLongitudinalControl", False))
        has_pedal = bool(getattr(cp, "enableGasInterceptorDEPRECATED", False))
        has_sascm = car_make == "gm" and bool(getattr(cp, "flags", 0) & GMFlags.SASCM.value)
        has_radar = not bool(getattr(cp, "radarUnavailable", False))
        has_sdsu = bool(starpilot_toggles.get("has_sdsu", has_sdsu))
        has_sng = bool(getattr(cp, "autoResumeSng", False))
        has_zss = bool(starpilot_toggles.get("has_zss", has_zss))
        is_bolt = car_fingerprint.startswith("CHEVROLET_BOLT")

        if PC and (car_make == "mock" or car_fingerprint == "MOCK"):
          fallback_make = str(starpilot_toggles.get("car_make", "") or "gm")
          fallback_model = str(starpilot_toggles.get("car_model", "") or "CHEVROLET_BOLT_ACC_2022_2023")
          has_pedal = bool(starpilot_toggles.get("has_pedal", True))
          has_sascm = bool(starpilot_toggles.get("has_sascm", has_sascm))
          has_sdsu = bool(starpilot_toggles.get("has_sdsu", has_sdsu))
          has_zss = bool(starpilot_toggles.get("has_zss", has_zss))
          is_bolt = fallback_model.startswith("CHEVROLET_BOLT")
          if fallback_make == "gm" and has_openpilot_longitudinal is None:
            has_openpilot_longitudinal = True
    except Exception:
      pass
  elif PC:
    fallback_model = str(starpilot_toggles.get("car_model", "") or "CHEVROLET_BOLT_ACC_2022_2023")
    has_pedal = bool(starpilot_toggles.get("has_pedal", True))
    has_sascm = bool(starpilot_toggles.get("has_sascm", has_sascm))
    has_sdsu = bool(starpilot_toggles.get("has_sdsu", has_sdsu))
    has_zss = bool(starpilot_toggles.get("has_zss", has_zss))
    is_bolt = fallback_model.startswith("CHEVROLET_BOLT")

  if can_use_pedal is None:
    can_use_pedal = has_pedal or is_bolt
  if can_use_sdsu is None:
    can_use_sdsu = has_sdsu

  fpcp_bytes = _safe_params_get_live_raw("StarPilotCarParamsPersistent")
  if fpcp_bytes:
    try:
      fpcp = messaging.log_from_bytes(fpcp_bytes, custom.StarPilotCarParams)
      can_use_pedal = bool(getattr(fpcp, "canUsePedal", can_use_pedal))
      can_use_sdsu = bool(getattr(fpcp, "canUseSDSU", can_use_sdsu))
    except Exception:
      pass

  detected = []
  if has_pedal:
    detected.append("comma Pedal")
  if has_sascm:
    detected.append("SASCM")
  if has_sdsu:
    detected.append("SDSU")
  if has_zss:
    detected.append("ZSS")

  return [
    {"id": "hardware_detected", "label": "Hardware Detected", "value": ", ".join(detected) if detected else "None", "resettable": False},
    {"id": "pedal_detected", "label": "Pedal Detected", "value": _snapshot_bool_text(has_pedal), "resettable": False},
    {"id": "sascm_detected", "label": "SASCM Detected", "value": _snapshot_bool_text(has_sascm), "resettable": False},
    {"id": "sdsu_detected", "label": "SDSU Detected", "value": _snapshot_bool_text(has_sdsu), "resettable": False},
    {"id": "zss_detected", "label": "ZSS Detected", "value": _snapshot_bool_text(has_zss), "resettable": False},
    {"id": "blind_spot_support", "label": "Blind Spot Support", "value": _snapshot_bool_text(has_bsm), "resettable": False},
    {"id": "openpilot_longitudinal_support", "label": "openpilot Longitudinal Support", "value": _snapshot_bool_text(has_openpilot_longitudinal), "resettable": False},
    {"id": "pedal_support", "label": "comma Pedal Support", "value": _snapshot_bool_text(can_use_pedal), "resettable": False},
    {"id": "radar_support", "label": "Radar Support", "value": _snapshot_bool_text(has_radar), "resettable": False},
    {"id": "sdsu_support", "label": "SDSU Support", "value": _snapshot_bool_text(can_use_sdsu), "resettable": False},
    {"id": "sng_support", "label": "Stop-and-Go Support", "value": _snapshot_bool_text(has_sng), "resettable": False},
  ]

def _build_troubleshoot_section_payload(section_definition, value_types, default_values, layout_metadata, learned_values):
  section_keys = [str(key).strip() for key in section_definition.get("keys", []) if str(key).strip()]
  items = []

  for key in section_keys:
    param_metadata = layout_metadata.get(key, {}) if isinstance(layout_metadata.get(key, {}), dict) else {}
    value_type = value_types.get(key, str)
    data_type = str(param_metadata.get("data_type") or "").strip().lower()
    if data_type == "float":
      value_type = float
    elif data_type == "int":
      value_type = int
    elif data_type == "bool":
      value_type = bool

    label = str(param_metadata.get("label") or key)
    try:
      current_value = _resolve_troubleshoot_current_value(key, value_type, default_values)
      default_value = _resolve_troubleshoot_default_value(key, value_type, default_values)
    except Exception:
      current_value = "Unavailable"
      default_value = "n/a"

    items.append({
      "key": key,
      "label": label,
      "value": current_value,
      "defaultValue": default_value,
      "learnedValue": learned_values.get(key),
    })

  return {
    "id": section_definition["id"],
    "title": section_definition["title"],
    "resettable": True,
    "hasLearnedColumn": any(item.get("learnedValue") not in (None, "") for item in items),
    "items": items,
  }

def _build_troubleshoot_payload():
  _, value_types = _get_param_type_info()
  default_values = _get_default_param_values()
  learned_values = _get_troubleshoot_learned_values()
  layout_metadata = _get_layout_param_metadata()

  longitudinal_personality_raw = _safe_params_get("LongitudinalPersonality", encoding="utf-8", default="") or ""
  snapshot_items = [
    {
      "id": "safety_param",
      "label": "Safety Param",
      "value": _get_safety_snapshot_text(),
      "resettable": False,
    },
    {
      "id": "fingerprint",
      "label": "Fingerprint",
      "value": _get_fingerprint_snapshot_text(),
      "resettable": False,
    },
    *_get_hardware_snapshot_items(),
    {
      "id": "driving_model",
      "label": "Current Driving Model",
      "value": str(_safe_params_get("Model", encoding="utf-8", default="") or "Unknown"),
      "resettable": False,
    },
    {
      "id": "selected_personality_profile",
      "label": "Selected Personality Profile",
      "value": _format_longitudinal_personality(longitudinal_personality_raw),
      "resettable": False,
    },
  ]

  sections = [
    _build_troubleshoot_section_payload(section_definition, value_types, default_values, layout_metadata, learned_values)
    for section_definition in _TROUBLESHOOT_SECTION_DEFINITIONS
  ]

  return {
    "vehicleStatus": _build_vehicle_fault_status(),
    "snapshot": snapshot_items,
    "sections": sections,
    "isOnroad": params.get_bool("IsOnroad"),
  }

def _reset_troubleshoot_section(section_id):
  section_definition = _TROUBLESHOOT_SECTION_BY_ID.get(str(section_id or "").strip())
  if section_definition is None:
    raise ValueError("Unknown troubleshoot section.")

  allowed_keys, _ = _get_param_type_info()
  default_values = _get_default_param_values()
  is_onroad = params.get_bool("IsOnroad")
  blocked_onroad_keys = {"Model", "AlwaysOnLateral", "ForceTorqueController", "NNFF", "NNFFLite"}

  updated_keys = []
  skipped_keys = []

  for key in section_definition.get("keys", []):
    if key in _TROUBLESHOOT_NON_RESETTABLE_SECTION_KEYS:
      skipped_keys.append({"key": key, "reason": "preserved by design"})
      continue

    if key not in allowed_keys:
      skipped_keys.append({"key": key, "reason": "not editable"})
      continue

    if is_onroad and key in blocked_onroad_keys:
      skipped_keys.append({"key": key, "reason": "blocked while onroad"})
      continue

    if key not in default_values:
      skipped_keys.append({"key": key, "reason": "default unavailable"})
      continue

    params.put(key, _serialize_param_write_value(default_values[key]))
    updated_keys.append(key)

  if updated_keys:
    update_starpilot_toggles()

  return {
    "sectionId": section_definition["id"],
    "sectionTitle": section_definition["title"],
    "updatedKeys": updated_keys,
    "skippedKeys": skipped_keys,
    "updatedCount": len(updated_keys),
    "skippedCount": len(skipped_keys),
  }

def _extract_testing_ground_variant_labels(slot_data, include_default=True):
  labels = {}
  if not isinstance(slot_data, dict):
    slot_data = {}

  raw_variant_labels = slot_data.get("variantLabels")
  if isinstance(raw_variant_labels, dict):
    for raw_variant, raw_label in raw_variant_labels.items():
      variant = str(raw_variant or "").strip().upper()
      label = str(raw_label or "").strip()
      if len(variant) == 1 and variant.isalpha() and label:
        labels[variant] = label

  for key, value in slot_data.items():
    if not isinstance(key, str) or not key.endswith("Label"):
      continue
    variant = key[:-5].strip().upper()
    if len(variant) != 1 or not variant.isalpha():
      continue
    label = str(value or "").strip()
    if label:
      labels[variant] = label

  if include_default and _TESTING_GROUNDS_DEFAULT_VARIANT not in labels:
    labels[_TESTING_GROUNDS_DEFAULT_VARIANT] = _TESTING_GROUNDS_DEFAULT_VARIANT

  return dict(sorted(labels.items()))

def _get_testing_ground_variant_labels(slot_id, slot=None):
  normalized_slot_id = str(slot_id or "").strip()
  labels = {}

  shared_labels = _TESTING_GROUNDS_VARIANT_LABELS_BY_SLOT.get(normalized_slot_id, {})
  if shared_labels:
    labels.update({
      str(variant or "").strip().upper(): str(label or "").strip()
      for variant, label in shared_labels.items()
      if len(str(variant or "").strip().upper()) == 1 and str(variant or "").strip().upper().isalpha() and str(label or "").strip()
    })
  else:
    labels.update(_extract_testing_ground_variant_labels(slot if isinstance(slot, dict) else {}, include_default=False))

  if _TESTING_GROUNDS_DEFAULT_VARIANT not in labels:
    labels[_TESTING_GROUNDS_DEFAULT_VARIANT] = _TESTING_GROUNDS_DEFAULT_VARIANT

  return dict(sorted(labels.items()))

def _normalize_testing_ground_variant(slot_id, variant, slot=None):
  allowed_variants = set(_get_testing_ground_variant_labels(slot_id, slot).keys()) or set(_TESTING_GROUNDS_VARIANTS)
  normalized_variant = str(variant or "").strip().upper()
  return normalized_variant if normalized_variant in allowed_variants else _TESTING_GROUNDS_DEFAULT_VARIANT

def _build_testing_ground_fallback_slots():
  definitions_by_id = {}

  for definition in _TESTING_GROUNDS_SLOT_DEFINITIONS:
    if not isinstance(definition, dict):
      continue

    slot_id = str(definition.get("id") or "").strip()
    if not slot_id:
      continue

    variant_labels = _get_testing_ground_variant_labels(slot_id, definition)
    definitions_by_id[slot_id] = {
      "id": slot_id,
      "name": str(definition.get("name") or "Unused").strip() or "Unused",
      "description": str(definition.get("description") or "").strip(),
      "variantLabels": variant_labels,
      "aLabel": variant_labels.get("A", "A"),
      "bLabel": variant_labels.get("B", "B"),
    }

  slots = []
  for slot_number in range(1, _TESTING_GROUNDS_SLOT_COUNT + 1):
    slot_id = str(slot_number)
    default_variant_labels = {
      _TESTING_GROUNDS_DEFAULT_VARIANT: _TESTING_GROUNDS_DEFAULT_VARIANT,
      "B": "B",
    }
    fallback_slot = definitions_by_id.get(slot_id, {
      "id": slot_id,
      "name": "Unused",
      "description": "",
      "variantLabels": default_variant_labels,
      "aLabel": "A",
      "bLabel": "B",
    })
    slot = dict(fallback_slot)
    slot_variant_labels = _get_testing_ground_variant_labels(slot_id, slot)
    slot["variantLabels"] = slot_variant_labels
    slot["aLabel"] = slot_variant_labels.get("A", slot.get("aLabel", "A"))
    slot["bLabel"] = slot_variant_labels.get("B", slot.get("bLabel", "B"))
    slots.append(slot)

  return slots

def _default_testing_grounds_state():
  return {
    "schemaVersion": _TESTING_GROUNDS_SCHEMA_VERSION,
    "activeSlot": "1",
    "activeVariant": _TESTING_GROUNDS_DEFAULT_VARIANT,
    "slots": _build_testing_ground_fallback_slots(),
  }

def _normalize_testing_ground_slot(raw_slot, fallback_slot):
  slot = dict(fallback_slot)
  if not isinstance(raw_slot, dict):
    return slot

  # Slot metadata (name/description) should always come from shared definitions.
  # Persisted state only owns active selection and per-slot variant labels.
  slot["name"] = str(slot.get("name") or "Unused").strip() or "Unused"
  slot["description"] = str(slot.get("description") or "").strip()

  variant_labels = _get_testing_ground_variant_labels(slot.get("id"), raw_slot)
  if not variant_labels:
    variant_labels = _get_testing_ground_variant_labels(slot.get("id"), slot)
  slot["variantLabels"] = variant_labels
  slot["aLabel"] = variant_labels.get("A", slot.get("aLabel", "A"))
  slot["bLabel"] = variant_labels.get("B", slot.get("bLabel", "B"))

  return slot

def _load_testing_grounds_state_unlocked():
  state = _default_testing_grounds_state()
  fallback_slots = state["slots"]
  fallback_slot_ids = {slot["id"] for slot in fallback_slots}
  needs_write = False

  raw_state = {}
  try:
    raw_state = json.loads(_TESTING_GROUNDS_STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw_state, dict):
      raw_state = {}
      needs_write = True
  except FileNotFoundError:
    needs_write = True
  except Exception:
    needs_write = True

  if raw_state.get("schemaVersion") != _TESTING_GROUNDS_SCHEMA_VERSION:
    needs_write = True

  raw_slots = raw_state.get("slots")
  if isinstance(raw_slots, list):
    raw_by_id = {}
    for index, raw_slot in enumerate(raw_slots, start=1):
      if not isinstance(raw_slot, dict):
        needs_write = True
        continue

      slot_id = str(raw_slot.get("id") or "").strip() or str(index)
      if slot_id not in fallback_slot_ids:
        needs_write = True
        continue

      raw_by_id[slot_id] = raw_slot

    normalized_slots = []
    for fallback_slot in fallback_slots:
      slot_id = fallback_slot["id"]
      normalized_slots.append(_normalize_testing_ground_slot(raw_by_id.get(slot_id), fallback_slot))
      if slot_id not in raw_by_id:
        needs_write = True

    state["slots"] = normalized_slots
  else:
    needs_write = True

  active_slot = str(raw_state.get("activeSlot") or "").strip()
  if active_slot not in fallback_slot_ids:
    active_slot = state["activeSlot"]
    needs_write = True
  state["activeSlot"] = active_slot

  active_slot_data = _find_testing_ground_slot(state, active_slot)
  raw_active_variant = str(raw_state.get("activeVariant") or "").strip().upper()
  active_variant = _normalize_testing_ground_variant(active_slot, raw_active_variant, active_slot_data)
  if raw_active_variant != active_variant:
    needs_write = True
  state["activeVariant"] = active_variant

  return state, needs_write

def _write_testing_grounds_state_unlocked(state):
  _TESTING_GROUNDS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
  tmp_path = _TESTING_GROUNDS_STATE_PATH.with_name(f".tmp_{_TESTING_GROUNDS_STATE_PATH.name}")
  tmp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
  os.replace(tmp_path, _TESTING_GROUNDS_STATE_PATH)

def _get_testing_grounds_state():
  with _TESTING_GROUNDS_LOCK:
    state, needs_write = _load_testing_grounds_state_unlocked()
    if needs_write:
      try:
        _write_testing_grounds_state_unlocked(state)
      except Exception:
        pass
    return state

def _is_unused_testing_ground_slot(slot):
  name = str(slot.get("name") or "").strip().lower()
  return name == "unused" or name.startswith("unused ")

def _find_testing_ground_slot(state, slot_id):
  for slot in state.get("slots", []):
    if str(slot.get("id") or "").strip() == slot_id:
      return slot
  return {}

def _serialize_testing_grounds_state(state):
  slots = state.get("slots", [])
  active_slot_id = str(state.get("activeSlot") or "").strip()
  active_slot = _find_testing_ground_slot(state, active_slot_id)
  active_variant = _normalize_testing_ground_variant(active_slot_id, state.get("activeVariant"), active_slot)
  active_variant_labels = _get_testing_ground_variant_labels(active_slot_id, active_slot)

  return {
    "schemaVersion": state.get("schemaVersion", _TESTING_GROUNDS_SCHEMA_VERSION),
    "activeSlot": active_slot_id,
    "activeVariant": active_variant,
    "activeVariantLabel": active_variant_labels.get(active_variant, active_variant),
    "activeSlotName": active_slot.get("name", active_slot_id),
    "slots": slots,
    "slotSummaryLines": [f"{slot.get('id', '?')}. {slot.get('name', 'Unused')}" for slot in slots],
    "selectableSlots": [slot for slot in slots if not _is_unused_testing_ground_slot(slot)],
  }

def _set_testing_ground_selection(slot_id, variant):
  normalized_slot_id = str(slot_id or "").strip()
  requested_variant = str(variant or "").strip().upper()

  with _TESTING_GROUNDS_LOCK:
    state, _ = _load_testing_grounds_state_unlocked()
    slot_ids = {slot["id"] for slot in state["slots"]}
    if normalized_slot_id not in slot_ids:
      raise ValueError(f"Unknown testing ground slot '{normalized_slot_id}'.")

    slot = _find_testing_ground_slot(state, normalized_slot_id)
    allowed_variant_labels = _get_testing_ground_variant_labels(normalized_slot_id, slot)
    if requested_variant not in allowed_variant_labels:
      allowed_variants = ", ".join(sorted(allowed_variant_labels.keys()))
      raise ValueError(f"Variant must be one of: {allowed_variants}.")

    normalized_variant = _normalize_testing_ground_variant(normalized_slot_id, requested_variant, slot)
    state["activeSlot"] = normalized_slot_id
    state["activeVariant"] = normalized_variant
    _write_testing_grounds_state_unlocked(state)
    return state

def _default_longitudinal_maneuver_status():
  return {
    "state": "idle",
    "phase": "",
    "paddleMode": "auto",
    "maneuver": "",
    "runIndex": 0,
    "runTotal": 0,
    "stepIndex": 0,
    "stepTotal": 0,
    "phaseStepIndex": 0,
    "phaseStepTotal": 0,
    "uiShow": False,
    "uiSize": "small",
    "uiText1": "Long Maneuvers",
    "uiText2": "",
    "updatedAtSec": 0.0,
    "history": [],
  }

def _load_longitudinal_maneuver_status():
  status = _default_longitudinal_maneuver_status()
  raw = params.get("LongitudinalManeuverStatus", encoding="utf-8") or ""
  if raw:
    try:
      payload = json.loads(raw)
      if isinstance(payload, dict):
        status.update(payload)
    except Exception:
      pass

  history = status.get("history")
  if not isinstance(history, list):
    history = []
  status["history"] = [str(line) for line in history if str(line).strip()][-120:]

  try:
    status["updatedAtSec"] = float(status.get("updatedAtSec") or 0.0)
  except Exception:
    status["updatedAtSec"] = 0.0

  return status

def _save_longitudinal_maneuver_status(status):
  status_copy = dict(status)
  history = status_copy.get("history")
  if not isinstance(history, list):
    history = []
  status_copy["history"] = [str(line) for line in history if str(line).strip()][-120:]
  status_copy["updatedAtSec"] = float(status_copy.get("updatedAtSec") or time.time())
  params.put("LongitudinalManeuverStatus", json.dumps(status_copy, separators=(",", ":")))
  return status_copy

def _append_longitudinal_maneuver_history(status, line):
  if not line:
    return status
  history = list(status.get("history", []))
  history.append(str(line))
  status["history"] = history[-120:]
  return status

def _serialize_longitudinal_maneuver_status(status):
  updated_at = _safe_float(status.get("updatedAtSec"), 0.0)
  age_seconds = max(0.0, time.time() - updated_at) if updated_at > 0 else None
  mode_enabled = params.get_bool("LongitudinalManeuverMode")
  paddle_mode = params.get("LongitudinalManeuverPaddleMode", encoding="utf-8") or str(status.get("paddleMode") or "auto")
  return {
    **status,
    "modeEnabled": mode_enabled,
    "paddleMode": paddle_mode,
    "isOnroad": params.get_bool("IsOnroad"),
    "isEngaged": params.get_bool("IsEngaged"),
    "updatedAgeSec": age_seconds,
  }

def _set_longitudinal_maneuver_mode(enabled):
  status = _load_longitudinal_maneuver_status()
  if enabled:
    params.put_bool("LongitudinalManeuverMode", True)
    params.put("LongitudinalManeuverPaddleMode", "auto")
    status.update({
      "state": "armed",
      "phase": "",
      "maneuver": "",
      "runIndex": 0,
      "runTotal": 0,
      "stepIndex": 0,
      "phaseStepIndex": 0,
      "uiShow": True,
      "uiSize": "small",
      "uiText1": "Long Maneuvers Armed",
      "uiText2": "Engage with SET to start the test suite.",
      "updatedAtSec": time.time(),
    })
    _append_longitudinal_maneuver_history(status, "Armed from The Pond. Engage with SET to start.")
  else:
    params.put_bool("LongitudinalManeuverMode", False)
    params.put("LongitudinalManeuverPaddleMode", "auto")
    status.update({
      "state": "stopped",
      "uiShow": True,
      "uiSize": "small",
      "uiText1": "Long Maneuvers Stopped",
      "uiText2": "Test mode disabled.",
      "updatedAtSec": time.time(),
    })
    _append_longitudinal_maneuver_history(status, "Stopped from The Pond.")

  return _save_longitudinal_maneuver_status(status)

def setup(app):
  model_status_debug = {
    "last_signature": None,
    "last_log_time": 0.0,
    "last_empty_catalog_log_time": 0.0,
  }

  @app.errorhandler(404)
  def not_found(_):
    response = make_response(render_template("index.html"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

  @app.route("/", methods=["GET"])
  def index():
    response = make_response(render_template("index.html"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

  @app.route("/manifest.json", methods=["GET"])
  @app.route("/assets/manifest.json", methods=["GET"])
  def manifest():
    manifest_path = Path(app.static_folder) / "manifest.json"
    if manifest_path.is_file():
      return send_file(str(manifest_path), mimetype="application/manifest+json")

    # Fallback so the browser doesn't keep logging noisy 404s.
    return jsonify({
      "name": "Galaxy",
      "short_name": "Galaxy",
      "display": "standalone",
      "start_url": "/",
      "background_color": "#000000",
      "theme_color": "#8b6cc5",
      "icons": [],
    }), 200

  @app.route("/api/car_features_check", methods=["GET"])
  def car_features_check():
    tool = request.args.get("tool")
    try:
      with car.CarParams.from_bytes(params.get("CarParamsPersistent")) as cp:
        if tool == "doors":
          return jsonify({"result": HARDWARE.get_device_type() != "tici" and cp.carName == "toyota"})
        elif tool == "tsk":
          return jsonify({"result": cp.secOcRequired})
    except Exception:
      pass
    return jsonify({"result": False})

  @app.route("/api/doors/lock", methods=["POST"])
  def lock_doors():
    can_parser = CANParser("toyota_nodsu_pt_generated", [("DOOR_LOCKS", 3)], bus=0)
    can_sock = messaging.sub_sock("can", timeout=100)

    while True:
      with Panda(disable_checks=True) as panda:
        if not params.get_bool("IsOnroad"):
          panda.set_safety_mode(panda.SAFETY_TOYOTA)
        panda.can_send(0x750, LOCK_CMD, 0)

      time.sleep(1)

      lock_status = get_lock_status(can_parser, can_sock)
      if lock_status == 0:
        break

    return {"message": "Doors locked!"}

  @app.route("/api/doors/unlock", methods=["POST"])
  def unlock_doors():
    can_parser = CANParser("toyota_nodsu_pt_generated", [("DOOR_LOCKS", 3)], bus=0)
    can_sock = messaging.sub_sock("can", timeout=100)

    while True:
      with Panda(disable_checks=True) as panda:
        if not params.get_bool("IsOnroad"):
          panda.set_safety_mode(panda.SAFETY_TOYOTA)
        panda.can_send(0x750, UNLOCK_CMD, 0)

      time.sleep(1)

      lock_status = get_lock_status(can_parser, can_sock)
      if lock_status != 0:
        break

    return {"message": "Doors unlocked!"}

  @app.route("/api/error_logs", methods=["GET"])
  def get_error_logs():
    if request.accept_mimetypes["text/html"]:
      return render_template("v2/error-logs.jinja", active="error_logs")

    if request.accept_mimetypes["application/json"]:
      files = utilities.list_file(ERROR_LOGS_PATH)
      filtered = [file for file in files if not file.startswith("error")]
      return filtered, 200

  @app.route("/api/error_logs/delete_all", methods=["DELETE"])
  def delete_all_error_logs():
    for f in os.listdir(ERROR_LOGS_PATH):
      delete_file(os.path.join(ERROR_LOGS_PATH, f))
    return {"message": "All error logs deleted!"}, 200

  @app.route("/api/error_logs/<filename>", methods=["DELETE"])
  def delete_error_log(filename):
    delete_file(os.path.join(ERROR_LOGS_PATH, filename))
    return {"message": "Error log deleted!"}

  @app.route("/api/error_logs/<filename>", methods=["GET"])
  def get_error_log(filename):
    with open(os.path.join(ERROR_LOGS_PATH, filename)) as file:
      return file.read(), 200, {"Content-Type": "text/plain; charset=utf-8"}

  @app.route("/api/navigation", methods=["DELETE"])
  def clear_navigation():
    params.remove("NavDestination")
    return {"message": "Destination cleared"}

  @app.route("/api/navigation", methods=["GET"])
  def navigation():
    last_position = json.loads(
      params.get("LastGPSPosition", encoding="utf8") or
      "{\"latitude\": 51.276824158421331, \"longitude\": 30.221928335547232, \"altitude\": 111.0}"
    )

    return {
      "amap1Key": params.get("AMapKey1", encoding="utf8") or "",
      "amap2Key": params.get("AMapKey2", encoding="utf8") or "",
      "destination": params.get("NavDestination", encoding="utf8") or "",
      "isMetric": params.get_bool("IsMetric"),
      "lastPosition": {
        "latitude": str(last_position["latitude"]),
        "longitude": str(last_position["longitude"])
      },
      "mapboxPublic": params.get("MapboxPublicKey", encoding="utf8") or "",
      "mapboxSecret": params.get("MapboxSecretKey", encoding="utf8") or "",
      "previousDestinations": params.get("ApiCache_NavDestinations", encoding="utf8") or "",
    }

  @app.route("/api/navigation", methods=["POST"])
  def set_navigation():
    params.remove("NavDestination")

    time.sleep(1)

    params.put("NavDestination", json.dumps(request.json))
    return {"message": "Destination set"}

  @app.route("/api/navigation/favorite", methods=["DELETE"])
  def remove_favorite_destination():
    to_remove = request.json or {}

    existing = json.loads(params.get("FavoriteDestinations", encoding="utf8") or "[]")
    fid = to_remove.get("id")
    if fid:
      favorites = [f for f in existing if f.get("id") != fid]
    else:
      favorites = [
        f for f in existing
        if not (
          f.get("routeId") == to_remove.get("routeId") and
          f.get("latitude") == to_remove.get("latitude") and
          f.get("longitude") == to_remove.get("longitude") and
          f.get("name") == to_remove.get("name")
        )
      ]

    params.put("FavoriteDestinations", json.dumps(favorites))
    return jsonify(message="Destination removed from favorites!")

  @app.route("/api/navigation/favorite", methods=["GET"])
  def list_favorite_destinations():
    favorites = json.loads(params.get("FavoriteDestinations", encoding="utf8") or "[]")
    changed = False
    for f in favorites:
      if "id" not in f:
        raw = f"{f.get('longitude')},{f.get('latitude')}|{f.get('routeId') or ''}|{f.get('name') or ''}"
        f["id"] = hashlib.sha1(raw.encode()).hexdigest()
        changed = True
    if changed:
      params.put("FavoriteDestinations", json.dumps(favorites))
    return jsonify(favorites=favorites)

  @app.route("/api/navigation/favorite", methods=["POST"])
  def add_favorite_destination():
    new_fav = request.json or {}

    if "id" not in new_fav:
      raw = f"{new_fav.get('longitude')},{new_fav.get('latitude')}|{new_fav.get('routeId') or ''}|{new_fav.get('name') or ''}"
      new_fav["id"] = hashlib.sha1(raw.encode()).hexdigest()

    existing = json.loads(params.get("FavoriteDestinations", encoding="utf8") or "[]")
    if not any(f.get("id") == new_fav["id"] for f in existing):
      existing.append(new_fav)

    params.put("FavoriteDestinations", json.dumps(existing))
    return {"message": "Destination added to favorites!"}

  @app.route("/api/navigation/favorite/rename", methods=["POST"])
  def rename_favorite_destination():
    data = request.json or {}
    fid = data.get("id")
    route_id_to_rename = data.get("routeId")
    new_name = data.get("name")
    is_home = data.get("is_home")
    is_work = data.get("is_work")

    if not fid and not route_id_to_rename:
      return jsonify({"error": "Missing id or routeId"}), 400

    existing_favorites = json.loads(params.get("FavoriteDestinations", encoding="utf8") or "[]")

    if is_home:
      for favorite in existing_favorites:
        favorite.pop("is_home", None)
    if is_work:
      for favorite in existing_favorites:
        favorite.pop("is_work", None)

    found = False
    for favorite in existing_favorites:
      if (fid and favorite.get("id") == fid) or (not fid and favorite.get("routeId") == route_id_to_rename):
        if new_name:
          favorite["name"] = new_name

        if is_home is not None:
          if is_home:
            favorite["is_home"] = True
            favorite.pop("is_work", None)
          else:
            favorite.pop("is_home", None)

        if is_work is not None:
          if is_work:
            favorite["is_work"] = True
            favorite.pop("is_home", None)
          else:
            favorite.pop("is_work", None)

        found = True
        break

    if not found:
      return jsonify({"error": "Favorite not found"}), 404

    params.put("FavoriteDestinations", json.dumps(existing_favorites))
    return jsonify(message="Favorite updated successfully!")

  @app.route("/api/navigation_key", methods=["DELETE"])
  def delete_navigation_key():
    meta = KEYS.get(request.args.get("type"))
    params.remove(meta[2])
    return jsonify(message=f"{meta[3]} deleted successfully!")

  @app.route("/api/navigation_key", methods=["POST"])
  def set_navigation_keys():
    data = request.get_json() or {}

    saved = []
    for meta in KEYS.values():
      raw = (data.get(meta[0]) or "").strip()
      if not raw:
        continue

      full = raw if raw.startswith(meta[1]) else meta[1] + raw
      if len(full) < meta[4]:
        return jsonify(error=f"{meta[3]} is invalid or too short..."), 400

      params.put(meta[2], full)
      saved.append(meta[3])

    if not saved:
      return jsonify(error="Nothing to update..."), 400

    return jsonify(message=f"{', '.join(saved)} saved successfully!")

  @app.route("/api/fingerprints/makes", methods=["GET"])
  def get_fingerprint_makes():
    return jsonify(_get_fingerprint_catalog()["makes"]), 200

  @app.route("/api/fingerprints/models", methods=["GET"])
  def get_fingerprint_models():
    catalog = _get_fingerprint_catalog()
    make_key = _normalize_fingerprint_make_key(
      request.args.get("make") or params.get("CarMake", encoding="utf-8") or ""
    )

    models = catalog["models_by_make"].get(make_key) if make_key else catalog["all_models"]
    if not models:
      models = catalog["all_models"]

    return jsonify(models), 200

  @app.route("/api/params", methods=["GET", "PUT"])
  def get_param():
    if request.method == "PUT":
      data = request.get_json()
      if not data or "key" not in data or "value" not in data:
        return jsonify({"error": "Missing 'key' or 'value' in request body."}), 400

      key = str(data["key"]).strip()
      key = {
        "model": "Model",
        "modelversion": "ModelVersion",
        "drivingmodel": "DrivingModel",
        "drivingmodelversion": "DrivingModelVersion",
      }.get(key.lower(), key)
      val = data["value"]

      # Python json parses true/false as boolean
      if isinstance(val, bool):
        str_val = "1" if val else "0"
      else:
        str_val = str(val)

      allowed_keys, _ = _get_param_type_info()
      if key not in allowed_keys:
        return jsonify({"error": f"Parameter '{key}' is not editable."}), 403

      # 1. Prevent changing the model or reboot-required toggles while the car is actively driving
      reboot_keys = {"Model", "DrivingModel", "AlwaysOnLateral", "ForceTorqueController", "NNFF", "NNFFLite"}
      if key in reboot_keys and params.get_bool("IsOnroad"):
        friendly_names = {
          "Model": "Driving Model",
          "DrivingModel": "Driving Model",
          "AlwaysOnLateral": "Always On Lateral",
          "ForceTorqueController": "Force Torque Controller",
          "NNFF": "NNFF",
          "NNFFLite": "NNFF-Lite"
        }
        name = friendly_names.get(key, key)
        return jsonify({"error": f"Cannot change {name} while the car is driving. A reboot is required."}), 403

      if key == "AutomaticUpdates" and params.get_bool("IsOnroad"):
        return jsonify({"error": "Cannot change Automatic Updates while driving."}), 403

      if key in {"EVTuning", "TruckTuning"}:
        enabled = str_val.strip() in ("1", "true", "True")
        params.put_bool(key, enabled)

        updated = {key: enabled}
        if enabled:
          other_key = "TruckTuning" if key == "EVTuning" else "EVTuning"
          params.put_bool(other_key, False)
          updated[other_key] = False

        update_starpilot_toggles()
        return jsonify({
          "message": f"Parameter '{key}' updated successfully.",
          "updated": updated,
        }), 200

      if key == "CustomAccelProfile":
        enabled = str_val.strip() in ("1", "true", "True")
        params.put_bool(key, enabled)

        updated = {key: enabled}
        if enabled and not _get_custom_accel_profile_initialized():
          defaults_lookup = _get_default_param_values()
          for custom_key in CUSTOM_ACCEL_PROFILE_PARAM_KEYS:
            custom_value = defaults_lookup[custom_key]
            params.put(custom_key, _serialize_param_write_value(custom_value))
            updated[custom_key] = float(custom_value)
          params.put_bool(CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY, True)

        update_starpilot_toggles()
        return jsonify({
          "message": f"Parameter '{key}' updated successfully.",
          "updated": updated,
        }), 200

      if key == "CarMake":
        catalog = _get_fingerprint_catalog()
        normalized_make = _normalize_fingerprint_make_key(str_val)
        stored_make = catalog["make_label_by_key"].get(normalized_make, str_val.strip())
        params.put("CarMake", stored_make)
        update_starpilot_toggles()
        return jsonify({
          "message": "Car make updated successfully.",
          "updated": {"CarMake": stored_make},
        }), 200

      if key == "CarModel":
        selected_model = str_val.strip()
        if not selected_model:
          return jsonify({"error": "Car model cannot be empty."}), 400

        catalog = _get_fingerprint_catalog()
        model_label = catalog["model_to_label"].get(selected_model)
        make_label = catalog["model_to_make"].get(selected_model)

        params.put("CarModel", selected_model)
        updated = {"CarModel": selected_model}

        if model_label:
          params.put("CarModelName", model_label)
          updated["CarModelName"] = model_label
        else:
          params.remove("CarModelName")
          updated["CarModelName"] = ""

        if make_label:
          params.put("CarMake", make_label)
          updated["CarMake"] = make_label

        update_starpilot_toggles()
        return jsonify({
          "message": f"Fingerprint set to '{model_label or selected_model}'.",
          "updated": updated,
        }), 200

      if key in ("Model", "DrivingModel"):
        selected_model = str_val.strip()
        if not selected_model:
          return jsonify({"error": "Driving model cannot be empty."}), 400

        params.put("Model", selected_model)
        params.put("DrivingModel", selected_model)

        available_models = [entry.strip() for entry in (params.get("AvailableModels", encoding="utf-8") or "").split(",")]
        available_names = [entry.strip() for entry in (params.get("AvailableModelNames", encoding="utf-8") or "").split(",")]
        model_versions = [entry.strip() for entry in (params.get("ModelVersions", encoding="utf-8") or "").split(",")]

        if selected_model in available_models:
          selected_index = available_models.index(selected_model)
          if selected_index < len(available_names) and available_names[selected_index]:
            params.put("DrivingModelName", available_names[selected_index])

          if selected_index < len(model_versions) and model_versions[selected_index]:
            resolved_version = model_versions[selected_index]
            params.put("ModelVersion", resolved_version)
            params.put("DrivingModelVersion", resolved_version)
        else:
          # Fallback to cached version map if this model isn't in the current manifest list yet.
          try:
            with open("/data/models/.model_versions.json", "r") as f:
              versions = json.load(f)
              if selected_model in versions:
                resolved_version = str(versions[selected_model]).strip()
                if resolved_version:
                  params.put("ModelVersion", resolved_version)
                  params.put("DrivingModelVersion", resolved_version)
          except Exception:
            pass
      elif key in ("ModelVersion", "DrivingModelVersion"):
        params.put("ModelVersion", str_val)
        params.put("DrivingModelVersion", str_val)
      elif key in CUSTOM_ACCEL_PROFILE_PARAM_KEYS:
        params.put(key, str_val)
        params.put_bool(CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY, True)
      else:
        params.put(key, str_val)

      gsm_metered_apply_result = None
      if key == "GsmMetered":
        metered_enabled = str_val.strip() in ("1", "true", "True")
        gsm_metered_apply_result = _apply_cellular_metered_setting(metered_enabled)

      locked_lkas = _enforce_cancel_remap_lkas_lock()
      update_starpilot_toggles()

      response = {"message": f"Parameter '{key}' updated successfully."}
      updated = {}
      if key == "RemapCancelToDistance" and params.get_bool("RemapCancelToDistance"):
        updated["RemapCancelToDistance"] = True
        updated["LKASButtonControl"] = 0
        response["message"] = "Remap Cancel To Distance enabled. LKAS Button has been locked to No Action."
      elif key == "LKASButtonControl" and params.get_bool("RemapCancelToDistance"):
        updated["LKASButtonControl"] = 0
        updated["RemapCancelToDistance"] = True
        response["message"] = "LKAS Button is locked to No Action while Remap Cancel To Distance is enabled."
      elif locked_lkas:
        updated["LKASButtonControl"] = 0

      if gsm_metered_apply_result is not None:
        updated["GsmMetered"] = str_val.strip() in ("1", "true", "True")
        response["networkProfilesUpdated"] = gsm_metered_apply_result.get("profiles", [])
        warnings = gsm_metered_apply_result.get("warnings", [])
        if warnings:
          response["warning"] = " ".join(warnings)
      if updated:
        response["updated"] = updated

      return jsonify(response), 200

    request_key = request.args.get("key")
    if request_key in CUSTOM_ACCEL_PROFILE_PARAM_KEYS and not _get_custom_accel_profile_initialized():
      defaults_lookup = _get_default_param_values()
      return _serialize_param_write_value(defaults_lookup.get(request_key)), 200
    if request_key == CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY:
      return _serialize_param_write_value(_get_custom_accel_profile_initialized()), 200
    return params.get(request_key) or "", 200

  @app.route("/api/params/all", methods=["GET"])
  def get_all_params():
    _enforce_cancel_remap_lkas_lock()
    allowed_keys, types = _get_param_type_info()
    defaults_lookup = _get_default_param_values()

    result = {}
    for key in allowed_keys:
      t = types.get(key, str)
      try:
        result[key] = _get_current_param_value(key, t, defaults_lookup)
      except Exception:
        result[key] = None

    return jsonify(result), 200

  @app.route("/api/params/defaults", methods=["GET"])
  def get_default_params():
    allowed_keys, types = _get_param_type_info()
    defaults_lookup = _get_default_param_values()

    result = {}
    for key in allowed_keys:
      t = types.get(key, str)
      default_val = defaults_lookup.get(key)

      try:
        if t == bool:
          if isinstance(default_val, bytes):
            default_str = default_val.decode("utf-8", errors="replace")
          else:
            default_str = str(default_val or "")
          result[key] = default_str in ("1", "true", "True")
        elif t == float:
          result[key] = float(default_val)
        elif t == int:
          result[key] = int(float(default_val))
        else:
          if isinstance(default_val, bytes):
            result[key] = default_val.decode("utf-8", errors="replace")
          else:
            result[key] = str(default_val or "")
      except Exception:
        result[key] = None

    return jsonify(result), 200

  @app.route("/api/troubleshoot", methods=["GET"])
  def get_troubleshoot_data():
    try:
      return jsonify(_build_troubleshoot_payload()), 200
    except Exception as exception:
      return jsonify({"error": str(exception)}), 500

  @app.route("/api/troubleshoot/reset", methods=["POST"])
  def reset_troubleshoot_section():
    request_data = request.get_json() or {}
    section_id = str(request_data.get("sectionId") or "").strip()
    if not section_id:
      return jsonify({"error": "Missing 'sectionId' in request body."}), 400

    try:
      result = _reset_troubleshoot_section(section_id)
      message = f"{result['sectionTitle']} reset to defaults."
      if result["skippedCount"] > 0:
        message += f" Updated {result['updatedCount']} setting(s), skipped {result['skippedCount']}."
      return jsonify({
        "message": message,
        **result,
      }), 200
    except ValueError as exception:
      return jsonify({"error": str(exception)}), 400
    except Exception as exception:
      return jsonify({"error": str(exception)}), 500

  @app.route("/api/models/installed", methods=["GET"])
  def get_installed_models():
    catalog = get_model_catalog()
    installed = [{"value": model["value"], "label": model["label"]} for model in catalog if model["installed"]]

    # Keep current model selectable even if local files are currently inconsistent.
    current_model = params.get("Model", encoding="utf-8") or ""
    if current_model and all(model["value"] != current_model for model in installed):
      for model in catalog:
        if model["value"] == current_model:
          installed.append({"value": model["value"], "label": model["label"]})
          break

    return jsonify(installed), 200

  @app.route("/api/models/catalog", methods=["GET"])
  def get_models_catalog():
    models = get_model_catalog()
    return jsonify({
      "models": models,
      "currentModel": params.get("Model", encoding="utf-8") or "",
      "summary": {
        "installed": sum(1 for model in models if model["installed"]),
        "missing": sum(1 for model in models if not model["installed"]),
        "total": len(models),
      },
    }), 200

  @app.route("/api/models/preferences", methods=["GET", "PUT"])
  def get_or_set_models_preferences():
    if request.method == "GET":
      return jsonify({
        "sortMode": read_legacy_param_file(MODEL_SORT_MODE_PARAM, "alphabetical"),
        "userFavorites": [entry for entry in (params.get(MODEL_USER_FAVORITES_PARAM, encoding="utf-8") or "").split(",") if entry],
      }), 200

    data = request.get_json() or {}
    changed = []

    if "sortMode" in data:
      sort_mode = str(data.get("sortMode") or "alphabetical").strip() or "alphabetical"
      write_legacy_param_file(MODEL_SORT_MODE_PARAM, sort_mode)
      changed.append("sort mode")

    if "userFavorites" in data:
      incoming = data.get("userFavorites")
      if isinstance(incoming, list):
        favorites = ",".join(entry.strip() for entry in incoming if str(entry).strip())
      else:
        favorites = ",".join(entry.strip() for entry in str(incoming or "").split(",") if entry.strip())
      params.put(MODEL_USER_FAVORITES_PARAM, favorites)
      changed.append("favorites")

    if not changed:
      return jsonify({"error": "No preferences provided."}), 400

    return jsonify({"message": f"Updated model {' and '.join(changed)}."}), 200

  @app.route("/api/models/status", methods=["GET"])
  def get_models_status():
    models = get_model_catalog()
    model_to_download = params_memory.get(MODEL_DOWNLOAD_PARAM, encoding="utf-8") or ""
    download_all = params_memory.get_bool(MODEL_DOWNLOAD_ALL_PARAM)
    progress = params_memory.get(MODEL_DOWNLOAD_PROGRESS_PARAM, encoding="utf-8") or ""
    cancelling = params_memory.get_bool(MODEL_CANCEL_DOWNLOAD_PARAM)

    downloading = bool(model_to_download) or download_all
    current_model = params.get("Model", encoding="utf-8") or ""
    sort_mode = read_legacy_param_file(MODEL_SORT_MODE_PARAM, "alphabetical")
    terminal = progress in ("Downloaded!", "All models downloaded!") or bool(re.search(r"cancelled|exists|failed|offline|invalid|error", progress, re.IGNORECASE))
    summary = {
      "installed": sum(1 for model in models if model["installed"]),
      "missing": sum(1 for model in models if not model["installed"]),
      "total": len(models),
    }

    now = time.monotonic()
    signature = (
      summary["total"],
      summary["installed"],
      summary["missing"],
      model_to_download,
      download_all,
      downloading,
      cancelling,
      progress,
      current_model,
      sort_mode,
      terminal,
      bool(params.get_bool("IsOnroad")),
    )
    if model_status_debug["last_signature"] != signature or now - model_status_debug["last_log_time"] >= 15:
      print(
        f"[ModelStatus] addr={request.remote_addr or 'unknown'} total={summary['total']} "
        f"installed={summary['installed']} missing={summary['missing']} downloading={downloading} "
        f"download_all={download_all} model='{model_to_download or '-'}' current='{current_model or '-'}' "
        f"progress='{progress or 'Idle'}' cancelling={cancelling} onroad={params.get_bool('IsOnroad')} terminal={terminal}"
      )
      model_status_debug["last_signature"] = signature
      model_status_debug["last_log_time"] = now

    if summary["total"] == 0 and now - model_status_debug["last_empty_catalog_log_time"] >= 15:
      available_models = params.get("AvailableModels", encoding="utf-8") or ""
      available_names = params.get("AvailableModelNames", encoding="utf-8") or ""
      available_models_count = len([item for item in available_models.split(",") if item.strip()])
      available_names_count = len([item for item in available_names.split(",") if item.strip()])
      print(
        f"[ModelStatus] WARNING empty catalog available_models={available_models_count} "
        f"available_names={available_names_count} raw_available_models='{available_models[:120]}'"
      )
      model_status_debug["last_empty_catalog_log_time"] = now

    return jsonify({
      "modelToDownload": model_to_download,
      "downloadAll": download_all,
      "downloading": downloading,
      "cancelling": cancelling,
      "progress": progress,
      "isOnroad": params.get_bool("IsOnroad"),
      "terminal": terminal,
      "models": models,
      "currentModel": current_model,
      "summary": summary,
      "sortMode": sort_mode,
    }), 200

  @app.route("/api/models/refresh_manifest", methods=["POST"])
  def refresh_models_manifest():
    if params.get_bool("IsOnroad"):
      return jsonify({"error": "Cannot refresh model manifest while driving."}), 403

    if params_memory.get_bool(MODEL_DOWNLOAD_ALL_PARAM) or (params_memory.get(MODEL_DOWNLOAD_PARAM, encoding="utf-8") or ""):
      return jsonify({"error": "Cannot refresh model manifest while a download is in progress."}), 409

    try:
      from openpilot.starpilot.assets.model_manager import ModelManager

      # ModelManager expects raw Params semantics (encoding-less get -> str, not legacy bytes).
      manager = ModelManager(_params_raw, _params_memory_raw)
      manager.update_models(False)
    except Exception as exception:
      return jsonify({"error": f"Failed to refresh model manifest: {exception}"}), 500

    return jsonify({"message": "Model manifest refreshed."}), 200

  @app.route("/api/models/download", methods=["POST"])
  def start_model_download():
    if params.get_bool("IsOnroad"):
      return jsonify({"error": "Cannot download models while driving."}), 403

    if params_memory.get_bool(MODEL_DOWNLOAD_ALL_PARAM) or (params_memory.get(MODEL_DOWNLOAD_PARAM, encoding="utf-8") or ""):
      return jsonify({"error": "A model download is already in progress."}), 409

    data = request.get_json() or {}
    model_key = (data.get("model") or "").strip()
    if not model_key:
      return jsonify({"error": "Missing model key."}), 400

    catalog = {model["value"]: model for model in get_model_catalog()}
    model = catalog.get(model_key)
    if model is None:
      return jsonify({"error": f"Unknown model '{model_key}'."}), 404

    if model["installed"]:
      return jsonify({"message": f"\"{model['label']}\" is already installed."}), 200

    params_memory.remove(MODEL_CANCEL_DOWNLOAD_PARAM)
    params_memory.remove(MODEL_DOWNLOAD_ALL_PARAM)
    params_memory.put(MODEL_DOWNLOAD_PARAM, model_key)
    params_memory.put(MODEL_DOWNLOAD_PROGRESS_PARAM, "Downloading...")

    return jsonify({"message": f"Started downloading \"{model['label']}\"."}), 200

  @app.route("/api/models/download_all", methods=["POST"])
  def start_models_download_all():
    if params.get_bool("IsOnroad"):
      return jsonify({"error": "Cannot download models while driving."}), 403

    if params_memory.get_bool(MODEL_DOWNLOAD_ALL_PARAM) or (params_memory.get(MODEL_DOWNLOAD_PARAM, encoding="utf-8") or ""):
      return jsonify({"error": "A model download is already in progress."}), 409

    missing_models = [model for model in get_model_catalog() if not model["installed"]]
    if not missing_models:
      return jsonify({"message": "All models are already installed."}), 200

    params_memory.remove(MODEL_CANCEL_DOWNLOAD_PARAM)
    params_memory.remove(MODEL_DOWNLOAD_PARAM)
    params_memory.put_bool(MODEL_DOWNLOAD_ALL_PARAM, True)
    params_memory.put(MODEL_DOWNLOAD_PROGRESS_PARAM, "Downloading...")

    return jsonify({"message": f"Started downloading {len(missing_models)} model(s)."}), 200

  @app.route("/api/models/cancel", methods=["POST"])
  def cancel_model_download():
    model_to_download = params_memory.get(MODEL_DOWNLOAD_PARAM, encoding="utf-8") or ""
    download_all = params_memory.get_bool(MODEL_DOWNLOAD_ALL_PARAM)
    if not model_to_download and not download_all:
      return jsonify({"message": "No active model download to cancel."}), 200

    params_memory.put_bool(MODEL_CANCEL_DOWNLOAD_PARAM, True)
    return jsonify({"message": "Cancellation requested."}), 200

  @app.route("/api/models/delete", methods=["POST"])
  def delete_model_files():
    if params.get_bool("IsOnroad"):
      return jsonify({"error": "Cannot delete model files while driving."}), 403

    if params_memory.get_bool(MODEL_DOWNLOAD_ALL_PARAM) or (params_memory.get(MODEL_DOWNLOAD_PARAM, encoding="utf-8") or ""):
      return jsonify({"error": "Cannot delete model files while a download is in progress."}), 409

    data = request.get_json() or {}
    model_key = (data.get("model") or "").strip()
    if not model_key:
      return jsonify({"error": "Missing model key."}), 400

    current_model = params.get("Model", encoding="utf-8") or ""
    if model_key == current_model:
      return jsonify({"error": "Cannot delete the currently active model."}), 409

    catalog = {model["value"]: model for model in get_model_catalog()}
    model = catalog.get(model_key)
    if model is None:
      return jsonify({"error": f"Unknown model '{model_key}'."}), 404

    models_dir = Path("/data/models")
    if not models_dir.is_dir():
      return jsonify({"message": "No model directory exists yet."}), 200

    deleted = []
    for item in models_dir.iterdir():
      name = item.name
      is_match = (
        name == f"{model_key}.thneed" or
        name == f"{model_key}.pkl" or
        name.startswith(f"{model_key}_")
      )

      if not is_match:
        continue

      try:
        if item.is_dir():
          shutil.rmtree(item)
        else:
          item.unlink(missing_ok=True)
        deleted.append(name)
      except Exception as exception:
        return jsonify({"error": f"Failed deleting '{name}': {exception}"}), 500

    if not deleted:
      return jsonify({"message": f"No files found for \"{model['label']}\"."}), 200

    return jsonify({"message": f"Deleted {len(deleted)} file(s) for \"{model['label']}\"."}), 200

  def _get_maps_status_payload():
    current_selected = params.get("MapsSelected", encoding="utf-8") or ""
    selected_raw = sanitize_selected_locations_csv(current_selected)
    if selected_raw != current_selected:
      params.put("MapsSelected", selected_raw)

    selected_entries = get_selected_map_entries(selected_raw)
    selected_locations = [entry["token"] for entry in selected_entries]
    maps_present = MAPS_PATH.exists() and any(path.is_file() for path in MAPS_PATH.rglob("*"))
    storage_bytes = 0
    if MAPS_PATH.exists():
      try:
        storage_bytes = sum(path.stat().st_size for path in MAPS_PATH.rglob("*") if path.is_file())
      except Exception:
        storage_bytes = 0

    return {
      "selectedLocations": selected_locations,
      "selectedEntries": selected_entries,
      "selectedCount": len(selected_locations),
      "hasSelection": bool(selected_locations),
      "downloading": params_memory.get_bool(MAPS_DOWNLOAD_PARAM),
      "cancelling": params_memory.get_bool(MAPS_CANCEL_DOWNLOAD_PARAM),
      "isOnroad": params.get_bool("IsOnroad"),
      "lastUpdate": params.get("LastMapsUpdate", encoding="utf-8") or "Never",
      "mapsPresent": maps_present,
      "scheduleLabel": schedule_label(params.get("PreferredSchedule")),
      "scheduleOptions": MAP_SCHEDULE_OPTIONS,
      "scheduleValue": schedule_param_value(params.get("PreferredSchedule")),
      "storageBytes": storage_bytes,
    }

  @app.route("/api/maps/catalog", methods=["GET"])
  def get_maps_catalog():
    return jsonify({
      "sections": MAPS_CATALOG,
      "scheduleOptions": MAP_SCHEDULE_OPTIONS,
    }), 200

  @app.route("/api/maps/status", methods=["GET"])
  def get_maps_status():
    return jsonify(_get_maps_status_payload()), 200

  @app.route("/api/maps/selection", methods=["POST"])
  def set_maps_selection():
    payload = request.get_json(silent=True) or {}
    selected_raw = sanitize_selected_locations_csv(payload.get("selectedLocations"))
    params.put("MapsSelected", selected_raw)
    return jsonify({
      "message": f"Saved {len([entry for entry in selected_raw.split(',') if entry])} selected map region(s).",
      "status": _get_maps_status_payload(),
    }), 200

  @app.route("/api/maps/schedule", methods=["POST"])
  def set_maps_schedule():
    payload = request.get_json(silent=True) or {}
    schedule_value = schedule_param_value(payload.get("schedule"))
    params.put("PreferredSchedule", schedule_value)
    return jsonify({
      "message": f"Map auto-update schedule set to {schedule_label(schedule_value)}.",
      "status": _get_maps_status_payload(),
    }), 200

  @app.route("/api/maps/download", methods=["POST"])
  def start_maps_download():
    payload = request.get_json(silent=True) or {}

    if params.get_bool("IsOnroad"):
      return jsonify({"error": "Cannot download maps while driving."}), 403

    if params_memory.get_bool(MAPS_DOWNLOAD_PARAM):
      return jsonify({"error": "A map download is already in progress."}), 409

    if "selectedLocations" in payload:
      params.put("MapsSelected", sanitize_selected_locations_csv(payload.get("selectedLocations")))

    if "schedule" in payload:
      params.put("PreferredSchedule", schedule_param_value(payload.get("schedule")))

    selected_raw = sanitize_selected_locations_csv(params.get("MapsSelected", encoding="utf-8") or "")
    if not selected_raw:
      return jsonify({"error": "No map regions are selected."}), 400

    params.put("MapsSelected", selected_raw)
    params_memory.remove(MAPS_CANCEL_DOWNLOAD_PARAM)
    params_memory.put_bool(MAPS_DOWNLOAD_PARAM, True)

    return jsonify({
      "message": f"Started downloading {len([entry for entry in selected_raw.split(',') if entry])} selected map region(s).",
      "status": _get_maps_status_payload(),
    }), 200

  @app.route("/api/maps/cancel", methods=["POST"])
  def cancel_maps_download():
    if not params_memory.get_bool(MAPS_DOWNLOAD_PARAM):
      return jsonify({"message": "No active map download to cancel.", "status": _get_maps_status_payload()}), 200

    params_memory.put_bool(MAPS_CANCEL_DOWNLOAD_PARAM, True)
    return jsonify({"message": "Map download cancellation requested.", "status": _get_maps_status_payload()}), 200

  @app.route("/api/maps/remove", methods=["POST"])
  def remove_maps_data():
    if params.get_bool("IsOnroad"):
      return jsonify({"error": "Cannot remove maps while driving."}), 403

    if params_memory.get_bool(MAPS_DOWNLOAD_PARAM):
      return jsonify({"error": "Cannot remove maps while a download is in progress."}), 409

    if MAPS_PATH.exists():
      shutil.rmtree(MAPS_PATH, ignore_errors=True)

    return jsonify({"message": "Maps removed.", "status": _get_maps_status_payload()}), 200

  @app.route("/api/params_memory", methods=["GET"])
  def get_param_memory():
    return params_memory.get(request.args.get("key")) or "", 200

  def is_model_installed(model_key, model_version, on_disk_files):
    if f"{model_key}.thneed" in on_disk_files:
      return True

    if model_version in ("v8", "v9", "v10", "v11", "v12"):
      required_files = {
        f"{model_key}_driving_policy_tinygrad.pkl",
        f"{model_key}_driving_vision_tinygrad.pkl",
        f"{model_key}_driving_policy_metadata.pkl",
        f"{model_key}_driving_vision_metadata.pkl",
      }
      if model_version == "v12":
        required_files |= {
          f"{model_key}_driving_off_policy_tinygrad.pkl",
          f"{model_key}_driving_off_policy_metadata.pkl",
        }
      return required_files.issubset(on_disk_files)

    if model_version == "v7":
      return f"{model_key}.pkl" in on_disk_files

    # Fallback for unknown versions
    return any(file.startswith(f"{model_key}.") or file.startswith(f"{model_key}_") for file in on_disk_files)

  def get_model_catalog():
    available = [model.strip() for model in (params.get("AvailableModels", encoding="utf-8") or "").split(",")]
    names = [name.strip() for name in (params.get("AvailableModelNames", encoding="utf-8") or "").split(",")]
    series = [entry.strip() for entry in (params.get("AvailableModelSeries", encoding="utf-8") or "").split(",")]
    versions = [entry.strip() for entry in (params.get("ModelVersions", encoding="utf-8") or "").split(",")]
    released_dates = [entry.strip() for entry in (params.get("ModelReleasedDates", encoding="utf-8") or "").split(",")]

    community_favorites = {entry.strip() for entry in (params.get("CommunityFavorites", encoding="utf-8") or "").split(",") if entry.strip()}
    user_favorites = {entry.strip() for entry in (params.get(MODEL_USER_FAVORITES_PARAM, encoding="utf-8") or "").split(",") if entry.strip()}

    models_dir = "/data/models"
    try:
      on_disk_files = set(os.listdir(models_dir)) if os.path.isdir(models_dir) else set()
    except Exception:
      on_disk_files = set()

    models = []
    for i, key in enumerate(available):
      if not key:
        continue

      label = names[i] if i < len(names) and names[i] else key
      model_version = versions[i] if i < len(versions) else ""
      model_series = series[i] if i < len(series) and series[i] else "Custom Series"
      released = released_dates[i] if i < len(released_dates) else ""

      installed = is_model_installed(key, model_version, on_disk_files)
      partial = not installed and any(file.startswith(f"{key}.") or file.startswith(f"{key}_") for file in on_disk_files)

      models.append({
        "value": key,
        "label": label,
        "series": model_series,
        "version": model_version,
        "released": released,
        "installed": installed,
        "partial": partial,
        "communityFavorite": key in community_favorites,
        "userFavorite": key in user_favorites,
      })

    models.sort(key=lambda model: (model["series"].lower(), model["label"].lower()))
    return models

  @app.route("/api/routes", methods=["GET"])
  def list_routes():
    def generate():
      routes = [(path, name) for path in FOOTAGE_PATHS for name in utilities.get_routes_names(path)]
      total = len(routes)
      yield f"data: {json.dumps({'progress': 0, 'total': total})}\n\n"

      with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(utilities.process_route, path, name): (path, name) for path, name in routes}
        for processed, future in enumerate(as_completed(futures), start=1):
          try:
            result = future.result()
            yield f"data: {json.dumps({'routes': [result]})}\n\n"
          except Exception as exception:
            print(f"Error processing route: {exception}")
          yield f"data: {json.dumps({'progress': processed, 'total': total})}\n\n"

    return Response(generate(), mimetype="text/event-stream")

  @app.route("/api/routes/<name>", methods=["DELETE"])
  def delete_route(name):
    for footage_path in FOOTAGE_PATHS:
      for segment in os.listdir(footage_path):
        if segment.startswith(name):
          delete_file(os.path.join(footage_path, segment))
    return {"message": "Route deleted!"}, 200

  @app.route("/api/routes/delete_all", methods=["DELETE"])
  def delete_all_routes():
    route_names = set()
    for footage_path in FOOTAGE_PATHS:
      if os.path.exists(footage_path):
        for segment in os.listdir(footage_path):
          route_names.add(segment.split("--")[0])

    for route_name in sorted(list(route_names)):
      for footage_path in FOOTAGE_PATHS:
        if os.path.exists(footage_path):
          for segment in os.listdir(footage_path):
            if segment.startswith(route_name):
              delete_file(os.path.join(footage_path, segment))

    return {"message": "All routes deleted!"}, 200

  @app.route("/api/routes/<name>/preserve", methods=["POST"])
  def preserve_route(name):
    preserved_routes = 0
    for footage_path in FOOTAGE_PATHS:
      for segment in os.listdir(footage_path):
        if segment.endswith("--0"):
          segment_path = os.path.join(footage_path, segment)
          if PRESERVE_ATTR_NAME in os.listxattr(segment_path) and os.getxattr(segment_path, PRESERVE_ATTR_NAME) == PRESERVE_ATTR_VALUE:
            preserved_routes += 1

    if preserved_routes >= PRESERVE_COUNT:
      return {"error": f"Maximum of {PRESERVE_COUNT} preserved routes reached..."}, 400

    for footage_path in FOOTAGE_PATHS:
      route_path = os.path.join(footage_path, f"{name}--0")
      if os.path.exists(route_path):
        os.setxattr(route_path, PRESERVE_ATTR_NAME, PRESERVE_ATTR_VALUE)
        return {"message": "Route preserved!!"}, 200

    return {"error": "Route not found"}, 404

  @app.route("/api/routes/<name>/preserve", methods=["DELETE"])
  def un_preserve_route(name):
    for footage_path in FOOTAGE_PATHS:
      route_path = os.path.join(footage_path, f"{name}--0")
      if PRESERVE_ATTR_NAME in os.listxattr(route_path):
        os.removexattr(route_path, PRESERVE_ATTR_NAME)
        return {"message": "Route unpreserved!"}, 200
    return {"error": "Route not found"}, 404

  @app.route("/video/<name>/combined", methods=["GET"])
  def get_combined_route_video(name):
    camera = request.args.get("camera", "forward")
    for footage_path in FOOTAGE_PATHS:
      segments = utilities.get_segments_in_route(name, footage_path)
      if segments:
        cam_file = {
          "forward": "fcamera.hevc",
          "wide": "ecamera.hevc",
          "driver": "dcamera.hevc",
        }.get(camera, "fcamera.hevc")

        input_files = [
          os.path.join(footage_path, seg, cam_file)
          for seg in segments
          if os.path.exists(os.path.join(footage_path, seg, cam_file))
        ]

        if not input_files:
          return {"error": "No video files found"}, 404

        mp4_file = utilities.ffmpeg_concat_segments_to_mp4(input_files, cache_key=f"{name}-{camera}")
        return send_file(mp4_file, mimetype="video/mp4")

    return {"error": "Route not found"}, 404

  @app.route("/api/routes/<name>", methods=["GET"])
  def get_route(name):
    for footage_path in FOOTAGE_PATHS:
      base_path = f"{footage_path}{name}--0"
      if os.path.exists(base_path):
        segments = utilities.get_segments_in_route(name, footage_path)
        if not segments:
          break

        segment_urls = [f"/video/{segment}" for segment in segments]
        total_duration = sum(utilities.get_video_duration(f"{footage_path}{name}--{i}/fcamera.hevc") for i in range(len(segment_urls)))
        return {
          "name": name,
          "segment_urls": segment_urls,
          "total_duration": round(total_duration),
          "date": utilities.get_route_start_time(base_path),
          "available_cameras": utilities.get_available_cameras(base_path),
        }, 200
    return {"error": "Route not found"}, 404

  @app.route("/api/routes/clear_name", methods=["POST"])
  def clear_route_name():
    data = request.get_json()
    route_name = data.get("name")

    if not route_name:
      return jsonify({"error": "Missing route name"}), 400

    cleared = False
    original_timestamp = None
    for footage_path in FOOTAGE_PATHS:
      if not os.path.exists(footage_path):
        continue

      segments_to_process = [s for s in os.listdir(footage_path) if s.startswith(route_name) and os.path.isdir(os.path.join(footage_path, s))]
      if not segments_to_process:
        continue

      for segment in segments_to_process:
        segment_dir = os.path.join(footage_path, segment)
        for item in os.listdir(segment_dir):
          if not item.endswith((".hevc", ".ts", ".png", ".gif")) and item not in utilities.LOG_CANDIDATES:
            try:
              os.remove(os.path.join(segment_dir, item))
              cleared = True
            except OSError:
              pass

        if cleared:
          route_timestamp_dt = utilities.get_route_start_time(segment_dir)
          original_timestamp = route_timestamp_dt.isoformat() if route_timestamp_dt else None

    if cleared:
      return jsonify({"message": "Route name cleared successfully!", "timestamp": original_timestamp}), 200
    else:
      return jsonify({"error": "Route not found or no custom name to clear"}), 404

  @app.route("/api/routes/rename", methods=["POST"])
  def rename_route():
    data = request.get_json()
    old_name = data.get("old")
    new_name_raw = data.get("new")

    if not old_name or not new_name_raw:
      return jsonify({"error": "Missing old or new name"}), 400

    new_name = utilities.secure_filename(new_name_raw)
    renamed = False

    for footage_path in FOOTAGE_PATHS:
      if not os.path.exists(footage_path):
        continue

      segments_to_process = [s for s in os.listdir(footage_path) if s.startswith(old_name) and os.path.isdir(os.path.join(footage_path, s))]
      if not segments_to_process:
        continue

      for segment in segments_to_process:
        segment_dir = os.path.join(footage_path, segment)
        for item in os.listdir(segment_dir):
          if not item.endswith((".hevc", ".ts", ".png", ".gif", "rlog")):
            try:
              os.remove(os.path.join(segment_dir, item))
            except OSError:
              pass

      for segment in segments_to_process:
        segment_dir = os.path.join(footage_path, segment)
        new_name_file_path = os.path.join(segment_dir, new_name)

        try:
          with open(new_name_file_path, "a"):
            os.utime(new_name_file_path, None)
          renamed = True
        except OSError as e:
          return jsonify({"error": f"Error creating new name file: {e}"}), 500

    if renamed:
      return jsonify({"message": "Route renamed successfully!"}), 200
    else:
      return jsonify({"error": "Route not found"}), 404

  @app.route("/api/screen_recordings/delete/<path:filename>", methods=["DELETE"])
  def delete_screen_recording(filename):
    mp4_path = SCREEN_RECORDINGS_PATH / filename
    if not mp4_path.exists():
      return {"error": "File not found"}, 404

    delete_file(str(mp4_path))

    for ext in (".png", ".gif"):
      thumb = mp4_path.with_suffix(ext)
      if thumb.exists():
        delete_file(str(thumb))

    return {"message": "Deleted"}, 200

  @app.route("/api/screen_recordings/delete_all", methods=["DELETE"])
  def delete_all_screen_recordings():
    files_to_delete = [f for f in os.listdir(SCREEN_RECORDINGS_PATH) if f.endswith(".mp4")]
    for filename in files_to_delete:
      delete_file(os.path.join(SCREEN_RECORDINGS_PATH, filename))
      for ext in (".png", ".gif"):
        thumb = os.path.join(SCREEN_RECORDINGS_PATH, filename.replace(".mp4", ext))
        if os.path.exists(thumb):
          delete_file(thumb)
    return {"message": "All screen recordings deleted!"}, 200

  @app.route("/api/screen_recordings/download/<path:filename>", methods=["GET"])
  def download_screen_recording(filename):
    return send_from_directory(SCREEN_RECORDINGS_PATH, filename, as_attachment=True)

  @app.route("/api/screen_recordings/list", methods=["GET"])
  def list_screen_recordings():
    def generate():
      recordings = sorted(
        [recording for recording in SCREEN_RECORDINGS_PATH.glob("*.mp4") if not Path(f"{recording}.lock").exists()],
        key=lambda p: p.stat().st_mtime,
        reverse=True
      )
      total = len(recordings)

      yield f"data: {json.dumps({'progress': 0, 'total': total})}\n\n"

      with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(utilities.process_screen_recording, mp4): mp4 for mp4 in recordings}
        for processed, future in enumerate(as_completed(futures), start=1):
          try:
            result = future.result()
            yield f"data: {json.dumps({'recordings': [result]})}\n\n"
          except Exception as exception:
            print(f"Error processing recording: {exception}")

          yield f"data: {json.dumps({'progress': processed, 'total': total})}\n\n"

    return Response(generate(), mimetype="text/event-stream")

  @app.route("/screen_recordings/<path:filename>", methods=["GET"])
  def serve_screen_recording_asset(filename):
    return send_from_directory(SCREEN_RECORDINGS_PATH, filename)

  @app.route("/api/screen_recordings/rename", methods=["POST"])
  def rename_screen_recording():
    data = request.get_json() or {}
    old = data.get("old")
    new_raw = data.get("new")

    if not old or not new_raw:
      return {"error": "Missing filenames"}, 400

    new = utilities.secure_filename(new_raw)
    old_path = SCREEN_RECORDINGS_PATH / old
    new_path = SCREEN_RECORDINGS_PATH / new

    if not old_path.exists():
      return {"error": "Original file not found"}, 404

    if new_path.exists():
      return {"error": "Target file already exists"}, 400

    old_path.rename(new_path)
    for extension in (".png", ".gif"):
      old_thumb = old_path.with_suffix(extension)
      new_thumb = new_path.with_suffix(extension)

      if old_thumb.exists():
        old_thumb.rename(new_thumb)

    return {"message": "Renamed"}, 200

  @app.route("/api/speed_limits", methods=["GET"])
  def speed_limits():
    data = json.loads(params.get("SpeedLimitsFiltered") or "[]")
    current_time = (datetime.now(timezone.utc) - timedelta(days=6, hours=23)).isoformat()
    data = [{**e, "last_vetted": current_time} for e in data]

    params.put("SpeedLimitsFiltered", json.dumps(data))

    buffer = BytesIO(json.dumps(data, indent=2).encode())
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="speed_limits.json", mimetype="application/json")

  def _speed_limits_status_payload():
    status = params_memory.get("UpdateSpeedLimitsStatus", encoding="utf-8") or ""
    processing = bool(status and status != "Completed!")
    enabled = params.get_bool("SpeedLimitFiller")
    is_onroad = params.get_bool("IsOnroad")
    time_valid = system_time_valid()
    is_metric = params.get_bool("IsMetric")

    vision_enabled = params.get_bool("VisionSpeedLimitDetection")
    vision_speed_limit = params_memory.get_float("VisionSpeedLimit") if vision_enabled else 0
    vision_confidence = params_memory.get_float("VisionSpeedLimitConfidence") if vision_enabled else 0
    vision_bookmark_count = params_memory.get_int("VisionSpeedLimitBookmarkCount") if vision_enabled else 0
    vision_debug_session = params_memory.get("VisionSpeedLimitDebugSession", encoding="utf-8") if vision_enabled else ""
    vision_last_event = params_memory.get("VisionSpeedLimitLastEvent", encoding="utf-8") if vision_enabled else ""
    vision_status = params_memory.get("VisionSpeedLimitStatus", encoding="utf-8") or ("Idle" if vision_enabled else "Disabled")
    vision_stream = params_memory.get("VisionSpeedLimitStream", encoding="utf-8") if vision_enabled else ""
    vision_speed_unit = "km/h" if is_metric else "mph"
    vision_display_speed = round(vision_speed_limit * (CV.MS_TO_KPH if is_metric else CV.MS_TO_MPH)) if vision_speed_limit > 0 else 0

    network_connected = True
    try:
      sm = messaging.SubMaster(["deviceState"], poll="deviceState")
      sm.update(0)
      network_connected = sm["deviceState"].networkType != log.DeviceState.NetworkType.none
    except Exception:
      pass

    overpass_requests = {}
    try:
      overpass_requests = json.loads(params.get("OverpassRequests", encoding="utf-8") or "{}")
    except Exception:
      pass

    current_day = datetime.now(timezone.utc).day
    saved_day = int(overpass_requests.get("day", current_day) or current_day)
    total_requests = int(overpass_requests.get("total_requests", 0) or 0)
    max_requests = int(overpass_requests.get("max_requests", 10000) or 10000)
    if saved_day != current_day:
      total_requests = 0
    api_limit_hit = total_requests >= max_requests

    reason = ""
    if not enabled:
      reason = "Enable Speed Limit Filler on the device first."
    elif processing:
      reason = status
    elif is_onroad:
      reason = "Processing is only available while parked."
    elif not time_valid:
      reason = "System time is not valid yet."
    elif not network_connected:
      reason = "Connect the device to the internet first."
    elif api_limit_hit:
      reason = "Today's Overpass API request limit has been reached."

    return {
      "apiLimitHit": api_limit_hit,
      "canProcessNow": enabled and not processing and not is_onroad and time_valid and network_connected and not api_limit_hit,
      "enabled": enabled,
      "isOnroad": is_onroad,
      "networkConnected": network_connected,
      "processing": processing,
      "reason": reason,
      "status": status or "Idle",
      "timeValid": time_valid,
      "totalRequests": total_requests,
      "maxRequests": max_requests,
      "visionConfidence": vision_confidence,
      "visionBookmarkCount": vision_bookmark_count,
      "visionDebugSession": vision_debug_session,
      "visionDisplaySpeed": vision_display_speed,
      "visionEnabled": vision_enabled,
      "visionLastEvent": vision_last_event,
      "visionSpeedUnit": vision_speed_unit,
      "visionStatus": vision_status,
      "visionStream": vision_stream,
    }

  @app.route("/api/speed_limits/status", methods=["GET"])
  def speed_limits_status():
    return jsonify(_speed_limits_status_payload()), 200

  @app.route("/api/speed_limits/process", methods=["POST"])
  def process_speed_limits():
    payload = _speed_limits_status_payload()
    if not payload["canProcessNow"]:
      return jsonify({"error": payload["reason"] or "Speed limit processing is unavailable right now."}), 409

    params_memory.put("UpdateSpeedLimitsStatus", "Calculating...")
    params_memory.put_bool("UpdateSpeedLimits", True)

    return jsonify({"message": "Speed limit processing started.", "status": "Calculating..."}), 202

  @app.route("/api/stats", methods=["GET"])
  def get_stats():
    build_metadata = get_build_metadata()

    short_branch = build_metadata.channel
    if build_metadata.release_channel:
      env = "Release"
    elif short_branch in ("StarPilot-Development", "StarPilot-Testing"):
      env = "Testing"
    elif build_metadata.tested_channel:
      env = "Staging"
    else:
      env = short_branch

    return {
      "diskUsage": utilities.get_disk_usage(),
      "driveStats": utilities.get_drive_stats(),
      "softwareInfo": {
        "branchName": build_metadata.channel,
        "buildEnvironment": env,
        "commitHash": build_metadata.openpilot.git_commit,
        "forkMaintainer": utilities.get_repo_owner(build_metadata.openpilot.git_normalized_origin),
        "updateAvailable": "Yes" if params.get_bool("UpdaterFetchAvailable") else "No",
        "versionDate": utilities.format_git_date(build_metadata.openpilot.git_commit_date),
      },
    }

  @app.route("/api/plots/live", methods=["GET"])
  def get_live_plots():
    _ensure_plots_worker()
    with _plots_lock:
      payload = dict(_plots_state)

    timestamp = _safe_float(payload.get("timestamp", 0.0), 0.0)
    age_seconds = max(0.0, time.time() - timestamp) if timestamp else 999.0

    return jsonify({
      **payload,
      "isOnroad": params.get_bool("IsOnroad"),
      "bootStabilizing": _is_plots_boot_stabilizing(),
      "sampleAgeSeconds": round(age_seconds, 3),
      "stale": age_seconds > _PLOTS_SAMPLE_STALE_AFTER_S,
    }), 200

  @app.route("/api/testing_grounds", methods=["GET"])
  def get_testing_grounds():
    state = _get_testing_grounds_state()
    return jsonify({
      **_serialize_testing_grounds_state(state),
      "isOnroad": params.get_bool("IsOnroad"),
    }), 200

  @app.route("/api/testing_grounds/select", methods=["POST"])
  def select_testing_ground():
    request_data = request.get_json() or {}
    slot_id = str(request_data.get("slotId") or "").strip()
    variant = str(request_data.get("variant") or "").strip().upper()

    if not slot_id:
      return jsonify({"error": "Missing 'slotId' in request body."}), 400

    try:
      state = _set_testing_ground_selection(slot_id, variant)
    except ValueError as exception:
      return jsonify({"error": str(exception)}), 400
    except Exception as exception:
      return jsonify({"error": str(exception)}), 500

    slot = _find_testing_ground_slot(state, slot_id)
    slot_name = slot.get("name", f"Testing Ground {slot_id}")
    selected_variant = str(state.get("activeVariant") or _TESTING_GROUNDS_DEFAULT_VARIANT)
    return jsonify({
      "message": f"{slot_name} set to variant {selected_variant}.",
      **_serialize_testing_grounds_state(state),
      "isOnroad": params.get_bool("IsOnroad"),
    }), 200

  @app.route("/api/longitudinal_maneuvers/status", methods=["GET"])
  def get_longitudinal_maneuvers_status():
    status = _load_longitudinal_maneuver_status()
    return jsonify(_serialize_longitudinal_maneuver_status(status)), 200

  @app.route("/api/longitudinal_maneuvers/start", methods=["POST"])
  def start_longitudinal_maneuvers():
    status = _set_longitudinal_maneuver_mode(True)
    return jsonify({
      "message": "Longitudinal maneuver mode armed. Engage with SET to start.",
      **_serialize_longitudinal_maneuver_status(status),
    }), 200

  @app.route("/api/longitudinal_maneuvers/stop", methods=["POST"])
  def stop_longitudinal_maneuvers():
    status = _set_longitudinal_maneuver_mode(False)
    return jsonify({
      "message": "Longitudinal maneuver mode disabled.",
      **_serialize_longitudinal_maneuver_status(status),
    }), 200

  @app.route("/api/update/fast/status", methods=["GET"])
  def get_fast_update_status():
    state_data = _get_fast_update_state()
    git_data = _collect_fast_update_info(include_remote=not state_data.get("running", False))
    return jsonify({
      **state_data,
      **git_data,
      "isOnroad": params.get_bool("IsOnroad"),
      "automaticUpdates": params.get_bool("AutomaticUpdates"),
      "warning": "Fast update skips backup creation and finalization safeguards.",
    }), 200

  @app.route("/api/update/branches", methods=["GET"])
  def get_update_branches():
    state_data = _get_fast_update_state()
    repo_path = str(_get_openpilot_root())

    try:
      current_branch = _git_stdout(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    except Exception as exception:
      return jsonify({"error": str(exception)}), 500

    branches, remote_error = _list_origin_branches(repo_path, include_remote=not state_data.get("running", False))
    if current_branch and current_branch not in branches:
      branches = sorted([*branches, current_branch], key=lambda branch: branch.lower())

    return jsonify({
      "currentBranch": current_branch,
      "branches": branches,
      "remoteError": remote_error,
      "isOnroad": params.get_bool("IsOnroad"),
      "running": state_data.get("running", False),
    }), 200

  @app.route("/api/update/fast", methods=["POST"])
  def run_fast_update():
    if params.get_bool("IsOnroad"):
      return jsonify({"error": "Cannot run a fast update while driving."}), 409

    with _fast_update_lock:
      if _fast_update_state.get("running"):
        return jsonify({"error": "Fast update already in progress."}), 409
      _fast_update_state.update({
        "running": True,
        "stage": "starting",
        "message": "Starting fast update...",
        "lastError": "",
        "startedAt": time.time(),
        "finishedAt": 0.0,
        "progressStep": 1,
        "progressTotalSteps": _FAST_UPDATE_TOTAL_STEPS,
        "progressStepPercent": 0.0,
        "progressPercent": 0.0,
        "progressLabel": "Preparing update",
        "progressDetail": "Initializing update process...",
      })

    threading.Thread(target=_fast_update_worker, daemon=True).start()

    return jsonify({
      "message": "Fast update started. Device will reboot when complete.",
      "warning": "Fast update skips backup creation and finalization safeguards.",
    }), 202

  @app.route("/api/update/branch", methods=["POST"])
  def run_branch_switch():
    if params.get_bool("IsOnroad"):
      return jsonify({"error": "Cannot switch branches while driving."}), 409

    request_data = request.get_json() or {}
    target_branch = str(request_data.get("branch") or "").strip()
    if not target_branch:
      return jsonify({"error": "Missing 'branch' in request body."}), 400

    repo_path = str(_get_openpilot_root())
    if not _is_valid_git_branch_name(repo_path, target_branch):
      return jsonify({"error": "Invalid branch name."}), 400

    with _fast_update_lock:
      if _fast_update_state.get("running"):
        return jsonify({"error": "Another update action is already in progress."}), 409
      _fast_update_state.update({
        "running": True,
        "stage": "starting",
        "message": f"Starting branch switch to '{target_branch}'...",
        "lastError": "",
        "lastBranch": target_branch,
        "lastMode": "branch-switch",
        "startedAt": time.time(),
        "finishedAt": 0.0,
        "progressStep": 1,
        "progressTotalSteps": _FAST_UPDATE_TOTAL_STEPS,
        "progressStepPercent": 0.0,
        "progressPercent": 0.0,
        "progressLabel": "Preparing branch switch",
        "progressDetail": "Initializing branch switch...",
      })

    threading.Thread(target=_branch_switch_worker, args=(target_branch,), daemon=True).start()

    return jsonify({
      "message": f"Branch switch started for '{target_branch}'. Device will reboot when complete.",
      "warning": "Fast update skips backup creation and finalization safeguards.",
    }), 202

  # ── Galaxy pairing (mirrors settings.cc L262-282) ──────────────────
  GALAXY_DIR = Path("/data/galaxy")
  GALAXY_AUTH_FILE = GALAXY_DIR / "glxyauth"

  @app.route("/api/galaxy/status", methods=["GET"])
  def galaxy_status():
    try:
      paired = GALAXY_AUTH_FILE.is_file() and len(GALAXY_AUTH_FILE.read_text().strip()) == 64
    except Exception:
      paired = False
    slug_file = GALAXY_DIR / "glxyslug"
    slug = slug_file.read_text().strip() if slug_file.is_file() else ""
    return jsonify({
      "paired": paired,
      "url": f"https://galaxy.firestar.link/{slug}" if slug else "",
    })

  @app.route("/api/galaxy/pair", methods=["POST"])
  def galaxy_pair():
    data = request.get_json() or {}
    password = (data.get("password") or "").strip()
    if len(password) < 6:
      return jsonify({"error": "Password must be at least 6 characters."}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    GALAXY_DIR.mkdir(parents=True, exist_ok=True)
    GALAXY_AUTH_FILE.write_text(pw_hash)
    
    # Generate 256-bit secure session token
    (GALAXY_DIR / "glxysession").write_text(secrets.token_hex(32))
    
    # Generate 16-character alphanumeric routing slug
    charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    slug = ''.join(secrets.choice(charset) for _ in range(16))
    (GALAXY_DIR / "glxyslug").write_text(slug)

    return jsonify({
      "message": "Pairing successful!",
      "url": f"https://galaxy.firestar.link/{slug}",
    })

  @app.route("/api/galaxy/unpair", methods=["POST"])
  def galaxy_unpair():
    for f in ["glxyauth", "glxysession", "glxyslug"]:
      file_path = GALAXY_DIR / f
      if file_path.is_file():
        file_path.unlink()
    return jsonify({"message": "Galaxy unpaired successfully."})

  @app.route("/api/tailscale/installed", methods=["GET"])
  def tailscale_installed():
    base = "/data/tailscale"
    tailscale_binary = f"{base}/tailscale"
    tailscaled_binary = f"{base}/tailscaled"

    systemd_unit = "/etc/systemd/system/tailscaled.service"

    if os.path.exists(tailscale_binary) and os.path.exists(tailscaled_binary) and os.path.exists(systemd_unit):
      return jsonify({"installed": True})

    result = subprocess.run(["which", "tailscale"], capture_output=True, text=True)
    if result.returncode == 0:
      return jsonify({"installed": True})

    return jsonify({"installed": False})

  @app.route("/api/tailscale/setup", methods=["POST"])
  def tailscale_setup():
    arch = "arm64"
    base = "/data/tailscale"

    result = subprocess.run(
      "curl -s https://pkgs.tailscale.com/stable/ | grep -oP 'tailscale_\\K[0-9]+\\.[0-9]+\\.[0-9]+' | sort -V | tail -1",
      shell=True, capture_output=True, text=True
    )

    version = result.stdout.strip() or "1.84.0"

    bin_dir = f"{base}/tailscale_{version}_{arch}"
    state = f"{base}/state"
    socket = f"{base}/tailscaled.sock"
    tgz_path = f"{base}/tailscale.tgz"

    tgz_url = f"https://pkgs.tailscale.com/stable/tailscale_{version}_{arch}.tgz"

    os.makedirs(state, exist_ok=True)

    run_cmd(["curl", "-fsSL", tgz_url, "-o", tgz_path], "Downloaded Tailscale archive.", "Failed to download Tailscale archive.")

    extract_tar(tgz_path, base)

    run_cmd(["cp", f"{bin_dir}/tailscale", f"{base}/tailscale"], "Copied tailscale binary.", "Failed to copy tailscale binary.")
    run_cmd(["cp", f"{bin_dir}/tailscaled", f"{base}/tailscaled"], "Copied tailscaled binary.", "Failed to copy tailscaled binary.")
    run_cmd(["chmod", "+x", f"{base}/tailscale", f"{base}/tailscaled"], "Made binaries executable.", "Failed to chmod binaries.")

    systemd_unit = f"""[Unit]
    Description=Tailscale node agent
    After=network.target

    [Service]
    ExecStart={base}/tailscaled \\
      --tun=userspace-networking \\
      --socks5-server=localhost:1055 \\
      --state={state}/tailscaled.state \\
      --socket={socket} \\
      --statedir={state}
    Restart=on-failure
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    """
    unit_tmp = f"{base}/tailscaled.service"
    with open(unit_tmp, "w") as f:
      f.write(systemd_unit)

    run_cmd(["sudo", "mount", "-o", "remount,rw", "/"], "Remounted / as read-write.", "Failed to remount / as read-write.")
    run_cmd(["sudo", "install", "-m", "644", unit_tmp, "/etc/systemd/system/tailscaled.service"], "Installed systemd unit.", "Failed to install systemd unit.")
    run_cmd(["sudo", "systemctl", "daemon-reload"], "Reloaded systemd daemon.", "Failed to reload systemd daemon.")
    run_cmd(["sudo", "systemctl", "enable", "/etc/systemd/system/tailscaled.service"], "Enabled tailscaled service.", "Failed to enable tailscaled service.")
    run_cmd(["sudo", "systemctl", "restart", "tailscaled"], "Started tailscaled service.", "Failed to start tailscaled service.")

    proc = subprocess.Popen(
      ["sudo", f"{base}/tailscale", "--socket", socket, "up", "--hostname", f"{HARDWARE.get_device_type()}-the-pond"],
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      preexec_fn=os.setsid
    )

    auth_url = None
    for line in proc.stdout:
      match = re.search(r"https://login\.tailscale\.com/\S+", line)
      if match and not auth_url:
        auth_url = match.group(0)
        run_cmd(["sudo", "kill", "-TERM", f"-{proc.pid}"], "Sent SIGTERM to Tailscale setup process.", "Failed to send SIGTERM to Tailscale setup process.")
        proc.wait(timeout=5)
        break

    return jsonify({
      "message": "Tailscale setup started. Please authenticate in your browser.",
      "auth_url": auth_url
    }), 200

  @app.route("/api/tailscale/uninstall", methods=["POST"])
  def tailscale_uninstall():
    base = "/data/tailscale"
    state = f"{base}/state"
    unit_path = "/etc/systemd/system/tailscaled.service"
    local_unit = f"{base}/tailscaled.service"

    run_cmd(["sudo", "mount", "-o", "remount,rw", "/"], "Remounted / as read-write.", "Failed to remount /.")
    run_cmd(["sudo", "systemctl", "stop", "tailscaled"], "Stopped tailscaled.", "Failed to stop tailscaled.")
    run_cmd(["sudo", "systemctl", "disable", "tailscaled"], "Disabled tailscaled.", "Failed to disable tailscaled.")

    if os.path.exists(unit_path):
      run_cmd(["sudo", "rm", unit_path], "Removed systemd unit file.", "Failed to remove systemd unit file.")
      run_cmd(["sudo", "systemctl", "daemon-reload"], "Reloaded systemd daemon.", "Failed to reload systemd.")

    delete_file(local_unit)

    for filename in ["tailscale", "tailscaled", "tailscale.tgz"]:
      delete_file(os.path.join(base, filename))

    for item in os.listdir(base):
      if item.startswith("tailscale_"):
        item_path = os.path.join(base, item)
        if os.path.isdir(item_path):
          run_cmd(["sudo", "rm", "-rf", item_path], f"Removed {item_path}.", f"Failed to remove {item_path}.")

    if os.path.exists(state):
      run_cmd(["sudo", "rm", "-rf", state], "Removed tailscale state dir.", "Failed to remove tailscale state dir.")

    if os.path.exists(base):
      run_cmd(["sudo", "rm", "-rf", base], "Removed tailscale dir.", "Failed to remove tailscale dir.")

    return jsonify({"message": "Tailscale uninstalled!"}), 200

  @app.route("/api/themes", methods=["POST"])
  def save_theme_route():
    theme_path, error = utilities.create_theme(request.form, request.files)
    if error:
      return jsonify({"message": error}), 400
    return jsonify({"message": f'Theme "{request.form.get("themeName")}" saved!'}), 200

  @app.route("/api/themes/download_asset", methods=["POST"])
  def start_download_asset():
    data = request.get_json() or {}
    raw_component = (data.get("component") or "").strip()
    display_name = (data.get("name") or "").strip()
    if not raw_component or not display_name:
      return jsonify({"error": "Missing component or name"}), 400

    component = "steering_wheels" if raw_component == "steering_wheel" else ("signals" if raw_component == "turn_signals" else raw_component)
    mem_key = THEME_COMPONENT_PARAMS.get(component)
    if not mem_key:
      return jsonify({"error": "Unknown component"}), 400

    slug = display_name.lower().replace("(", "").replace(")", "").replace(" ", "_")

    params_memory.put(mem_key, slug)
    params_memory.put("ThemeDownloadProgress", "Downloading...")

    return jsonify({"message": "Download started", "component": component, "param": mem_key, "slug": slug}), 200

  @app.route("/api/themes/apply", methods=["POST"])
  def apply_theme():
    try:
      form_data = request.form.to_dict(flat=True)
      files = request.files

      if not form_data.get("themeName"):
        form_data["themeName"] = f"tmp_{secrets.token_hex(8)}"

      temp_path, error = utilities.create_theme(form_data, files, temporary=True)
      if error:
        return jsonify({"error": error}), 400

      save_checklist = json.loads(form_data.get("saveChecklist", "{}"))

      if save_checklist.get("colors") and temp_path is not None:
        asset_location = temp_path / "colors"
        save_location = ACTIVE_THEME_PATH / "colors"
        if save_location.exists() or save_location.is_symlink():
          delete_file(save_location)
        if asset_location.exists():
          save_location.parent.mkdir(parents=True, exist_ok=True)
          save_location.symlink_to(asset_location, target_is_directory=True)

      if save_checklist.get("distance_icons") and temp_path is not None:
        asset_location = temp_path / "distance_icons"
        save_location = ACTIVE_THEME_PATH / "distance_icons"
        if save_location.exists() or save_location.is_symlink():
          delete_file(save_location)
        if asset_location.exists():
          save_location.parent.mkdir(parents=True, exist_ok=True)
          save_location.symlink_to(asset_location, target_is_directory=True)

      if save_checklist.get("icons") and temp_path is not None:
        asset_location = temp_path / "icons"
        save_location = ACTIVE_THEME_PATH / "icons"
        if save_location.exists() or save_location.is_symlink():
          delete_file(save_location)
        if asset_location.exists():
          save_location.parent.mkdir(parents=True, exist_ok=True)
          save_location.symlink_to(asset_location, target_is_directory=True)

      if save_checklist.get("sounds") and temp_path is not None:
        asset_location = temp_path / "sounds"
        save_location = ACTIVE_THEME_PATH / "sounds"
        if save_location.exists() or save_location.is_symlink():
          delete_file(save_location)
        if asset_location.exists():
          save_location.parent.mkdir(parents=True, exist_ok=True)
          save_location.symlink_to(asset_location, target_is_directory=True)

      if save_checklist.get("turn_signals") and temp_path is not None:
        asset_location = temp_path / "signals"
        save_location = ACTIVE_THEME_PATH / "signals"
        if save_location.exists() or save_location.is_symlink():
          delete_file(save_location)
        if asset_location.exists():
          save_location.parent.mkdir(parents=True, exist_ok=True)
          save_location.symlink_to(asset_location, target_is_directory=True)

      wheel_location = (temp_path / "WheelIcon") if temp_path is not None else None
      wheel_save_location = ACTIVE_THEME_PATH / "steering_wheel"
      if wheel_location is not None and wheel_location.exists():
        if wheel_save_location.exists():
          delete_file(wheel_save_location)

        wheel_save_location.mkdir(parents=True, exist_ok=True)
        for file in wheel_location.iterdir():
          destination_file = wheel_save_location / file.name
          delete_file(destination_file)
          destination_file.symlink_to(file)

      params.put_bool("CustomThemes", True)
      params_memory.put_bool("UseActiveTheme", True)

      update_starpilot_toggles()
      return jsonify({"message": "Theme applied successfully!"}), 200
    except Exception as e:
      return jsonify({"error": f"Failed to apply theme: {e}"}), 500

  def _resolve_stock_theme_asset_path(asset_path):
    stock_asset_path = STOCK_THEME_PATH / asset_path
    if stock_asset_path.exists():
      return stock_asset_path

    stock_fallbacks = {
      "steering_wheel/wheel.png": STOCK_THEME_PATH.parents[2] / "selfdrive" / "assets" / "icons" / "chffr_wheel.png",
    }

    fallback_path = stock_fallbacks.get(asset_path)
    if fallback_path is not None and fallback_path.exists():
      return fallback_path

    return stock_asset_path

  @app.route("/api/themes/asset/<path:theme>/<path:asset_path>")
  def get_theme_asset(theme, asset_path):
    theme_type = request.args.get("type", "")

    if theme_type == "active" or theme == "__active__":
      file_path = ACTIVE_THEME_PATH / asset_path
    elif theme_type == "stock" or theme == "__stock__":
      file_path = _resolve_stock_theme_asset_path(asset_path)
    elif asset_path.startswith("steering_wheels/"):
      file_path = THEME_SAVE_PATH / asset_path
    elif asset_path.startswith("steering_wheel/") and "holiday" in theme_type:
      file_path = HOLIDAY_THEME_PATH / theme / asset_path
    else:
      base_dir = HOLIDAY_THEME_PATH / theme if "holiday" in theme_type else THEME_SAVE_PATH / "theme_packs" / theme
      file_path = base_dir / asset_path

    if not file_path.exists():
      return "File not found", 404

    return send_file(file_path, as_attachment=False)

  @app.route("/api/themes/delete/<path:theme_path_str>", methods=["DELETE"])
  def delete_theme(theme_path_str):
    theme_type = request.args.get("type", "user")
    component = (request.args.get("component") or "").strip()

    if theme_type == "holiday":
      return jsonify({"message": "Cannot delete holiday themes."}), 403

    if theme_type == "steering_wheel":
      wheel_path = THEME_SAVE_PATH / "steering_wheels" / theme_path_str
      if wheel_path.exists():
        delete_file(wheel_path)
        return jsonify({"message": f'Steering wheel "{utilities.normalize_theme_name(wheel_path.stem)}" deleted!'}), 200
      return jsonify({"message": "Steering wheel not found..."}), 404

    theme_path = THEME_SAVE_PATH / "theme_packs" / theme_path_str
    if not theme_path.is_dir():
      return jsonify({"message": "Theme not found..."}), 404

    if component:
      allowed = {"colors", "distance_icons", "icons", "sounds", "signals"}
      if component not in allowed:
        return jsonify({"message": "Unknown component..."}), 400

      target = theme_path / component
      if not target.exists():
        return jsonify({"message": f'Component "{component}" not found in theme...'}), 404

      delete_file(target)

      return jsonify({"message": f'Removed {component.replace("_", " ")} from "{utilities.normalize_theme_name(theme_path.name)}"!'}), 200

    delete_file(theme_path)
    return jsonify({"message": f'Theme "{utilities.normalize_theme_name(theme_path.name)}" deleted!'}), 200

  @app.route("/api/themes/default", methods=["GET"])
  def get_default_theme():
    theme_data = {
      "colors": {},
      "images": {},
      "sounds": {},
      "turnSignalLength": 100,
      "turnSignalType": "Single Image",
      "sequentialImages": [],
      "theme_names": {}
    }

    if not params.get_bool("CustomThemes"):
      theme_data["theme_names"] = {
        "colors": "Stock",
        "distanceIcons": "Stock",
        "icons": "Stock",
        "sounds": "Stock",
        "turnSignals": "Stock",
        "steeringWheel": "Stock"
      }
    else:
      theme_param_map = {
        "ColorScheme": "colors",
        "DistanceIconPack": "distanceIcons",
        "IconPack": "icons",
        "SoundPack": "sounds",
        "SignalAnimation": "turnSignals",
        "WheelIcon": "steeringWheel"
      }
      for param, theme_key in theme_param_map.items():
        param_value = params.get(param, encoding="utf-8")
        if param_value:
          theme_data["theme_names"][theme_key] = utilities.normalize_theme_name(param_value)

    colors_path = ACTIVE_THEME_PATH / "colors" / "colors.json"
    if colors_path.exists():
      with open(colors_path, "r") as f:
        theme_data["colors"] = json.load(f)

    signals_dir = ACTIVE_THEME_PATH / "signals"
    if signals_dir.exists():
      sequential_files = sorted([f.name for f in signals_dir.glob("turn_signal_*.png") if "blindspot" not in f.name.lower()])
      if sequential_files:
        theme_data["sequentialImages"] = sequential_files
        theme_data["turnSignalType"] = "Sequential"

      theme_data["turnSignalStyle"] = "Traditional"
      theme_data["turnSignalLength"] = 100

      for file in os.listdir(signals_dir):
        if not any(file.endswith(ext) for ext in [".png", ".gif", ".jpg", ".jpeg"]):
          parts = file.split("_")
          if len(parts) == 2:
            theme_data["turnSignalStyle"] = parts[0].capitalize()
            try:
              theme_data["turnSignalLength"] = int(parts[1])
            except ValueError:
              pass
          break

      exts = [".png", ".gif", ".jpg", ".jpeg"]
      for ext in exts:
        p = signals_dir / f"turn_signal{ext}"
        if p.exists():
          theme_data["images"]["turnSignal"] = f"turn_signal{ext}"
          break
      for ext in exts:
        p = signals_dir / f"turn_signal_blindspot{ext}"
        if p.exists():
          theme_data["images"]["turnSignalBlindspot"] = f"turn_signal_blindspot{ext}"
          break

    icons_path = ACTIVE_THEME_PATH / "icons"
    if icons_path.exists() and icons_path.is_dir():
      for file in os.listdir(icons_path):
        if Path(file).stem == "button_settings":
          theme_data["images"]["settingsButton"] = file
        elif Path(file).stem == "button_home":
          theme_data["images"]["homeButton"] = file

    wheel_path = ACTIVE_THEME_PATH / "steering_wheel"
    if wheel_path.exists() and wheel_path.is_dir():
      wheel_files = list(wheel_path.glob("wheel.*"))
      if wheel_files:
        theme_data["images"]["steeringWheel"] = wheel_files[0].name

    distance_icons_path = ACTIVE_THEME_PATH / "distance_icons"
    if distance_icons_path.exists() and distance_icons_path.is_dir():
      theme_data["images"]["distanceIcons"] = {}
      for file in os.listdir(distance_icons_path):
        key = Path(file).stem
        if key in ["traffic", "aggressive", "standard", "relaxed"]:
          theme_data["images"]["distanceIcons"][key] = file

    sounds_path = ACTIVE_THEME_PATH / "sounds"
    if sounds_path.exists() and sounds_path.is_dir():
      valid_sound_keys = ["engage", "disengage", "prompt", "startup"]
      for file in os.listdir(sounds_path):
        stem = Path(file).stem
        if stem in valid_sound_keys:
          theme_data["sounds"][stem] = file

    return jsonify(theme_data)

  @app.route("/api/themes/download", methods=["POST"])
  def download_theme_route():
    theme_path, error = utilities.create_theme(request.form, request.files, temporary=True)
    if error:
      return jsonify({"message": error}), 400

    sane_theme_name = utilities.normalize_theme_name(request.form.get("themeName"), for_path=True)

    archive_path = shutil.make_archive(str(theme_path.parent / sane_theme_name), "zip", theme_path.parent, sane_theme_name)

    memory_file = BytesIO()
    with open(archive_path, "rb") as f:
      memory_file.write(f.read())
    memory_file.seek(0)

    delete_file(theme_path.parent)

    return send_file(memory_file, download_name=f'{sane_theme_name}.zip', as_attachment=True)

  @app.route("/api/themes/list", methods=["GET"])
  def list_themes():
    all_themes = []
    themes_path = THEME_SAVE_PATH / "theme_packs"

    if themes_path.exists():
      for theme_dir in themes_path.iterdir():
        if theme_dir.is_dir():
          is_user_created = "-user_created" in theme_dir.name
          components = utilities.check_theme_components(theme_dir)
          all_themes.append({
            "name": utilities.normalize_theme_name(theme_dir.name),
            "path": theme_dir.name,
            "type": "user" if is_user_created else "standard",
            "is_user_created": is_user_created,
            **components
          })

    if HOLIDAY_THEME_PATH.exists():
      for theme_dir in HOLIDAY_THEME_PATH.iterdir():
        if theme_dir.is_dir():
          components = utilities.check_theme_components(theme_dir)
          all_themes.append({
            "name": utilities.normalize_theme_name(theme_dir.name),
            "path": theme_dir.name,
            "type": "holiday",
            "is_user_created": False,
            **components
          })

    wheels_path = THEME_SAVE_PATH / "steering_wheels"
    if wheels_path.exists():
      for wheel_file in wheels_path.iterdir():
        all_themes.append({
          "name": utilities.normalize_theme_name(wheel_file.stem),
          "path": wheel_file.name,
          "type": "steering_wheel",
          "is_user_created": "-user_created" in wheel_file.name,
          "hasSteeringWheel": True,
        })

    return jsonify({"themes": sorted(all_themes, key=lambda x: x['name'])})

  @app.route("/api/themes/load/<path:theme_path>")
  def load_theme(theme_path):
    theme_type = request.args.get("type", "")
    if theme_type == "stock" or theme_path == "__stock__":
      theme_dir = STOCK_THEME_PATH
    else:
      theme_dir = HOLIDAY_THEME_PATH / theme_path if "holiday" in theme_type else THEME_SAVE_PATH / "theme_packs" / theme_path

    response_data = {
      "colors": None,
      "images": {},
      "sounds": {},
      "sequentialImages": [],
      "turnSignalType": "Single Image",
      "turnSignalStyle": "Static",
      "turnSignalLength": 100
    }

    colors_file = theme_dir / "colors" / "colors.json"
    if colors_file.exists():
      with open(colors_file) as f:
        response_data["colors"] = json.load(f)

    icons_dir = theme_dir / "icons"
    if icons_dir.exists():
      for base_name, response_key in [("button_home", "homeButton"), ("button_settings", "settingsButton")]:
        for ext in [".gif", ".png", ".jpg", ".jpeg"]:
          filename = f"{base_name}{ext}"
          if (icons_dir / filename).exists():
            response_data["images"][response_key] = {
              "filename": filename,
              "path": f"icons/{filename}"
            }
            break

    distance_dir = theme_dir / "distance_icons"
    if distance_dir.exists():
      response_data["images"]["distanceIcons"] = {}
      exts = [".png", ".gif", ".jpg", ".jpeg"]
      for name in ["aggressive", "relaxed", "standard", "traffic"]:
        for ext in exts:
          p = distance_dir / f"{name}{ext}"
          if p.exists():
            response_data["images"]["distanceIcons"][name] = {
              "filename": f"{name}{ext}",
              "path": f"distance_icons/{name}{ext}"
            }
            break

    signals_dir = theme_dir / "signals"
    if signals_dir.exists():
      sequential_files = sorted([f.name for f in signals_dir.glob("turn_signal_*.png") if "blindspot" not in f.name.lower()])
      if sequential_files:
        response_data["sequentialImages"] = sequential_files
        response_data["turnSignalType"] = "Sequential"

      response_data["turnSignalStyle"] = "Traditional"
      response_data["turnSignalLength"] = 100

      for file in os.listdir(signals_dir):
        if not any(file.endswith(ext) for ext in [".png", ".gif", ".jpg", ".jpeg"]):
          parts = file.split("_")
          if len(parts) == 2:
            response_data["turnSignalStyle"] = parts[0].capitalize()
            try:
              response_data["turnSignalLength"] = int(parts[1])
            except ValueError:
              pass
            break

      exts = [".png", ".gif", ".jpg", ".jpeg"]
      for ext in exts:
        p = signals_dir / f"turn_signal{ext}"
        if p.exists():
          response_data["images"]["turnSignal"] = {
            "filename": f"turn_signal{ext}",
            "path": f"signals/turn_signal{ext}",
          }
          break
      for ext in exts:
        p = signals_dir / f"turn_signal_blindspot{ext}"
        if p.exists():
          response_data["images"]["turnSignalBlindspot"] = {
            "filename": f"turn_signal_blindspot{ext}",
            "path": f"signals/turn_signal_blindspot{ext}",
          }
          break

    sounds_dir = theme_dir / "sounds"
    if sounds_dir.exists():
      for name in ["engage", "disengage", "startup", "prompt"]:
        file_path = sounds_dir / f"{name}.wav"
        if file_path.exists():
          response_data["sounds"][name] = {
            "filename": f"{name}.wav",
            "path": f"sounds/{name}.wav"
          }

    steering_wheel_path = None
    if theme_type == "stock" or theme_path == "__stock__":
      if _resolve_stock_theme_asset_path("steering_wheel/wheel.png").exists():
        steering_wheel_path = "steering_wheel/wheel.png"
    elif "holiday" in theme_type:
      steering_dir = theme_dir / "steering_wheel"
      if steering_dir.exists() and steering_dir.is_dir():
        for file in steering_dir.iterdir():
          if file.is_file() and file.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]:
            steering_wheel_path = f"steering_wheel/{file.name}"
            break
    else:
      steering_wheels_dir = THEME_SAVE_PATH / "steering_wheels"
      if steering_wheels_dir.exists():
        for file in steering_wheels_dir.iterdir():
          if file.is_file() and file.stem.lower() == theme_path.lower() and file.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]:
            steering_wheel_path = f"steering_wheels/{file.name}"
            break

    if steering_wheel_path:
      response_data["images"]["steeringWheel"] = {
        "filename": steering_wheel_path.split("/")[-1],
        "path": steering_wheel_path
      }

    return jsonify(response_data)

  @app.route("/api/themes/submit", methods=["POST"])
  def submit_theme():
    if not GITLAB_TOKEN:
      return jsonify({"error": "Missing GitLab token"}), 500

    try:
      theme_name = request.form.get("themeName")
      if not theme_name:
        return jsonify({"error": "Missing theme name"}), 400

      discord_username = request.form.get("discordUsername") or "Unknown"

      theme_path, error = utilities.create_theme(request.form, request.files, temporary=True)
      if error:
        return jsonify({"message": error}), 400

      safe_theme_name = utilities.normalize_theme_name(theme_name, for_path=True)
      combined_name = f"{safe_theme_name}~{discord_username}"
      timestamp = int(time.time())

      def gitlab_post(project_id, endpoint, payload):
        url = f"{GITLAB_API}/projects/{project_id}/{endpoint}"
        resp = requests.post(url, headers={"PRIVATE-TOKEN": GITLAB_TOKEN}, json=payload)
        if resp.status_code not in (200, 201):
          raise RuntimeError(f"GitLab API error {resp.status_code}: {resp.text}")
        return resp.json()

      def encode_file_base64(path):
        with open(path, "rb") as f:
          return base64.b64encode(f.read()).decode("utf-8")

      def send_discord_notification(username, theme_name, asset_types):
        if not DISCORD_WEBHOOK_URL:
          return

        message = (
          f"🎨 **New Theme Submission**\n"
          f"User: `{username}`\n"
          f"Theme: `{theme_name}`\n"
          f"Assets: {', '.join(asset_types)}\n"
          f"[View Submissions Repo](https://gitlab.com/{RESOURCES_REPO}-Submissions)\n"
          f"<@263565721336807424>"
        )
        payload = {"content": message}
        try:
          resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
          if resp.status_code not in (200, 204):
            print(f"Discord notification failed: {resp.status_code} {resp.text}")
        except Exception as exception:
          print(f"Error sending Discord message: {exception}")

      asset_types = []
      submission_urls = {}

      distance_icons_path = theme_path / "distance_icons"
      if distance_icons_path.exists() and any(distance_icons_path.iterdir()):
        zip_path = shutil.make_archive(str(distance_icons_path), "zip", distance_icons_path)
        encoded = encode_file_base64(zip_path)
        file_name = f"{combined_name}.zip"
        actions = [
          {
            "action": "create",
            "file_path": file_name,
            "content": encoded,
            "encoding": "base64"
          }
        ]
        commit_payload = {
          "branch": "Distance-Icons",
          "commit_message": f"Added Distance Icons: {combined_name}",
          "actions": actions
        }
        gitlab_post(GITLAB_SUBMISSIONS_PROJECT_ID, "repository/commits", commit_payload)
        asset_types.append("Distance Icons")
        submission_urls["distance_icons"] = f"https://gitlab.com/{RESOURCES_REPO}-Submissions/-/tree/Distance-Icons"

      theme_actions = []
      for folder in ["colors", "icons", "signals", "sounds"]:
        folder_path = theme_path / folder
        if folder_path.exists() and any(folder_path.iterdir()):
          zip_path = shutil.make_archive(str(folder_path), "zip", folder_path)
          encoded = encode_file_base64(zip_path)
          file_path = f"{combined_name}/{folder}.zip"
          theme_actions.append({
            "action": "create",
            "file_path": file_path,
            "content": encoded,
            "encoding": "base64"
          })

      if theme_actions:
        commit_payload = {
          "branch": "Themes",
          "commit_message": f"Added Theme: {combined_name}",
          "actions": theme_actions
        }
        gitlab_post(GITLAB_SUBMISSIONS_PROJECT_ID, "repository/commits", commit_payload)
        asset_types.append("Theme")
        submission_urls["theme"] = f"https://gitlab.com/{RESOURCES_REPO}-Submissions/-/tree/Themes"

      wheel_file = request.files.get("steeringWheel")
      if wheel_file and wheel_file.filename:
        suffix = Path(wheel_file.filename).suffix
        file_name = f"{combined_name}{suffix}"
        wheel_file.seek(0)
        encoded_wheel = base64.b64encode(wheel_file.read()).decode("utf-8")
        actions = [
          {
            "action": "create",
            "file_path": file_name,
            "content": encoded_wheel,
            "encoding": "base64"
          }
        ]
        commit_payload = {
          "branch": "Steering-Wheels",
          "commit_message": f"Added Steering Wheel: {combined_name}",
          "actions": actions
        }
        gitlab_post(GITLAB_SUBMISSIONS_PROJECT_ID, "repository/commits", commit_payload)
        asset_types.append("Steering Wheel")
        submission_urls["steering_wheel"] = f"https://gitlab.com/{RESOURCES_REPO}-Submissions/-/tree/Steering-Wheels"

      if not submission_urls:
        return jsonify({"error": "No valid theme data or steering wheel file provided"}), 400

      send_discord_notification(discord_username, theme_name, asset_types)

      return jsonify({
        "message": "Submission successful!",
        "branches": submission_urls
      }), 200

    except Exception as exception:
      return jsonify({"error": str(exception)}), 500

    finally:
      if "theme_path" in locals() and theme_path.parent.exists():
        delete_file(theme_path.parent)

  @app.route("/api/tmux_log/capture", methods=["POST"])
  def capture_tmux_log_route():
    TMUX_LOGS_PATH.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"tmux_log_{timestamp}.json"
    log_path = TMUX_LOGS_PATH / log_filename

    run_cmd(["tmux", "capture-pane", "-J", "-S", "-"], "Captured tmux pane.", "Failed to capture tmux pane.")

    result = subprocess.run(["tmux", "show-buffer"], capture_output=True, text=True, check=True)
    log_path.write_text(result.stdout, encoding="utf-8")

    run_cmd(["tmux", "delete-buffer"], "Deleted tmux buffer.", "Failed to delete tmux buffer.")
    return jsonify({"message": "Captured console log successfully!", "log_file": log_filename}), 200

  @app.route("/api/tmux_log/delete/<filename>", methods=["DELETE"])
  def delete_tmux_log(filename):
    file_path = TMUX_LOGS_PATH / filename
    if file_path.exists():
      delete_file(file_path)
      return jsonify({"message": f"{filename} deleted!"}), 200

    return jsonify({"error": "File not found"}), 404

  @app.route("/api/tmux_log/delete_all", methods=["DELETE"])
  def delete_all_tmux_logs():
    if TMUX_LOGS_PATH.exists():

      delete_file(TMUX_LOGS_PATH)

    TMUX_LOGS_PATH.mkdir(parents=True, exist_ok=True)
    return jsonify({"message": "All tmux logs deleted!"}), 200

  @app.route("/api/tmux_log/download/<path:filename>", methods=["GET"])
  def download_tmux_log(filename):
    return send_from_directory(str(TMUX_LOGS_PATH), filename, as_attachment=True)

  @app.route("/api/tmux_log/list", methods=["GET"])
  def list_tmux_logs():
    TMUX_LOGS_PATH.mkdir(parents=True, exist_ok=True)
    files = sorted(TMUX_LOGS_PATH.glob("*.json"), key=lambda file: file.stat().st_mtime, reverse=True)
    return jsonify([{"filename": file.name, "timestamp": file.stat().st_mtime} for file in files])

  @app.route("/api/tmux_log/live", methods=["GET"])
  def stream_tmux_log():
    if subprocess.run(["tmux", "has-session", "-t", "comma"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
      run_cmd(["tmux", "new-session", "-d", "-s", "comma", "-x", "240", "-y", "70", "bash"], "Started tmux session", "Failed to start tmux session")
    else:
      run_cmd(["tmux", "resize-window", "-t", "comma:0", "-x", "240", "-y", "70"], "Resized tmux window", "Failed to resize tmux window")

    def generate():
      last_output = ""
      last_keepalive = 0.0
      while True:
        output = subprocess.check_output(["tmux", "capture-pane", "-t", "comma:0", "-p", "-S", "-1000"], text=True)

        if output != last_output:
          yield "data: " + "\n".join(reversed(output.splitlines())).replace("\n", "\ndata: ") + "\n\n"
          last_output = output
          last_keepalive = time.monotonic()
        elif (time.monotonic() - last_keepalive) >= 5.0:
          # Keep SSE alive through proxies/tunnels even when output is unchanged.
          yield ": keepalive\n\n"
          last_keepalive = time.monotonic()

        time.sleep(0.5)
    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

  @app.route("/api/tmux_log/snapshot", methods=["GET"])
  def snapshot_tmux_log():
    try:
      output = subprocess.check_output(["tmux", "capture-pane", "-t", "comma:0", "-p", "-S", "-1000"], text=True)
    except subprocess.CalledProcessError:
      run_cmd(["tmux", "new-session", "-d", "-s", "comma", "-x", "240", "-y", "70", "bash"], "Started tmux session", "Failed to start tmux session")
      output = subprocess.check_output(["tmux", "capture-pane", "-t", "comma:0", "-p", "-S", "-1000"], text=True)
    except Exception as e:
      return jsonify({"error": str(e)}), 500

    try:
      live_text = "\n".join(reversed(output.splitlines()))
      return jsonify({"data": live_text}), 200
    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route("/api/tmux_log/rename/<old>/<new>", methods=["PUT"])
  def rename_tmux_log_path_params(old, new):
    old_path = TMUX_LOGS_PATH / old
    new_safe = utilities.secure_filename(new)
    new_path = TMUX_LOGS_PATH / new_safe

    if not old_path.exists():
      return jsonify({"error": "Original file not found"}), 404

    if new_path.exists():
      return jsonify({"error": "Target file already exists"}), 400

    old_path.rename(new_path)

    return jsonify({"message": f"Renamed {old} to {new_safe}!"}), 200


  @app.route("/api/tsk_keys", methods=["DELETE"])
  def delete_secoc_key():
    name = request.args.get("name")
    keys = json.loads(params.get("SecOCKeys") or "[]")
    keys = [key for key in keys if key.get("name") != name]
    params.put("SecOCKeys", json.dumps(keys))
    return jsonify(keys)

  @app.route("/api/tsk_keys", methods=["GET"])
  def get_secoc_keys():
    return jsonify(json.loads(params.get("SecOCKeys", encoding="utf-8", default="[]")))

  @app.route("/api/tsk_keys", methods=["POST"])
  def save_secoc_keys():
    keys = request.get_json() or []
    params.put("SecOCKeys", json.dumps(keys))

    return jsonify(keys)

  @app.route("/api/tsk_key_set", methods=["POST"])
  def set_secoc_key():
    data = request.get_json()
    if not data or "value" not in data:
      return jsonify({"error": "Missing key value"}), 400

    value = data["value"]
    if not isinstance(value, str):
      return jsonify({"error": "Key value must be a string"}), 400

    params.put("SecOCKey", value)

    return "", 204

  @app.route("/api/toggles/backup", methods=["POST"])
  def backup_toggle_values():
    toggle_values = {}
    for key, _, _, _ in starpilot_default_params:
      if key in EXCLUDED_KEYS:
        continue

      raw_value = params.get(key)
      if isinstance(raw_value, bytes):
        value = raw_value.decode("utf-8", errors="replace")
      else:
        value = raw_value or "0"

      toggle_values[key] = value

    encoded = utilities.encode_parameters(toggle_values)
    wrapped = json.dumps({"data": encoded}, indent=2)

    buffer = BytesIO(wrapped.encode("utf-8"))
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="toggle_backup.json", mimetype="application/json")

  @app.route("/api/toggles/restore", methods=["POST"])
  def restore_toggle_values():
    request_data = request.get_json()
    if not request_data or "data" not in request_data:
      return jsonify({"success": False, "message": "Missing 'data' in request."}), 400

    allowed_keys = {key for key, _, _, _ in starpilot_default_params if key not in EXCLUDED_KEYS}

    toggle_values = utilities.decode_parameters(request_data["data"])
    for key, value in toggle_values.items():
      mapped_key = LEGACY_STARPILOT_PARAM_RENAMES.get(key, key)
      if mapped_key in allowed_keys:
        params.put(mapped_key, value)

    update_starpilot_toggles()
    return jsonify({"success": True, "message": "Toggles restored!"})

  @app.route("/api/toggles/reset_default", methods=["POST"])
  def reset_toggle_values():
    params.put_bool("DoToggleReset", True)
    HARDWARE.reboot()

  @app.route("/api/toggles/reset_stock", methods=["POST"])
  def reset_toggle_values_to_stock():
    params.put_bool("DoToggleResetStock", True)
    HARDWARE.reboot()

  @app.route("/mapbox-help/<path:filename>", methods=["GET"])
  def serve_mapbox_help(filename):
    return send_from_directory("/data/openpilot/starpilot/navigation/navigation_training", filename)

  @app.route("/playground", methods=["GET"])
  def playground():
    return render_template("playground.html")

  @app.route("/thumbnails/<path:file_path>", methods=["GET"])
  def get_thumbnail(file_path):
    for footage_path in FOOTAGE_PATHS:
      if os.path.exists(os.path.join(footage_path, file_path)):
        return send_from_directory(footage_path, file_path, as_attachment=True)
    return {"error": "Thumbnail not found"}, 404

  @app.route("/video/<path>", methods=["GET"])
  def get_video(path):
    camera = request.args.get("camera")
    filename = {"driver": "dcamera.hevc", "wide": "ecamera.hevc"}.get(camera, "fcamera.hevc")
    for footage_path in FOOTAGE_PATHS:
      filepath = f"{footage_path}{path}/{filename}"
      if os.path.exists(filepath):
        file_handle = utilities.ffmpeg_mp4_wrap_process_builder(filepath)

        file_handle.seek(0, 2)
        file_size = file_handle.tell()
        file_handle.seek(0)

        range_header = request.headers.get('Range', None)
        if range_header:
          byte_start = 0
          byte_end = file_size - 1

          if range_header.startswith('bytes='):
            range_spec = range_header[6:]
            if '-' in range_spec:
              start, end = range_spec.split('-', 1)
              if start:
                byte_start = max(0, int(start))
              if end:
                byte_end = min(file_size - 1, int(end))

          if byte_start >= file_size:
            file_handle.close()
            return Response("Requested Range Not Satisfiable", 416)

          byte_end = max(byte_start, byte_end)

          file_handle.seek(byte_start)
          read_length = byte_end - byte_start + 1
          data = file_handle.read(read_length)

          response = Response(
            data,
            206,
            headers={
              'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
              'Accept-Ranges': 'bytes',
              'Content-Length': str(len(data)),
              'Content-Type': 'video/mp4'
            }
          )
        else:
          data = file_handle.read()
          response = Response(
            data,
            200,
            headers={
              'Accept-Ranges': 'bytes',
              'Content-Length': str(file_size),
              'Content-Type': 'video/mp4'
            }
          )

        file_handle.close()
        return response
    return {"error": "Video not found"}, 404

def main():
  while not _ensure_pond_web_deps():
    print(f"The Pond waiting for Flask dependency ({_POND_WEB_DEPS_ERROR}); retrying in 60s.")
    time.sleep(60)

  app = Flask(__name__, static_folder="assets", static_url_path="/assets")
  setup(app)

  # Desktop-only debug mode. On-device must stay on 8082 to match Galaxy FRP routing.
  debug = not _is_comma_device_runtime()
  port = 8083 if debug else 8082

  if debug:
    print("\"The Pond\" is not running on a comma device, enabling debug mode")

  app.secret_key = secrets.token_hex(32)
  app.run(host="0.0.0.0", port=port, debug=debug)

if __name__ == "__main__":
  main()
