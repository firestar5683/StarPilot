from opendbc.car.gm.values import CAR, is_bolt_pedal_profile
from openpilot.starpilot.saved_source import read_saved

PADDLE_IDS = (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021,
              CAR.CHEVROLET_BOLT_CC_2022_2023, CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL)


class PaddlePreference:
  def __init__(self, cp, params):
    self.cp, self.params = cp, params

  def update(self, now_ns):
    if (type(now_ns) is not int or now_ns <= 0 or self.cp.carFingerprint not in PADDLE_IDS or
        not is_bolt_pedal_profile(self.cp)):
      return "auto"
    try:
      master = read_saved(self.params, "OpenpilotEnabledToggle", 8)
      safe, safe_valid = read_saved(self.params, "SafeMode", 8)
      disabled, disabled_valid = read_saved(self.params, "DisableOpenpilotLongitudinal", 8)
      if (master != (b"1", True) or not safe_valid or safe not in (None, b"0") or
          not disabled_valid or disabled not in (None, b"0")):
        return "auto"
      raw, valid = read_saved(self.params, "LongitudinalManeuverPaddleMode", 64)
      mode = raw.decode("utf-8", errors="replace").strip().lower() if valid and raw is not None else "auto"
      return mode if mode in ("auto", "off", "force") else "auto"
    except (OSError, RuntimeError, TypeError, ValueError):
      return "auto"
