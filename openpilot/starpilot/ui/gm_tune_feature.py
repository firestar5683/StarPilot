from opendbc.car.gm.long_tune import CONFIGURABLE_ACC_TUNE_CARS, VOLT_TUNE_CARS, tune_options
from openpilot.starpilot.car.gm.tune_preferences import KEY, CHOICES, read_choice
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.ui.feature_settings_state import FeatureRow


class GmTuneFeature:
  def __init__(self, owner):
    self.owner = owner

  def capability(self):
    owner = self.owner
    cp = owner.vehicle_params()
    try:
      if cp is None or cp.brand != "gm" or cp.notCar:
        return None
      configured = bool(owner.configuration_vehicle())
      if configured and cp.carFingerprint in VOLT_TUNE_CARS:
        options = (0, 2)
      elif configured and cp.carFingerprint in CONFIGURABLE_ACC_TUNE_CARS:
        options = (0, 1)
      else:
        options = tune_options(cp)
      if len(options) < 2:
        return None
      return (str(cp.carFingerprint), configured, bool(cp.openpilotLongitudinalControl), bool(cp.pcmCruise),
              bool(cp.passive), bool(cp.dashcamOnly), int(cp.flags), int(cp.alternativeExperience),
              tuple((str(c.safetyModel), int(c.safetyParam)) for c in cp.safetyConfigs), options)
    except (AttributeError, TypeError, ValueError, OverflowError):
      return None

  def rows(self, parked):
    capability = self.capability()
    if capability is None:
      return ()
    value, raw, readable, valid = read_choice(self.owner.params)
    options = capability[-1]
    applicable = valid and value in options
    reason = ("Vehicle Default preserves the vehicle's normal tune. ACC Tune softens low-speed acceleration and adjusts the braking handoff."
              if 1 in options else
              "Vehicle Default preserves the vehicle's normal tune. Volt Tune changes speed response and assistance when moving away from a stop.")
    if valid and not applicable:
      reason = "The saved tune belongs to a different vehicle. Vehicle Default is used until you choose an applicable tune."
    if not valid:
      reason = "Restore Vehicle Default to repair this saved choice." if readable else "Saved choice cannot be read."
    timing = " Updates within half a second." if 1 in options else " Applies after the next startup."
    return (FeatureRow(KEY, "Speed Control Tune", CHOICES[value] if valid else "Invalid saved choice", raw,
                       choices=tuple(CHOICES[v] for v in options), available=parked and self.owner.authority("parked_preferences") and readable,
                       capability=capability, repair_value="" if applicable else CHOICES[0], default_value=CHOICES[0],
                       reason=reason + timing),)

  def apply(self, request):
    value = next((code for code, label in CHOICES.items() if label == request.value), None)
    if (request.key != KEY or value is None or request.dependencies or request.related_source is not None or
        request.display_unit or request.direction):
      return False
    owner = self.owner

    def authorized():
      capability = self.capability()
      _, raw, readable, valid = read_choice(owner.params)
      return (owner.authority("parked_preferences") and bool(request.vehicle_fingerprint) and
              owner.vehicle_fingerprint() == request.vehicle_fingerprint and capability is not None and
              capability == request.capability and value in capability[-1] and readable and raw == request.expected and
              (valid or value == 0))

    result = commit_exact(owner.params, key=KEY, max_bytes=8, raw=str(value).encode(), expected=request.expected,
                          authorized=authorized, temp_prefix=".gm-tune-")
    return result.committed and result.verified
