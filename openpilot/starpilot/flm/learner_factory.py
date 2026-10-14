"""Raw parent recordings, one bounded child fit, real selected-controller replay."""

import base64
from itertools import islice
from dataclasses import asdict
from openpilot.starpilot.flm.runtime_adapter_registry import (
  selected_descriptor,
  selected_identity,
  baseline_revision,
  baseline_values,
  canonical_physical_context,
  physical_model_revision,
)
from openpilot.starpilot.flm.torque_adapter import Objective
from openpilot.starpilot.flm.controller_replay import (
  SelectedControllerFactory,
  ControllerReplay,
  ReplayFrame,
  snapshot_from_values,
  pack_primitive_snapshot,
  unpack_primitive_snapshot,
  factory_from_snapshot,
)

RAW_TORQUE = 'torque-selected-stage-snapshot-v1'
FF_KEYS = tuple(('feedforward', speed, phase) for speed in ('low', 'high') for phase in ('steady', 'turn_in', 'unwind'))


def objective_key(evidence):
  stage = dict(evidence.stage_values)
  phase = stage['setpoint'] * stage['jerk']
  return ('feedforward', 'low' if stage['speed'] < 25 else 'high', 'steady' if abs(phase) < 0.03 else 'turn_in' if phase > 0 else 'unwind')


def collection_keys(evidence):
  key = objective_key(evidence)
  # Ten bounded fit metadata entries cover six FF cells and four centre bands;
  # they all share this single primitive recorder and child process.
  return FF_KEYS if key[0] == 'feedforward' else (key,)


def _frame(evidence):
  stage = dict(evidence.stage_values)
  return ReplayFrame(
    evidence.control_ns,
    evidence.replay_inputs,
    evidence.requested,
    evidence.applied_coordinates,
    frame_sequence=int(dict(evidence.replay_inputs)['control_frame']),
    actual_lac_command=stage['selected_command'],
    torque_values=tuple((key, stage[key]) for key in ('effective_factor', 'offset', 'friction', 'pid_pos_limit', 'pid_neg_limit')),
    actual_stage_residual=(stage['actual_delta_ff'], stage['actual_delta_threshold']),
    centre_values=(stage.get('centre_threshold_delta', 0.0), stage.get('centre_extra_deadband_deg', 0.0)),
    desired_physical_accel=stage['setpoint'],
    healthy=evidence.valid and not evidence.fault and not evidence.override,
    manual=evidence.manual,
    limited=evidence.limited,
    applied_parameter_names=tuple(evidence.applied_parameter_names),
  )


class TorqueCollectionAdapter:
  command_domain = 'normalized_torque'
  raw_collection = True

  def __init__(self, cp, evidence, key=None):
    if evidence.stage_schema_revision != RAW_TORQUE:
      raise ValueError('actual raw stage trace')
    factory = SelectedControllerFactory(cp, evidence.controller_mode, turn_assist=evidence.turn_assist)
    controller, vm = factory.create()
    if evidence.replay_snapshot:
      from openpilot.starpilot.flm.controller_replay import restore_snapshot

      restore_snapshot(controller, vm, snapshot_from_values(evidence.replay_snapshot))
    descriptor = selected_descriptor(cp, factory.interface_class(cp), controller)
    if (
      descriptor is None
      or descriptor.policy != evidence.policy
      or descriptor.controller_revision != evidence.controller_revision
      or selected_identity(descriptor, evidence.source_epoch, evidence.baseline_revision) != evidence.identity
      or baseline_revision(descriptor, baseline_values(controller)) != evidence.baseline_revision
    ):
      raise ValueError('actual selected baseline identity')
    self.identity, self.baseline_revision = evidence.identity, evidence.baseline_revision
    self.source_epoch, self.generation = evidence.source_epoch, evidence.generation
    self.factory = factory
    self.objective = Objective('feedforward', 'low', 'steady')
    self.centres = {}
    self.select_objective(key or objective_key(evidence))
    self.replay = ControllerReplay(
      factory,
      Objective('feedforward', 'low', 'steady'),
      identity=evidence.identity,
      baseline_revision=evidence.baseline_revision,
      model_revision='raw-child-v1',
    )
    self.snapshot_sequence = 0
    self.model = None
    self.model_cutoff_ns = 0
    self.fit_profile = None
    self.current_physical_valid = False
    self.last_physical_ns = 0

  def select_objective(self, key):
    self.key = tuple(key)
    if key not in FF_KEYS:
      raise ValueError('selected FF objective')
    self.objective = Objective(*key)

  def prepare_control(self, evidence):
    if (
      evidence.identity != self.identity
      or evidence.source_epoch != self.source_epoch
      or evidence.generation != self.generation
      or evidence.stage_schema_revision != RAW_TORQUE
    ):
      return None
    if evidence.replay_snapshot:
      if evidence.snapshot_sequence <= self.snapshot_sequence:
        return None
      self.replay.checkpoint(evidence.control_ns, snapshot_from_values(evidence.replay_snapshot))
      self.snapshot_sequence = evidence.snapshot_sequence
    if not self.snapshot_sequence or evidence.snapshot_sequence != self.snapshot_sequence:
      return None
    # Primitive recording only. No controller updates, fitting or differences.
    if not self.replay.record_actual_frame(_frame(evidence)):
      return None
    return evidence

  def record_actual_carrier(self, output):
    return self.replay.emissions.record_carrier(output)

  def record_actual_emission(self, control, output):
    return self.replay.emissions.record(control, output)

  def parameters(self):
    return self.objective.parameters

  def prior_schemas(self):
    return (tuple(self.parameters()),)

  def select_prior_schema(self, parameters):
    return tuple(parameters) == tuple(self.parameters())

  def required_cohorts(self):
    if self.key[0] == 'centre':
      return (f'{self.key[1]}.mixed.center',)
    return self.objective.required_cohorts

  def physical_observable(self, value):
    return value.speed_mps >= (2 if self.key[0] == 'centre' else 15) and abs(value.roll_rad) < 0.3

  def cohort(self, control, physical):
    if self.model is not None and 'applied_command' in physical and 'response_ns' in physical:
      applied = -float(physical['applied_command'])
      observed = float(physical['lateral_accel'])
      predicted = self.model.slope * applied + self.model.intercept
      self.current_physical_valid = bool(
        self.model.command_low <= applied <= self.model.command_high and abs(predicted - observed) <= max(0.01, 3 * self.model.heldout_rmse)
      )
      self.last_physical_ns = int(physical['response_ns'])
    else:
      self.current_physical_valid = False
    stage = dict(control.stage_values)
    key = objective_key(control)
    if key[0] == 'centre':
      facade = self.centres.get(key[1])
      return facade.cohort(control, physical) if facade is not None else None
    if abs(stage['setpoint']) < 0.25:
      return None
    side = 'left' if stage['setpoint'] > 0 else 'right'
    return f'{key[1]}.{side}.{key[2]}'

  def can_seal_raw(self, points):
    return len(points) >= 80

  def fit_job_snapshot(self, blocks, now_ns, sequence, prior, *, control, output, physical_context):
    # Actual independent maneuvers remain whole; no row thinning to fit IPC.
    if self.key[0] == 'centre':
      # Item2 joins FF/PID only. Centre's raw-command physical gates cannot
      # borrow a delivered-encoder model until their separate join is qualified.
      return None
    selected = tuple(block for block in blocks if block.cohort in self.objective.required_cohorts)
    if len(selected) < 16:
      return None
    selected = selected[-24:]
    if any(any(point.control.applied_coordinates) for block in selected for point in block.samples):
      # Refit only genuine neutral-baseline evidence. A retained admitted fit
      # has its separate fresh physical-response/replay renewal path.
      return None
    from opendbc.car.steering_projection import projection_to_dict

    # asdict preserves TorqueProjection's NamedTuple class. Export only its
    # existing validated primitive wire mapping, including every original field.
    block_rows = tuple(asdict(block) for block in selected)
    for block in block_rows:
      for point in block['samples']:
        point['output']['projection'] = projection_to_dict(point['output']['projection'])
        if point['output']['projection'] is None:
          raise ValueError('fit job actual projection')
    output_row = asdict(output)
    output_row['projection'] = projection_to_dict(output.projection)
    if output_row['projection'] is None:
      raise ValueError('fit job current projection')
    payload = {
      'version': 1,
      'family': 'torque',
      'objective': asdict(self.objective),
      'now_ns': now_ns,
      'sequence': sequence,
      'prior': prior,
      'replay': self.replay.to_snapshot(selected),
      'blocks': block_rows,
      'control': asdict(control),
      'output': output_row,
      'physical_context': tuple(physical_context),
    }
    return {'version': 1, 'family': 'torque', 'snapshot_b64': base64.b64encode(pack_primitive_snapshot(payload)).decode('ascii')}

  def install_fit(self, report, result, validation, *, physical_context):
    from openpilot.starpilot.flm.physical_response import PhysicalModel

    if self.key[0] == 'centre':
      facade = self.centres.get(self.key[1])
      return bool(facade is not None and facade.install_fit(report, result, validation, physical_context=physical_context))
    try:
      if result.profile is None or result.profile.identity != self.identity or result.profile.parameters != self.parameters():
        return False
      values = dict(report['model'])
      for field in ('train_blocks', 'heldout_blocks'):
        values[field] = tuple(values[field])
      model = PhysicalModel(**values)
      if (
        model.identity != self.identity
        or model.context != canonical_physical_context(physical_context)
        or physical_model_revision(model) != validation.physical_model_revision
        or validation.baseline_revision != self.baseline_revision
      ):
        return False
      if self.model != model:
        self.current_physical_valid = False
        self.last_physical_ns = 0
      self.model, self.model_cutoff_ns = model, int(report['model_cutoff_ns'])
      self.fit_profile = result.profile
      self.replay.objective = self.objective
      return True
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      return False

  def application_witness(self):
    return None

  def current_admission(self, profile, control, output, physical_context):
    # FourHz current evidence guard. The per-frame parent remains primitive-only.
    from openpilot.starpilot.flm.evidence_noise import noisy_frames

    recent = tuple(
      {'control_ns': frame.control_ns, 'inputs': frame.inputs, 'selected_command': frame.selected_command}
      for frame in reversed(tuple(islice(reversed(self.replay.records), 101)))
    )
    try:
      flags = noisy_frames(recent, 'normalized_torque')
      noisy = any(model or chatter and self.key[0] != 'centre' for model, chatter in flags.values())
    except (KeyError, TypeError, ValueError, OverflowError):
      noisy = True
    if noisy:
      from openpilot.starpilot.flm.adaptive_profile import CurrentAdmission

      return CurrentAdmission(control.identity, control.baseline_revision, '', control.control_ns, False, control.enabled, control.manual, False)
    from openpilot.starpilot.flm.adaptive_profile import CurrentAdmission

    if self.key[0] == 'centre':
      return CurrentAdmission(control.identity, control.baseline_revision, '', control.control_ns, False, control.enabled, control.manual, False)
    model = self.model
    context_ok = bool(
      model is not None
      and model.context == canonical_physical_context(physical_context)
      and self.model_cutoff_ns < control.control_ns <= self.model_cutoff_ns + 600_000_000_000
    )
    self.replay.objective = self.objective
    healthy = bool(
      context_ok
      and self.current_physical_valid
      and 0 < self.last_physical_ns <= output.apply_ns + 500_000_000
      and 0 <= output.apply_ns - self.last_physical_ns <= 100_000_000
      and self.replay.current_probe(profile, control, output, physical_context, model)
    )
    return CurrentAdmission(
      control.identity,
      control.baseline_revision,
      physical_model_revision(model) if model is not None else '',
      min(control.control_ns, output.apply_ns),
      healthy,
      bool(control.enabled),
      bool(control.manual),
      context_ok,
    )


def from_evidence(cp, evidence, key=None):
  try:
    if cp.notCar or cp.passive or cp.dashcamOnly:
      return None
    key = tuple(key or objective_key(evidence))
    if evidence.stage_schema_revision == RAW_TORQUE:
      return TorqueCollectionAdapter(cp, evidence, key)
    return None  # PID/angle/curvature remain explicitly outside torque learning.
  except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
    return None


def _profile_from_dict(value):
  from openpilot.starpilot.flm.adaptive_profile import Profile, Parameter

  return Profile(
    value['identity'],
    value['sequence'],
    value['observed_ns'],
    value['expires_ns'],
    tuple(Parameter(**parameter) for parameter in value['parameters']),
    tuple(value['coefficients']),
    tuple(value['train_ids']),
    tuple(value['heldout_ids']),
    value['baseline_loss'],
    value['candidate_loss'],
    tuple(tuple(row) for row in value['cohort_improvements']),
    value['policy'],
  )


def decode_fit_result(report):
  from openpilot.starpilot.flm.adaptive_profile import Result, ReplayValidation, replay_accepts

  try:
    if report['profile'] is None:
      return Result(report['status'], report['reason']), None
    profile = _profile_from_dict(report['profile'])
    value = report['validation']
    validation = ReplayValidation(
      _profile_from_dict(value['profile']),
      value['baseline_revision'],
      value['physical_model_revision'],
      value['no_saturation_regression'],
      value['no_slew_regression'],
      value['worst_cohort_improvement'],
    )
    return (Result(report['status'], report['reason'], profile), validation) if replay_accepts(validation, profile) else None
  except (KeyError, TypeError, ValueError, OverflowError):
    return None


def fit_snapshot(snapshot):
  """Fresh child: independent physical fit, stage fit, chronological replay."""
  if snapshot.get('version') != 1 or len(snapshot.get('snapshot_b64', '')) > 6 * 1024 * 1024:
    raise ValueError('fit wrapper bound')
  payload = unpack_primitive_snapshot(base64.b64decode(snapshot['snapshot_b64'], validate=True))
  if payload.get('version') != 1 or payload.get('family') != snapshot.get('family'):
    raise ValueError('fit family')
  if payload['family'] != 'torque':
    raise ValueError('only actual torque-controller evidence is admitted')
  from openpilot.starpilot.flm.evidence_noise import reject_noisy_job

  reason = reject_noisy_job(payload, retain_centre_chatter=False)
  if reason is not None:
    return {'status': 'collecting', 'reason': reason, 'profile': None, 'validation': None}
  factory, _ = factory_from_snapshot(payload['replay'])
  objective = Objective(**payload['objective'])
  # Bind the recorded actual stream to the fitting objective only in the child;
  # actual applied residual scalars reproduce any previously selected objective.
  replay_payload = unpack_primitive_snapshot(payload['replay'])
  replay_payload['objective'] = asdict(objective)
  engine = ControllerReplay.from_snapshot(factory, objective, pack_primitive_snapshot(replay_payload))
  from openpilot.starpilot.flm.torque_raw_fit import fit_raw_torque

  return fit_raw_torque(payload, engine, objective)
