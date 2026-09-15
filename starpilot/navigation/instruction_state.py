import json
import math
import time


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
  return raw
