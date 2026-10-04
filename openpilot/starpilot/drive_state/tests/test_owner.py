"""Temporary typed-store fakes exercise the shared request boundary."""

import copy
from types import SimpleNamespace as NS

import pytest

from openpilot.starpilot.drive_state.owner import DriveStateOwner, Mode, Rejected, REQUEST_KEY, SESSION_KEY

BOOT = '00000000-0000-0000-0000-000000000001'


class Params:
  def __init__(self):
    self.values = {}
    self.writes = []

  def get(self, key):
    return copy.deepcopy(self.values.get(key))

  def put(self, key, value, block=False):
    assert block
    self.values[key] = copy.deepcopy(value)
    self.writes.append((key, copy.deepcopy(value)))


@pytest.fixture
def fixture(tmp_path):
  params = Params()
  live = [True]
  owner = DriveStateOwner(params, tmp_path / 'owner', alive=lambda _: live[0])
  owner.initialize(pid=1, birth=2, boot=BOOT)
  return NS(params=params, live=live, owner=owner)


def request(f, mode, **kwargs):
  return f.owner.request(mode, expected_revision=f.owner.snapshot().revision,
                         authorized=kwargs.get('authorized', lambda: True),
                         override_allowed=kwargs.get('override_allowed', lambda: True))


def test_shared_owner_idempotence_atomic_mode_and_manager_reset(fixture):
  f = fixture
  state = request(f, 'onroad')
  writes = len(f.params.writes)
  assert request(f, 'onroad') == state and len(f.params.writes) == writes
  assert request(f, 'offroad').mode == Mode.OFFROAD
  assert set(f.params.values) == {REQUEST_KEY, SESSION_KEY}
  old_revision = f.owner.snapshot().revision
  f.owner.initialize(pid=1, birth=3, boot=BOOT)
  assert f.owner.snapshot().mode == Mode.AUTO
  with pytest.raises(Rejected):
    f.owner.request('onroad', expected_revision=old_revision, authorized=lambda: True, override_allowed=lambda: True)


def test_only_deliberate_override_requires_physical_admission(fixture):
  f = fixture
  with pytest.raises(Rejected):
    request(f, 'onroad', override_allowed=lambda: False)
  request(f, 'offroad')
  assert request(f, 'auto', override_allowed=lambda: False).mode == Mode.AUTO
  assert not any(key in f.params.values for key in ('ForceOffroad', 'ForceOnroad'))


@pytest.mark.parametrize('change', ['permission', 'physical', 'manager'])
def test_revocation_before_commit_never_writes_request(fixture, change):
  f = fixture
  writes = len(f.params.writes)
  calls = [0]

  def checked():
    calls[0] += 1
    if calls[0] == 2 and change == 'manager':
      f.live[0] = False
    return calls[0] < 2

  with pytest.raises(Rejected):
    request(f, 'onroad', authorized=checked if change == 'permission' else lambda: True,
            override_allowed=checked if change in ('physical', 'manager') else lambda: True)
  assert len(f.params.writes) == writes


@pytest.mark.parametrize('damage', ['missing', 'invalid-mode', 'extra-key', 'wrong-generation', 'boolean-version', 'dead'])
def test_bad_or_old_requests_never_grant_override(fixture, damage):
  f = fixture
  request(f, 'onroad')
  if damage == 'missing':
    f.params.values.pop(REQUEST_KEY)
  elif damage == 'invalid-mode':
    f.params.values[REQUEST_KEY]['mode'] = 'both'
  elif damage == 'extra-key':
    f.params.values[REQUEST_KEY]['ForceOnroad'] = True
  elif damage == 'wrong-generation':
    f.params.values[REQUEST_KEY]['session'] = '0' * 32
  elif damage == 'boolean-version':
    f.params.values[REQUEST_KEY]['version'] = True
  else:
    f.live[0] = False
  assert f.owner.snapshot().mode == Mode.AUTO
  assert not f.owner.snapshot().available


def test_two_key_initialization_crash_defaults_auto(fixture):
  f = fixture
  request(f, 'onroad')
  old_session = f.params.get(SESSION_KEY)
  original_put = f.params.put

  def interrupted(key, value, block=False):
    if key == SESSION_KEY:
      raise OSError('interrupted manager initialization')
    original_put(key, value, block=block)

  f.params.put = interrupted
  with pytest.raises(OSError):
    f.owner.initialize(pid=1, birth=3, boot=BOOT)
  assert f.params.get(SESSION_KEY) == old_session
  assert f.owner.snapshot().mode == Mode.AUTO and not f.owner.snapshot().available


def test_session_storage_symlink_is_rejected(fixture, tmp_path):
  f = fixture
  target = tmp_path / 'elsewhere'
  target.mkdir()
  alias = tmp_path / 'alias'
  alias.symlink_to(target)
  owner = DriveStateOwner(f.params, alias, alive=lambda _: True)
  with pytest.raises(Rejected):
    owner.request('onroad', expected_revision=f.owner.snapshot().revision,
                  authorized=lambda: True, override_allowed=lambda: True)


class FileParams:
  def __init__(self, root):
    self.root = root

  def get(self, key):
    import json
    try:
      return json.loads((self.root / key).read_text())
    except FileNotFoundError:
      return None

  def put(self, key, value, block=False):
    import json
    import os
    import uuid
    assert block
    temporary = self.root / ('.put-' + uuid.uuid4().hex)
    temporary.write_text(json.dumps(value))
    os.replace(temporary, self.root / key)



PROCESS_PROGRAM = """
import json,sys,time,types
from pathlib import Path
sys.path.insert(0,sys.argv[2])
sys.path.insert(0,sys.argv[1])
import openpilot.starpilot
pkg=types.ModuleType('openpilot.starpilot.drive_state')
pkg.__path__=[str(Path(sys.argv[1])/'openpilot/starpilot/drive_state')]
sys.modules[pkg.__name__]=pkg
from openpilot.starpilot.drive_state.owner import DriveStateOwner, Rejected
# FILE_PARAMS
params_root,lock_root,revision,mode,ready,release,result,started,go=sys.argv[3:]
owner=DriveStateOwner(FileParams(Path(params_root)),Path(lock_root),alive=lambda _: True)
if started != '-':
  Path(started).touch()
  startup_deadline=time.monotonic()+15
  while not Path(go).exists():
    if time.monotonic()>startup_deadline:raise RuntimeError('request barrier timeout')
    time.sleep(.01)
def authorized():
  if ready != '-':
    Path(ready).touch()
    deadline=time.monotonic()+30
    while not Path(release).exists():
      if time.monotonic()>deadline:raise RuntimeError('fixture timeout')
      time.sleep(.01)
  return True
try:
  state=owner.request(mode,expected_revision=revision,authorized=authorized,override_allowed=lambda: True)
  output=['accepted',state.mode.value]
except Rejected:
  output=['rejected',mode]
Path(result).write_text(json.dumps(output))
"""


def test_crossprocess_revision_commit_and_nonblocking_hardware_snapshot(tmp_path):
  import json
  import subprocess
  import sys
  import inspect
  import time
  from pathlib import Path
  params_root = tmp_path / 'params'
  params_root.mkdir()
  lock_root = tmp_path / 'owner'
  owner = DriveStateOwner(FileParams(params_root), lock_root, alive=lambda _: True)
  state = owner.initialize(pid=1, birth=2, boot=BOOT)
  ready, release = tmp_path / 'ready', tmp_path / 'release'
  source = Path(__file__).parents[4]
  from openpilot.common import params as native_params
  native_source = Path(native_params.__file__).parents[2]
  result1, result2 = tmp_path / 'result1', tmp_path / 'result2'
  program = PROCESS_PROGRAM.replace('# FILE_PARAMS', inspect.getsource(FileParams))
  common = [sys.executable, '-c', program, str(source), str(native_source), str(params_root), str(lock_root), state.revision]
  first = subprocess.Popen(common + ['onroad', str(ready), str(release), str(result1), '-', '-'])
  second = None
  second_ready, second_go = tmp_path / 'second-ready', tmp_path / 'second-go'
  try:
    deadline = time.monotonic() + 15
    while not ready.exists() and time.monotonic() < deadline:
      time.sleep(.01)
    assert ready.exists()
    # Hardware reads do not join a UI/auth request holding the writer lock.
    assert owner.snapshot() == state
    assert not release.exists()
    second = subprocess.Popen(common + ['offroad', '-', str(release), str(result2), str(second_ready), str(second_go)])
    # Interpreter/native imports have their own startup budget, separate from
    # the writer latency proof. The holder is never released by a timer.
    deadline = time.monotonic() + 15
    while not second_ready.exists() and time.monotonic() < deadline:
      time.sleep(.01)
    assert second_ready.exists() and not release.exists()
    second_go.touch()
    assert second.wait(timeout=2) == 0
    assert not release.exists()  # A competing UI request fails without waiting on the holder.
    release.touch()
    assert first.wait(timeout=5) == 0
    assert sorted((json.loads(result1.read_text()), json.loads(result2.read_text()))) == [
      ['accepted', 'onroad'], ['rejected', 'offroad']]
    assert owner.snapshot().mode == Mode.ONROAD
  finally:
    release.touch()
    for process in (first, second):
      if process is not None and process.poll() is None:
        process.kill()
        process.wait(timeout=3)


def test_process_identity_and_boot_liveness_use_single_stat_read(monkeypatch):
  from pathlib import Path
  from openpilot.starpilot.drive_state.owner import process_identity, manager_alive
  reads = []
  # Linux field 22 follows comm (which may contain spaces and closing parentheses).
  fields = [b'S'] + [b'0'] * 18 + [b'12345']
  raw = b'42 (manager ) worker) ' + b' '.join(fields)
  def read_bytes(path):
    reads.append(str(path))
    return raw
  monkeypatch.setattr(Path, 'read_bytes', read_bytes)
  monkeypatch.setattr(Path, 'read_text', lambda path: BOOT)
  session = {'pid': 42, 'birth': 12345, 'boot': BOOT}
  assert manager_alive(session)
  assert reads == ['/proc/42/stat']
  assert not manager_alive(dict(session, birth=12346))
  assert not manager_alive(dict(session, boot='different-boot'))
  raw = raw.replace(b') S ', b') Z ')
  assert not manager_alive(session)
  raw = b'malformed'
  assert process_identity(42) == (None, None)


def test_empty_real_native_registry_resolves_auto_and_unsupported_key_is_explicit(tmp_path):
  from openpilot.common.params import Params as NativeParams, UnknownKeyName
  from openpilot.starpilot.drive_state.owner import State
  params = NativeParams(str(tmp_path / 'params'))
  owner = DriveStateOwner(params, tmp_path / 'owner')
  assert owner.snapshot() == State()
  class Unsupported:
    def get(self, key):
      raise UnknownKeyName(key)
  assert DriveStateOwner(Unsupported(), tmp_path / 'unsupported').snapshot() == State()


def test_force_offroad_withdraws_authority_without_healthy_can(fixture):
  f = fixture
  assert request(f, 'offroad', override_allowed=lambda: False).mode == Mode.OFFROAD
  with pytest.raises(Rejected):
    request(f, 'onroad', override_allowed=lambda: False)
  with pytest.raises(Rejected):
    request(f, 'auto', authorized=lambda: False, override_allowed=lambda: False)
  assert f.owner.snapshot().mode == Mode.OFFROAD
