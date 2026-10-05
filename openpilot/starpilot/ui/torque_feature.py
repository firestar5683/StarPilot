"""Native Torque editor adapter; strict numeric policy lives in the lateral domain."""

from __future__ import annotations

from dataclasses import replace
import json

from openpilot.starpilot.lateral.torque_supported import BOLT_VEHICLES
from openpilot.starpilot.lateral.torque_settings import (
  DOCUMENT_KEY, LEGACY_KEYS, FieldChoice, LegacyMode, PlatformProfile, bounds as torque_bounds,
  interpret_legacy, parse_document, replace_field, resolve_document, serialize_document,
)
from openpilot.starpilot.ui.feature_settings_state import FeaturePage, FeatureRow, FeatureSettingsRequest, TORQUE_CONFIRM_ACTIONS

TORQUE_NUMBERS = LEGACY_KEYS


class TorqueFeature:
  def __init__(self, owner):
    self.owner = owner
    self.params = owner.params
    self.authority = owner.authority
    self.vehicle_fingerprint = owner.vehicle_fingerprint
    self._capability = owner._capability
    self._raw = owner._raw
    self._readable = owner._readable
    self._dependents = owner._dependents

  @staticmethod
  def _legacy_label(mode: LegacyMode, saved: float | None) -> str:
    if mode == LegacyMode.ABSENT:
      return "No saved override"
    if saved is None:
      raise ValueError("Missing saved torque value")
    return f"Stock tracked ({saved:.2f})" if mode == LegacyMode.STOCK else f"Saved custom ({saved:.2f})"

  def _torque_values(self, capability: tuple | None) -> tuple[bool, tuple[FeatureRow, ...]]:
    readings = {key: self._raw(key) for key in TORQUE_NUMBERS}
    try:
      if capability is None:
        raise ValueError("Vehicle unavailable")
      legacy = interpret_legacy(readings, (capability[5], capability[6], capability[7]))
      statuses = (self._legacy_label(legacy.factor_mode, legacy.factor_saved),
                  self._legacy_label(legacy.friction_mode, legacy.friction_saved))
      valid = True
    except (ValueError, OverflowError):
      statuses = tuple("Invalid saved value" if readings[key] is not None else "No saved override"
                       for key in TORQUE_NUMBERS[:2])
      valid = False
    return valid, tuple(FeatureRow(key, "Lateral acceleration" if key == "SteerLatAccel" else "Friction",
                                   status, readings[key], reason="Legacy saved value; adopt to edit")
                        for key, status in zip(TORQUE_NUMBERS[:2], statuses, strict=True))

  def rows(self, capability: tuple | None, allowed: bool, *, repair_allowed: bool | None = None) -> tuple[bool, tuple[FeatureRow, ...]]:
    repair_allowed = allowed if repair_allowed is None else repair_allowed
    raw = self._raw(DOCUMENT_KEY)
    bolt = capability is not None and capability[0] in BOLT_VEHICLES
    try:
      if capability is None:
        return False, (FeatureRow("", "Torque profile", "Select a supported vehicle in Vehicle settings",
                                  page=FeaturePage.VEHICLE, available=True),)
      fingerprint = capability[0]
      basis = (capability[5], capability[6], capability[7])
      if raw is None:
        legacy = interpret_legacy({key: None if fingerprint in BOLT_VEHICLES else self._raw(key) for key in TORQUE_NUMBERS}, basis)
        profiles = {fingerprint: PlatformProfile(basis,
                    FieldChoice("custom", legacy.factor) if legacy.factor is not None and fingerprint not in BOLT_VEHICLES else FieldChoice(),
                    FieldChoice("custom", legacy.friction) if legacy.friction is not None and fingerprint not in BOLT_VEHICLES else FieldChoice())}
      else:
        profiles = parse_document(raw)
      factor, friction, review = resolve_document(profiles, fingerprint, basis)
    except (ValueError, UnicodeError, OverflowError):
      reset = FeatureRow("torque_reset", "Reset invalid torque profiles", "", raw,
                         available=repair_allowed and raw is not None and self._readable(DOCUMENT_KEY), capability=capability,
                         dependencies=self._dependents("ForceAutoTuneOff", *TORQUE_NUMBERS))
      return False, (FeatureRow("", "Torque profile", "Invalid saved values; supplied tune in use"), reset)
    if review:
      profile = profiles[fingerprint]
      if bolt and profile.factor.mode == "custom":
        reset = FeatureRow("torque_reset_profile", "Reset this model's tuning", "Reset to configure friction", raw,
                           available=repair_allowed, capability=capability,
                           dependencies=self._dependents("AdvancedLateralTune", "ForceAutoTuneOff"))
        return False, (FeatureRow("", "Friction tuning paused",
                                  "This saved tune includes a lateral-acceleration adjustment that this Bolt editor cannot apply. " +
                                  "Reset this model’s tune to configure friction."), reset)
      details = []
      summary = []
      for field, label, current, choice in (("factor", "Lateral acceleration", basis[0], profile.factor),
                                            ("friction", "Friction", basis[2], profile.friction)):
        low, high = torque_bounds(basis, field)
        saved = f"{choice.custom_value:.4f}" if choice.mode == "custom" and choice.custom_value is not None else "Vehicle/learned"
        details.append(FeatureRow("", label, f"Saved {saved} · vehicle {current:.4f} · range {low:.4f}–{high:.4f}"))
        summary.append(f"{label} {saved}")
      rebase = FeatureRow("torque_rebase", "Review changed vehicle tune", ", ".join(summary), raw,
                          available=repair_allowed, capability=capability,
                          dependencies=self._dependents("ForceAutoTuneOff", *TORQUE_NUMBERS))
      reset = FeatureRow("torque_reset_profile", "Use vehicle values for this model", "", raw,
                         available=repair_allowed, capability=capability,
                         dependencies=self._dependents("ForceAutoTuneOff", *TORQUE_NUMBERS))
      return False, (FeatureRow("", "Torque profile", "Vehicle tune changed; custom values paused"), *details, rebase, reset)
    profile = profiles.get(fingerprint, PlatformProfile(basis, FieldChoice(), FieldChoice()))
    rows: list[FeatureRow] = []
    for field, label, active in (("factor", "Lateral acceleration", factor), ("friction", "Friction", friction)):
      if bolt and field == "factor":
        continue
      choice = profile.factor if field == "factor" else profile.friction
      low, high = torque_bounds(basis, field)
      dependencies = self._dependents("ForceAutoTuneOff", *TORQUE_NUMBERS)
      supplied = basis[0 if field == "factor" else 2]
      value = active if active is not None else supplied
      displayed = str(round(value, 8))
      rows.append(FeatureRow(f"torque:{field}:value", "Lat Accel" if field == "factor" else "Friction", displayed, raw,
                             step=0.05 if field == "factor" else 0.01, minimum=low, maximum=high,
                             available=allowed, capability=capability, dependencies=dependencies,
                             reason="Supplied tune; edits saved for the next drive" if active is None else "Custom value; saved for the next drive"))
      rows.append(FeatureRow(f"torque:{field}:reset", label + " — Reset to Default", "", raw,
                             available=allowed and active is not None, repair_value="Reset",
                             capability=capability, dependencies=dependencies))
    if bolt:
      rows.insert(0, FeatureRow("", "Manual friction", "Enable manual adjustments before the next drive. Saved friction changes then apply during that drive."))
      from openpilot.starpilot.ui.gain_feature import GainFeature
      rows.extend(GainFeature(self.owner).rows(capability, profiles, raw, allowed, repair_allowed))
    return True, tuple(rows)

  def apply(self, request: FeatureSettingsRequest) -> bool:
    """One guarded document replacement; the presentation never writes Params."""
    if request.key == "torque_gain_rebase" or request.key.startswith("torque:gain:"):
      from openpilot.starpilot.ui.gain_feature import GainFeature
      return GainFeature(self.owner).apply(request)
    if request.key in TORQUE_CONFIRM_ACTIONS and not self.authority("parked_preferences"):
      return False
    if (request.vehicle_fingerprint != self.vehicle_fingerprint() or not self.authority("torque") or
        request.capability is None or request.capability != self._capability("torque") or
        self._raw(DOCUMENT_KEY) != request.expected or not self._readable(DOCUMENT_KEY) or
        any(self._raw(name) != raw or not self._readable(name) for name, raw in request.dependencies)):
      return False
    capability = request.capability
    fingerprint = capability[0]
    basis = (capability[5], capability[6], capability[7])
    try:
      if request.key == "torque_adopt":
        if not request.confirmation or request.expected is not None:
          return False
        profiles: dict[str, PlatformProfile] = {fingerprint: PlatformProfile(basis, FieldChoice(), FieldChoice())}
      elif request.key == "torque_reset":
        if not request.confirmation or request.expected is None:
          return False
        try:
          parse_document(request.expected)
          return False
        except (ValueError, UnicodeError, OverflowError):
          profiles = {}
      else:
        if request.expected is None:
          legacy = interpret_legacy({key: None if fingerprint in BOLT_VEHICLES else self._raw(key) for key in TORQUE_NUMBERS}, basis)
          profiles = {fingerprint: PlatformProfile(basis,
                      FieldChoice("custom", legacy.factor) if legacy.factor is not None and fingerprint not in BOLT_VEHICLES else FieldChoice(),
                      FieldChoice("custom", legacy.friction) if legacy.friction is not None and fingerprint not in BOLT_VEHICLES else FieldChoice())}
        else:
          profiles = parse_document(request.expected)
        _, _, review = resolve_document(profiles, fingerprint, basis)
        if request.key == "torque_reset_profile":
          if not request.confirmation or not review:
            return False
          amended = dict(profiles)
          amended[fingerprint] = PlatformProfile(basis, FieldChoice(), FieldChoice())
          profiles = amended
        elif request.key == "torque_rebase":
          if not request.confirmation or not review:
            return False
          prior = profiles[fingerprint]
          updated = replace(prior, basis=basis)
          amended = dict(profiles)
          amended[fingerprint] = updated
          resolve_document(amended, fingerprint, basis)
          profiles = amended
        elif request.key.startswith("torque:"):
          if review:
            return False
          _, field, part = request.key.split(":")
          if fingerprint in BOLT_VEHICLES and field == "factor":
            return False
          if field not in ("factor", "friction") or part not in ("mode", "value", "reset"):
            return False
          profile = profiles.get(fingerprint)
          choice = getattr(profile, field) if profile else FieldChoice()
          if part == "mode":
            if request.value == "Vehicle/learned":
              profiles = replace_field(profiles, fingerprint, basis, field, "source", None)
            elif request.value == "Custom":
              candidate = choice.custom_value if choice.custom_value is not None else basis[0 if field == "factor" else 2]
              low, high = torque_bounds(basis, field)
              if not low <= candidate <= high:
                candidate = basis[0 if field == "factor" else 2]
              profiles = replace_field(profiles, fingerprint, basis, field, "custom", candidate)
            else:
              return False
          elif part == "reset" and request.value == "Reset":
            profiles = replace_field(profiles, fingerprint, basis, field, "source", None)
          elif part == "value":
            value = float(request.value)
            supplied = basis[0 if field == "factor" else 2]
            mode = "source" if round(value, 2) == round(supplied, 2) else "custom"
            profiles = replace_field(profiles, fingerprint, basis, field, mode, value if mode == "custom" else None)
          else:
            return False
        else:
          return False
      encoded = serialize_document(profiles)
      # Fresh authority and source evidence immediately before the one Params replacement.
      if (not self.authority("torque") or self.vehicle_fingerprint() != request.vehicle_fingerprint or
          self._capability("torque") != capability or not self._readable(DOCUMENT_KEY) or
          self._raw(DOCUMENT_KEY) != request.expected or
          request.key in TORQUE_CONFIRM_ACTIONS and not self.authority("parked_preferences") or
          any(not self._readable(name) or self._raw(name) != raw for name, raw in request.dependencies)):
        return False
      self.params.put(DOCUMENT_KEY, json.loads(encoded), block=True)
      saved = self._raw(DOCUMENT_KEY)
      return saved is not None and parse_document(saved) == profiles
    except (OSError, ValueError, TypeError, OverflowError, UnicodeError):
      return False
