"""Selfdrived's short-lived acknowledgment of the effective conditional mode.

The plannerd proposal is never an applied-mode receipt. Only selfdrived emits
this event after it has chosen and published selfdriveState.experimentalMode.
"""

from dataclasses import dataclass
import re

from openpilot.cereal import messaging
from openpilot.starpilot.conditional_mode.consumer import ConsumerResult
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.status import CHOICES, ModeObservation


VERSION = 1
LIFETIME_NS = 50_000_000
_SESSION = re.compile(r'[0-9a-f]{32}\Z')
_FINGERPRINT = re.compile(r'[0-9a-f]{64}\Z')
_WIRE_CHOICES = {wire: choice for choice, wire in CHOICES.items()}


@dataclass(frozen=True)
class EffectiveModeAck:
  session: str
  sequence: int
  observed_ns: int
  expires_ns: int
  selfdrive_state_ns: int
  drive_id: int
  choice: ModeChoice
  accepted: bool
  effective_experimental: bool
  planner_session: str | None = None
  planner_sequence: int = 0
  fingerprint: str | None = None
  settings_revision: int = 0
  model_ns: int = 0
  reason: str | None = None
  status_code: int = 0


def publish_ack(*, session: str, sequence: int, observed_ns: int, selfdrive_state_ns: int,
                drive_id: int, effective_experimental: bool, result: ConsumerResult,
                accepted_proposal: ModeObservation | None):
  """Create one bounded Event; failed authority cannot retain a prior reason."""
  accepted = (result.accepted is True and accepted_proposal is not None and
              accepted_proposal.override is effective_experimental and
              accepted_proposal.choice in (ModeChoice.CEM, ModeChoice.CCM))
  proposal = accepted_proposal if accepted else None
  event = messaging.new_message('starpilotSelfdriveState', valid=True)
  event.logMonoTime = observed_ns
  event.starpilotSelfdriveState.conditionalModeAck = {
    'version': VERSION, 'sessionId': session, 'sequence': sequence,
    'observedMonoTime': observed_ns, 'validUntilMonoTime': observed_ns + LIFETIME_NS,
    'sourceSelfdriveStateMonoTime': selfdrive_state_ns, 'driveStartMonoTime': drive_id,
    'choice': CHOICES[proposal.choice] if proposal is not None else 'stock',
    'accepted': accepted, 'effectiveExperimental': effective_experimental,
    'plannerSessionId': proposal.session if proposal is not None else '',
    'plannerSequence': proposal.sequence if proposal is not None else 0,
    'settingsFingerprint': proposal.fingerprint if proposal is not None else '',
    'settingsRevision': proposal.settings_revision if proposal is not None else 0,
    'modelMonoTime': proposal.model_ns if proposal is not None else 0,
    'reason': proposal.reason if proposal is not None else '',
    'statusCode': proposal.status_code if proposal is not None else 0,
  }
  return event


def observation(state, now_ns: int) -> EffectiveModeAck | None:
  """Decode the nested receipt; transport and same-frame join are caller-owned."""
  try:
    value = state.conditionalModeAck
    version, sequence = value.version, value.sequence
    observed, expires = value.observedMonoTime, value.validUntilMonoTime
    source, drive = value.sourceSelfdriveStateMonoTime, value.driveStartMonoTime
    session, choice = str(value.sessionId), _WIRE_CHOICES[str(value.choice)]
    accepted, effective = value.accepted, value.effectiveExperimental
    planner_session, planner_sequence = str(value.plannerSessionId), value.plannerSequence
    fingerprint, revision, model = str(value.settingsFingerprint), value.settingsRevision, value.modelMonoTime
    reason, code = str(value.reason), value.statusCode
    if (type(now_ns) is not int or type(version) is not int or version != VERSION or
        type(sequence) is not int or sequence <= 0 or not _SESSION.fullmatch(session) or
        type(observed) is not int or type(expires) is not int or
        not 0 < observed <= now_ns <= expires or expires - observed != LIFETIME_NS or
        type(source) is not int or not 0 < source <= observed or observed - source > LIFETIME_NS or
        type(drive) is not int or type(accepted) is not bool or type(effective) is not bool or
        len(reason) > 64 or type(code) is not int or code > 255):
      return None
    if accepted:
      if (choice not in (ModeChoice.CEM, ModeChoice.CCM) or not 0 < drive <= source or
          not _SESSION.fullmatch(planner_session) or type(planner_sequence) is not int or planner_sequence <= 0 or
          not _FINGERPRINT.fullmatch(fingerprint) or type(revision) is not int or revision <= 0 or
          type(model) is not int or not drive <= model <= observed):
        return None
    elif (choice is not ModeChoice.STOCK or planner_session or planner_sequence or fingerprint or revision or model or reason or code):
      return None
    return EffectiveModeAck(session, sequence, observed, expires, source, drive, choice, accepted, effective,
                            planner_session if accepted else None, planner_sequence, fingerprint if accepted else None,
                            revision, model, reason if accepted else None, code)
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return None
