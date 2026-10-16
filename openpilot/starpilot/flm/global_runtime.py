"""Controls-owned profile admission and capture, with no settings or fit I/O."""

import math
from collections import OrderedDict
from types import SimpleNamespace
from openpilot.starpilot.flm.adaptive_profile import ApplicationOutcome, Parameter, ProfileOwner
from openpilot.starpilot.flm.runtime_adapter_registry import (
  selected_descriptor,
  baseline_values,
  baseline_revision,
  selected_identity,
  SOURCE_LEASE_NS,
  native_identity_key,
  native_identity_digest,
  vm_regime,
)
from openpilot.starpilot.flm.learning_wire import read_runtime_admission, read_source_receipt
from openpilot.starpilot.flm.fullrate_collector import ControlEvidence
from openpilot.starpilot.flm.torque_adapter import Objective, Admission, TorqueStageOwner


def native_witness_current(native, *, now_ns, active):
  # Observer copies the exact already-validated native object. No verifier or
  # inventory/transport traversal belongs to this per-frame guard.
  try:
    observed, expires = int(native.observedMonoTime), int(native.validUntilMonoTime)
    return bool(active and native.requestedLateral and native.lateralAllowed and 0 < observed <= now_ns <= expires <= observed + 200_000_000)
  except (AttributeError, TypeError, ValueError, OverflowError):
    return False


SERVICE = 'autoSteeringLearning'
NON_TORQUE_SCHEMAS = {
  'pid': 'pid-ff-pre-pid-v1',
  'angle': 'angle-no-offset-v1',
  'curvature': 'curvature-ff-pre-pid-v1',
  'ford_curvature': 'ford-requested-pre-trim-v1',
}


class GlobalRuntime:
  def __init__(self, cp, ci, controller):
    # Construct AFTER actual LaC selection, startup native/manual configuration.
    self.cp, self.ci, self.controller = cp, ci, controller
    from openpilot.starpilot.flm.calibration_lifecycle import ConsumerCalibrationLifecycle
    self._calibration_lifecycle = ConsumerCalibrationLifecycle()
    self.health_services = ('carState', 'modelV2', 'vehicleParameters', 'lateralDelay', 'driverMonitoringState', 'extrinsicsCalibration')
    try:
      self.descriptor = selected_descriptor(cp, ci, controller)
      if self.descriptor is not None and self.descriptor.domain != 'torque':
        self.descriptor = None
      self.initial_values = baseline_values(controller) if self.descriptor is not None else ()
      self.baseline_revision = baseline_revision(self.descriptor, self.initial_values) if self.descriptor is not None else ''
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      self.descriptor, self.initial_values, self.baseline_revision = None, (), ''
    self.source = self.profile = self.validation = self.stage = self.frame = None
    from openpilot.starpilot.flm.learned_lifecycle import SettingsLeaseCache

    self.settings_cache = SettingsLeaseCache(self.descriptor.cp_sha256 if self.descriptor is not None else '')
    self.identity = ''
    self.identity_source_epoch = ''
    self.generation = 0
    self.owner = self.torque_owner = self.centre_source = None
    self.coefficient = 0.0
    self.session = ''
    self.outer_sequence = -1
    self.last_now = 0
    self.used = False
    self.eligible = False
    self.stage_effect = False
    self.reason = 'initializing'
    self.outcome = None
    self.snapshot = ()
    self.snapshot_sequence = 0
    self.frame_sequence = 0
    self.snapshot_ns = 0
    self.replay_inputs = ()
    self.observation = None
    self.prior_policy_output = self.prior_policy_ff = 0.0
    self.native_identity_cache = None
    self.native_identity = ''
    self.profile_native_identity = ''
    self.replaced_native_model_revision = ''
    self.vm_anchor = None
    self.replaced_vm_model_revision = ''
    self.centre_frame = None
    self.centre_ack = None
    self.centre_history = OrderedDict()
    self.centre_raw = ()
    self.centre_result = (0.0, 0.0)
    self.torque_result = (0.0, 0.0)
    if self.descriptor is not None and self.descriptor.domain == 'torque':
      from openpilot.starpilot.flm.torque_observation import TorqueObservation

      self.observation = TorqueObservation()
      controller.automatic_flm_observation = self.observation
    if self.descriptor is not None:
      controller.automatic_flm_adapter = self
      if self.descriptor.domain == 'torque':
        controller.automatic_flm_stages = self
        controller.automatic_flm_centre = self
      elif self.descriptor.domain != 'ford_curvature':
        controller.response_adapter = self

  def _neutral(self, reason):
    self.coefficient = 0.0
    if self.owner is not None:
      self.owner.applied = (0.0,) * len(self.owner.parameters)
    if self.torque_owner is not None:
      self.torque_owner.owner.applied = (0.0,) * len(self.torque_owner.owner.parameters)
    if self.centre_source is not None:
      self.centre_source.owner.owner.applied = (0.0, 0.0)
    self.reason = reason

  def prepare(self, sm, *, now_ns, active, healthy, controller=None, manual_current=False, native_required=False, native_witness=None):
    """Bounded current source/admission checks; invoked immediately before LaC."""
    self.used, self.stage, self.frame, self.eligible = False, None, None, False
    self.source = None
    # Capture a fresh V2 generation and calibration interruption before ANY
    # unrelated adapter/native/vehicle health gate can return.
    tracker = self._calibration_lifecycle
    early_source = None
    try:
      if (type(now_ns) is int and now_ns > 0 and self.descriptor is not None and
          sm.seen[SERVICE] and sm.alive[SERVICE] and sm.valid[SERVICE] and sm.freq_ok[SERVICE] and
          0 <= now_ns - int(sm.recv_time[SERVICE] * 1e9) <= SOURCE_LEASE_NS):
        envelope = sm[SERVICE]
        if envelope.learning.sourceReceipt.version == 2:
          early_source = read_source_receipt(SimpleNamespace(valid=True, autoSteeringLearning=envelope),
            now_ns=now_ns, cp_sha256=self.descriptor.cp_sha256)
          if early_source is not None and not tracker.generation:
            tracker.capture(early_source.calibration_generation)
      stamp = int(sm.logMonoTime['extrinsicsCalibration'])
      receipt = int(sm.recv_time['extrinsicsCalibration'] * 1e9)
      current_calibration = bool(type(now_ns) is int and now_ns > 0 and
        sm.all_checks(['extrinsicsCalibration']) and
        0 < stamp <= now_ns <= stamp + 500_000_000 and
        0 < receipt <= now_ns <= receipt + 500_000_000)
      tracker.observe(sm['extrinsicsCalibration'], current=current_calibration, now_ns=now_ns)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      tracker.reject(now_ns=now_ns)
    self.outcome = None
    self.centre_frame = None
    self.centre_raw = ()
    self.centre_result = (0.0, 0.0)
    self.torque_result = (0.0, 0.0)
    self.stage_effect = False
    self.centre_ack = None
    policy = getattr(getattr(self.controller, 'starpilot_extension', None), 'policy', None)
    self.live_manual = bool(manual_current or getattr(self.controller, 'flm_surface', None) is not None or
                            getattr(policy, 'surface', None) is not None)
    self.native_required = bool(native_required)
    self.native_witness = native_witness
    key = native_identity_key(native_witness)
    if self.native_identity_cache is None or key != self.native_identity_cache[0]:
      self.native_identity_cache = (key, native_identity_digest(key))
    self.native_identity = self.native_identity_cache[1]
    self.active, self.healthy, self.now_ns = bool(active), bool(healthy), now_ns
    if self.descriptor is None or controller is not None and controller is not self.controller:
      self._neutral('actual_adapter_unavailable')
      return
    try:
      current_values = baseline_values(self.controller)
      if current_values != self.initial_values:
        self.initial_values = current_values
        self.baseline_revision = baseline_revision(self.descriptor, current_values)
        self.identity_source_epoch = ''
        self.profile = self.validation = self.torque_owner = self.owner = self.centre_source = None
        self.snapshot_ns = 0
        self._neutral('baseline_changed')
    except (AttributeError, TypeError, ValueError, OverflowError):
      self._neutral('baseline_unavailable')
      return
    clock_valid = type(now_ns) is int and now_ns > 0 and (not self.last_now or 0 < now_ns - self.last_now <= 50_000_000)
    self.last_now = now_ns
    try:
      if self.native_required and not native_witness_current(self.native_witness, now_ns=now_ns, active=active):
        raise ValueError('native_lease_unavailable')
      if not clock_valid or not sm.all_checks(list(self.health_services)) or not healthy:
        raise ValueError('unhealthy_clock_or_vehicle')
      # Fixed cardinality original-source and receipt checks. A recent profile
      # never turns old vehicle/model messages into fresh controller evidence.
      age_limits = (
        ('carState', 100_000_000),
        ('modelV2', 150_000_000),
        ('vehicleParameters', 150_000_000),
        ('driverMonitoringState', 150_000_000),
        ('lateralDelay', 500_000_000),
        ('extrinsicsCalibration', 500_000_000),
      )
      for service, maximum in age_limits:
        stamp = int(sm.logMonoTime[service])
        receipt = int(sm.recv_time[service] * 1e9)
        if not (sm.seen[service] and 0 < stamp <= now_ns <= stamp + maximum and 0 < receipt <= now_ns <= receipt + maximum):
          if service == 'extrinsicsCalibration' and hasattr(self, '_calibration_lifecycle'):
            self._calibration_lifecycle.reject()
          raise ValueError('stale_original_source')
      if self.controller.sat_time > 0:
        raise ValueError('controller_saturation')
      if not (sm.seen[SERVICE] and sm.alive[SERVICE] and sm.valid[SERVICE] and sm.freq_ok[SERVICE]):
        raise ValueError('source_unavailable')
      received = int(sm.recv_time[SERVICE] * 1e9)
      if not 0 <= now_ns - received <= SOURCE_LEASE_NS:
        raise ValueError('stale_receipt')
      envelope = sm[SERVICE]
      event = SimpleNamespace(valid=True, autoSteeringLearning=envelope)
      source = early_source if early_source is not None else read_source_receipt(event, now_ns=now_ns, cp_sha256=self.descriptor.cp_sha256)
      if (
        source is None
        or source.cp_sha256 != self.descriptor.cp_sha256
        or not 0 < source.observed_ns <= now_ns <= source.expires_ns <= source.observed_ns + SOURCE_LEASE_NS
      ):
        raise ValueError('source_identity_or_clock')
      calibration = sm['extrinsicsCalibration']
      if source.calibration_generation:
        if (len(source.calibration) != 3 or not all(math.isfinite(value) for value in source.calibration) or
            not tracker.admit(source.calibration_generation, source.observed_ns)):
          raise ValueError('calibration_identity_changed')
      elif str(calibration.calStatus) != 'calibrated' or source.calibration != tuple(float(value) for value in calibration.rpyCalib):
        raise ValueError('calibration_identity_changed')
      if not self.settings_cache.install(source, received_ns=received) or self.settings_cache.current(now_ns=now_ns) is None:
        raise ValueError('source_cache')
      if source.source_epoch != self.identity_source_epoch:
        identity = selected_identity(self.descriptor, source.source_epoch, self.baseline_revision)
        self.identity_source_epoch = source.source_epoch
        self.identity = identity
        self.generation += 1
        self.owner = self.torque_owner = self.centre_source = None
        self.profile = self.validation = None
        self.snapshot_ns = self.snapshot_sequence = 0
        self.session, self.outer_sequence = '', -1
        self.centre_history.clear()
      self.source = source
      self.eligible = bool(source.enabled and not source.manual and not self.live_manual and active and healthy)
      if not source.enabled or source.manual or self.live_manual or not active:
        raise ValueError('manual_or_off_or_inactive')
      admission = read_runtime_admission(event)
      if admission is None:
        raise ValueError('collecting')
      profile, validation = admission
      if self.native_required and self.profile_native_identity and self.native_identity != self.profile_native_identity:
        if self.validation is not None:
          self.replaced_native_model_revision = self.validation.physical_model_revision
        self.owner = self.torque_owner = self.centre_source = None
      if self.native_required and validation.physical_model_revision == self.replaced_native_model_revision:
        raise ValueError('native_identity_replaced')
      if validation.physical_model_revision == self.replaced_vm_model_revision:
        raise ValueError('vehicle_model_material_change')
      if profile.identity != self.identity or validation.baseline_revision != self.baseline_revision:
        raise ValueError('profile_baseline_identity')
      outer = envelope.learning
      session, sequence = str(outer.session), int(outer.sequence)
      if not session or len(session) > 64 or sequence < 0:
        raise ValueError('session')
      if session == self.session and (
        sequence < self.outer_sequence or sequence == self.outer_sequence and (profile != self.profile or validation != self.validation)
      ):
        raise ValueError('changed_or_reordered_admission')
      if session != self.session:
        self.owner = self.torque_owner = self.centre_source = None
      self.session, self.outer_sequence = session, sequence
      self.profile, self.validation = profile, validation
      if self.native_required:
        self.profile_native_identity = self.native_identity
      if self.descriptor.domain == 'torque':
        names = [p.name.split('.') for p in profile.parameters]
        if len(names) != 2 or any(len(row) != 4 for row in names) or names[0][0] != 'centre' and (names[0][2] != 'left' or names[1][2] != 'right'):
          raise ValueError('torque_objective')
        if names[0][0] != 'feedforward':
          raise ValueError('unsupported_torque_objective')
        self.centre_source = None
        objective = Objective(names[0][0], names[0][1], names[0][3])
        if profile.parameters != objective.parameters:
          raise ValueError('torque_parameter_schema')
        if (
          self.torque_owner is None
          or self.torque_owner.objective != objective
          or self.torque_owner.physical_model_revision != validation.physical_model_revision
        ):
          self.torque_owner = TorqueStageOwner(
            self.identity, objective, baseline_revision=self.baseline_revision, physical_model_revision=validation.physical_model_revision
          )
        self.torque_owner.prepare(Admission(profile, now_ns, source.enabled, source.manual, healthy, validation))
      else:
        parameters = self.response_parameters()
        if profile.parameters != parameters:
          raise ValueError('domain_parameter_schema')
        if self.owner is None or self.owner.physical_model_revision != validation.physical_model_revision:
          self.owner = ProfileOwner(
            self.identity, parameters, baseline_revision=self.baseline_revision, physical_model_revision=validation.physical_model_revision
          )
        self.coefficient = self.owner.tick(
          profile, now_ns=now_ns, active=active, enabled=source.enabled, manual=source.manual, healthy=healthy, replay_validation=validation
        )[0]
      self.reason = 'qualified'
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      self._neutral('unavailable')

  def response_parameters(self):
    return (Parameter('response', self.descriptor.stage_revision, -0.03, 0.03, 0.03, 0.005, 1e-5 if self.descriptor.domain == 'curvature' else 0.01),)

  def _read_centre_ack(self, event, now_ns):
    return None

  def begin_frame(self, cs, vm, params, *, active, safety_limited, desired_curvature, curvature_limited, lat_delay, raw_model_curvature, model_source_ns):
    self.frame_sequence += 1
    if self.observation is not None:
      self.observation.begin_frame()
    if self.descriptor is None or not self.eligible:
      self.snapshot = self.replay_inputs = ()
      return
    try:
      from openpilot.starpilot.flm.controller_replay import capture_snapshot, frame_input

      self.snapshot = ()
      if self.identity and self.descriptor.domain != 'ford_curvature' and (not self.snapshot_ns or self.now_ns - self.snapshot_ns >= 1_000_000_000):
        if self.descriptor.domain == 'torque':
          self.snapshot = capture_snapshot(self.controller, vm).values
        else:
          self.snapshot = ()
        self.snapshot_ns = self.now_ns
        self.snapshot_sequence += 1
      self.replay_inputs = frame_input(
        cs,
        vm,
        params,
        active=active,
        safety_limited=safety_limited,
        desired_curvature=desired_curvature,
        curvature_limited=curvature_limited,
        lat_delay=lat_delay,
      ) + (
        ('control_frame', float(self.frame_sequence)),
        ('raw_model_curvature', float(raw_model_curvature)),
        ('model_source_ns.high', float(int(model_source_ns) >> 32)),
        ('model_source_ns.low', float(int(model_source_ns) & 0xFFFFFFFF)),
      )
      regime = vm_regime(dict(self.replay_inputs), self.vm_anchor)
      if regime is None or self.vm_anchor is not None and regime != self.vm_anchor:
        if self.validation is not None:
          self.replaced_vm_model_revision = self.validation.physical_model_revision
        self.eligible = False
        self._neutral('vehicle_model_material_change')
      self.vm_anchor = regime
      if self.observation is not None:
        self.observation.begin_frame()
        policy = getattr(getattr(self.controller, 'starpilot_extension', None), 'policy', None)
        self.prior_policy_output = float(getattr(policy, 'prev_output_torque', getattr(policy, 'previous_output', 0.0)))
        prior_ff = getattr(policy, 'previous_feedforward', 0.0)
        self.prior_policy_ff = 0.0 if prior_ff is None else float(prior_ff)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
      self.snapshot, self.replay_inputs = (), ()
      self._neutral('snapshot_unavailable')

  def stage_value(self, baseline):
    """Actual non-torque hook before feedback or live angle offset."""
    if not math.isfinite(baseline):
      self._neutral('invalid_stage')
      return baseline
    self.used = True
    self.stage = float(baseline)
    self.stage_effect = bool(baseline * self.coefficient)
    return baseline if self.coefficient == 0.0 else baseline * (1 + self.coefficient)

  def torque_residual(self, frame, *, stage_revision):
    self.stage, self.used = frame, True
    policy = getattr(getattr(self.controller, 'starpilot_extension', None), 'policy', None)
    if getattr(self.controller, 'flm_surface', None) is not None or getattr(policy, 'surface', None) is not None:
      self.live_manual = True
      self.eligible = False
      self._neutral('manual_surface')
      return 0.0, 0.0
    if self.torque_owner is None or self.reason != 'qualified':
      return 0.0, 0.0
    result = self.torque_owner.torque_residual(frame, stage_revision=stage_revision)
    self.torque_result = tuple(result)
    self.stage_effect = bool(result[0] * frame.baseline_ff or result[1] * frame.baseline_threshold)
    return result

  @property
  def torque_applied_coordinates(self):
    return self.torque_owner.owner.applied if self.torque_owner is not None else (0.0, 0.0)

  @property
  def applied_coordinates(self):
    if self.centre_source is not None:
      return self.centre_source.owner.owner.applied
    return self.torque_owner.owner.applied if self.torque_owner is not None else (0.0, 0.0)

  def observe_centre_stage(
    self, *, speed, setpoint, jerk, baseline_threshold, baseline_deadzone, friction_error, friction_scale=1.0, friction_parent_wrapper=False
  ):
    values = (
      ('baseline_threshold', float(baseline_threshold)),
      ('baseline_deadzone', float(baseline_deadzone)),
      ('friction_error', float(friction_error)),
      ('friction_scale', float(friction_scale)),
      ('friction_parent_wrapper', float(bool(friction_parent_wrapper))),
    )
    self.centre_raw = values if all(math.isfinite(value) for _, value in values) else ()

  def centre_residual(self, frame, *, stage_revision):
    self.centre_frame = frame
    if self.centre_source is None or self.reason != 'qualified':
      return 0.0, 0.0
    self.used = True
    result = self.centre_source.centre_residual(frame, stage_revision=stage_revision)
    self.centre_result = tuple(result)
    self.stage_effect = False
    return result

  def finish_centre_stage(self, *, actual_friction, baseline_friction):
    if self.centre_source is not None and all(math.isfinite(float(value)) for value in (actual_friction, baseline_friction)):
      self.stage_effect = bool(float(actual_friction) != float(baseline_friction))

  def torque_deadband(self, speed, *, stage_revision, setpoint=0.0, jerk=0.0):
    if self.torque_owner is None or self.reason != 'qualified':
      return 0.0
    self.used = True
    result = self.torque_owner.torque_deadband(speed, stage_revision=stage_revision, setpoint=setpoint, jerk=jerk)
    self.stage_effect = bool(result)
    return result

  def finish_frame(self, cs, vm, params, lac_log, **kwargs):
    try:
      self._finish_frame(cs, vm, params, lac_log, **kwargs)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError, RuntimeError):
      self.frame = None
      self._neutral('optional_capture_unavailable')

  def _finish_frame(self, cs, vm, params, lac_log, *, desired_curvature, curvature_limited, lat_delay, requested, selected_command=None):
    """Capture the actual same-frame controller inputs; never controller clones."""
    if self.descriptor is None or not self.eligible:
      self.frame = None
      return
    if not all(math.isfinite(float(value)) for value in (desired_curvature, lat_delay, requested, requested if selected_command is None else selected_command)):
      self.healthy = False
      self._neutral('invalid_output')
      self.frame = None
      return
    values = baseline_values(self.controller)
    p, i, d = (float(getattr(lac_log, key, 0.0)) for key in ('p', 'i', 'd'))
    self.frame = (
      cs,
      vm,
      params,
      lac_log,
      float(desired_curvature),
      bool(curvature_limited),
      float(lat_delay),
      float(requested),
      values,
      p,
      i,
      d,
      float(requested if selected_command is None else selected_command),
    )
    if self.descriptor is None:
      return
    coordinates = (self.coefficient,) if self.descriptor.domain != 'torque' else (self.applied_coordinates)
    applied = bool(self.used and self.stage_effect and self.reason == 'qualified' and any(coordinates) and self.active and self.healthy)
    self.outcome = ApplicationOutcome(
      self.identity,
      self.profile.sequence if self.profile is not None else 0,
      self.now_ns,
      'applied' if applied else 'collecting' if self.eligible else 'paused',
      coordinates,
      'actual_stage_used' if applied else self.reason,
      self.baseline_revision,
      self.validation.physical_model_revision if self.validation is not None else '',
    )

    if (
      self.centre_ack is not None
      and self.centre_source is not None
      and self.centre_frame is not None
      and self.used
      and self.reason == 'qualified'
      and self.active
      and self.healthy
      and self.eligible
    ):
      ack = self.centre_ack
      self.outcome = ApplicationOutcome(
        ack.identity,
        ack.profile_sequence,
        ack.control_ns,
        'applied',
        tuple(ack.actual_coordinates),
        'actual_centre_friction_observed',
        ack.baseline_revision,
        ack.physical_model_revision,
      )

  def capture_evidence(self, *, control_ns, state_ns, active, limited):
    if self.descriptor is None or self.frame is None or self.source is None or not self.identity:
      return None
    cs, vm, params, log, desired, curvature_limited, delay, requested, values, p, i, d, raw_command = self.frame
    if self.descriptor.domain == 'torque':
      # Exact policy-specific normalized counterfactual trace is mandatory.
      trace = self.observation.finish_frame(
        self.controller, log, selected_command=raw_command, prior_policy_output=self.prior_policy_output, prior_policy_ff=self.prior_policy_ff
      )
      if trace is None:
        return None
      schema, stage_values, coordinates = trace
      if self.centre_raw:
        stage_values = tuple(stage_values) + self.centre_raw
      stage_values = tuple(stage_values) + (
        ('actual_delta_ff', self.torque_result[0]),
        ('actual_delta_threshold', self.torque_result[1]),
        ('centre_threshold_delta', self.centre_result[0]),
        ('centre_extra_deadband_deg', self.centre_result[1]),
        ('centre_parameter_left', self.applied_coordinates[0] if self.centre_source is not None else 0.0),
        ('centre_parameter_right', self.applied_coordinates[1] if self.centre_source is not None else 0.0),
      )
      if self.centre_source is not None:
        coordinates = (0.0, 0.0)
      # Raw basis is identified by schema; separate learner actual replay turns
      # it into normalized same-state command sensitivities before collection.
      stage = self.observation.stage
      from openpilot.starpilot.flm.torque_adapter import gates

      objective = (
        self.torque_owner.objective
        if self.torque_owner is not None
        else Objective(
          'feedforward',
          'low' if cs.vEgo < 25 else 'high',
          'steady' if abs(stage.setpoint * stage.jerk) < 0.03 else 'turn_in' if stage.setpoint * stage.jerk > 0 else 'unwind',
        )
      )
      features = tuple(stage.baseline_ff * value for value in gates(objective, stage.speed, stage.setpoint, stage.jerk))
      prediction, response_revision = requested, 'torque-independent-local-physical-v1'
      command_domain = 'normalized_torque'
    elif self.descriptor.domain == 'ford_curvature':
      # Ford's actual final path angle belongs to the downstream Card host;
      # generic LatControlAngle output is not a valid curvature stage trace.
      return None
    else:
      if self.stage is None:
        return None
      actual_stage = dict(getattr(self.controller, 'response_stage', ()))
      baseline_stage = actual_stage.get('baseline_stage', float(self.stage))
      p, i, d = (actual_stage.get(key, fallback) for key, fallback in zip(('p', 'i', 'd'), (p, i, d), strict=True))
      features, coordinates = (baseline_stage,), (self.coefficient,)
      pre_limit = p + i + d + baseline_stage
      actual_pre_limit = actual_stage.get(
        'pre_limit', pre_limit + baseline_stage * self.coefficient if self.descriptor.domain in ('pid', 'curvature') else raw_command
      )
      prediction = pre_limit if self.descriptor.domain in ('pid', 'curvature') else requested - self.stage * self.coefficient
      schema, response_revision, command_domain = (
        self.descriptor.stage_revision,
        'passive-physical-command-response-v1',
        ('normalized_torque' if self.descriptor.domain == 'pid' else self.descriptor.domain),
      )
      if self.descriptor.domain in ('pid', 'curvature'):
        limited = bool(limited or abs(pre_limit + self.stage * self.coefficient - raw_command) > 1e-6)
      stage_values = (
        ('baseline_stage', baseline_stage),
        ('p', p),
        ('i', i),
        ('d', d),
        ('pre_limit', actual_pre_limit),
        ('desired_physical', actual_stage.get('desired_physical', -desired)),
        ('speed', float(cs.vEgo)),
        ('steering_angle', float(cs.steeringAngleDeg)),
        ('steering_rate', float(cs.steeringRateDeg)),
        ('angle_offset', float(params.angleOffsetDeg)),
        ('roll', float(params.roll)),
        ('steer_ratio', float(vm.sR)),
        ('desired_curvature', desired),
        ('lat_delay', delay),
        ('selected_command', raw_command),
        ('desired_angle_deg', baseline_stage + float(params.angleOffsetDeg)),
        ('desired_physical_accel', desired * float(cs.vEgo) ** 2),
        ('applied_stage', baseline_stage * (1 + self.coefficient)),
      )
    native_observed = int(getattr(self.native_witness, 'observedMonoTime', 0))
    native_expires = int(getattr(self.native_witness, 'validUntilMonoTime', 0))
    native_allowed = bool(
      self.native_required
      and self.native_witness is not None
      and active
      and getattr(self.native_witness, 'requestedLateral', False)
      and getattr(self.native_witness, 'lateralAllowed', False)
      and 0 < native_observed <= control_ns <= native_expires
    )
    if self.native_required and not native_allowed:
      self.eligible = False
      self._neutral('native_lease_unavailable')
      self.outcome = ApplicationOutcome(
        self.identity,
        self.profile.sequence if self.profile is not None else 0,
        self.now_ns,
        'paused',
        (0.0,) * len(coordinates),
        'native_lease_unavailable',
        self.baseline_revision,
        self.validation.physical_model_revision if self.validation is not None else '',
      )
    current_profile = bool(
      self.profile is not None
      and self.reason == 'qualified'
      and 0 < self.profile.observed_ns <= control_ns <= self.profile.expires_ns <= self.profile.observed_ns + SOURCE_LEASE_NS
    )
    if current_profile and self.centre_source is not None:
      key = (
        self.profile.sequence,
        self.profile.observed_ns,
        self.profile.expires_ns,
        self.source.source_epoch,
        tuple(self.applied_coordinates),
        self.baseline_revision,
        self.validation.physical_model_revision,
      )
      self.centre_history[control_ns] = (key, min(self.profile.expires_ns, self.source.expires_ns), tuple(p.name for p in self.profile.parameters))
      while len(self.centre_history) > 64:
        self.centre_history.popitem(last=False)
    return ControlEvidence(
      self.identity,
      self.generation,
      control_ns,
      state_ns,
      command_domain,
      self.descriptor.stage_revision,
      response_revision,
      requested,
      tuple(features),
      prediction,
      self.source.enabled,
      bool(self.source.manual or self.live_manual),
      active,
      bool(cs.canValid and not cs.canTimeout and self.healthy and self.eligible),
      bool(cs.steeringPressed),
      bool(cs.steerFaultTemporary or cs.steerFaultPermanent),
      bool(log.saturated),
      bool(limited or curvature_limited),
      False,
      False,
      schema,
      tuple(stage_values),
      tuple(coordinates),
      source_epoch=self.source.source_epoch,
      source_receipt_ns=self.source.observed_ns,
      controller_mode=self.descriptor.controller_mode,
      policy=self.descriptor.policy,
      baseline_revision=self.baseline_revision,
      baseline_values=values,
      controller_revision=self.descriptor.controller_revision,
      replay_snapshot=self.snapshot,
      replay_inputs=self.replay_inputs,
      snapshot_sequence=self.snapshot_sequence,
      turn_assist=self.descriptor.turn_assist,
      applied_parameter_names=tuple(p.name for p in self.profile.parameters) if current_profile else (),
      native_required=self.native_required,
      native_observed_ns=native_observed,
      native_expires_ns=native_expires,
      native_allowed=native_allowed,
      native_identity=self.native_identity,
      applied_profile_sequence=self.profile.sequence if current_profile else 0,
      applied_profile_observed_ns=self.profile.observed_ns if current_profile else 0,
      applied_profile_expires_ns=self.profile.expires_ns if current_profile else 0,
    )
