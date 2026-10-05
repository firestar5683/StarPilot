import hashlib

from openpilot.starpilot.aol.vehicle import policy_for
from openpilot.starpilot.conditional_mode.manual import ioniq6_media_eligible
from openpilot.starpilot.controllers.wheel_actions import ACTIONS, DEFAULTS, KEYS, eligible
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.ui.feature_settings_state import FeatureRow


PREFIX = "wheel:"
LABELS = ("LKAS press", "Main cruise press", "Distance short press", "Distance long press", "Distance very long press",
          "Cancel short press", "Cancel long press", "Cancel very long press", "MODE press", "MODE long press",
          "MODE very long press", "Star button", "Star long press", "Star very long press")


class WheelFeature:
  def __init__(self, owner):
    self.owner = owner

  def capability(self):
    cp = self.owner.vehicle_params()
    if not eligible(cp):
      return None
    reader = cp.as_reader() if hasattr(cp, "as_reader") else cp
    base = (cp.carFingerprint, hashlib.sha256(reader.as_builder().to_bytes()).hexdigest())
    if self.owner.configuration_vehicle():
      return base + (self.owner.longitudinal_available(), "configuration")
    return base + (True,) if self.owner.configuration_longitudinal() else base

  def choices(self, key):
    cp = self.owner.vehicle_params()
    if self.capability() is None:
      return ()
    policy = policy_for(cp)
    media = ioniq6_media_eligible(cp)
    if self.owner.configuration_vehicle():
      from openpilot.starpilot.car.hyundai.settings import configuration_wheel_policy, configuration_media_supported
      policy = configuration_wheel_policy(cp) or policy
      media = configuration_media_supported(cp) or media
    if key in KEYS[:2] and policy.fixed_cruise_buttons:
      return ()
    if key in KEYS[8:] and not media:
      return ()
    if key in KEYS[:5] and not policy.settings_supported:
      return ()
    codes = {0, 8, 11, 12, 13}
    if self.owner.longitudinal_available():
      codes.update((1, 2, 5, 10, 14))
      codes.add(6)
    if media:
      codes.add(7)
    if not policy.fixed_cruise_buttons and policy.settings_supported:
      if key in KEYS[:5] or not policy.explicit_latch:
        codes.update((3, 4, 9))
    elif policy.distance_pause_only and key in KEYS[2:5]:
      codes.update((3, 4))
    if key == "MainCruiseButtonControl":
      codes &= {0, 9}
      if self.owner.longitudinal_available():
        codes.add(10)
    return tuple(label for label, code in ACTIONS.items() if code in codes)

  def rows(self):
    capability = self.capability()
    if capability is None:
      return []
    rows = []
    for key, label in zip(KEYS, LABELS, strict=True):
      choices = self.choices(key)
      if not choices:
        continue
      raw, readable = read_saved(self.owner.params, key, 8)
      number = DEFAULTS.get(key, 0) if raw is None else int(raw) if raw in tuple(str(i).encode() for i in range(15)) else -1
      selected = next((name for name, code in ACTIONS.items() if code == number), None)
      default = next(label for label, code in ACTIONS.items() if code == DEFAULTS.get(key, 0))
      rows.append(FeatureRow(PREFIX + key, label, selected or "Invalid saved action", raw, choices,
                             default_value=default if default in choices else None,
                             available=readable and self.owner.authority("preferences"),
                             reason="Axis pause and AOL assignments apply after restarting. Other actions can apply this drive. Long actions fire while held.",
                             capability=capability, repair_value="Off" if selected is None else ""))
    return rows

  def apply(self, request):
    key = request.key.removeprefix(PREFIX)
    if key not in KEYS or request.value not in self.choices(key) or request.capability != self.capability():
      return False
    capability = request.capability
    def authorized():
      return (self.owner.authority("preferences") and capability == self.capability() and
              request.value in self.choices(key))
    return commit_exact(self.owner.params, key=key, max_bytes=8, raw=str(ACTIONS[request.value]).encode(),
                        expected=request.expected, authorized=authorized, temp_prefix=".tmp_wheel_").committed
