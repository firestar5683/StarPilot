"""One saved planner preference, latched for the manager-owned drive process."""
from dataclasses import dataclass
from importlib import import_module

from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.saved_document import commit_exact

KEY = 'UseStarPilotLongitudinalPlanner'


@dataclass(frozen=True)
class PlannerSelection:
  starpilot: bool
  valid: bool
  raw: bytes | None


def read_selection(params):
  raw, readable = read_saved(params, KEY, 8)
  valid = readable and raw in (None, b'0', b'1')
  # Invalid/unreadable preference preserves the default planner. Only an exact
  # saved Off selects upstream; no malformed prefix silently changes a drive.
  return PlannerSelection(raw != b'0' or not readable, valid, raw)


def run_selected(params, starpilot_main, *, importer=import_module):
  selection = read_selection(params)
  if selection.starpilot:
    return starpilot_main()
  return importer('openpilot.starpilot.longitudinal.upstream.plannerd').main()


def save_selection(params, value, expected, *, authorized):
  if value not in ("Off", "On"):
    return False
  result = commit_exact(params, key=KEY, max_bytes=8, raw=b"1" if value == "On" else b"0",
                        expected=expected, authorized=authorized, temp_prefix=".planner-selection-")
  return result.committed and result.verified
