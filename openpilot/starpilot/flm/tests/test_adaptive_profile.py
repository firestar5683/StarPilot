from dataclasses import replace

import pytest

from openpilot.starpilot.flm.adaptive_profile import Block, Parameter, ProfileOwner, ReplayValidation, CurrentAdmission, readmit_profile, Sample, evaluate

IDENTITY = 'a' * 64
PARAMETERS = (Parameter('ff_gain', 'stage1', -.03, .03, .03, .005),)


def blocks():
  result = []
  for index in range(8):
    rows = tuple(Sample(1_000_000_000 + (index * 40 + j) * 10_000_000,
                        990_000_000 + (index * 40 + j) * 10_000_000,
                        995_000_000 + (index * 40 + j) * 10_000_000,
                        (1. + j / 40,), .02 * (1. + j / 40), 1.) for j in range(40))
    result.append(Block(IDENTITY, str(index), 'left' if index % 2 else 'right', 'stage1', 'plant1', rows))
  return tuple(result)


def fit(data=None, parameters=PARAMETERS, **kwargs):
  return evaluate(IDENTITY, parameters, blocks() if data is None else data, now_ns=5_000_000_000,
                  required_cohorts=('left', 'right'), response_revision='plant1', **kwargs)


def test_identified_plant_and_original_expiry():
  profile = fit().profile
  assert profile is not None
  assert 0 < profile.coefficients[0] < .02
  assert profile.candidate_loss < profile.baseline_loss
  assert profile.expires_ns == profile.observed_ns + 500_000_000
  assert set(profile.train_ids).isdisjoint(profile.heldout_ids)


@pytest.mark.parametrize('field', ['override', 'fault', 'saturated', 'model_wobble', 'controller_chatter'])
def test_ineligible_response_never_trains(field):
  data = list(blocks())
  rows = list(data[0].samples)
  rows[0] = replace(rows[0], **{field: True})
  data[0] = replace(data[0], samples=tuple(rows))
  assert fit(tuple(data)).reason == 'evidence'


def test_wrong_physical_model_and_missing_cohort():
  data = tuple(replace(block, response_revision='unqualified') for block in blocks())
  assert fit(data).reason == 'provenance'
  data = tuple(replace(block, cohort='left') for block in blocks())
  assert fit(data).reason == 'independent_cohorts'


def test_heldout_regression_rejected():
  data = list(blocks())
  for index in range(4, 8):
    data[index] = replace(data[index], samples=tuple(replace(row, residual_target=-row.residual_target) for row in data[index].samples))
  assert fit(tuple(data)).status == 'rejected'


@pytest.mark.parametrize('epsilon', [0., 1e-9])
def test_confounded_basis_rejected(epsilon):
  parameters = PARAMETERS + (replace(PARAMETERS[0], name='friction'),)
  data = tuple(replace(block, samples=tuple(replace(row, features=(row.features[0], row.features[0] + epsilon))
                                          for row in block.samples)) for block in blocks())
  assert fit(data, parameters).reason == 'confounded_stage'


def test_gradual_adoption_same_sequence_mutation_and_exact_fallback():
  profile = fit().profile
  assert profile is not None
  owner = ProfileOwner(IDENTITY, PARAMETERS, baseline_revision="baseline1", physical_model_revision="plant1")
  kwargs = {"active": True, "enabled": True, "manual": False, "healthy": True,
            "replay_validation": ReplayValidation(profile, "baseline1", "plant1", True, True, .001)}
  first = owner.tick(profile, now_ns=5_000_000_000, **kwargs)
  assert first == (.00005,)
  changed = replace(profile, coefficients=(.01,))
  changed_validation = replace(kwargs["replay_validation"], profile=changed)
  assert owner.tick(changed, now_ns=5_010_000_000, **(kwargs | {"replay_validation": changed_validation})) == (0.,)
  assert owner.tick(profile, now_ns=5_020_000_000, **kwargs) == (.00005,)
  assert owner.tick(profile, now_ns=5_030_000_000, **(kwargs | {'manual': True})) == (0.,)
  assert owner.tick(profile, now_ns=5_040_000_000, **(kwargs | {'active': False})) == (0.,)
  assert owner.tick(profile, now_ns=5_550_000_001, **kwargs) == (0.,)


def test_live_revalidation_adopts_for_six_seconds_then_stale_withdraws():
  fit_profile = fit().profile
  assert fit_profile is not None
  validation = ReplayValidation(fit_profile, 'baseline', 'physical', True, True, .001)
  owner = ProfileOwner(IDENTITY, PARAMETERS, baseline_revision="baseline", physical_model_revision="physical")
  profile, replay = fit_profile, validation
  for tick in range(601):
    now = 5_000_000_000 + tick * 10_000_000
    if tick % 25 == 0:
      admission = CurrentAdmission(IDENTITY, 'baseline', 'physical', now, True, True, False, True)
      renewed = readmit_profile(fit_profile, validation, admission, now_ns=now, sequence=tick + 2)
      assert renewed is not None
      profile, replay = renewed
    value = owner.tick(profile, now_ns=now, active=True, enabled=True, manual=False, healthy=True, replay_validation=replay)
  assert value == profile.coefficients
  stale = replace(admission, source_ns=now - 100_000_001)
  assert readmit_profile(fit_profile, validation, stale, now_ns=now, sequence=1000) is None
  assert fit_profile.expires_ns == 5_500_000_000
  owner.last_ns = profile.expires_ns - 1
  assert owner.tick(profile, now_ns=profile.expires_ns + 1, active=True, enabled=True, manual=False,
                    healthy=True, replay_validation=replay) == (0.,)


@pytest.mark.parametrize('field', ['baseline_revision', 'physical_model_revision'])
def test_owner_rejects_wrong_current_revision(field):
  profile = fit().profile
  assert profile is not None
  owner = ProfileOwner(IDENTITY, PARAMETERS, baseline_revision='baseline', physical_model_revision='physical')
  validation = ReplayValidation(profile, 'baseline', 'physical', True, True, .001)
  assert owner.tick(profile, now_ns=5_000_000_000, active=True, enabled=True, manual=False,
                    healthy=True, replay_validation=replace(validation, **{field: 'different'})) == (0.,)


def test_historical_prior_regularizes_only_fresh_fit():
  neutral = fit().profile
  informed = fit(prior=(.02,)).profile
  assert neutral is not None and informed is not None
  assert abs(informed.coefficients[0] - .02) < abs(neutral.coefficients[0] - .02)
  assert informed.train_ids == neutral.train_ids
  assert informed.heldout_ids == neutral.heldout_ids
  assert fit((), prior=(.02,)).profile is None
  assert fit(prior=None) == fit()


@pytest.mark.parametrize('prior', [(.04,), (float('nan'),), (), [0.], (True,)])
def test_bad_historical_prior_cannot_admit(prior):
  assert fit(prior=prior).reason == 'historical_prior'


def test_prior_cannot_bypass_fresh_override_or_heldout_regression():
  data = list(blocks())
  data[0] = replace(data[0], samples=tuple(replace(row, override=True) for row in data[0].samples))
  assert fit(tuple(data), prior=(.02,)).reason == 'evidence'
  data = list(blocks())
  for index in range(4, 8):
    data[index] = replace(data[index], samples=tuple(replace(row, residual_target=-row.residual_target) for row in data[index].samples))
  assert fit(tuple(data), prior=(.02,)).status == 'rejected'
