"""Neutral commands and direction labels cannot manufacture bilateral evidence."""
from dataclasses import replace
import math

import pytest

from openpilot.starpilot.flm.event_physical import fit_event_physical
from openpilot.starpilot.flm.physical_response import PhysicalRow, fit_physical


IDENTITY = 'a' * 64
CONTEXT = 'exact-independent-sign-support'
LAG = 50_000_000


def cohort(signs):
  rows = []
  for block, sign in enumerate(signs):
    for sample in range(80):
      stamp = 1_000_000_000 + (block * 80 + sample) * 50_000_000
      command = sign * (.10 + sample * .004)
      rows.append(PhysicalRow(str(block), stamp, stamp + LAG, command,
                              1.98 * command + .002, CONTEXT,
                              'left' if command > 0 else 'right', True, False, False))
  return tuple(rows)


def event_fit(rows):
  return fit_event_physical(IDENTITY, CONTEXT, rows, lag_ns=LAG, now_ns=rows[-1].response_ns)


@pytest.mark.parametrize('neutral', [0.0, -0.0])
def test_two_positive_two_neutral_episodes_per_chronological_half_cannot_fit(neutral):
  rows = cohort((1., 1., neutral, neutral, 1., 1., neutral, neutral))
  assert len(rows) == 640 and len({row.block_id for row in rows}) == 8
  for half in (rows[:320], rows[320:]):
    assert sum(row.command > 0 for row in half) == 160
    assert sum(row.command == 0 for row in half) == 160
    assert not any(row.command < 0 for row in half)
    assert sum(row.direction == 'right' for row in half) == 160
  # Independent measured-response rule has ample positive-vs-zero variance
  # and exact heldout OLS; the sole missing qualification is negative support.
  train = rows[:320]
  mean = sum(row.command for row in train) / len(train)
  assert sum((row.command - mean)**2 for row in train) / len(train) > .05**2
  assert all(math.isclose(row.physical_response, 1.98 * row.command + .002, abs_tol=1e-15) for row in rows)
  assert event_fit(rows) is None


@pytest.mark.parametrize('neutral', [0.0, -0.0])
def test_neutral_observations_remain_valid_when_real_bilateral_support_exists(neutral):
  data = cohort((1., -1., 1., -1., 1., -1., 1., -1.))
  # Keep60 substantive sign rows perblock, hence120/sign/half and2independent
  # blocks, while preserving all neutral points inOLS/heldout/error evaluation.
  rows = tuple(replace(row, command=neutral, physical_response=.002, direction='right')
               if index % 80 < 20 else row for index, row in enumerate(data))
  model = event_fit(rows)
  assert model is not None
  assert math.isclose(model.slope, 1.98, abs_tol=1e-12)
  assert model.train_blocks == ('0', '1', '2', '3')
  assert model.heldout_blocks == ('4', '5', '6', '7')
  assert model.heldout_rmse < 1e-12


def test_real_negative_rows_only_in_one_episode_do_not_become_two_with_zero_episode():
  rows = cohort((1., -1., 1., 0., 1., -1., 1., 0.))
  assert event_fit(rows) is None


def test_legacy_wrong_sign_labels_cannot_create_bilateral_support():
  # Unlike event rows, legacyblocks must each have one direction. Preserve
  # chronology, nonzero variance and exactphysicalOLS, but forge half labels.
  data = cohort((1., 1., 1., 1., 1., 1., 1., 1.))
  rows = tuple(replace(row, direction='left' if int(row.block_id) % 2 == 0 else 'right') for row in data)
  assert all(row.command > 0 for row in rows)
  assert fit_physical(IDENTITY, 'normalized_torque', CONTEXT, rows, lag_ns=LAG,
                      min_excitation=.05, max_rmse=.05, now_ns=rows[-1].response_ns) is None
