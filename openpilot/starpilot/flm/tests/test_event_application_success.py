"""Actual parent/readmit/wire lifecycle with existing explicit profile fixture.

NOT a route-fit/registered-native/model qualification. BoundaryAdapter is the
existing synthetic lifecycle adapter; scientific validation is not invented.
"""
from dataclasses import asdict, replace
from types import SimpleNamespace
from unittest import mock

import pytest

from openpilot.cereal import messaging
from openpilot.starpilot.flm import steerlearnerd
from openpilot.starpilot.flm.adaptive_profile import replay_accepts
from openpilot.starpilot.flm.canonical_surface_adapter import GROUPS, parameters_for
from openpilot.starpilot.flm.event_collection import event_key, event_keys
from openpilot.starpilot.flm.event_collector import EventFullrateCollector
from openpilot.starpilot.flm.learner_factory import decode_fit_result
from openpilot.starpilot.flm.learning_wire import read_runtime_admission
from openpilot.starpilot.flm.runtime_adapter_registry import SourceState
from openpilot.starpilot.flm.tests.test_event_target_renewal import BoundaryAdapter
from openpilot.starpilot.flm.tests.test_full_surface_profile import base, wire_profile
from openpilot.starpilot.flm.tests.test_fullrate_pipeline import BASE, snapshots, serialized_control, serialized_output


def exercise(*, no_new_pose=False):
  old_key, new_key = ('event', 'deadband.high'), ('event', 'center')
  full = base(GROUPS[old_key[1]]).with_proposal({'center_deadband_fast_deg': .005, 'center_deadband_highway_deg': .005})
  profile, validation = wire_profile(full)
  profile = replace(profile, observed_ns=BASE+2_500_000_000, expires_ns=BASE+3_000_000_000)
  validation = replace(validation, profile=profile)
  report = {'status': 'qualified', 'reason': 'existing-explicit-lifecycle-fixture',
            'profile': asdict(profile), 'validation': asdict(validation)}
  decoded = decode_fit_result(report)
  assert decoded is not None and decoded[0].profile == profile and decoded[1] == validation
  phase, now = [-1], [BASE]
  installs, admitted, sent, collectors = [], [], [], []

  class Adapter(BoundaryAdapter):
    event_collection = True
    raw_storage = False
    target_changed = False
    def __init__(self):
      super().__init__(profile)
      self.envelope = full
      self.key = old_key
      self.installed = False
    def prepare_control(self, evidence):
      return evidence
    def select_objective(self, key):
      self.key = key
    def parameters(self):
      return parameters_for(GROUPS[self.key[1]])
    def install_fit(self, offered, result, proof, *, physical_context):
      assert offered == report and self.key == old_key
      assert result.profile == profile and replay_accepts(proof, profile)
      assert physical_context == ('cal', 'vm', 'lag', 0)
      installs.append((phase[0], self.key))
      # Existing adapter lifecycle boundary: installing a new model requires a
      # later independent pose. Repeated SAME immutable proposal cannot reset it.
      if not self.installed:
        self.current_physical_valid, self.last_physical_ns = False, 0
      self.installed = True
      self.fit_profile = profile
      return True
    def current_admission(self, profile, control, output, context):
      result = super().current_admission(profile, control, output, context)
      admitted.append((phase[0], result.healthy, self.last_physical_ns))
      return result

  class Collector(EventFullrateCollector):
    def __init__(self, adapter):
      super().__init__(adapter)
      self.offered = False
      collectors.append(self)
    def job_snapshot(self, now_ns):
      if phase[0] == 50 and not self.offered and self.ready and self.physical_context is not None:
        self.offered = True
        return {'unit_transport_only': True}
      return None

  class Fitter:
    child = None
    def __init__(self):
      self.token = None
      self.complete = False
    def submit(self, snapshot, *, token, now_ns):
      assert phase[0] == 50 and snapshot == {'unit_transport_only': True}
      self.token, self.child = token, object()
      return True
    def poll(self, *, token, now_ns):
      if self.child is not None and phase[0] == 51:
        assert token == self.token
        self.child, self.complete = None, True
        return report
      return None
    def cancel(self, reason):
      self.child = None
    def close(self, reason):
      self.child = None

  csock, osock = object(), object()
  fitter, sm, persistence = Fitter(), mock.Mock(), mock.Mock()
  def update(timeout=None):
    if timeout == 0:
      return
    phase[0] += 1
    if phase[0] == 67:
      raise StopIteration
    now[0] = BASE + phase[0]*50_000_000
  sm.update.side_effect = update
  def source(stamp):
    return SourceState(True, False, '0', full.source_epoch, stamp, stamp+500_000_000,
                       full.cp_sha256, (0.,0.,0.), configuration_known=True)
  def rows():
    stamp = now[0]-1_000_000
    control, output, physical = snapshots(stamp)
    control = replace(control, identity=profile.identity, baseline_revision='a'*64, source_epoch=full.source_epoch,
                      controller_revision=full.controller_revision, source_receipt_ns=stamp,
                      replay_inputs=(('control_frame', float(5949+phase[0])),))
    return control, output, physical
  def drain(socket, callback, receive, sink, stamp):
    control, output, _ = rows()
    callback(serialized_control(control) if socket is csock else serialized_output(output), sink, stamp)
  def physical(*args):
    # Before and at the installation publication there are genuine fixture poses;
    # only the negative case withdraws all LATER poses after the flags reset.
    return None if no_new_pose and phase[0] > 55 else rows()[2]
  def send(service, message):
    wire = messaging.log_from_bytes(message.to_bytes())
    admission = read_runtime_admission(wire)
    sent.append((phase[0], admission))
  publisher = mock.Mock()
  publisher.send.side_effect = send
  with mock.patch.object(steerlearnerd, 'drain', drain), \
       mock.patch('openpilot.starpilot.flm.event_collector.EventFullrateCollector', Collector), \
       mock.patch('openpilot.starpilot.flm.native_health.current_native_health', return_value=True):
    with pytest.raises(StopIteration):
      steerlearnerd.run(SimpleNamespace(), sm, csock, osock, publisher, lambda *args: Adapter(), physical, source,
                       event_keys, event_key, decode_fit_result, persistence, fitter, mock.Mock(), clock=lambda: now[0])
  assert fitter.complete and len(collectors) == 1
  assert collectors[0].adapter.key == new_key
  assert installs and installs[0] == (55, old_key)
  assert admitted[0][0] == 55 and admitted[0][1] is False
  assert all(admission is None for tick, admission in sent if tick <= 55)
  return profile, validation, sent, admitted


def test_pending_old_group_fixture_applies_after_next_pose_without_cycle_wait():
  original, proof, sent, admissions = exercise()
  qualified = [(tick, pair) for tick, pair in sent if pair is not None]
  assert qualified and qualified[0][0] == 60  # active selector has been CENTER since51.
  assert any(tick >= 60 and healthy and response > 0 for tick, healthy, response in admissions)
  for _, (profile, validation) in qualified:
    assert profile.coefficients == original.coefficients
    assert profile.train_ids == original.train_ids and profile.heldout_ids == original.heldout_ids
    assert profile.effect_envelope == original.effect_envelope
    assert validation.baseline_revision == proof.baseline_revision
    assert validation.physical_model_revision == proof.physical_model_revision
    assert profile.observed_ns > original.observed_ns and profile.expires_ns-profile.observed_ns == 500_000_000


def test_pending_successful_install_without_next_pose_never_applies():
  _, _, sent, admissions = exercise(no_new_pose=True)
  assert all(admission is None for _, admission in sent)
  assert not any(healthy for _, healthy, _ in admissions)
