"""Explicit controller-bound steering response edits in the shared torque document."""

import json

from openpilot.starpilot.lateral.bolt_policy import supported_cp
from openpilot.starpilot.lateral.controller_selection import DOCUMENT_KEY as SELECTION_KEY, ControllerMode, selection_from_bytes
from openpilot.starpilot.lateral.torque_settings import (DOCUMENT_KEY, GainBasis, FieldChoice, parse_document, replace_gain, serialize_document)
from openpilot.starpilot.ui.feature_settings_state import FeatureRow


class GainFeature:
  def __init__(self, owner):
    self.owner = owner

  def _basis(self, capability):
    cp = self.owner.vehicle_params()
    if cp is None or not supported_cp(cp) or capability != self.owner._capability("torque"):
      raise ValueError("Qualified vehicle unavailable")
    if not self.owner._readable(SELECTION_KEY):
      raise ValueError("Controller selection unavailable")
    selection = selection_from_bytes(cp, self.owner._raw(SELECTION_KEY))
    if selection.source == "invalid":
      raise ValueError("Controller selection needs review")
    if selection.mode == ControllerMode.STARPILOT:
      table = ((0,), (0.6,))
    else:
      from openpilot.selfdrive.controls.lib.latcontrol_torque import INTERP_SPEEDS, KP_INTERP
      table = (tuple(INTERP_SPEEDS), tuple(KP_INTERP))
    return GainBasis(selection.mode.value, table, (capability[5], capability[6], capability[7]))

  def rows(self, capability, profiles, raw, allowed, repair_allowed):
    try:
      basis = self._basis(capability)
    except (AttributeError, ValueError, TypeError, OverflowError):
      return (FeatureRow("", "Steering response", "Controller selection unavailable"),)
    profile = profiles.get(capability[0])
    choice = profile.proportional_gain if profile is not None else FieldChoice()
    dependencies = self.owner._dependents("AdvancedLateralTune", "ForceAutoTuneOff", SELECTION_KEY)
    if choice.mode == "custom" and profile.gain_basis != basis:
      return (FeatureRow("torque_gain_rebase", "Review steering response",
                         "Controller or vehicle tune changed. Confirm this response for the selected controller.", raw,
                         available=repair_allowed, capability=capability, dependencies=dependencies),
              FeatureRow("torque:gain:mode", "Steering response source", "Custom", raw,
                         choices=("Selected controller",), available=allowed, capability=capability, dependencies=dependencies))
    rows = [FeatureRow("", "Manual steering response",
                       "Enable before the next drive. Higher values respond more strongly; lower values respond more gently.")]
    rows.append(FeatureRow("torque:gain:mode", "Steering response source",
                           "Custom" if choice.mode == "custom" else "Selected controller", raw,
                           choices=("Selected controller", "Custom"), available=allowed, capability=capability, dependencies=dependencies))
    if choice.mode == "custom":
      rows.append(FeatureRow("torque:gain:value", "Steering response", f"{choice.custom_value:.2f}", raw,
                             minimum=0.3, maximum=0.9, step=0.05, available=allowed,
                             capability=capability, dependencies=dependencies))
    return tuple(rows)

  def apply(self, request):
    owner = self.owner
    def current():
      return (owner.authority("torque") and request.vehicle_fingerprint == owner.vehicle_fingerprint() and
              request.capability is not None and request.capability == owner._capability("torque") and
              {"AdvancedLateralTune", "ForceAutoTuneOff", SELECTION_KEY}.issubset(key for key, _ in request.dependencies) and
              owner._readable(DOCUMENT_KEY) and owner._raw(DOCUMENT_KEY) == request.expected and
              all(owner._readable(key) and owner._raw(key) == value for key, value in request.dependencies))
    try:
      if not current() or request.expected is None:
        return False
      basis = self._basis(request.capability)
      profiles = parse_document(request.expected)
      prior = profiles.get(request.capability[0])
      choice = prior.proportional_gain if prior is not None else FieldChoice()
      review = request.key == "torque_gain_rebase"
      if review:
        if not request.confirmation or not owner.authority("parked_preferences") or choice.mode != "custom":
          return False
        mode, value = choice.mode, choice.custom_value
      elif request.key == "torque:gain:mode":
        if request.value == "Selected controller":
          mode, value = "source", None
        elif request.value == "Custom":
          mode, value = "custom", choice.custom_value if choice.custom_value is not None else 0.6
        else:
          return False
      elif request.key == "torque:gain:value" and choice.mode == "custom":
        mode, value = "custom", float(request.value)
      else:
        return False
      updated = replace_gain(profiles, request.capability[0], basis, mode, value, review=review)
      if not current() or self._basis(request.capability) != basis or review and not owner.authority("parked_preferences"):
        return False
      owner.params.put(DOCUMENT_KEY, json.loads(serialize_document(updated)), block=True)
      return parse_document(owner._raw(DOCUMENT_KEY)) == updated
    except (OSError, ValueError, TypeError, AttributeError, OverflowError, UnicodeError):
      return False
