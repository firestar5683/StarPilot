"""Actual child dispatch for canonical full30 event trials, never a helper-only path."""

from typing import TypedDict, cast


from openpilot.starpilot.flm.clipping_quality import event_clipping_quality
from dataclasses import asdict
import itertools
import math

from openpilot.starpilot.flm.adaptive_profile import solve
from openpilot.starpilot.flm.controller_replay import ControllerReplay, pack_primitive_snapshot
from openpilot.starpilot.flm.event_controller_replay import EventControllerReplay
from openpilot.starpilot.flm.event_objective import EffectObjective
from openpilot.starpilot.flm.full_surface_profile import envelope_from_dict
from openpilot.starpilot.flm.torque_adapter import Objective
from openpilot.starpilot.flm.torque_emission_replay import delivered
from openpilot.starpilot.flm.torque_raw_fit import output_from_dict


class _EffectObjectiveFields(TypedDict):
  group: str
  names: tuple[str, ...]
  anchor_digest: str
  context_key: str


def _identified(engine, raw):
  # Selection uses actual feature support ONLY, before any target/loss. A
  # globally excited column cannot qualify episodes that lack that column.
  count = len(engine.objective.names)
  if not 1 <= count <= 4:
    raise ValueError('event feature coordinate bound')
  episodes, ids = [], set()
  for block in raw:
    if block['block_id'] in ids:
      raise ValueError('event feature duplicate episode')
    ids.add(block['block_id'])
    features = []
    for point in block['samples']:
      output = output_from_dict(point['output'])
      if output.limited or output.apply_ns not in engine.projected:
        continue
      if delivered(output) != point['physical']['applied_command']:
        raise ValueError('event feature actual motor coordinate')
      row = engine.projected[output.apply_ns][1]
      if len(row) != count or any(not math.isfinite(value) for value in row):
        raise ValueError('event feature encoded basis')
      features.append(row)
    if len(features) < 40:
      continue
    gram = tuple(tuple(sum(row[i] * row[j] for row in features) for j in range(count)) for i in range(count))
    episodes.append((len(features), gram))
  candidates = []
  for size in range(1, count + 1):
    for selected in itertools.combinations(range(count), size):
      # These are exactly the whole episodes whose selected coordinates meet
      # objective_excited's ORIGINAL per-episode RMS floor. Never pool absent
      # columns across episodes or borrow conditioning from discarded rows.
      eligible = tuple((length, gram) for length, gram in episodes if all(
        gram[i][i] / length >= engine.objective.parameters[i].excitation_floor**2 for i in selected))
      if len(eligible) < 8:
        continue
      length = sum(n for n, _ in eligible)
      gram = [[sum(matrix[i][j] for _, matrix in eligible) / length for j in selected] for i in selected]
      normalized = [[gram[i][j] / math.sqrt(gram[i][i] * gram[j][j]) for j in range(size)] for i in range(size)]
      try:
        if any(max(abs(value) for value in solve(normalized, [float(j == k) for j in range(size)])) > 100 for k in range(size)):
          continue
      except ValueError:
        continue
      # Fixed cardinality, eligible-row mean energy, canonical index order;
      # never tracking error, physical target, candidate loss or heldout gain.
      candidates.append((size, sum(gram[i][i] for i in range(size)), selected))
  if not candidates:
    return ()
  selected = max(candidates)[2]
  return tuple(engine.objective.names[i] for i in selected)


def fit_event_snapshot(payload, factory, replay_payload):
  if type(payload.get('event_version')) is not int or payload['event_version'] not in (2, 3, 4, 5, 6):
    raise ValueError('explicit event snapshot version')
  event_clipping_quality(payload)
  envelope = envelope_from_dict(payload['effect_envelope'])
  if payload['event_version'] in (4, 5, 6) and (payload.get('event_operation') != 'restore' or envelope.operation != 'restore'):
    raise ValueError('whole-map activation is restore-only')
  if payload['event_version'] == 3 and (payload.get('event_operation') != 'trial' or envelope.operation != 'trial'):
    raise ValueError('declared activation requires original trial operation')
  objective = EffectObjective(**cast(_EffectObjectiveFields, {**payload['event_objective'], 'names': tuple(payload['event_objective']['names'])}))
  if (envelope.trial_names != objective.names or envelope.trial_anchor != objective.anchor_digest or
      envelope.context_key != objective.context_key or envelope.source_epoch != objective.context_key or
      envelope.selected_baseline_revision != replay_payload['baseline_revision']):
    raise ValueError('event original source/trial anchor')
  legacy = Objective(**payload['objective'])
  replay_payload['objective'] = asdict(legacy)
  actual = ControllerReplay.from_snapshot(factory, legacy, pack_primitive_snapshot(replay_payload), rebuild=False)
  if envelope.operation == 'restore':
    if payload.get('event_version') not in (2, 4, 5, 6):
      raise ValueError('declared activation cannot replace full-map restore contract')
    if payload.get('event_operation') != 'restore':
      raise ValueError('explicit historical restore job required')
    from openpilot.starpilot.flm.event_restore_fit import fit_event_restore, prepare_fixed_restore_calibration
    engine = EventControllerReplay(actual, objective, envelope.replay_anchor(), restore_envelope=envelope)
    if payload['event_version'] in (4, 5, 6):
      from openpilot.starpilot.flm.restore_activation import build_restore_plan
      from openpilot.starpilot.flm.runtime_adapter_registry import canonical_physical_context
      prepared = prepare_fixed_restore_calibration(payload, engine, objective)
      if type(prepared) is dict:
        return prepared
      model, cutoff, events, stage = prepared
      plan = build_restore_plan(engine, model=model, cutoff_ns=cutoff, stage_events=stage,
        physical_context=canonical_physical_context(payload['physical_context']), envelope=envelope, restore_version=payload['event_version'])
      engine = EventControllerReplay(actual, objective, envelope.replay_anchor(), restore_envelope=envelope, activation_plan=plan)
    return fit_event_restore(payload, engine, objective)
  engine = EventControllerReplay(actual, objective, envelope.replay_anchor())
  activation_plan = None
  stage = payload.get('raw_blocks', payload.get('blocks', ()))
  if payload.get('event_version') == 3:
    from openpilot.starpilot.flm.event_activation import build_activation_plan
    from openpilot.starpilot.flm.event_raw_fit import prepare_fixed_event_calibration
    from openpilot.starpilot.flm.runtime_adapter_registry import canonical_physical_context
    prepared = prepare_fixed_event_calibration(payload, engine, objective)
    if type(prepared) is dict:
      return prepared
    model, cutoff, events, stage = prepared
    activation_plan = build_activation_plan(engine, model=model, cutoff_ns=cutoff, stage_events=stage,
      physical_context=canonical_physical_context(payload['physical_context']), quality_contract=event_clipping_quality(payload))
    engine = EventControllerReplay(actual, objective, envelope.replay_anchor(), activation_plan=activation_plan)
  engine.rebuild_causal_features()
  selected = _identified(engine, stage)
  if not selected:
    return {'status': 'collecting', 'reason': 'no_identifiable_canonical_coordinates', 'profile': None, 'validation': None,
      **({'event_version': 3, 'activation_plan': asdict(activation_plan), 'model_cutoff_ns': activation_plan.cutoff_ns}
         if activation_plan is not None else {})}
  if selected != objective.names:
    envelope = envelope.for_trial(selected)
    objective = EffectObjective(objective.group, selected, envelope.trial_anchor, objective.context_key)
    previous = engine
    engine = EventControllerReplay(actual, objective, envelope.replay_anchor(), activation_plan=activation_plan)
    if payload.get('event_version') != 3 or engine.reuse_subset_causal_features(previous) is not True:
      engine.rebuild_causal_features()
  from openpilot.starpilot.flm.event_raw_fit import fit_event_torque
  payload = {**payload, 'effect_envelope': asdict(envelope),
             'event_objective': asdict(objective),
             'prior': tuple(dict(envelope.prior_coordinates)[name] for name in selected)}
  return fit_event_torque(payload, engine, objective)
