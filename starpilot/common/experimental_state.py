#!/usr/bin/env python3
from openpilot.common.params import Params


CE_STATUS_PARAM = "CEStatus"
CC_STATUS_PARAM = "CCStatus"
LONGITUDINAL_PREFERENCE_PARAM = "LongitudinalModelPreference"
LONGITUDINAL_PREFERENCE_OVERRIDE_PARAM = "LongitudinalModelPreferenceOverride"

# Status values stay schema-compatible with the existing onroad widgets.
CEStatus = {
  "OFF": 0,
  "USER_DISABLED": 1,
  "USER_OVERRIDDEN": 2,
  "CURVATURE": 3,
  "LEAD": 4,
  "SIGNAL": 5,
  "SPEED": 6,
  "SPEED_LIMIT": 7,
  "STOP_LIGHT": 8,
}

# Kept only so older/mici status renderers can safely read a stale CCStatus.
CCStatus = {
  "OFF": 0,
  "USER_EXPERIMENTAL": 1,
  "USER_CHILL": 2,
  "LEAD": 4,
  "SPEED": 6,
}


def requested_experimental_mode(params: Params, params_memory: Params | None = None) -> bool:
  if params.get_bool("SafeMode"):
    return False

  persistent = params.get_int(LONGITUDINAL_PREFERENCE_PARAM, default=0)
  override = params_memory.get_int(LONGITUDINAL_PREFERENCE_OVERRIDE_PARAM, default=-1) if params_memory is not None else -1
  return bool(override if override in (0, 1) else persistent)


def toggle_longitudinal_model_preference(params: Params, params_memory: Params) -> bool:
  requested = not requested_experimental_mode(params, params_memory)
  params_memory.put_int(LONGITUDINAL_PREFERENCE_OVERRIDE_PARAM, int(requested))
  return requested
