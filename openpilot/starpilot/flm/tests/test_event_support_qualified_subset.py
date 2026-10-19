"""Feature-support policy unit tests, NOT manufactured physical derivatives.

Explicit synthetic matrices isolate the actual selector and excitation gates.
Codec/delivery stubs supply no native permission, fit, profile or validation.
Actual causal derivative, source, native and heldout regressions remain required.
"""
from types import SimpleNamespace

import pytest

from openpilot.starpilot.flm import event_fit_factory as factory
from openpilot.starpilot.flm.canonical_surface_adapter import GROUPS
from openpilot.starpilot.flm.event_objective import EffectObjective
from openpilot.starpilot.flm.event_raw_fit import objective_excited


def case(monkeypatch, vectors, *, group='deadband.low'):
  names = GROUPS[group]
  assert all(len(vector) == len(names) for vector in vectors)
  objective = EffectObjective(group, names, 'a' * 64, 'b' * 64)
  projected, events = {}, []
  stamp = 1_000_000_000
  for index, vector in enumerate(vectors):
    points = []
    for _ in range(40):
      stamp += 50_000_000
      projected[stamp] = (0., tuple(vector))
      points.append({'apply_ns': stamp, 'output': {'apply_ns': stamp, 'limited': False},
                     'physical': {'applied_command': 0.}})
    events.append({'block_id': 'synthetic-complete-episode-' + str(index), 'samples': tuple(points)})
  monkeypatch.setattr(factory, 'output_from_dict', lambda value: SimpleNamespace(**value))
  monkeypatch.setattr(factory, 'delivered', lambda output: 0.)
  return SimpleNamespace(objective=objective, projected=projected), tuple(events)


def support(engine, events, selected):
  indices = tuple(engine.objective.names.index(name) for name in selected)
  objective = EffectObjective(engine.objective.group, selected, 'a' * 64, 'b' * 64)
  narrowed = SimpleNamespace(projected={stamp: (baseline, tuple(row[i] for i in indices))
    for stamp, (baseline, row) in engine.projected.items()})
  return tuple(event for event in events if objective_excited(event, narrowed, objective))


def test_disjoint_speed_bands_cannot_make_every_stage_episode_unexcited(monkeypatch):
  # Actual deadband interpolation pattern at stable2/5/10m/s, represented
  # by explicit unit-test features rather than claiming physical derivatives.
  engine, events = case(monkeypatch, [(.6,.4,0.)] * 6 + [(0.,1.,0.)] * 5 + [(0.,0.,1.)] * 5)
  selected = factory._identified(engine, events)
  assert selected == ('center_deadband_low_deg',)
  assert len(support(engine, events, selected)) == 11
  assert all(len(event['samples']) == 40 for event in events)


def test_conditioning_cannot_be_borrowed_from_discarded_episodes(monkeypatch):
  # Both columns exist globally, but every jointly supported episode has
  # identical columns. The other episodes cannot rescue the joint Gram.
  engine, events = case(monkeypatch, [(.1,.1)] * 8 + [(.1,0.)] * 8, group='center')
  selected = factory._identified(engine, events)
  assert len(selected) == 1
  assert len(support(engine, events, selected)) >= 8


def test_seven_supported_episodes_are_not_eight_or_disjoint_heldout(monkeypatch):
  engine, events = case(monkeypatch, [(.1,.1)] * 7, group='center')
  assert factory._identified(engine, events) == ()


def test_original_floor_is_not_lowered_to_obtain_a_subset(monkeypatch):
  engine, events = case(monkeypatch, [(.009,.009)] * 8, group='center')
  assert factory._identified(engine, events) == ()


def test_full_jointly_supported_conditioned_group_remains_selected(monkeypatch):
  engine, events = case(monkeypatch, [(.1,.02)] * 4 + [(.02,.1)] * 4, group='center')
  assert factory._identified(engine, events) == engine.objective.names
  assert len(support(engine, events, engine.objective.names)) == 8


def test_duplicate_episode_cannot_manufacture_minimum_support(monkeypatch):
  engine, events = case(monkeypatch, [(.1,.1)] * 7, group='center')
  with pytest.raises(ValueError, match='duplicate episode'):
    factory._identified(engine, events + (events[-1],))


def test_selection_never_reads_targets_or_mutates_rows(monkeypatch):
  engine, events = case(monkeypatch, [(.1,.02)] * 4 + [(.02,.1)] * 4, group='center')
  original = tuple(tuple(event['samples']) for event in events)
  first = factory._identified(engine, events)
  for event in events:
    for point in event['samples']:
      point['physical']['lateral_accel'] = float('nan')
      point['untrusted_loss'] = float('-inf')
  assert factory._identified(engine, events) == first
  assert all(a is b for event, rows in zip(events, original, strict=True)
             for a, b in zip(event['samples'], rows, strict=True))


@pytest.mark.parametrize('fault', ('limited', 'missing-projection'))
def test_seven_eligible_episodes_cannot_use_an_incomplete_eighth(monkeypatch, fault):
  engine, events = case(monkeypatch, [(.1,.02)] * 4 + [(.02,.1)] * 4, group='center')
  point = events[-1]['samples'][-1]
  if fault == 'limited':
    point['output']['limited'] = True
  else:
    del engine.projected[point['apply_ns']]
  # Original complete-episode minimum40 cannot borrow a skipped endpoint.
  assert factory._identified(engine, events) == ()


@pytest.mark.parametrize('row', ((.1,), (.1, float('nan'))))
def test_malformed_or_nonfinite_encoded_basis_fails_closed(monkeypatch, row):
  engine, events = case(monkeypatch, [(.1,.02)] * 4 + [(.02,.1)] * 4, group='center')
  stamp = events[0]['samples'][0]['apply_ns']
  engine.projected[stamp] = (0., row)
  with pytest.raises(ValueError, match='encoded basis'):
    factory._identified(engine, events)


def test_actual_encoder_endpoint_repeated_under_new_packet_id_is_rejected_before_model(tmp_path, monkeypatch):
  # Existing registered CI/CAN fixture supplies actual projections and verified
  # public-health fixture receipts. Synthetic physical metadata here is ONLY a
  # parser/provenance negative: no physical model/profile/current proof exists.
  from dataclasses import asdict, replace
  from opendbc.car.toyota.values import CAR
  from opendbc.car.steering_projection import projection_to_dict
  from openpilot.starpilot.flm.controller_replay import ControllerReplay, SelectedControllerFactory
  from openpilot.starpilot.flm.full_surface_profile import FullSurfaceEnvelope
  from openpilot.starpilot.flm.torque_adapter import Objective
  from openpilot.starpilot.flm.torque_emission_replay import delivered
  from openpilot.starpilot.flm import event_raw_fit
  from openpilot.starpilot.flm.runtime_adapter_registry import car_params_digest
  from openpilot.starpilot.flm.tests.test_fullrate_pipeline import snapshots
  from openpilot.starpilot.flm.tests.test_torque_emission_join import interface, settle, cc, emitted

  ci = interface(CAR.TOYOTA_COROLLA_TSS2)
  command = cc(.01)
  settle(ci, command)
  context = ('a' * 64, 'b' * 64, 'c' * 64, 0)
  engine, points = None, []
  for _ in range(160):
    pair = emitted(ci, command, tmp_path)
    if pair is None:
      continue
    actual, output = pair
    original, _, _ = snapshots(actual.control_ns)
    control = replace(original, identity=actual.identity, domain='normalized_torque',
      requested=actual.requested, source_epoch=actual.source_epoch,
      source_receipt_ns=actual.control_ns, baseline_revision=actual.baseline_revision)
    if engine is None:
      selected = SelectedControllerFactory(ci.CP, 'standard', turn_assist=False)
      engine = ControllerReplay(selected, Objective('feedforward', 'high', 'steady'),
        identity=control.identity, baseline_revision=control.baseline_revision)
    assert engine.emissions.record_carrier(output)
    assert engine.emissions.record(control, output)
    assert engine.applied_matches(control, output)
    output_row = asdict(output)
    output_row['projection'] = projection_to_dict(output.projection)
    points.append({'control_ns': control.control_ns, 'apply_ns': output.apply_ns,
      'mono_ns': output.apply_ns + 1, 'control': asdict(control), 'output': output_row,
      'physical_context': context, 'physical': {'applied_command': delivered(output), 'lateral_accel': 0.}})
    if len(points) == 40:
      break
  assert len(points) == 40
  envelope = FullSurfaceEnvelope.initial(cp_sha256=car_params_digest(ci.CP), controller_revision='parser-negative-fixture',
    source_epoch=control.source_epoch, reset_generation='0', selected_baseline_revision=control.baseline_revision,
    trial_names=GROUPS['deadband.low'])
  objective = EffectObjective('deadband.low', envelope.trial_names, envelope.trial_anchor, envelope.context_key)
  # First packet has40 different genuine encoded endpoints; the next NEW ID
  # repeats them. Renaming a packet cannot manufacture independent support.
  packets = tuple({'identity': engine.identity, 'block_id': 'distinct-packet-' + str(index),
                   'samples': tuple(points)} for index in range(8))
  payload = {'effect_envelope': asdict(envelope), 'physical_context': context, 'raw_blocks': packets}
  def no_model(*args, **kwargs):
    raise AssertionError('duplicate endpoints must fail before physical fitting')
  monkeypatch.setattr(event_raw_fit, 'fit_event_physical', no_model)
  with pytest.raises(ValueError, match='exact consumed physical endpoint'):
    event_raw_fit.prepare_fixed_event_calibration(payload, engine, objective)
