"""Typed custom child snapshots; legacy Event fields and linear fit unchanged."""

from capnp.lib.capnp import _DynamicStructReader
from openpilot.cereal import custom, messaging
from openpilot.starpilot.flm.adaptive_profile import Parameter, Profile, ReplayValidation, replay_accepts
from openpilot.starpilot.flm.fullrate_collector import ControlEvidence, AppliedEvidence, identity, finite

VERSION = 1
MAX_FIELDS = 8
MAX_IDS = 24


def _string(value, limit=96):
  if type(value) is not str or not value or len(value.encode()) > limit:
    raise ValueError('bounded string')
  return value


def _named_values(values):
  return [{'name': _string(name, 96), 'boolean' if type(value) is bool else 'text' if type(value) is str else 'number': value} for name, value in values]


def _read_named_values(values, bound):
  if len(values) > bound:
    raise ValueError('replay scalar bounds')
  result = []
  for row in values:
    name = _string(str(row.name), 96)
    kind = row.which()
    value = bool(row.boolean) if kind == 'boolean' else _string(str(row.text), 96) if kind == 'text' else float(row.number)
    result.append((name, value))
  return tuple(result)


def write_control(parent, evidence):
  if (
    not isinstance(evidence, ControlEvidence)
    or not identity(evidence.identity)
    or not 1 <= len(evidence.features) <= MAX_FIELDS
    or not all(finite(v) for v in (*evidence.features, evidence.requested, evidence.baseline_prediction))
  ):
    raise ValueError('control evidence')
  parent.learningEvidence = {
    'version': VERSION,
    'identity': evidence.identity,
    'generation': evidence.generation,
    'controlMonoTime': evidence.control_ns,
    'sourceStateMonoTime': evidence.state_ns,
    'domain': _string(evidence.domain),
    'stageRevision': _string(evidence.stage_revision),
    'responseRevision': _string(evidence.response_revision),
    'requested': evidence.requested,
    'features': evidence.features,
    'baselinePrediction': evidence.baseline_prediction,
    'stageSchemaRevision': _string(evidence.stage_schema_revision),
    'stageValues': [{'name': _string(name, 64), 'value': v} for name, v in evidence.stage_values],
    'appliedCoordinates': evidence.applied_coordinates,
    'sourceEpoch': evidence.source_epoch,
    'sourceReceiptMonoTime': evidence.source_receipt_ns,
    'controllerMode': _string(evidence.controller_mode),
    'policy': _string(evidence.policy),
    'baselineRevision': evidence.baseline_revision,
    'baselineValues': evidence.baseline_values,
    'controllerRevision': _string(evidence.controller_revision),
    'replaySnapshot': _named_values(evidence.replay_snapshot),
    'replayInputs': _named_values(evidence.replay_inputs),
    'snapshotSequence': evidence.snapshot_sequence,
    'turnAssist': evidence.turn_assist,
    'appliedParameterNames': evidence.applied_parameter_names,
    'nativeRequired': evidence.native_required,
    'nativeObservedMonoTime': evidence.native_observed_ns,
    'nativeValidUntilMonoTime': evidence.native_expires_ns,
    'nativeAllowed': evidence.native_allowed,
    'nativeIdentity': evidence.native_identity,
    'appliedProfileSequence': evidence.applied_profile_sequence,
    'appliedProfileObservedMonoTime': evidence.applied_profile_observed_ns,
    'appliedProfileValidUntilMonoTime': evidence.applied_profile_expires_ns,
    **{
      name: getattr(evidence, field)
      for name, field in (
        ('enabled', 'enabled'),
        ('manual', 'manual'),
        ('active', 'active'),
        ('valid', 'valid'),
        ('override', 'override'),
        ('fault', 'fault'),
        ('saturated', 'saturated'),
        ('limited', 'limited'),
        ('modelWobble', 'model_wobble'),
        ('controllerChatter', 'controller_chatter'),
      )
    },
  }


def read_control(event):
  if not event.valid:
    raise ValueError('invalid envelope')
  row = event.starpilotLateralState.learningEvidence
  if (
    row.version != VERSION
    or len(row.features) > MAX_FIELDS
    or len(row.appliedCoordinates) > MAX_FIELDS
    or len(row.stageValues) > 40
    or len(row.baselineValues) > 32
    or len(row.appliedParameterNames) > 8
  ):
    raise ValueError('control version or bound')
  return ControlEvidence(
    str(row.identity),
    int(row.generation),
    int(row.controlMonoTime),
    int(row.sourceStateMonoTime),
    str(row.domain),
    str(row.stageRevision),
    str(row.responseRevision),
    float(row.requested),
    tuple(float(v) for v in row.features),
    float(row.baselinePrediction),
    bool(row.enabled),
    bool(row.manual),
    bool(row.active),
    bool(row.valid),
    bool(row.override),
    bool(row.fault),
    bool(row.saturated),
    bool(row.limited),
    bool(row.modelWobble),
    bool(row.controllerChatter),
    str(row.stageSchemaRevision),
    tuple((str(v.name), float(v.value)) for v in row.stageValues),
    tuple(float(v) for v in row.appliedCoordinates),
    str(row.sourceEpoch),
    int(row.sourceReceiptMonoTime),
    str(row.controllerMode),
    str(row.policy),
    str(row.baselineRevision),
    tuple(float(v) for v in row.baselineValues),
    str(row.controllerRevision),
    _read_named_values(row.replaySnapshot, 1024),
    _read_named_values(row.replayInputs, 32),
    int(row.snapshotSequence),
    bool(row.turnAssist),
    tuple(_string(str(name)) for name in row.appliedParameterNames),
    bool(row.nativeRequired),
    int(row.nativeObservedMonoTime),
    int(row.nativeValidUntilMonoTime),
    bool(row.nativeAllowed),
    str(row.nativeIdentity),
    int(row.appliedProfileSequence),
    int(row.appliedProfileObservedMonoTime),
    int(row.appliedProfileValidUntilMonoTime),
  )


def write_applied(parent, evidence):
  if not isinstance(evidence, AppliedEvidence) or not finite(evidence.applied):
    raise ValueError('applied evidence')
  parent.appliedEvidence = {
    'version': VERSION,
    'controlMonoTime': evidence.control_ns,
    'sourceStateMonoTime': evidence.state_ns,
    'appliedMonoTime': evidence.apply_ns,
    'domain': _string(evidence.domain),
    'applied': evidence.applied,
    **{name: getattr(evidence, name) for name in ('valid', 'active', 'override', 'fault', 'limited')},
    'nativeAllowed': evidence.native_allowed,
    'carrierFrame': evidence.carrier_frame,
    'carrierObservedMonoTime': evidence.carrier_observed_ns,
  }
  if evidence.projection is not None:
    from openpilot.starpilot.flm.projection_wire import write_projection

    parent.appliedEvidence.projection = write_projection(evidence.projection)


def _read_projection(value):
  if value.version == 0:
    return None
  from openpilot.starpilot.flm.projection_wire import read_projection

  return read_projection(value)


def read_applied(event):
  if not event.valid:
    raise ValueError('invalid envelope')
  row = event.starpilotCarState.appliedEvidence
  if row.version != VERSION:
    raise ValueError('applied version')
  return AppliedEvidence(
    int(row.controlMonoTime),
    int(row.sourceStateMonoTime),
    int(row.appliedMonoTime),
    str(row.domain),
    float(row.applied),
    bool(row.valid),
    bool(row.active),
    bool(row.override),
    bool(row.fault),
    bool(row.limited),
    bool(row.nativeAllowed),
    _read_projection(row.projection),
    int(row.carrierFrame),
    int(row.carrierObservedMonoTime),
  )


def result_message(result, session, sequence, now_ns, *, replay_validation=None):
  event = messaging.new_message('autoSteeringLearning')
  value = event.autoSteeringLearning.learning
  value.version, value.session, value.sequence = VERSION, _string(session, 64), sequence
  value.observedMonoTime, value.validUntilMonoTime = now_ns, now_ns + 500_000_000
  value.status, value.reason, value.family = 'collecting', 'independent_evidence', 'runtimeProfile'
  profile = None if result is None else result.profile
  if profile is not None:
    if (
      not isinstance(profile, Profile)
      or not identity(profile.identity)
      or not 1 <= len(profile.parameters) == len(profile.coefficients) <= MAX_FIELDS
      or len(profile.train_ids) + len(profile.heldout_ids) > MAX_IDS
    ):
      raise ValueError('profile bound')
    if any(not finite(p.excitation_floor) or p.excitation_floor <= 0 for p in profile.parameters):
      raise ValueError('profile excitation floor')
    if not replay_accepts(replay_validation, profile):
      raise ValueError('actual replay validation required')
    value.status = 'qualifiedFit' if result.status == 'qualified' else 'rejected'
    value.reason = _string(result.reason)
    # Profile's original observation/expiry is copied, never renewed by a4Hz
    # publication. Outer collecting metadata cannot extend its500ms lease.
    value.runtimeProfile = {
      'version': VERSION,
      'identity': profile.identity,
      'sequence': profile.sequence,
      'observedMonoTime': profile.observed_ns,
      'validUntilMonoTime': profile.expires_ns,
      'policy': _string(profile.policy),
      'parameters': [
        {
          'name': _string(p.name),
          'stageRevision': _string(p.stage_revision),
          'low': p.low,
          'high': p.high,
          'maxStep': p.max_step,
          'slewPerS': p.slew_per_s,
          'excitationFloor': p.excitation_floor,
        }
        for p in profile.parameters
      ],
      'coefficients': profile.coefficients,
      'trainIds': [_string(v, 128) for v in profile.train_ids],
      'heldoutIds': [_string(v, 128) for v in profile.heldout_ids],
      'baselineLoss': profile.baseline_loss,
      'candidateLoss': profile.candidate_loss,
      'cohortImprovements': [{'name': _string(name), 'lowerBound': v} for name, v in profile.cohort_improvements],
      'replay': {
        'baselineRevision': _string(replay_validation.baseline_revision),
        'physicalModelRevision': _string(replay_validation.physical_model_revision),
        'noSaturationRegression': replay_validation.no_saturation_regression,
        'noSlewRegression': replay_validation.no_slew_regression,
        'worstCohortImprovement': replay_validation.worst_cohort_improvement,
      },
    }

  elif result is not None:
    value.status = 'rejected' if result.status == 'rejected' else 'collecting'
    value.reason = _string(result.reason)
  event.valid = True
  return event


def read_profile(event):
  if not event.valid:
    return None
  value = event.autoSteeringLearning.learning
  if value.version != VERSION or str(value.family) != 'runtimeProfile' or str(value.status) != 'qualifiedFit':
    return None
  row = value.runtimeProfile
  if (
    row.version != VERSION
    or not identity(str(row.identity))
    or not 1 <= len(row.parameters) == len(row.coefficients) <= MAX_FIELDS
    or not 4 <= len(row.trainIds) <= MAX_IDS
    or not 4 <= len(row.heldoutIds) <= MAX_IDS
    or len(row.trainIds) + len(row.heldoutIds) > MAX_IDS
    or len(row.cohortImprovements) > MAX_IDS
  ):
    return None
  parameters = tuple(
    Parameter(str(p.name), str(p.stageRevision), float(p.low), float(p.high), float(p.maxStep), float(p.slewPerS), float(p.excitationFloor))
    for p in row.parameters
  )
  if any(not finite(p.excitation_floor) or p.excitation_floor <= 0 for p in parameters):
    return None
  return Profile(
    str(row.identity),
    int(row.sequence),
    int(row.observedMonoTime),
    int(row.validUntilMonoTime),
    parameters,
    tuple(float(v) for v in row.coefficients),
    tuple(str(v) for v in row.trainIds),
    tuple(str(v) for v in row.heldoutIds),
    float(row.baselineLoss),
    float(row.candidateLoss),
    tuple((str(v.name), float(v.lowerBound)) for v in row.cohortImprovements),
    str(row.policy),
  )


def read_runtime_admission(event):
  profile = read_profile(event)
  if profile is None:
    return None
  row = event.autoSteeringLearning.learning.runtimeProfile.replay
  validation = ReplayValidation(
    profile,
    str(row.baselineRevision),
    str(row.physicalModelRevision),
    bool(row.noSaturationRegression),
    bool(row.noSlewRegression),
    float(row.worstCohortImprovement),
  )
  return (profile, validation) if replay_accepts(validation, profile) else None


def write_source_receipt(event, source):
  # Shared registry SourceState; read only by separate learner/startup.
  if (
    not identity(source.cp_sha256) or type(source.observed_ns) is not int or not 0 < source.observed_ns <= source.expires_ns <= source.observed_ns + 500_000_000
  ):
    raise ValueError('source receipt bounds')
  if source.enabled and (not identity(source.source_epoch) or not source.reset):
    raise ValueError('enabled source receipt identity')
  event.autoSteeringLearning.learning.sourceReceipt = {
    'version': VERSION,
    'enabled': source.enabled,
    'manual': source.manual,
    'resetGeneration': source.reset,
    'sourceEpoch': source.source_epoch,
    'observedMonoTime': source.observed_ns,
    'validUntilMonoTime': source.expires_ns,
    'cpSha256': source.cp_sha256,
    'calibrationBasis': source.calibration,
  }


def _read_native_source_receipt(row, now_ns, cp_sha256, source_type):
  if row.version != VERSION:
    return None
  cp = str(row.cpSha256)
  if cp != cp_sha256 or not identity(cp):
    return None
  observed = row.observedMonoTime
  if not 0 < observed <= now_ns:
    return None
  expires = row.validUntilMonoTime
  if not now_ns <= expires <= observed + 500_000_000:
    return None
  enabled = bool(row.enabled)
  if enabled:
    epoch = str(row.sourceEpoch)
    if not identity(epoch):
      return None
    reset = str(row.resetGeneration)
    if not reset:
      return None
  else:
    reset = str(row.resetGeneration)
  if len(reset) > 64:
    return None
  basis = row.calibrationBasis
  if len(basis) != 3:
    return None
  calibration = []
  for item in basis:
    value = float(item)
    if not finite(value):
      return None
    calibration.append(value)
  manual = bool(row.manual)
  if not enabled:
    epoch = str(row.sourceEpoch)
  return source_type(enabled, manual, reset, epoch, observed, expires, cp, tuple(calibration))


def read_source_receipt(event, *, now_ns, cp_sha256):
  from openpilot.starpilot.flm.runtime_adapter_registry import SourceState

  if not event.valid:
    return None
  row = event.autoSteeringLearning.learning.sourceReceipt
  if (type(row) is _DynamicStructReader and row.schema == custom.AutomaticLearningSourceReceipt.schema
      and type(now_ns) is int and type(cp_sha256) is str):
    return _read_native_source_receipt(row, now_ns, cp_sha256, SourceState)
  if (
    row.version != VERSION
    or str(row.cpSha256) != cp_sha256
    or not identity(str(row.cpSha256))
    or not 0 < row.observedMonoTime <= now_ns <= row.validUntilMonoTime <= row.observedMonoTime + 500_000_000
    or bool(row.enabled)
    and (not identity(str(row.sourceEpoch)) or not str(row.resetGeneration))
    or len(str(row.resetGeneration)) > 64
    or len(row.calibrationBasis) != 3
    or not all(finite(float(value)) for value in row.calibrationBasis)
  ):
    return None
  return SourceState(
    bool(row.enabled),
    bool(row.manual),
    str(row.resetGeneration),
    str(row.sourceEpoch),
    int(row.observedMonoTime),
    int(row.validUntilMonoTime),
    str(row.cpSha256),
    tuple(float(value) for value in row.calibrationBasis),
  )
