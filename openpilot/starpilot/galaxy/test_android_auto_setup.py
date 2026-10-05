from typing import cast
from unittest.mock import Mock
import io

import pytest

from openpilot.starpilot.galaxy.android_auto_setup import AndroidAutoSetup, SetupRejected
from openpilot.starpilot.system.android_auto.apk_identity import MAX_FILE_BYTES


class FakeImport:
  def __init__(self, root):
    self.work_dir = root
    self.started = []
    self.running = False
  def busy(self): return self.running
  def status(self): return {'state': 'running' if self.running else 'idle'}
  def start(self, *, path, enabled):
    self.started.append((path, path.read_bytes(), enabled))
    self.running = True


def setup(tmp_path, state):
  job = FakeImport(tmp_path / 'imports')
  service = AndroidAutoSetup(parked=lambda: state['parked'], enabled=lambda: state['enabled'],
                             session_valid=lambda token: token == state['session'], import_job=Mock(wraps=job, work_dir=job.work_dir),
                             identity_status=lambda: {'installed': False, 'message': 'No identity', 'key': 'SECRET'},
                             bluetooth_enabled=lambda: True)
  return service, job


def test_status_explains_phone_role_and_hides_key(tmp_path):
  state = {'parked': True, 'enabled': True, 'session': ('galaxy', '1')}
  service, _ = setup(tmp_path, state)
  result = service.status(state['session'])
  assert result['identity'] == {'installed': False, 'message': 'No identity'}
  assert result['bluetoothEnabled'] is True
  assert 'phone' in result['steps'][0] and 'Wi-Fi access point' in result['steps'][3]
  assert result['wiredAvailable'] is False and result['maxUploadBytes'] == MAX_FILE_BYTES


def test_upload_is_bounded_private_and_session_bound(tmp_path):
  state = {'parked': True, 'enabled': True, 'session': ('galaxy', '1')}
  service, job = setup(tmp_path, state)
  result = service.upload(state['session'], io.BytesIO(b'not-a-real-apk'), 14)
  assert result['import']['state'] == 'running'
  path, data, admission = job.started[0]
  assert data == b'not-a-real-apk' and path.stat().st_mode & 0o077 == 0
  state['session'] = ('galaxy', '2')
  assert admission() is False
  with pytest.raises(SetupRejected, match='session expired'):
    service.upload(('galaxy', '1'), io.BytesIO(b'abc'), 3)


def test_invalid_or_truncated_upload_never_starts_job(tmp_path):
  state = {'parked': True, 'enabled': True, 'session': ('galaxy', '1')}
  service, job = setup(tmp_path, state)
  for length, data in ((0, b''), (MAX_FILE_BYTES + 1, b''), (4, b'abc')):
    with pytest.raises(SetupRejected):
      service.upload(state['session'], io.BytesIO(data), length)
  assert job.started == [] and not list(job.work_dir.glob('*'))


def test_park_loss_during_upload_cleans_staging(tmp_path):
  state = {'parked': True, 'enabled': True, 'session': ('galaxy', '1')}
  service, job = setup(tmp_path, state)
  class Revoking(io.BytesIO):
    def read(self, size=-1):
      data = super().read(size)
      state['parked'] = False
      return data
  with pytest.raises(SetupRejected, match='offroad mode or Park'):
    service.upload(state['session'], Revoking(b'package'), 7)
  assert job.started == [] and not list(job.work_dir.glob('*'))


def test_busy_import_and_upload_lock_refuse_overlap(tmp_path):
  state = {'parked': True, 'enabled': True, 'session': ('galaxy', '1')}
  service, job = setup(tmp_path, state)
  job.running = True
  with pytest.raises(SetupRejected, match='import is running'):
    service.upload(state['session'], io.BytesIO(b'a'), 1)
  job.running = False
  service._upload_lock.acquire()
  try:
    with pytest.raises(SetupRejected, match='Another Android Auto upload'):
      service.upload(state['session'], io.BytesIO(b'a'), 1)
  finally:
    service._upload_lock.release()


@pytest.mark.parametrize('ignition_field', ['ignitionLine', 'ignitionCan'])
def test_forced_offroad_with_powered_car_admits_setup_and_rechecks_authority(tmp_path, ignition_field):
  from openpilot.common.params import Params
  from openpilot.starpilot.galaxy.settings import LiveContextSource
  from openpilot.starpilot.galaxy.tests.test_borrowed_authority import Messages

  messages = Messages()
  setattr(cast(dict, messages.data)['pandaStates'][0], ignition_field, True)
  # Forced offroad stops card/controlsd; connectivity does not require them.
  for service in ('carState', 'selfdriveState'):
    messages.seen[service] = messages.alive[service] = messages.valid[service] = False
  params = Params(str(tmp_path / 'params'))
  params.put_bool('IsOffroad', True, block=True)
  now = [1_000_000_000]
  authority = LiveContextSource(params, messages=messages, borrowed_messages=True, evidence_wait_ms=0,
                               mono_clock=lambda: now[0], boot_clock=lambda: now[0] + 10_000_000_000)
  now[0] = 2_100_000_000
  state: dict = {'enabled': False, 'session': ('galaxy', '1')}
  job = FakeImport(tmp_path / 'imports')
  service = AndroidAutoSetup(parked=authority.configuration_allowed, enabled=lambda: state['enabled'],
                            session_valid=lambda token: token == state['session'], import_job=Mock(wraps=job, work_dir=job.work_dir),
                            identity_status=lambda: {'installed': True}, install_ready=lambda: True,
                            service_ready=lambda: True, bluetooth_enabled=lambda: True,
                            set_enabled=lambda enabled: state.update(enabled=enabled))
  assert authority.parked()  # All offroad operations use the effective drive state.
  assert service.status(state['session'])['parked'] is True
  with pytest.raises(SetupRejected, match='session expired'):
    service.enable(('galaxy', 'expired'), True)
  assert service.enable(state['session'], True)['enabled'] is True
  assert service.upload(state['session'], io.BytesIO(b'package'), 7)['import']['state'] == 'running'
  admitted = job.started[0][2]
  assert admitted()
  params.put_bool('IsOffroad', False, block=True)
  assert not admitted()  # No onroad physical Park publishers are available.
  params.put_bool('IsOffroad', True, block=True)
  now[0] += 2_000_000_000
  assert not admitted()  # A saved offroad flag cannot extend stale publisher authority.
  messages.update.assert_not_called()
  authority.close()
  messages.sock['carState'].close.assert_not_called()
