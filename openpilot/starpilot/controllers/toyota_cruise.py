"""Toyota PCM cruise step preference for the recurring ACC_CONTROL owner."""

import time
from openpilot.starpilot.saved_source import read_saved


def capability(cp):
  try:
    if (cp is None or cp.brand != "toyota" or not cp.pcmCruise or not cp.openpilotLongitudinalControl or
        cp.passive or cp.dashcamOnly or cp.notCar or not cp.carFingerprint):
      return None
    return (cp.brand, cp.carFingerprint, bool(cp.pcmCruise), bool(cp.openpilotLongitudinalControl),
            bool(cp.passive), bool(cp.dashcamOnly), bool(cp.notCar))
  except (AttributeError, TypeError, ValueError):
    return None


class ToyotaCruisePreference:
  def __init__(self, cp, params):
    self.cp, self.params = cp, params
    self.next_read = 0.0
    self.enabled = False

  def update(self):
    now = time.monotonic()
    if now >= self.next_read:
      self.next_read = now + 1.0
      choice, choice_valid = read_saved(self.params, "ReverseCruise", 8)
      safe, safe_valid = read_saved(self.params, "SafeMode", 8)
      self.enabled = bool(capability(self.cp) is not None and choice_valid and safe_valid and
                          choice == b"1" and safe in (None, b"0"))
    return self.enabled
