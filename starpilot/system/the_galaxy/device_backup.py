"""Portable same-device backups. Never extract archive paths into live data."""
import base64
import copy
import hashlib
import json
import os
import io
import re
import math
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

from openpilot.common.params import ParamKeyType
from openpilot.starpilot.common.param_profiles import PROFILE_MAX_BYTES

FORMAT = "starpilot-device-backup"
VERSION = 3
# Every persistent Param is listed as include or exclude; a test enforces it.
POLICY = json.loads(Path(__file__).with_name("device_backup_keys.json").read_text())
BACKUP_KEYS = frozenset(POLICY["include"])
AUTH_FILES = {"glxyauth", "glxysession", "glxyslug", "sentry_vapid_private.pem", "sentry_push_subscriptions.json"}
# flm/progress.json is persistent tuning progression; runtime job status lives in /tmp.
ROOT_LABELS = ("flm", "themes", "profiles")
# Older archives may list these; their contents are never restored.
LEGACY_LABELS = {"models", "active_theme"}
PROFILE_DOCUMENTS = {".params-profile-a.json", ".params-profile-b.json"}
MAX_ARCHIVE_BYTES = 8 * 1024 ** 3
PARAM_GROUPS = (
  {"LongitudinalPersonalityProfiles", "CustomPersonalities"},
  {"FLMActiveOverrides", "FLMActiveProfileId", "FLMTrialBaseline", "FLMTrialApplied"},
  {"SafeMode", "SafeModeBackup"},
)
HISTORY_KEYS = frozenset({"GalaxyDashboardStats", "ModelDrivesAndScores", "StarPilotStats"})
RESTORE_MARGIN_BYTES = 256 * 1024 * 1024
# Headroom kept on the device while a backup is staged on disk before it is streamed out.
BACKUP_MARGIN_BYTES = 128 * 1024 * 1024
PYTHON_TYPES = {
  ParamKeyType.STRING: (str,), ParamKeyType.BOOL: (bool,), ParamKeyType.INT: (int,), ParamKeyType.FLOAT: (float,),
  ParamKeyType.TIME: (datetime,), ParamKeyType.JSON: (dict, list), ParamKeyType.BYTES: (bytes,),
}


def eligible_keys(keys):
  return set(keys) & BACKUP_KEYS


def allowed_file(name, keys):
  parts = PurePosixPath(name).parts
  if any(part in AUTH_FILES for part in parts):
    return False
  if parts[0] != "profiles":
    return True
  # Profile slot documents, or raw Params files inside toggle backup folders.
  if len(parts) == 2:
    return parts[1] in PROFILE_DOCUMENTS
  return len(parts) == 3 and not parts[1].endswith("_in_progress") and parts[2] in keys


def sanitized_profile(content, keys):
  payload = json.loads(content)
  if payload.get("format") != "starpilot-params-profile" or not isinstance(payload.get("settings"), dict):
    raise ValueError("Invalid saved settings profile")
  payload = {key: value for key, value in payload.items() if key in {"format", "version", "slot", "createdAt", "settings"}}
  payload["settings"] = {key: value for key, value in payload["settings"].items() if key in keys}
  payload["settingsCount"] = len(payload["settings"])
  return json.dumps(payload).encode("utf-8")


def sanitized_profile_file(path, keys):
  if path.stat().st_size > PROFILE_MAX_BYTES:
    raise ValueError("Saved settings profile exceeds its supported size limit")
  return sanitized_profile(path.read_bytes(), keys)


def saved_models(catalog):
  return [{"key": entry["value"], "version": entry.get("version", ""),
           "standard": bool(entry.get("installed") and not entry.get("builtin")),
           "lab": bool(entry.get("modelLabArtifactInstalled"))}
          for entry in catalog if (entry.get("installed") and not entry.get("builtin")) or entry.get("modelLabArtifactInstalled")]


def validate_models(models):
  if not isinstance(models, list) or len(models) > 2000:
    raise ValueError("Invalid saved model inventory")
  result = []
  seen = set()
  for model in models:
    key = model.get("key") if isinstance(model, dict) else None
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", key):
      raise ValueError("Invalid saved model identifier")
    if key in seen or type(model.get("standard")) is not bool or type(model.get("lab")) is not bool:
      raise ValueError("Invalid saved model inventory")
    seen.add(key)
    result.append({"key": key, "version": str(model.get("version", ""))[:200],
                   "standard": model["standard"], "lab": model["lab"]})
  return result


def read_param(params, key):
  # Native Params.get() returns typed values, not the serialized bytes in the store.
  if hasattr(params, "get_param_path"):
    try:
      return Path(params.get_param_path(key)).read_bytes()
    except FileNotFoundError:
      return None
  return params.get(key)


def decode_param(params, key, raw):
  """Native deserialization that rejects loose booleans and non-finite floats; None if incompatible."""
  if not hasattr(params, "cpp2python"):
    return raw
  try:
    kind = ParamKeyType(params.get_type(key))
    if kind == ParamKeyType.BOOL and raw not in (b"0", b"1"):
      return None
    value = params.cpp2python(key, raw)
    if type(value) not in PYTHON_TYPES[kind]:
      return None
    if kind == ParamKeyType.FLOAT and not math.isfinite(value):
      return None
    return value
  except (KeyError, TypeError, ValueError, OverflowError, UnicodeError):
    return None


class RestoreError(OSError):
  pass


def verify_param(params, key, value):
  """Confirm a write reached the underlying Params store."""
  if hasattr(params, "_put_cast"):
    expected = params._put_cast(key, value) if value is not None else None
    actual = read_param(params, key)
  else:
    expected = value
    actual = params.get(key)
  if type(actual) is not type(expected) or actual != expected:
    raise RestoreError(f"Setting write could not be verified: {key}")


def write_param(params, key, raw):
  if raw is None:
    params.remove(key)
    verify_param(params, key, None)
    return
  value = decode_param(params, key, raw)
  if value is None:
    raise ValueError(f"Cannot roll back incompatible setting: {key}")
  params.put(key, value)
  verify_param(params, key, value)


def merge_history(saved, current):
  """Union history records by identity, with current values winning conflicts."""
  if isinstance(saved, dict) and isinstance(current, dict):
    result = copy.deepcopy(saved)
    for key, value in current.items():
      result[key] = merge_history(result[key], value) if key in result else copy.deepcopy(value)
    return result
  if isinstance(saved, list) and isinstance(current, list):
    return copy.deepcopy(current + [value for value in saved if value not in current])
  return copy.deepcopy(current)


def _nonnegative_number(value):
  try:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0
  except OverflowError:
    return False


def _merge_cumulative_history(saved, current):
  if isinstance(saved, dict) and isinstance(current, dict):
    return {
      key: _merge_cumulative_history(saved[key], current[key]) if key in saved and key in current
      else copy.deepcopy(current[key] if key in current else saved[key])
      for key in saved.keys() | current.keys()
    }
  if _nonnegative_number(saved) and _nonnegative_number(current):
    return max(saved, current)
  return copy.deepcopy(current)


def merge_history_param(key, saved, current):
  if not isinstance(saved, dict):
    return saved
  current = current if isinstance(current, dict) else {}
  if key == "StarPilotStats":
    merged = _merge_cumulative_history(saved, current)
    if "Month" in current:
      merged["Month"] = current["Month"]
      if saved.get("Month") != current["Month"]:
        merged["CurrentMonthsMeters"] = current.get("CurrentMonthsMeters", 0)
    return merged
  merged = merge_history(saved, current)
  if key == "GalaxyDashboardStats":
    saved_routes = saved.get("routes", {}) if isinstance(saved.get("routes", {}), dict) else {}
    current_routes = current.get("routes", {}) if isinstance(current.get("routes", {}), dict) else {}
    merged["routes"] = {**copy.deepcopy(saved_routes), **copy.deepcopy(current_routes)}
  return merged


def rollback(params, previous, files, check_parked=lambda: None):
  """Restore saved Params and (target, copy, existed) files; returns what failed."""
  failures = []
  for key, value in previous.items():
    check_parked()
    try:
      write_param(params, key, value)
    except Exception:
      failures.append(key)
  for target, old, existed in reversed(files):
    check_parked()
    try:
      if existed:
        shutil.copy2(old, target)
      else:
        target.unlink(missing_ok=True)
    except OSError:
      failures.append(str(target))
  return failures


def pending_recoveries(workdir):
  return sorted(Path(workdir).glob("restore-*/recovery.json"))


def discard_recoveries(workdir):
  """Abandon interrupted-restore records at the user's explicit request."""
  removed = []
  for record in pending_recoveries(workdir):
    shutil.rmtree(record.parent, ignore_errors=True)
    removed.append(record.parent)
  return removed


def cleanup_stages(workdir):
  """Remove staging directories left by a crash before any live change was made; keeps recovery records."""
  workdir = Path(workdir)
  if not workdir.is_dir():
    return
  for stage in workdir.glob("restore-*"):
    if stage.is_dir() and not (stage / "recovery.json").exists():
      shutil.rmtree(stage, ignore_errors=True)


def cleanup_downloads(workdir):
  """Remove prepared backup archives that were never fetched; a download is short-lived."""
  downloads = Path(workdir) / "downloads"
  if not downloads.is_dir():
    return
  for path in downloads.glob("starpilot-device-*.zip"):
    if path.is_file():
      path.unlink(missing_ok=True)


def available_restore_bytes(workdir):
  return shutil.disk_usage(workdir).free - RESTORE_MARGIN_BYTES


def restore_upload_limit(workdir):
  # Upload, staged copy, and rollback copy can coexist, so only a third of the space is offered.
  return min(MAX_ARCHIVE_BYTES, max(0, available_restore_bytes(workdir) // 3))


def _fsync_dir(path):
  """Best-effort directory fsync so a rename survives a power cut."""
  try:
    descriptor = os.open(path, os.O_RDONLY)
  except OSError:
    return
  try:
    os.fsync(descriptor)
  except OSError:
    pass
  finally:
    os.close(descriptor)


def recover_restore(record, params, check_parked=lambda: None):
  """Roll back an interrupted restore from its record. Progress is unknown, so every planned file is restored."""
  record = Path(record)
  data = json.loads(record.read_text())
  previous = {key: base64.b64decode(value) if value is not None else None for key, value in data["params"].items()}
  files = [(Path(item["target"]), Path(item["copy"]), item["existed"]) for item in data["files"]]
  failures = rollback(params, previous, files, check_parked)
  if failures:
    raise RuntimeError(f"Could not roll back {', '.join(failures)}. Recovery copies kept at {record.parent}.")
  shutil.rmtree(record.parent)
  _fsync_dir(record.parent.parent)


@contextmanager
def restore_workspace(workdir):
  stage = Path(tempfile.mkdtemp(prefix="restore-", dir=workdir))
  try:
    yield stage
  finally:
    # A remaining recovery record means rollback is incomplete; keep its copies.
    if not (stage / "recovery.json").exists():
      shutil.rmtree(stage)


def backup_files(root):
  """Regular files under root; symlinks (such as linked theme assets) are skipped."""
  root = Path(root)
  if root.is_symlink() or not root.is_dir():
    return
  for directory, dirnames, filenames in os.walk(root):
    dirnames[:] = sorted(name for name in dirnames if not os.path.islink(os.path.join(directory, name)))
    for filename in sorted(filenames):
      path = Path(directory, filename)
      if path.is_file() and not path.is_symlink():
        yield path


def included_backup_files(roots, keys):
  """Yield (name, path) for every file create_backup would archive, in the same order and with the same filter."""
  keys = eligible_keys(keys)
  for label, root in roots.items():
    if label in LEGACY_LABELS:
      continue
    if label not in ROOT_LABELS:
      raise ValueError(f"Unknown backup root: {label}")
    root = Path(root)
    for path in backup_files(root):
      name = f"{label}/{path.relative_to(root).as_posix()}"
      if allowed_file(name, keys):
        yield name, path


def estimate_backup_bytes(roots, keys):
  """Conservative pre-flight archive size (stored, so roughly the source size) for the disk-space check."""
  total = 0
  for _name, path in included_backup_files(roots, keys):
    try:
      total += path.stat().st_size
    except OSError:
      continue
  return total


def _gigabytes(value):
  return f"{value / 1024 ** 3:.1f} GB"


def check_backup_space(workdir, needed):
  """Refuse a backup that cannot be staged on disk, pointing the user at space they can reclaim."""
  if needed > MAX_ARCHIVE_BYTES:
    raise ValueError(f"This backup is about {_gigabytes(needed)}, over the 8 GiB limit. "
                     + "Remove large theme assets or FLM workspace files and try again.")
  free = shutil.disk_usage(workdir).free
  if free < needed + BACKUP_MARGIN_BYTES:
    raise ValueError(f"Not enough free space to build the backup: it needs about {_gigabytes(needed)} but only "
                     + f"{_gigabytes(free)} is free. Delete driving routes or recordings from the Recordings page, "
                     + "or use Danger Zone \u2192 Delete All Driving Routes, then try again.")


def create_backup(destination, roots, params, keys, models=()):
  keys = eligible_keys(keys)
  manifest = {"format": FORMAT, "version": VERSION, "params": {}, "files": {}, "models": validate_models(list(models)),
              "keys": sorted(keys), "types": {key: int(params.get_type(key)) for key in keys} if hasattr(params, "get_type") else {}}
  for key in sorted(keys):
    value = read_param(params, key)
    if value is not None:
      manifest["params"][key] = base64.b64encode(value).decode("ascii")
  with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
    for name, path in included_backup_files(roots, keys):
      profile = PurePosixPath(name).parts[0] == "profiles" and len(PurePosixPath(name).parts) == 2
      source_file = io.BytesIO(sanitized_profile_file(path, keys)) if profile else path.open("rb")
      digest = hashlib.sha256()
      size = 0
      with source_file as source, archive.open(name, "w", force_zip64=True) as output:
        while chunk := source.read(1024 * 1024):
          output.write(chunk)
          digest.update(chunk)
          size += len(chunk)
          if archive.fp.tell() > MAX_ARCHIVE_BYTES:
            raise ValueError("Full backups are limited to 8 GiB; reduce stored reports or theme assets and try again.")
      manifest["files"][name] = {"size": size, "sha256": digest.hexdigest()}
    encoded = json.dumps(manifest)
    if len(encoded.encode()) > 16 * 1024 * 1024:
      raise ValueError("Backup manifest is too large")
    archive.writestr("manifest.json", encoded)
  archive_size = destination.tell() if hasattr(destination, "tell") else Path(destination).stat().st_size
  if archive_size > MAX_ARCHIVE_BYTES:
    raise ValueError("Full backups are limited to 8 GiB; reduce stored reports or theme assets and try again.")


def restore_backup(source, roots, params, keys, workdir, check_parked, models_out=None, validate=None):
  """Validate everything, then apply with rollback. Incompatible or rejected settings keep current values.

  Returns (restored setting count, restored file count, skipped setting names).
  """
  keys = eligible_keys(keys)
  with restore_workspace(workdir) as stage:
    with zipfile.ZipFile(source) as archive:
      entries = archive.infolist()
      names = [entry.filename for entry in entries]
      if "manifest.json" not in names:
        raise ValueError("This file is not a full StarPilot backup.")
      if len(names) != len(set(names)) or archive.getinfo("manifest.json").file_size > 16 * 1024 * 1024:
        raise ValueError("Invalid backup manifest")
      manifest = json.loads(archive.read("manifest.json"))
      if not isinstance(manifest, dict) or manifest.get("format") != FORMAT or manifest.get("version") not in (1, 2, VERSION):
        raise ValueError("Unsupported device backup")
      models = validate_models(manifest.get("models", []))
      files = manifest.get("files")
      raw_params = manifest.get("params")
      types = manifest.get("types", {})
      if not isinstance(files, dict) or not isinstance(raw_params, dict) or not isinstance(types, dict):
        raise ValueError("Invalid backup contents")
      if set(names) != set(files) | {"manifest.json"}:
        raise ValueError("Backup file list does not match manifest")
      # The recorded scope separates cleared settings from ones added after the backup.
      scope = manifest.get("keys", list(raw_params))
      if not isinstance(scope, list) or any(not isinstance(key, str) for key in scope) or not set(raw_params) <= set(scope):
        raise ValueError("Invalid backup setting list")
      restore_keys = keys & set(scope)
      values = {}
      for key, raw in raw_params.items():
        if key not in restore_keys:
          continue
        try:
          if key in types and hasattr(params, "get_type") and types[key] != int(params.get_type(key)):
            continue
          value = decode_param(params, key, base64.b64decode(raw, validate=True))
          if value is not None:
            values[key] = value
        except (TypeError, ValueError):
          pass
      skipped = (set(raw_params) & restore_keys) - set(values)
      # Keep coupled settings together when one is skipped.
      for group in PARAM_GROUPS:
        if group & skipped:
          skipped.update(group & restore_keys)
      restore_keys -= skipped
      values = {key: value for key, value in values.items() if key in restore_keys}
      if validate is not None:
        validated = validate(dict(values), restore_keys)
        skipped.update(set(values) - set(validated))
        values = validated
        restore_keys.update(set(validated) & keys)
      for group in PARAM_GROUPS:
        if group & skipped:
          skipped.update(group & restore_keys)
      restore_keys -= skipped
      values = {key: value for key, value in values.items() if key in restore_keys}
      # History from the device and archive is combined so an older backup cannot erase newer records.
      restore_keys -= HISTORY_KEYS - set(values)
      for key in HISTORY_KEYS & set(values):
        values[key] = merge_history_param(key, values[key], params.get(key))

      # Budget space for staged files, rollback copies, and the largest atomic replacement.
      selected = []
      for name, metadata in files.items():
        relative = PurePosixPath(name)
        if (relative.is_absolute() or relative.as_posix() != name or ".." in relative.parts or len(relative.parts) < 2
            or relative.parts[0] not in set(roots) | LEGACY_LABELS):
          raise ValueError("Invalid backup file path")
        if relative.parts[0] in LEGACY_LABELS or not allowed_file(name, keys):
          continue
        entry = archive.getinfo(name)
        if not isinstance(metadata, dict) or metadata.get("size") != entry.file_size or entry.is_dir():
          raise ValueError("Invalid backup contents")
        root = Path(roots[relative.parts[0]])
        target = root.joinpath(*relative.parts[1:])
        if any(root.joinpath(*relative.parts[1:index]).is_symlink() for index in range(1, len(relative.parts) + 1)):
          raise ValueError("Restore destination contains a symbolic link")
        if target.exists() and not target.is_file():
          raise ValueError("Restore destination is not a regular file")
        selected.append((name, metadata, target))
      sizes = [metadata["size"] for _, metadata, _ in selected]
      rollback_size = sum(target.stat().st_size for _, _, target in selected if target.exists())
      needed = sum(sizes) + rollback_size + max(sizes, default=0) + RESTORE_MARGIN_BYTES
      if needed > shutil.disk_usage(workdir).free:
        raise ValueError("Not enough free space to safely restore this backup")
      targets = []
      for name, metadata, target in selected:
        check_parked()
        staged = stage / "new" / name
        staged.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with archive.open(name) as input_file, staged.open("wb") as output:
          while chunk := input_file.read(1024 * 1024):
            digest.update(chunk)
            output.write(chunk)
        if staged.stat().st_size != metadata["size"] or digest.hexdigest() != metadata.get("sha256"):
          raise ValueError("Backup checksum failed")
        if PurePosixPath(name).parts[0] == "profiles" and len(PurePosixPath(name).parts) == 2:
          staged.write_bytes(sanitized_profile_file(staged, keys))
        targets.append((name, staged, target))

    check_parked()
    previous = {key: read_param(params, key) for key in restore_keys}
    plans = []
    for name, staged, target in targets:
      check_parked()
      old = stage / "old" / name
      old.parent.mkdir(parents=True, exist_ok=True)
      existed = target.exists()
      if existed:
        shutil.copy2(target, old)
        with old.open("rb") as snapshot:
          os.fsync(snapshot.fileno())
        _fsync_dir(old.parent)
      plans.append((staged, target, old, existed))
    recovery = stage / "recovery.json"
    # Persist the recovery record before any live change.
    with recovery.open("w") as output:
      json.dump({
        "params": {key: base64.b64encode(value).decode() if value is not None else None for key, value in previous.items()},
        "files": [{"target": str(target), "copy": str(old), "existed": existed} for _, target, old, existed in plans],
      }, output)
      output.flush()
      os.fsync(output.fileno())
    _fsync_dir(recovery.parent)
    applied = []
    try:
      for staged, target, old, existed in plans:
        check_parked()
        target.parent.mkdir(parents=True, exist_ok=True)
        applied.append((target, old, existed))
        descriptor, pending_name = tempfile.mkstemp(prefix=".device-restore-", dir=target.parent)
        pending = Path(pending_name)
        try:
          with os.fdopen(descriptor, "wb") as output, staged.open("rb") as source_file:
            shutil.copyfileobj(source_file, output)
            output.flush()
            os.fsync(output.fileno())
          os.replace(pending, target)
          _fsync_dir(target.parent)
        finally:
          pending.unlink(missing_ok=True)
      check_parked()
      # Write the profile document before its enabling master switch.
      for key in sorted(restore_keys, key=lambda key: (key == "CustomPersonalities", key)):
        if key in values:
          params.put(key, values[key])
          verify_param(params, key, values[key])
        else:
          params.remove(key)
          verify_param(params, key, None)
    except Exception as error:
      failures = rollback(params, previous, applied)
      if failures:
        raise RuntimeError(
          f"Restore failed and rollback was incomplete. Recovery copies kept at {stage}. "
          + "Galaxy retries the rollback when it next starts while parked; free storage first if it is full."
        ) from error
      recovery.unlink()
      _fsync_dir(recovery.parent)
      raise
    recovery.unlink()
    _fsync_dir(recovery.parent)
    if models_out is not None:
      models_out.extend(models)
    return len(values), len(targets), sorted(skipped)
