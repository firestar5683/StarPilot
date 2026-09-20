"""Galaxy-owned saved replay lifecycle; never starts a composer or a vehicle service."""
import fcntl
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time

from demo_catalog import entry


def read(path):
  try:
    data = json.loads(Path(path).read_text())
    return data if isinstance(data, dict) else {}
  except (OSError, ValueError):
    return {}


def write(path, value):
  path = Path(path)
  temporary = path.with_suffix('.tmp')
  temporary.write_text(json.dumps(value))
  temporary.replace(path)


def process_ticks(pid):
  try:
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
    arguments = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    if fields[0] == 'Z' or not any(argument.endswith(b'/native_prepared_showcase.py') for argument in arguments):
      return None
    return fields[19]
  except (OSError, ValueError, IndexError):
    return None


class DemoSession:
  def __init__(self, root, offroad, *, spawn=subprocess.Popen, ticks=process_ticks, stop_group=None):
    self.root = Path(root)
    self.offroad, self.spawn, self.ticks = offroad, spawn, ticks
    self.stop_group = stop_group or (lambda pid: os.killpg(pid, signal.SIGTERM))
    self.lock = threading.Lock()
    self.owner_path = self.root / 'generated/demo_owner.json'

  def status(self):
    owner = read(self.owner_path)
    pid = owner.get('pid')
    running = type(pid) is int and pid > 1 and self.ticks(pid) == owner.get('start_ticks') and owner.get('start_ticks') is not None
    result = {key: owner.get(key) for key in ('request_id', 'alias', 'route', 'pid', 'out', 'muted')}
    result['screen_mirror'] = owner.get('screen_mirror') is True
    result.update(running=bool(running), generation_invoked=False)
    if owner.get('out'):
      out = Path(owner['out'])
      ready = read(out/'demo_ready.json')
      result['prepared'] = bool(running and ready.get('ready') is True and ready.get('session_id'))
      result['ready_session_id'] = ready.get('session_id') if result['prepared'] else None
      state = read(out/'status.json')
      result['presentation_session_id'] = state.get('presentation_session_id') if running else None
      result['failure'] = read(out/'demo_failure.json').get('error')
      result['complete'] = read(out/'demo_complete.json').get('complete') is True
    return result

  def start(self, data):
    required = {'alias', 'request_id', 'muted'}
    if (not isinstance(data, dict) or not required <= set(data) or set(data) - required - {'screen_mirror'}
        or not isinstance(data['request_id'], str) or not re.fullmatch(r'[a-zA-Z0-9-]{8,80}', data['request_id'])
        or type(data['muted']) is not bool or type(data.get('screen_mirror', False)) is not bool):
      raise ValueError('Saved demo requires an alias, request ID, explicit output choice and optional screen_mirror boolean')
    data = {**data, 'screen_mirror': data.get('screen_mirror', False)}
    if not self.offroad():
      raise ValueError('Saved demo playback requires the vehicle to be offroad')
    selected = entry(self.root, data['alias'])
    with self.lock:
      current = self.status()
      if current['running']:
        if (current['request_id'] == data['request_id'] and current['alias'] == data['alias']
            and current['muted'] == data['muted'] and current['screen_mirror'] == data['screen_mirror']):
          return current
        raise ValueError('A saved demo is already running; stop that owned session first')
      if read(self.owner_path).get('request_id') == data['request_id']:
        raise ValueError('This launch request already finished; use a new request ID')
      (self.root/'generated').mkdir(parents=True, exist_ok=True)
      with (self.root/'generated/native_session.lock').open('a') as lease:
        try: fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('Another RoadScore replay is active') from None
      out = self.root/'results'/('demo_' + data['request_id'])
      out.mkdir(parents=True, exist_ok=False)
      command = ['/usr/local/venv/bin/python', str(self.root/'prototype/native_prepared_showcase.py'),
                 '--roadscore', data['alias'], '--demo', '--hold-start', '--out', str(out),
                 '--score-archive', selected['archive']]
      if selected.get('curve_plan'): command += ['--curve-plan', selected['curve_plan']]
      if data['muted']: command.append('--muted')
      if data['screen_mirror']: command.append('--screen-mirror')
      env = os.environ.copy()
      for key in ('ZMQ', 'OPENPILOT_PREFIX', 'OPENPILOT_ZMQ_NAMESPACE', 'PARAMS_ROOT', 'ROADSCORE_MIRROR_DIR'):
        env.pop(key, None)
      env['PYTHONPATH'] = ':'.join((str(self.root/'prototype'), '/data/openpilot', '/data/roadscore-feasibility/venv/lib/python3.12/site-packages'))
      with (out/'launcher.log').open('wb') as log:
        process = self.spawn(command, cwd='/data/openpilot', env=env, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
      stamp = None
      for _ in range(20):
        stamp = self.ticks(process.pid)
        if stamp is not None or process.poll() is not None: break
        time.sleep(.01)
      if stamp is None:
        raise ValueError('Saved demo launcher failed; inspect its launcher.log')
      write(self.owner_path, {**data, 'route': selected['route'], 'pid': process.pid,
                             'start_ticks': stamp, 'out': str(out), 'created_wall': time.monotonic()})
      return self.status()

  def release(self, data):
    if not isinstance(data, dict) or set(data) != {'request_id', 'session_id'}:
      raise ValueError('Starting prepared playback requires both session identities')
    if not self.offroad():
      raise ValueError('Saved demo playback requires the vehicle to be offroad')
    with self.lock:
      current = self.status()
      if (not current['running'] or not current.get('prepared')
          or current.get('request_id') != data['request_id']
          or current.get('ready_session_id') != data['session_id']):
        raise ValueError('No matching prepared demo is ready')
      path = Path(current['out'])/'start.json'
      previous = read(path)
      deadline = previous.get('start_at_wall')
      if previous.get('session_id') != data['session_id'] or type(deadline) not in (int, float) or not math.isfinite(deadline):
        deadline = time.monotonic() + 1.
        write(path, {'session_id': data['session_id'], 'play': True, 'start_at_wall': deadline})
      return {'request_id': data['request_id'], 'session_id': data['session_id'],
              'start_at_wall': deadline, 'server_wall': time.monotonic()}

  def stop(self, data):
    if not isinstance(data, dict) or set(data) != {'request_id'}:
      raise ValueError('Stopping a saved demo requires its request ID')
    with self.lock:
      current = self.status()
      if current.get('request_id') != data['request_id']:
        raise ValueError('Saved demo session changed; refusing to stop another session')
      if current['running']:
        self.stop_group(current['pid'])
      return {'stopping': current['running'], 'request_id': data['request_id']}
