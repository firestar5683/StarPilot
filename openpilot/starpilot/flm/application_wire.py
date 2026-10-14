"""Actual controller application acknowledgement, distinct from producer fit."""

from openpilot.starpilot.flm.adaptive_profile import ApplicationOutcome

VERSION = 1
MAX_AGE_NS = 500_000_000


def write_application(envelope, outcome):
  if not isinstance(outcome, ApplicationOutcome):
    return
  envelope.learningApplication = {
    'version': VERSION,
    'identity': outcome.identity,
    'profileSequence': outcome.profile_sequence,
    'observedMonoTime': outcome.observed_ns,
    'status': outcome.status,
    'actualCoordinates': outcome.actual_coordinates,
    'reason': outcome.reason,
    'baselineRevision': outcome.baseline_revision,
    'physicalModelRevision': outcome.physical_model_revision,
  }


def read_application(envelope, *, now_ns):
  row = envelope.learningApplication
  identity = str(row.identity)
  if (
    int(row.version) != VERSION
    or len(identity) != 64
    or any(c not in '0123456789abcdef' for c in identity)
    or type(now_ns) is not int
    or not 0 < int(row.observedMonoTime) <= now_ns <= int(row.observedMonoTime) + MAX_AGE_NS
    or str(row.status) not in ('collecting', 'applied', 'paused', 'rejected')
    or len(row.actualCoordinates) > 8
    or len(str(row.reason)) > 96
    or len(str(row.baselineRevision)) > 96
    or len(str(row.physicalModelRevision)) > 96
  ):
    return None
  values = tuple(float(v) for v in row.actualCoordinates)
  import math

  if not all(math.isfinite(v) for v in values):
    return None
  if str(row.status) == 'applied' and (
    not values or not any(v != 0 for v in values) or not row.profileSequence or not row.baselineRevision or not row.physicalModelRevision
  ):
    return None
  return ApplicationOutcome(
    identity,
    int(row.profileSequence),
    int(row.observedMonoTime),
    str(row.status),
    values,
    str(row.reason),
    str(row.baselineRevision),
    str(row.physicalModelRevision),
  )
