"""Drive-start selection of vision-only longitudinal leads."""

from openpilot.starpilot.saved_source import read_saved

KEY = "UseVOACC"
DESCRIPTION = ("Use vision-only adaptive cruise control instead of radar-assisted lead detection. " +
               "Requires StarPilot longitudinal control. Applies next drive; radar faults and safety checks remain active.")


def selected(params, cp) -> bool:
  if (cp is None or not getattr(cp, "openpilotLongitudinalControl", False) or
      getattr(cp, "notCar", True) or getattr(cp, "dashcamOnly", True) or getattr(cp, "passive", True)):
    return False
  raw, readable = read_saved(params, KEY, 8)
  return readable and raw == b"1"
