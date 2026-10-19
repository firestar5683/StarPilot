"""Actual detector/regroup/storage, synthetic goals; no model or fit authority."""
from types import SimpleNamespace

import pytest
from openpilot.starpilot.flm.event_windows import GROUPING_REVISION, regroup_whole_events, whole_event_windows
from openpilot.starpilot.flm.event_storage import select_whole_event_snapshot, source_windows


def fixture(large_count=60):
  # Two complete large episodes then a complete subtle cycle, using the REAL
  # production detector. Source controls exist through the zero-row interval.
  goals = [.3] * large_count + [-.3] * large_count + [0.] * 60 + [.1] * 30 + [-.1] * 30 + [.1] * 30 + [-.1] * 30
  frames = tuple(SimpleNamespace(control_ns=1_000_000_000 + i * 10_000_000,
    frame_sequence=i + 1, healthy=True, desired_physical_accel=value) for i, value in enumerate(goals))
  engine = SimpleNamespace(records=frames, replay_windows=(), _frame_context=lambda frame: frame.healthy,
    checkpoints=((frames[0].control_ns, None),), identity='a' * 64, baseline_revision='original-baseline')
  engine.replay_windows = source_windows(engine)
  events = whole_event_windows(engine)
  assert [event[3] for event in events] == ['large', 'large', 'subtle']
  objective = SimpleNamespace(context_key='original-context', required_cohorts=('whole',))
  def points(event, count):
    _, start, end, _ = event
    stamps = [frame.control_ns for frame in frames if start <= frame.control_ns <= end]
    assert len(stamps) >= count
    return tuple({'control_ns': stamp, 'apply_ns': stamp + 1, 'mono_ns': stamp + 2,
      'original_marker': (start, i)} for i, stamp in enumerate(stamps[:count]))
  def packet(rows, identity=None):
    return {'identity': engine.identity if identity is None else identity, 'samples': rows}
  return engine, events, objective, points, packet


def test_complete_mixed_kinds_combine_once_without_splitting_or_duplicate_support():
  engine, events, objective, points, packet = fixture()
  a, b = points(events[1], 20), points(events[2], 20)
  blocks = regroup_whole_events(engine, (packet(a + b),), objective)
  assert len(blocks) == 1 and len(blocks[0]['samples']) == 40
  assert blocks[0]['samples'] == a + b
  assert all(x is y for x, y in zip(blocks[0]['samples'], a + b, strict=True))
  assert [boundary[2] for boundary in blocks[0]['event_windows']] == ['large', 'subtle']
  assert blocks[0]['grouping_revision'] == GROUPING_REVISION
  assert blocks[0]['block_id'].startswith('event-v3:')


def test_zero_row_episode_retains_prior_support_and_full_original_interval():
  engine, events, objective, points, packet = fixture()
  a, b = points(events[0], 20), points(events[2], 20)
  packets = (packet(a + b),)
  blocks = regroup_whole_events(engine, packets, objective)
  assert len(blocks) == 1 and blocks[0]['samples'] == a + b
  assert len(blocks[0]['event_windows']) == 2  # Empty episode has no boundary/ID support.
  selected, windows = select_whole_event_snapshot(engine, packets, objective)
  assert len(selected) == 1
  empty_start, empty_end = events[1][1:3]
  assert any(start <= empty_start <= empty_end <= end for start, end in windows)
  assert all(any(start <= frame.control_ns <= end for start, end in windows)
             for frame in engine.records if empty_start <= frame.control_ns <= empty_end)


def test_real_unhealthy_window_barrier_cannot_be_bridged_by_zero_row_retention():
  engine, events, objective, points, packet = fixture()
  a, b = points(events[0], 20), points(events[2], 20)
  engine.records[150].healthy = False
  engine.replay_windows = source_windows(SimpleNamespace(records=engine.records, replay_windows=(), _frame_context=engine._frame_context))
  assert len(engine.replay_windows) == 2
  assert not regroup_whole_events(engine, (packet(a + b),), objective)


def test_same_total_thirty_nine_remains_insufficient_and_foreign_identity_rejected():
  engine, events, objective, points, packet = fixture()
  rows = points(events[0], 20) + points(events[2], 19)
  assert not regroup_whole_events(engine, (packet(rows),), objective)
  with pytest.raises(ValueError, match='storage identity'):
    regroup_whole_events(engine, (packet(rows, 'foreign'),), objective)


def test_boundary_kind_and_intervening_complete_interval_are_bound_to_id():
  engine, events, objective, points, packet = fixture()
  rows = points(events[0], 20) + points(events[2], 20)
  first = regroup_whole_events(engine, (packet(rows),), objective)[0]
  engine.records[30].desired_physical_accel = -.1  # Alter a SUPPORTED episode boundary, not the zero-row gap.
  second = regroup_whole_events(engine, (packet(rows),), objective)
  assert not second or second[0]['block_id'] != first['block_id']



def test_missing_original_checkpoint_still_rejects_entire_complete_bundle():
  engine, events, objective, points, packet = fixture()
  rows = points(events[0], 20) + points(events[2], 20)
  engine.checkpoints = ()
  diagnostics = {}
  selected, windows = select_whole_event_snapshot(engine, (packet(rows),), objective, diagnostics=diagnostics)
  assert not selected and not windows
  assert diagnostics['missingCheckpoint'] == 1


def test_oversized_complete_episode_is_still_discarded_not_phase_sliced():
  engine, events, objective, points, packet = fixture(large_count=300)
  rows = points(events[0], 20) + points(events[1], 241) + points(events[2], 20)
  # Original oversized-episode barrier drops prior pending; final20 cannot form40.
  assert not regroup_whole_events(engine, (packet(rows),), objective)


def test_missing_frame_inside_zero_row_interval_cannot_be_skipped_from_full_replay():
  engine, events, objective, points, packet = fixture()
  rows = points(events[0], 20) + points(events[2], 20)
  engine.records = engine.records[:150] + engine.records[151:]
  engine.replay_windows = source_windows(SimpleNamespace(records=engine.records, replay_windows=(), _frame_context=engine._frame_context))
  assert len(engine.replay_windows) == 2
  assert not regroup_whole_events(engine, (packet(rows),), objective)
