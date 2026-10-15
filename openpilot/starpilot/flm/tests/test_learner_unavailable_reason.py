"""Existing status publications must name settings blocks accurately."""
from dataclasses import replace
from types import SimpleNamespace
from unittest import mock

import pytest

from openpilot.starpilot.flm import steerlearnerd
from openpilot.starpilot.flm.runtime_adapter_registry import SourceState


NOW = 1_000_000_000


def publication(source, evidence=None, adapter=None, sources=None):
  sources = [source] if sources is None else sources
  sm = mock.Mock()
  sm.update.side_effect = [*([None] * len(sources)), StopIteration()]
  pm, fitter = mock.Mock(), mock.Mock()
  control_socket, applied_socket = object(), object()
  factory = mock.Mock(return_value=adapter)
  source_reader = mock.Mock(side_effect=sources)
  clock = mock.Mock(side_effect=[NOW + index * 250_000_000 for index in range(len(sources))])

  def drain(socket, callback, receive, sink, now):
    if socket is control_socket and evidence is not None:
      event = SimpleNamespace(which=lambda: 'starpilotLateralState',
                              starpilotLateralState=SimpleNamespace(learningEvidence=SimpleNamespace(version=1)))
      callback(event, now, now)

  with mock.patch.object(steerlearnerd, 'drain', drain), mock.patch.object(steerlearnerd, 'read_control', return_value=evidence):
    with pytest.raises(StopIteration):
      steerlearnerd.run(SimpleNamespace(), sm, control_socket, applied_socket, pm, factory, mock.Mock(),
                        source_reader, lambda item: (('feedforward', 'low', 'steady'),),
                        lambda item: ('feedforward', 'low', 'steady'), mock.Mock(), mock.Mock(), fitter,
                        mock.Mock(), clock=clock)
  fitter.close.assert_called_once_with('learner_parent_exit')
  factory_calls = factory.call_count
  message = pm.send.call_args.args[1]
  assert message.valid
  assert str(message.autoSteeringLearning.learning.status) == 'unavailable'
  assert message.autoSteeringLearning.learning.sourceReceipt.manual == sources[-1].manual
  return str(message.autoSteeringLearning.learning.reason), factory_calls


def source():
  return SourceState(True, False, '0', 'a' * 64, NOW, NOW + 500_000_000, 'b' * 64, (0., 0., 0.))


@pytest.mark.parametrize('change,reason', (({'enabled': False}, 'learning_disabled'),
                                         ({'manual': True}, 'manual_profile_override'),
                                         ({'observed_ns': NOW - 600_000_000, 'expires_ns': NOW - 100_000_000},
                                          'settings_receipt_expired')))
def test_settings_block_is_reported_without_claiming_an_unsupported_controller(change, reason):
  actual, factory_calls = publication(replace(source(), **change))
  assert actual == reason
  assert factory_calls == 0


def test_no_controller_evidence_is_distinct_from_adapter_rejection():
  reason, factory_calls = publication(source())
  assert reason == 'no_current_controller_evidence'
  assert factory_calls == 0


def test_cleared_manual_block_does_not_leave_a_stale_status_reason():
  reason, factory_calls = publication(source(), sources=[replace(source(), manual=True), source()])
  assert reason == 'no_current_controller_evidence'
  assert factory_calls == 0


def test_actual_adapter_unavailable_is_reserved_for_a_real_factory_refusal():
  evidence = SimpleNamespace(source_epoch='a' * 64, source_receipt_ns=NOW, control_ns=NOW,
                             identity='c' * 64, generation=1, domain='normalized_torque', stage_revision='stage',
                             response_revision='response', controller_mode='starpilot', policy='ioniq6',
                             baseline_revision='baseline', controller_revision='controller', turn_assist=False)
  reason, factory_calls = publication(source(), evidence)
  assert reason == 'actual_adapter_unavailable'
  assert factory_calls == 1
