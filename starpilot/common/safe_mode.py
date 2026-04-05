#!/usr/bin/env python3
from __future__ import annotations

from cereal import log

from openpilot.common.params import Params

SAFE_MODE_PARAM = "SafeMode"
SAFE_MODE_BACKUP_PARAM = "SafeModeBackup"
SAFE_MODE_ENFORCE_FRAMES = 20

# Driving-affecting settings that Safe Mode forces back to safe branch/stock behavior.
SAFE_MODE_MANAGED_KEYS = (
  "ExperimentalMode",
  "LongitudinalPersonality",
  "Model",
  "DrivingModel",
  "DrivingModelName",
  "ModelVersion",
  "DrivingModelVersion",
  "ModelRandomizer",
  "DisableOpenpilotLongitudinal",
  "ForceFingerprint",
  "ClusterOffset",
  "LateralTune",
  "AdvancedLateralTune",
  "ForceAutoTune",
  "ForceAutoTuneOff",
  "ForceTorqueController",
  "SteerDelay",
  "SteerFriction",
  "SteerKP",
  "SteerLatAccel",
  "SteerRatio",
  "LaneChanges",
  "LaneChangeTime",
  "LaneDetectionWidth",
  "MinimumLaneChangeSpeed",
  "NudgelessLaneChange",
  "OneLaneChange",
  "NNFF",
  "NNFFLite",
  "TurnDesires",
  "QOLLateral",
  "PauseLateralSpeed",
  "PauseLateralOnSignal",
  "LongitudinalTune",
  "AdvancedLongitudinalTune",
  "EVTuning",
  "TruckTuning",
  "CustomAccelProfile",
  "CustomAccelProfileInitialized",
  "CustomAccelProfile0MPH",
  "CustomAccelProfile11MPH",
  "CustomAccelProfile22MPH",
  "CustomAccelProfile34MPH",
  "CustomAccelProfile45MPH",
  "CustomAccelProfile56MPH",
  "CustomAccelProfile89MPH",
  "LongitudinalActuatorDelay",
  "MaxDesiredAcceleration",
  "StartAccel",
  "StopAccel",
  "StoppingDecelRate",
  "VEgoStarting",
  "VEgoStopping",
  "AccelerationProfile",
  "DecelerationProfile",
  "HumanAcceleration",
  "HumanFollowing",
  "HumanLaneChanges",
  "LeadDetectionThreshold",
  "RecoveryPower",
  "StopDistance",
  "TacoTune",
  "QOLLongitudinal",
  "ForceStops",
  "ForceStandstill",
  "IncreasedStoppedDistance",
  "MapGears",
  "MapAcceleration",
  "MapDeceleration",
  "ReverseCruise",
  "SetSpeedOffset",
  "WeatherPresets",
  "IncreaseFollowingLowVisibility",
  "IncreaseFollowingRain",
  "IncreaseFollowingRainStorm",
  "IncreaseFollowingSnow",
  "IncreasedStoppedDistanceLowVisibility",
  "IncreasedStoppedDistanceRain",
  "IncreasedStoppedDistanceRainStorm",
  "IncreasedStoppedDistanceSnow",
  "ReduceAccelerationLowVisibility",
  "ReduceAccelerationRain",
  "ReduceAccelerationRainStorm",
  "ReduceAccelerationSnow",
  "ReduceLateralAccelerationLowVisibility",
  "ReduceLateralAccelerationRain",
  "ReduceLateralAccelerationRainStorm",
  "ReduceLateralAccelerationSnow",
  "ConditionalExperimental",
  "CECurves",
  "CECurvesLead",
  "CELead",
  "CESlowerLead",
  "CEStoppedLead",
  "CESpeed",
  "CESpeedLead",
  "CEModelStopTime",
  "CEStopLights",
  "CESignalSpeed",
  "CESignalLaneDetection",
  "CurveSpeedController",
  "SpeedLimitController",
  "SetSpeedLimit",
  "SLCFallback",
  "SLCMapboxFiller",
  "SLCOverride",
  "SLCConfirmation",
  "SLCConfirmationHigher",
  "SLCConfirmationLower",
  "SLCLookaheadHigher",
  "SLCLookaheadLower",
  "SLCPriority1",
  "SLCPriority2",
  "Offset1",
  "Offset2",
  "Offset3",
  "Offset4",
  "Offset5",
  "Offset6",
  "Offset7",
  "SpeedLimitFiller",
  "VisionSpeedLimitDetection",
  "CustomPersonalities",
  "TrafficPersonalityProfile",
  "AggressivePersonalityProfile",
  "StandardPersonalityProfile",
  "RelaxedPersonalityProfile",
  "TrafficFollow",
  "TrafficJerkAcceleration",
  "TrafficJerkDeceleration",
  "TrafficJerkDanger",
  "TrafficJerkSpeed",
  "TrafficJerkSpeedDecrease",
  "AggressiveFollow",
  "AggressiveFollowHigh",
  "AggressiveJerkAcceleration",
  "AggressiveJerkDeceleration",
  "AggressiveJerkDanger",
  "AggressiveJerkSpeed",
  "AggressiveJerkSpeedDecrease",
  "StandardFollow",
  "StandardFollowHigh",
  "StandardJerkAcceleration",
  "StandardJerkDeceleration",
  "StandardJerkDanger",
  "StandardJerkSpeed",
  "StandardJerkSpeedDecrease",
  "RelaxedFollow",
  "RelaxedFollowHigh",
  "RelaxedJerkAcceleration",
  "RelaxedJerkDeceleration",
  "RelaxedJerkDanger",
  "RelaxedJerkSpeed",
  "RelaxedJerkSpeedDecrease",
  "FrogsGoMoosTweak",
  "SNGHack",
  "SubaruSNG",
  "VoltSNG",
  "GMPedalLongitudinal",
  "LongPitch",
  "TacoTuneHacks",
)

SAFE_MODE_FIXED_VALUES = {
  "ExperimentalMode": False,
  "LongitudinalPersonality": int(log.LongitudinalPersonality.relaxed),
}

SAFE_MODE_STOCK_PARAM_MAP = {
  "SteerDelay": "SteerDelayStock",
  "SteerFriction": "SteerFrictionStock",
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

SAFE_MODE_MEMORY_VALUES = {
  "CEStatus": 0,
}


def safe_mode_enabled(params_raw: Params | None = None) -> bool:
  params_raw = params_raw or Params()
  return params_raw.get_bool(SAFE_MODE_PARAM)


def _load_backup(params_raw: Params) -> dict[str, dict]:
  backup = params_raw.get(SAFE_MODE_BACKUP_PARAM)
  return backup if isinstance(backup, dict) else {}


def _current_entry(params_raw: Params, key: str) -> dict[str, object]:
  value = params_raw.get(key)
  return {"present": value is not None, "value": value}


def _safe_value(params: Params, key: str):
  if key in SAFE_MODE_FIXED_VALUES:
    return SAFE_MODE_FIXED_VALUES[key]

  stock_param = SAFE_MODE_STOCK_PARAM_MAP.get(key)
  if stock_param is not None:
    stock_value = params.get(stock_param)
    if stock_value is not None:
      return stock_value

  return params.get_stock_value(key)


def _apply_value(params_raw: Params, key: str, value) -> bool:
  current = params_raw.get(key)
  if value is None:
    if current is None:
      return False
    params_raw.remove(key)
    return True

  if current == value:
    return False

  params_raw.put(key, value)
  return True


def _mark_toggle_update(params_memory: Params | None) -> None:
  if params_memory is None:
    return
  params_memory.put_bool("StarPilotTogglesUpdated", True)


def apply_safe_mode(params: Params, params_raw: Params, params_memory: Params | None = None, *,
                    ensure_backup: bool = True) -> bool:
  changed = False

  if ensure_backup:
    backup = _load_backup(params_raw)
    missing_backup_keys = [key for key in SAFE_MODE_MANAGED_KEYS if key not in backup]
    if missing_backup_keys:
      backup = dict(backup)
      for key in missing_backup_keys:
        backup[key] = _current_entry(params_raw, key)
      params_raw.put(SAFE_MODE_BACKUP_PARAM, backup)
      changed = True

  for key in SAFE_MODE_MANAGED_KEYS:
    changed |= _apply_value(params_raw, key, _safe_value(params, key))

  if params_memory is not None:
    for key, value in SAFE_MODE_MEMORY_VALUES.items():
      if params_memory.get(key) != value:
        params_memory.put(key, value)
        changed = True

  if changed:
    params_raw.put_bool("OnroadCycleRequested", True)
    _mark_toggle_update(params_memory)

  return changed


def restore_safe_mode(params_raw: Params, params_memory: Params | None = None) -> bool:
  changed = False
  backup = _load_backup(params_raw)

  if not backup:
    if params_raw.get(SAFE_MODE_BACKUP_PARAM) is not None:
      params_raw.remove(SAFE_MODE_BACKUP_PARAM)
      changed = True

    if params_memory is not None:
      for key, value in SAFE_MODE_MEMORY_VALUES.items():
        if params_memory.get(key) != value:
          params_memory.put(key, value)
          changed = True

    if changed:
      params_raw.put_bool("OnroadCycleRequested", True)
      _mark_toggle_update(params_memory)
    return changed

  restore_keys = dict.fromkeys((*SAFE_MODE_MANAGED_KEYS, *backup.keys()))
  for key in restore_keys:
    entry = backup.get(key, {"present": False, "value": None})
    restore_value = entry.get("value") if entry.get("present") else None
    changed |= _apply_value(params_raw, key, restore_value)

  if params_raw.get(SAFE_MODE_BACKUP_PARAM) is not None:
    params_raw.remove(SAFE_MODE_BACKUP_PARAM)
    changed = True

  if params_memory is not None:
    for key, value in SAFE_MODE_MEMORY_VALUES.items():
      if params_memory.get(key) != value:
        params_memory.put(key, value)
        changed = True

  if changed:
    params_raw.put_bool("OnroadCycleRequested", True)
    _mark_toggle_update(params_memory)

  return changed
