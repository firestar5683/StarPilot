"""Galaxy authority stays sampled independently of HTTP traffic."""
from types import SimpleNamespace as NS

import pytest

from openpilot.starpilot.galaxy.evidence import EvidenceSource
from openpilot.starpilot.galaxy.settings import LiveContextSource
from openpilot.starpilot.drive_state.evidence import PhysicalSource


class Messages:
  def __init__(self, clock):
    self.clock = clock
    self.calls = 0
    self.fail = False
    self.sock = {'owned': NS(close=lambda: setattr(self, 'socket_closed', True))}
    self.socket_closed = False
    self.publish()

  def publish(self, *, ignition=False, started=False):
    mono, boot = self.clock['mono'], self.clock['boot']
    self.data = {'deviceState': NS(started=started),
                 'pandaStates': [NS(pandaType='uno', ignitionLine=ignition, ignitionCan=False, controlsAllowed=False, safetyModel='noOutput')],
                 'carState': NS(canValid=True, canTimeout=False, standstill=True, gearShifter='park'),
                 'selfdriveState': NS(enabled=False, active=False)}
    self.seen = self.alive = self.valid = dict.fromkeys(EvidenceSource.SERVICES, True)
    self.updated = dict(self.seen)
    self.logMonoTime = {name: boot if name == 'pandaStates' else mono for name in EvidenceSource.SERVICES}
    self.recv_time = dict.fromkeys(EvidenceSource.SERVICES, mono / 1000000000.0)

  def update(self, timeout):
    assert timeout == 0
    self.calls += 1
    if self.fail:
      raise OSError('reader failed')

  def __getitem__(self, name):
    return self.data[name]


def readers(tmp_path):
  clock = {'mono': 10_000_000_000, 'boot': 20_000_000_000}
  messages = Messages(clock)
  source = EvidenceSource(messages, mono=lambda: clock['mono'], boot=lambda: clock['boot'])
  (tmp_path / 'IsOffroad').write_bytes(b'1')
  params = NS(get_param_path=lambda key: str(tmp_path / key))
  def clients():
    return (LiveContextSource(params, source, mono_clock=lambda: clock['mono'], boot_clock=lambda: clock['boot'], evidence_wait_ms=0),
            PhysicalSource(source, mono=lambda: clock['mono'], boot=lambda: clock['boot']))
  return clock, messages, source, clients


def tick(clock, messages, source, **state):
  clock['mono'] += 100_000_000
  clock['boot'] += 100_000_000
  messages.publish(**state)
  source.poll()


def test_cold_start_and_idle_first_reads_use_sampled_source_not_http_polling(tmp_path):
  clock, messages, source, clients = readers(tmp_path)
  source.poll()
  parked, physical = clients()
  assert not parked.parked() and not physical.allowed() and physical.effective() is None
  for _ in range(30):
    tick(clock, messages, source)
  # Lazy owners inherit the already-qualified collector startup boundary.
  parked, physical = clients()
  calls = messages.calls
  assert parked.parked() and physical.allowed() and physical.effective() is False
  assert messages.calls == calls


def test_current_stale_future_and_ignition_transition_authority(tmp_path):
  clock, messages, source, clients = readers(tmp_path)
  tick(clock, messages, source)
  parked, physical = clients()
  assert parked.parked() and physical.allowed()
  clock['mono'] += 400_000_000
  clock['boot'] += 400_000_000
  assert not parked.parked() and not physical.allowed()
  tick(clock, messages, source, ignition=True, started=True)
  assert not parked.parked() and physical.effective() is True
  messages.data['selfdriveState'] = NS(enabled=True, active=True)
  source.poll()
  assert not physical.allowed()
  tick(clock, messages, source)
  assert parked.parked() and physical.allowed()
  messages.logMonoTime['pandaStates'] = clock['boot'] + 1
  source.poll()
  assert not parked.parked() and not physical.allowed()


def test_short_resume_before_next_poll_rejects_new_lazy_consumers(tmp_path):
  clock, messages, source, clients = readers(tmp_path)
  tick(clock, messages, source)
  assert clients()[0].parked()
  clock['boot'] += 100_000_000  # Still inside Panda TTL; suspend must invalidate anyway.
  parked, physical = clients()
  assert not parked.parked() and not physical.allowed() and physical.effective() is None
  source.poll()  # Cached pre-resume publisher cannot clear the shared barrier.
  assert not parked.parked()
  tick(clock, messages, source)
  assert parked.parked() and physical.allowed()


def test_snapshot_metadata_stays_coherent_and_immutable(tmp_path):
  clock, messages, source, _ = readers(tmp_path)
  tick(clock, messages, source)
  captured = source.snapshot()
  tick(clock, messages, source, started=True)
  assert not captured['deviceState'].started and source.snapshot()['deviceState'].started
  with pytest.raises(TypeError):
    captured.seen['deviceState'] = False
  with pytest.raises(AttributeError):
    captured.after_mono_ns = 0


def test_failure_and_terminal_close_never_resurrect_subscription(tmp_path):
  clock, messages, source, clients = readers(tmp_path)
  tick(clock, messages, source)
  parked, physical = clients()
  messages.fail = True
  source.poll()
  assert not parked.parked() and not physical.allowed() and physical.effective() is None
  messages.fail = False
  tick(clock, messages, source)
  assert parked.parked()
  parked.close()
  calls = messages.calls
  assert not parked.parked() and messages.calls == calls
  source.close()
  assert messages.socket_closed and source.snapshot() is None and not physical.allowed()


def test_background_reader_closes_and_drains_owned_thread(tmp_path):
  _, messages, source, _ = readers(tmp_path)
  source.start()
  assert source.thread.is_alive()
  source.close()
  assert not source.thread.is_alive() and messages.socket_closed and source.snapshot() is None
