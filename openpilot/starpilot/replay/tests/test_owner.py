"""Inert owners and one synthetic private engine; never run driving services."""

from collections.abc import Callable
from pathlib import Path
import json
import os
import socket
import stat
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
from typing import NoReturn, cast

import pytest

from openpilot.starpilot.replay.client import ReplayUnavailable, encode, parse, request_operation
from openpilot.starpilot.replay.owner import LiveAuthority, ReplayOwner, Rejected, _group_active, serve
from openpilot.tools.replay.display_clock import RECORD


CLIENT = 'a' * 32
OTHER = 'b' * 32
ROUTE = '00000001--aaaaaaaaaa'


class Lease:
  def __init__(self, catalog):
    self.catalog = catalog
    self.route = catalog.detail(ROUTE)

  def current(self):
    return self.catalog.current

  def close(self):
    self.catalog.released += 1


class Catalog:
  def __init__(self, root):
    self.root = root
    self.current = True
    self.released = 0

  def detail(self, route):
    if route != ROUTE:
      raise Rejected('invalid_route')
    return {'routeId': route, 'playable': True, 'warnings': [],
            'segments': [{'number': number, 'files': {'rlog': True, 'qlog': False, 'fcamera': True, 'qcamera': False}}
                         for number in (0, 2)]}

  def catalog(self):
    return {'schemaVersion': 1, 'routes': [self.detail(ROUTE)], 'scanIncomplete': False}

  def lease(self, route):
    self.detail(route)
    return Lease(self)


FIXTURE = '''import json,sys
s={'event':'status','state':'paused','position':0.,'start':0.,'end':120.,'rate':1.,'paused':True,'epoch':1,
   'frameReady':True,'mediaReady':False,'lastRequestId':None,'error':None}
print(json.dumps(s),flush=True)
for line in sys.stdin:
 c=json.loads(line)
 if c['op']=='pause': s.update(paused=c['paused'],state='paused' if c['paused'] else 'playing')
 elif c['op']=='seek': s.update(position=c['position'],epoch=s['epoch']+1)
 elif c['op']=='rate': s['rate']=c['rate']
 elif c['op']=='stop': break
 s['lastRequestId']=c['requestId']
 print(json.dumps(s),flush=True)
'''


def wait_for(predicate):
  deadline = time.monotonic() + 4
  while time.monotonic() < deadline:
    if predicate():
      return
    time.sleep(.01)
  raise AssertionError('owner did not reach expected state')


@pytest.fixture
def owner(tmp_path):
  catalog = Catalog(tmp_path / 'logs')
  catalog.root.mkdir()
  allowed = [True]
  children = []

  def spawn(command, **kwargs):
    # Assert isolation before replacing the production worker with an inert fixture.
    env = kwargs['env']
    assert env['OPENPILOT_PREFIX'].startswith('replay-')
    assert Path(env['PARAMS_ROOT']).is_relative_to(tmp_path)
    assert env['SP_REPLAY_CONTEXT'] == '1'
    assert 'SP_HOST_RUNTIME' not in env
    clock = Path(env['SP_REPLAY_CLOCK_PATH'])
    info = clock.stat()
    assert stat.S_IMODE(info.st_mode) == 0o600 and info.st_size == RECORD.size
    assert clock.read_bytes() == bytes(RECORD.size)
    assert kwargs['start_new_session'] is True
    child = subprocess.Popen([sys.executable, '-u', '-c', FIXTURE], **kwargs)
    child.replay_command = command
    children.append(child)
    return child

  value = ReplayOwner(catalog, root=tmp_path / 'replay', authority=lambda: allowed[0], spawn=spawn)
  yield value, catalog, allowed, children
  value.close()


def start(value, request_id='1' * 32):
  return value.dispatch({'op': 'start', 'routeId': ROUTE, 'target': 'native', 'clientId': CLIENT,
                         'requestId': request_id, 'expectedOwnerId': value.owner_id})


def control(value, action, field, item, request_id='2' * 32):
  state = value.dispatch({'op': 'status', 'clientId': CLIENT})
  return {'op': 'control', 'sessionId': state['sessionId'], 'clientId': CLIENT, 'requestId': request_id,
          'expectedRevision': state['revision'], 'action': action, field: item}


def test_catalog_and_detail_reuse_validated_dates_without_starting_analysis(owner, tmp_path, monkeypatch):
  from openpilot.starpilot.galaxy.drive_stats import DriveStatsOwner
  value, catalog, _, _ = owner
  monkeypatch.setattr('openpilot.starpilot.galaxy.drive_stats.galaxy_storage_root', lambda: tmp_path)
  def unexpected_analysis(_):
    raise AssertionError('Listing dates must not start analysis')
  monkeypatch.setattr(DriveStatsOwner, 'start', unexpected_analysis)
  record = {'routeId': ROUTE, 'startTime': 1_792_008_330, 'complete': False, 'ignored': False,
            'segmentCount': 2, 'sourceSignature': 'fixture'}
  path = tmp_path / 'drive-stats.json'
  def save():
    path.write_text(json.dumps({'schemaVersion': 1, 'routes': {ROUTE: record}}))
  save()
  loads = []
  load = DriveStatsOwner._load
  def counted_load(reader):
    loads.append(reader)
    load(reader)
  monkeypatch.setattr(DriveStatsOwner, '_load', counted_load)
  original = catalog.catalog
  monkeypatch.setattr(catalog, 'catalog', lambda: {**original(), 'routes': [catalog.detail(ROUTE),
                                                                         {'routeId': '00000002--bbbbbbbbbb', 'fileTime': 1_792_008_360}]})
  result = value.dispatch({'op': 'catalog'})
  assert len(loads) == 1
  assert result['routes'][0]['startTime'] == record['startTime']
  assert result['routes'][1]['startTime'] is None
  assert result['routes'][1]['fileTime'] == 1_792_008_360
  record['startTime'] += 60
  save()
  assert value.dispatch({'op': 'detail', 'routeId': ROUTE})['startTime'] == record['startTime']
  record['startTime'] = 'invalid'
  save()
  assert value.dispatch({'op': 'catalog'})['routes'][0]['startTime'] is None
  path.write_text('{')
  assert value.dispatch({'op': 'detail', 'routeId': ROUTE})['playable']
  assert value.worker is None


@pytest.mark.parametrize('segment', [True, -1, 1000000, '2', 1])
def test_start_rejects_invalid_or_missing_segment_before_spawning(owner, segment):
  value, _, _, children = owner
  with pytest.raises(Rejected):
    value.dispatch({'op': 'start', 'routeId': ROUTE, 'target': 'native', 'clientId': CLIENT,
                    'requestId': '1' * 32, 'expectedOwnerId': value.owner_id, 'segment': segment})
  assert not children


def test_start_forwards_selected_segment_to_worker(owner):
  value, _, _, children = owner
  value.dispatch({'op': 'start', 'routeId': ROUTE, 'target': 'native', 'clientId': CLIENT,
                  'requestId': '1' * 32, 'expectedOwnerId': value.owner_id, 'segment': 2})
  wait_for(lambda: value.status['state'] == 'paused')
  command = children[0].replay_command
  assert command[command.index('--start-segment') + 1] == '2'


def test_explicit_actions_retries_and_no_takeover(owner):
  value, catalog, _, children = owner
  first = start(value)
  assert first['owned'] and first['state'] == 'preparing'
  assert start(value)['sessionId'] == first['sessionId']
  wait_for(lambda: value.status['state'] == 'paused')
  assert len(children) == 1
  command = control(value, 'pause', 'paused', False)
  accepted = value.dispatch(command)
  wait_for(lambda: value.pending is None)
  assert value.status['state'] == 'playing'
  assert value.dispatch(command)['revision'] == accepted['revision']
  observer = value.dispatch({'op': 'status', 'clientId': OTHER})
  assert observer['owned'] is False and 'framePath' not in observer
  with pytest.raises(Rejected, match='another viewer'):
    value.dispatch(dict(command, clientId=OTHER, requestId='3' * 32))
  with pytest.raises(Rejected, match='Another viewer'):
    value.dispatch({'op': 'start', 'routeId': ROUTE, 'target': 'web', 'clientId': OTHER,
                    'requestId': '4' * 32, 'expectedOwnerId': value.owner_id})
  value.dispatch({'op': 'stop', 'sessionId': first['sessionId'], 'clientId': CLIENT, 'requestId': '5' * 32})
  wait_for(lambda: value.worker is None)
  assert children[0].poll() is not None and catalog.released == 1
  assert not list((value.root / 'sessions').iterdir())


def test_live_revocation_kills_only_fixture_and_releases_sources(owner):
  value, catalog, allowed, children = owner
  start(value)
  wait_for(lambda: value.status['state'] == 'paused')
  allowed[0] = False
  wait_for(lambda: value.worker is None)
  assert value.status['errorCode'] == 'not_offroad'
  assert children[0].poll() is not None and catalog.released == 1
  with pytest.raises(Rejected, match='Turn off'):
    start(value, '6' * 32)


def test_renderer_exit_reaps_inert_descendant_before_releasing_sources(owner, tmp_path):
  value, catalog, _, children = owner
  pid_file = tmp_path / 'descendant.pid'
  fixture = '\n'.join(('import subprocess,sys',
                       'args=[sys.executable,"-c","import time; time.sleep(120)"]',
                       'p=subprocess.Popen(args, stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)',
                       f'open({str(pid_file)!r},"w").write(str(p.pid))', 'sys.exit(1)'))

  def spawn(command, **kwargs):
    child = subprocess.Popen([sys.executable, '-c', fixture], **kwargs)
    children.append(child)
    return child

  value.spawn = spawn
  start(value)
  wait_for(lambda: value.worker is None)
  assert pid_file.exists()
  assert value.status['errorCode'] == 'worker_failed'
  assert not _group_active(children[0].pid)
  assert catalog.released == 1


def test_restart_cleans_only_marked_dead_sessions(owner):
  value, _, _, _ = owner
  sid = 'c' * 32
  directory = value.root / 'sessions' / sid
  directory.mkdir(mode=0o700)
  (directory / 'session.json').write_text(json.dumps({'version': 1, 'ownerPid': 2**30, 'ownerBirth': 1,
                                                    'workerPid': None, 'workerBirth': None}))
  ipc = Path('/dev/shm') / ('msgq_replay-' + sid[:24])
  ipc.mkdir(mode=0o700)
  (ipc / 'fixture').write_bytes(b'inert')
  unknown = value.root / 'sessions' / ('d' * 32)
  unknown.mkdir(mode=0o700)
  (unknown / 'keep').write_bytes(b'unknown')
  try:
    value.recover()
    assert not directory.exists() and not ipc.exists()
    assert (unknown / 'keep').read_bytes() == b'unknown'
    # A live previous owner must never be scavenged even if its socket is missing.
    marked = value.root / 'sessions' / ('e' * 32)
    marked.mkdir(mode=0o700)
    value._record_session(marked)
    with pytest.raises(Rejected, match='still stopping'):
      value.recover()
  finally:
    import shutil
    if ipc.exists():
      shutil.rmtree(ipc)


def test_real_authority_requires_fresh_parked_no_output_evidence(tmp_path, monkeypatch):
  mono, boot = 1_000_000_000_000, 1_120_000_000_000
  monkeypatch.setattr('openpilot.starpilot.replay.owner.time.monotonic_ns', lambda: mono)
  monkeypatch.setattr('openpilot.starpilot.replay.owner.time.clock_gettime_ns', lambda _: boot)
  params = SimpleNamespace(get_param_path=lambda key: str(tmp_path / key))
  (tmp_path / 'IsOffroad').write_bytes(b'1')
  (tmp_path / 'IsEngaged').write_bytes(b'0')
  panda = SimpleNamespace(pandaType='dos', safetyModel='noOutput', controlsAllowed=False,
                          ignitionLine=False, ignitionCan=False)

  class Snapshot(dict):
    pass

  sm = Snapshot(deviceState=SimpleNamespace(started=False), pandaStates=[panda])
  sm.seen = dict.fromkeys(sm, True)
  sm.alive = dict.fromkeys(sm, True)
  sm.valid = dict.fromkeys(sm, True)
  sm.logMonoTime = {'deviceState': mono - 100_000_000, 'pandaStates': boot - 100_000_000}
  sm.recv_time = dict.fromkeys(sm, (mono - 10_000_000) / 1e9)
  sm.device_offset_ns = boot - mono
  sm.after_mono_ns = mono - 2_000_000_000
  value = object.__new__(LiveAuthority)
  value.params = params
  value.evidence = SimpleNamespace(snapshot=lambda: sm)
  assert value.allowed()
  for field, bad in (('ignitionLine', True), ('ignitionCan', True), ('controlsAllowed', True),
                     ('safetyModel', 'elm327'), ('pandaType', 'unknown')):
    previous = getattr(panda, field)
    setattr(panda, field, bad)
    assert not value.allowed()
    setattr(panda, field, previous)
  sm['deviceState'].started = True
  assert not value.allowed()
  sm['deviceState'].started = False
  sm.alive['pandaStates'] = False
  assert not value.allowed()
  sm.alive['pandaStates'] = True
  sm.device_offset_ns = 0
  assert not value.allowed()  # Evidence from before a suspend cannot authorize.
  sm.device_offset_ns = boot - mono
  sm.after_mono_ns = sm.logMonoTime['deviceState']
  assert not value.allowed()
  sm.after_mono_ns = mono - 2_000_000_000
  (tmp_path / 'IsEngaged').write_bytes(b'1')
  assert not value.allowed()
  (tmp_path / 'IsEngaged').write_bytes(b'0')
  (tmp_path / 'DoShutdown').write_bytes(b'1')
  assert not value.allowed()
  monkeypatch.setenv('SP_HOST_RUNTIME', '1')
  monkeypatch.setenv('SP_HOST_PARKED', '1')
  value.evidence = SimpleNamespace(snapshot=lambda: None)
  assert not value.allowed()  # Desktop shortcuts are never authority for real replay.


def test_display_snapshot_never_exceeds_renderer_bounds(owner, tmp_path):
  value, _, _, _ = owner
  saved = tmp_path / 'saved'
  saved.mkdir()
  value.params = SimpleNamespace(get_param_path=lambda key: str(saved / key))
  output = tmp_path / 'snapshot'
  output.mkdir()
  (saved / 'OnroadCustomizations').write_bytes(b'x' * (48 * 1024))
  value._display_snapshot(output)
  path = output / 'display.json'
  assert len(path.read_bytes()) <= 128 * 1024
  assert all(len(raw) <= 64 * 1024 for raw in json.loads(path.read_bytes())['values'].values())
  path.unlink()
  (saved / 'IsMetric').write_bytes(b'x' * (48 * 1024))
  with pytest.raises(Rejected, match='settings unavailable'):
    value._display_snapshot(output)
  assert not path.exists()  # Invalid context never reaches renderer startup.


def test_disconnect_source_change_and_restart_identity(owner):
  value, catalog, _, _ = owner
  with pytest.raises(Rejected, match='restarted'):
    value.dispatch({'op': 'start', 'routeId': ROUTE, 'target': 'native', 'clientId': CLIENT,
                    'requestId': '1' * 32, 'expectedOwnerId': '0' * 32})
  start(value)
  wait_for(lambda: value.status['state'] == 'paused')
  value.lease_at -= 16
  wait_for(lambda: value.worker is None)
  assert value.status['errorCode'] == 'viewer_disconnected'
  start(value, '6' * 32)
  wait_for(lambda: value.status['state'] == 'paused')
  catalog.current = False
  wait_for(lambda: value.worker is None)
  assert value.status['errorCode'] == 'route_changed'


def test_strict_revision_numbers_and_request_identity(owner):
  value, _, _, _ = owner
  start(value)
  wait_for(lambda: value.status['state'] == 'paused')
  for action, key, bad in (('seek', 'position', float('nan')), ('seek', 'position', True), ('rate', 'rate', 8), ('pause', 'paused', 1)):
    with pytest.raises(Rejected, match='invalid request'):
      value.dispatch(control(value, action, key, bad))
  command = control(value, 'seek', 'position', 30)
  accepted = value.dispatch(command)
  wait_for(lambda: value.pending is None)
  assert value.status['position'] == 30 and value.status['epoch'] == 2
  with pytest.raises(Rejected, match='request changed'):
    value.dispatch(dict(command, position=60))
  with pytest.raises(Rejected, match='Replay changed'):
    value.dispatch(dict(control(value, 'pause', 'paused', False, '7' * 32), expectedRevision=accepted['revision'] - 1))


def test_accepted_seek_cannot_restore_media_from_unacknowledged_worker_status(owner, tmp_path):
  value, _, _, _ = owner
  value.client_id = CLIENT
  value.status.update(sessionId='c' * 32, target='web', state='playing', revision=1, epoch=1, end=120.,
                      frameReady=True, mediaReady=True)
  published = {**value.status, 'event': 'status', 'error': None, 'lastRequestId': None}
  command = control(value, 'seek', 'position', 30.)
  accepted = value.dispatch(command)
  assert accepted['state'] == 'seeking' and not accepted['mediaReady']
  for status in (published, {**published, 'epoch': 2, 'state': 'buffering', 'frameReady': False, 'mediaReady': False}):
    value._observe(status, tmp_path)
    assert value.status['state'] == 'seeking'
    assert not value.status['frameReady'] and not value.status['mediaReady']
    assert value.pending == command['requestId']
    with pytest.raises(Rejected, match='epoch changed'):
      value.dispatch({'op': 'media', 'sessionId': accepted['sessionId'], 'clientId': CLIENT,
                      'epoch': value.status['epoch'], 'sequence': 0})
  value._observe({**published, 'epoch': 2, 'position': 30., 'lastRequestId': command['requestId']}, tmp_path)
  assert value.status['state'] == 'playing' and value.status['mediaReady'] and value.status['frameReady']
  assert value.pending is None


@pytest.mark.parametrize('ranges', [None, [[0]], [[0, True]], [[0, float('nan')]], [[20, 10]],
                                   [[0, 101]], [[0, 20], [10, 30]]])
def test_worker_seek_ranges_reject_malformed_or_overlapping_bounds(owner, tmp_path, ranges):
  value, _, _, _ = owner
  status = {**value._idle(), 'event': 'status', 'state': 'paused', 'end': 100., 'seekRanges': ranges}
  with pytest.raises(Rejected, match='worker failed'):
    value._observe(status, tmp_path)


def test_gap_seek_is_rejected_without_losing_owned_viewer(owner):
  value, _, _, children = owner
  start(value)
  wait_for(lambda: value.status['state'] == 'paused')
  value.status['seekRanges'] = [[0., 40.], [80., 120.]]
  epoch, revision = value.status['epoch'], value.status['revision']
  with pytest.raises(Rejected, match='no recorded camera'):
    value.dispatch(control(value, 'seek', 'position', 60))
  state = value.dispatch({'op': 'status', 'clientId': CLIENT})
  assert state['owned'] and state['state'] == 'paused'
  assert (state['epoch'], state['revision']) == (epoch, revision)
  assert state['frameReady'] and children[0].poll() is None


def test_real_machine_uses_owner_created_clock_and_cleans_it(tmp_path, monkeypatch):
  from openpilot.common.basedir import BASEDIR
  from openpilot.starpilot.replay.catalog import ReplayCatalog
  from openpilot.tools.replay.display_clock import DisplayClockReader
  from openpilot.tools.replay.tests.test_machine import segment

  binary = Path(BASEDIR) / 'openpilot/tools/replay/replay'
  if not binary.is_file():
    cast(Callable[[str], NoReturn], pytest.skip)('Build the isolated replay engine first')
  routes = tmp_path / 'routes'
  routes.mkdir()
  segment(routes, 0, [.1, .2, 10], compressed=True)
  (routes / '00000001--1234567890--0').rename(routes / (ROUTE + '--0'))
  original = {path.name: path.read_bytes() for path in (routes / (ROUTE + '--0')).iterdir()}
  unrelated = tmp_path / 'unrelated-clock'
  unrelated.write_bytes(b'untouched-clock')
  monkeypatch.setenv('SP_REPLAY_CLOCK_PATH', str(unrelated))
  children, clocks, readers = [], [], []

  def spawn(command, **kwargs):
    env = dict(kwargs['env'])
    clock = Path(env['SP_REPLAY_CLOCK_PATH'])
    info = clock.stat()
    assert stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600
    assert info.st_uid == os.getuid() and info.st_nlink == 1 and info.st_size == RECORD.size
    assert clock.read_bytes() == bytes(RECORD.size)
    assert clock != unrelated
    reader = DisplayClockReader(env)
    assert not reader.sample().valid
    readers.append(reader)
    clocks.append(clock)
    # Replace only the GPU compositor with the real machine engine; production
    # owner creates every namespace prerequisite before this callback runs.
    env['SP_REPLAY_PARENT_PID'] = str(os.getpid())
    kwargs['env'] = env
    child = subprocess.Popen([str(binary), '--machine', '--no-vipc', '--data_dir', str(routes), ROUTE], **kwargs)
    children.append(child)
    return child

  value = ReplayOwner(ReplayCatalog(routes), root=tmp_path / 'replay', authority=lambda: True, spawn=spawn)
  try:
    started = start(value)
    wait_for(lambda: value.status['state'] == 'paused')
    reader = readers[0]
    initial = reader.sample()
    assert initial.valid and initial.paused and initial.epoch == value.status['epoch']
    assert initial.now_ns == 37_100_000_000 and initial.boot_ns == 40_100_000_000
    value.dispatch(control(value, 'seek', 'position', .2))
    wait_for(lambda: value.pending is None and value.status['epoch'] > initial.epoch)
    sought = reader.sample()
    assert sought.valid and sought.paused and sought.epoch > initial.epoch
    assert sought.now_ns == 37_200_000_000
    value.dispatch({'op': 'stop', 'sessionId': started['sessionId'], 'clientId': CLIENT, 'requestId': '5' * 32})
    wait_for(lambda: value.worker is None)
    assert children[0].poll() == 0
    assert not reader.sample().valid
    assert not clocks[0].parent.exists()
    assert not list((value.root / 'sessions').iterdir())
    restarted = start(value, '6' * 32)
    wait_for(lambda: value.status['state'] == 'paused')
    assert restarted['sessionId'] != started['sessionId'] and clocks[1] != clocks[0]
    assert readers[1].sample().valid and not reader.sample().valid
    value.dispatch({'op': 'stop', 'sessionId': restarted['sessionId'], 'clientId': CLIENT, 'requestId': '7' * 32})
    wait_for(lambda: value.worker is None)
    assert children[1].poll() == 0 and not clocks[1].parent.exists()
    assert unrelated.read_bytes() == b'untouched-clock'
    assert {path.name: path.read_bytes() for path in (routes / (ROUTE + '--0')).iterdir()} == original
  finally:
    value.close()
    for reader in readers:
      reader.close()


def test_protocol_bounds_and_duplicate_owner_keeps_live_socket(owner):
  value, _, _, _ = owner
  for raw in (b'{"op":"status","op":"stop"}', b'{"value":NaN}', b'[]'):
    with pytest.raises(ValueError):
      parse(raw, 4096)
  with pytest.raises(ValueError):
    encode({'value': 'x' * 5000}, 4096)
  stop = threading.Event()
  thread = threading.Thread(target=serve, args=(value,), kwargs={'stop': stop}, daemon=True)
  thread.start()
  path = value.root / 'owner.sock'
  try:
    wait_for(path.exists)
    assert request_operation({'op': 'status'}, socket_path=path)['result']['ownerId'] == value.owner_id
    with pytest.raises(BlockingIOError):
      serve(value, stop=threading.Event())
    assert path.exists()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
      peer.connect(str(path))
      peer.sendall(b'\x7f\xff\xff\xff')
      assert peer.recv(4096)
    assert request_operation({'op': 'catalog'}, socket_path=path)['ok'] is True
  finally:
    stop.set()
    thread.join(timeout=2)
  assert not thread.is_alive() and not path.exists()
  with pytest.raises(ReplayUnavailable):
    request_operation({'op': 'status'}, socket_path=path)


def test_storage_symlink_is_never_repurposed(tmp_path):
  outside = tmp_path / 'outside'
  outside.mkdir()
  linked = tmp_path / 'linked'
  linked.symlink_to(outside, target_is_directory=True)
  with pytest.raises(Rejected, match='storage'):
    ReplayOwner(Catalog(tmp_path), root=linked)
  assert not list(outside.iterdir())


def test_media_batch_keeps_owner_and_authority_checks(owner):
  from openpilot.starpilot.replay.media import MediaStore
  value, _, allowed, _ = owner
  state = start(value)
  wait_for(lambda: value.status['state'] == 'paused')
  media = MediaStore(value.session_dir, state['sessionId'], 1280, 640)
  media.begin(1, 'avc1.42c01f', b'init')
  media.publish(b'first', position=0., keyframe=True)
  media.publish(b'second', position=.05, keyframe=False)
  value.status.update(target='web', mediaReady=True)
  request = {'op': 'media', 'sessionId': state['sessionId'], 'clientId': CLIENT, 'epoch': 1, 'sequence': 1, 'count': 8}
  assert [row['sequence'] for row in value.dispatch(request)['fragments']] == [1, 2]
  for invalid in (0, 9, True):
    with pytest.raises(Rejected, match='invalid request'):
      value.dispatch({**request, 'count': invalid})
  with pytest.raises(Rejected):
    value.dispatch({**request, 'clientId': OTHER})
  with pytest.raises(Rejected):
    value.dispatch({**request, 'epoch': 2})
  allowed[0] = False
  with pytest.raises(Rejected, match='not offroad'):
    value.dispatch(request)
