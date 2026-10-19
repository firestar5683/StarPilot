"""Optional-learner event capture using unchanged actual source/native joins."""
from openpilot.starpilot.flm.clipping_quality import RECORDED_DEBT, clipping_quality as validate_clipping_quality, identification_for_quality
from dataclasses import asdict
import base64
import math

from openpilot.starpilot.flm.canonical_surface_adapter import GROUPS
from openpilot.starpilot.flm.controller_replay import pack_primitive_snapshot
from openpilot.starpilot.flm.event_objective import EffectObjective
from openpilot.starpilot.flm.full_surface_profile import FullSurfaceEnvelope
from openpilot.starpilot.flm.learner_factory import TorqueCollectionAdapter


def _fresh_current_physical(control_ns, apply_ns, response_ns, now_ns):
  """Compare independent streams to trusted decision time, never restamp them."""
  if now_ns is None:
    # Preserve the conservative legacy direct-call contract exactly.
    return 0 < response_ns <= apply_ns + 500_000_000 and 0 <= apply_ns - response_ns <= 100_000_000
  stamps = control_ns, apply_ns, response_ns, now_ns
  return bool(all(type(stamp) is int and stamp > 0 for stamp in stamps) and
    control_ns <= apply_ns <= now_ns and
    all(0 <= now_ns - stamp <= 100_000_000 for stamp in stamps[:3]))


def event_key(evidence):
  # A bounded complete registry, independent of instantaneous phase. Every
  # canonical group eventually receives an attempt; absent physical excitation
  # is reported, never substituted by an invented feature or another car tune.
  order = ('deadband.high', 'center', 'friction.left', 'friction.right',
           'ff.left', 'ff.right', 'turn.window.left', 'turn.window.right',
           'unwind.window.left', 'unwind.window.right', 'deadband.low', 'angle.assist')
  tick = int(dict(evidence.replay_inputs)['control_frame'])
  return 'event', order[(tick // 6000) % len(order)]


def event_keys(evidence):
  return tuple(('event', group) for group in GROUPS)


class EventCollectionAdapter(TorqueCollectionAdapter):
  event_collection = True
  raw_storage = True

  def __init__(self, cp, evidence, key, *, source=None, replay_version=2, clipping_quality=RECORDED_DEBT, restore_version=2):
    if type(replay_version) is not int or replay_version not in (2, 3):
      raise ValueError('event replay experiment version')
    self.clipping_quality = validate_clipping_quality(clipping_quality)
    if replay_version != 3 and self.clipping_quality != RECORDED_DEBT:
      raise ValueError('state-aligned quality requires explicit event version3')
    from openpilot.starpilot.flm.clipping_quality import restore_quality
    if type(restore_version) is not int or restore_version not in (2, 4, 5, 6) or (restore_version in (4, 5, 6) and
        (replay_version != 3 or self.clipping_quality != restore_quality(restore_version))):
      raise ValueError('explicit whole-map restore producer contract')
    self.restore_version = restore_version
    self.replay_version = replay_version
    self.snapshot_readiness = None
    self._event_initialized = False
    super().__init__(cp, evidence, ('feedforward', 'high', 'steady'), source=source, event_capture=True)
    self._event_initialized = True
    from openpilot.starpilot.flm.runtime_adapter_registry import car_params_digest
    self.cp_sha256 = car_params_digest(cp)
    self.controller_revision = evidence.controller_revision
    self.envelope = None
    self.optimizer_prior = None
    self.restore_envelope = None
    self.accepted_restore_envelope = None
    self._source = None
    self.event_objective = None
    self.select_objective(key)
    self.model_speed_bounds = None
    self.target_changed = False
    self.actual_target_sha256 = None
    if source is not None:
      self.bind_source(source)

  def select_objective(self, key):
    if not getattr(self, '_event_initialized', False):
      return super().select_objective(key)
    if type(key) is not tuple or len(key) != 2 or key[0] != 'event' or key[1] not in GROUPS:
      raise ValueError('actual event group')
    unchanged = getattr(self, 'key', None) == key
    self.key = key
    if not unchanged:
      self.snapshot_readiness = None
    if unchanged and self.event_objective is not None:
      return
    if self.envelope is not None:
      self.envelope = self.envelope.for_trial(GROUPS[key[1]])
      self.event_objective = EffectObjective(key[1], self.envelope.trial_names, self.envelope.trial_anchor, self.source_epoch)

  def bind_source(self, source):
    if (source.source_epoch != self.source_epoch or source.cp_sha256 != self.cp_sha256 or
        not source.enabled or source.manual or not source.reset):
      raise ValueError('event original settings identity')
    if self._source is not None and (source.source_epoch, source.reset) != (self._source.source_epoch, self._source.reset):
      raise ValueError('event reset without new collector')
    self._source = source
    if self.envelope is None:
      self.envelope = FullSurfaceEnvelope.initial(cp_sha256=self.cp_sha256, controller_revision=self.controller_revision,
        source_epoch=self.source_epoch, reset_generation=source.reset, selected_baseline_revision=self.baseline_revision,
        trial_names=GROUPS[self.key[1]], persistent_source_epoch=getattr(source, 'persistent_source_epoch', ''))
      self.select_objective(self.key)

  @property
  def full_surface_binding(self):
    return None if self.envelope is None else self.envelope.source_binding()

  def install_full_prior(self, prior):
    if self._source is None or self.envelope is None:
      raise ValueError('event current source must precede historical prior')
    if prior is not None and (not prior.historical_only or prior.envelope.source_binding() != self.envelope.source_binding()):
      raise ValueError('foreign historical optimizer prior')
    self.optimizer_prior = prior
    self.restore_envelope = None
    if prior is None:
      return
    # Historical values are NOT actual current accepted target / regression
    # centre. A new drive remains neutral until a distinct full-map restore
    # operation passes fresh whole-controller/physical/native qualification.
    from openpilot.starpilot.flm.full_surface_profile import neutral_coordinates
    if (self.envelope.prior_coordinates == neutral_coordinates() and
        self.envelope.coordinates == neutral_coordinates() and
        prior.envelope.coordinates != neutral_coordinates()):
      self.restore_envelope = self.envelope.restore_from_history(prior)


  def parameters(self):
    if not getattr(self, '_event_initialized', False):
      return self.objective.parameters
    if self.event_objective is None:
      return ()
    return self.event_objective.parameters

  def required_cohorts(self):
    if not getattr(self, '_event_initialized', False):
      return self.objective.required_cohorts
    return () if self.event_objective is None else self.event_objective.required_cohorts

  def prepare_control(self, evidence):
    trace = getattr(evidence, 'effect_trace', None)
    target = None if trace is None else trace.envelope
    digest = None if target is None else target.full_profile_sha256
    if digest != self.actual_target_sha256:
      self.target_changed = self.actual_target_sha256 is not None or target is not None
      self.actual_target_sha256 = digest
      if target is not None:
        self.restore_envelope = None
        self.accepted_restore_envelope = target if target.operation == "restore" else None
        from dataclasses import replace
        target.validate()
        if self.envelope is None or target.source_binding() != self.envelope.source_binding():
          return None
        # Current accepted target becomes the immutable prior for the NEXT
        # trial; an already accepted outside-group coordinate is never zeroed.
        self.envelope = replace(target, prior_coordinates=target.coordinates,
          prior_full_profile_sha256=target.full_profile_sha256).for_trial(GROUPS[self.key[1]])
        self.event_objective = EffectObjective(self.key[1], self.envelope.trial_names,
          self.envelope.trial_anchor, self.source_epoch)
    return super().prepare_control(evidence)

  def physical_observable(self, value):
    # Raw storage is shared by all scheduled groups, including crawl FF.
    # Per-coordinate excitation and independent model/admission stay in child.
    return value.speed_mps >= 2 and abs(value.roll_rad) < .3

  def cohort(self, control, physical):
    if self.envelope is None or control.identity != self.identity or control.source_epoch != self.source_epoch:
      return None
    if self.model is not None:
      command, observed = -physical['applied_command'], physical['lateral_accel']
      self.current_physical_valid = bool(self.model.command_low <= command <= self.model.command_high and
        abs(self.model.slope * command + self.model.intercept - observed) <= max(.01, 3 * self.model.heldout_rmse) and
        self.model_speed_bounds is not None and self.model_speed_bounds[0] <= physical['speed_mps'] <= self.model_speed_bounds[1])
      self.last_physical_ns = int(physical['response_ns'])
    # A storage packet is never called a maneuver; the child reconstructs full
    # cycles/turns from original 100Hz trace before assigning independent IDs.
    return 'event-storage.' + self.source_epoch

  def raw_maneuver_complete(self, control, physical):
    return False

  def fit_job_snapshot(self, blocks, now_ns, sequence, prior, *, control, output, physical_context):
    self.snapshot_readiness = None
    if self.envelope is None or self.event_objective is None or len(blocks) < 8:
      self.snapshot_readiness = {'reason': 'event_objective_unavailable' if self.envelope is None or self.event_objective is None
                                 else 'event_storage_packet_support', 'storageBlocks': len(blocks), 'requiredStorageBlocks': 8}
      return None
    from opendbc.car.steering_projection import projection_to_dict
    from openpilot.starpilot.flm.event_storage import select_whole_event_snapshot
    packets = tuple(asdict(block) for block in blocks)
    diagnostics = {}
    rows, windows = select_whole_event_snapshot(self.replay, packets, self.event_objective, diagnostics=diagnostics)
    # Parent selection counts are not child physical-model or fit qualification.
    self.snapshot_readiness = {
      'reason': ('snapshot_preparing' if len(rows) >= 16 else
                 'whole_event_export_support' if diagnostics['wholeBlocks'] >= 16 else 'whole_physical_event_support'),
      'wholeBundles': diagnostics['wholeBlocks'], 'selectedBundles': len(rows),
      'requiredBundles': 16, 'requiredCalibrationBundles': 8, 'requiredLaterBundles': 8,
      'missingCheckpoint': diagnostics['missingCheckpoint'], 'frameBudget': diagnostics['frameBudget'],
      'windowBudget': diagnostics['windowBudget'], 'childQualification': 'not_yet_evaluated',
    }
    if len(rows) < 16:
      return None
    # Complete source windows include the original maneuver boundary and its
    # neutral recovery, not merely first/last admitted physical sample.
    original_points = {(point.control_ns, point.apply_ns, point.mono_ns): point for block in blocks for point in block.samples}
    from openpilot.starpilot.flm.fullrate_collector import RawBlock
    selected = tuple(RawBlock(row['identity'], row['block_id'], row['cohort'], row['stage_revision'], row['response_revision'],
      tuple(original_points[item['control_ns'], item['apply_ns'], item['mono_ns']] for item in row['samples'])) for row in rows)
    for block in rows:
      for point in block['samples']:
        point['output']['projection'] = projection_to_dict(point['output']['projection'])
        if point['output']['projection'] is None:
          raise ValueError('event actual projection missing')
    # The child's replay witness is an original selected endpoint. It is NOT
    # current authority: parent revalidate_fit separately requires the fresh
    # latest command/native/physical/current_effect_probe before publication.
    control, output = selected[-1].samples[-1].control, selected[-1].samples[-1].output
    output_row = asdict(output)
    output_row['projection'] = projection_to_dict(output.projection)
    if output_row['projection'] is None:
      raise ValueError('event current actual projection missing')
    operation = 'trial'
    envelope = self.envelope
    if self.restore_envelope is not None:
      # Bind the current scheduled marker group without changing the FULL
      # historical restoration target. Child restoration never Gram-fits these
      # <=4 protocol markers as if they identified all30 coordinates.
      envelope = self.envelope.for_trial(self.event_objective.names).restore_from_history(self.optimizer_prior)
      envelope.validate()
      operation = 'restore'
    from openpilot.starpilot.flm.clipping_quality import FIXED_MAP_IDENTIFICATION, restore_policy
    payload = {'version': 1, 'family': self.command_family,
      'event_version': self.replay_version if operation == 'trial' else self.restore_version, 'event_operation': operation,
      **({'event_clipping_quality': self.clipping_quality, 'event_identification_policy': identification_for_quality(self.clipping_quality)}
         if self.replay_version == 3 and operation == 'trial' else {}),
      **({'event_clipping_quality': self.clipping_quality, 'event_identification_policy': FIXED_MAP_IDENTIFICATION,
          'event_restore_policy': restore_policy(self.restore_version)}
         if operation == 'restore' and self.restore_version in (4, 5, 6) else {}),
      'event_objective': asdict(self.event_objective),
      'effect_envelope': asdict(envelope), 'objective': asdict(self.objective),
      'now_ns': now_ns, 'sequence': sequence, 'prior': tuple(dict(envelope.prior_coordinates)[name] for name in self.event_objective.names),
      'historical_optimizer_target': None if self.optimizer_prior is None else asdict(self.optimizer_prior.envelope),
      'restoration_required_groups': list(envelope.restoration_groups) if operation == 'restore' else [],
      'replay': self.replay.to_snapshot(selected, event_windows=windows), 'raw_blocks': rows, 'control': asdict(control),
      'output': output_row, 'physical_context': tuple(physical_context)}
    snapshot = {'version': 1, 'family': self.command_family, 'snapshot_b64': base64.b64encode(pack_primitive_snapshot(payload)).decode('ascii')}
    self.snapshot_readiness['reason'] = 'snapshot_ready'
    return snapshot

  def install_fit(self, report, result, validation, *, physical_context):
    from openpilot.starpilot.flm.full_surface_profile import FullSurfaceEnvelope
    from openpilot.starpilot.flm.event_activation import activation_from_dict, activation_matches_model, activation_model_from_dict
    try:
      envelope = result.profile.effect_envelope
      if (not isinstance(envelope, FullSurfaceEnvelope) or self.envelope is None or
          envelope.source_binding() != self.envelope.source_binding() or
          (envelope.prior_full_profile_sha256 != self.envelope.prior_full_profile_sha256 and
           envelope.full_profile_sha256 != self.envelope.prior_full_profile_sha256) or
          not set(envelope.trial_names).issubset(GROUPS[self.key[1]]) or validation is None or validation.profile != result.profile):
        return False
      envelope.validate(result.profile)
      if envelope.operation == 'restore':
        from openpilot.starpilot.flm.full_surface_profile import RESTORE_POLICY
        renewing = envelope == self.accepted_restore_envelope
        pending = (self.optimizer_prior is not None and self.restore_envelope is not None and
          envelope.coordinates == self.optimizer_prior.envelope.coordinates and
          envelope.history_full_profile_sha256 == self.optimizer_prior.envelope.full_profile_sha256)
        if (not (renewing or pending) or result.profile.policy != RESTORE_POLICY or
            set(report.get('restoration_qualified_groups', ())) != set(envelope.restoration_groups)):
          return False
      model = activation_model_from_dict(report['model'])
      report_version = report.get('event_version', 2)
      if type(report_version) is not int or report_version == 3 and 'restore_activation_plan' in report:
        return False
      if envelope.operation == 'restore' and report_version != self.restore_version:
        return False
      if report_version == 3:
        plan = activation_from_dict(report['activation_plan'])
        if (self.replay_version != 3 or envelope.operation != 'trial' or
            plan.identity != self.identity or plan.baseline_revision != self.baseline_revision or
            plan.source_epoch != self.source_epoch or plan.cutoff_ns != report['model_cutoff_ns'] or
            plan.clipping_quality != self.clipping_quality or
            not set(result.profile.train_ids + result.profile.heldout_ids).issubset(plan.stage_blocks) or
            not activation_matches_model(plan, model)):
          return False
      elif report_version in (4, 5, 6):
        from openpilot.starpilot.flm.restore_activation import restore_plan_from_dict, restore_plan_matches
        from openpilot.starpilot.flm.clipping_quality import restore_policy
        plan = restore_plan_from_dict(report['restore_activation_plan'])
        expected_policy = restore_policy(report_version)
        if (self.restore_version != report_version or plan.version != expected_policy or
            report_version == 6 and plan.clipping_quality != self.clipping_quality or
            envelope.operation != 'restore' or 'activation_plan' in report or
            plan.identity != self.identity or plan.baseline_revision != self.baseline_revision or
            plan.source_epoch != self.source_epoch or plan.cutoff_ns != report['model_cutoff_ns'] or
            not restore_plan_matches(plan, envelope) or
            not set(result.profile.train_ids + result.profile.heldout_ids).issubset(plan.stage_blocks) or
            not activation_matches_model(plan, model)):
          return False
      elif (report_version != 2 or 'activation_plan' in report or 'restore_activation_plan' in report or hasattr(model, 'activation_version') or
            self.replay_version == 3 and envelope.operation != 'restore'):
        return False
      bounds = tuple(report['speed_mps_bounds'])
      if len(bounds) != 2 or not all(math.isfinite(value) for value in bounds) or not 0 < bounds[0] <= bounds[1] <= 90:
        return False
      from openpilot.starpilot.flm.runtime_adapter_registry import canonical_physical_context, physical_model_revision
      if (model.identity != self.identity or model.context != canonical_physical_context(physical_context) or
          physical_model_revision(model) != validation.physical_model_revision or validation.baseline_revision != self.baseline_revision):
        return False
      self.event_objective = EffectObjective(self.key[1], envelope.trial_names, envelope.trial_anchor, self.source_epoch)
      if report_version in (3, 4, 5, 6) and self.model != model:
        self.current_physical_valid = False
        self.last_physical_ns = 0
      self.model, self.model_cutoff_ns = model, report['model_cutoff_ns']
      self.model_speed_bounds = bounds
      self.fit_profile = result.profile
      return True
    except (AttributeError, KeyError, TypeError, ValueError):
      return False

  def current_admission(self, profile, control, output, physical_context, *, now_ns=None):
    from openpilot.starpilot.flm.adaptive_profile import CurrentAdmission
    from openpilot.starpilot.flm.effect_current_probe import current_effect_probe
    from openpilot.starpilot.flm.runtime_adapter_registry import canonical_physical_context, physical_model_revision

    model = self.model
    healthy = bool(model is not None and self.fit_profile is not None and profile.effect_envelope is not None and
      self.envelope is not None and profile.effect_envelope.source_binding() == self.envelope.source_binding() and
      (profile.effect_envelope.prior_full_profile_sha256 == self.envelope.prior_full_profile_sha256 or
       profile.effect_envelope.full_profile_sha256 == self.envelope.prior_full_profile_sha256) and
      model.context == canonical_physical_context(physical_context) and
      self.model_cutoff_ns < control.control_ns <= self.model_cutoff_ns + 600_000_000_000 and
      self.current_physical_valid and
      _fresh_current_physical(control.control_ns, output.apply_ns, self.last_physical_ns, now_ns) and
      current_effect_probe(self.replay, profile, control, output, model))
    return CurrentAdmission(control.identity, control.baseline_revision,
      physical_model_revision(model) if model is not None else '', min(control.control_ns, output.apply_ns),
      healthy, control.enabled, control.manual, healthy, tuple(control.baseline_values))
