"""Versioned accepted-limit persistence with explicit identity applicability."""

import json
import math

from openpilot.cereal import custom
from openpilot.starpilot.schema_cache import schema_fingerprint
from openpilot.starpilot.speed_limits import acceptance as acc

FORMAT = "starpilot-slc-accepted"
VERSION = 1


def encode(accepted: acc.AcceptedLimit, saved_wall_ns: int) -> str:
  if not isinstance(accepted, acc.AcceptedLimit) or type(saved_wall_ns) is not int or saved_wall_ns <= 0:
    raise ValueError("invalid accepted history")
  candidate = accepted.candidate
  identity = candidate.observation_identity
  if not acc.observation_is_valid(acc.Observation(acc.ObservationKind.VALID, candidate), session_id=accepted.session_id):
    raise ValueError("invalid accepted candidate")
  return json.dumps({"format": FORMAT, "version": VERSION, "source_schema": schema_fingerprint(custom.SlcDashboardObservation.schema),
                     "saved_wall_ns": saved_wall_ns, "source": candidate.source, "speed_mps": candidate.speed_mps,
                     "identity_kind": identity.kind.value, "identity_value": identity.value,
                     "origin_session": accepted.session_id}, sort_keys=True, separators=(",", ":"))


def decode(raw: str | bytes | dict | None, *, session_id: str, current: acc.Observation,
           now_wall_ns: int, max_age_ns: int) -> acc.AcceptedLimit | None:
  """Only durable geographic identity can be carried into a new drive.

  The caller sets an applicability age from its source contract. Dashboard TSR
  producer episodes are drive-local and cannot be restored across a new session.
  """
  if raw is None or type(session_id) is not str or not session_id or type(now_wall_ns) is not int or type(max_age_ns) is not int:
    return None
  if max_age_ns < 0 or now_wall_ns <= 0:
    return None
  try:
    value = raw if isinstance(raw, dict) else json.loads(raw)
    if (type(value) is not dict or set(value) != {"format", "version", "source_schema", "saved_wall_ns", "source",
                                               "speed_mps", "identity_kind", "identity_value", "origin_session"} or
        value["format"] != FORMAT or type(value["version"]) is not int or value["version"] != VERSION or
        value["source_schema"] != schema_fingerprint(custom.SlcDashboardObservation.schema) or
        type(value["saved_wall_ns"]) is not int or value["saved_wall_ns"] > now_wall_ns or
        now_wall_ns - value["saved_wall_ns"] > max_age_ns or
        value["identity_kind"] != acc.IdentityKind.GEOGRAPHIC.value or
        not isinstance(value["identity_value"], str) or not value["identity_value"] or
        not isinstance(value["origin_session"], str) or not value["origin_session"] or
        type(value["speed_mps"]) not in (int, float) or not math.isfinite(value["speed_mps"])):
      return None
    candidate = acc.Candidate(value["source"], acc.ObservationIdentity(acc.IdentityKind.GEOGRAPHIC, value["identity_value"]),
                              float(value["speed_mps"]))
    if (not acc.observation_is_valid(acc.Observation(acc.ObservationKind.VALID, candidate), session_id=session_id) or
        current != acc.Observation(acc.ObservationKind.VALID, candidate)):
      return None
    return acc.AcceptedLimit(candidate, session_id, 0)
  except (TypeError, ValueError, OverflowError):
    return None
