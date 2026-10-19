"""Actual evidence_noise labels reach only the declared event trial capture.

Explicit synthetic producer rows test eligibility, never a native/current fit.
The original controller_chatter flag remains true on every retained object.
"""
from dataclasses import replace

import pytest

from openpilot.starpilot.flm.canonical_surface_adapter import GROUPS
from openpilot.starpilot.flm.event_collector import EventFullrateCollector
from openpilot.starpilot.flm.event_objective import EffectObjective
from openpilot.starpilot.flm.evidence_noise import noisy_frames
from openpilot.starpilot.flm.fullrate_collector import FullrateCollector
from openpilot.starpilot.flm.tests.test_friction_chatter_contract import noisy_payload
from openpilot.starpilot.flm.controller_replay import unpack_primitive_snapshot
from openpilot.starpilot.flm.tests.test_fullrate_pipeline import SyntheticAdapter, snapshots

ALLOWED = ('center', 'deadband.low', 'deadband.high', 'friction.left', 'friction.right')


def original_noisy_control(*, model=False):
  payload = noisy_payload(model=model)
  frames = unpack_primitive_snapshot(payload['replay'])['frames']
  labels = noisy_frames(frames, 'normalized_torque')
  frame = frames[-1]
  wobble, chatter = labels[frame['control_ns']]
  assert wobble is model
  if not model:
    assert chatter
  control, _, _ = snapshots(frame['control_ns'])
  return replace(control, requested=frame['actual_command'], model_wobble=wobble,
                 controller_chatter=chatter)


def event_collector(group, control):
  adapter = SyntheticAdapter()
  adapter.target_changed = False
  adapter.restore_envelope = None
  adapter.event_objective = EffectObjective(group, GROUPS[group], 'a' * 64, control.source_epoch)
  return EventFullrateCollector(adapter)


@pytest.mark.parametrize('group', tuple(GROUPS))
def test_noise_origin_flag_is_retained_only_by_exact_trial_groups(group):
  control = original_noisy_control()
  collector = event_collector(group, control)
  accepted = collector.control(control, control.control_ns)
  assert accepted is (group in ALLOWED)
  assert control.controller_chatter is True
  if accepted:
    assert collector.controls[control.control_ns] is control
    assert collector.controls[control.control_ns].controller_chatter is True
  else:
    assert not collector.controls and not collector.ready
  assert collector.fit_result is None and collector.result is None


@pytest.mark.parametrize('group', ALLOWED)
def test_model_noise_and_restore_remain_rejected_for_chatter_groups(group):
  noisy = original_noisy_control(model=True)
  collector = event_collector(group, noisy)
  assert not collector.control(noisy, noisy.control_ns)
  quiet_model = original_noisy_control()
  collector = event_collector(group, quiet_model)
  collector.adapter.restore_envelope = object()  # Presence only, no restore proof.
  assert not collector.control(quiet_model, quiet_model.control_ns)
  assert not collector.controls and quiet_model.controller_chatter


def test_default_foreign_or_absent_objective_never_retains_chatter():
  control = original_noisy_control()
  assert not FullrateCollector(SyntheticAdapter()).control(control, control.control_ns)
  absent = event_collector('center', control)
  absent.adapter.event_objective = None
  assert not absent.control(control, control.control_ns)
  foreign = event_collector('center', control)
  foreign.adapter.event_objective = EffectObjective('center', GROUPS['center'], 'a' * 64, 'f' * 64)
  assert not foreign.control(control, control.control_ns)


@pytest.mark.parametrize('field', ('fault', 'override', 'manual', 'saturated', 'limited', 'model_wobble'))
def test_other_existing_control_exclusions_survive_trial_chatter_capture(field):
  control = replace(original_noisy_control(), **{field: True})
  collector = event_collector('center', control)
  assert not collector.control(control, control.control_ns)
  assert not collector.controls and not collector.ready
  assert collector.fit_result is None and collector.result is None
