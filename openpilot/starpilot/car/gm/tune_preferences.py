from opendbc.car.gm.long_tune import tune_options
from openpilot.starpilot.saved_source import read_saved

KEY = "GMLongitudinalTune"
CHOICES = {0: "Vehicle Default", 1: "ACC Tune", 2: "Volt Tune"}


def read_choice(params):
  try:
    raw, readable = read_saved(params, KEY, 8)
  except (OSError, RuntimeError, TypeError, ValueError):
    return 0, None, False, False
  values = {None: 0, b"0": 0, b"1": 1, b"2": 2}
  return values.get(raw, 0), raw, readable, readable and raw in values


def selected_tune(params, *, enabled):
  try:
    value, _, _, valid = read_choice(params)
    safe, readable = read_saved(params, "SafeMode", 8)
    return value if enabled and valid and readable and safe in (None, b"0") else 0
  except (OSError, RuntimeError, TypeError, ValueError):
    return 0


class AccTunePreference:
  def __init__(self, cp, params):
    self.cp, self.params = cp, params
    self.read_ns = 0
    self.enabled = False

  def update(self, now_ns):
    if type(now_ns) is not int or now_ns <= 0 or 1 not in tune_options(self.cp):
      self.enabled = False
      return False
    if now_ns < self.read_ns:
      self.read_ns = 0
      self.enabled = False
      return False
    if self.read_ns == 0 or now_ns - self.read_ns >= 500_000_000:
      self.read_ns = now_ns
      try:
        master = read_saved(self.params, "OpenpilotEnabledToggle", 8) == (b"1", True)
        disabled, readable = read_saved(self.params, "DisableOpenpilotLongitudinal", 8)
        self.enabled = bool(readable and disabled in (None, b"0") and selected_tune(self.params, enabled=master) == 1)
      except (OSError, RuntimeError, TypeError, ValueError):
        self.enabled = False
    return self.enabled
