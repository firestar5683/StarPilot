"""Independent whole-episode response gates, separate from legacy sign blocks."""
from dataclasses import replace
import math

from openpilot.starpilot.flm.event_physical import fit_event_physical
from openpilot.starpilot.flm.physical_response import PhysicalRow, fit_physical

BASE = 1_000_000_000


def episodes():
  result = []
  for episode in range(8):
    for sample in range(80):
      stamp = BASE + episode * 5_000_000_000 + sample * 50_000_000
      command = .15 * math.sin(2 * math.pi * (sample + .25) / 40)
      result.append(PhysicalRow(str(episode), stamp, stamp + 50_000_000,
        command, 1.98 * command + .002, 'physical-context', 'left' if command > 0 else 'right', True, False, False))
  return tuple(result)


def test_whole_mixed_sign_episodes_are_not_split_into_fake_independent_turns():
  rows = episodes()
  now = rows[-1].response_ns
  legacy = fit_physical('a' * 64, 'normalized_torque', 'physical-context', rows,
    lag_ns=50_000_000, min_excitation=.05, max_rmse=.05, now_ns=now)
  assert legacy is None  # Legacy one-sign block policy remains unchanged.
  model = fit_event_physical('a' * 64, 'physical-context', rows, lag_ns=50_000_000, now_ns=now)
  assert model is not None and abs(model.slope - 1.98) < 1e-12
  assert model.train_blocks == ('0', '1', '2', '3')
  assert model.heldout_blocks == ('4', '5', '6', '7')
  assert model.heldout_rmse < 1e-12
  assert len({row.block_id for row in rows}) == 8


def test_whole_episode_model_preserves_fault_clip_context_and_latency_gates():
  rows = episodes()
  for changed in (
    replace(rows[25], saturated=True), replace(rows[25], healthy=False),
    replace(rows[25], overridden=True), replace(rows[25], context='foreign'),
    replace(rows[25], response_ns=rows[25].response_ns + 30_000_001),
  ):
    altered = rows[:25] + (changed,) + rows[26:]
    assert fit_event_physical('a' * 64, 'physical-context', altered, lag_ns=50_000_000, now_ns=rows[-1].response_ns) is None


def test_one_whole_episode_cannot_be_relabelled_as_eight_independent_episodes():
  rows = tuple(replace(row, block_id='same-turn') for row in episodes())
  assert fit_event_physical('a' * 64, 'physical-context', rows, lag_ns=50_000_000, now_ns=rows[-1].response_ns) is None


def test_local_model_does_not_extrapolate_or_accept_quiet_unidentified_input():
  rows = episodes()
  quiet = tuple(replace(row, command=row.command / 100, physical_response=row.physical_response / 100) for row in rows)
  assert fit_event_physical('a' * 64, 'physical-context', quiet, lag_ns=50_000_000, now_ns=quiet[-1].response_ns) is None
  unsupported = tuple(replace(row, command=row.command * 2, physical_response=row.physical_response * 2)
                      if row.block_id in ('4', '5', '6', '7') else row for row in rows)
  assert fit_event_physical('a' * 64, 'physical-context', unsupported, lag_ns=50_000_000, now_ns=unsupported[-1].response_ns) is None


def test_zero_and_negative_zero_do_not_supply_negative_direction_support():
  for zero in (0.0, -0.0):
    for change_train in (True, False):
      rows = tuple(replace(row, command=zero, physical_response=.002, direction='right')
                   if row.command < 0 and (change_train or row.block_id in ('4', '5', '6', '7')) else row
                   for row in episodes())
      assert fit_event_physical('a' * 64, 'physical-context', rows,
                                lag_ns=50_000_000, now_ns=rows[-1].response_ns) is None


def test_tiny_positive_has_no_negative_direction_support_and_no_epsilon_is_used():
  for tiny, expected in ((1e-15, False), (-1e-15, True)):
    rows = tuple(replace(row, command=tiny, physical_response=1.98 * tiny + .002,
                         direction='left' if tiny > 0 else 'right') if row.command < 0 else row
                 for row in episodes())
    model = fit_event_physical('a' * 64, 'physical-context', rows,
                               lag_ns=50_000_000, now_ns=rows[-1].response_ns)
    assert (model is not None) is expected


def test_true_bilateral_original_control_still_qualifies():
  rows = episodes()
  assert any(row.command > 0 for row in rows) and any(row.command < 0 for row in rows)
  assert fit_event_physical('a' * 64, 'physical-context', rows,
                            lag_ns=50_000_000, now_ns=rows[-1].response_ns) is not None
