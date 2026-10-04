"""Retire redundant switches once, preserving their effective saved behavior."""

import base64
import json
import hashlib

from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.longitudinal.profile_document import (
  PERSONALITY_PROFILES_PARAM, migrate_profile_document, is_unconfigured_profile_document,
)

STATE_KEY = "SettingsRetirementState"
EVIDENCE_KEY = "RetiredSettingsEvidence"
PROFILE_FLAGS = tuple(name.title() + "PersonalityProfile" for name in ("aggressive", "standard", "relaxed", "traffic"))


def retire_settings(params):
  """Run parked after state admission and before default creation/consumers.

  Write child reconciliation before retiring each parent. Corrupt switches are
  archived in an optional document and treated as Off; this never enables a
  dormant feature. Returns concrete reconciliation issues for manager logging.
  """
  issues = []
  evidence = {}
  evidence_writable = True
  raw, readable = read_saved(params, EVIDENCE_KEY, 65536)
  if not readable:
    evidence_writable = False
    issues.append("Unreadable retired switch evidence retained")
  elif raw is not None:
    try:
      prior = json.loads(raw)
      valid = (isinstance(prior, dict) and len(prior) <= 6 and
               all(key in (*PROFILE_FLAGS, "QOLLongitudinal", "AdvancedLateralTune") and isinstance(value, dict) and
                   set(value) <= {"rawBase64", "reason", "sha256"} and
                   (value.get("rawBase64") is None or isinstance(value.get("rawBase64"), str) and len(value["rawBase64"]) <= 2048) and
                   isinstance(value.get("reason"), str) and len(value["reason"]) <= 512
                   for key, value in prior.items()))
      if valid:
        evidence = prior
      else:
        evidence_writable = False
        issues.append("Invalid retired switch evidence retained")
    except (ValueError, UnicodeError, RecursionError):
      evidence_writable = False
      issues.append("Invalid retired switch evidence retained")

  def archive(key, raw, reason, readable=True):
    item = {"rawBase64": base64.b64encode(raw).decode() if readable and raw is not None else None,
            "reason": reason + ("; original file could not be read safely" if not readable else "")}
    if readable and raw is not None:
      item["sha256"] = hashlib.sha256(raw).hexdigest()
    amended = {**evidence, key: item}
    if evidence_writable and len(json.dumps(amended).encode()) <= 65536:
      params.put(EVIDENCE_KEY, amended, block=True)
      evidence.update(amended)
    else:
      issues.append(f"{key}: new retirement evidence not saved; existing evidence retained")
    issues.append(reason)

  state_raw, state_readable = read_saved(params, STATE_KEY, 256)
  try:
    state = json.loads(state_raw) if state_readable and state_raw is not None else {"version": 1, "completed": []}
    state_valid = (isinstance(state, dict) and set(state) == {"version", "completed"} and state["version"] == 1 and
                   isinstance(state["completed"], list) and len(state["completed"]) <= 2 and
                   all(group in ("cruise", "profiles") for group in state["completed"]))
  except (ValueError, UnicodeError):
    state, state_valid = {"version": 1, "completed": []}, False
  if not state_readable or not state_valid:
    issues.append("Invalid settings retirement completion state; safe first-migration reconciliation used")
    state = {"version": 1, "completed": []}
  completed_raw = state["completed"]
  assert isinstance(completed_raw, list)
  completed = set(completed_raw)
  def finish(group):
    completed.add(group)
    # Separate from raw evidence, so corrupt older evidence cannot prevent a
    # completed migration from preserving the user's subsequent edits.
    params.put(STATE_KEY, {"version": 1, "completed": sorted(completed)}, block=True)

  if "cruise" not in completed:
    master, readable = read_saved(params, "QOLLongitudinal", 8)
    if not readable or master not in (None, b"0", b"1"):
      archive("QOLLongitudinal", master, "Invalid cruise switch; inactive cruise features restored to defaults", readable)
    if master != b"1":
      for key in ("ForceStops", "ReverseCruise"):
        params.put_bool(key, False, block=True)
      for key, value in (("CustomCruise", 1.0), ("CustomCruiseLong", 5.0)):
        params.put(key, value, block=True)
    params.remove("QOLLongitudinal")
    finish("cruise")

  if "profiles" not in completed:
    flags = {}
    for key in PROFILE_FLAGS:
      raw, readable = read_saved(params, key, 8)
      if not readable or raw not in (None, b"0", b"1"):
        archive(key, raw, "Invalid personality curve switch; its legacy curves disabled", readable)
        flags[key] = b"0"
      else:
        flags[key] = raw if raw is not None else b"0"
    raw, readable = read_saved(params, PERSONALITY_PROFILES_PARAM, 65536)
    try:
      document = migrate_profile_document(raw) if readable and raw is not None else None
    except (ValueError, TypeError, UnicodeError, RecursionError):
      document = None
    if not readable or raw is not None and document is None and not is_unconfigured_profile_document(raw):
      issues.append("Invalid personality curves retained; supplied profiles remain in use")
    if document is not None:
      for key, enabled in flags.items():
        if enabled != b"0":
          continue
        name = key.removesuffix("PersonalityProfile").lower()
        profile = document["profiles"][name]
        profile["following"] = {"preset": "dom_default", "curve": []}
        for category in ("acceleration", "braking"):
          if profile[category].get("legacyActivation", False):
            profile[category] = {"preset": "selected_profile", "curve": []}
      params.put(PERSONALITY_PROFILES_PARAM, document, block=True)
    for key in PROFILE_FLAGS:
      params.remove(key)
    finish("profiles")
  params.remove("AdvancedLateralTune")
  return tuple(issues)
