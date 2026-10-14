"""Executable typed producer/transport tests with explicit synthetic physical plant.

These prove joining/serialization/bounds, not registered controller qualification.
Actual factory/controller/runtime/native tests remain root-owned requirements.
"""

from dataclasses import replace

from openpilot.cereal import messaging
from openpilot.starpilot.flm.adaptive_profile import Parameter, Profile, ReplayValidation, Result, CurrentAdmission
from openpilot.starpilot.flm.fullrate_collector import (
  AppliedEvidence,
  ControlEvidence,
  FullrateCollector,
  PhysicalEvidence,
  drain,
)
from openpilot.starpilot.flm.learning_wire import (
  read_applied,
  read_control,
  read_runtime_admission,
  result_message,
  write_applied,
  write_control,
)
from openpilot.starpilot.flm.physical_response import PhysicalRow, fit_physical

BASE = 10_000_000_000
IDENTITY = '1' * 64


def model():
  rows = []
  for block in range(8):
    sign = 1 if block % 2 == 0 else -1
    for sample in range(60):
      stamp = BASE - 8_000_000_000 + block * 500_000_000 + sample * 5_000_000
      command = sign * (0.1 + 0.003 * sample)
      rows.append(PhysicalRow(str(block), stamp, stamp, command, 3 * command, 'physical', 'left' if sign > 0 else 'right', True, False, False))
  result = fit_physical(IDENTITY, 'torque', 'physical', rows, lag_ns=0, min_excitation=0.02, max_rmse=0.01, now_ns=BASE)
  assert result is not None
  return result


class SyntheticAdapter:
  """Known physical fixture inverse; no controller table or live PID error."""

  command_domain = 'torque'

  def __init__(self):
    self.model = model()
    self.observed = 0

  def parameters(self):
    return (Parameter('ff', 'stage', -0.03, 0.03, 0.03, 0.005),)

  def required_cohorts(self):
    return ('left', 'right')

  def physical_observable(self, row):
    return row.speed_mps > 15

  def cohort(self, control, physical):
    return 'left' if control.requested > 0 else 'right'

  def observe_model(self, *args, **kwargs):
    self.observed += 1

  def response_target(self, control, physical, applied, context):
    return self.model.inverse(physical['lateral_accel'])

  def current_admission(self, profile, control, output, context):
    return CurrentAdmission(
      control.identity, 'synthetic-baseline', 'synthetic-physical', min(control.control_ns, output.apply_ns), True, control.enabled, control.manual, True
    )

  def revalidate_fit(self, profile, control, output, context, blocks):
    # Explicit synthetic-only replay witness; actual registered controller replay
    # implementation must provide this contract before production acceptance.
    return ReplayValidation(profile, 'synthetic-baseline', 'synthetic-physical', True, True, 0.001)


def snapshots(stamp, sign=1):
  applied = sign * 0.2
  control = ControlEvidence(
    IDENTITY,
    0,
    stamp,
    stamp - 1_000_000,
    'linear_torque',
    'stage',
    'response',
    applied,
    (sign,),
    applied - sign * 0.012,
    True,
    False,
    True,
    True,
    False,
    False,
    False,
    False,
    False,
    False,
    'trace',
    (('f', applied - sign * 0.012), ('p', 0.0), ('i', 0.0)),
    (0.0,),
    '2' * 64,
    stamp,
    'standard',
    'synthetic',
    '3' * 64,
    (3.0,),
    'synthetic-controller',
  )
  output = AppliedEvidence(stamp, stamp, stamp + 1_000_000, 'torque', applied, True, True, False, False, False, True)
  response = PhysicalEvidence(stamp + 1_000_000, stamp + 1_000_000, 'cal', 'vm', 'lag', 0, 20.0, 3 * applied / 20.0, 0.0, 1.0, True, False, False, True)
  return control, output, response


def serialized_control(row):
  event = messaging.new_message('starpilotLateralState', valid=True, logMonoTime=row.control_ns)
  write_control(event.starpilotLateralState, row)
  return messaging.log_from_bytes(event.to_bytes())


def serialized_output(row):
  event = messaging.new_message('starpilotCarState', valid=True, logMonoTime=row.apply_ns)
  write_applied(event.starpilotCarState, row)
  return messaging.log_from_bytes(event.to_bytes())


def test_actual_serialized_producer_update_and_profile_payload_roundtrip():
  collector = FullrateCollector(SyntheticAdapter())
  stamp = BASE
  for block in range(8):
    collector.split('independent_synthetic_maneuver')
    for _sample in range(281):
      stamp += 50_000_000
      control, output, physical = snapshots(stamp, 1 if block % 2 == 0 else -1)
      assert collector.control(read_control(serialized_control(control)), stamp + 1_000_000)
      assert collector.output(read_applied(serialized_output(output)), stamp + 1_000_000)
      collector.physical(physical, stamp + 1_000_000)
    assert len(collector.blocks) == block + 1
  result = collector.fit(stamp + 1_000_000)
  assert result.status == 'qualified'
  admitted = collector.revalidate_fit(stamp + 1_000_000)
  event = result_message(admitted, collector.session, collector.live_profile_sequence, stamp + 1_000_000, replay_validation=collector.last_validation)
  decoded = read_runtime_admission(messaging.log_from_bytes(event.to_bytes()))
  assert decoded is not None and decoded[0] == admitted.profile
  assert decoded[1] == collector.last_validation
  assert len(decoded[0].train_ids) == 4 and len(decoded[0].heldout_ids) == 4
  assert decoded[0].coefficients[0] > 0


def test_swapped_consumed_control_and_changed_duplicate_cannot_join():
  collector = FullrateCollector(SyntheticAdapter())
  control, output, _ = snapshots(BASE)
  assert collector.control(control, BASE + 1_000_000)
  assert collector.output(replace(output, control_ns=BASE + 1), BASE + 1_000_000)
  assert not collector.ready
  assert not collector.control(replace(control, baseline_prediction=0.123), BASE + 1_000_000)
  assert not collector.ready and not collector.points


def test_stale_or_overridden_current_sources_do_not_renew_cached_fit():
  collector = FullrateCollector(SyntheticAdapter())
  control, output, physical = snapshots(BASE)
  for field in ('fault', 'override', 'limited'):
    collector.control(control, BASE + 1_000_000)
    assert not collector.output(replace(output, **{field: True}), BASE + 1_000_000)
    assert collector.revalidate_fit(BASE + 1_000_000) is None
  assert not collector.control(replace(control, manual=True), BASE + 1_000_000)
  assert collector.revalidate_fit(BASE + 1_000_000) is None


def test_fullrate_drain_accepts_actual_transport_reader():
  collector = FullrateCollector(SyntheticAdapter())
  control, _, _ = snapshots(BASE)
  events = [serialized_control(control)]
  decoded = []

  def decode(event, current, now):
    value = read_control(event)
    decoded.append(value)
    assert current.control(value, now)

  assert drain(object(), decode, lambda sock: events.pop(0) if events else None, collector, BASE + 1_000_000)
  assert decoded == [control] and not events
  assert collector.controls[BASE] == control
  assert collector.dropped == 0 and not collector.ready and not collector.points


def test_fullrate_drain_overrun_is_a_maneuver_boundary_not_silent_conflation():
  collector = FullrateCollector(SyntheticAdapter())
  control, output, _ = snapshots(BASE)
  collector.control(control, BASE + 1_000_000)
  collector.output(output, BASE + 1_000_000)
  events = [serialized_control(control)] * 33
  assert not drain(object(), lambda event, current, now: None, lambda sock: events.pop(0) if events else None, collector, BASE + 1_000_000)
  assert collector.dropped == 1 and not collector.ready and not collector.points


def test_legacy_custom_defaults_and_missing_replay_cannot_claim_profile():
  legacy = messaging.new_message('autoSteeringLearning', valid=True)
  assert read_runtime_admission(legacy.as_reader()) is None
  collector = FullrateCollector(SyntheticAdapter())
  profile = Profile(
    IDENTITY,
    1,
    BASE,
    BASE + 500_000_000,
    collector.adapter.parameters(),
    (0.01,),
    ('a', 'b', 'c', 'd'),
    ('e', 'f', 'g', 'h'),
    1.0,
    0.9,
    (('left', 0.1), ('right', 0.1)),
  )
  import pytest

  with pytest.raises(ValueError):
    result_message(Result('qualified', 'synthetic', profile), 'fixture', 1, BASE)


def test_exact_command_with_distinct_control_and_current_card_state_is_admitted():
  collector = FullrateCollector(SyntheticAdapter())
  control, output, _ = snapshots(BASE)
  assert control.state_ns != output.state_ns
  assert collector.control(read_control(serialized_control(control)), BASE + 1_000_000)
  assert collector.output(read_applied(serialized_output(output)), BASE + 1_000_000)
  assert collector.ready[-1] == (control, output)
  bad = replace(output, control_ns=BASE - 1)
  other = FullrateCollector(SyntheticAdapter())
  other.control(control, BASE + 1_000_000)
  other.output(bad, BASE + 1_000_000)
  assert not other.ready


def test_sparse_replay_snapshot_preserves_scalar_kinds_and_named_inputs():
  control, _, _ = snapshots(BASE)
  control = replace(
    control, replay_snapshot=(('pid.integrator', 0.01), ('active', True), ('mode', 'steady')), replay_inputs=(('speed', 20.0),), snapshot_sequence=1
  )
  assert read_control(serialized_control(control)) == control


def test_same_identity_dynamic_native_baseline_values_do_not_reset_stage_history():
  collector = FullrateCollector(SyntheticAdapter())
  control, output, _ = snapshots(BASE)
  collector.control(control, BASE + 1_000_000)
  collector.output(output, BASE + 1_000_000)
  collector.points.append(object())
  newer = replace(control, control_ns=BASE + 10_000_000, state_ns=BASE + 9_000_000, baseline_values=(3.01,))
  assert collector.control(newer, BASE + 11_000_000)
  assert len(collector.points) == 1
  epoch = replace(newer, control_ns=BASE + 20_000_000, state_ns=BASE + 19_000_000, source_epoch='4' * 64)
  assert collector.control(epoch, BASE + 21_000_000)
  assert not collector.points and not collector.blocks


def test_historical_coefficients_are_only_fresh_fit_prior_not_live_permission():
  collector = FullrateCollector(SyntheticAdapter())
  collector.restore_prior((0.01,))
  assert collector.prior_coefficients == (0.01,)
  assert collector.fit(BASE) is None
  assert collector.revalidate_fit(BASE) is None
  assert collector.result is None and collector.fit_result is None
  import pytest

  with pytest.raises(ValueError):
    collector.restore_prior((0.1,))


def test_required_native_witness_binds_exact_consumed_command_and_original_lease():
  control, output, _ = snapshots(BASE)
  control = replace(
    control, native_required=True, native_observed_ns=BASE - 1_000_000, native_expires_ns=BASE + 10_000_000, native_allowed=True, native_identity='4' * 64
  )
  output = replace(output, native_allowed=False)
  collector = FullrateCollector(SyntheticAdapter())
  assert collector.control(read_control(serialized_control(control)), BASE + 1_000_000)
  assert collector.output(read_applied(serialized_output(output)), BASE + 1_000_000)
  assert len(collector.ready) == 1 and collector.ready[-1][1].native_allowed
  assert collector.ready[-1][0].native_expires_ns == BASE + 10_000_000
  for native_change in ({'native_allowed': False}, {'native_observed_ns': BASE + 1}, {'native_expires_ns': BASE}, {'native_expires_ns': BASE + 200_000_001}):
    candidate = FullrateCollector(SyntheticAdapter())
    assert candidate.control(replace(control, **native_change), BASE + 1_000_000)
    assert candidate.output(output, BASE + 1_000_000)
    assert not candidate.ready
    assert candidate.reason == 'original_native_admission_unavailable'
  missing = FullrateCollector(SyntheticAdapter())
  assert missing.control(replace(control, native_allowed=False, native_observed_ns=0, native_expires_ns=0), BASE + 1_000_000)
  assert missing.output(output, BASE + 1_000_000)
  assert not missing.ready
  wrong = FullrateCollector(SyntheticAdapter())
  assert wrong.control(control, BASE + 1_000_000)
  assert wrong.output(replace(output, control_ns=BASE - 1), BASE + 1_000_000)
  assert not wrong.ready


def test_raw_parent_records_maneuvers_without_model_fit_normalization_or_inverse():
  class RawAdapter(SyntheticAdapter):
    raw_collection = True

    def __init__(self):
      self.snapshots = []

    def observe_model(self, *args, **kwargs):
      raise AssertionError('model fitting must run in child')

    def response_target(self, *args, **kwargs):
      raise AssertionError('physical inverse must run in child')

    def fit_job_snapshot(self, blocks, now_ns, sequence, prior, **kwargs):
      self.snapshots.append((blocks, kwargs))
      return {'version': 1, 'fixture': 'raw-job'}

  adapter = RawAdapter()
  collector = FullrateCollector(adapter)
  stamp = BASE
  # Healthy initial2s is required; then independent real direction boundaries
  # seal40point maneuvers without dropping the continuous physical chronology.
  for _tick in range(42):
    control, output, physical = snapshots(stamp)
    collector.control(control, output.apply_ns)
    collector.output(output, output.apply_ns)
    collector.physical(physical, physical.mono_ns)
    stamp += 50_000_000
  for block in range(17):
    sign = -1 if block % 2 == 0 else 1
    for _tick in range(40):
      control, output, physical = snapshots(stamp, sign)
      collector.control(control, output.apply_ns)
      collector.output(output, output.apply_ns)
      collector.physical(physical, physical.mono_ns)
      stamp += 50_000_000
  assert len(collector.blocks) == 16
  assert all(len(block.samples) == 40 for block in collector.blocks)
  sample = collector.blocks[0].samples[0]
  assert sample.control_ns == sample.control.control_ns
  assert sample.apply_ns == sample.output.apply_ns
  assert sample.physical['lateral_accel'] != sample.control.baseline_prediction
  assert collector.job_snapshot(stamp) == {'version': 1, 'fixture': 'raw-job'}
  assert collector.last_fit == 0 and collector.fit_block_sequence == 0
  assert adapter.snapshots[0][1]['control'] == collector.ready[-1][0]
  collector.mark_job_submitted(stamp)
  assert collector.last_fit == stamp
  assert collector.job_snapshot(stamp + 1) is None


def test_curvature_profile_excitation_floor_survives_typed_transport():
  parameter = Parameter('curvature_ff', 'curvature-stage', -0.03, 0.03, 0.03, 0.005, 1e-5)
  profile = Profile(
    IDENTITY, 1, BASE, BASE + 500_000_000, (parameter,), (0.01,), ('a', 'b', 'c', 'd'), ('e', 'f', 'g', 'h'), 1.0, 0.9, (('left', 0.1), ('right', 0.1))
  )
  validation = ReplayValidation(profile, 'baseline', 'model', True, True, 0.1)
  event = result_message(Result('qualified', 'qualified', profile), 'fixture', 1, BASE, replay_validation=validation)
  decoded = read_runtime_admission(messaging.log_from_bytes(event.to_bytes()))
  assert decoded == (profile, validation)
  assert decoded[0].parameters[0].excitation_floor == 1e-5
  event.autoSteeringLearning.learning.runtimeProfile.parameters[0].excitationFloor = 0.0
  assert read_runtime_admission(event.as_reader()) is None


def test_raw_parent_retains_original_pose_clock_bridge():
  class RawAdapter(SyntheticAdapter):
    raw_collection = True

    def __init__(self):
      pass

  collector = FullrateCollector(RawAdapter())
  for tick in range(42):
    control, output, physical = snapshots(BASE + tick * 50_000_000)
    physical = replace(physical, source_boot_ns=physical.mono_ns + 2_000_000_000, clock_offset_ns=2_000_000_000, clock_uncertainty_ns=40)
    collector.control(control, output.apply_ns)
    collector.output(output, output.apply_ns)
    collector.physical(physical, physical.mono_ns)
  raw = collector.raw_points[-1]
  assert raw.mono_ns == physical.mono_ns
  assert raw.physical['source_boot_ns'] == physical.source_boot_ns
  assert raw.physical['clock_offset_ns'] == physical.clock_offset_ns
  assert raw.physical['clock_uncertainty_ns'] == physical.clock_uncertainty_ns
  assert raw.physical['source_boot_ns'] - raw.physical['clock_offset_ns'] == raw.mono_ns
