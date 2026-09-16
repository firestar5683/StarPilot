import json
import math
import time

from openpilot.starpilot.navigation.location_state import finite_number

# navigationd publishes at 1 Hz. Allow a missed update, then stop using its hints.
NAV_INSTRUCTION_MAX_AGE = 2.5


def parse_instruction_state(raw: object) -> dict:
  if isinstance(raw, (str, bytes)):
    try:
      raw = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
      return {}

  if not isinstance(raw, dict) or raw.get("valid") is not True:
    return {}

  updated_at = raw.get("updatedAtMonotonic")
  if isinstance(updated_at, bool) or not isinstance(updated_at, (int, float)):
    return {}
  try:
    updated_at = float(updated_at)
  except OverflowError:
    return {}
  if not math.isfinite(updated_at):
    return {}
  # Check on every control cycle, even when the stored instruction is unchanged.
  if not 0.0 <= time.monotonic() - updated_at <= NAV_INSTRUCTION_MAX_AGE:
    return {}
  distance = finite_number(raw.get("maneuverDistance"))
  if distance is None or distance < 0:
    return {}
  if "nextManeuverDistance" in raw:
    distance = finite_number(raw["nextManeuverDistance"])
    if distance is None or distance < 0:
      return {}
  for field in ("laneCount", "sameSideLaneCount", "activeLaneIndex"):
    if field in raw and (type(raw[field]) is not int or raw[field] < (-1 if field == "activeLaneIndex" else 0)):
      return {}
  return raw
