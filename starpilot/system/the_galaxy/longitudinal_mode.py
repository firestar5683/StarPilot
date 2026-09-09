"""Adapter over existing mode Params, with coherent participating runtime reads.

Enable a conditional target before clearing its competitor; for fixed modes,
set the fallback before disabling conditional flags. Every stored write boundary
selects either the old or requested mode, including when a write fails. The
shared sidecar lock keeps participating readers on their complete snapshot.
Legacy nonparticipating writers remain advisory-lock exceptions, not
transactions. API success confirms storage, not plan activation.
"""
from contextlib import contextmanager
from threading import RLock

from openpilot.starpilot.common.longitudinal_mode import MODE_KEYS, mode_lock
MODES = {"chill": None, "experimental": "ExperimentalMode",
         "conditional_experimental": "ConditionalExperimental", "conditional_chill": "ConditionalChill"}
WRITE_LOCK = RLock()


class ModeError(ValueError):
  def __init__(self, message, status=409):
    super().__init__(message)
    self.status = status


def selected_mode(values):
  if values["ConditionalExperimental"]:
    return "conditional_experimental"
  if values["ConditionalChill"]:
    return "conditional_chill"
  return "experimental" if values["ExperimentalMode"] else "chill"


def lock_reason(params, capable):
  # Explicit state only: absent/malformed safety state must not authorize writes.
  def boolean(key):
    value = params.get(key)
    if value in (True, "1", b"1", "True", b"True"):
      return True
    if value in (False, "0", b"0", "False", b"False"):
      return False
    return None
  offroad, onroad = boolean("IsOffroad"), boolean("IsOnroad")
  if offroad is None or onroad is None or offroad == onroad:
    return "Longitudinal control mode requires a known, consistent road state."
  if boolean("SafeMode") is not False:
    return "Longitudinal control mode is locked by Safe Mode or unavailable safety state."
  if capable is not True:
    return "openpilot longitudinal control is unavailable for the detected vehicle."
  return ""


def snapshot(params, capable):
  try:
    with mode_lock(params):
      return _snapshot(params, capable)
  except OSError as error:
    raise ModeError("Longitudinal mode is busy or unavailable. Refresh before retrying.", 503) from error


def _snapshot(params, capable):
  values = {key: params.get_bool(key) for key in MODE_KEYS}
  reason = lock_reason(params, capable)
  return {"mode": selected_mode(values), "values": values, "locked": bool(reason), "reason": reason,
          "experimental_confirmed": params.get_bool("ExperimentalModeConfirmed")}


@contextmanager
def _write_lock(params):
  try:
    with mode_lock(params, exclusive=True):
      yield
  except OSError as error:
    raise ModeError("Longitudinal mode is busy or unavailable. Refresh before retrying.", 503) from error


def set_mode(params, target, expected, capability, acknowledged=False):
  if not isinstance(target, str) or target not in MODES:
    raise ModeError("Unknown longitudinal control mode.", 400)
  if not isinstance(expected, dict) or any(type(expected.get(key)) is not bool for key in MODE_KEYS):
    raise ModeError("An exact previous mode snapshot is required.", 400)
  with WRITE_LOCK, _write_lock(params):
    try:
      current = _snapshot(params, capability())
      if current["locked"]:
        raise ModeError(current["reason"], 403)
      if current["values"] != {key: expected[key] for key in MODE_KEYS}:
        raise ModeError("Longitudinal mode changed elsewhere. Refresh before retrying.")
      if current["mode"] == target:
        return current  # Preserve dormant flags, defaults and manual override state.
      if target == "experimental" and not current["experimental_confirmed"] and acknowledged is not True:
        raise ModeError("Experimental Mode requires explicit acknowledgement before enabling.")
      if target == "conditional_experimental":
        writes = [("ConditionalExperimental", True), ("ConditionalChill", False), ("ExperimentalMode", False)]
      elif target == "conditional_chill":
        writes = [("ConditionalChill", True), ("ConditionalExperimental", False), ("ExperimentalMode", False)]
      else:
        writes = [("ExperimentalMode", target == "experimental"), ("ConditionalChill", False), ("ConditionalExperimental", False)]
      for key, value in writes:
        reason = lock_reason(params, capability())
        if reason:
          raise ModeError(reason, 403)
        params.put_bool(key, value)
        if params.get_bool(key) is not value:
          raise ModeError("Mode write could not be verified; refresh before retrying.", 500)
      result = _snapshot(params, capability())
      desired = {key: key == MODES[target] for key in MODE_KEYS}
      if result["values"] != desired or result["locked"]:
        raise ModeError("Mode changed during the update; refresh before retrying.")
      return result
    except ModeError:
      raise
    except Exception as error:
      raise ModeError("Longitudinal mode update failed; refresh to inspect the stored state.", 500) from error
