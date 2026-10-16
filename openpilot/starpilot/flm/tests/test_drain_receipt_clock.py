"""Real learner run callback clocks: deterministic transport and monotonic clock."""
from types import SimpleNamespace
from unittest import mock

import pytest

from openpilot.starpilot.flm import steerlearnerd
from openpilot.starpilot.flm.runtime_adapter_registry import SourceState

NOW = 1_000_000_000
KEY = ('feedforward', 'low', 'steady')


def exercise(*, control_offset=10_000_000, callback_offset=20_000_000,
             epoch='a' * 64, output_offset=None):
  source = SourceState(True, False, '0', 'a' * 64, NOW, NOW + 500_000_000,
                       'b' * 64, (0., 0., 0.))
  evidence = SimpleNamespace(source_epoch=epoch, source_receipt_ns=NOW,
    control_ns=NOW + control_offset, identity='c' * 64, generation=1,
    domain='normalized_torque', stage_revision='stage', response_revision='response',
    controller_mode='starpilot', policy='ioniq6', baseline_revision='baseline',
    controller_revision='controller', turn_assist=False)
  control_socket, output_socket = object(), object()
  adapter = mock.Mock()
  adapter.prepare_control.return_value = evidence
  collector = mock.Mock(adapter=adapter)
  receipt_clock = [NOW]
  source_reader = mock.Mock(return_value=source)
  fitter = mock.Mock()
  event = SimpleNamespace(which=lambda: 'starpilotLateralState',
    starpilotLateralState=SimpleNamespace(learningEvidence=SimpleNamespace(version=1)))
  applied = SimpleNamespace(which=lambda: 'starpilotCarState',
    starpilotCarState=SimpleNamespace(appliedEvidence=SimpleNamespace(version=1)))
  output_value = object()

  def drain(socket, callback, receive, sink, captured_now):
    assert captured_now == NOW  # Original outer loop snapshot really is older.
    if socket is control_socket:
      receipt_clock[0] = NOW + callback_offset
      callback(event, sink, captured_now)
    else:
      receipt_clock[0] = NOW + (max(30_000_000, callback_offset + 10_000_000) if output_offset is None else output_offset)
      callback(applied, sink, captured_now)
      raise StopIteration  # Stop only after both real run callbacks execute.

  with mock.patch.object(steerlearnerd, 'drain', drain), \
       mock.patch.object(steerlearnerd, 'read_control', return_value=evidence), \
       mock.patch.object(steerlearnerd, 'read_applied', return_value=output_value), \
       mock.patch.object(steerlearnerd, 'FullrateCollector', return_value=collector):
    with pytest.raises(StopIteration):
      steerlearnerd.run(SimpleNamespace(), mock.Mock(), control_socket, output_socket,
        mock.Mock(), mock.Mock(return_value=adapter), mock.Mock(), source_reader,
        lambda _: (KEY,), lambda _: KEY, mock.Mock(), mock.Mock(), fitter,
        mock.Mock(), clock=lambda: receipt_clock[0])
  source_reader.assert_called_once_with(NOW)  # No opportunistic epoch replacement.
  fitter.close.assert_called_once_with('learner_parent_exit')
  return collector, fitter, evidence, output_value


def test_live_frames_after_loop_snapshot_use_actual_callback_receipts():
  collector, _, evidence, output = exercise()
  collector.control.assert_called_once_with(evidence, NOW + 20_000_000)
  collector.output.assert_called_once_with(output, NOW + 30_000_000)


@pytest.mark.parametrize('changes', [
  {'control_offset': 20_000_001},  # Truly future relative to callback receipt.
  {'callback_offset': 500_000_001},  # Frozen source lease really expired.
  {'epoch': 'd' * 64},  # Fresh clock must not forgive source identity mismatch.
])
def test_fresh_callback_clock_preserves_admission_rejections(changes):
  collector, fitter, _, _ = exercise(**changes)
  collector.control.assert_not_called()
  collector.output.assert_not_called()
  assert any(call.args == ('controller_source_receipt_mismatch',)
             for call in fitter.cancel.call_args_list)


def test_output_after_frozen_source_expiry_does_not_enter_collector():
  collector, fitter, evidence, _ = exercise(output_offset=500_000_001)
  collector.control.assert_called_once_with(evidence, NOW + 20_000_000)
  collector.output.assert_not_called()
  assert any(call.args == ('settings_receipt_expired',)
             for call in fitter.cancel.call_args_list)


def test_post_drain_health_and_fit_use_current_time():
  source = SourceState(False, False, '0', 'a' * 64, NOW, NOW + 500_000_000,
                       'b' * 64, (0., 0., 0.))
  receipt_clock = [NOW]
  sm, fitter = mock.Mock(), mock.Mock()
  sm.update.side_effect = [None, StopIteration()]

  def drain(socket, callback, receive, sink, captured_now):
    assert captured_now == NOW
    receipt_clock[0] += 10_000_000

  with mock.patch.object(steerlearnerd, 'drain', drain):
    with pytest.raises(StopIteration):
      steerlearnerd.run(SimpleNamespace(), sm, object(), object(), mock.Mock(),
        mock.Mock(), mock.Mock(), mock.Mock(return_value=source), mock.Mock(),
        mock.Mock(), mock.Mock(), mock.Mock(), fitter, mock.Mock(),
        clock=lambda: receipt_clock[0])
  fitter.poll.assert_called_once_with(token=None, now_ns=NOW + 20_000_000)
  fitter.close.assert_called_once_with('learner_parent_exit')
