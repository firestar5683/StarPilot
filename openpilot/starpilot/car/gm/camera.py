from opendbc.car.gm.values import camera_acc_pedal_profile
from openpilot.starpilot.saved_source import read_saved


class CameraPedalPreference:
  def __init__(self, cp, params, *, maneuver=False):
    self.cp, self.params = cp, params
    self.maneuver = maneuver
    self.read_ns = 0
    self.enabled = False

  def update(self, now_ns):
    profile = camera_acc_pedal_profile(self.cp)
    if (type(now_ns) is not int or now_ns <= 0 or profile is None or not profile.longitudinal or
        self.maneuver and not profile.volt):
      self.enabled = False
      return False
    if now_ns < self.read_ns:
      self.read_ns = 0
      self.enabled = False
      return False
    if self.read_ns == 0 or now_ns - self.read_ns >= 250_000_000:
      self.read_ns = now_ns
      try:
        master = read_saved(self.params, 'OpenpilotEnabledToggle', 8)
        safe, safe_valid = read_saved(self.params, 'SafeMode', 8)
        disabled, disable_valid = read_saved(self.params, 'DisableOpenpilotLongitudinal', 8)
        self.enabled = bool(master == (b'1', True) and safe_valid and safe in (None, b'0') and
                            disable_valid and disabled in (None, b'0'))
        if self.maneuver:
          self.enabled = self.enabled and read_saved(self.params, 'LongitudinalManeuverMode', 8) == (b'1', True)
      except (OSError, RuntimeError, TypeError, ValueError):
        self.enabled = False
    return self.enabled
