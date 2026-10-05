from opendbc.car.gm.values import is_gm_auto_hold
from openpilot.starpilot.saved_source import read_saved


class AutoHoldPreference:
  def __init__(self, cp, params):
    self.cp, self.params = cp, params
    self.read_ns = 0
    self.enabled = False

  def update(self, now_ns):
    if type(now_ns) is not int or now_ns <= 0 or not is_gm_auto_hold(self.cp):
      self.enabled = False
      return False
    if now_ns < self.read_ns:
      self.read_ns = 0
      self.enabled = False
      return False
    if self.read_ns == 0 or now_ns - self.read_ns >= 250_000_000:
      self.read_ns = now_ns
      try:
        choice = read_saved(self.params, "GMAutoHold", 8)
        safe, safe_valid = read_saved(self.params, "SafeMode", 8)
        longitudinal, long_valid = read_saved(self.params, "DisableOpenpilotLongitudinal", 8)
        master = read_saved(self.params, "OpenpilotEnabledToggle", 8)
        self.enabled = bool(choice == (b"1", True) and master == (b"1", True) and
                            safe_valid and safe in (None, b"0") and long_valid and longitudinal in (None, b"0"))
      except (OSError, RuntimeError, TypeError, ValueError):
        self.enabled = False
    return self.enabled
