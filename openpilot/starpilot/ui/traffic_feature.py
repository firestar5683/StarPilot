"""Saved Traffic profile rows and exact-source preference edits."""

import math

from openpilot.starpilot.longitudinal.profile_document import PERSONALITY_PROFILES_PARAM
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest
from openpilot.starpilot.ui.long_profile_feature import VALUE_HELP


FOLLOW = "TrafficFollow"
JERKS = ("TrafficJerkAcceleration", "TrafficJerkDeceleration", "TrafficJerkSpeed",
         "TrafficJerkSpeedDecrease", "TrafficJerkDanger")
RELAXED = ("RelaxedFollow", "RelaxedJerkAcceleration", "RelaxedJerkDeceleration", "RelaxedJerkSpeed",
           "RelaxedJerkSpeedDecrease", "RelaxedJerkDanger")
SOURCES = ("CustomPersonalities", PERSONALITY_PROFILES_PARAM, FOLLOW, *JERKS, *RELAXED)
EDIT_KEYS = frozenset((FOLLOW, *JERKS))
REPAIR_FOLLOW = "long_repair:TrafficFollow"
LABELS = {FOLLOW: "Low-speed follow", "TrafficJerkAcceleration": "Acceleration jerk",
          "TrafficJerkDeceleration": "Deceleration jerk", "TrafficJerkSpeed": "Speed jerk",
          "TrafficJerkSpeedDecrease": "Speed decrease jerk", "TrafficJerkDanger": "Danger jerk"}


class TrafficFeature:
  def __init__(self, owner):
    self.owner = owner
    self.params = owner.params

  def capability(self) -> tuple | None:
    return self.owner.long_profiles.curve_capability()

  def _sources(self) -> tuple[tuple[tuple[str, bytes | None], ...], bool]:
    sources = []
    readable = True
    for key in SOURCES:
      raw, valid_source = read_saved(self.params, key, 65536 if key == PERSONALITY_PROFILES_PARAM else 128)
      sources.append((key, raw))
      readable = readable and valid_source
    return tuple(sources), readable

  def _value(self, key: str, raw: bytes | None) -> tuple[float | bool | None, bool]:
    if key == "CustomPersonalities":
      if raw is None:
        default = self.params.get_default_value(key)
        return (default, type(default) is bool)
      return (raw == b"1", raw in (b"0", b"1"))
    try:
      number = float(raw) if raw is not None else float(self.params.get_default_value(key))
    except (TypeError, ValueError, OverflowError):
      return None, False
    low = 0.5 if key.endswith("Follow") else 25.0
    high = 3.0 if key.endswith("Follow") else 200.0
    return number, math.isfinite(number) and low <= number <= high

  def rows(self, parked: bool, system_long: bool, *, repair_allowed: bool | None = None) -> list[FeatureRow]:
    repair_allowed = (parked if repair_allowed is None else repair_allowed) and self.owner.authority("parked_preferences")
    dependencies, readable = self._sources()
    source = dict(dependencies)
    capability = self.capability()
    allowed = system_long and self.owner.authority("long") and capability is not None and readable
    fingerprint = self.owner.vehicle_fingerprint()
    master, master_valid = self._value("CustomPersonalities", source["CustomPersonalities"])
    active_note = ("Saved profiles switch needs repair" if not master_valid else
                   "Saved values are inactive while Custom Driving Profiles is Off" if not master else
                   "Saved follow and jerk settings apply when Traffic mode is selected")
    rows = []
    for key in (FOLLOW, *JERKS):
      value, valid = self._value(key, source[key])
      unsupported = key == FOLLOW and valid and isinstance(value, float) and value < 0.75
      unit = "s" if key == FOLLOW else "%"
      shown = str(value) if valid else "Invalid saved value"
      rows.append(FeatureRow(key, LABELS[key], shown, source[key],
                             step=0.05 if key == FOLLOW else 5.0,
                             minimum=0.75 if key == FOLLOW else 25.0,
                             maximum=3.0 if key == FOLLOW else 200.0, unit=unit,
                             available=allowed and valid and not unsupported,
                             reason=("Saved follow is below the supported 0.75 s minimum; restore explicitly" if unsupported else
                                     active_note + ". " + ("Following time at low speeds; blends toward Relaxed as speed rises." if key == FOLLOW else
                                                          VALUE_HELP[key.removeprefix("Traffic")]) if valid else
                                     "Invalid saved value; original bytes remain unchanged"),
                             vehicle_fingerprint=fingerprint, capability=capability, dependencies=dependencies))
      if unsupported:
        rows.append(FeatureRow(REPAIR_FOLLOW, "Restore supported Traffic follow", "Set to 0.75 s",
                               source[key], available=allowed and repair_allowed,
                               reason="Requires confirmation; other saved Traffic values stay unchanged",
                               vehicle_fingerprint=fingerprint, capability=capability, dependencies=dependencies))
    rows.append(FeatureRow("", "Higher-speed values", "Inherited from Relaxed follow and jerk settings",
                           reason="With Custom Driving Profiles On, blends toward saved Relaxed values; otherwise defaults apply"))
    return rows

  def apply(self, request: FeatureSettingsRequest) -> bool:
    if request.key == REPAIR_FOLLOW and not self.owner.authority("parked_preferences"):
      return False
    if request.key not in EDIT_KEYS and request.key != REPAIR_FOLLOW:
      return False
    key = FOLLOW if request.key == REPAIR_FOLLOW else request.key
    if tuple(name for name, _ in request.dependencies) != SOURCES:
      return False
    expected = dict(request.dependencies)
    if request.expected != expected[key]:
      return False

    def authorized() -> bool:
      if (not request.vehicle_fingerprint or self.owner.vehicle_fingerprint() != request.vehicle_fingerprint or
          request.capability is None or self.capability() != request.capability or
          not self.owner.authority("long") or
          request.key == REPAIR_FOLLOW and not self.owner.authority("parked_preferences")):
        return False
      fresh, readable = self._sources()
      return readable and fresh == request.dependencies

    if not authorized():
      return False
    current, valid = self._value(key, request.expected)
    if not valid:
      return False
    if request.key == REPAIR_FOLLOW:
      if not request.confirmation or request.value != "confirm" or not isinstance(current, float) or not 0.5 <= current < 0.75:
        return False
      raw = b"0.75"
    else:
      try:
        number = float(request.value)
      except (TypeError, ValueError, OverflowError):
        return False
      low, high = (0.75, 3.0) if key == FOLLOW else (25.0, 200.0)
      if not math.isfinite(number) or not low <= number <= high or (key == FOLLOW and
          (not isinstance(current, float) or current < 0.75)):
        return False
      raw = str(round(number, 4)).encode()
    return commit_exact(self.params, key=key, max_bytes=128, raw=raw, expected=request.expected,
                        authorized=authorized, temp_prefix=".traffic-profile-").verified
