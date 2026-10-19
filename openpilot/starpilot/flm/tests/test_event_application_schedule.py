"""Actual owner scheduling with declared unit transport; NEVER a fit grant.

The child output is an opaque proposal deliberately rejected by adapter install.
Real typed control/output/physical collector/source guards still run. Synthetic
native health is explicit; this is not controller/native/physical qualification.
"""
from dataclasses import replace
from types import SimpleNamespace
from unittest import mock
import pytest

from openpilot.starpilot.flm import steerlearnerd
from openpilot.starpilot.flm.event_collection import event_key, event_keys
from openpilot.starpilot.flm.event_collector import EventFullrateCollector
from openpilot.starpilot.flm.runtime_adapter_registry import SourceState
from openpilot.starpilot.flm.tests.test_fullrate_pipeline import (
  BASE, SyntheticAdapter, snapshots, serialized_control, serialized_output,
)


def exercise(*, failure=None):
  now, phase = [BASE], [-1]
  attempts, sent, collectors, sources = [], [], [], []
  old_key, new_key = ('event','deadband.high'), ('event','center')
  class Adapter(SyntheticAdapter):
    event_collection = True
    raw_storage = False
    target_changed = False
    def __init__(self):
      super().__init__()
      self.envelope = SimpleNamespace(prior_full_profile_sha256='a'*64)
      self.current_physical_valid = False
      self.last_physical_ns = 0
      self.fit_profile = None
      self.key = None
    def prepare_control(self, value):
      return value
    def select_objective(self, value):
      self.key = value
    def install_fit(self, report, *decoded, physical_context):
      attempts.append((phase[0], self.key))
      return False  # Opaque unit proposal MUST NOT become a fit or permission.
    def current_admission(self, *args, **kwargs):
      raise AssertionError('unit transport proposal cannot reach live admission')
  class Collector(EventFullrateCollector):
    def __init__(self, adapter):
      super().__init__(adapter)
      self.offered = False
      collectors.append(self)
    def job_snapshot(self, now_ns):
      # Unit fitter transport only; not a forged eligible scientific snapshot.
      if not self.offered and self.ready and self.physical_context is not None:
        self.offered = True
        return {'unit_transport_only':True}
      return None
  class Fitter:
    child = None
    def __init__(self):
      self.token = None
      self.completed = False
    def poll(self, *, token, now_ns):
      if self.child is not None and phase[0] == 1:
        self.child = None
        self.completed = True
        assert token == self.token
        return {'unit_unqualified_proposal':True}
      return None
    def submit(self, snapshot, *, token, now_ns):
      assert snapshot == {'unit_transport_only':True}
      self.child, self.token = object(), token
      return True
    def cancel(self, reason):
      self.child = None
    def close(self, reason):
      self.child = None
  c_sock, a_sock = object(), object()
  fitter, persistence, sm = Fitter(), mock.Mock(), mock.Mock()
  def update(timeout=None):
    if timeout == 0:
      return
    phase[0] += 1
    if phase[0] == 7:
      raise StopIteration
    now[0] = BASE + phase[0]*50_000_000
    if phase[0] == 5 and failure == 'prior' and collectors:
      collectors[0].adapter.envelope.prior_full_profile_sha256 = 'd'*64
  sm.update.side_effect = update
  def source(stamp):
    known = not (failure == 'source' and phase[0] >= 5)
    value = SourceState(known,False,'0' if known else '', '2'*64 if known else '',stamp,stamp+500_000_000,
      'b'*64,(0.,0.,0.),configuration_known=known)
    sources.append(value)
    return value
  def rows():
    stamp = now[0]-1_000_000
    control, output, physical = snapshots(stamp)
    control = replace(control,source_receipt_ns=stamp,replay_inputs=(('control_frame',float(5999+phase[0])),))
    return control,output,physical
  def drain(socket, callback, receive, sink, stamp):
    control,output,_ = rows()
    callback(serialized_control(control) if socket is c_sock else serialized_output(output),sink,stamp)
  def physical(*args):
    return None if failure == 'physical' and phase[0] >= 5 else rows()[2]
  def send(service,message):
    row=message.autoSteeringLearning.learning
    sent.append((phase[0],str(row.status),row.runtimeProfile.version))
  publisher=mock.Mock()
  publisher.send.side_effect=send
  proposal=(SimpleNamespace(profile=object()), object())
  with mock.patch.object(steerlearnerd,'drain',drain), \
       mock.patch('openpilot.starpilot.flm.event_collector.EventFullrateCollector',Collector), \
       mock.patch('openpilot.starpilot.flm.native_health.current_native_health',
         side_effect=lambda *args: not (failure == 'native' and phase[0] >= 5)):
    with pytest.raises(StopIteration):
      steerlearnerd.run(SimpleNamespace(),sm,c_sock,a_sock,publisher,lambda *args:Adapter(),physical,source,
        event_keys,event_key,lambda report:proposal,persistence,fitter,mock.Mock(),clock=lambda:now[0])
  assert fitter.completed
  assert len(collectors)==1
  assert collectors[0].adapter.key == new_key or failure == 'source'
  assert all(status != 'qualified' and version == 0 for _,status,version in sent)
  assert collectors[0].fit_result is None and collectors[0].last_validation is None
  return attempts, sent, collectors, old_key


def test_completed_old_group_proposal_attempts_own_selector_without_waiting_full_cycle():
  attempts,_,_,old_key=exercise()
  assert attempts == [(5,old_key)]


@pytest.mark.parametrize('failure',('native','physical','source','prior'))
def test_later_current_or_lineage_failure_never_attempts_or_publishes_unit_proposal(failure):
  attempts,_,_,_=exercise(failure=failure)
  assert attempts == []
