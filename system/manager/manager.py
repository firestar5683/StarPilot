#!/usr/bin/env python3
import datetime
import json
import os
import shutil
from pathlib import Path
import signal
import stat
import sys
import time
import traceback

_MANAGER_IMPORT_START = time.monotonic()
_BOOT_TIMING_LOG_PATH = os.environ.get("SP_BOOT_TIMING_LOG", "/tmp/starpilot_boot_timing.log")


def _append_boot_timing_line(line: str) -> None:
  try:
    with open(_BOOT_TIMING_LOG_PATH, "a") as f:
      f.write(line + "\n")
  except OSError:
    pass


from cereal import car, log
import cereal.messaging as messaging
import openpilot.system.sentry as sentry
from openpilot.common.utils import atomic_write
from openpilot.common.params import Params, ParamKeyFlag, ParamKeyType
from openpilot.common.text_window import TextWindow
from openpilot.system.hardware import HARDWARE
from openpilot.system.manager.helpers import unblock_stdout, write_onroad_params, save_bootlog
from openpilot.system.manager.process import ensure_running
from openpilot.system.manager.process_config import managed_processes
from openpilot.system.athena.registration import register, UNREGISTERED_DONGLE_ID
from openpilot.common.swaglog import cloudlog, add_file_handler
from openpilot.system.version import get_build_metadata, terms_version, training_version
from openpilot.system.hardware.hw import Paths

_MANAGER_CORE_IMPORT_DONE = time.monotonic()

from openpilot.starpilot.common.starpilot_functions import starpilot_boot_functions, install_starpilot, uninstall_starpilot
from openpilot.starpilot.common.starpilot_variables import (
  LEGACY_STARPILOT_PARAM_RENAMES,
  LEGACY_STARPILOT_STATS_KEY_RENAMES,
  get_starpilot_toggles,
)

_MANAGER_IMPORT_DONE = time.monotonic()
_manager_import_timing_line = (
  "SP_BOOT_TIMING manager_import "
  f"core={_MANAGER_CORE_IMPORT_DONE - _MANAGER_IMPORT_START:.3f}s "
  f"starpilot={_MANAGER_IMPORT_DONE - _MANAGER_CORE_IMPORT_DONE:.3f}s "
  f"total={_MANAGER_IMPORT_DONE - _MANAGER_IMPORT_START:.3f}s"
)
print(_manager_import_timing_line, flush=True)
_append_boot_timing_line(_manager_import_timing_line)


LEGACY_BOLT_FP_MIGRATION_FLAG = Path("/data") / "legacy_bolt_fp_migration_v1"
STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG = Path("/data") / "starpilot_defaults_parity_v1"
STARPILOT_HUMANLIKE_DISABLE_MIGRATION_FLAG = Path("/data") / "starpilot_humanlike_disable_v1"
STARPILOT_CLUSTER_OFFSET_MIGRATION_FLAG = Path("/data") / "starpilot_cluster_offset_v1"
STARPILOT_TRAFFIC_SMOOTH_MIGRATION_FLAG = Path("/data") / "starpilot_traffic_smooth_v1"
STARPILOT_TRAFFIC_FOLLOW_MIGRATION_FLAG = Path("/data") / "starpilot_traffic_follow_v1"
STARPILOT_PARAM_RENAME_MIGRATION_FLAG = Path("/data") / "starpilot_param_rename_v1"
STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG = Path("/data") / "starpilot_param_canonicalization_v1"
STARPILOT_PC_ROOT_MIGRATION_FLAG = Path("/data") / "starpilot_pc_root_v1"
STARPILOT_PARAMS_CACHE_MIGRATION_FLAG = Path("/data") / "starpilot_params_cache_v1"
STARPILOT_DEFAULT_MODEL_MIGRATION_FLAG = Path("/data") / "starpilot_default_model_rdf_v4"
STARPILOT_CE_MODEL_STOP_TIME_MIGRATION_FLAG = Path("/data") / "starpilot_ce_model_stop_time_v2"
STARPILOT_LEGACY_CACHE_MARKER_KEYS = ("RemapCancelToDistance",)
STARPILOT_REMOVED_PARAM_KEYS = (
  "CoastUpToLeads", "HumanAcceleration", "HumanFollowing", "PrioritizeSmoothFollowing", "ReverseCruise",
)
LEGACY_CARMODEL_MIGRATIONS = {
  "CHEVROLET_BOLT_CC_2019_2021": "CHEVROLET_BOLT_CC_2018_2021",
}
STARPILOT_STATS_DROP_KEYS = {"CurrentMonthsKilometers", "ResetStats"}
STARPILOT_STATS_MAX_KEYS = {"LongestDistanceWithoutOverride", "MaxAcceleration"}


def _log_boot_timing(scope: str, label: str, start: float, previous: float | None = None) -> float:
  now = time.monotonic()
  base = previous if previous is not None else start
  line = f"SP_BOOT_TIMING {scope} {label} +{now - base:.3f}s total={now - start:.3f}s"
  _append_boot_timing_line(line)
  cloudlog.warning(line)
  return now


def _to_text(value):
  if value is None:
    return None
  if isinstance(value, bytes):
    return value.decode("utf-8", errors="ignore")
  return str(value)


def _has_meaningful_param_value(value) -> bool:
  if value is None:
    return False
  if isinstance(value, bool):
    return True
  if isinstance(value, (bytes, bytearray, str, dict, list, tuple, set)):
    return len(value) > 0
  return True


def _is_numeric_stat_value(value) -> bool:
  return isinstance(value, (int, float)) and not isinstance(value, bool)


def _get_int_param_value(params, key: str, default: int = 0) -> int:
  getter = getattr(params, "get_int", None)
  if callable(getter):
    try:
      return int(getter(key))
    except Exception:
      pass

  value = params.get(key)
  if value is None:
    return default
  if isinstance(value, bytes):
    value = value.decode("utf-8", errors="ignore")

  try:
    return int(float(str(value).strip()))
  except (TypeError, ValueError):
    return default


def get_nav_offroad_clear_timeout_seconds(params) -> int:
  return max(_get_int_param_value(params, "ClearNavOnOffroadTimeoutMinutes", 0), 0) * 60


def update_nav_offroad_clear_state(
  params,
  started: bool,
  tracked_destination,
  tracked_started_at,
  now: float,
  *,
  offroad_transition: bool,
):
  if started or not params.get_bool("ClearNavOnOffroad"):
    return None, None

  nav_destination = params.get("NavDestination")
  if offroad_transition:
    if not nav_destination:
      return None, None
    tracked_destination = nav_destination
    tracked_started_at = now
  elif tracked_destination is None or tracked_started_at is None:
    return None, None

  if nav_destination != tracked_destination:
    return None, None

  if now - tracked_started_at >= get_nav_offroad_clear_timeout_seconds(params):
    current_destination = params.get("NavDestination")
    if current_destination != tracked_destination:
      return None, None
    params.remove("NavDestination")
    return None, None

  return tracked_destination, tracked_started_at


def should_defer_reboot(param: str, started: bool, ignition: bool) -> bool:
  return param == "DoReboot" and (started or ignition)


def _merge_starpilot_stat_values(existing, incoming, key=None):
  if existing is None:
    return incoming
  if incoming is None:
    return existing

  if isinstance(existing, dict) and isinstance(incoming, dict):
    merged = dict(existing)
    for child_key, child_value in incoming.items():
      merged[child_key] = _merge_starpilot_stat_values(merged.get(child_key), child_value, child_key)
    return merged

  if key == "Month":
    return incoming

  if key in STARPILOT_STATS_MAX_KEYS and _is_numeric_stat_value(existing) and _is_numeric_stat_value(incoming):
    return max(existing, incoming)

  if _is_numeric_stat_value(existing) and _is_numeric_stat_value(incoming):
    return existing + incoming

  return incoming


def _normalize_starpilot_stats_value(value):
  if isinstance(value, dict):
    normalized = {}
    for child_key, child_value in value.items():
      normalized[child_key] = _merge_starpilot_stat_values(
        normalized.get(child_key),
        _normalize_starpilot_stats_value(child_value),
        child_key,
      )
    return normalized
  return value


def _normalize_starpilot_stats(stats):
  if not isinstance(stats, dict):
    return {}

  normalized = {}
  for key, value in stats.items():
    mapped_key = LEGACY_STARPILOT_STATS_KEY_RENAMES.get(key, key)
    if mapped_key in STARPILOT_STATS_DROP_KEYS:
      continue

    normalized[mapped_key] = _merge_starpilot_stat_values(
      normalized.get(mapped_key),
      _normalize_starpilot_stats_value(value),
      mapped_key,
    )

  return normalized


def _load_first_available_param_value(params: Params, params_cache: Params, source_key: str, typed_key: str):
  for params_obj in (params, params_cache):
    raw_value = _read_raw_param_bytes(params_obj, source_key)
    if not raw_value:
      continue

    try:
      return params.cpp2python(typed_key, raw_value)
    except Exception:
      cloudlog.exception(f"Failed to decode legacy param {source_key} as {typed_key}")

  return None


def _has_persisted_param_file(params: Params, key: str | bytes) -> bool:
  try:
    path = params.get_param_path(key)
  except Exception:
    return False

  return bool(path) and os.path.isfile(path)


def _remove_persisted_param_file(params: Params, key: str | bytes) -> bool:
  try:
    path = params.get_param_path(key)
  except Exception:
    return False

  if not path or not os.path.isfile(path):
    return False

  try:
    os.remove(path)
    return True
  except Exception:
    cloudlog.exception(f"Failed to remove deprecated param file: {key}")
    return False


def _params_store_path(root: str | Path) -> Path:
  return Path(root) / os.environ.get("OPENPILOT_PREFIX", "d")


def _cache_store_has_starpilot_marker(cache_root: str | Path) -> bool:
  store_path = _params_store_path(cache_root)
  return any((store_path / key).is_file() for key in STARPILOT_LEGACY_CACHE_MARKER_KEYS)


def _copy_param_store_without_overwrite(source: Path, destination: Path) -> int:
  if not source.is_dir():
    return 0

  destination.mkdir(parents=True, exist_ok=True)
  copied_entries = 0
  for path in source.iterdir():
    if not path.is_file() or path.name == ".lock" or path.name.startswith(".tmp_"):
      continue

    target = destination / path.name
    if target.exists():
      continue

    shutil.copy2(path, target)
    copied_entries += 1

  return copied_entries


def migrate_legacy_starpilot_params_cache(params: Params, legacy_cache_root: str | Path, cache_root: str | Path) -> None:
  if STARPILOT_PARAMS_CACHE_MIGRATION_FLAG.exists():
    return

  legacy_store = _params_store_path(legacy_cache_root)
  cache_store = _params_store_path(cache_root)
  active_marker = any(_has_persisted_param_file(params, key) for key in STARPILOT_LEGACY_CACHE_MARKER_KEYS)
  cache_marker = _cache_store_has_starpilot_marker(legacy_cache_root)

  migration_succeeded = True
  copied_entries = 0
  if active_marker or cache_marker:
    try:
      copied_entries = _copy_param_store_without_overwrite(legacy_store, cache_store)
    except Exception:
      migration_succeeded = False
      cloudlog.exception(f"Failed to migrate legacy StarPilot params cache from {legacy_store} to {cache_store}")
  elif legacy_store.exists():
    cloudlog.warning(f"Skipped legacy params cache import without StarPilot marker: {legacy_store}")

  if not migration_succeeded:
    return

  if copied_entries:
    cloudlog.warning(f"Migrated {copied_entries} legacy StarPilot params cache entries from {legacy_store} to {cache_store}")

  try:
    STARPILOT_PARAMS_CACHE_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_PARAMS_CACHE_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_PARAMS_CACHE_MIGRATION_FLAG}")


def _normalize_secoc_key(candidate) -> str | None:
  if isinstance(candidate, bytes):
    candidate = candidate.decode("utf-8", errors="ignore")
  if not isinstance(candidate, str):
    return None

  candidate = candidate.strip()
  try:
    return candidate if len(bytes.fromhex(candidate)) == 16 else None
  except ValueError:
    return None


def migrate_legacy_secoc_key(params: Params, params_cache: Params, legacy_cache_root: str | Path) -> None:
  if _normalize_secoc_key(params.get("SecOCKey")) is not None or _normalize_secoc_key(params_cache.get("SecOCKey")) is not None:
    return

  legacy_cache_root = Path(legacy_cache_root)
  candidates = []
  try:
    candidates.append(Params(str(legacy_cache_root)).get("SecOCKey"))
  except Exception:
    pass

  try:
    candidates.append((legacy_cache_root / "SecOCKey").read_text())
  except OSError:
    pass

  for candidate in candidates:
    normalized_key = _normalize_secoc_key(candidate)
    if normalized_key is not None:
      params.put("SecOCKey", normalized_key)
      params_cache.put("SecOCKey", normalized_key)
      cloudlog.warning("Recovered Toyota SecOC key from legacy params cache")
      return


def cleanup_removed_starpilot_params(params: Params, params_cache: Params) -> None:
  removed_keys = []
  for key in STARPILOT_REMOVED_PARAM_KEYS:
    removed = _remove_persisted_param_file(params, key)
    removed = _remove_persisted_param_file(params_cache, key) or removed
    if removed:
      removed_keys.append(key)

  if removed_keys:
    cloudlog.warning(f"Removed deprecated StarPilot params: {removed_keys}")


def migrate_starpilot_param_renames(params: Params, params_cache: Params) -> None:
  if STARPILOT_PARAM_RENAME_MIGRATION_FLAG.exists():
    return

  migrated_keys: list[str] = []

  for old_key, new_key in LEGACY_STARPILOT_PARAM_RENAMES.items():
    if new_key == "StarPilotStats":
      continue

    migrated_value = _load_first_available_param_value(params, params_cache, old_key, new_key)
    if not _has_meaningful_param_value(migrated_value):
      continue

    current_value = params.get(new_key)
    if _has_meaningful_param_value(current_value) and not (new_key == "StarPilotDongleId" and current_value != migrated_value):
      continue

    try:
      if current_value != migrated_value:
        params.put(new_key, migrated_value)
        params_cache.put(new_key, migrated_value)
        migrated_keys.append(f"{old_key}->{new_key}")
    except Exception:
      cloudlog.exception(f"Failed to migrate legacy param {old_key} to {new_key}")

  old_stats = _normalize_starpilot_stats(_load_first_available_param_value(params, params_cache, "FrogPilotStats", "StarPilotStats"))
  new_stats = _normalize_starpilot_stats(_load_first_available_param_value(params, params_cache, "StarPilotStats", "StarPilotStats"))
  merged_stats = new_stats if old_stats == new_stats else _merge_starpilot_stat_values(old_stats, new_stats, "StarPilotStats")

  if _has_meaningful_param_value(merged_stats):
    current_stats = params.get("StarPilotStats")
    if current_stats != merged_stats:
      try:
        params.put("StarPilotStats", merged_stats)
        params_cache.put("StarPilotStats", merged_stats)
        migrated_keys.append("FrogPilotStats->StarPilotStats")
      except Exception:
        cloudlog.exception("Failed to migrate legacy StarPilot stats payload")

  if migrated_keys:
    cloudlog.warning(f"Applied legacy StarPilot param rename migration for {migrated_keys}")

  try:
    STARPILOT_PARAM_RENAME_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_PARAM_RENAME_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_PARAM_RENAME_MIGRATION_FLAG}")


def _merge_tree_without_overwrite(source: Path, destination: Path) -> int:
  moved_entries = 0

  if not source.exists():
    return moved_entries

  if not destination.exists():
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return 1

  for path in sorted(source.rglob("*"), key=lambda p: (len(p.parts), str(p))):
    target = destination / path.relative_to(source)
    if path.is_dir():
      target.mkdir(parents=True, exist_ok=True)
      continue

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
      continue

    shutil.move(str(path), str(target))
    moved_entries += 1

  for directory in sorted((p for p in source.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
    try:
      directory.rmdir()
    except OSError:
      pass

  try:
    source.rmdir()
  except OSError:
    pass

  return moved_entries


def migrate_starpilot_pc_root() -> None:
  if HARDWARE.get_device_type() != "pc" or STARPILOT_PC_ROOT_MIGRATION_FLAG.exists():
    return

  old_root = Path(Paths.comma_home()) / "frogpilot"
  new_root = Path(Paths.comma_home()) / "starpilot"

  moved_entries = 0
  migration_succeeded = True
  if old_root.exists():
    try:
      moved_entries = _merge_tree_without_overwrite(old_root, new_root)
    except Exception:
      migration_succeeded = False
      cloudlog.exception(f"Failed to migrate legacy PC StarPilot root from {old_root} to {new_root}")

  if moved_entries:
    cloudlog.warning(f"Migrated legacy PC StarPilot root from {old_root} to {new_root}")

  if not migration_succeeded:
    return

  try:
    STARPILOT_PC_ROOT_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_PC_ROOT_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_PC_ROOT_MIGRATION_FLAG}")


def migrate_legacy_bolt_fingerprint(params: Params) -> None:
  old_fp, new_fp = next(iter(LEGACY_CARMODEL_MIGRATIONS.items()))
  carparams_keys = ("CarParams", "CarParamsCache", "CarParamsPersistent", "CarParamsPrevRoute")
  keys_to_clear = (
    "CarParams",
    "CarParamsCache",
    "CarParamsPersistent",
    "CarParamsPrevRoute",
    "StarPilotCarParams",
    "StarPilotCarParamsPersistent",
  )

  car_model = _to_text(params.get("CarModel"))
  legacy_detected = car_model == old_fp
  if not legacy_detected:
    old_fp_bytes = old_fp.encode()
    for key in carparams_keys:
      raw = params.get(key)
      if raw is None:
        continue

      raw_bytes = raw if isinstance(raw, bytes) else str(raw).encode()
      # Fast path for payloads that still embed the legacy fingerprint string.
      if old_fp_bytes in raw_bytes:
        legacy_detected = True
        break

      # Fallback decode for payloads that don't expose the raw string directly.
      try:
        with car.CarParams.from_bytes(raw_bytes) as cp:
          if cp.carFingerprint == old_fp:
            legacy_detected = True
            break
      except Exception:
        continue

  if not legacy_detected:
    return

  cleared_keys: list[str] = []
  for key in keys_to_clear:
    if params.get(key) is None:
      continue
    params.remove(key)
    cleared_keys.append(key)

  if car_model == old_fp:
    params.put("CarModel", new_fp)
  car_model_name = _to_text(params.get("CarModelName")) or ""
  if "2019-21" in car_model_name:
    params.put("CarModelName", car_model_name.replace("2019-21", "2018-21"))

  cloudlog.warning(
    f"Detected legacy Bolt fingerprint {old_fp}; cleared={cleared_keys}, remapped CarModel to {new_fp}"
  )

  try:
    LEGACY_BOLT_FP_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    LEGACY_BOLT_FP_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {LEGACY_BOLT_FP_MIGRATION_FLAG}")


def migrate_starpilot_default_parity(params: Params, params_cache: Params) -> None:
  if STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG.exists():
    return

  seeded_keys: list[str] = []
  desired_bool_values = {
    "AdvancedLateralTune": True,
    "ForceAutoTuneOff": True,
    "NNFF": False,
    "NNFFLite": False,
  }

  for key, value in desired_bool_values.items():
    if _has_persisted_param_file(params, key) or _has_persisted_param_file(params_cache, key):
      continue
    params.put_bool(key, value)
    params_cache.put_bool(key, value)
    seeded_keys.append(key)

  if not _has_persisted_param_file(params, "CEModelStopTime") and not _has_persisted_param_file(params_cache, "CEModelStopTime"):
    params.put_float("CEModelStopTime", 7.7)
    params_cache.put_float("CEModelStopTime", 7.7)
    seeded_keys.append("CEModelStopTime")

  # Rebase default regression fix:
  # EVTuning must default to enabled on EV/direct-drive platforms to preserve
  # StarPilot acceleration profile behavior, but existing user overrides win.
  carparams_blob = params.get("CarParamsPersistent") or params.get("CarParams")
  if carparams_blob is not None:
    try:
      with car.CarParams.from_bytes(carparams_blob) as cp:
        is_ev_platform = cp.transmissionType == car.CarParams.TransmissionType.direct
      if is_ev_platform and not params.get_bool("TruckTuning") and not _has_persisted_param_file(params, "EVTuning") and not _has_persisted_param_file(params_cache, "EVTuning"):
        params.put_bool("EVTuning", True)
        params_cache.put_bool("EVTuning", True)
        seeded_keys.append("EVTuning")
    except Exception:
      cloudlog.exception("Failed EVTuning EV default parity migration")

  if seeded_keys:
    cloudlog.warning(f"Applied one-time StarPilot default parity migration for {seeded_keys}")

  try:
    STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_DEFAULTS_PARITY_MIGRATION_FLAG}")


def migrate_starpilot_default_model(params: Params, params_cache: Params) -> None:
  """Move the old bundled default to the bundled RDF V4 model once."""
  if STARPILOT_DEFAULT_MODEL_MIGRATION_FLAG.exists():
    return

  def persisted_text(key: str) -> str:
    for params_obj in (params, params_cache):
      raw_value = _read_raw_param_bytes(params_obj, key)
      if raw_value:
        return _to_text(raw_value).strip()
    return ""

  selected_model = persisted_text("Model") or persisted_text("DrivingModel")
  selected_version = persisted_text("ModelVersion") or persisted_text("DrivingModelVersion")
  selected_name = persisted_text("DrivingModelName").lower()

  is_legacy_default = selected_model.lower() in {"sc", "sc2", "rdf"}
  is_legacy_metadata = (
    not selected_version
    or selected_version.lower() in {"v11", "v15"}
  ) and (
    not selected_name
    or selected_name.startswith("south carolina")
    or selected_name.startswith("regret driven framework")
  )
  if is_legacy_default and is_legacy_metadata:
    for key, value in {
      "Model": "rdf43",
      "DrivingModel": "rdf43",
      "DrivingModelName": "Regret Driven Framework V4",
      "ModelVersion": "v15",
      "DrivingModelVersion": "v15",
    }.items():
      params.put(key, value)
      params_cache.put(key, value)
    cloudlog.warning("Migrated the bundled default model to RDF V4")

  try:
    STARPILOT_DEFAULT_MODEL_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_DEFAULT_MODEL_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_DEFAULT_MODEL_MIGRATION_FLAG}")


def migrate_starpilot_ce_model_stop_time(params: Params, params_cache: Params) -> None:
  """Move persisted users of the old 9-second stop prediction threshold to 7.7 once."""
  if STARPILOT_CE_MODEL_STOP_TIME_MIGRATION_FLAG.exists():
    return

  legacy_default_detected = False
  for params_obj in (params, params_cache):
    raw_value = _read_raw_param_bytes(params_obj, "CEModelStopTime")
    if not raw_value:
      continue

    try:
      parsed_value = float(raw_value.decode("utf-8", errors="strict").strip())
    except Exception:
      continue

    if abs(parsed_value - 9.0) < 1e-6:
      legacy_default_detected = True
      break

  if legacy_default_detected:
    params.put_float("CEModelStopTime", 7.7)
    params_cache.put_float("CEModelStopTime", 7.7)
    cloudlog.warning("Migrated CEModelStopTime from 9 seconds to 7.7 seconds")

  try:
    STARPILOT_CE_MODEL_STOP_TIME_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_CE_MODEL_STOP_TIME_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_CE_MODEL_STOP_TIME_MIGRATION_FLAG}")


def migrate_disable_humanlike_defaults(params: Params, params_cache: Params) -> None:
  if STARPILOT_HUMANLIKE_DISABLE_MIGRATION_FLAG.exists():
    return

  disabled_keys: list[str] = []

  for key in ("HumanLaneChanges",):
    if not (params.get_bool(key) or params_cache.get_bool(key)):
      continue

    params.put_bool(key, False)
    params_cache.put_bool(key, False)
    disabled_keys.append(key)

  if disabled_keys:
    cloudlog.warning(f"Applied one-time human-like toggle disable migration for {disabled_keys}")

  try:
    STARPILOT_HUMANLIKE_DISABLE_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_HUMANLIKE_DISABLE_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_HUMANLIKE_DISABLE_MIGRATION_FLAG}")


def migrate_cluster_offset_default(params: Params, params_cache: Params) -> None:
  if STARPILOT_CLUSTER_OFFSET_MIGRATION_FLAG.exists():
    return

  legacy_default_detected = False
  for params_obj in (params, params_cache):
    raw_value = _read_raw_param_bytes(params_obj, "ClusterOffset")
    if not raw_value:
      continue

    try:
      parsed_value = float(raw_value.decode("utf-8", errors="strict").strip())
    except Exception:
      continue

    if abs(parsed_value - 1.015) < 1e-6:
      legacy_default_detected = True
      break

  if legacy_default_detected:
    params.put_float("ClusterOffset", 1.0)
    params_cache.put_float("ClusterOffset", 1.0)
    cloudlog.warning("Applied one-time ClusterOffset migration from 1.015 to 1.0")

  try:
    STARPILOT_CLUSTER_OFFSET_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_CLUSTER_OFFSET_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_CLUSTER_OFFSET_MIGRATION_FLAG}")


def migrate_traffic_mode_smooth_defaults(params: Params, params_cache: Params) -> None:
  # Traffic Mode was repurposed from an aggressive city mode (jerk 50%) into a smooth
  # bumper-to-bumper mode with Relaxed-parity jerk defaults (100%). Rewrite persisted
  # legacy defaults only; user-tuned values are preserved.
  if STARPILOT_TRAFFIC_SMOOTH_MIGRATION_FLAG.exists():
    return

  migrated_keys: list[str] = []
  for key in ("TrafficJerkAcceleration", "TrafficJerkDeceleration", "TrafficJerkSpeed", "TrafficJerkSpeedDecrease"):
    # Decide off the real params store only: the boot sync mirrors real -> cache, so a
    # cache-first check could clobber a user override with a stale cached default.
    raw_value = _read_raw_param_bytes(params, key)
    if not raw_value:
      continue

    try:
      parsed_value = float(raw_value.decode("utf-8", errors="strict").strip())
    except Exception:
      continue

    if abs(parsed_value - 50.0) < 1e-6:
      params.put_float(key, 100.0)
      params_cache.put_float(key, 100.0)
      migrated_keys.append(key)

  if migrated_keys:
    cloudlog.warning(f"Applied one-time Traffic Mode smooth-defaults migration for {migrated_keys}")

  try:
    STARPILOT_TRAFFIC_SMOOTH_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_TRAFFIC_SMOOTH_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_TRAFFIC_SMOOTH_MIGRATION_FLAG}")


def migrate_traffic_follow_default(params: Params, params_cache: Params) -> None:
  # TrafficFollow's initial smooth-mode default (0.5s) proved too tight in on-road
  # testing (frequent closing-on-lead); raised to 0.75s. Rewrite persisted legacy
  # 0.5 only; user-tuned values are preserved.
  if STARPILOT_TRAFFIC_FOLLOW_MIGRATION_FLAG.exists():
    return

  raw_value = _read_raw_param_bytes(params, "TrafficFollow")
  if raw_value:
    try:
      parsed_value = float(raw_value.decode("utf-8", errors="strict").strip())
    except Exception:
      parsed_value = None

    if parsed_value is not None and abs(parsed_value - 0.5) < 1e-6:
      params.put_float("TrafficFollow", 0.75)
      params_cache.put_float("TrafficFollow", 0.75)
      cloudlog.warning("Applied one-time TrafficFollow migration from 0.5 to 0.75")

  try:
    STARPILOT_TRAFFIC_FOLLOW_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_TRAFFIC_FOLLOW_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_TRAFFIC_FOLLOW_MIGRATION_FLAG}")


def _read_raw_param_bytes(params: Params, key: str | bytes):
  try:
    path = params.get_param_path(key)
  except Exception:
    return None

  if not path or not os.path.isfile(path):
    return None

  try:
    with open(path, "rb") as f:
      return f.read()
  except Exception:
    return None


def _parse_legacy_time(raw_text: str):
  text = raw_text.strip()
  if not text:
    return None

  try:
    return datetime.datetime.fromisoformat(text)
  except ValueError:
    pass

  for fmt in ("%B %d, %Y - %I:%M%p", "%B %d, %Y - %I:%M %p"):
    try:
      return datetime.datetime.strptime(text, fmt)
    except ValueError:
      continue

  return None


def migrate_param_type_canonicalization(params: Params) -> None:
  if STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG.exists():
    return

  normalized_keys: list[str] = []

  for raw_key in params.all_keys():
    key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
    raw_value = _read_raw_param_bytes(params, raw_key)
    if not raw_value:
      continue

    try:
      text_value = raw_value.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError:
      continue

    if not text_value:
      continue

    try:
      expected_type = params.get_type(raw_key)
    except Exception:
      continue

    try:
      if expected_type == ParamKeyType.INT:
        parsed = float(text_value)
        # Canonicalize decimal/exponent forms into integer storage.
        canonical = str(int(parsed))
        if canonical != text_value:
          params.put_int(raw_key, int(parsed))
          normalized_keys.append(key)

      elif expected_type == ParamKeyType.FLOAT:
        parsed = float(text_value)
        canonical = str(parsed)
        if canonical != text_value:
          params.put_float(raw_key, parsed)
          normalized_keys.append(key)

      elif expected_type == ParamKeyType.BOOL:
        lowered = text_value.lower()
        if lowered in ("1", "true", "yes", "on"):
          if text_value != "1":
            params.put_bool(raw_key, True)
            normalized_keys.append(key)
        elif lowered in ("0", "false", "no", "off"):
          if text_value != "0":
            params.put_bool(raw_key, False)
            normalized_keys.append(key)

      elif expected_type == ParamKeyType.TIME:
        dt = _parse_legacy_time(text_value)
        if dt is not None:
          if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.UTC).replace(tzinfo=None)
          if text_value != dt.isoformat():
            params.put(raw_key, dt)
            normalized_keys.append(key)

      elif expected_type == ParamKeyType.JSON:
        parsed = json.loads(text_value)
        canonical = json.dumps(parsed, separators=(",", ":"))
        if canonical != text_value:
          params.put(raw_key, parsed)
          normalized_keys.append(key)
    except Exception:
      continue

  if normalized_keys:
    cloudlog.warning(f"Canonicalized legacy param values for {len(normalized_keys)} keys")

  try:
    STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG.write_text(f"{datetime.datetime.now(datetime.UTC).isoformat()}\n")
  except Exception:
    cloudlog.exception(f"Failed to write migration flag: {STARPILOT_PARAM_CANONICALIZATION_MIGRATION_FLAG}")


def migrate_legacy_experimental_longitudinal(params: Params, params_cache: Params) -> None:
  legacy_value = params.get("ExperimentalLongitudinalEnabled")
  if legacy_value is None:
    return

  if params.get("AlphaLongitudinalEnabled") is None:
    alpha_long_enabled = params.get_bool("ExperimentalLongitudinalEnabled")
    params.put_bool("AlphaLongitudinalEnabled", alpha_long_enabled)
    params_cache.put_bool("AlphaLongitudinalEnabled", alpha_long_enabled)
    cloudlog.warning("Migrated legacy ExperimentalLongitudinalEnabled to AlphaLongitudinalEnabled")

  params.remove("ExperimentalLongitudinalEnabled")
  params_cache.remove("ExperimentalLongitudinalEnabled")


def _msgq_file_is_readwrite_openable(path: Path) -> bool:
  fd = os.open(path, os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
  try:
    return True
  finally:
    os.close(fd)


def cleanup_inaccessible_msgq_files(shm_path: str | Path) -> int:
  """Remove stale msgq files that would crash SubSocket/PubSocket creation."""
  shm_root = Path(shm_path)
  if not shm_root.is_dir():
    return 0

  removed = 0
  for path in shm_root.rglob("msgq_*"):
    try:
      st = path.lstat()
    except OSError:
      continue

    if not stat.S_ISREG(st.st_mode):
      continue

    try:
      _msgq_file_is_readwrite_openable(path)
      continue
    except PermissionError:
      pass
    except OSError:
      continue

    try:
      path.unlink()
      removed += 1
      cloudlog.warning(f"Removed inaccessible stale msgq file: {path}")
    except OSError:
      cloudlog.exception(f"Failed to remove inaccessible stale msgq file: {path}")

  return removed


def manager_init() -> None:
  manager_init_start = time.monotonic()
  last_timing = _log_boot_timing("manager_init", "start", manager_init_start, manager_init_start)

  save_bootlog()
  last_timing = _log_boot_timing("manager_init", "save_bootlog", manager_init_start, last_timing)

  build_metadata = get_build_metadata()
  last_timing = _log_boot_timing("manager_init", "build_metadata", manager_init_start, last_timing)

  params = Params()
  cache_params_path = Paths.params_cache_root()
  migrate_legacy_starpilot_params_cache(params, Paths.legacy_params_cache_root(), cache_params_path)
  params_cache = Params(cache_params_path, return_defaults=True)
  migrate_legacy_secoc_key(params, params_cache, Paths.legacy_params_cache_root())
  last_timing = _log_boot_timing("manager_init", "params_cache", manager_init_start, last_timing)

  # Legacy FrogPilot params are unknown to the renamed schema and would be
  # deleted by clear_all() if we do not migrate them first.
  migrate_starpilot_param_renames(params, params_cache)
  last_timing = _log_boot_timing("manager_init", "param_renames", manager_init_start, last_timing)

  params.clear_all(ParamKeyFlag.CLEAR_ON_MANAGER_START)
  params.clear_all(ParamKeyFlag.CLEAR_ON_ONROAD_TRANSITION)
  params.clear_all(ParamKeyFlag.CLEAR_ON_OFFROAD_TRANSITION)
  params.clear_all(ParamKeyFlag.CLEAR_ON_IGNITION_ON)
  if build_metadata.release_channel:
    params.clear_all(ParamKeyFlag.DEVELOPMENT_ONLY)
  last_timing = _log_boot_timing("manager_init", "clear_params", manager_init_start, last_timing)

  migrate_starpilot_pc_root()
  last_timing = _log_boot_timing("manager_init", "pc_root_migration", manager_init_start, last_timing)

  if params.get_bool("RecordFrontLock"):
    params.put_bool("RecordFront", True)

  # StarPilot variables

  # Preserve StarPilot's legacy longitudinal toggle when switching branches.
  migrate_legacy_experimental_longitudinal(params, params_cache)

  # Canonicalize legacy string encodings (e.g. INT params stored as "26.000000")
  # before bulk reads below to avoid repeated cast warnings and UI-side churn.
  migrate_param_type_canonicalization(params)
  cleanup_removed_starpilot_params(params, params_cache)
  migrate_starpilot_default_parity(params, params_cache)
  migrate_starpilot_default_model(params, params_cache)
  migrate_starpilot_ce_model_stop_time(params, params_cache)
  migrate_disable_humanlike_defaults(params, params_cache)
  migrate_cluster_offset_default(params, params_cache)
  migrate_traffic_mode_smooth_defaults(params, params_cache)
  migrate_traffic_follow_default(params, params_cache)
  last_timing = _log_boot_timing("manager_init", "starpilot_migrations", manager_init_start, last_timing)

  # set unset params to their default value
  for k in params.all_keys():
    current_value = params.get(k)
    if current_value is None:
      cached_value = params_cache.get(k)
      if cached_value is not None:
        params.put(k, cached_value)
    else:
      params_cache.put(k, current_value)
  last_timing = _log_boot_timing("manager_init", "params_defaults_cache_sync", manager_init_start, last_timing)

  # Create folders needed for msgq
  try:
    os.mkdir(Paths.shm_path())
  except FileExistsError:
    pass
  except PermissionError:
    print(f"WARNING: failed to make {Paths.shm_path()}")
  last_timing = _log_boot_timing("manager_init", "shm_path", manager_init_start, last_timing)

  removed_msgq_files = cleanup_inaccessible_msgq_files(Paths.shm_path())
  if removed_msgq_files:
    cloudlog.warning(f"Removed {removed_msgq_files} inaccessible stale msgq files before process startup")
  last_timing = _log_boot_timing("manager_init", "msgq_cleanup", manager_init_start, last_timing)

  # set params
  serial = HARDWARE.get_serial()
  params.put("Version", build_metadata.openpilot.version)
  params.put("TermsVersion", terms_version)
  params.put("TrainingVersion", training_version)
  params.put("GitCommit", build_metadata.openpilot.git_commit)
  params.put("GitCommitDate", build_metadata.openpilot.git_commit_date)
  params.put("GitBranch", build_metadata.channel)
  params.put("GitRemote", build_metadata.openpilot.git_origin)
  params.put_bool("IsTestedBranch", build_metadata.tested_channel)
  params.put_bool("IsReleaseBranch", build_metadata.release_channel)
  params.put("HardwareSerial", serial)

  # Branch migration: rename legacy Bolt fingerprint persisted in CarParams.
  migrate_legacy_bolt_fingerprint(params)
  last_timing = _log_boot_timing("manager_init", "version_params", manager_init_start, last_timing)

  # set dongle id
  reg_res = register(show_spinner=True)
  if reg_res:
    dongle_id = reg_res
  else:
    raise Exception(f"Registration failed for device {serial}")
  last_timing = _log_boot_timing("manager_init", "register", manager_init_start, last_timing)
  os.environ['DONGLE_ID'] = dongle_id  # Needed for swaglog
  os.environ['GIT_ORIGIN'] = build_metadata.openpilot.git_normalized_origin # Needed for swaglog
  os.environ['GIT_BRANCH'] = build_metadata.channel # Needed for swaglog
  os.environ['GIT_COMMIT'] = build_metadata.openpilot.git_commit # Needed for swaglog

  if not build_metadata.openpilot.is_dirty:
    os.environ['CLEAN'] = '1'

  # init logging
  sentry.init(sentry.SentryProject.SELFDRIVE)
  cloudlog.bind_global(dongle_id=dongle_id,
                       version=build_metadata.openpilot.version,
                       origin=build_metadata.openpilot.git_normalized_origin,
                       branch=build_metadata.channel,
                       commit=build_metadata.openpilot.git_commit,
                       dirty=build_metadata.openpilot.is_dirty,
                       device=HARDWARE.get_device_type())
  last_timing = _log_boot_timing("manager_init", "logging_ready", manager_init_start, last_timing)

  # StarPilot variables
  install_starpilot(build_metadata, params)
  last_timing = _log_boot_timing("manager_init", "install_starpilot", manager_init_start, last_timing)
  starpilot_boot_functions(build_metadata, params)
  _log_boot_timing("manager_init", "starpilot_boot_functions", manager_init_start, last_timing)


def manager_cleanup() -> None:
  # send signals to kill all procs
  for p in managed_processes.values():
    p.stop(block=False)

  # ensure all are killed
  for p in managed_processes.values():
    p.stop(block=True)

  cloudlog.info("everything is dead")


def manager_thread() -> None:
  manager_thread_start = time.monotonic()
  last_timing = _log_boot_timing("manager_thread", "start", manager_thread_start, manager_thread_start)
  cloudlog.bind(daemon="manager")
  cloudlog.info("manager start")
  cloudlog.info({"environ": os.environ})

  params = Params()
  last_timing = _log_boot_timing("manager_thread", "params", manager_thread_start, last_timing)

  ignore: list[str] = []
  if params.get("DongleId") in (None, UNREGISTERED_DONGLE_ID):
    ignore += ["manage_athenad", "uploader"]
  if os.getenv("NOBOARD") is not None:
    ignore.append("pandad")
  ignore += [x for x in os.getenv("BLOCK", "").split(",") if len(x) > 0]
  last_timing = _log_boot_timing("manager_thread", "ignore_list", manager_thread_start, last_timing)

  sm = messaging.SubMaster(['deviceState', 'carParams', 'pandaStates'], poll='deviceState')
  pm = messaging.PubMaster(['managerState'])
  last_timing = _log_boot_timing("manager_thread", "messaging", manager_thread_start, last_timing)

  write_onroad_params(False, params)
  initial_toggles = get_starpilot_toggles(read_persisted_force_params=True)
  last_timing = _log_boot_timing("manager_thread", "initial_toggles", manager_thread_start, last_timing)
  ensure_running(managed_processes.values(), False, params=params, CP=sm['carParams'], not_run=ignore, starpilot_toggles=initial_toggles)
  last_timing = _log_boot_timing("manager_thread", "initial_ensure_running", manager_thread_start, last_timing)

  started_prev = False
  ignition_prev = False
  warned_onroad_reboot = False
  offroad_nav_destination = None
  offroad_nav_started_at = None

  # StarPilot variables
  sm = sm.extend(['starpilotPlan'])

  params_memory = Params(memory=True)

  starpilot_toggles = get_starpilot_toggles(read_persisted_force_params=True)
  last_timing = _log_boot_timing("manager_thread", "loop_toggles", manager_thread_start, last_timing)
  _log_boot_timing("manager_thread", "loop_ready", manager_thread_start, last_timing)

  while True:
    sm.update(1000)

    started = sm['deviceState'].started

    if started and not started_prev and not starpilot_toggles.force_onroad:
      params.clear_all(ParamKeyFlag.CLEAR_ON_ONROAD_TRANSITION)

      # StarPilot variables
      params_memory.clear_all(ParamKeyFlag.CLEAR_ON_ONROAD_TRANSITION)
    elif not started and started_prev:
      params.clear_all(ParamKeyFlag.CLEAR_ON_OFFROAD_TRANSITION)

      # StarPilot variables
      params_memory.clear_all(ParamKeyFlag.CLEAR_ON_OFFROAD_TRANSITION)

    offroad_nav_destination, offroad_nav_started_at = update_nav_offroad_clear_state(
      params,
      started,
      offroad_nav_destination,
      offroad_nav_started_at,
      time.monotonic(),
      offroad_transition=not started and started_prev,
    )

    ignition = any(ps.ignitionLine or ps.ignitionCan for ps in sm['pandaStates'] if ps.pandaType != log.PandaState.PandaType.unknown)
    if ignition and not ignition_prev:
      params.clear_all(ParamKeyFlag.CLEAR_ON_IGNITION_ON)

    # update onroad params, which drives pandad's safety setter thread
    if started != started_prev:
      write_onroad_params(started, params)

    started_prev = started
    ignition_prev = ignition

    ensure_running(managed_processes.values(), started, params=params, CP=sm['carParams'], not_run=ignore, starpilot_toggles=starpilot_toggles)

    running = ' '.join("{}{}\u001b[0m".format("\u001b[32m" if p.proc.is_alive() else "\u001b[31m", p.name)
                       for p in managed_processes.values() if p.proc)
    cloudlog.debug(running)

    # send managerState
    msg = messaging.new_message('managerState', valid=True)
    msg.managerState.processes = [p.get_process_state_msg() for p in managed_processes.values()]
    pm.send('managerState', msg)

    # kick AGNOS power monitoring watchdog
    try:
      if sm.all_checks(['deviceState']):
        with atomic_write("/var/tmp/power_watchdog", "w", overwrite=True) as f:
          f.write(str(time.monotonic()))
    except Exception:
      pass

    # Exit main loop when uninstall/shutdown/reboot is needed
    shutdown = False
    for param in ("DoUninstall", "DoShutdown", "DoReboot", "DoUserReboot"):
      if should_defer_reboot(param, started, ignition):
        if params.get_bool(param):
          if not warned_onroad_reboot:
            cloudlog.warning("ignoring DoReboot while started or ignition is on; deferring until offroad")
            warned_onroad_reboot = True
        continue
      if params.get_bool(param):
        shutdown = True
        warned_onroad_reboot = False
        params.put("LastManagerExitReason", f"{param} {datetime.datetime.now()}")
        cloudlog.warning(f"Shutting down manager - {param} set")

    if shutdown:
      break

    # StarPilot variables
    starpilot_toggles = get_starpilot_toggles(sm, read_persisted_force_params=True)


def main() -> None:
  manager_init()
  if os.getenv("PREPAREONLY") is not None:
    return

  # SystemExit on sigterm
  signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(1))

  try:
    manager_thread()
  except Exception:
    traceback.print_exc()
    sentry.capture_exception()
  finally:
    manager_cleanup()

  params = Params()
  if params.get_bool("DoUninstall"):
    cloudlog.warning("uninstalling")
    uninstall_starpilot()
  elif params.get_bool("DoReboot") or params.get_bool("DoUserReboot"):
    cloudlog.warning("reboot")
    HARDWARE.reboot()
  elif params.get_bool("DoShutdown"):
    cloudlog.warning("shutdown")
    HARDWARE.shutdown()


if __name__ == "__main__":
  unblock_stdout()

  try:
    main()
  except KeyboardInterrupt:
    print("got CTRL-C, exiting")
  except Exception:
    add_file_handler(cloudlog)
    cloudlog.exception("Manager failed to start")

    try:
      managed_processes['ui'].stop()
    except Exception:
      pass

    # Show last 3 lines of traceback
    error = traceback.format_exc(-3)
    error = "Manager failed to start\n\n" + error
    with TextWindow(error) as t:
      t.wait_for_exit()

    raise

  # manual exit because we are forked
  sys.exit(0)
