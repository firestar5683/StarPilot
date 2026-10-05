"""Parked, source-bound editor for the opt-in native display preferences."""

from collections.abc import Callable
from dataclasses import replace
import math

from openpilot.starpilot.ui.display_preferences import AUTO, BRIGHTNESS, KEYS, MASTER, default_value, read_choice
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest, FeatureSettingsState
from openpilot.starpilot.ui.presentation import Profile


LABELS = {
  MASTER: "Custom Display Settings",
  "ScreenBrightness": "Parked Brightness",
  "ScreenBrightnessOnroad": "Driving Brightness",
  "ScreenTimeout": "Parked Screen Timeout",
  "ScreenTimeoutOnroad": "Driving Interaction Timeout",
}
AUTO_PREFIX = "display:auto:"
BRIGHTNESS_CHOICES = ("Auto",) + tuple(f"{number}%" for number in range(5, 101))
TIMEOUT_CHOICES = tuple(f"{number} s" for number in range(5, 61, 5))


def _display(key: str, value: int | None, valid: bool, unsupported: bool) -> str:
  if unsupported:
    return "Saved Off (unsupported)"
  if not valid or value is None:
    return "Invalid saved choice"
  if key == MASTER:
    return "On" if value else "Off"
  if key in BRIGHTNESS:
    return "Auto" if value == AUTO else str(value)
  return str(value)


class DisplayOwner:
  def __init__(self, params, parked: Callable[[], bool]):
    self.params = params
    self.parked = parked

  def snapshot(self, profile: Profile) -> FeatureSettingsState:
    large = profile == Profile.LARGE
    parked = self.parked()
    saved = {key: read_choice(self.params, key, large=large) for key in KEYS}
    master = saved[MASTER]
    rows = []
    for key in KEYS:
      choice = saved[key]
      valid = choice.valid
      value = _display(key, choice.value, valid, choice.unsupported)
      if not choice.readable:
        reason = "Saved choice cannot be read"
      elif choice.unsupported:
        reason = "Choose Auto before enabling custom display"
      elif not valid:
        reason = "Choose default to repair"
      elif key != MASTER and master.value != 1:
        reason = "Saved; custom display is off"
      elif key == "ScreenTimeoutOnroad":
        reason = "Returns to driving view; screen stays awake"
      else:
        reason = ""
      repair = "Off" if key == MASTER else "Auto" if key in BRIGHTNESS else "30 s" if key == "ScreenTimeout" else \
        "10 s" if large else "5 s"
      dependencies = (tuple((name, saved[name].raw) for name in KEYS if name != MASTER) if key == MASTER else
                      ((MASTER, master.raw),))
      editable = parked and choice.readable and (key == MASTER or master.valid and master.value == 1 or not valid)
      numeric = valid and key != MASTER and choice.value != AUTO
      rows.append(FeatureRow(key, LABELS[key], value, source=choice.raw,
                             choices=("Off", "On") if key == MASTER else
                                     (("Auto",) if numeric else BRIGHTNESS_CHOICES) if key in BRIGHTNESS else (),
                             step=(1.0 if key in BRIGHTNESS else 5.0) if valid and key != MASTER else 0.0,
                             minimum=5.0, maximum=100.0 if key in BRIGHTNESS else 60.0,
                             unit=("%" if key in BRIGHTNESS else "s") if valid and key != MASTER else "",
                             available=editable, reason=reason,
                             repair_value=repair if not valid and choice.readable else "",
                             dependencies=dependencies))
      if key in BRIGHTNESS and valid and choice.value != AUTO:
        rows.append(FeatureRow(AUTO_PREFIX + key, "Use Auto " + LABELS[key], "Fixed level saved",
                               source=choice.raw, available=editable,
                               repair_value="Auto", dependencies=((MASTER, master.raw),)))
    defaults = {key: ('Off' if key == MASTER else 'Auto' if key in BRIGHTNESS else str(default_value(key, large=large))) for key in KEYS}
    rows = tuple(replace(row, default_value=defaults[row.key]) if row.key in defaults else row for row in rows)
    return FeatureSettingsState(page="display", title="Display", subtitle="Saved brightness and interaction timing.",
                                rows=tuple(rows), parked=parked)

  def apply(self, request: FeatureSettingsRequest) -> bool:
    key = request.key.removeprefix(AUTO_PREFIX)
    if key not in KEYS or not self.parked():
      return False
    if request.key.startswith(AUTO_PREFIX) and key not in BRIGHTNESS:
      return False
    if key == MASTER:
      if request.value not in ("Off", "On"):
        return False
      desired = int(request.value == "On")
    elif key in BRIGHTNESS:
      if request.value == "Auto":
        desired = AUTO
      else:
        try:
          number = float(request.value.removesuffix("%"))
        except ValueError:
          return False
        if not math.isfinite(number) or not number.is_integer() or not 5 <= number <= 100:
          return False
        desired = int(number)
    else:
      try:
        number = float(request.value.removesuffix(" s"))
      except ValueError:
        return False
      if not math.isfinite(number) or not number.is_integer() or int(number) % 5 or not 5 <= number <= 60:
        return False
      desired = int(number)
    for final in (False, True):
      if not self.parked():
        return False
      observed = read_choice(self.params, key, large=True)
      if not observed.readable or observed.raw != request.expected:
        return False
      # Turning the master off stays available even when other saved choices
      # are corrupt or have changed while the user was viewing the page.
      if not (key == MASTER and desired == 0):
        expected = dict(request.dependencies)
        required = (set(KEYS) - {MASTER}) if key == MASTER else {MASTER}
        if set(expected) != required:
          return False
        for name in required:
          source = read_choice(self.params, name, large=True)
          if not source.readable or source.raw != expected[name] or (key == MASTER and not source.valid):
            return False
          if key != MASTER and observed.valid and (not source.valid or source.value != 1):
            return False
      if not final:
        continue
    try:
      if key == MASTER:
        self.params.put_bool(key, bool(desired), block=True)
      else:
        self.params.put(key, desired, block=True)
    except (OSError, KeyError, TypeError, ValueError):
      return False
    result = read_choice(self.params, key, large=True)
    return result.readable and result.valid and result.value == desired
