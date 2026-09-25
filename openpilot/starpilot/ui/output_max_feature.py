"""Source-bound edits for the shared final acceleration ceiling."""

import math

from openpilot.starpilot.longitudinal.output_max import KEY, DEFAULT, MINIMUM, MAXIMUM, MAX_BYTES, capability, read_maximum
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.ui.feature_settings_state import FeatureRow


class OutputMaximumFeature:
  def __init__(self, owner):
    self.owner = owner

  def row(self) -> FeatureRow:
    owner = self.owner
    saved = read_maximum(owner.params)
    parked = owner.authority("parked_preferences")
    capable = None if parked else capability(owner.vehicle_params())
    allowed = (parked or capable is not None and owner.authority("long_output")) and saved.readable
    return FeatureRow(KEY, "Maximum acceleration", str(saved.value) if saved.valid else "Invalid saved value", saved.raw,
                      step=0.1 if saved.valid else 0.0, minimum=MINIMUM, maximum=MAXIMUM, unit="m/s²",
                      available=allowed, reason="Updates within one second; vehicle limits still apply" if saved.valid else
                      "Restore 4.0 to replace the invalid saved value" if saved.readable else "Saved value cannot be read",
                      vehicle_fingerprint=None if parked else owner.vehicle_fingerprint(), capability=capable,
                      repair_value="" if saved.valid else str(DEFAULT))

  def apply(self, request) -> bool:
    if (request.key != KEY or request.dependencies or request.related_source is not None or request.display_unit or
        request.direction):
      return False
    try:
      value = float(request.value)
    except (TypeError, ValueError, OverflowError):
      return False
    if not math.isfinite(value) or not MINIMUM <= value <= MAXIMUM:
      return False
    owner = self.owner

    def authorized() -> bool:
      saved = read_maximum(owner.params)
      parked_request = request.capability is None and request.vehicle_fingerprint is None
      if parked_request:
        allowed = owner.authority("parked_preferences")
      else:
        capable = capability(owner.vehicle_params())
        allowed = (owner.authority("long_output") and capable is not None and capable == request.capability and
                   owner.vehicle_fingerprint() == request.vehicle_fingerprint)
      return bool(allowed and saved.readable and saved.raw == request.expected and (saved.valid or value == DEFAULT))

    result = commit_exact(owner.params, key=KEY, max_bytes=MAX_BYTES, raw=str(value).encode(), expected=request.expected,
                          authorized=authorized, temp_prefix=".long-output-")
    return result.committed and result.verified
