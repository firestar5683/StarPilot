"""Actual Controls capture to the live optional factory; no fit verdict supplied."""
from dataclasses import asdict, replace
from unittest import mock

import pytest

from opendbc.car.car_helpers import interfaces
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.hyundai.values import CAR as HKG
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.starpilot.flm.clipping_quality import RECORDED_DEBT, STATE_ALIGNED_DEBT, ZERO_REFERENCE_QUALITY, event_clipping_quality
from openpilot.starpilot.flm.event_fit_factory import fit_event_snapshot
from openpilot.starpilot.flm.event_objective import EffectObjective
from openpilot.starpilot.flm.learner_factory import from_evidence
from openpilot.starpilot.flm.runtime_adapter_registry import baseline_values, read_source
from openpilot.starpilot.flm.steerlearnerd import production_adapter_for_evidence
from openpilot.starpilot.flm.tests.test_fixed_manual_baseline import fixed_controls
from openpilot.starpilot.flm.tests.test_history_parent import parent, saved_prior
from openpilot.starpilot.flm.tests.test_registered_controls_global import controls_for, frame
from openpilot.starpilot.flm.torque_adapter import Objective

BASE = 400_000_000_000


def capture(controls):
  startup_rejections = 0
  for tick in range(151):
    now = BASE + tick * 10_000_000
    frame(controls, now, tick)
    runtime = controls.global_learning
    evidence = runtime.capture_evidence(control_ns=now, state_ns=now, active=True, limited=False)
    if runtime.eligible and evidence is not None and evidence.replay_snapshot:
      assert runtime.source is not None
      # Production's optional owner reads Params independently. Wire evidence
      # deliberately omits the local fixed-manual reconstruction tuple.
      source = read_source(controls.CP, controls.params, now_ns=now,
        calibration=(0., 0., 0.), vehicle_session='fixture-drive')
      assert source.source_epoch == runtime.source.source_epoch
      assert source.cp_sha256 == runtime.source.cp_sha256
      # The real optional owner retries a rejected constructor at subsequent
      # genuine checkpoints while the selected manual baseline settles.
      adapter = production_adapter_for_evidence(controls.CP, evidence, ('event', 'center'), source=source)
      if adapter is None:
        startup_rejections += 1
        continue
      return evidence, source, startup_rejections
  raise pytest.fail.Exception('actual source-bound controller checkpoint was not captured')


@pytest.mark.parametrize('platform,mode,domain', [
  (TOYOTA.TOYOTA_RAV4_TSS2, 'standard', 'torque'),
  (HKG.HYUNDAI_IONIQ_6, 'starpilot', 'torque'),
  (HONDA.HONDA_CIVIC, None, 'torque_pid'),
])
def test_actual_live_factory_adopts_both_domains_without_changing_legacy_defaults(platform, mode, domain):
  cp = interfaces[platform].get_non_essential_params(platform)
  with controls_for(cp, mode, True) as controls:
    evidence, source, _ = capture(controls)
    cp_bytes, tuning = controls.CP.as_builder().to_bytes(), baseline_values(controls.LaC)
    key = ('event', 'center')
    live = production_adapter_for_evidence(controls.CP, evidence, key, source=source)
    old = from_evidence(controls.CP, evidence, key, source=source)
    assert live is not None and old is not None
    assert controls.global_learning.descriptor.domain == domain
    assert live.replay_version == 3 and live.clipping_quality == ZERO_REFERENCE_QUALITY
    assert old.replay_version == 2 and old.clipping_quality == RECORDED_DEBT
    live.select_objective(('event', 'deadband.high'))
    assert live.replay_version == 3 and live.clipping_quality == ZERO_REFERENCE_QUALITY
    assert production_adapter_for_evidence(controls.CP, evidence, key, source=None) is None
    assert production_adapter_for_evidence(controls.CP, evidence, key, source=replace(source, enabled=False)) is None
    assert production_adapter_for_evidence(controls.CP, evidence, key, source=replace(source, manual=True)) is None
    assert controls.CP.as_builder().to_bytes() == cp_bytes and baseline_values(controls.LaC) == tuning


def test_actual_fixed_manual_baseline_is_preserved_by_live_factory():
  with fixed_controls() as (controls, _):
    evidence, source, startup_rejections = capture(controls)
    assert startup_rejections >= 1  # Actual first manual-ramp checkpoint is not constructor-admissible.
    before = baseline_values(controls.LaC)
    cp_bytes = controls.CP.as_builder().to_bytes()
    adapter = production_adapter_for_evidence(controls.CP, evidence, ('event', 'center'), source=source)
    assert adapter is not None and source.manual_baseline
    assert adapter.factory.manual_baseline == source.manual_baseline
    assert adapter.baseline_revision == controls.global_learning.baseline_revision
    assert baseline_values(controls.LaC) == before and controls.CP.as_builder().to_bytes() == cp_bytes


def test_history_child_keeps_distinct_recorded_debt_whole_map_contract():
  # Only dispatch is stubbed: no controller/native/model qualification is
  # fabricated, no profile is constructed or admitted by this boundary test.
  owner = parent()
  owner.install_full_prior(saved_prior(owner.envelope))
  envelope = owner.restore_envelope
  objective = EffectObjective('ff.left', envelope.trial_names, envelope.trial_anchor, envelope.context_key)
  payload = {'event_version': 2, 'event_operation': 'restore', 'effect_envelope': asdict(envelope),
    'event_objective': asdict(objective), 'objective': asdict(Objective('feedforward', 'high', 'steady'))}
  assert event_clipping_quality(payload) == RECORDED_DEBT
  expected = {'status': 'collecting', 'reason': 'test-dispatch-only'}
  with mock.patch('openpilot.starpilot.flm.event_fit_factory.ControllerReplay.from_snapshot'), \
       mock.patch('openpilot.starpilot.flm.event_fit_factory.EventControllerReplay') as engine, \
       mock.patch('openpilot.starpilot.flm.event_restore_fit.fit_event_restore', return_value=expected) as restore:
    assert fit_event_snapshot(payload, object(), {'baseline_revision': envelope.selected_baseline_revision}) is expected
    assert engine.call_args.kwargs['restore_envelope'] == envelope
    assert restore.call_count == 1
  with pytest.raises(ValueError, match='version3'):
    event_clipping_quality({**payload, 'event_clipping_quality': STATE_ALIGNED_DEBT})
  with pytest.raises(ValueError, match='original trial operation'):
    fit_event_snapshot({**payload, 'event_version': 3}, object(), {'baseline_revision': envelope.selected_baseline_revision})
