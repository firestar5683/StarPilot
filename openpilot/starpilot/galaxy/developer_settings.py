"""Galaxy-only, next-drive developer preferences."""

from openpilot.starpilot.longitudinal.voacc import KEY, DESCRIPTION
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsState


class DeveloperSettingsOwner:
  def __init__(self, params, authorized):
    self.params = params
    self.authorized = authorized

  def snapshot(self):
    raw, readable = read_saved(self.params, KEY, 8)
    valid = readable and raw in (None, b"0", b"1")
    parked = self.authorized()
    row = FeatureRow(KEY, "Use VOACC", ("On" if raw == b"1" else "Off") if valid else "Invalid saved value",
                     raw, ("Off", "On") if valid else (), available=parked and valid,
                     reason=(DESCRIPTION if parked else "Park the vehicle to change this setting.") if valid else
                            "Invalid saved value", default_value="Off")
    return FeatureSettingsState("developer", "Developer driving options", "Changes apply next drive.", (row,), parked)

  def apply(self, request):
    if request.key != KEY or request.value not in ("Off", "On") or request.expected not in (None, b"0", b"1"):
      return False
    result = commit_exact(self.params, key=KEY, max_bytes=8, raw=b"1" if request.value == "On" else b"0",
                          expected=request.expected, authorized=self.authorized, temp_prefix=".voacc-")
    return result.committed and result.verified
