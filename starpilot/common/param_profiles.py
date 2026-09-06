from __future__ import annotations

import base64
import json
import math
import threading
from datetime import UTC, datetime
from pathlib import Path

from openpilot.common.params import ParamKeyFlag, ParamKeyType


PROFILE_FORMAT = "starpilot-params-profile"
PROFILE_VERSION = 1
PROFILE_MAX_BYTES = 2_000_000
DEFAULT_PROFILE_ROOT = Path("/data/toggle_backups")
PROFILE_SLOTS = {
  "a": "Profile Slot A",
  "b": "Profile Slot B",
}
PROFILE_NO_DEFAULT_KEYS = {
  "AdbEnabled",
  "AlphaLongitudinalEnabled",
  "AlwaysOnDM",
  "ExperimentalMode",
  "ExperimentalModeConfirmed",
  "IsLdwEnabled",
  "IsMetric",
  "IsRHD",
  "IsRHDOverride",
  "RecordAudio",
  "RecordFront",
  "SshEnabled",
}

_PROFILE_LOCK = threading.Lock()


class ParamProfileError(ValueError):
  pass


def _normalize_slot(slot: str) -> str:
  normalized = str(slot or "").strip().lower()
  if normalized not in PROFILE_SLOTS:
    raise ParamProfileError("Unknown settings profile slot.")
  return normalized


def _profile_path(slot: str, profile_root: Path | None = None) -> Path:
  normalized = _normalize_slot(slot)
  root = Path(profile_root) if profile_root is not None else DEFAULT_PROFILE_ROOT
  return root / f".params-profile-{normalized}.json"


def _key_text(raw_key) -> str:
  return raw_key.decode("utf-8") if isinstance(raw_key, bytes) else str(raw_key)


def eligible_profile_keys(params, *, excluded_keys: set[str] | None = None) -> set[str]:
  excluded = excluded_keys or set()
  keys = set()
  for raw_key in params.all_keys():
    key = _key_text(raw_key)
    if key in excluded:
      continue

    try:
      flags = params.get_key_flag(raw_key)
      default_value = params.get_default_value(raw_key)
    except Exception:
      continue

    if not flags & ParamKeyFlag.PERSISTENT or flags & ParamKeyFlag.DONT_LOG:
      continue
    if default_value is None and key not in PROFILE_NO_DEFAULT_KEYS:
      continue
    keys.add(key)
  return keys


def _get_current_value(params, key: str):
  try:
    return params.get(key, return_default=True)
  except TypeError:
    return params.get(key)


def _serialize_value(value_type: ParamKeyType, value):
  if value_type == ParamKeyType.BYTES:
    raw_value = value if isinstance(value, bytes) else str(value).encode("utf-8")
    return base64.b64encode(raw_value).decode("ascii")
  if value_type == ParamKeyType.TIME:
    return value.isoformat() if isinstance(value, datetime) else str(value)
  if isinstance(value, tuple):
    return list(value)
  if isinstance(value, float) and not math.isfinite(value):
    raise ValueError("non-finite numeric value")
  return value


def _deserialize_value(value_type: ParamKeyType, value):
  if value_type == ParamKeyType.BYTES:
    if not isinstance(value, str):
      raise ValueError("invalid bytes value")
    return base64.b64decode(value.encode("ascii"), validate=True)
  if value_type == ParamKeyType.TIME:
    if not isinstance(value, str):
      raise ValueError("invalid time value")
    return datetime.fromisoformat(value)
  return value


def _build_profile_payload(params, slot: str, allowed_keys: set[str] | None = None) -> dict:
  normalized = _normalize_slot(slot)
  keys = eligible_profile_keys(params) if allowed_keys is None else set(allowed_keys)
  settings = {}
  for key in sorted(keys):
    try:
      value = _get_current_value(params, key)
      if value is None:
        continue
      value_type = ParamKeyType(params.get_type(key))
      serialized_value = _serialize_value(value_type, value)
      json.dumps(serialized_value, allow_nan=False)
      settings[key] = {
        "type": int(value_type),
        "value": serialized_value,
      }
    except (TypeError, ValueError, OverflowError):
      continue

  if not settings:
    raise ParamProfileError("No compatible settings were available to save.")

  return {
    "format": PROFILE_FORMAT,
    "version": PROFILE_VERSION,
    "slot": normalized,
    "createdAt": datetime.now(UTC).isoformat(),
    "settingsCount": len(settings),
    "settings": settings,
  }


def save_profile(params, slot: str, *, allowed_keys: set[str] | None = None, profile_root: Path | None = None) -> dict:
  normalized = _normalize_slot(slot)
  payload = _build_profile_payload(params, normalized, allowed_keys)
  encoded = json.dumps(payload, indent=2, allow_nan=False).encode("utf-8")
  if len(encoded) > PROFILE_MAX_BYTES:
    raise ParamProfileError("The settings profile is too large to save.")

  path = _profile_path(normalized, profile_root)
  temp_path = path.with_suffix(".tmp")
  with _PROFILE_LOCK:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_bytes(encoded)
    temp_path.chmod(0o600)
    temp_path.replace(path)
  return profile_status(normalized, profile_root=profile_root)


def _read_profile(slot: str, profile_root: Path | None = None) -> dict:
  normalized = _normalize_slot(slot)
  path = _profile_path(normalized, profile_root)
  if not path.is_file():
    raise ParamProfileError(f"{PROFILE_SLOTS[normalized]} has not been saved yet.")
  if path.stat().st_size > PROFILE_MAX_BYTES:
    raise ParamProfileError("The saved settings profile is too large.")

  try:
    payload = json.loads(path.read_text(encoding="utf-8"))
  except (OSError, UnicodeError, json.JSONDecodeError) as error:
    raise ParamProfileError("The saved settings profile is damaged.") from error

  if not isinstance(payload, dict) or payload.get("format") != PROFILE_FORMAT:
    raise ParamProfileError("The saved settings profile is invalid.")
  version = payload.get("version")
  if not isinstance(version, int) or version > PROFILE_VERSION:
    raise ParamProfileError("The saved settings profile requires a newer StarPilot version.")
  if payload.get("slot") != normalized or not isinstance(payload.get("settings"), dict):
    raise ParamProfileError("The saved settings profile is invalid.")
  return payload


def prepare_profile(params, slot: str, *, allowed_keys: set[str] | None = None, profile_root: Path | None = None,
                    legacy_renames: dict[str, str] | None = None) -> dict:
  """Decode a slot without writes so callers can apply their validated restore policy."""
  normalized = _normalize_slot(slot)
  with _PROFILE_LOCK:
    payload = _read_profile(normalized, profile_root)
  keys = eligible_profile_keys(params) if allowed_keys is None else set(allowed_keys)
  renames = legacy_renames or {}
  settings = {}
  skipped_count = 0
  for saved_key, entry in payload["settings"].items():
    key = renames.get(saved_key, saved_key)
    if not isinstance(key, str) or key not in keys or not isinstance(entry, dict):
      skipped_count += 1
      continue
    try:
      current_type = ParamKeyType(params.get_type(key))
      saved_type = ParamKeyType(entry.get("type"))
      if saved_type != current_type or "value" not in entry:
        raise ValueError("setting type changed")
      settings[saved_key] = _deserialize_value(current_type, entry["value"])
    except (KeyError, TypeError, ValueError, OverflowError):
      skipped_count += 1

  if not settings:
    raise ParamProfileError("No compatible settings were found in this profile.")
  return {
    "slot": normalized,
    "label": PROFILE_SLOTS[normalized],
    "settings": settings,
    "skippedCount": skipped_count,
  }


def load_profile(params, slot: str, *, allowed_keys: set[str] | None = None, profile_root: Path | None = None,
                 legacy_renames: dict[str, str] | None = None) -> dict:
  result = prepare_profile(params, slot, allowed_keys=allowed_keys, profile_root=profile_root, legacy_renames=legacy_renames)
  settings = result.pop("settings")
  renames = legacy_renames or {}
  restored_count = 0
  with _PROFILE_LOCK:
    for saved_key, value in settings.items():
      try:
        params.put(renames.get(saved_key, saved_key), value)
        restored_count += 1
      except (KeyError, TypeError, ValueError, OverflowError):
        result["skippedCount"] += 1
  if restored_count == 0:
    raise ParamProfileError("No compatible settings were found in this profile.")
  return {**result, "restoredCount": restored_count}


def profile_status(slot: str, *, profile_root: Path | None = None) -> dict:
  normalized = _normalize_slot(slot)
  status = {
    "slot": normalized,
    "label": PROFILE_SLOTS[normalized],
    "saved": False,
    "createdAt": None,
    "settingsCount": 0,
  }
  path = _profile_path(normalized, profile_root)
  if not path.is_file():
    return status
  try:
    payload = _read_profile(normalized, profile_root)
  except ParamProfileError:
    return {**status, "saved": True, "invalid": True}
  return {
    **status,
    "saved": True,
    "createdAt": payload.get("createdAt"),
    "settingsCount": len(payload["settings"]),
  }


def list_profiles(*, profile_root: Path | None = None) -> list[dict]:
  return [profile_status(slot, profile_root=profile_root) for slot in PROFILE_SLOTS]
