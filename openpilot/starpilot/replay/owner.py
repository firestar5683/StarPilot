"""One offroad replay resource owner; neither UI owns driving processes."""

from __future__ import annotations

import base64
from collections import OrderedDict
import fcntl
import json
import math
import os
from pathlib import Path
import queue
import re
import selectors
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import threading
import time
from typing import cast
import uuid

from openpilot.starpilot.replay.client import MAX_REQUEST, MAX_RESPONSE, encode, parse, receive, replay_root
from openpilot.tools.replay.display_clock import RECORD


TOKEN = re.compile(r'[0-9a-f]{32}\Z')
STATES = frozenset(('preparing', 'paused', 'playing', 'seeking', 'buffering', 'ended', 'failed'))
LEASE_SECONDS = 15.0
PREPARE_SECONDS = 45.0
CONTROL_SECONDS = 15.0
STOP_GRACE_SECONDS = 1.5
DISPLAY_KEYS = (
  'OnroadCustomizations', 'IsMetric', 'CameraView', 'DriverCamera', 'AlwaysOnDM', 'HidePersonalityAlerts',
  'ShowBrakeStatus', 'PedalsOnUI', 'StockConfidenceBallWidget', 'HideLeadMarker', 'LeadInfo', 'LeadInfoMode',
  'BlindSpotMetrics', 'SignalMetrics', 'ShowSpeedLimits', 'UseVienna', 'ShowCSCStatus', 'PIPPreviewEnabled',
  'PIPPreviewMask', 'PIPPreviewShowOnBlinker', 'PIPPreviewShowOnBSM', 'PIPPreviewInvert',
)


class Rejected(ValueError):
  def __init__(self, code, message=None):
    self.code = code
    super().__init__(message or code.replace('_', ' '))


def _token(value):
  return type(value) is str and TOKEN.fullmatch(value) is not None


def _finite(value):
  return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 604800


def _owned_dir(path: Path):
  for ancestor in (path, *path.parents):
    if ancestor.is_symlink():
      raise Rejected('unavailable', 'Replay storage is unavailable')
  path.mkdir(mode=0o700, parents=True, exist_ok=True)
  info = path.lstat()
  if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
    raise Rejected('unavailable', 'Replay storage is unavailable')


def _process_birth(pid):
  try:
    raw = Path(f'/proc/{pid}/stat').read_bytes()
    return int(raw[raw.rfind(b')') + 2:].split()[19])
  except (OSError, IndexError, ValueError):
    return None


def _group_active(group):
  # Zombies cannot access sources or publish. Live descendants still own resources.
  count = 0
  for path in Path('/proc').iterdir():
    if not path.name.isdecimal():
      continue
    count += 1
    if count > 8192:
      raise Rejected('stop_unconfirmed')
    try:
      raw = (path / 'stat').read_bytes()
      fields = raw[raw.rfind(b')') + 2:].split()
      if int(fields[2]) == group and fields[0] != b'Z':
        return True
    except (FileNotFoundError, ProcessLookupError):
      continue
    except (OSError, IndexError, ValueError):
      raise Rejected('stop_unconfirmed') from None
  return False


def _guarded_command(command):
  # Linux kills the worker if its manager-supervised owner disappears.
  guard = '; '.join(('import ctypes,os,signal,sys', 'rc=ctypes.CDLL(None).prctl(1,signal.SIGKILL,0,0,0)',
                    'rc==0 or sys.exit(125)', 'os.getppid()==int(sys.argv[1]) or sys.exit(125)',
                    'os.execv(sys.argv[2],sys.argv[2:])'))
  return [sys.executable, '-c', guard, str(os.getpid()), *command]


class LiveAuthority:
  """Real source only; recorded ignition and Force Onroad never authorize replay."""

  def __init__(self, params):
    from openpilot.starpilot.galaxy.evidence import EvidenceSource
    self.params = params
    self.evidence = EvidenceSource().start()

  def allowed(self):
    from openpilot.starpilot.parked_evidence import ParkedEvidence, fresh_parked
    from openpilot.starpilot.saved_source import read_saved
    try:
      sm = self.evidence.snapshot()
      if sm is None:
        return False
      offroad, readable = read_saved(self.params, 'IsOffroad', 8)
      engaged, engaged_readable = read_saved(self.params, 'IsEngaged', 8)
      for key in ('DoShutdown', 'DoReboot', 'DoUninstall'):
        value, valid = read_saved(self.params, key, 8)
        if not valid or value not in (None, b'0'):
          return False
      pandas = sm['pandaStates']
      if (not pandas or any(str(p.pandaType) == 'unknown' or str(p.safetyModel) != 'noOutput' or p.controlsAllowed for p in pandas) or
          not engaged_readable or engaged not in (None, b'0')):
        return False
      evidence = ParkedEvidence(
        readable and offroad == b'1', sm.seen['deviceState'], sm.alive['deviceState'], sm.valid['deviceState'],
        bool(sm['deviceState'].started), int(sm.logMonoTime['deviceState']), int(sm.recv_time['deviceState'] * 1e9),
        sm.device_offset_ns, sm.after_mono_ns, sm.seen['pandaStates'], sm.alive['pandaStates'], sm.valid['pandaStates'],
        int(sm.logMonoTime['pandaStates']), int(sm.recv_time['pandaStates'] * 1e9),
        tuple(bool(p.ignitionLine or p.ignitionCan) for p in pandas),
      )
      return fresh_parked(evidence, now_mono_ns=time.monotonic_ns(),
                          now_boot_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))
    except (OSError, RuntimeError, KeyError, TypeError, ValueError, AttributeError, OverflowError):
      return False

  def close(self):
    self.evidence.close()


class ReplayOwner:
  def __init__(self, catalog, *, root=None, authority=lambda: False, params=None, profile='large',
               spawn=subprocess.Popen, clock=time.monotonic):
    self.catalog = catalog
    self.root = Path(root) if root is not None else replay_root()
    _owned_dir(self.root)
    _owned_dir(self.root / 'sessions')
    if profile not in ('large', 'compact'):
      raise ValueError('Invalid replay profile')
    self.authority, self.params, self.profile, self.spawn, self.clock = authority, params, profile, spawn, clock
    self.lock = threading.RLock()
    self.owner_id = uuid.uuid4().hex
    self.closed = False
    self.worker = None
    self.child = None
    self.child_birth = None
    self.cancel = threading.Event()
    self.commands = queue.Queue(maxsize=4)
    self.history = OrderedDict()
    self.client_id = None
    self.lease_at = 0.0
    self.pending = None
    self.pending_at = 0.0
    self.session_dir = None
    self.retained_lease = None
    self.base_warnings = []
    self.status = self._idle()

  def _idle(self, error=None):
    return {'schemaVersion': 1, 'ownerId': self.owner_id, 'sessionId': None, 'state': 'idle', 'routeId': None,
            'profile': self.profile, 'revision': 0, 'epoch': 0, 'position': 0.0, 'start': 0.0, 'end': 0.0,
            'rate': 1.0, 'paused': True, 'errorCode': error, 'sourceWarnings': [], 'seekRanges': [],
            'frameReady': False, 'mediaReady': False}

  def _snapshot(self, client=None):
    result = dict(self.status)
    owned = client == self.client_id and client is not None
    result['owned'] = owned
    result['offroad'] = bool(self.authority())
    if not owned:
      for key in ('framePath', 'media', 'codec'):
        result.pop(key, None)
    return result

  def _touch(self, request):
    client = request.get('clientId')
    if client is not None and not _token(client):
      raise Rejected('invalid_request')
    if client == self.client_id and client is not None:
      self.lease_at = self.clock()
    return client

  def _owned(self, request):
    client = self._touch(request)
    if (not _token(request.get('sessionId')) or request['sessionId'] != self.status['sessionId'] or
        client != self.client_id or client is None):
      raise Rejected('session_changed', 'Replay belongs to another viewer or has ended')
    return client

  def _repeat(self, request):
    if not _token(request.get('requestId')) or not _token(request.get('clientId')):
      raise Rejected('invalid_request')
    key = request['clientId'], request['requestId']
    previous = self.history.get(key)
    if previous is not None and previous != request:
      raise Rejected('request_changed')
    if previous is not None:
      self._touch(request)
      return True
    return False

  def _remember(self, request):
    self.history[request['clientId'], request['requestId']] = dict(request)
    while len(self.history) > 32:
      self.history.popitem(last=False)

  def dispatch(self, request):
    if type(request) is not dict or type(request.get('op')) is not str or self.closed:
      raise Rejected('unavailable' if self.closed else 'invalid_request')
    op = request['op']
    if (op == 'catalog' and set(request) == {'op'} or
        op == 'detail' and set(request) == {'op', 'routeId'}):
      result = self.catalog.catalog() if op == 'catalog' else self.catalog.detail(request['routeId'])
      routes = result['routes'] if op == 'catalog' else [result]
      try:
        from openpilot.starpilot.galaxy.drive_stats import DriveStatsOwner
        dates = DriveStatsOwner(root=self.catalog.root).recording_dates(route['routeId'] for route in routes)
      except (OSError, RuntimeError, ValueError):
        dates = {}  # Optional dates must not hide usable recordings.
      for route in routes:
        route['startTime'] = dates.get(route['routeId'])
      return result
    with self.lock:
      if op == 'status' and set(request) <= {'op', 'clientId'}:
        return self._snapshot(self._touch(request))
      if op == 'start':
        return self._start(request)
      if op == 'control':
        return self._control(request)
      if op == 'stop':
        if set(request) != {'op', 'sessionId', 'clientId', 'requestId'}:
          raise Rejected('invalid_request')
        if self._repeat(request):
          return self._snapshot(request['clientId'])
        client = self._owned(request)
        self._remember(request)
        self._stop('stopped')
        return self._snapshot(client)
      if op == 'media':
        return self._media(request)
    raise Rejected('invalid_request')

  def _start(self, request):
    common = {'op', 'routeId', 'target', 'clientId', 'requestId', 'expectedOwnerId'}
    if (set(request) not in (common, common | {'segment'}) or request['target'] not in ('native', 'web') or
        'segment' in request and (type(request['segment']) is not int or not 0 <= request['segment'] <= 999999)):
      raise Rejected('invalid_request')
    if self._repeat(request):
      return self._snapshot(request['clientId'])
    if request['expectedOwnerId'] != self.owner_id:
      raise Rejected('owner_changed', 'Replay service restarted; refresh first')
    if self.worker is not None:
      raise Rejected('busy', 'Another viewer is using replay')
    if not self.authority():
      raise Rejected('not_offroad', 'Turn off the vehicle before replaying a drive')
    route = self.catalog.detail(request['routeId'])
    if not route.get('playable'):
      raise Rejected(route.get('reasonCode') or 'route_unavailable', route.get('reason') or 'Recorded route is unavailable')
    segment = request.get('segment')
    if segment is not None and not any(item['number'] == segment and (item['files']['rlog'] or item['files']['qlog']) and
                                      (item['files']['fcamera'] or item['files']['qcamera']) for item in route.get('segments', [])):
      raise Rejected('segment_unavailable', 'This segment has no replayable driving logs and road video')
    sid = uuid.uuid4().hex
    directory = self.root / 'sessions' / sid
    _owned_dir(directory)
    self._record_session(directory)
    self.session_dir = directory
    self.client_id = request['clientId']
    self.lease_at = self.clock()
    self.cancel = threading.Event()
    self.commands = queue.Queue(maxsize=4)
    self.pending = None
    self.base_warnings = list(route.get('warnings', []))[:32]
    self.status = self._idle()
    self.status.update(sessionId=sid, state='preparing', routeId=route['routeId'], revision=1,
                       target=request['target'], sourceWarnings=self.base_warnings, lastRequestId=request['requestId'])
    self._remember(request)
    self.worker = threading.Thread(target=self._run, args=(sid, route['routeId'], request['target'], segment),
                                   name='recorded-replay', daemon=True)
    self.worker.start()
    return self._snapshot(self.client_id)

  def _control(self, request):
    common = {'op', 'sessionId', 'clientId', 'requestId', 'expectedRevision', 'action'}
    action = request.get('action')
    extra = {'pause': 'paused', 'seek': 'position', 'rate': 'rate'}.get(action)
    if (extra is None or set(request) != common | {extra} or type(request['expectedRevision']) is not int or
        action == 'pause' and type(request[extra]) is not bool or
        action == 'seek' and not _finite(request[extra]) or
        action == 'rate' and (type(request[extra]) not in (int, float) or request[extra] not in (.5, 1, 2))):
      raise Rejected('invalid_request')
    if self._repeat(request):
      return self._snapshot(request['clientId'])
    client = self._owned(request)
    if not self.authority():
      self._stop('not_offroad')
      raise Rejected('not_offroad')
    if request['expectedRevision'] != self.status['revision']:
      raise Rejected('revision_changed', 'Replay changed; refresh first')
    if self.pending is not None or self.status['state'] not in ('paused', 'playing', 'ended', 'buffering'):
      raise Rejected('busy', 'Replay is preparing or applying another action')
    if action == 'seek' and not self.status['start'] <= request[extra] <= self.status['end']:
      raise Rejected('invalid_position')
    if (action == 'seek' and self.status['seekRanges'] and
        not any(lo <= request[extra] <= hi for lo, hi in self.status['seekRanges'])):
      raise Rejected('invalid_position', 'This position has no recorded camera and log')
    command = {'op': action, extra: request[extra], 'requestId': request['requestId']}
    try:
      self.commands.put_nowait(command)
    except queue.Full:
      raise Rejected('busy') from None
    self.pending = request['requestId']
    self.pending_at = self.clock()
    self.status['revision'] += 1
    if action == 'seek':
      self.status['state'] = 'seeking'
      self.status['frameReady'] = self.status['mediaReady'] = False
    self._remember(request)
    return self._snapshot(client)

  def _media(self, request):
    fields = {'op', 'sessionId', 'clientId', 'epoch', 'sequence'}
    count = request.get('count', 1)
    if (set(request) not in (fields, fields | {'count'}) or type(count) is not int or not 1 <= count <= 8 or
        any(type(request.get(key)) is not int or request[key] < 0 for key in ('epoch', 'sequence'))):
      raise Rejected('invalid_request')
    self._owned(request)
    if not self.authority():
      self._stop('not_offroad')
      raise Rejected('not_offroad')
    if self.status.get('target') != 'web' or request['epoch'] != self.status['epoch'] or not self.status.get('mediaReady'):
      raise Rejected('epoch_changed')
    from openpilot.starpilot.replay.media import media_descriptor
    directory = self.session_dir
    if directory is None:
      raise Rejected('session_changed')
    return media_descriptor(directory, request['epoch'], request['sequence'], count)

  def _stop(self, reason):
    if self.worker is not None:
      self.cancel.set()
      self.status.update(state='stopping', errorCode=None if reason == 'stopped' else reason,
                         frameReady=False, mediaReady=False)

  def _display_snapshot(self, directory):
    from openpilot.starpilot.saved_source import read_saved
    values = {}
    total = 0
    if self.params is not None:
      for key in DISPLAY_KEYS:
        try:
          raw, valid = read_saved(self.params, key, 48 * 1024)
        except (OSError, KeyError, ValueError):
          continue
        if valid and raw:
          total += len(raw)
          if total > 262144:
            raise Rejected('settings_unavailable')
          values[key] = base64.b64encode(raw).decode('ascii')
    snapshot = json.dumps({'version': 1, 'values': values}).encode('utf-8')
    if len(snapshot) > 128 * 1024:
      raise Rejected('settings_unavailable')
    path = directory / 'display.json'
    path.write_bytes(snapshot)
    path.chmod(0o600)

  def _observe(self, value, directory):
    if value.get('event') != 'status' or value.get('state') not in STATES:
      raise Rejected('worker_failed')
    with self.lock:
      if self.cancel.is_set():
        return
      for field in ('position', 'start', 'end'):
        if not _finite(value.get(field)):
          raise Rejected('worker_failed')
      if (not value['start'] <= value['position'] <= value['end'] or
          type(value.get('rate')) not in (int, float) or value.get('rate') not in (.5, 1, 2) or type(value.get('paused')) is not bool or
          type(value.get('epoch')) is not int or not 0 <= value['epoch'] < 2**63):
        raise Rejected('worker_failed')
      self.status.update({key: value[key] for key in ('state', 'position', 'start', 'end', 'rate', 'paused', 'epoch')})
      self.status['frameReady'] = value.get('frameReady') is True
      self.status['mediaReady'] = value.get('mediaReady') is True
      self.status['errorCode'] = str(value.get('error') or '')[:128] or None
      ranges = value.get('seekRanges', [])
      if (type(ranges) is not list or len(ranges) > 512 or
          any(type(item) is not list or len(item) != 2 or not all(_finite(number) for number in item) or
              not value['start'] <= item[0] <= item[1] <= value['end'] for item in ranges)):
        raise Rejected('worker_failed')
      ranges = cast(list[list[float]], ranges)
      if any(before[1] > after[0] for before, after in zip(ranges, ranges[1:], strict=False)):
        raise Rejected('worker_failed')
      self.status['seekRanges'] = ranges
      warnings = value.get('sourceWarnings', [])
      if type(warnings) is not list or len(warnings) > 32 or any(type(warning) is not str or len(warning) > 160 for warning in warnings):
        raise Rejected('worker_failed')
      self.status['sourceWarnings'] = list(dict.fromkeys([*self.base_warnings, *warnings]))[:32]
      if self.status['target'] == 'native':
        self.status['framePath'] = str(directory / 'frame')
      media = value.get('media')
      if type(media) is dict:
        if (set(media) != {'epoch', 'codec', 'firstSequence', 'lastSequence', 'width', 'height'} or
            type(media['codec']) is not str or len(media['codec']) > 100 or
            any(type(media[key]) is not int or media[key] < 0 for key in ('epoch', 'firstSequence', 'lastSequence', 'width', 'height')) or
            media['epoch'] != value['epoch']):
          raise Rejected('worker_failed')
        self.status['media'] = dict(media)
        self.status['codec'] = media['codec']
      applied = value.get('lastRequestId')
      if applied == self.pending and applied is not None:
        self.status['lastRequestId'] = applied
        self.pending = None

  def _signal_child(self, child, sig):
    # The renderer may have exited while its engine still owns this process group.
    # Refuse a reused leader PID, but retain ownership after the original leader exits.
    if _process_birth(child.pid) in (None, self.child_birth):
      try:
        os.killpg(child.pid, sig)
      except ProcessLookupError:
        pass

  def _record_session(self, directory, child=None):
    record = {'version': 1, 'ownerPid': os.getpid(), 'ownerBirth': _process_birth(os.getpid()),
              'workerPid': child.pid if child is not None else None,
              'workerBirth': _process_birth(child.pid) if child is not None else None}
    path = directory / 'session.json'
    temporary = directory / 'session.tmp'
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, 'w') as output:
      json.dump(record, output, allow_nan=False)
    temporary.replace(path)

  def recover(self):
    """Called only after acquiring the owner lease; never clean another live owner."""
    entries = list((self.root / 'sessions').iterdir())
    if len(entries) > 64:
      raise Rejected('unavailable', 'Replay recovery needs attention')
    for directory in entries:
      if not _token(directory.name):
        continue
      _owned_dir(directory)
      try:
        fd = os.open(directory / 'session.json', os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
          info = os.fstat(fd)
          if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_size > 1024:
            raise Rejected('unavailable')
          record = parse(os.read(fd, 1025), 1024)
        finally:
          os.close(fd)
      except FileNotFoundError:
        # Unknown contents are preserved rather than mistaken for our session.
        continue
      if (set(record) != {'version', 'ownerPid', 'ownerBirth', 'workerPid', 'workerBirth'} or record['version'] != 1 or
          any(type(record[key]) is not int or record[key] <= 0 for key in ('ownerPid', 'ownerBirth'))):
        raise Rejected('unavailable')
      if _process_birth(record['ownerPid']) == record['ownerBirth']:
        raise Rejected('busy', 'Previous replay owner is still stopping')
      pid, birth = record['workerPid'], record['workerBirth']
      if pid is not None or birth is not None:
        if type(pid) is not int or type(birth) is not int or pid <= 0 or birth <= 0:
          raise Rejected('unavailable')
        current_birth = _process_birth(pid)
        if current_birth is not None and current_birth != birth:
          raise Rejected('stop_unconfirmed')
        if current_birth == birth or _group_active(pid):
          try:
            if current_birth == birth:
              command = Path(f'/proc/{pid}/cmdline').read_bytes()
              if b'openpilot.starpilot.replay.render' not in command or os.getpgid(pid) != pid:
                raise Rejected('stop_unconfirmed')
            os.killpg(pid, signal.SIGKILL)
          except ProcessLookupError:
            pass
          deadline = self.clock() + 1
          while _group_active(pid) and self.clock() < deadline:
            time.sleep(.01)
          if _group_active(pid):
            raise Rejected('stop_unconfirmed')
      prefix = 'replay-' + directory.name[:24]
      ipc = Path('/dev/shm') / ('msgq_' + prefix)
      if ipc.exists() or ipc.is_symlink():
        _owned_dir(ipc)
        shutil.rmtree(ipc)
      Path('/tmp', prefix + '_visionipc_camerad').unlink(missing_ok=True)
      shutil.rmtree(directory)

  def _run(self, sid, route_id, target, segment=None):
    directory = self.root / 'sessions' / sid
    prefix = 'replay-' + sid[:24]
    ipc = Path('/dev/shm') / ('msgq_' + prefix)
    child = lease = None
    error = None
    ipc_owned = False
    try:
      lease = self.catalog.lease(route_id)
      if self.cancel.is_set() or not self.authority():
        raise Rejected('not_offroad')
      self._display_snapshot(directory)
      for name in ('params', 'cache'):
        _owned_dir(directory / name)
      ipc.mkdir(mode=0o700)
      ipc_owned = True
      clock_fd = os.open(ipc / 'display-clock', os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
      try:
        os.fchmod(clock_fd, 0o600)
        os.ftruncate(clock_fd, RECORD.size)
      finally:
        os.close(clock_fd)
      env = dict(os.environ)
      for key in ('SP_HOST_RUNTIME', 'SP_HOST_PARKED', 'SP_HOST_PREFIX', 'SP_HOST_PARAMS_ROOT', 'REPLAY', 'SIMULATION', 'NOBOARD', 'BLOCK'):
        env.pop(key, None)
      env.update(OPENPILOT_PREFIX=prefix, PARAMS_ROOT=str(directory / 'params'), COMMA_CACHE=str(directory / 'cache'),
                 SP_REPLAY_CONTEXT='1', SP_REPLAY_CLOCK_PATH=str(ipc / 'display-clock'), STARPILOT_PROJECTION_READ_ONLY='1',
                 STARPILOT_GALAXY_DISABLE='1', STARPILOT_CLOUD_DISABLED='1', BIG='1' if self.profile == 'large' else '0')
      command = [sys.executable, '-m', 'openpilot.starpilot.replay.render', '--session-dir', str(directory),
                 '--route-id', route_id, '--data-dir', str(self.catalog.root), '--target', target, '--profile', self.profile]
      if segment is not None:
        command.extend(['--start-segment', str(segment)])
      child = self.spawn(_guarded_command(command), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, start_new_session=True, bufsize=0)
      with self.lock:
        self.child, self.child_birth = child, _process_birth(child.pid)
      self._record_session(directory, child)
      assert child.stdout is not None and child.stderr is not None and child.stdin is not None
      for file in (child.stdout, child.stderr, child.stdin):
        os.set_blocking(file.fileno(), False)
      stdout = bytearray()
      diagnostics = bytearray()
      started = last_source_check = self.clock()
      stopped_at = None
      with selectors.DefaultSelector() as selector:
        selector.register(child.stdout, selectors.EVENT_READ)
        selector.register(child.stderr, selectors.EVENT_READ)
        while child.poll() is None or selector.get_map():
          now = self.clock()
          if not self.cancel.is_set():
            if not self.authority():
              error = 'not_offroad'
              self.cancel.set()
            elif now - self.lease_at > LEASE_SECONDS:
              error = 'viewer_disconnected'
              self.cancel.set()
            elif now - last_source_check >= 1:
              last_source_check = now
              if not lease.current():
                error = 'route_changed'
                self.cancel.set()
            if self.status['state'] == 'preparing' and now - started > PREPARE_SECONDS:
              error = 'prepare_timeout'
              self.cancel.set()
            if self.pending is not None and now - self.pending_at > CONTROL_SECONDS:
              error = 'action_timeout'
              self.cancel.set()
          if self.cancel.is_set():
            with self.lock:
              self.status.update(state='stopping', frameReady=False, mediaReady=False)
            if stopped_at is None:
              stopped_at = now
              self._signal_child(child, signal.SIGTERM)
            elif now - stopped_at >= STOP_GRACE_SECONDS:
              self._signal_child(child, signal.SIGKILL)
              if now - stopped_at >= STOP_GRACE_SECONDS + 1:
                raise Rejected('stop_unconfirmed')
          elif not self.commands.empty():
            command = self.commands.get_nowait()
            data = json.dumps(command, separators=(',', ':'), allow_nan=False).encode() + b'\n'
            try:
              written = os.write(child.stdin.fileno(), data)
            except BlockingIOError:
              raise Rejected('worker_unresponsive') from None
            if written != len(data):
              raise Rejected('worker_unresponsive')
          for key, _ in selector.select(timeout=.1):
            chunk = os.read(key.fd, 8192)
            if not chunk:
              selector.unregister(key.fileobj)
              continue
            if key.fileobj is child.stderr:
              diagnostics.extend(chunk)
              del diagnostics[:-65536]
            else:
              stdout.extend(chunk)
              if len(stdout) > 32768:
                raise Rejected('worker_failed')
              while b'\n' in stdout:
                line, _, remaining = stdout.partition(b'\n')
                stdout = bytearray(remaining)
                self._observe(parse(bytes(line), 16384), directory)
          if child.poll() is not None and not selector.get_map():
            break
      if stdout:
        raise Rejected('worker_failed')
      if child.returncode != 0 and not self.cancel.is_set():
        raise Rejected(self.status.get('errorCode') or 'worker_failed')
    except Exception as failure:
      error = getattr(failure, 'code', 'worker_failed')
    finally:
      reaped = child is None
      if child is not None:
        self._signal_child(child, signal.SIGKILL)
        try:
          child.wait(timeout=1)
          deadline = self.clock() + 1
          while _group_active(child.pid) and self.clock() < deadline:
            self._signal_child(child, signal.SIGKILL)
            time.sleep(.01)
          reaped = not _group_active(child.pid)
          if not reaped:
            error = 'stop_unconfirmed'
        except (subprocess.TimeoutExpired, Rejected, OSError):
          error = 'stop_unconfirmed'
        for stream in (child.stdin, child.stdout, child.stderr):
          if stream is not None:
            stream.close()
      if reaped:
        try:
          if lease is not None:
            lease.close()
          if ipc_owned:
            shutil.rmtree(ipc)
            Path('/tmp', prefix + '_visionipc_camerad').unlink(missing_ok=True)
          shutil.rmtree(directory)
        except OSError:
          reaped = False
          error = 'cleanup_failed'
      with self.lock:
        if reaped:
          previous_error = self.status.get('errorCode')
          self.status = self._idle(error or previous_error)
          self.child = self.worker = None
          self.client_id = None
          self.pending = None
          self.session_dir = None
        else:
          self.retained_lease = lease
          self.status.update(state='failed', errorCode=error or 'stop_unconfirmed', frameReady=False, mediaReady=False)

  def close(self):
    with self.lock:
      self.closed = True
      self._stop('owner_stopped')
      worker = self.worker
    if worker is not None:
      worker.join(timeout=STOP_GRACE_SECONDS + 2)
      if worker.is_alive():
        raise RuntimeError('Replay teardown was not confirmed')


def serve(owner, *, stop=None, path=None):
  stop = threading.Event() if stop is None else stop
  path = owner.root / 'owner.sock' if path is None else Path(path)
  if not hasattr(socket, 'SO_PEERCRED') or len(os.fsencode(path)) >= 100:
    raise Rejected('unavailable')
  lock_fd = os.open(path.with_suffix('.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
  bound = False
  try:
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    owner.recover()
    if path.exists() or path.is_symlink():
      info = path.lstat()
      if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
        raise Rejected('unavailable')
      path.unlink()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
      server.bind(str(path))
      bound = True
      os.chmod(path, 0o600)
      server.listen(8)
      server.settimeout(.2)
      while not stop.is_set():
        try:
          peer, _ = server.accept()
        except TimeoutError:
          continue
        with peer:
          peer.settimeout(1)
          _, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
          if uid != os.geteuid():
            continue
          try:
            request = receive(peer, MAX_REQUEST, 1)
            result = {'ok': True, 'result': owner.dispatch(request)}
          except Exception as error:
            code = getattr(error, 'code', 'invalid_request')
            result = {'ok': False, 'error': {'code': code, 'message': str(error)[:200] if hasattr(error, 'code') else 'Replay request unavailable'}}
          try:
            peer.sendall(encode(result, MAX_RESPONSE))
          except (OSError, ValueError):
            pass
  finally:
    try:
      if bound:
        try:
          owner.close()
        finally:
          path.unlink(missing_ok=True)
    finally:
      os.close(lock_fd)


def main():
  from openpilot.common.hardware import HARDWARE
  from openpilot.common.params import Params
  from openpilot.starpilot.replay.catalog import ReplayCatalog
  if os.environ.get('OPENPILOT_PREFIX'):
    raise RuntimeError('Replay owner must use the real device namespace')
  params = Params()
  authority = LiveAuthority(params)
  owner = ReplayOwner(ReplayCatalog(), authority=authority.allowed, params=params,
                      profile='compact' if HARDWARE.get_device_type() == 'mici' else 'large')
  stop = threading.Event()
  for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda *_: stop.set())
  try:
    serve(owner, stop=stop)
  finally:
    try:
      owner.close()
    finally:
      authority.close()


if __name__ == '__main__':
  main()
