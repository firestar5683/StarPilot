"""Actual parent selection/collector/reporter; synthetic goals confer no fit proof."""
from collections import deque
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest

from openpilot.starpilot.flm.event_collection import EventCollectionAdapter
from openpilot.starpilot.flm.event_collector import EventFullrateCollector
from openpilot.starpilot.flm.fullrate_collector import RawBlock, RawPoint
from openpilot.starpilot.flm.training_report import read_report
from openpilot.starpilot.flm.tests.test_fullrate_pipeline import snapshots
from openpilot.starpilot.flm.tests.test_training_report import NOW, fixture, publish


def actual_selection_collector(count, *, checkpoint=True):
  control, output, _ = snapshots(NOW)
  # Real detector sees alternating whole large episodes and final recovery.
  goals = [(.3 if index % 2 == 0 else -.3) for index in range(count) for _ in range(60)] + [0.] * 60
  frames = tuple(SimpleNamespace(control_ns=NOW + tick * 10_000_000, frame_sequence=tick + 1,
    desired_physical_accel=goal) for tick, goal in enumerate(goals))
  adapter = EventCollectionAdapter.__new__(EventCollectionAdapter)
  adapter.envelope = object()
  cast(SimpleNamespace, adapter).event_objective = SimpleNamespace(context_key='context', required_cohorts=('whole',))
  cast(SimpleNamespace, adapter).objective = SimpleNamespace(required_cohorts=())
  adapter.key = ('event', 'center')
  adapter.snapshot_readiness = None
  adapter.model = None
  cast(SimpleNamespace, adapter).replay = SimpleNamespace(records=frames, replay_windows=(), _frame_context=lambda _frame: True,
    checkpoints=((NOW, None),) if checkpoint else (), identity=control.identity, baseline_revision='baseline')
  collector = EventFullrateCollector(adapter)
  cast(SimpleNamespace, collector).context = ('source',)
  cast(SimpleNamespace, collector).physical_context = ('physical',)
  collector.ready.append((control, output))
  points = tuple(RawPoint(frame.control_ns, frame.control_ns + 1, frame.control_ns + 2,
    control, output, {}, ('physical',)) for frame in frames[:-60])
  collector.blocks = deque((RawBlock(control.identity, str(index), 'whole', 'stage', 'response', points[index:index + 40])
    for index in range(0, len(points), 40)), maxlen=64)
  collector.block_sequence = len(collector.blocks)
  return collector


@pytest.mark.parametrize('count,checkpoint,reason,whole,selected', (
  (12, True, 'whole_physical_event_support', 12, 12),
  (20, False, 'whole_event_export_support', 20, 0),
))
def test_real_snapshot_decline_reaches_galaxy_report_without_rescanning(tmp_path, count, checkpoint, reason, whole, selected):
  collector = actual_selection_collector(count, checkpoint=checkpoint)
  _, _, reporter, source, path = fixture(tmp_path)
  with patch('openpilot.starpilot.flm.event_storage.regroup_whole_events',
             wraps=__import__('openpilot.starpilot.flm.event_windows', fromlist=['regroup_whole_events']).regroup_whole_events) as regroup:
    assert collector.job_snapshot(NOW) is None
    for tick in range(1, 21):
      assert collector.job_snapshot(NOW + tick * 50_000_000) is None
    assert regroup.call_count == 1
    publish(reporter, collector, source)
    publish(reporter, collector, source, now=NOW + 1_000_000_000)
    assert regroup.call_count == 1
  row = read_report(path, now_ns=NOW + 1_000_000_000)['current']
  assert row is not None
  readiness = row['details']['Snapshot readiness']
  assert readiness['reason'] == reason
  assert (readiness['wholeBundles'], readiness['selectedBundles']) == (whole, selected)
  assert (readiness['requiredBundles'], readiness['requiredCalibrationBundles'], readiness['requiredLaterBundles']) == (16, 8, 8)
  assert readiness['childQualification'] == 'not_yet_evaluated'
  assert readiness['ageSeconds'] == 1.
  assert readiness['missingCheckpoint'] == (0 if checkpoint else 20)
  assert row['details']['Snapshot selection attempts (collector lifetime)'] == row['details']['Snapshot selections declined (collector lifetime)'] == 1
  assert row['details']['Submitted fit jobs (reporter lifetime)'] == 0
  assert not row['details']['Parent fit profile retained']
  assert not row['details']['Collector admission result retained']
  assert not row['application']['applied']
  assert collector.fit_block_sequence == 0
  assert collector.job_snapshot(NOW + 60_000_000_000) is None
  assert collector.snapshot_attempts == 2


def test_context_reset_discards_cached_readiness_and_keeps_source_guard(tmp_path):
  collector = actual_selection_collector(12)
  assert collector.job_snapshot(NOW) is None
  collector.split('manual_or_source_changed', reset=True)
  assert collector.snapshot_readiness is collector.adapter.snapshot_readiness is None
  assert collector.job_snapshot(NOW + 60_000_000_000) is None
  assert collector.snapshot_readiness['reason'] in ('event_storage_packet_support', 'no_current_controller_evidence')
  assert collector.snapshot_attempts == 1
  assert not collector.blocks and not collector.ready
  assert collector.fit_result is None and collector.result is None


def test_last_unsuccessful_child_result_remains_distinct_from_newer_result(tmp_path):
  from openpilot.starpilot.flm.adaptive_profile import Result
  collector, _, reporter, source, path = fixture(tmp_path)
  collector.adapter.event_collection = True
  reporter.fitted(Result('rejected', 'independent_physical_model', None), ('event', 'center'))
  reporter.fitted(SimpleNamespace(status='qualified', reason='qualified_actual_replay', profile=object()), ('event', 'ff.left'))
  publish(reporter, collector, source)
  row = read_report(path, now_ns=NOW)['current']
  assert row['details']['Last unsuccessful fit'][:2] == ['rejected', 'independent_physical_model']
  assert row['details']['Last fit'][:2] == ['qualified', 'qualified_actual_replay']
  assert not row['application']['applied']


@pytest.mark.parametrize('changed', ('objective', 'source', 'physical', 'prior'))
def test_reporter_during_cooldown_cannot_reuse_other_context_counts(tmp_path, changed):
  collector = actual_selection_collector(12)
  assert collector.job_snapshot(NOW) is None
  attempts = collector.snapshot_attempts
  if changed == 'objective':
    collector.adapter._event_initialized = True
    collector.adapter.envelope = None
    collector.adapter.select_objective(('event', 'ff.left'))
  elif changed == 'source':
    collector.context = ('new-source',)
  elif changed == 'physical':
    collector.physical_context = ('new-physical',)
  else:
    collector.adapter.envelope = SimpleNamespace(prior_full_profile_sha256='new-prior')
  _, _, reporter, source, path = fixture(tmp_path)
  # Reporter reads can happen before the next collector.job_snapshot call.
  publish(reporter, collector, source)
  row = read_report(path, now_ns=NOW)['current']
  assert row['details']['Snapshot readiness']['reason'] == 'snapshot_context_changed'
  assert 'selectedBundles' not in row['details']['Snapshot readiness']
  assert collector.snapshot_attempts == attempts
  assert collector.job_snapshot(NOW + 1) is None
  assert collector.snapshot_attempts == attempts
  assert not row['application']['applied']


def test_real_storage_discard_path_invalidates_cached_selection(tmp_path):
  collector = actual_selection_collector(12)
  assert collector.job_snapshot(NOW) is None
  point = collector.blocks[0].samples[0]
  collector.raw_points.extend([point] * 81)
  # Actual storage bound failure calls _discard_storage -> superclass reset.
  collector._seal_raw()
  assert collector.training_interruptions['event_storage_pending_bound'] == 1
  assert collector.snapshot_readiness is collector.adapter.snapshot_readiness is None
  _, _, reporter, source, path = fixture(tmp_path)
  publish(reporter, collector, source)
  row = read_report(path, now_ns=NOW)['current']
  assert row['details']['Snapshot readiness']['reason'] == 'snapshot_not_attempted'
  assert not collector.blocks and not row['application']['applied']


def test_successful_selection_then_actual_export_failure_never_reports_ready(tmp_path):
  collector = actual_selection_collector(20)
  # The real fixture output has no production projection. Twenty complete
  # bundles pass selection, then the actual export projection check rejects.
  assert collector.ready[-1][1].projection is None
  assert collector.job_snapshot(NOW) is None
  assert collector.snapshot_attempts == collector.snapshot_declines == 1
  assert collector.snapshot_readiness['reason'] == 'event_snapshot_unavailable'
  assert collector.snapshot_readiness['selectedBundles'] == 20
  assert collector.snapshot_readiness['wholeBundles'] == 20
  _, _, reporter, source, path = fixture(tmp_path)
  publish(reporter, collector, source)
  row = read_report(path, now_ns=NOW)['current']
  assert row['details']['Snapshot readiness']['reason'] == 'event_snapshot_unavailable'
  assert row['details']['Snapshot readiness']['selectedBundles'] == 20
  assert row['details']['Submitted fit jobs (reporter lifetime)'] == 0
  assert not row['details']['Parent fit profile retained']
  assert not row['details']['Collector admission result retained']
  assert not row['application']['applied']
