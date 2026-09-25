"""Enroll a settings namespace in the built-in sounds once, before consumers start."""

from pathlib import Path
import json
import os
import tempfile

from openpilot.starpilot.state_migration import (
  _atomic_write, _fsync_dir, _outside_params, _params_lock, _private_dir, _read_value, canonical_json, digest,
)


def _write_selection(namespace):
  fd, temporary = tempfile.mkstemp(prefix=".sound-default-", dir=namespace.parent)
  try:
    with os.fdopen(fd, "wb") as output:
      output.write(b"starpilot")
      output.flush()
      os.fsync(output.fileno())
    os.replace(temporary, namespace / "SoundPack")
    _fsync_dir(namespace)
  finally:
    Path(temporary).unlink(missing_ok=True)


def enroll_default_sounds(params, storage) -> bool:
  namespace, storage = Path(params.get_param_path()).absolute(), Path(storage).absolute()
  _outside_params(namespace, storage)
  with _params_lock(namespace):
    identity = {"version": 1, "namespace": str(namespace), "target": str(namespace.resolve(strict=True))}
    marker_dir = storage / "sound-default-once"
    new_directory = not marker_dir.exists()
    _private_dir(marker_dir)
    if new_directory:
      _fsync_dir(storage)
    marker = marker_dir / f"{digest(str(namespace).encode())}.json"
    complete = {**identity, "state": "complete"}
    try:
      encoded = _read_value(marker)
    except FileNotFoundError:
      encoded = None
    previous = json.loads(encoded) if encoded is not None else None
    if previous is not None:
      if not isinstance(previous, dict) or type(previous.get("version")) is not int or previous["version"] != 1 or encoded != canonical_json(previous):
        raise ValueError("Invalid sound enrollment marker")
      if previous == complete:
        return False
      state = previous.get("state")
      required = {*identity, "state"} | ({"before_sha256"} if state == "pending" else set())
      if state not in ("pending", "complete") or set(previous) != required:
        raise ValueError("Invalid sound enrollment marker")
      if previous["namespace"] != identity["namespace"] or not isinstance(previous["target"], str) or not Path(previous["target"]).is_absolute():
        raise ValueError("Invalid sound enrollment identity")
      before = previous.get("before_sha256")
      if before is not None and (not isinstance(before, str) or len(before) != 64 or any(c not in "0123456789abcdef" for c in before)):
        raise ValueError("Invalid sound enrollment source")
      if any(previous[key] != value for key, value in identity.items()):
        previous = None

    selection = namespace / "SoundPack"
    try:
      raw = _read_value(selection)
    except FileNotFoundError:
      raw = None
    current = digest(raw) if raw is not None else None
    if previous is None:
      previous = {**identity, "state": "pending", "before_sha256": current}
      _atomic_write(marker, canonical_json(previous))
    elif current != previous["before_sha256"] and raw != b"starpilot":
      # A later choice takes precedence over an interrupted startup enrollment.
      _atomic_write(marker, canonical_json(complete))
      return False

    if raw != b"starpilot":
      _write_selection(namespace)
    if _read_value(selection) != b"starpilot":
      raise ValueError("Sound enrollment could not verify its selection")
    _atomic_write(marker, canonical_json(complete))
    return True
