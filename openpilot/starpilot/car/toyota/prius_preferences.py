from opendbc.car.toyota.prius_longitudinal import enabled as filter_enabled
from openpilot.starpilot.saved_source import read_saved


def filter_preference_enabled(params):
  try:
    master = read_saved(params, 'OpenpilotEnabledToggle', 8)
    safe, safe_valid = read_saved(params, 'SafeMode', 8)
    disabled, disable_valid = read_saved(params, 'DisableOpenpilotLongitudinal', 8)
    return bool(master == (b'1', True) and safe_valid and safe in (None, b'0') and
                disable_valid and disabled in (None, b'0'))
  except (OSError, RuntimeError, TypeError, ValueError):
    return False


class PriusFilterPreference:
  def __init__(self, cp, params):
    self.cp, self.params = cp, params
    self.read_ns = 0
    self.enabled = False

  def update(self, now_ns):
    if type(now_ns) is not int or now_ns <= 0 or not filter_enabled(self.cp):
      self.enabled = False
      return False
    if now_ns < self.read_ns:
      self.read_ns = 0
      self.enabled = False
      return False
    if self.read_ns == 0 or now_ns - self.read_ns >= 250_000_000:
      self.read_ns = now_ns
      self.enabled = filter_preference_enabled(self.params)
    return self.enabled
