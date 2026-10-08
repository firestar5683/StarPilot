"""Allowlisted conditional-mode document edits and guarded Params commits.

Presentation callers bind exact saved bytes, units and parked vehicle context.
The ordinary edit replaces one document; manual persistence first clears the
selected remembered code under the planner's lease and Params lock.
"""

from dataclasses import dataclass, replace
from collections.abc import Callable
import fcntl
import math
import os
from pathlib import Path
import tempfile

from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.manual_saved import (
  KEY as MANUAL_KEY, SavedCodes, encode as encode_manual,
  manual_lock_path, read_codes,
)
from openpilot.starpilot.conditional_mode.preferences import (
  CCMOptions, CEMOptions, MAX_DOCUMENT_BYTES, MPH_TO_MPS,
  PreferenceError, SavedPreferences, decode_preferences, encode_preferences,
)
from openpilot.starpilot.saved_source import read_saved


DOCUMENT_KEY = "ConditionalModeConfig"
PREFIX = "conditional:"
RESET = PREFIX + "reset"
MANUAL_RESET = PREFIX + "manual_reset"
MODE = PREFIX + "mode"
SPEED_FIELDS = frozenset(("speed_mps", "speed_with_lead_mps", "signal_speed_mps", "set_speed_margin_mps"))
BOOLEAN_FIELDS = {
  "cem": frozenset(("open_road", "curves", "curves_with_lead", "lead", "slower_lead", "stopped_lead",
                       "stop_lights", "signal_lane_detection")),
  "ccm": frozenset(("lead", "launch_assist")),
}
NUMBER_FIELDS = {
  "cem": frozenset(("speed_mps", "speed_with_lead_mps", "signal_speed_mps", "model_stop_s", "signal_lane_width_m")),
  "ccm": frozenset(("speed_mps", "speed_with_lead_mps", "set_speed_margin_mps")),
}


def field_limit(section: str, field: str, metric: bool) -> float:
  if field == "model_stop_s":
    return 9.0
  if field == "signal_lane_width_m":
    return 15.0
  if field == "set_speed_margin_mps":
    return 30.0 if metric else 15.0
  if section in ("cem", "ccm") and field in SPEED_FIELDS:
    return 150.0 if metric else 99.0
  raise PreferenceError("unknown conditional numeric option")


def display_number(field: str, value: float, metric: bool) -> float:
  if field == "signal_lane_width_m":
    return value if metric else value / 0.3048
  if field in SPEED_FIELDS:
    return value * (3.6 if metric else 1 / MPH_TO_MPS)
  return value


def stored_number(field: str, value: float, metric: bool) -> float:
  if field == "signal_lane_width_m":
    return value if metric else value * 0.3048
  if field in SPEED_FIELDS:
    return value / 3.6 if metric else value * MPH_TO_MPS
  return value


def edit(preferences: SavedPreferences, key: str, value: str, *, metric: bool) -> bytes:
  """Return a validated whole document, rejecting hidden/unknown option edits."""
  if key == MODE:
    modes = {"Stock": ModeChoice.STOCK, "Conditional Experimental": ModeChoice.CEM,
             "Conditional Chill": ModeChoice.CCM}
    if value not in modes:
      raise PreferenceError("unknown conditional mode")
    updated = replace(preferences, mode=modes[value])
  else:
    parts = key.split(":")
    if len(parts) != 3 or parts[0] != "conditional" or parts[1] not in ("cem", "ccm"):
      raise PreferenceError("unknown conditional option")
    section, field = parts[1:]
    option = preferences.cem if section == "cem" else preferences.ccm
    if field in BOOLEAN_FIELDS[section]:
      if value not in ("On", "Off"):
        raise PreferenceError("invalid conditional boolean")
      changed = replace(option, **{field: value == "On"})
    elif field in NUMBER_FIELDS[section]:
      try:
        number = float(value)
      except (ValueError, OverflowError) as exc:
        raise PreferenceError("invalid conditional number") from exc
      # A unit change may put a valid SI value above the edit cap; allow only steps down.
      maximum = max(field_limit(section, field, metric), display_number(field, getattr(option, field), metric))
      if not math.isfinite(number) or not 0.0 <= number <= maximum:
        raise PreferenceError("conditional number outside display range")
      changed = replace(option, **{field: stored_number(field, number, metric)})
    else:
      raise PreferenceError("unsupported conditional option")
    updated = replace(preferences, **{section: changed})
  return encode_preferences(updated)


def stock_document() -> bytes:
  return encode_preferences(SavedPreferences(mode=ModeChoice.STOCK, cem=CEMOptions(), ccm=CCMOptions()))


@dataclass(frozen=True)
class CommitResult:
  committed: bool
  verified: bool
  manual_cleared: bool = False
  rollback_failed: bool = False


def commit(params, raw: bytes, expected: bytes | None, expected_units: bytes | None,
           authorized: Callable[[], bool]) -> CommitResult:
  """One atomic Params document write after an exact, locked source check.

  Uses the same Params-root flock as Params.put and the Curve editor. The
  caller checks the full vehicle context in ``authorized`` both before and
  within this lock. Readers never create or repair saved files.
  """
  try:
    if encode_preferences(decode_preferences(raw)) != raw:
      return CommitResult(False, False)
  except PreferenceError:
    return CommitResult(False, False)
  if len(raw) > MAX_DOCUMENT_BYTES or not authorized():
    return CommitResult(False, False)
  document, readable = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
  units, unit_readable = read_saved(params, "IsMetric", 8)
  if not readable or not unit_readable or document != expected or units != expected_units:
    return CommitResult(False, False)
  temporary = None
  lock_fd = None
  committed = False
  try:
    destination = Path(params.get_param_path(DOCUMENT_KEY))
    root = destination.parent.parent
    with tempfile.NamedTemporaryFile(prefix=".tmp_conditional_", dir=root, delete=False) as staging:
      temporary = staging.name
      staging.write(raw)
      staging.flush()
      os.fsync(staging.fileno())
    lock_fd = os.open(root / ".lock", os.O_CREAT | os.O_RDONLY, 0o775)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not authorized():
      return CommitResult(False, False)
    document, readable = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    units, unit_readable = read_saved(params, "IsMetric", 8)
    if not readable or not unit_readable or document != expected or units != expected_units:
      return CommitResult(False, False)
    if not authorized():
      return CommitResult(False, False)
    document, readable = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    units, unit_readable = read_saved(params, "IsMetric", 8)
    if not readable or not unit_readable or document != expected or units != expected_units:
      return CommitResult(False, False)
    os.replace(temporary, destination)
    temporary = None
    committed = True
    directory_fd = os.open(destination.parent, os.O_RDONLY)
    try:
      os.fsync(directory_fd)
    finally:
      os.close(directory_fd)
    observed, readable = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    return CommitResult(True, readable and observed == raw)
  except (OSError, ValueError, TypeError):
    return CommitResult(committed, False)
  finally:
    if lock_fd is not None:
      os.close(lock_fd)
    if temporary is not None:
      try:
        os.unlink(temporary)
      except OSError:
        pass



def commit_mode(params, raw: bytes, baseline: bytes, *, expected: bytes | None, expected_baseline: bytes | None,
                expected_units: bytes | None, expected_safe: bytes | None, authorized: Callable[[], bool]) -> CommitResult:
  """Commit the selector's document and baseline together for locked readers.

  Params.put and ordinary document commits use this same lock. If either
  replacement fails, restore both original sources before releasing it.
  """
  if baseline not in (b"0", b"1") or expected_baseline not in (None, b"0", b"1") or expected_safe not in (None, b"0", b"1"):
    return CommitResult(False, False)
  try:
    if encode_preferences(decode_preferences(raw)) != raw or not authorized():
      return CommitResult(False, False)
  except PreferenceError:
    return CommitResult(False, False)

  def sources_match() -> bool:
    return all(read_saved(params, key, limit) == (source, True) for key, limit, source in (
      (DOCUMENT_KEY, MAX_DOCUMENT_BYTES, expected), ("ExperimentalMode", 8, expected_baseline),
      ("IsMetric", 8, expected_units), ("SafeMode", 8, expected_safe)))

  temporary: list[str] = []
  lock_fd = None
  replaced = False
  try:
    destinations = (Path(params.get_param_path(DOCUMENT_KEY)), Path(params.get_param_path("ExperimentalMode")))
    root = destinations[0].parent.parent

    def stage(value: bytes | None) -> str | None:
      if value is None:
        return None
      with tempfile.NamedTemporaryFile(prefix=".tmp_conditional_mode_", dir=root, delete=False) as source:
        temporary.append(source.name)
        source.write(value)
        source.flush()
        os.fsync(source.fileno())
        return source.name

    staged = (stage(raw), stage(baseline))
    rollback = (stage(expected), stage(expected_baseline))
    lock_fd = os.open(root / ".lock", os.O_CREAT | os.O_RDONLY, 0o775)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not authorized() or not sources_match():
      return CommitResult(False, False)
    directory_fd = os.open(destinations[0].parent, os.O_RDONLY)
    try:
      try:
        for source, destination in zip(staged, destinations, strict=True):
          assert source is not None
          os.replace(source, destination)
          replaced = True
        os.fsync(directory_fd)
        if not authorized() or read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES) != (raw, True) or \
           read_saved(params, "ExperimentalMode", 8) != (baseline, True):
          raise OSError("Mode commit verification failed")
        return CommitResult(True, True)
      except (OSError, ValueError, TypeError):
        if not replaced:
          return CommitResult(False, False)
        restored = True
        for source, destination in zip(rollback, destinations, strict=True):
          try:
            if source is None:
              destination.unlink(missing_ok=True)
            else:
              os.replace(source, destination)
          except OSError:
            restored = False
        try:
          os.fsync(directory_fd)
          restored = restored and sources_match()
        except OSError:
          restored = False
        return CommitResult(False, False, rollback_failed=not restored)
    finally:
      os.close(directory_fd)
  except (OSError, ValueError, TypeError):
    return CommitResult(False, False)
  finally:
    if lock_fd is not None:
      os.close(lock_fd)
    for source in temporary:
      try:
        os.unlink(source)
      except OSError:
        pass


def commit_manual(params, *, expected_config: bytes | None, expected_units: bytes | None,
                  expected_safe: bytes | None, expected_manual: bytes | None,
                  authorized: Callable[[], bool], choice: ModeChoice | None,
                  config_raw: bytes | None) -> CommitResult:
  """Clear selected saved manual code before a persist toggle, or reset corrupt codes.

  The drive writer owns the manual lease for its session. Taking that lease
  before Params `.lock` makes a parked edit exclude a live writer; both sides
  then compare exact config, manual, and SafeMode bytes. A failed second write
  may leave a cleared manual code, which is safe and explicitly reported.
  """
  if (choice is not None and (type(choice) is not ModeChoice or choice not in (ModeChoice.CEM, ModeChoice.CCM))) or \
     (choice is None) == (config_raw is not None) or not authorized():
    return CommitResult(False, False)
  if config_raw is not None:
    try:
      if encode_preferences(decode_preferences(config_raw)) != config_raw:
        return CommitResult(False, False)
    except PreferenceError:
      return CommitResult(False, False)
  initial = read_codes(params)
  if initial.raw != expected_manual or initial.status not in (("valid", "absent") if choice is not None else ("invalid",)):
    return CommitResult(False, False)
  if choice is None:
    next_manual = encode_manual(SavedCodes())
  else:
    assert initial.codes is not None
    next_manual = encode_manual(initial.codes.with_code(choice, 0)) if initial.codes.code(choice) else None

  def sources_match(manual_raw: bytes | None) -> bool:
    document, document_ok = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    units, units_ok = read_saved(params, "IsMetric", 8)
    safe, safe_ok = read_saved(params, "SafeMode", 8)
    manual = read_codes(params)
    return bool(document_ok and units_ok and safe_ok and document == expected_config and
                units == expected_units and safe == expected_safe and safe in (None, b"0", b"1") and
                manual.raw == manual_raw and manual.status == ("invalid" if choice is None else initial.status))

  if not sources_match(expected_manual):
    return CommitResult(False, False)
  manual_staging = config_staging = None
  lease_fd = lock_fd = None
  manual_cleared = config_committed = False
  try:
    config_destination = Path(params.get_param_path(DOCUMENT_KEY))
    root = config_destination.parent.parent
    manual_destination = Path(params.get_param_path(MANUAL_KEY))
    if next_manual is not None:
      with tempfile.NamedTemporaryFile(prefix=".tmp_conditional_manual_ui_", dir=root, delete=False) as staged:
        manual_staging = staged.name
        staged.write(next_manual)
        staged.flush()
        os.fsync(staged.fileno())
    if config_raw is not None:
      with tempfile.NamedTemporaryFile(prefix=".tmp_conditional_ui_", dir=root, delete=False) as staged:
        config_staging = staged.name
        staged.write(config_raw)
        staged.flush()
        os.fsync(staged.fileno())
    lease_fd = os.open(manual_lock_path(params), os.O_CREAT | os.O_RDONLY, 0o600)
    fcntl.flock(lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock_fd = os.open(root / ".lock", os.O_CREAT | os.O_RDONLY, 0o775)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not authorized() or not sources_match(expected_manual):
      return CommitResult(False, False)
    if next_manual is not None:
      assert manual_staging is not None
      os.replace(manual_staging, manual_destination)
      manual_staging = None
      manual_cleared = True
      directory_fd = os.open(manual_destination.parent, os.O_RDONLY)
      try:
        os.fsync(directory_fd)
      finally:
        os.close(directory_fd)
      observed = read_codes(params)
      if observed.status != "valid" or observed.raw != next_manual:
        return CommitResult(False, False, True)
    if config_raw is None:
      return CommitResult(manual_cleared, manual_cleared, manual_cleared)
    # Keep the clear if a later write fails so the old override cannot return.
    if not authorized():
      return CommitResult(False, False, manual_cleared)
    document, document_ok = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    units, units_ok = read_saved(params, "IsMetric", 8)
    safe, safe_ok = read_saved(params, "SafeMode", 8)
    manual = read_codes(params)
    if (not document_ok or not units_ok or not safe_ok or document != expected_config or units != expected_units or
        safe != expected_safe or manual.raw != (next_manual if manual_cleared else expected_manual) or
        manual.status not in ("valid", "absent")):
      return CommitResult(False, False, manual_cleared)
    if not authorized():
      return CommitResult(False, False, manual_cleared)
    document, document_ok = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    units, units_ok = read_saved(params, "IsMetric", 8)
    safe, safe_ok = read_saved(params, "SafeMode", 8)
    manual = read_codes(params)
    if (not document_ok or not units_ok or not safe_ok or document != expected_config or units != expected_units or
        safe != expected_safe or manual.raw != (next_manual if manual_cleared else expected_manual) or
        manual.status not in ("valid", "absent")):
      return CommitResult(False, False, manual_cleared)
    assert config_staging is not None
    os.replace(config_staging, config_destination)
    config_staging = None
    config_committed = True
    directory_fd = os.open(config_destination.parent, os.O_RDONLY)
    try:
      os.fsync(directory_fd)
    finally:
      os.close(directory_fd)
    written, readable = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    return CommitResult(True, readable and written == config_raw, manual_cleared)
  except (OSError, ValueError, TypeError):
    return CommitResult(config_committed if config_raw is not None else manual_cleared, False, manual_cleared)
  finally:
    if lock_fd is not None:
      os.close(lock_fd)
    if lease_fd is not None:
      os.close(lease_fd)
    for staging in (manual_staging, config_staging):
      if staging is not None:
        try:
          os.unlink(staging)
        except OSError:
          pass
