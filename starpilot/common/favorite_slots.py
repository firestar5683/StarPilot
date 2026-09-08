#!/usr/bin/env python3
from __future__ import annotations

import functools
import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from openpilot.common.params import ParamKeyType, Params


FAVORITE_SLOTS_PARAM = "StarPilotFavoriteSlots"
FAVORITE_SLOT_COUNT = 3
FAVORITE_ACTION_PREFIX = "__starpilot_favorite_action__:"
FAVORITE_ACTION_DISTANCE_DECREASE = f"{FAVORITE_ACTION_PREFIX}distance_decrease"
FAVORITE_ACTION_DISTANCE_INCREASE = f"{FAVORITE_ACTION_PREFIX}distance_increase"
FAVORITE_ACTION_TOGGLE_TRAFFIC_MODE = f"{FAVORITE_ACTION_PREFIX}toggle_traffic_mode"
FAVORITE_ACTION_DECEL_COUNTER = "FavoriteVirtualDecelCruiseCounter"
FAVORITE_ACTION_ACCEL_COUNTER = "FavoriteVirtualAccelCruiseCounter"
FAVORITE_ACTION_TRAFFIC_MODE_COUNTER = "FavoriteTrafficModeCounter"
FAVORITE_ACTION_OPTIONS = (
  {
    "key": FAVORITE_ACTION_DISTANCE_DECREASE,
    "label": "Distance - / SET",
    "description": "Acts like a short press of the car's SET/- cruise button.",
    "section": "Actions",
    "action": "decelCruise",
  },
  {
    "key": FAVORITE_ACTION_DISTANCE_INCREASE,
    "label": "Distance + / RES",
    "description": "Acts like a short press of the car's RES/+ cruise button.",
    "section": "Actions",
    "action": "accelCruise",
  },
  {
    "key": FAVORITE_ACTION_TOGGLE_TRAFFIC_MODE,
    "label": "Toggle Traffic Mode",
    "description": "Engages or disengages Traffic Mode while openpilot is actively controlling.",
    "section": "Actions",
    "action": "trafficMode",
  },
)
FAVORITE_ACTION_KEYS = {option["key"] for option in FAVORITE_ACTION_OPTIONS}
FAVORITE_ACTION_LABELS = {option["key"]: option["label"] for option in FAVORITE_ACTION_OPTIONS}
SETTINGS_CATALOG_PATH = Path(__file__).resolve().parent / "assets" / "device_settings_layout.json"


BLOCKED_ONROAD_KEYS = {
  "ActiveBigModel",
  "ActiveBigModelName",
  "ActiveBigModelVersion",
  "ActiveSmallModel",
  "ActiveSmallModelName",
  "ActiveSmallModelVersion",
  "AlphaLongitudinalEnabled",
  "DrivingModel",
  "Model",
  "ModelVersion",
  "CarMake",
  "CarModel",
  "ForceFingerprint",
  "DisableOpenpilotLongitudinal",
  "SecOCKey",
  "SecOCKeys",
  "SteerRatio",
  "SteerDelay",
  "SteerKP",
  "SteerFriction",
  "SteerLatAccel",
}


def is_param_action_safe_onroad(key: str | None, params: Params | None = None) -> bool:
  if not key or is_favorite_action_key(key):
    return True
  if params is not None and key in BLOCKED_ONROAD_KEYS:
    try:
      if params.get_bool("IsOnroad"):
        return False
    except Exception:
      pass
  return True


@functools.lru_cache(maxsize=4)
def load_settings_catalog(layout_path: Path | str | None = None) -> list[dict[str, Any]] | None:
  try:
    with Path(layout_path or SETTINGS_CATALOG_PATH).open(encoding="utf-8") as layout_file:
      layout_data = json.load(layout_file)
  except (OSError, json.JSONDecodeError, TypeError):
    return None

  if not isinstance(layout_data, list):
    return None
  return [section for section in layout_data if isinstance(section, dict)]


@functools.lru_cache(maxsize=4)
def get_catalog_param_map(layout_path: Path | str | None = None) -> dict[str, dict[str, Any]]:
  """Returns a dictionary mapping param key to its full catalog descriptor."""
  layout_data = load_settings_catalog(layout_path)
  if layout_data is None:
    return {}

  catalog_map = {}
  for section in layout_data:
    if not isinstance(section, dict):
      continue
    section_name = str(section.get("name") or "")
    for param_data in section.get("params", []):
      if not isinstance(param_data, dict):
        continue
      key = str(param_data.get("key") or "").strip()
      if not key:
        continue
      entry = dict(param_data)
      entry["section"] = section_name
      catalog_map[key] = entry
  return catalog_map


def build_favorite_slot_options(is_eligible_param: Callable[[str], bool], *,
                                alpha_longitudinal_available: bool,
                                layout_path: Path | str | None = None) -> list[dict[str, Any]]:
  """Build the shared Galaxy/Big UI favorite-option catalogue.

  Supports boolean toggles, safe multi-state dropdowns (N <= 4), and virtual actions.
  """
  catalog_map = get_catalog_param_map(layout_path)
  if not catalog_map:
    return []

  options = [dict(option) for option in FAVORITE_ACTION_OPTIONS]
  for key, param_data in catalog_map.items():
    if param_data.get("galaxy_only"):
      continue

    ui_type = str(param_data.get("ui_type") or "")
    data_type = str(param_data.get("data_type") or "")
    raw_options = param_data.get("options")

    # Eligibility rules:
    # 1. Boolean toggles
    # 2. Multi-state dropdowns with 2 to 4 options (e.g. AccelerationProfile, CameraView)
    is_toggle = (ui_type == "toggle" and data_type == "bool")
    is_dropdown = (ui_type == "dropdown" and isinstance(raw_options, list) and 2 <= len(raw_options) <= 4)

    if not (is_toggle or is_dropdown):
      continue

    if key == "AlphaLongitudinalEnabled" and not alpha_longitudinal_available:
      continue

    try:
      if not is_eligible_param(key):
        continue
    except Exception:
      continue

    opt_dict: dict[str, Any] = {
      "key": key,
      "label": str(param_data.get("label") or key),
      "description": str(param_data.get("description") or ""),
      "section": param_data.get("section", ""),
      "ui_type": ui_type,
      "data_type": data_type,
      "requiresCapability": str(param_data.get("requires_capability") or ""),
    }
    for picker_field in ("picker_label", "picker_description"):
      picker_value = str(param_data.get(picker_field) or "").strip()
      if picker_value:
        opt_dict[picker_field] = picker_value
    if is_dropdown:
      opt_dict["options"] = [dict(o) for o in raw_options if isinstance(o, dict)]
    options.append(opt_dict)

  options.sort(key=lambda option: (
    str(option.get("label") or option.get("key") or "").casefold(),
    str(option.get("key") or "").casefold(),
  ))
  return options


def filter_favorite_slot_options(options: Iterable[Mapping[str, Any]],
                                 capabilities: Mapping[str, bool] | None = None) -> list[dict[str, Any]]:
  """Keep only favorite options whose declared capability is currently present."""
  capabilities = capabilities or {}
  return [
    dict(option)
    for option in options
    if not option.get("requiresCapability") or capabilities.get(str(option["requiresCapability"]), False)
  ]


def default_favorite_slots() -> list[dict[str, Any]]:
  return [
    {"enabled": False, "show_onroad": False, "key": None, "label": ""}
    for _ in range(FAVORITE_SLOT_COUNT)
  ]


def _load_raw_slots(raw_slots: Any) -> list[Any]:
  if raw_slots in (None, "", b""):
    return default_favorite_slots()

  if isinstance(raw_slots, bytes):
    raw_slots = raw_slots.decode("utf-8", errors="replace")

  if isinstance(raw_slots, str):
    try:
      raw_slots = json.loads(raw_slots)
    except json.JSONDecodeError:
      return default_favorite_slots()

  if isinstance(raw_slots, dict):
    raw_slots = raw_slots.get("slots", [])

  return raw_slots if isinstance(raw_slots, list) else default_favorite_slots()


def _get_key_type(params: Params, key: str):
  for getter_name in ("get_type", "get_key_type"):
    getter = getattr(params, getter_name, None)
    if getter is None:
      continue
    try:
      return getter(key)
    except Exception:
      return None
  return None


def is_enum_param(key: str | None, catalog_map: Mapping[str, dict[str, Any]] | None = None) -> bool:
  if not key:
    return False
  if catalog_map is None:
    catalog_map = get_catalog_param_map()
  meta = catalog_map.get(key, {})
  return meta.get("ui_type") == "dropdown" and isinstance(meta.get("options"), list)


def get_param_enum_options(key: str | None, catalog_map: Mapping[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
  if not key:
    return []
  if catalog_map is None:
    catalog_map = get_catalog_param_map()
  meta = catalog_map.get(key, {})
  raw_options = meta.get("options", [])
  return [dict(opt) for opt in raw_options if isinstance(opt, dict)]


def get_favorite_param_value(key: str | None, params: Params | None = None,
                             catalog_map: Mapping[str, dict[str, Any]] | None = None) -> Any:
  """Safely extract typed value (bool, int, float, str) for a favorite parameter."""
  if not key or is_favorite_action_key(key):
    return None

  params = params or Params(return_defaults=True)
  if catalog_map is None:
    catalog_map = get_catalog_param_map()

  meta = catalog_map.get(key, {})
  ui_type = meta.get("ui_type")
  data_type = meta.get("data_type")
  options = meta.get("options")

  if ui_type == "dropdown" or (isinstance(options, list) and options):
    first_val = options[0].get("value") if options else None
    key_type = _get_key_type(params, key)
    if key_type == ParamKeyType.INT or isinstance(first_val, int) or data_type == "int":
      try:
        return params.get_int(key)
      except Exception:
        return int(first_val) if first_val is not None else 0
    elif data_type == "float" or isinstance(first_val, float):
      try:
        return params.get_float(key)
      except Exception:
        return float(first_val) if first_val is not None else 0.0
    else:
      try:
        val = params.get(key, encoding="utf-8")
        return val if val is not None else str(first_val or "")
      except Exception:
        return str(first_val or "")

  if ui_type == "toggle" or data_type == "bool" or _get_key_type(params, key) == ParamKeyType.BOOL:
    try:
      return params.get_bool(key)
    except Exception:
      return False

  try:
    return params.get(key, encoding="utf-8")
  except Exception:
    return None


def get_favorite_values(items: Iterable[str | Mapping[str, Any]],
                        params: Params | None = None) -> dict[str, Any]:
  """Extract a dictionary of typed parameter values for an iterable of keys, options, or slots."""
  params = params or Params(return_defaults=True)
  catalog_map = get_catalog_param_map()
  values: dict[str, Any] = {}
  for item in items:
    key = item if isinstance(item, str) else (item.get("key") if isinstance(item, Mapping) else None)
    if key and not is_favorite_action_key(key):
      values[key] = get_favorite_param_value(key, params, catalog_map=catalog_map)
  return values


def get_favorite_enum_state(key: str | None, params: Params | None = None,
                            catalog_map: Mapping[str, dict[str, Any]] | None = None) -> tuple[Any, int, str, list[dict[str, Any]]]:
  """Returns (current_value, active_index, active_label, options_list) for an enum/dropdown favorite."""
  if not key:
    return None, 0, "", []

  params = params or Params(return_defaults=True)
  if catalog_map is None:
    catalog_map = get_catalog_param_map()

  options = get_param_enum_options(key, catalog_map=catalog_map)
  if not options:
    return None, 0, "", []

  curr_val = get_favorite_param_value(key, params, catalog_map=catalog_map)
  first_val = options[0].get("value")
  is_int = isinstance(first_val, int)

  if is_int:
    val_list = [int(o["value"]) for o in options if "value" in o]
    try:
      active_idx = val_list.index(int(curr_val)) if curr_val is not None else 0
    except (ValueError, TypeError):
      active_idx = 0
  else:
    val_list = [str(o["value"]) for o in options if "value" in o]
    try:
      active_idx = val_list.index(str(curr_val)) if curr_val is not None else 0
    except (ValueError, TypeError):
      active_idx = 0

  active_opt = options[active_idx] if active_idx < len(options) else options[0]
  active_label = str(active_opt.get("label") or active_opt.get("value") or "")
  return curr_val, active_idx, active_label, options


def cycle_enum_parameter(key: str, params: Params | None = None,
                         params_memory: Params | None = None, *,
                         options: list[dict[str, Any]] | None = None,
                         catalog_map: Mapping[str, dict[str, Any]] | None = None) -> bool:
  """Safely cycle an int or string enum parameter to its next option without blocking."""
  if not key:
    return False
  params = params or Params(return_defaults=True)
  if not is_param_action_safe_onroad(key, params):
    return False

  _curr_val, active_idx, _label, detected_options = get_favorite_enum_state(key, params, catalog_map=catalog_map)
  opts = options if options is not None else detected_options
  if not opts or len(opts) < 2:
    return False

  next_idx = (active_idx + 1) % len(opts)
  next_val = opts[next_idx].get("value")
  if next_val is None:
    return False

  key_type = _get_key_type(params, key)
  is_int_enum = (key_type == ParamKeyType.INT or isinstance(opts[0].get("value"), int))

  put_nonblocking = getattr(params, "put_nonblocking", None) or getattr(params, "put", None)
  if put_nonblocking is None:
    return False

  if is_int_enum:
    put_int_nonblocking = getattr(params, "put_int_nonblocking", None)
    if put_int_nonblocking is not None:
      put_int_nonblocking(key, int(next_val))
    else:
      put_nonblocking(key, int(next_val))
  else:
    put_nonblocking(key, str(next_val))

  request_starpilot_toggle_refresh(params_memory)
  return True


def is_favorite_action_key(key: str | None) -> bool:
  return bool(key) and key in FAVORITE_ACTION_KEYS


def favorite_key_is_valid(params: Params, key: str | None, eligible_keys: Iterable[str] | None = None) -> bool:
  if not key:
    return False

  if is_favorite_action_key(key):
    return True

  if eligible_keys is not None:
    return key in set(eligible_keys)

  return is_bool_param(params, key) or is_enum_param(key)


def is_bool_param(params: Params, key: str | None, eligible_keys: Iterable[str] | None = None) -> bool:
  if not key:
    return False

  if eligible_keys is not None and key not in set(eligible_keys):
    return False

  return _get_key_type(params, key) == ParamKeyType.BOOL


def normalize_favorite_slots(raw_slots: Any, params: Params | None = None,
                             eligible_keys: Iterable[str] | None = None) -> list[dict[str, Any]]:
  slots = default_favorite_slots()
  eligible = set(eligible_keys) if eligible_keys is not None else None

  for idx, raw_slot in enumerate(_load_raw_slots(raw_slots)[:FAVORITE_SLOT_COUNT]):
    if not isinstance(raw_slot, dict):
      continue

    key = raw_slot.get("key")
    if key is not None:
      key = str(key).strip() or None

    if key and is_favorite_action_key(key):
      pass
    elif key and (
      (eligible is not None and key not in eligible) or
      (params is not None and not favorite_key_is_valid(params, key, eligible_keys=eligible))
    ):
      key = None

    label = str(raw_slot.get("label") or FAVORITE_ACTION_LABELS.get(key, "")).strip()
    if len(label) > 32:
      label = label[:32].rstrip()

    slots[idx] = {
      "enabled": bool(raw_slot.get("enabled", False)),
      "show_onroad": bool(raw_slot.get("show_onroad", False)),
      "key": key,
      "label": label if key else "",
    }

  return slots


def load_favorite_slots(params: Params | None = None, eligible_keys: Iterable[str] | None = None) -> list[dict[str, Any]]:
  params = params or Params(return_defaults=True)
  try:
    raw_slots = params.get(FAVORITE_SLOTS_PARAM)
  except Exception:
    raw_slots = None
  return normalize_favorite_slots(raw_slots, params=params, eligible_keys=eligible_keys)


def save_favorite_slots(slots: list[dict[str, Any]], params: Params | None = None, *,
                        eligible_keys: Iterable[str] | None = None) -> list[dict[str, Any]]:
  params = params or Params(return_defaults=True)
  normalized = normalize_favorite_slots(slots, params=params, eligible_keys=eligible_keys)
  params.put(FAVORITE_SLOTS_PARAM, normalized)
  return normalized


def request_starpilot_toggle_refresh(params_memory: Params | None = None) -> None:
  params_memory = params_memory or Params(memory=True)
  params_memory.put_bool("StarPilotTogglesUpdated", True)


def trigger_favorite_action(key: str | None, params_memory: Params | None = None) -> bool:
  if not is_favorite_action_key(key):
    return False

  params_memory = params_memory or Params(memory=True)
  counter_key = {
    FAVORITE_ACTION_DISTANCE_DECREASE: FAVORITE_ACTION_DECEL_COUNTER,
    FAVORITE_ACTION_DISTANCE_INCREASE: FAVORITE_ACTION_ACCEL_COUNTER,
    FAVORITE_ACTION_TOGGLE_TRAFFIC_MODE: FAVORITE_ACTION_TRAFFIC_MODE_COUNTER,
  }[key]
  params_memory.put_int(counter_key, params_memory.get_int(counter_key) + 1)
  return True


def execute_favorite_key(key: str | None, params: Params | None = None, params_memory: Params | None = None, *,
                         eligible_keys: Iterable[str] | None = None) -> bool:
  params = params or Params(return_defaults=True)
  eligible_keys = set(eligible_keys) if eligible_keys is not None else None
  if not favorite_key_is_valid(params, key, eligible_keys=eligible_keys):
    return False
  if not is_param_action_safe_onroad(key, params):
    return False

  if is_favorite_action_key(key):
    return trigger_favorite_action(key, params_memory)

  if is_enum_param(key):
    return cycle_enum_parameter(key, params, params_memory)

  if is_bool_param(params, key, eligible_keys=eligible_keys):
    next_value = not params.get_bool(key)
    put_bool = getattr(params, "put_bool_nonblocking", None) or getattr(params, "put_bool", None)
    if put_bool is None:
      return False

    put_bool(key, next_value)
    request_starpilot_toggle_refresh(params_memory)
    return True

  return False


def toggle_favorite_slot(slot_index: int, params: Params | None = None, params_memory: Params | None = None, *,
                         eligible_keys: Iterable[str] | None = None) -> bool:
  """Universal polymorphic favorite execution dispatcher."""
  if slot_index < 0 or slot_index >= FAVORITE_SLOT_COUNT:
    return False

  params = params or Params(return_defaults=True)
  eligible_keys = set(eligible_keys) if eligible_keys is not None else None
  slots = load_favorite_slots(params, eligible_keys=eligible_keys)
  slot = slots[slot_index]
  key = slot.get("key")
  if not slot.get("enabled") or not key:
    return False
  return execute_favorite_key(key, params, params_memory, eligible_keys=eligible_keys)


def unassign_favorite_slot(slot_index: int, params: Params | None = None, params_memory: Params | None = None, *,
                           eligible_keys: Iterable[str] | None = None) -> list[dict[str, Any]] | None:
  """Reset a slot to the disabled/unassigned state and notify listeners."""
  if slot_index < 0 or slot_index >= FAVORITE_SLOT_COUNT:
    return None

  params = params or Params(return_defaults=True)
  eligible_keys = set(eligible_keys) if eligible_keys is not None else None
  slots = load_favorite_slots(params, eligible_keys=eligible_keys)
  slots[slot_index] = {"enabled": False, "show_onroad": False, "key": None, "label": ""}
  saved = save_favorite_slots(slots, params, eligible_keys=eligible_keys)
  request_starpilot_toggle_refresh(params_memory)
  return saved
