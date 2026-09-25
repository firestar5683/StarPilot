"""Shared saved controller preference for Galaxy and native driving settings."""

from __future__ import annotations

from dataclasses import replace
import json

from openpilot.starpilot.lateral.controller_selection import (
  DOCUMENT_KEY, LEARNING_OFF_KEY, MAX_DOCUMENT_BYTES, ControllerMode, policy_for, replace_mode, selection_from_bytes,
)
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.lateral.lane_change_preferences import (
  KEY as LANE_CHANGE_KEY, MAX_BYTES as LANE_CHANGE_LIMIT, LaneChangePolicy, decode as decode_lane_change, to_value,
)
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest


CHOICES = ('Stock Controller', 'StarPilot Controller')
MODES = dict(zip(CHOICES, (ControllerMode.STANDARD, ControllerMode.STARPILOT), strict=True))
TUNING_GUIDANCE = "StarPilot's torque controller can provide higher low-speed steering accuracy, but may require additional tuning. Join the StarPilot Discord and open a tuning request: https://firestar.link/discord"
SETUP_ACTION = 'torque_prepare_firestar'
SETUP_QUESTION = 'Change tuning preparation? Turning it off restores your previous steering preferences.'
SETUP_DEFAULTS = {'TurnAssist': b'0', LEARNING_OFF_KEY: b'1', 'LaneCentering': b'0',
                  'LaneCenterOffset': b'0.0', 'LaneCenteringE2EAuthority': b'1.0', 'LaneCenteringPauseOnSignal': b'1'}
SETUP_LIMITS = {**dict.fromkeys(SETUP_DEFAULTS, 128), LANE_CHANGE_KEY: LANE_CHANGE_LIMIT, DOCUMENT_KEY: MAX_DOCUMENT_BYTES}


class ControllerFeature:
  def __init__(self, owner):
    self.params = owner.params
    self.authority = owner.authority
    self.vehicle_fingerprint = owner.vehicle_fingerprint
    self.vehicle_params = owner.vehicle_params

  def capability(self, CP=None) -> tuple | None:
    CP = self.vehicle_params() if CP is None else CP
    if CP is None or CP.notCar:
      return None
    try:
      policy = policy_for(CP)
      if policy is None:
        return None
      tune = CP.lateralTuning.torque
      firmware = tuple((str(fw.ecu), bytes(fw.fwVersion)) for fw in CP.carFw)
      return (str(CP.brand), str(CP.carFingerprint), policy, str(CP.steerControlType),
              str(CP.lateralTuning.which()), bool(CP.passive), bool(CP.dashcamOnly), bool(CP.notCar),
              int(CP.flags), int(CP.alternativeExperience), float(tune.latAccelFactor),
              float(tune.latAccelOffset), float(tune.friction), float(tune.steeringAngleDeadzoneDeg),
              float(CP.steerActuatorDelay), float(CP.steerLimitTimer), str(CP.carVin), firmware)
    except (AttributeError, TypeError, ValueError, OverflowError):
      return None

  def _setup_sources(self) -> dict[str, bytes | None] | None:
    sources = {}
    for key, limit in SETUP_LIMITS.items():
      raw, readable = read_saved(self.params, key, limit)
      if not readable:
        return None
      sources[key] = raw
    return sources

  @staticmethod
  def _setup_values(CP, sources: dict[str, bytes | None]) -> dict[str, bytes]:
    lane_raw = sources[LANE_CHANGE_KEY]
    lane = LaneChangePolicy() if lane_raw is None else decode_lane_change(lane_raw)
    if lane is None:
      raise ValueError('Invalid lane-change preferences')
    # Gap reduction is longitudinal; retain it while resetting lateral behavior.
    lane = replace(LaneChangePolicy(), close_gap=lane.close_gap, close_gap_seconds=lane.close_gap_seconds)
    return {**SETUP_DEFAULTS, LANE_CHANGE_KEY: json.dumps(to_value(lane), sort_keys=True, separators=(',', ':')).encode(),
            DOCUMENT_KEY: replace_mode(sources[DOCUMENT_KEY], CP, ControllerMode.STARPILOT)}

  def setup_row(self) -> FeatureRow | None:
    CP = self.vehicle_params()
    capability = self.capability(CP)
    if capability is None:
      return None
    sources = self._setup_sources()
    valid = sources is not None
    if sources is not None:
      try:
        self._setup_values(CP, sources)
      except (ValueError, TypeError, UnicodeError, OverflowError):
        valid = False
    from openpilot.starpilot.ui.tuning_preparation import KEY, LIMIT, decode
    journal_raw, readable = read_saved(self.params, KEY, LIMIT)
    journal = decode(journal_raw, SETUP_LIMITS)
    active = isinstance(journal, dict) and journal['vehicle'] == str(CP.carFingerprint)
    complete = active and sources == journal['prepared']
    conflict = isinstance(journal, dict) and (journal['vehicle'] != str(CP.carFingerprint) or
      any(raw not in (journal['prior'][key], journal['prepared'][key]) for key, raw in (sources or {}).items()))
    return FeatureRow(SETUP_ACTION, 'Prep My Vehicle for Tuning', 'On' if active else 'Off',
                      journal_raw, choices=('Off', 'On'),
                      available=valid and readable and journal is not False and not conflict and
                                self.authority('parked_preferences') and self.authority('preferences'),
                      reason=('Enable before recording a route for a tuning request on the StarPilot Discord. ' +
                              'Turn off to restore your previous tune.' if not conflict and (not active or complete) else
                              'Preparation was interrupted. Turn off to restore your previous tune.' if not conflict else
                              'Settings changed during preparation; your saved tune has been kept.'),
                      capability=capability, dependencies=tuple((key, raw) for key, raw in (sources or {}).items()))

  def apply_setup(self, request: FeatureSettingsRequest) -> bool:
    from openpilot.starpilot.ui.tuning_preparation import transition
    row = self.setup_row()
    if (row is None or not row.available or request.key != SETUP_ACTION or request.value not in row.choices or
        request.expected != row.source or request.capability != row.capability or request.dependencies != row.dependencies or
        request.vehicle_fingerprint != self.vehicle_fingerprint()):
      return False
    CP = self.vehicle_params()
    sources = dict(row.dependencies)
    try:
      desired = self._setup_values(CP, sources)
    except (ValueError, TypeError, UnicodeError, OverflowError):
      return False
    capability = row.capability
    def authorized():
      return (self.authority('parked_preferences') and self.authority('preferences') and
              self.vehicle_fingerprint() == request.vehicle_fingerprint and self.capability() == capability)
    return transition(self.params, str(CP.carFingerprint), sources, desired, request.expected,
                      request.value == 'On', authorized)

  def row(self) -> FeatureRow | None:
    CP = self.vehicle_params()
    capability = self.capability(CP)
    if capability is None:
      return None
    raw, readable = read_saved(self.params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    selected = selection_from_bytes(CP, raw) if readable else None
    valid = readable and selected is not None and selected.source != 'invalid'
    value = CHOICES[0] if valid and selected.mode == ControllerMode.STANDARD else \
      CHOICES[1] if valid else 'Invalid saved controller choice'
    learning, learning_readable = read_saved(self.params, LEARNING_OFF_KEY, 1)
    learning_valid = learning_readable and learning in (None, b'0', b'1')
    allowed = valid and learning_valid and self.authority('preferences')
    reason = ('Choose the steering controller for your next drive. ' + TUNING_GUIDANCE if valid and learning_valid else
              'Saved steering preferences are unreadable or invalid; no change was made.')
    return FeatureRow(DOCUMENT_KEY, 'Steering Controller', value, raw, CHOICES if valid else (),
                      available=allowed, reason=reason, capability=capability, dependencies=((LEARNING_OFF_KEY, learning),))

  def learning_row(self) -> FeatureRow | None:
    CP = self.vehicle_params()
    capability = self.capability(CP)
    if capability is None:
      return None
    controller, controller_readable = read_saved(self.params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    selection = selection_from_bytes(CP, controller)
    raw, readable = read_saved(self.params, LEARNING_OFF_KEY, 1)
    valid = readable and raw in (None, b'0', b'1') and controller_readable and selection.source != 'invalid'
    starpilot = selection.mode == ControllerMode.STARPILOT
    value = ('Off' if starpilot or raw == b'1' else 'On') if valid else 'Invalid saved preference'
    reason = ('StarPilot uses the vehicle tune. ' + TUNING_GUIDANCE
              if starpilot else 'Saved for the next drive. Turn on only if you want Stock Controller to learn torque values.')
    return FeatureRow(LEARNING_OFF_KEY, 'Automatic Steering Learning', value, raw, ('Off', 'On') if valid else (),
                      available=valid and not starpilot and self.authority('preferences'),
                      reason=reason if valid else 'Saved controller or learning preference is unreadable or invalid.',
                      capability=capability, dependencies=((DOCUMENT_KEY, controller),))

  def apply_learning(self, request: FeatureSettingsRequest) -> bool:
    row = self.learning_row()
    if (row is None or not row.available or request.key != LEARNING_OFF_KEY or request.value not in row.choices or
        request.capability != row.capability or request.expected != row.source or request.dependencies != row.dependencies or
        request.related_source is not None or request.display_unit or request.direction or
        not request.vehicle_fingerprint or request.vehicle_fingerprint != self.vehicle_fingerprint()):
      return False

    def authorized() -> bool:
      current = self.learning_row()
      return (self.vehicle_fingerprint() == request.vehicle_fingerprint and current is not None and current.available and
              current.capability == request.capability and current.dependencies == request.dependencies)

    result = commit_exact(self.params, key=LEARNING_OFF_KEY, max_bytes=1,
                          raw=b'0' if request.value == 'On' else b'1', expected=request.expected,
                          authorized=authorized, temp_prefix='.torque-learning-')
    return result.verified

  def apply(self, request: FeatureSettingsRequest) -> bool:
    if (request.key != DOCUMENT_KEY or request.value not in MODES or request.capability is None or
        request.related_source is not None or request.display_unit or request.direction or
        not request.vehicle_fingerprint or request.vehicle_fingerprint != self.vehicle_fingerprint()):
      return False
    CP = self.vehicle_params()
    if CP is None or request.capability != self.capability(CP):
      return False
    raw, readable = read_saved(self.params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    learning, learning_readable = read_saved(self.params, LEARNING_OFF_KEY, 1)
    if (not readable or raw != request.expected or not self.authority('preferences') or
        not learning_readable or learning not in (None, b'0', b'1') or request.dependencies != ((LEARNING_OFF_KEY, learning),)):
      return False
    try:
      selected = selection_from_bytes(CP, raw)
      if selected.source == 'invalid':
        return False
      encoded = replace_mode(raw, CP, MODES[request.value])
    except (UnicodeError, ValueError, TypeError, OverflowError):
      return False

    def authorized() -> bool:
      current, readable = read_saved(self.params, LEARNING_OFF_KEY, 1)
      return (self.authority('preferences') and self.vehicle_fingerprint() == request.vehicle_fingerprint and
              self.capability() == request.capability and readable and current == learning)

    if learning != b'1' and (MODES[request.value] == ControllerMode.STARPILOT or selected.mode == ControllerMode.STARPILOT):
      def authorize_learning_off() -> bool:
        current, readable = read_saved(self.params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
        return authorized() and readable and current == request.expected

      # Persist the conservative side first, including a return from a default
      # StarPilot choice. An interrupted save can leave learning off, but never
      # enables it or saves StarPilot with an enabled learning preference.
      result = commit_exact(self.params, key=LEARNING_OFF_KEY, max_bytes=1, raw=b'1', expected=learning,
                            authorized=authorize_learning_off, temp_prefix='.torque-learning-')
      if not result.verified:
        return False
      learning = b'1'

    result = commit_exact(self.params, key=DOCUMENT_KEY, max_bytes=MAX_DOCUMENT_BYTES,
                          raw=encoded, expected=request.expected, authorized=authorized,
                          temp_prefix='.lateral-controller-')
    return result.verified
