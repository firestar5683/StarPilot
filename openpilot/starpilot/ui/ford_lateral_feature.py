"""One saved Ford enum shared by Galaxy and the native feature presentation."""
from opendbc.bluepilot_lateral.hosts.starpilot import supported
from openpilot.starpilot.car.ford.lateral_preferences import KEY, CHOICES, read_choice
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.ui.feature_settings_state import FeatureRow


class FordLateralFeature:
  def __init__(self, owner):
    self.owner = owner

  def capability(self):
    cp = self.owner.vehicle_params()
    try:
      if cp is None or not supported(cp):
        return None
      return (str(cp.carFingerprint), int(cp.flags), int(cp.alternativeExperience), bool(cp.openpilotLongitudinalControl),
              bool(cp.pcmCruise), str(cp.steerControlType), bool(cp.passive), bool(cp.dashcamOnly), bool(cp.notCar),
              tuple((str(c.safetyModel), int(c.safetyParam)) for c in cp.safetyConfigs))
    except (AttributeError, TypeError, ValueError, OverflowError):
      return None

  def dependencies(self):
    values = []
    for key in ("SafeMode", "AlwaysOnLateral"):
      raw, readable = read_saved(self.owner.params, key, 8)
      if not readable or raw not in (None, b"0"):
        return None
      values.append((key, raw))
    return tuple(values)

  def rows(self, parked):
    capability = self.capability()
    if capability is None:
      return ()
    value, raw, readable, valid = read_choice(self.owner.params)
    dependencies = self.dependencies()
    return (FeatureRow(KEY, "Ford steering controller", CHOICES[value] if valid else "Invalid saved choice", raw,
                       choices=tuple(CHOICES.values()), available=parked and self.owner.authority("parked_preferences") and
                       readable and dependencies is not None, capability=capability,
                       dependencies=dependencies or (), repair_value="" if valid else CHOICES[0], default_value=CHOICES[0],
                       reason="Applies next drive. BluePilot angle is available with normal cruise control on supported Ford vehicles."),)

  def apply(self, request):
    value = next((code for code, label in CHOICES.items() if label == request.value), None)
    if (request.key != KEY or value is None or request.related_source is not None or request.display_unit or request.direction):
      return False

    def authorized():
      capability = self.capability()
      _, raw, readable, valid = read_choice(self.owner.params)
      dependencies = self.dependencies()
      return (self.owner.authority("parked_preferences") and bool(request.vehicle_fingerprint) and
              self.owner.vehicle_fingerprint() == request.vehicle_fingerprint and capability is not None and
              capability == request.capability and dependencies is not None and dependencies == request.dependencies and
              readable and raw == request.expected and (valid or value == 0))

    result = commit_exact(self.owner.params, key=KEY, max_bytes=8, raw=str(value).encode(), expected=request.expected,
                          authorized=authorized, temp_prefix=".ford-lateral-")
    return result.committed and result.verified
