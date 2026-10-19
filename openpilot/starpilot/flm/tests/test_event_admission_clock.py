"""Clock causality/collector propagation; synthetic lifecycle is not admission proof."""
from dataclasses import replace
from unittest import mock

import pytest

from openpilot.starpilot.flm.event_collection import EventCollectionAdapter, _fresh_current_physical
from openpilot.starpilot.flm.tests.test_event_target_renewal import BoundaryAdapter, fixture

NOW = 20_000_000_000


def test_response_after_command_is_fresh_only_at_a_trusted_later_decision():
  control, applied, response = NOW - 2_000_000, NOW - 1_000_000, NOW
  assert not _fresh_current_physical(control, applied, response, None)
  assert _fresh_current_physical(control, applied, response, NOW)
  assert not _fresh_current_physical(control, applied, response, applied)
  assert _fresh_current_physical(NOW - 100_000_000, NOW - 99_000_000, NOW, NOW)


@pytest.mark.parametrize('index', (0, 1, 2))
def test_each_original_stream_must_be_nonfuture_and_within_100ms(index):
  valid: list[int | float] = [NOW - 2_000_000, NOW - 1_000_000, NOW]
  for stamp in (NOW + 1, NOW - 101_000_000, 0, -1, True, float(NOW)):
    values = valid.copy()
    values[index] = stamp
    assert not _fresh_current_physical(values[0], values[1], values[2], NOW)
  assert not _fresh_current_physical(NOW, NOW - 1, NOW, NOW)


@pytest.mark.parametrize('decision', (0, -1, True, float(NOW), NOW - 1))
def test_malformed_or_earlier_decision_cannot_make_future_pose_fresh(decision):
  assert not _fresh_current_physical(NOW - 2_000_000, NOW - 1_000_000, NOW, decision)


def test_no_clock_legacy_condition_is_unchanged():
  for delta in (-1, 0, 1, 100_000_000, 100_000_001):
    response = NOW - delta
    expected = 0 < response <= NOW + 500_000_000 and 0 <= NOW - response <= 100_000_000
    assert _fresh_current_physical(NOW - 1_000_000, NOW, response, None) == expected


class ClockedBoundaryAdapter(BoundaryAdapter, EventCollectionAdapter):
  # Reuse existing explicitly synthetic collector lifecycle fixture; never grant
  # a registered physical/native qualification. readmit is blocked below.
  raw_collection = False
  decisions = None

  def physical_observable(self, row=None, *, value=None):
    return super().physical_observable(row if value is None else value)

  def current_admission(self, profile, control, output, context, *, now_ns=None):
    self.decisions = now_ns
    return BoundaryAdapter.current_admission(self, profile, control, output, context)


def collector_ready(*, clocked):
  collector, control, output, pose = fixture()
  if clocked:
    old = collector.adapter
    adapter = ClockedBoundaryAdapter(old.fit_profile)
    adapter.__dict__.update(old.__dict__)
    collector.adapter = adapter
  assert collector.control(control, output.apply_ns)
  assert collector.output(output, output.apply_ns)
  assert collector.physical(pose, pose.received_ns)
  return collector, pose.received_ns


def test_actual_collector_passes_trusted_decision_only_to_event_adapter():
  collector, decision = collector_ready(clocked=True)
  with mock.patch('openpilot.starpilot.flm.fullrate_collector.readmit_profile', return_value=None) as readmit:
    assert collector.revalidate_fit(decision) is None
  assert collector.adapter.decisions == decision
  admission = readmit.call_args.args[2]
  control, output = collector.ready[-1]
  assert admission.source_ns == min(control.control_ns, output.apply_ns)
  assert readmit.call_args.kwargs['now_ns'] == decision
  # Legacy fixture's old four-argument method must still work unchanged.
  collector, decision = collector_ready(clocked=False)
  with mock.patch('openpilot.starpilot.flm.fullrate_collector.readmit_profile', return_value=None) as readmit:
    assert collector.revalidate_fit(decision) is None
  assert readmit.called


@pytest.mark.parametrize('bad', ('source_future', 'source_expired', 'native_future', 'native_expired', '101ms'))
def test_existing_source_native_and_freshness_leases_precede_admission(bad):
  collector, decision = collector_ready(clocked=True)
  control, output = collector.ready[-1]
  changes = {}
  if bad == 'source_future':
    changes['source_receipt_ns'] = decision + 1
  elif bad == 'source_expired':
    changes['source_receipt_ns'] = decision - 500_000_001
  elif bad == 'native_future':
    changes.update(native_required=True, native_allowed=True, native_observed_ns=decision + 1, native_expires_ns=decision + 100_000_000)
  elif bad == 'native_expired':
    changes.update(native_required=True, native_allowed=True, native_observed_ns=decision - 100_000_000, native_expires_ns=decision - 1)
  else:
    decision += 101_000_000
  collector.ready[-1] = (replace(control, **changes), output)
  assert collector.revalidate_fit(decision) is None
  assert collector.adapter.decisions is None
