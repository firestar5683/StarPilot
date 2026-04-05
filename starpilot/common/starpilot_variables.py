#!/usr/bin/env python3
import json
import math
import os
import random
import tomllib

from functools import cache
from pathlib import Path
from types import SimpleNamespace

import cereal.messaging as messaging
import numpy as np

from cereal import car, custom, log
from opendbc.car import gen_empty_fingerprint
from opendbc.car.car_helpers import interfaces
from opendbc.car.gm.values import CAR as GM_CAR, EV_CAR as GM_EV_CAR, GMFlags
from opendbc.car.hyundai.values import EV_CAR as HYUNDAI_EV_CAR, HyundaiFlags
from opendbc.car.interfaces import TORQUE_SUBSTITUTE_PATH, CarInterfaceBase, GearShifter
from opendbc.car.mock.values import CAR as MOCK
from opendbc.car.subaru.values import SubaruFlags
from opendbc.car.toyota.values import ToyotaStarPilotFlags
from openpilot.common.basedir import BASEDIR
from openpilot.common.constants import CV
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib.latcontrol_torque import KP
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.starpilot.common.accel_profile import (
  ACCELERATION_PROFILES,
  CUSTOM_ACCEL_PROFILE_PARAM_KEYS,
  CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY,
  CUSTOM_ACCEL_PROFILE_VALUE_MAX,
  CUSTOM_ACCEL_PROFILE_VALUE_MIN,
  DECELERATION_PROFILES,
  build_custom_accel_profile_defaults,
  custom_accel_profile_is_initialized,
  normalize_acceleration_profile,
  normalize_deceleration_profile,
)
from openpilot.system.hardware import HARDWARE
from openpilot.system.hardware.hw import Paths
from openpilot.system.hardware.power_monitoring import VBATT_PAUSE_CHARGING
from openpilot.system.version import get_build_metadata

CITY_SPEED_LIMIT = 25                     # 55mph is typically the minimum speed for highways
CRUISING_SPEED = 5                        # Roughly the speed cars go when not touching the gas while in drive
DEFAULT_LATERAL_ACCELERATION = 2.0        # m/s^2, typical lateral acceleration when taking curves
DISPLAY_MENU_TIMER = 350                  # The length of time the following distance menu appears on some GM vehicles to prevent things getting out of sync
EARTH_RADIUS = 6378137                    # Radius of the Earth in meters
MAX_ACCELERATION = 4.0                    # ISO 15622:2018
MAX_T_FOLLOW = 3.0                        # Maximum allowed following duration. Larger values risk losing track of the lead but may be increased as models improve
MINIMUM_LATERAL_ACCELERATION = 1.3        # m/s^2, typical minimum lateral acceleration when taking curves
PLANNER_TIME = ModelConstants.T_IDXS[-1]  # Length of time the model projects out for
THRESHOLD = 1 - 1 / math.e                # Requires the condition to be true for ~1 second

NON_DRIVING_GEARS = [GearShifter.neutral, GearShifter.park, GearShifter.reverse, GearShifter.unknown]

# Temporary fallback until the weather-compatible API is hosted locally.
STARPILOT_API = os.getenv("STARPILOT_API", "https://frogpilot.com/api")

LEGACY_CARMODEL_MIGRATIONS = {
  "CHEVROLET_BOLT_CC_2019_2021": "CHEVROLET_BOLT_CC_2018_2021",
}

LEGACY_STARPILOT_PARAM_RENAMES = {
  "FrogPilotApiToken": "StarPilotApiToken",
  "FrogPilotCarParams": "StarPilotCarParams",
  "FrogPilotCarParamsPersistent": "StarPilotCarParamsPersistent",
  "FrogPilotDongleId": "StarPilotDongleId",
  "FrogPilotStats": "StarPilotStats",
}

LEGACY_STARPILOT_STATS_KEY_RENAMES = {
  "FrogPilotDrives": "StarPilotDrives",
  "FrogPilotMeters": "StarPilotMeters",
  "FrogPilotSeconds": "StarPilotSeconds",
}

RESOURCES_REPO = os.getenv("STARPILOT_RESOURCES_REPO", "firestar5683/StarPilot-Resources")

ACTIVE_THEME_PATH = Path(BASEDIR) / "starpilot/assets/active_theme"
METADATAS_PATH = Path(BASEDIR) / "starpilot/assets/model_metadata"
RANDOM_EVENTS_PATH = Path(BASEDIR) / "starpilot/assets/random_events"
STOCK_THEME_PATH = Path(BASEDIR) / "starpilot/assets/stock_theme"
THEME_COLORS_PATH = (ACTIVE_THEME_PATH / "colors/colors.json")
if HARDWARE.get_device_type() == "pc":
  _FP_PC_ROOT = Path(Paths.comma_home()) / "starpilot"
  _FP_DATA_ROOT = _FP_PC_ROOT / "data"
  _FP_CACHE_ROOT = _FP_PC_ROOT / "cache"
  _FP_PERSIST_ROOT = Path(Paths.persist_root())
else:
  _FP_DATA_ROOT = Path("/data")
  _FP_CACHE_ROOT = Path("/cache")
  _FP_PERSIST_ROOT = Path("/persist")

MODELS_PATH = _FP_DATA_ROOT / "models"
THEME_SAVE_PATH = _FP_DATA_ROOT / "themes"

ERROR_LOGS_PATH = _FP_DATA_ROOT / "error_logs"
SCREEN_RECORDINGS_PATH = _FP_DATA_ROOT / "media/screen_recordings"
VIDEO_CACHE_PATH = _FP_DATA_ROOT / "video_cache"

BACKUP_PATH = _FP_CACHE_ROOT / "on_backup"
STARPILOT_BACKUPS = _FP_DATA_ROOT / "backups"
TOGGLE_BACKUPS = _FP_DATA_ROOT / "toggle_backups"

FROGS_GO_MOO_PATH = _FP_PERSIST_ROOT / "frogsgomoo.py"

HD_LOGS_PATH = _FP_DATA_ROOT / "media/0/realdata_HD"
HD_PATH = _FP_CACHE_ROOT / "use_HD"

KONIK_LOGS_PATH = _FP_DATA_ROOT / "media/0/realdata_konik"
KONIK_PATH = _FP_CACHE_ROOT / "use_konik"

MAPS_PATH = _FP_DATA_ROOT / "media/0/osm/offline"

NNFF_MODELS_PATH = Path(BASEDIR) / "starpilot/assets/nnff_models"

BUTTON_FUNCTIONS = {
  "NOTHING": 0,
  "PERSONALITY_PROFILE": 1,
  "FORCE_COAST": 2,
  "PAUSE_LATERAL": 3,
  "PAUSE_LONGITUDINAL": 4,
  "EXPERIMENTAL_MODE": 5,
  "TRAFFIC_MODE": 6,
  "SWITCHBACK_MODE": 7,
}

DEVELOPER_SIDEBAR_METRICS = {
  "NONE": 0,
  "ACCELERATION_CURRENT": 1,
  "ACCELERATION_MAX": 2,
  "AUTOTUNE_ACTUATOR_DELAY": 3,
  "AUTOTUNE_FRICTION": 4,
  "AUTOTUNE_LATERAL_ACCELERATION": 5,
  "AUTOTUNE_STEER_RATIO": 6,
  "AUTOTUNE_STIFFNESS_FACTOR": 7,
  "ENGAGEMENT_LATERAL": 8,
  "ENGAGEMENT_LONGITUDINAL": 9,
  "LATERAL_STEERING_ANGLE": 10,
  "LATERAL_TORQUE_USED": 11,
  "LONGITUDINAL_ACTUATOR_ACCELERATION": 12,
  "LONGITUDINAL_MPC_JERK_ACCELERATION": 13,
  "LONGITUDINAL_MPC_JERK_DANGER_ZONE": 14,
  "LONGITUDINAL_MPC_JERK_SPEED_CONTROL": 15,
}

DEVICE_SHUTDOWN_TIMES = {
  0: 300,      # 5 mins
  1: 900,      # 15 mins
  2: 1800,     # 30 mins
  3: 2700,     # 45 mins
  4: 3600,     # 1 hour
  5: 7200,     # 2 hours
  6: 10800,    # 3 hours
  7: 14400,    # 4 hours
  8: 18000,    # 5 hours
  9: 21600,    # 6 hours
  10: 25200,   # 7 hours
  11: 28800,   # 8 hours
  12: 32400,   # 9 hours
  13: 36000,   # 10 hours
  14: 39600,   # 11 hours
  15: 43200,   # 12 hours
  16: 46800,   # 13 hours
  17: 50400,   # 14 hours
  18: 54000,   # 15 hours
  19: 57600,   # 16 hours
  20: 61200,   # 17 hours
  21: 64800,   # 18 hours
  22: 68400,   # 19 hours
  23: 72000,   # 20 hours
  24: 75600,   # 21 hours
  25: 79200,   # 22 hours
  26: 82800,   # 23 hours
  27: 86400,   # 24 hours
  28: 90000,   # 25 hours
  29: 93600,   # 26 hours
  30: 97200,   # 27 hours
  31: 100800,  # 28 hours
  32: 104400,  # 29 hours
  33: 108000,  # 30 hours
}

EXCLUDED_KEYS = {
  "AvailableModelSeries",
  "AvailableModelNames",
  "AvailableModels",
  "CalibratedLateralAcceleration",
  "CalibrationProgress",
  "CarBatteryCapacity",
  "CarParamsPersistent",
  "CommunityFavorites",
  "CurvatureData",
  "ExperimentalLongitudinalEnabled",
  "StarPilotCarParamsPersistent",
  "KonikMinutes",
  "LastUpdateTime",
  "MapBoxRequests",
  "ModelDrivesAndScores",
  "ModelReleasedDates",
  "ModelSortMode",
  "ModelVersions",
  "openpilotMinutes",
  "OverpassRequests",
  "PandaSignatures",
  "SpeedLimits",
  "SpeedLimitsFiltered",
  "UpdateFailedCount",
  "UpdaterAvailableBranches",
  "UpdaterCurrentDescription",
  "UpdaterCurrentReleaseNotes",
  "UpdaterFetchAvailable",
  "UpdaterTargetBranch",
  "UserFavorites",
  "UptimeOffroad"
}

TUNING_LEVELS = {
  "MINIMAL": 0,
  "STANDARD": 1,
  "ADVANCED": 2,
  "DEVELOPER": 3
}

# Shared params handles for modules that import these from starpilot_variables.
params = Params(return_defaults=True)
params_memory = Params(memory=True)

@cache
def get_nnff_model_files():
  return [file.stem for file in NNFF_MODELS_PATH.iterdir() if file.is_file()]

@cache
def get_nnff_substitutes():
  substitutes = {}
  with open(TORQUE_SUBSTITUTE_PATH, "rb") as f:
    substitutes_data = tomllib.load(f)
    substitutes = {key: value for key, value in substitutes_data.items()}
  return substitutes

def nnff_supported(car_fingerprint):
  model_files = set(get_nnff_model_files())
  substitutes = get_nnff_substitutes()

  fingerprints_to_check = [car_fingerprint]
  if car_fingerprint in substitutes:
    fingerprints_to_check.append(substitutes[car_fingerprint])

  for fingerprint in fingerprints_to_check:
    if any(file.startswith(fingerprint) for file in model_files):
      return True

  return False


def normalize_legacy_car_model(car_model):
  if car_model is None:
    return None
  if isinstance(car_model, bytes):
    car_model = car_model.decode("utf-8", errors="ignore")
  car_model = str(car_model)
  normalized = LEGACY_CARMODEL_MIGRATIONS.get(car_model, car_model)
  return normalized

def default_ev_tuning_enabled(CP):
  car_make = str(getattr(CP, "brand", "") or "")
  car_model = normalize_legacy_car_model(getattr(CP, "carFingerprint", "")) or ""

  gm_ev_vehicle = car_make == "gm" and car_model in GM_EV_CAR
  gm_ev_vehicle &= not (car_model.startswith("CHEVROLET_VOLT") and not car_model.endswith("_CC"))
  gm_ev_vehicle &= car_model != "CHEVROLET_MALIBU_HYBRID_CC"

  ev_vehicle = gm_ev_vehicle or (car_make == "hyundai" and car_model in HYUNDAI_EV_CAR)
  ev_vehicle |= getattr(CP, "transmissionType", None) == car.CarParams.TransmissionType.direct
  return bool(ev_vehicle)

def get_starpilot_toggles(sm=messaging.SubMaster(["starpilotPlan"])):
  toggles = process_starpilot_toggles(sm["starpilotPlan"].starpilotToggles)

  # Force drive-state controls must be authoritative from params so they
  # apply immediately even if starpilotPlan publication is temporarily stale.
  if not hasattr(get_starpilot_toggles, "_params"):
    get_starpilot_toggles._params = Params(return_defaults=True)

  toggles.force_offroad = get_starpilot_toggles._params.get_bool("ForceOffroad")
  toggles.force_onroad = get_starpilot_toggles._params.get_bool("ForceOnroad")
  return toggles

@cache
def process_starpilot_toggles(toggles):
  if toggles:
    return SimpleNamespace(**json.loads(toggles))
  return StarPilotVariables().starpilot_toggles

def update_starpilot_toggles():
  if not hasattr(update_starpilot_toggles, "_params_memory"):
    update_starpilot_toggles._params_memory = Params(memory=True)

  update_starpilot_toggles._params_memory.put_bool("StarPilotTogglesUpdated", True)

class StarPilotVariables:
  def __init__(self):
    self.params = Params(return_defaults=True)
    self.params_raw = Params()
    self.params_memory = Params(memory=True)

    self.starpilot_toggles = SimpleNamespace()
    toggle = self.starpilot_toggles

    self.default_values = {key.decode(): self.params.get_default_value(key) for key in self.params.all_keys()}
    self.tuning_levels = {key.decode(): self.params.get_tuning_level(key) for key in self.params.all_keys()}

    branch = get_build_metadata().channel
    self.release_branch = branch == "StarPilot"
    self.staging_branch = branch == "StarPilot-Staging"
    self.testing_branch = branch == "StarPilot-Testing"
    self.vetting_branch = branch == "StarPilot-Vetting"

    self.frogs_go_moo = FROGS_GO_MOO_PATH.is_file()
    # Development/vetting branches are no longer gated into dashcam mode.
    toggle.block_user = False

    toggle.tuning_level = self.params.get("TuningLevel") if self.params.get_bool("TuningLevelConfirmed") else TUNING_LEVELS["ADVANCED"]

    device_management = self.get_value("DeviceManagement")

    toggle.use_higher_bitrate = device_management
    toggle.use_higher_bitrate &= self.get_value("HigherBitrate")
    toggle.use_higher_bitrate &= self.get_value("NoUploads")
    toggle.use_higher_bitrate &= not self.get_value("DisableOnroadUploads")
    toggle.use_higher_bitrate &= not self.vetting_branch

    HD_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HD_PATH.is_file() and toggle.use_higher_bitrate:
      HD_PATH.touch()
      HARDWARE.reboot()
    elif HD_PATH.is_file() and not toggle.use_higher_bitrate:
      HD_PATH.unlink()
      HARDWARE.reboot()

    toggle.use_konik_server = device_management
    toggle.use_konik_server &= self.get_value("UseKonikServer")

    KONIK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not KONIK_PATH.is_file() and toggle.use_konik_server:
      KONIK_PATH.touch()
      HARDWARE.reboot()
    elif KONIK_PATH.is_file() and not toggle.use_konik_server:
      KONIK_PATH.unlink()
      HARDWARE.reboot()

    stock_colors_json = (STOCK_THEME_PATH / "colors/colors.json")
    self.stock_colors = json.loads(stock_colors_json.read_text()) if stock_colors_json.is_file() else {}

    self.update()

  def get_color(self, key, theme_colors):
    for source in (theme_colors, self.stock_colors):
      color = source.get(key)
      if isinstance(color, dict):
        return f"#{color.get('alpha', 255):02X}{color.get('red', 255):02X}{color.get('green', 255):02X}{color.get('blue', 255):02X}"
    return "#FFFFFFFF"

  def get_value(self, key, cast=bool, condition=True, conversion=None, default=None, min=None, max=None):
    if not condition or (self.starpilot_toggles.tuning_level < self.tuning_levels.get(key, 0)):
      if default is not None:
        value = default
      elif cast is bool:
        return False
      else:
        value = self.default_values.get(key)
        if cast is not None:
          try:
            value = cast(value)
          except (TypeError, ValueError):
            value = self.default_values.get(key)

      if conversion is not None and isinstance(value, (int, float)):
        value *= conversion

      if min is not None and value < min:
        value = min
      elif max is not None and value > max:
        value = max

      return value

    if cast is bool:
      value = self.params.get_bool(key)
    else:
      value = self.params.get(key)

    if value is not None:
      if cast is not bool and cast is not None:
        try:
          value = cast(value)
        except (TypeError, ValueError):
          value = self.default_values.get(key)
    elif default is not None:
      value = default

    if conversion is not None and isinstance(value, (int, float)):
      value *= conversion

    if min is not None and value < min:
      value = min
    elif max is not None and value > max:
      value = max

    return value

  def _sync_stock_param(self, key, stock_key, live_value):
    try:
      live_value = float(live_value)
    except (TypeError, ValueError):
      return

    if math.isclose(live_value, 0.0, abs_tol=1e-6):
      return

    current_stock = self.params.get_float(stock_key)
    if math.isclose(current_stock, live_value, abs_tol=1e-6):
      return

    current_value = self.params.get_float(key)
    if math.isclose(current_value, current_stock, abs_tol=1e-6) or math.isclose(current_stock, 0.0, abs_tol=1e-6):
      self.params.put_float(key, live_value)

    self.params.put_float(stock_key, live_value)

  def update(self, holiday_theme="stock", started=False):
    toggle = self.starpilot_toggles
    toggle.tuning_level = self.params.get("TuningLevel") if self.params.get_bool("TuningLevelConfirmed") else TUNING_LEVELS["ADVANCED"]

    fallback_platform = GM_CAR.CHEVROLET_BOLT_ACC_2022_2023 if HARDWARE.get_device_type() == "pc" else MOCK.MOCK

    msg_bytes = self.params.get("CarParams" if started else "CarParamsPersistent", block=started)
    if msg_bytes:
      CP = messaging.log_from_bytes(msg_bytes, car.CarParams)
      car_platform = CP.carFingerprint if CP.carFingerprint in interfaces else fallback_platform
    else:
      car_platform = fallback_platform
      CP = interfaces[car_platform].get_params(car_platform, gen_empty_fingerprint(), [], False, False, False, toggle).as_reader()

    is_torque_car = CP.lateralTuning.which() == "torque"
    if not is_torque_car:
      CP_builder = CP.as_builder()
      CarInterfaceBase.configure_torque_tune(car_platform, CP_builder.lateralTuning)
      CP = CP_builder.as_reader()

    fpmsg_bytes = self.params.get("StarPilotCarParams" if started else "StarPilotCarParamsPersistent", block=started)
    if fpmsg_bytes:
      FPCP = messaging.log_from_bytes(fpmsg_bytes, custom.StarPilotCarParams)
    else:
      FPCP = interfaces[car_platform].get_starpilot_params(car_platform, gen_empty_fingerprint(), [], CP, toggle)

    alpha_longitudinal = CP.alphaLongitudinalAvailable
    toggle.car_make = CP.brand
    toggle.car_model = CP.carFingerprint
    toggle.disable_openpilot_long = self.get_value("DisableOpenpilotLongitudinal", condition=not alpha_longitudinal)
    friction = CP.lateralTuning.torque.friction
    has_bsm = CP.enableBsm
    toggle.has_cc_long = toggle.car_make == "gm" and bool(CP.flags & GMFlags.CC_LONG.value)
    toggle.has_sascm = toggle.car_make == "gm" and bool(CP.flags & GMFlags.SASCM.value)
    has_nnff = nnff_supported(toggle.car_model)
    toggle.has_pedal = CP.enableGasInterceptorDEPRECATED
    has_radar = not CP.radarUnavailable
    toggle.has_sdsu = toggle.car_make == "toyota" and bool(FPCP.flags & ToyotaStarPilotFlags.SMART_DSU.value)
    has_sng = CP.autoResumeSng
    toggle.has_zss = toggle.car_make == "toyota" and bool(FPCP.flags & ToyotaStarPilotFlags.ZSS.value)
    is_angle_car = CP.steerControlType == car.CarParams.SteerControlType.angle
    latAccelFactor = CP.lateralTuning.torque.latAccelFactor
    toggle.lkas_allowed_for_aol = toggle.car_make == "hyundai" and bool(CP.flags & HyundaiFlags.CANFD or CP.flags & HyundaiFlags.HAS_LDA_BUTTON)
    longitudinalActuatorDelay = CP.longitudinalActuatorDelay
    toggle.openpilot_longitudinal = CP.openpilotLongitudinalControl and not toggle.disable_openpilot_long
    pcm_cruise = CP.pcmCruise
    prohibited_main_aol = not toggle.openpilot_longitudinal and toggle.car_make == "hyundai" and bool(CP.flags & HyundaiFlags.CANFD or CP.flags & HyundaiFlags.HAS_LDA_BUTTON)
    startAccel = CP.startAccel
    stopAccel = CP.stopAccel
    steerActuatorDelay = CP.steerActuatorDelay
    steerKp = KP
    steerRatio = CP.steerRatio
    toggle.stoppingDecelRate = CP.stoppingDecelRate
    toggle.vEgoStarting = CP.vEgoStarting
    toggle.vEgoStopping = CP.vEgoStopping

    # Keep stock tuning params synchronized for all device UIs (Qt + raylib).
    # Historically this only ran in Qt settings, which left C4 defaults at 0.
    self._sync_stock_param("SteerDelay", "SteerDelayStock", steerActuatorDelay)
    self._sync_stock_param("SteerFriction", "SteerFrictionStock", friction)
    self._sync_stock_param("SteerKP", "SteerKPStock", steerKp)
    self._sync_stock_param("SteerLatAccel", "SteerLatAccelStock", latAccelFactor)
    self._sync_stock_param("LongitudinalActuatorDelay", "LongitudinalActuatorDelayStock", longitudinalActuatorDelay)
    self._sync_stock_param("StartAccel", "StartAccelStock", startAccel)
    self._sync_stock_param("SteerRatio", "SteerRatioStock", steerRatio)
    self._sync_stock_param("StopAccel", "StopAccelStock", stopAccel)
    self._sync_stock_param("StoppingDecelRate", "StoppingDecelRateStock", toggle.stoppingDecelRate)
    self._sync_stock_param("VEgoStarting", "VEgoStartingStock", toggle.vEgoStarting)
    self._sync_stock_param("VEgoStopping", "VEgoStoppingStock", toggle.vEgoStopping)

    msg_bytes = self.params.get("LiveTorqueParameters")
    if msg_bytes:
      LTP = messaging.log_from_bytes(msg_bytes, log.LiveTorqueParametersData)
      has_auto_tune = LTP.useParams
      toggle.liveValid = LTP.liveValid
    else:
      has_auto_tune = False
      toggle.liveValid = False

    toggle.debug_mode = self.params.get_bool("DebugMode")
    toggle.force_offroad = self.params.get_bool("ForceOffroad")
    toggle.force_onroad = self.params.get_bool("ForceOnroad")
    toggle.safe_mode = self.params.get_bool("SafeMode")

    toggle.is_metric = self.params.get_bool("IsMetric")
    distance_conversion = 1 if toggle.is_metric else CV.FOOT_TO_METER
    small_distance_conversion = 1 if toggle.is_metric else CV.INCH_TO_CM
    speed_conversion = CV.KPH_TO_MS if toggle.is_metric else CV.MPH_TO_MS

    advanced_custom_ui = self.get_value("AdvancedCustomUI")
    toggle.hide_alerts = self.get_value("HideAlerts", condition=advanced_custom_ui and not toggle.debug_mode)
    toggle.hide_lead_marker = self.get_value("HideLeadMarker", condition=advanced_custom_ui and toggle.openpilot_longitudinal and not toggle.debug_mode)
    toggle.hide_max_speed = self.get_value("HideMaxSpeed", condition=advanced_custom_ui and not toggle.debug_mode)
    toggle.hide_speed = self.get_value("HideSpeed", condition=advanced_custom_ui and not toggle.debug_mode)
    toggle.hide_speed_limit = self.get_value("HideSpeedLimit", condition=advanced_custom_ui and not toggle.debug_mode)
    toggle.use_wheel_speed = self.get_value("WheelSpeed", condition=advanced_custom_ui)

    advanced_lateral_tuning = self.get_value("AdvancedLateralTune")
    toggle.force_auto_tune = self.get_value("ForceAutoTune", condition=advanced_lateral_tuning and not has_auto_tune and is_torque_car and not is_angle_car)
    toggle.force_auto_tune_off = self.get_value("ForceAutoTuneOff", condition=advanced_lateral_tuning and has_auto_tune and is_torque_car and not is_angle_car)
    toggle.steerActuatorDelay = self.get_value("SteerDelay", cast=float, condition=advanced_lateral_tuning, default=steerActuatorDelay, min=0.01, max=1.0)
    toggle.use_custom_steerActuatorDelay = bool(round(toggle.steerActuatorDelay, 2) != round(steerActuatorDelay, 2))
    toggle.friction = self.get_value("SteerFriction", cast=float, condition=advanced_lateral_tuning, default=friction, min=0, max=1)
    toggle.use_custom_friction = bool(round(toggle.friction, 2) != round(friction, 2)) and is_torque_car and not toggle.force_auto_tune or toggle.force_auto_tune_off
    toggle.steerKp = [[0], [self.get_value("SteerKP", cast=float, condition=advanced_lateral_tuning and is_torque_car and not is_angle_car, default=steerKp, min=steerKp * 0.5, max=steerKp * 1.5)]]
    toggle.latAccelFactor = self.get_value("SteerLatAccel", cast=float, condition=advanced_lateral_tuning, default=latAccelFactor, min=latAccelFactor * 0.5, max=latAccelFactor * 1.5)
    toggle.use_custom_latAccelFactor = bool(round(toggle.latAccelFactor, 2) != round(latAccelFactor, 2)) and is_torque_car and not toggle.force_auto_tune or toggle.force_auto_tune_off
    toggle.steerRatio = self.get_value("SteerRatio", cast=float, condition=advanced_lateral_tuning, default=steerRatio, min=steerRatio * 0.5, max=steerRatio * 1.5)
    toggle.use_custom_steerRatio = bool(round(toggle.steerRatio, 2) != round(steerRatio, 2)) and not toggle.force_auto_tune or toggle.force_auto_tune_off

    advanced_longitudinal_tuning = toggle.openpilot_longitudinal and self.get_value("AdvancedLongitudinalTune")
    ev_vehicle = default_ev_tuning_enabled(CP)

    if self.params_raw.get("EVTuning") in (None, b""):
      self.params.put_bool("EVTuning", ev_vehicle)

    if self.params_raw.get("TruckTuning") in (None, b""):
      self.params.put_bool("TruckTuning", False)

    ev_tuning_param = self.params.get_bool("EVTuning")
    truck_tuning_param = self.params.get_bool("TruckTuning")

    # EV and truck tuning are mutually exclusive.
    if truck_tuning_param and ev_tuning_param:
      ev_tuning_param = False
      self.params.put_bool("EVTuning", False)

    # Seed powertrain-based defaults once, but always honor persisted user overrides.
    toggle.ev_tuning = ev_tuning_param
    toggle.truck_tuning = truck_tuning_param
    toggle.longitudinalActuatorDelay = self.get_value("LongitudinalActuatorDelay", cast=float, condition=advanced_longitudinal_tuning, default=longitudinalActuatorDelay, min=0, max=1)
    toggle.max_desired_acceleration = self.get_value("MaxDesiredAcceleration", cast=float, condition=advanced_longitudinal_tuning, default=MAX_ACCELERATION, min=0.1, max=MAX_ACCELERATION)
    toggle.startAccel = self.get_value("StartAccel", cast=float, condition=advanced_longitudinal_tuning, default=startAccel, min=0, max=MAX_ACCELERATION)
    toggle.stopAccel = self.get_value("StopAccel", cast=float, condition=advanced_longitudinal_tuning, default=stopAccel, min=-MAX_ACCELERATION, max=0)
    toggle.stoppingDecelRate = self.get_value("StoppingDecelRate", cast=float, condition=advanced_longitudinal_tuning, default=toggle.stoppingDecelRate, min=0.001, max=1)
    toggle.vEgoStarting = self.get_value("VEgoStarting", cast=float, condition=advanced_longitudinal_tuning, default=toggle.vEgoStarting, min=0.01, max=1)
    toggle.vEgoStopping = self.get_value("VEgoStopping", cast=float, condition=advanced_longitudinal_tuning, default=toggle.vEgoStopping, min=0.01, max=1)

    toggle.alert_volume_controller = self.get_value("AlertVolumeControl")
    toggle.below_steer_speed_volume = self.get_value("BelowSteerSpeedVolume", cast=float, condition=toggle.alert_volume_controller)
    toggle.switchback_mode_cooldown = self.get_value("SwitchbackModeCooldown", cast=float, conversion=60, min=0, max=1800)
    toggle.disengage_volume = self.get_value("DisengageVolume", cast=float, condition=toggle.alert_volume_controller)
    toggle.engage_volume = self.get_value("EngageVolume", cast=float, condition=toggle.alert_volume_controller)
    toggle.prompt_volume = self.get_value("PromptVolume", cast=float, condition=toggle.alert_volume_controller)
    toggle.promptDistracted_volume = self.get_value("PromptDistractedVolume", cast=float, condition=toggle.alert_volume_controller)
    toggle.refuse_volume = self.get_value("RefuseVolume", cast=float, condition=toggle.alert_volume_controller)
    toggle.warningSoft_volume = self.get_value("WarningSoftVolume", cast=float, condition=toggle.alert_volume_controller)
    toggle.warningImmediate_volume = max(self.get_value("WarningImmediateVolume", cast=float, condition=toggle.alert_volume_controller, default=25), 25)

    toggle.always_on_lateral = self.get_value("AlwaysOnLateral")
    toggle.always_on_lateral_lkas = toggle.always_on_lateral and toggle.lkas_allowed_for_aol and self.get_value("AlwaysOnLateralLKAS")
    toggle.always_on_lateral_main = toggle.always_on_lateral and not prohibited_main_aol and not toggle.always_on_lateral_lkas
    toggle.always_on_lateral_pause_speed = self.get_value("PauseAOLOnBrake", cast=float, condition=toggle.always_on_lateral)

    toggle.automatic_updates = self.get_value("AutomaticUpdates") and not BACKUP_PATH.is_file()

    car_model = normalize_legacy_car_model(self.params.get("CarModel"))
    if car_model != self.params.get("CarModel"):
      self.params.put("CarModel", car_model)
      car_model_name = self.params.get("CarModelName")
      if car_model_name and "2019-21" in car_model_name:
        self.params.put("CarModelName", car_model_name.replace("2019-21", "2018-21"))
    toggle.force_fingerprint = self.get_value("ForceFingerprint", condition=car_model != self.default_values["CarModel"])
    if toggle.force_fingerprint:
      toggle.car_model = car_model

    toggle.cluster_offset = self.get_value("ClusterOffset", cast=float, condition=toggle.car_make == "toyota")

    toggle.conditional_experimental_mode = toggle.openpilot_longitudinal and self.get_value("ConditionalExperimental")
    toggle.conditional_curves = self.get_value("CECurves", condition=toggle.conditional_experimental_mode)
    toggle.conditional_curves_lead = self.get_value("CECurvesLead", condition=toggle.conditional_curves)
    toggle.conditional_lead = self.get_value("CELead", condition=toggle.conditional_experimental_mode)
    toggle.conditional_slower_lead = self.get_value("CESlowerLead", condition=toggle.conditional_lead)
    toggle.conditional_stopped_lead = self.get_value("CEStoppedLead", condition=toggle.conditional_lead)
    toggle.conditional_limit = self.get_value("CESpeed", cast=float, condition=toggle.conditional_experimental_mode, conversion=speed_conversion)
    toggle.conditional_limit_lead = self.get_value("CESpeedLead", cast=float, condition=toggle.conditional_experimental_mode, conversion=speed_conversion)
    toggle.conditional_model_stop_time = self.get_value("CEModelStopTime", cast=float, condition=toggle.conditional_experimental_mode and self.get_value("CEStopLights"))
    toggle.conditional_signal = self.get_value("CESignalSpeed", cast=float, condition=toggle.conditional_experimental_mode, conversion=speed_conversion)
    toggle.conditional_signal_lane_detection = self.get_value("CESignalLaneDetection", condition=toggle.conditional_signal != 0)
    toggle.cem_status = self.get_value("ShowCEMStatus", condition=toggle.conditional_experimental_mode) or toggle.debug_mode

    toggle.curve_speed_controller = toggle.openpilot_longitudinal and self.get_value("CurveSpeedController")
    toggle.csc_status = self.get_value("ShowCSCStatus", condition=toggle.curve_speed_controller) or toggle.debug_mode

    custom_alerts = self.get_value("CustomAlerts")
    toggle.goat_scream_alert = self.get_value("GoatScream", condition=custom_alerts)
    toggle.goat_scream_critical_alerts = self.get_value("GoatScreamCriticalAlerts", condition=custom_alerts)
    toggle.green_light_alert = self.get_value("GreenLightAlert", condition=custom_alerts)
    toggle.lead_departing_alert = self.get_value("LeadDepartingAlert", condition=custom_alerts)
    toggle.loud_blindspot_alert = self.get_value("LoudBlindspotAlert", condition=custom_alerts and has_bsm)
    toggle.speed_limit_changed_alert = self.get_value("SpeedLimitChangedAlert", condition=custom_alerts)

    toggle.custom_personalities = toggle.openpilot_longitudinal and self.get_value("CustomPersonalities")
    toggle.aggressive_jerk_acceleration = self.get_value("AggressiveJerkAcceleration", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.aggressive_jerk_deceleration = self.get_value("AggressiveJerkDeceleration", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.aggressive_jerk_danger = self.get_value("AggressiveJerkDanger", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.aggressive_jerk_speed = self.get_value("AggressiveJerkSpeed", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.aggressive_jerk_speed_decrease = self.get_value("AggressiveJerkSpeedDecrease", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    aggressive_follow_low = float(self.get_value("AggressiveFollow", cast=float, condition=toggle.custom_personalities, min=1, max=MAX_T_FOLLOW))
    aggressive_follow_high = float(self.get_value("AggressiveFollowHigh", cast=float, condition=toggle.custom_personalities, min=1, max=MAX_T_FOLLOW))
    toggle.aggressive_follow = [aggressive_follow_low, aggressive_follow_high]
    toggle.standard_jerk_acceleration = self.get_value("StandardJerkAcceleration", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.standard_jerk_deceleration = self.get_value("StandardJerkDeceleration", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.standard_jerk_danger = self.get_value("StandardJerkDanger", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.standard_jerk_speed = self.get_value("StandardJerkSpeed", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.standard_jerk_speed_decrease = self.get_value("StandardJerkSpeedDecrease", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    standard_follow_low = float(self.get_value("StandardFollow", cast=float, condition=toggle.custom_personalities, min=1, max=MAX_T_FOLLOW))
    standard_follow_high = float(self.get_value("StandardFollowHigh", cast=float, condition=toggle.custom_personalities, min=1, max=MAX_T_FOLLOW))
    toggle.standard_follow = [standard_follow_low, standard_follow_high]
    toggle.relaxed_jerk_acceleration = self.get_value("RelaxedJerkAcceleration", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.relaxed_jerk_deceleration = self.get_value("RelaxedJerkDeceleration", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.relaxed_jerk_danger = self.get_value("RelaxedJerkDanger", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.relaxed_jerk_speed = self.get_value("RelaxedJerkSpeed", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    toggle.relaxed_jerk_speed_decrease = self.get_value("RelaxedJerkSpeedDecrease", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0)
    relaxed_follow_low = float(self.get_value("RelaxedFollow", cast=float, condition=toggle.custom_personalities, min=1, max=MAX_T_FOLLOW))
    relaxed_follow_high = float(self.get_value("RelaxedFollowHigh", cast=float, condition=toggle.custom_personalities, min=1, max=MAX_T_FOLLOW))
    toggle.relaxed_follow = [relaxed_follow_low, relaxed_follow_high]
    toggle.traffic_mode_jerk_acceleration = [self.get_value("TrafficJerkAcceleration", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0), toggle.aggressive_jerk_acceleration]
    toggle.traffic_mode_jerk_deceleration = [self.get_value("TrafficJerkDeceleration", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0), toggle.aggressive_jerk_deceleration]
    toggle.traffic_mode_jerk_danger = [self.get_value("TrafficJerkDanger", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0), toggle.aggressive_jerk_danger]
    toggle.traffic_mode_jerk_speed = [self.get_value("TrafficJerkSpeed", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0), toggle.aggressive_jerk_speed]
    toggle.traffic_mode_jerk_speed_decrease = [self.get_value("TrafficJerkSpeedDecrease", cast=float, condition=toggle.custom_personalities, conversion=0.01, min=0.25, max=2.0), toggle.aggressive_jerk_speed_decrease]
    toggle.traffic_mode_follow = [float(self.get_value("TrafficFollow", cast=float, condition=toggle.custom_personalities, min=0.5, max=MAX_T_FOLLOW)), toggle.aggressive_follow[0]]

    custom_themes = self.get_value("CustomThemes")
    toggle.boot_logo = self.get_value("BootLogo", cast=None, default="starpilot")
    toggle.color_scheme = self.get_value("ColorScheme", cast=None, condition=custom_themes, default="stock")
    theme_colors = json.loads(THEME_COLORS_PATH.read_text()) if THEME_COLORS_PATH.is_file() else {}
    toggle.lane_lines_color = self.get_color("LaneLines", theme_colors)
    toggle.lead_marker_color = self.get_color("LeadMarker", theme_colors)
    toggle.path_color = self.get_color("Path", theme_colors)
    toggle.path_edges_color = self.get_color("PathEdge", theme_colors)
    toggle.sidebar_color1 = self.get_color("Sidebar1", theme_colors)
    toggle.sidebar_color2 = self.get_color("Sidebar2", theme_colors)
    toggle.sidebar_color3 = self.get_color("Sidebar3", theme_colors)
    toggle.distance_icons = self.get_value("DistanceIconPack", cast=None, condition=custom_themes, default="stock")
    toggle.icon_pack = self.get_value("IconPack", cast=None, condition=custom_themes, default="stock")
    toggle.signal_icons = self.get_value("SignalAnimation", cast=None, condition=custom_themes, default="stock")
    toggle.sound_pack = self.get_value("SoundPack", cast=None, condition=custom_themes, default="stock")
    toggle.random_themes = self.get_value("RandomThemes", condition=custom_themes)
    toggle.random_themes_holidays = self.get_value("RandomThemesHolidays", condition=toggle.random_themes)
    if toggle.random_themes:
      toggle.wheel_image = random.choice([file.stem for file in (THEME_SAVE_PATH / "steering_wheels").iterdir() if file.is_file()] or ["stock"]) if (THEME_SAVE_PATH / "steering_wheels").exists() else "stock"
    else:
      toggle.wheel_image = self.get_value("WheelIcon", cast=None, condition=custom_themes, default="stock")

    custom_ui = self.get_value("CustomUI")
    toggle.acceleration_path = toggle.openpilot_longitudinal and (self.get_value("AccelerationPath", condition=custom_ui) or toggle.debug_mode)
    toggle.adjacent_paths = self.get_value("AdjacentPath", condition=custom_ui)
    toggle.blind_spot_path = has_bsm and self.get_value("BlindSpotPath", condition=custom_ui)
    toggle.compass = self.get_value("Compass", condition=custom_ui)
    toggle.pedals_on_ui = self.get_value("PedalsOnUI", condition=custom_ui and toggle.openpilot_longitudinal)
    toggle.dynamic_pedals_on_ui = self.get_value("DynamicPedalsOnUI", condition=toggle.pedals_on_ui)
    toggle.static_pedals_on_ui = self.get_value("StaticPedalsOnUI", condition=toggle.pedals_on_ui)
    toggle.rotating_wheel = self.get_value("RotatingWheel", condition=custom_ui)

    toggle.developer_ui = self.get_value("DeveloperUI")
    developer_metrics = self.get_value("DeveloperMetrics", condition=toggle.developer_ui)
    border_metrics = self.get_value("BorderMetrics", condition=developer_metrics)
    toggle.blind_spot_metrics = has_bsm and self.get_value("BlindSpotMetrics", condition=border_metrics)
    toggle.signal_metrics = self.get_value("SignalMetrics", condition=border_metrics) or toggle.debug_mode
    toggle.steering_metrics = self.get_value("ShowSteering", condition=border_metrics) or toggle.debug_mode
    toggle.show_fps = self.get_value("FPSCounter", condition=developer_metrics) or toggle.debug_mode
    toggle.adjacent_path_metrics = self.get_value("AdjacentPathMetrics", condition=developer_metrics) or toggle.debug_mode
    toggle.lead_info = self.get_value("LeadInfo", condition=developer_metrics) or toggle.debug_mode
    toggle.numerical_temp = self.get_value("NumericalTemp", condition=developer_metrics) or toggle.debug_mode
    toggle.fahrenheit = self.get_value("Fahrenheit", condition=toggle.numerical_temp and not toggle.debug_mode)
    toggle.cpu_metrics = self.get_value("ShowCPU", condition=developer_metrics) or toggle.debug_mode
    toggle.gpu_metrics = self.get_value("ShowGPU", condition=developer_metrics and not toggle.debug_mode)
    toggle.ip_metrics = self.get_value("ShowIP", condition=developer_metrics)
    toggle.memory_metrics = self.get_value("ShowMemoryUsage", condition=developer_metrics) or toggle.debug_mode
    toggle.storage_left_metrics = self.get_value("ShowStorageLeft", condition=developer_metrics and not toggle.debug_mode)
    toggle.storage_used_metrics = self.get_value("ShowStorageUsed", condition=developer_metrics and not toggle.debug_mode)
    toggle.use_si_metrics = self.get_value("UseSI", condition=developer_metrics) or toggle.debug_mode
    toggle.developer_sidebar = self.get_value("DeveloperSidebar", condition=toggle.developer_ui) or toggle.debug_mode
    toggle.developer_sidebar_metric1 = self.get_value("DeveloperSidebarMetric1", cast=None, condition=toggle.developer_sidebar, default=DEVELOPER_SIDEBAR_METRICS["LONGITUDINAL_ACTUATOR_ACCELERATION"] if toggle.debug_mode else None)
    toggle.developer_sidebar_metric2 = self.get_value("DeveloperSidebarMetric2", cast=None, condition=toggle.developer_sidebar, default=DEVELOPER_SIDEBAR_METRICS["ACCELERATION_CURRENT"] if toggle.debug_mode else None)
    toggle.developer_sidebar_metric3 = self.get_value("DeveloperSidebarMetric3", cast=None, condition=toggle.developer_sidebar, default=DEVELOPER_SIDEBAR_METRICS["LATERAL_STEERING_ANGLE"] if toggle.debug_mode else None)
    toggle.developer_sidebar_metric4 = self.get_value("DeveloperSidebarMetric4", cast=None, condition=toggle.developer_sidebar, default=DEVELOPER_SIDEBAR_METRICS["LATERAL_TORQUE_USED"] if toggle.debug_mode else None)
    toggle.developer_sidebar_metric5 = self.get_value("DeveloperSidebarMetric5", cast=None, condition=toggle.developer_sidebar, default=DEVELOPER_SIDEBAR_METRICS["LONGITUDINAL_MPC_JERK_ACCELERATION"] if toggle.debug_mode else None)
    toggle.developer_sidebar_metric6 = self.get_value("DeveloperSidebarMetric6", cast=None, condition=toggle.developer_sidebar, default=DEVELOPER_SIDEBAR_METRICS["LONGITUDINAL_MPC_JERK_DANGER_ZONE"] if toggle.debug_mode else None)
    toggle.developer_sidebar_metric7 = self.get_value("DeveloperSidebarMetric7", cast=None, condition=toggle.developer_sidebar, default=DEVELOPER_SIDEBAR_METRICS["LONGITUDINAL_MPC_JERK_SPEED_CONTROL"] if toggle.debug_mode else None)
    developer_widgets = self.get_value("DeveloperWidgets", condition=toggle.developer_ui)
    toggle.adjacent_lead_tracking = has_radar and (self.get_value("AdjacentLeadsUI", condition=developer_widgets) or toggle.debug_mode)
    toggle.radar_tracks = has_radar and (self.get_value("RadarTracksUI", condition=developer_widgets) or toggle.debug_mode)
    toggle.show_stopping_point = toggle.openpilot_longitudinal and (self.get_value("ShowStoppingPoint", condition=developer_widgets) or toggle.debug_mode)
    toggle.show_stopping_point_metrics = self.get_value("ShowStoppingPointMetrics", condition=toggle.show_stopping_point) or toggle.debug_mode

    device_management = self.get_value("DeviceManagement")
    toggle.device_shutdown_time = DEVICE_SHUTDOWN_TIMES.get(self.get_value("DeviceShutdown", cast=int, condition=device_management))
    toggle.increase_thermal_limits = self.get_value("IncreaseThermalLimits", condition=device_management)
    toggle.low_voltage_shutdown = self.get_value("LowVoltageShutdown", cast=float, condition=device_management, min=VBATT_PAUSE_CHARGING, max=12.5)
    # Keep force-onroad desktop simulations from polluting logs, but never disable
    # loggerd/encoderd on real devices because that breaks route continuity/uploads.
    toggle.no_logging = self.get_value("NoLogging", condition=device_management and not self.vetting_branch) or (toggle.force_onroad and HARDWARE.get_device_type() == "pc")
    toggle.no_uploads = self.get_value("NoUploads", condition=device_management and not self.vetting_branch)
    toggle.no_onroad_uploads = self.get_value("DisableOnroadUploads", condition=toggle.no_uploads)

    distance_button_control = self.get_value("DistanceButtonControl", cast=float)
    toggle.experimental_mode_via_distance = toggle.openpilot_longitudinal and distance_button_control == BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"]
    toggle.experimental_mode_via_press = toggle.experimental_mode_via_distance
    toggle.force_coast_via_distance = toggle.openpilot_longitudinal and distance_button_control == BUTTON_FUNCTIONS["FORCE_COAST"]
    toggle.pause_lateral_via_distance = distance_button_control == BUTTON_FUNCTIONS["PAUSE_LATERAL"]
    toggle.pause_longitudinal_via_distance = toggle.openpilot_longitudinal and distance_button_control == BUTTON_FUNCTIONS["PAUSE_LONGITUDINAL"]
    toggle.personality_profile_via_distance = toggle.openpilot_longitudinal and distance_button_control == BUTTON_FUNCTIONS["PERSONALITY_PROFILE"]
    toggle.switchback_mode_via_distance = distance_button_control == BUTTON_FUNCTIONS["SWITCHBACK_MODE"]
    toggle.traffic_mode_via_distance = toggle.openpilot_longitudinal and distance_button_control == BUTTON_FUNCTIONS["TRAFFIC_MODE"]

    distance_button_control_long = self.get_value("LongDistanceButtonControl", cast=float)
    toggle.experimental_mode_via_distance_long = toggle.openpilot_longitudinal and distance_button_control_long == BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"]
    toggle.experimental_mode_via_press |= toggle.experimental_mode_via_distance_long
    toggle.force_coast_via_distance_long = toggle.openpilot_longitudinal and distance_button_control_long == BUTTON_FUNCTIONS["FORCE_COAST"]
    toggle.pause_lateral_via_distance_long = distance_button_control_long == BUTTON_FUNCTIONS["PAUSE_LATERAL"]
    toggle.pause_longitudinal_via_distance_long = toggle.openpilot_longitudinal and distance_button_control_long == BUTTON_FUNCTIONS["PAUSE_LONGITUDINAL"]
    toggle.personality_profile_via_distance_long = toggle.openpilot_longitudinal and distance_button_control_long == BUTTON_FUNCTIONS["PERSONALITY_PROFILE"]
    toggle.switchback_mode_via_distance_long = distance_button_control_long == BUTTON_FUNCTIONS["SWITCHBACK_MODE"]
    toggle.traffic_mode_via_distance_long = toggle.openpilot_longitudinal and distance_button_control_long == BUTTON_FUNCTIONS["TRAFFIC_MODE"]

    distance_button_control_very_long = self.get_value("VeryLongDistanceButtonControl", cast=float)
    toggle.experimental_mode_via_distance_very_long = toggle.openpilot_longitudinal and distance_button_control_very_long == BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"]
    toggle.experimental_mode_via_press |= toggle.experimental_mode_via_distance_very_long
    toggle.force_coast_via_distance_very_long = toggle.openpilot_longitudinal and distance_button_control_very_long == BUTTON_FUNCTIONS["FORCE_COAST"]
    toggle.pause_lateral_via_distance_very_long = distance_button_control_very_long == BUTTON_FUNCTIONS["PAUSE_LATERAL"]
    toggle.pause_longitudinal_via_distance_very_long = toggle.openpilot_longitudinal and distance_button_control_very_long == BUTTON_FUNCTIONS["PAUSE_LONGITUDINAL"]
    toggle.personality_profile_via_distance_very_long = toggle.openpilot_longitudinal and distance_button_control_very_long == BUTTON_FUNCTIONS["PERSONALITY_PROFILE"]
    toggle.switchback_mode_via_distance_very_long = distance_button_control_very_long == BUTTON_FUNCTIONS["SWITCHBACK_MODE"]
    toggle.traffic_mode_via_distance_very_long = toggle.openpilot_longitudinal and distance_button_control_very_long == BUTTON_FUNCTIONS["TRAFFIC_MODE"]

    toggle.frogsgomoo_tweak = self.get_value("FrogsGoMoosTweak", condition=toggle.openpilot_longitudinal and toggle.car_make == "toyota")
    toggle.stoppingDecelRate = 0.01 if toggle.frogsgomoo_tweak else toggle.stoppingDecelRate
    toggle.vEgoStarting = 0.1 if toggle.frogsgomoo_tweak else toggle.vEgoStarting
    toggle.vEgoStopping = 0.5 if toggle.frogsgomoo_tweak else toggle.vEgoStopping

    toggle.holiday_themes = self.get_value("HolidayThemes")
    toggle.current_holiday_theme = holiday_theme if toggle.holiday_themes else "stock"
    if toggle.current_holiday_theme != "stock":
      toggle.color_scheme = toggle.current_holiday_theme
      toggle.distance_icons = toggle.current_holiday_theme
      toggle.icon_pack = toggle.current_holiday_theme
      toggle.signal_icons = toggle.current_holiday_theme
      toggle.sound_pack = toggle.current_holiday_theme
      toggle.wheel_image = toggle.current_holiday_theme

    toggle.lane_changes = self.get_value("LaneChanges")
    toggle.lane_change_delay = self.get_value("LaneChangeTime", cast=float, condition=toggle.lane_changes)
    toggle.lane_detection_width = self.get_value("LaneDetectionWidth", cast=float, condition=toggle.lane_changes, conversion=distance_conversion)
    toggle.minimum_lane_change_speed = self.get_value("MinimumLaneChangeSpeed", cast=float, condition=toggle.lane_changes, conversion=speed_conversion)
    toggle.nudgeless = self.get_value("NudgelessLaneChange", condition=toggle.lane_changes)
    toggle.one_lane_change = self.get_value("OneLaneChange", condition=toggle.lane_changes)

    lateral_tuning = self.get_value("LateralTune")
    toggle.force_torque_controller = self.get_value("ForceTorqueController", condition=lateral_tuning and not is_torque_car and not is_angle_car)
    toggle.nnff = self.get_value("NNFF", condition=lateral_tuning and has_nnff and not is_angle_car)
    toggle.nnff_lite = self.get_value("NNFFLite", condition=not toggle.nnff and lateral_tuning and not is_angle_car)
    toggle.use_turn_desires = self.get_value("TurnDesires", condition=lateral_tuning)

    lkas_button_control = self.get_value("LKASButtonControl", cast=float, condition=toggle.car_make != "subaru")
    toggle.experimental_mode_via_lkas = toggle.openpilot_longitudinal and lkas_button_control == BUTTON_FUNCTIONS["EXPERIMENTAL_MODE"]
    toggle.experimental_mode_via_press |= toggle.experimental_mode_via_lkas
    toggle.force_coast_via_lkas = toggle.openpilot_longitudinal and lkas_button_control == BUTTON_FUNCTIONS["FORCE_COAST"]
    toggle.pause_lateral_via_lkas = lkas_button_control == BUTTON_FUNCTIONS["PAUSE_LATERAL"]
    toggle.pause_longitudinal_via_lkas = toggle.openpilot_longitudinal and lkas_button_control == BUTTON_FUNCTIONS["PAUSE_LONGITUDINAL"]
    toggle.personality_profile_via_lkas = toggle.openpilot_longitudinal and lkas_button_control == BUTTON_FUNCTIONS["PERSONALITY_PROFILE"]
    toggle.switchback_mode_via_lkas = lkas_button_control == BUTTON_FUNCTIONS["SWITCHBACK_MODE"]
    toggle.traffic_mode_via_lkas = toggle.openpilot_longitudinal and lkas_button_control == BUTTON_FUNCTIONS["TRAFFIC_MODE"]

    toggle.lock_doors_timer = self.get_value("LockDoorsTimer", cast=float, condition=(toggle.car_make == "toyota"))

    longitudinal_tuning = toggle.openpilot_longitudinal and self.get_value("LongitudinalTune")
    toggle.acceleration_profile = normalize_acceleration_profile(
      self.get_value("AccelerationProfile", cast=None, condition=longitudinal_tuning, default=ACCELERATION_PROFILES["SPORT"])
    )
    toggle.deceleration_profile = normalize_deceleration_profile(
      self.get_value("DecelerationProfile", cast=None, condition=longitudinal_tuning, default=DECELERATION_PROFILES["ECO"])
    )
    toggle.custom_accel_profile = self.get_value("CustomAccelProfile", condition=longitudinal_tuning)
    custom_accel_defaults = build_custom_accel_profile_defaults(toggle.acceleration_profile, toggle.ev_tuning, toggle.truck_tuning)
    custom_accel_raw_values = {key: self.params_raw.get(key) for key in CUSTOM_ACCEL_PROFILE_PARAM_KEYS}
    custom_accel_initialized = custom_accel_profile_is_initialized(
      self.params_raw.get(CUSTOM_ACCEL_PROFILE_INITIALIZED_KEY),
      custom_accel_raw_values,
    )
    if custom_accel_initialized:
      toggle.custom_accel_profile_values = [
        self.get_value(key, cast=float, condition=longitudinal_tuning, default=custom_accel_defaults[key],
                       min=CUSTOM_ACCEL_PROFILE_VALUE_MIN, max=CUSTOM_ACCEL_PROFILE_VALUE_MAX)
        for key in CUSTOM_ACCEL_PROFILE_PARAM_KEYS
      ]
    else:
      toggle.custom_accel_profile_values = [custom_accel_defaults[key] for key in CUSTOM_ACCEL_PROFILE_PARAM_KEYS]
    toggle.human_acceleration = self.get_value("HumanAcceleration", condition=longitudinal_tuning)
    toggle.human_following = self.get_value("HumanFollowing", condition=longitudinal_tuning)
    toggle.human_lane_changes = has_radar and self.get_value("HumanLaneChanges", condition=longitudinal_tuning)
    # Keep lead detection sensitivity normalized even when longitudinal tuning is disabled.
    # Some branches can return raw integer defaults (e.g. 35) when condition=False.
    lead_detection_probability = self.get_value("LeadDetectionThreshold", cast=float, condition=toggle.openpilot_longitudinal,
                                                conversion=0.01, default=0.35, min=0.25, max=0.5)
    if isinstance(lead_detection_probability, (int, float)) and lead_detection_probability > 1.0:
      lead_detection_probability = float(np.clip(lead_detection_probability * 0.01, 0.25, 0.5))
    toggle.lead_detection_probability = lead_detection_probability
    toggle.recovery_power = self.get_value("RecoveryPower", cast=float, condition=longitudinal_tuning, default=1.0, min=0.5, max=2.0)
    toggle.stop_distance = self.get_value("StopDistance", cast=float, condition=longitudinal_tuning, default=6.0)
    toggle.taco_tune = self.get_value("TacoTune", condition=longitudinal_tuning)

    toggle.model = self.get_value("Model", cast=None, default="sc2")
    if not toggle.model:
      toggle.model = self.get_value("DrivingModel", cast=None, default="sc2")
    toggle.model_name = self.get_value("DrivingModelName", cast=None, default="South Carolina")
    toggle.model_version = self.get_value("ModelVersion", cast=None, default="v11")
    if not toggle.model_version:
      toggle.model_version = self.get_value("DrivingModelVersion", cast=None, default="v11")
    if isinstance(toggle.model, bytes):
      toggle.model = toggle.model.decode("utf-8", "ignore")
    if isinstance(toggle.model_name, bytes):
      toggle.model_name = toggle.model_name.decode("utf-8", "ignore")
    if isinstance(toggle.model_version, bytes):
      toggle.model_version = toggle.model_version.decode("utf-8", "ignore")
    toggle.classic_model = toggle.model_version in {"v1", "v2", "v3", "v4"}
    toggle.tinygrad_model = toggle.model_version in {"v8", "v9", "v10", "v11", "v12"}
    toggle.tomb_raider = toggle.model == "space-lab"

    toggle.model_ui = self.get_value("ModelUI")
    toggle.dynamic_path_width = self.get_value("DynamicPathWidth", condition=toggle.model_ui and not toggle.debug_mode)
    toggle.lane_line_width = self.get_value("LaneLinesWidth", cast=float, condition=toggle.model_ui and not toggle.debug_mode, conversion=small_distance_conversion / 200)
    toggle.path_edge_width = self.get_value("PathEdgeWidth", cast=float, condition=toggle.model_ui and not toggle.debug_mode)
    toggle.path_width = self.get_value("PathWidth", cast=float, condition=toggle.model_ui and not toggle.debug_mode, conversion=distance_conversion / 2)
    toggle.road_edge_width = self.get_value("RoadEdgesWidth", cast=float, condition=toggle.model_ui and not toggle.debug_mode, conversion=small_distance_conversion / 200)

    navigation_ui = self.get_value("NavigationUI")
    toggle.road_name_ui = self.get_value("RoadNameUI", condition=navigation_ui) or toggle.debug_mode
    # Speed-limit display is also used by the C4 display-only vision test path,
    # so it must not be disabled just because the broader Navigation UI group is off.
    toggle.show_speed_limits = self.get_value("ShowSpeedLimits") or toggle.debug_mode
    toggle.speed_limit_vienna = self.get_value("UseVienna", condition=navigation_ui)

    quality_of_life_lateral = self.get_value("QOLLateral")
    toggle.pause_lateral_below_speed = self.get_value("PauseLateralSpeed", cast=float, condition=quality_of_life_lateral, conversion=speed_conversion)
    toggle.pause_lateral_below_signal = self.get_value("PauseLateralOnSignal", condition=toggle.pause_lateral_below_speed != 0)

    quality_of_life_longitudinal = toggle.openpilot_longitudinal and self.get_value("QOLLongitudinal")
    toggle.cruise_increase = self.get_value("CustomCruise", cast=float, condition=(quality_of_life_longitudinal and not pcm_cruise))
    toggle.cruise_increase_long = self.get_value("CustomCruiseLong", cast=float, condition=(quality_of_life_longitudinal and not pcm_cruise))
    toggle.force_stops = self.get_value("ForceStops", condition=quality_of_life_longitudinal)
    toggle.force_standstill = self.get_value("ForceStandstill", condition=quality_of_life_longitudinal)
    toggle.increase_stopped_distance = self.get_value("IncreasedStoppedDistance", cast=float, condition=quality_of_life_longitudinal, conversion=distance_conversion)
    map_gears = self.get_value("MapGears", condition=quality_of_life_longitudinal)
    toggle.map_acceleration = self.get_value("MapAcceleration", condition=map_gears)
    toggle.map_deceleration = self.get_value("MapDeceleration", condition=map_gears)
    toggle.reverse_cruise_increase = self.get_value("ReverseCruise", condition=quality_of_life_longitudinal and toggle.car_make == "toyota" and pcm_cruise)
    toggle.set_speed_offset = self.get_value("SetSpeedOffset", cast=float, condition=(quality_of_life_longitudinal and not pcm_cruise), conversion=(1 if toggle.is_metric else CV.MPH_TO_KPH))
    toggle.weather_presets = self.get_value("WeatherPresets", condition=quality_of_life_longitudinal)
    toggle.increase_following_distance_low_visibility = self.get_value("IncreaseFollowingLowVisibility", cast=float, condition=toggle.weather_presets)
    toggle.increase_following_distance_rain = self.get_value("IncreaseFollowingRain", cast=float, condition=toggle.weather_presets)
    toggle.increase_following_distance_rain_storm = self.get_value("IncreaseFollowingRainStorm", cast=float, condition=toggle.weather_presets)
    toggle.increase_following_distance_snow = self.get_value("IncreaseFollowingSnow", cast=float, condition=toggle.weather_presets)
    toggle.increase_stopped_distance_low_visibility = self.get_value("IncreasedStoppedDistanceLowVisibility", cast=float, condition=toggle.weather_presets, conversion=distance_conversion)
    toggle.increase_stopped_distance_rain = self.get_value("IncreasedStoppedDistanceRain", cast=float, condition=toggle.weather_presets, conversion=distance_conversion)
    toggle.increase_stopped_distance_rain_storm = self.get_value("IncreasedStoppedDistanceRainStorm", cast=float, condition=toggle.weather_presets, conversion=distance_conversion)
    toggle.increase_stopped_distance_snow = self.get_value("IncreasedStoppedDistanceSnow", cast=float, condition=toggle.weather_presets, conversion=distance_conversion)
    toggle.reduce_acceleration_low_visibility = self.get_value("ReduceAccelerationLowVisibility", cast=float, condition=toggle.weather_presets, conversion=0.01)
    toggle.reduce_acceleration_rain = self.get_value("ReduceAccelerationRain", cast=float, condition=toggle.weather_presets, conversion=0.01)
    toggle.reduce_acceleration_rain_storm = self.get_value("ReduceAccelerationRainStorm", cast=float, condition=toggle.weather_presets, conversion=0.01)
    toggle.reduce_acceleration_snow = self.get_value("ReduceAccelerationSnow", cast=float, condition=toggle.weather_presets, conversion=0.01)
    toggle.reduce_lateral_acceleration_low_visibility = self.get_value("ReduceLateralAccelerationLowVisibility", cast=float, condition=toggle.weather_presets, conversion=0.01)
    toggle.reduce_lateral_acceleration_rain = self.get_value("ReduceLateralAccelerationRain", cast=float, condition=toggle.weather_presets, conversion=0.01)
    toggle.reduce_lateral_acceleration_rain_storm = self.get_value("ReduceLateralAccelerationRainStorm", cast=float, condition=toggle.weather_presets, conversion=0.01)
    toggle.reduce_lateral_acceleration_snow = self.get_value("ReduceLateralAccelerationSnow", cast=float, condition=toggle.weather_presets, conversion=0.01)

    quality_of_life_visuals = self.get_value("QOLVisuals")
    toggle.camera_view = self.get_value("CameraView", cast=float, condition=quality_of_life_visuals and not toggle.debug_mode)
    toggle.driver_camera_in_reverse = self.get_value("DriverCamera", condition=quality_of_life_visuals)
    toggle.onroad_distance_button = toggle.openpilot_longitudinal and (self.get_value("OnroadDistanceButton", condition=quality_of_life_visuals) or toggle.debug_mode)
    toggle.stopped_timer = self.get_value("StoppedTimer", condition=quality_of_life_visuals)

    toggle.rainbow_path = self.get_value("RainbowPath", condition=not toggle.debug_mode)

    toggle.random_events = self.get_value("RandomEvents")

    screen_management = self.get_value("ScreenManagement")
    toggle.screen_brightness = max(self.get_value("ScreenBrightness", cast=float, condition=screen_management), 1)
    toggle.screen_brightness_onroad = self.get_value("ScreenBrightnessOnroad", cast=float, condition=(screen_management and not toggle.force_onroad))
    toggle.screen_recorder = self.get_value("ScreenRecorder", condition=screen_management) or toggle.debug_mode
    toggle.screen_timeout = self.get_value("ScreenTimeout", cast=float, condition=screen_management)
    toggle.screen_timeout_onroad = self.get_value("ScreenTimeoutOnroad", cast=float, condition=screen_management)
    toggle.standby_mode = self.get_value("StandbyMode", condition=screen_management)

    toggle.sng_hack = self.get_value("SNGHack", condition=toggle.openpilot_longitudinal and toggle.car_make == "toyota" and not toggle.has_pedal and not has_sng)

    toggle.speed_limit_controller = toggle.openpilot_longitudinal and self.get_value("SpeedLimitController")
    speed_limit_display = toggle.show_speed_limits or toggle.speed_limit_controller
    toggle.map_speed_lookahead_higher = self.get_value("SLCLookaheadHigher", cast=float, condition=speed_limit_display)
    toggle.map_speed_lookahead_lower = self.get_value("SLCLookaheadLower", cast=float, condition=speed_limit_display)
    toggle.set_speed_limit = self.get_value("SetSpeedLimit", condition=toggle.speed_limit_controller)
    toggle.show_speed_limit_offset = self.get_value("ShowSLCOffset", condition=toggle.speed_limit_controller) or toggle.debug_mode
    slc_fallback_method = self.get_value("SLCFallback", cast=float, condition=toggle.speed_limit_controller)
    toggle.slc_fallback_experimental_mode = slc_fallback_method == 1
    toggle.slc_fallback_previous_speed_limit = slc_fallback_method == 2
    toggle.slc_fallback_set_speed = slc_fallback_method == 0
    toggle.slc_mapbox_filler = self.get_value("SLCMapboxFiller", condition=(toggle.show_speed_limits or toggle.speed_limit_controller) and self.params.get("MapboxSecretKey") is not None)
    speed_limit_confirmation = self.get_value("SLCConfirmation", condition=toggle.speed_limit_controller)
    toggle.speed_limit_confirmation_higher = self.get_value("SLCConfirmationHigher", condition=speed_limit_confirmation)
    toggle.speed_limit_confirmation_lower = self.get_value("SLCConfirmationLower", condition=speed_limit_confirmation)
    slc_override_method = self.get_value("SLCOverride", cast=float, condition=toggle.speed_limit_controller)
    toggle.speed_limit_controller_override_manual = slc_override_method == 1
    toggle.speed_limit_controller_override_set_speed = slc_override_method == 2
    toggle.speed_limit_offset1 = self.get_value("Offset1", cast=float, condition=toggle.speed_limit_controller, conversion=speed_conversion)
    toggle.speed_limit_offset2 = self.get_value("Offset2", cast=float, condition=toggle.speed_limit_controller, conversion=speed_conversion)
    toggle.speed_limit_offset3 = self.get_value("Offset3", cast=float, condition=toggle.speed_limit_controller, conversion=speed_conversion)
    toggle.speed_limit_offset4 = self.get_value("Offset4", cast=float, condition=toggle.speed_limit_controller, conversion=speed_conversion)
    toggle.speed_limit_offset5 = self.get_value("Offset5", cast=float, condition=toggle.speed_limit_controller, conversion=speed_conversion)
    toggle.speed_limit_offset6 = self.get_value("Offset6", cast=float, condition=toggle.speed_limit_controller, conversion=speed_conversion)
    toggle.speed_limit_offset7 = self.get_value("Offset7", cast=float, condition=toggle.speed_limit_controller, conversion=speed_conversion)
    toggle.speed_limit_priority1 = self.get_value("SLCPriority1", cast=None, condition=speed_limit_display)
    toggle.speed_limit_priority2 = self.get_value("SLCPriority2", cast=None, condition=speed_limit_display)
    toggle.speed_limit_priority_highest = toggle.speed_limit_priority1 == "Highest"
    toggle.speed_limit_priority_lowest = toggle.speed_limit_priority1 == "Lowest"
    toggle.speed_limit_sources = self.get_value("SpeedLimitSources", condition=speed_limit_display) or toggle.debug_mode

    toggle.speed_limit_filler = self.get_value("SpeedLimitFiller")
    toggle.vision_speed_limit_detection = self.get_value("VisionSpeedLimitDetection")

    toggle.startup_alert_top = self.get_value("StartupMessageTop", cast=str, default="")
    toggle.startup_alert_bottom = self.get_value("StartupMessageBottom", cast=str, default="")

    toggle.subaru_sng = self.get_value("SubaruSNG", condition=toggle.car_make == "subaru" and not (CP.flags & SubaruFlags.GLOBAL_GEN2 or CP.flags & SubaruFlags.HYBRID))

    toggle.tethering_config = self.get_value("TetheringEnabled", cast=float)

    toyota_doors = self.get_value("ToyotaDoors", condition=toggle.car_make == "toyota")
    toggle.lock_doors = self.get_value("LockDoors", condition=toyota_doors)
    toggle.unlock_doors = self.get_value("UnlockDoors", condition=toyota_doors)

    toggle.gm_pedal_longitudinal = self.get_value(
      "GMPedalLongitudinal",
      condition=toggle.car_make == "gm" and toggle.has_pedal,
    )
    toggle.long_pitch = self.get_value(
      "LongPitch",
      condition=toggle.openpilot_longitudinal and toggle.car_make == "gm",
    )
    toggle.remote_start_boots_comma = self.get_value("RemoteStartBootsComma", condition=toggle.car_make == "gm")
    toggle.remap_cancel_to_distance = self.get_value(
      "RemapCancelToDistance",
      condition=toggle.car_make == "gm" and toggle.has_pedal and "BOLT" in toggle.car_model,
    )

    toggle.volt_sng = self.get_value("VoltSNG", condition=toggle.car_model == "CHEVROLET_VOLT")

    process_starpilot_toggles.cache_clear()
    self.params_memory.remove("StarPilotTogglesUpdated")
