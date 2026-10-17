"""spotifyd: owns the private audio server, the Soloist player and its API connection.

Started by the manager only while Spotify is enabled. Music is never driving-critical: every failure
here stays inside this process group and shows up as a status, never as a driving alert.
"""
from __future__ import annotations

import collections
import json
import os
import random
import re
import shutil
import signal
import socket
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from openpilot.starpilot.soloist import backend, credentials, package, preferences
from openpilot.starpilot.soloist.client import PlayerClient
from openpilot.starpilot.soloist.paths import CONTROL_SOCKET, Layout, private_dir

A2DP_SINK = '0000110b-0000-1000-8000-00805f9b34fb'
EXIT_EXPIRED = 10
STOP_SECONDS = 5.0
OUTPUT_RETRY_SECONDS = 20.0
MAX_FAST_FAILURES = 5
LOG_LINES = 200
EXPIRES_IN = re.compile(r'client expires in (\d+) days?')


def _kill_group(process: subprocess.Popen | None) -> None:
  if process is None or process.poll() is not None:
    return
  try:
    os.killpg(process.pid, signal.SIGTERM)
    process.wait(timeout=STOP_SECONDS)
  except (ProcessLookupError, PermissionError):
    pass
  except subprocess.TimeoutExpired:
    try:
      os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
      pass
    process.wait(timeout=STOP_SECONDS)


def reap_orphans(layout: Layout, proc: Path = Path('/proc')) -> int:
  """Kill leftover players/audio servers from a supervisor that was killed before it could stop them."""
  root = os.path.realpath(layout.root) + os.sep
  killed = 0
  for entry in proc.glob('[0-9]*'):
    try:
      exe = os.path.realpath(entry / 'exe')
    except OSError:
      continue
    if exe.startswith(root):
      try:
        os.kill(int(entry.name), signal.SIGKILL)
        killed += 1
      except (ProcessLookupError, PermissionError, ValueError):
        pass
  return killed


class BluetoothOutput:
  """Readiness of the one selected speaker. Connects only its A2DP profile, never pairs or switches devices."""

  def __init__(self):
    self.client = None

  def ready(self, address: str) -> bool:
    try:
      from openpilot.starpilot.bluetooth.owner import BlueZ, DEVICE
      if self.client is None:
        self.client = BlueZ()
      for path, interfaces in self.client._objects().items():
        props = interfaces.get(DEVICE)
        if props and str(props.get('Address', '')).upper() == address:
          if props.get('Connected') is True:
            return True
          if props.get('Paired') is True:
            self.client._call(path, DEVICE, 'ConnectProfile', 's', (A2DP_SINK,), timeout=15.0)
          return False
    except Exception:
      self._reset()
    return False

  def _reset(self) -> None:
    client, self.client = self.client, None
    if client is not None:
      try:
        client.close()
      except Exception:
        pass


class Supervisor:
  def __init__(self, layout: Layout | None = None, *, output: BluetoothOutput | None = None,
               spawn: Callable[..., subprocess.Popen] = subprocess.Popen, clock: Callable[[], float] = time.monotonic,
               make_client: Callable[[Path], PlayerClient] | None = None):
    self.layout = layout or Layout.default()
    self.output = output or BluetoothOutput()
    self.spawn, self.clock = spawn, clock
    self.make_client = make_client or (lambda data: PlayerClient(data))
    self.server: subprocess.Popen | None = None
    self.player: subprocess.Popen | None = None
    self.client: PlayerClient | None = None
    self.launched: tuple | None = None
    self.release_target: str | None = None
    self.lock = threading.Lock()
    self.log: collections.deque[str] = collections.deque(maxlen=LOG_LINES)
    self.state, self.message = 'starting', ''
    self.fast_failures, self.retry_at, self.started_at = 0, 0.0, 0.0
    self.expired_target: str | None = None
    self.days_left: int | None = None
    self.secret = ''

  # ---- status ---------------------------------------------------------------------------------------
  def _set(self, state: str, message: str = '') -> None:
    if (state, message) != (self.state, self.message):
      self.state, self.message = state, message
      self.publish()

  def status(self) -> dict:
    player = self.client.snapshot() if self.client is not None else None
    state = self.state
    if state == 'running' and player is not None:
      state = ('connecting' if not player['connected'] else 'waiting' if not player['loggedIn'] else
               'playing' if player['status'] == 'playing' and player['active'] else 'ready')
    return {'state': state, 'message': self.message, 'daysLeft': self.days_left, 'player': player,
            'log': list(self.log)[-20:]}

  def publish(self) -> None:
    try:
      private_dir(self.layout.runtime)
      temporary = self.layout.status.with_suffix('.tmp')
      temporary.write_text(json.dumps(self.status()))
      os.replace(temporary, self.layout.status)
    except OSError:
      pass

  # ---- children -------------------------------------------------------------------------------------
  def _record(self, stream, label: str) -> None:
    for raw in iter(stream.readline, b''):
      line = raw.decode('utf-8', 'replace').rstrip()
      line = re.sub(r'\x1b\[[0-9;]*m', '', line)
      if self.secret:
        line = line.replace(self.secret, '[api key]')
      with self.lock:
        self.log.append(f'{label}: {line[:300]}')
      match = EXPIRES_IN.search(line)
      if match:
        self.days_left = int(match.group(1))

  def _start(self, launch: backend.Launch, label: str) -> subprocess.Popen:
    process = self.spawn(launch.argv, env=launch.env, cwd=str(self.layout.runtime), stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    threading.Thread(target=self._record, args=(process.stdout, label), name=f'spotify_{label}_log', daemon=True).start()
    return process

  def stop_children(self) -> None:
    if self.client is not None:
      self.client.stop()
      self.client = None
    _kill_group(self.player)
    _kill_group(self.server)
    self.player = self.server = None
    self.launched = None

  # ---- policy ---------------------------------------------------------------------------------------
  def desired(self) -> tuple[str, str, tuple | None]:
    """Return (state, message, launch key). The key changes whenever the player must restart."""
    release = package.release_status(self.layout)
    if not release['installed']:
      return 'missing_package', 'Upload Spotify Soloist to finish setup.', None
    target = os.path.realpath(self.layout.current)
    if release.get('expired') or self.expired_target == target:
      return 'expired', 'This Soloist build expired. Download the newest one from Spotify and upload it.', None
    key = credentials.load(self.layout)
    if key is None:
      return 'missing_key', 'Add your Soloist API key.', None
    prefs = preferences.load(self.layout)
    if prefs.output == 'bluetooth' and not prefs.output_address:
      return 'no_output', 'Choose where music plays.', None
    if not backend.bundle_ready():
      return 'audio_unavailable', 'This build is missing the Spotify audio component.', None
    return 'running', '', (target, key, prefs)

  def tick(self) -> None:
    state, message, launch_key = self.desired()
    now = self.clock()
    if launch_key != self.launched:
      self.stop_children()
    if launch_key is None:
      self._set(state, message)
      return
    target, key, prefs = launch_key
    if self.release_target != target:
      self.release_target, self.fast_failures, self.retry_at = target, 0, 0.0
    if self.player is not None:
      self._watch(now, target)
      return
    if now < self.retry_at:
      return
    if prefs.output == 'bluetooth' and not self.output.ready(prefs.output_address):
      name = prefs.output_name or 'your Bluetooth speaker'
      self._set('waiting_output', f'Waiting for {name} to connect over Bluetooth.')
      self.retry_at = now + OUTPUT_RETRY_SECONDS
      return
    self.secret = key
    self._set('starting', 'Starting Spotify…')
    try:
      self.server = self._start(backend.server_launch(self.layout, prefs), 'audio')
      deadline = now + 5.0
      socket_path = backend.runtime_paths(self.layout)['socket']
      while not socket_path.exists() and self.server.poll() is None and self.clock() < deadline:
        time.sleep(0.1)
      if not socket_path.exists():
        raise RuntimeError('audio output could not open')
      self.player = self._start(backend.player_launch(self.layout, prefs, key), 'soloist')
    except (OSError, RuntimeError, backend.BackendUnavailable) as error:
      self.stop_children()
      self._fail(now, f'Could not start Spotify: {error}')
      return
    self.launched, self.started_at = launch_key, now
    self.client = self.make_client(self.layout.state)
    self.client.on_change = self.publish
    self.client.start()
    self._set('running')

  def _watch(self, now: float, target: str) -> None:
    code = self.player.poll() if self.player is not None else None
    server_dead = self.server is not None and self.server.poll() is not None
    if code is None and not server_dead:
      if now - self.started_at > 60:
        self.fast_failures = 0
      return
    self.stop_children()
    if code == EXIT_EXPIRED:
      self.expired_target = target
      self._set('expired', 'This Soloist build expired. Download the newest one from Spotify and upload it.')
      return
    detail = 'audio output closed' if server_dead and code is None else f'player exited ({code})'
    self._fail(now, f'Spotify stopped: {detail}. Retrying…')

  def _fail(self, now: float, message: str) -> None:
    self.fast_failures += 1
    if self.fast_failures >= MAX_FAST_FAILURES and package.rollback(self.layout):
      self.fast_failures = 0
      message = 'The new Soloist build would not start; went back to the previous one.'
    elif self.fast_failures >= MAX_FAST_FAILURES:
      self.retry_at = now + 300
      self._set('failed', message.replace('Retrying…', 'Will retry in a few minutes.'))
      return
    self.retry_at = now + min(60.0, 2.0 ** self.fast_failures) * random.uniform(0.8, 1.2)
    self._set('retrying', message)

  # ---- control --------------------------------------------------------------------------------------
  def handle(self, request: dict) -> dict:
    command = request.get('command')
    if command == 'status':
      return {'ok': True, 'status': self.status()}
    if command == 'control':
      client = self.client
      if client is None:
        return {'ok': False, 'error': 'Spotify isn’t running'}
      args = request.get('args', {})
      if not isinstance(args, dict):
        return {'ok': False, 'error': 'Invalid control'}
      client.send(str(request.get('action')), args)
      return {'ok': True}
    if command == 'reset_session':
      with self.lock:
        self.stop_children()
        shutil.rmtree(self.layout.state, ignore_errors=True)
        shutil.rmtree(self.layout.cache, ignore_errors=True)
      return {'ok': True}
    if command == 'clear_cache':
      with self.lock:
        self.stop_children()
        shutil.rmtree(self.layout.cache, ignore_errors=True)
      return {'ok': True}
    return {'ok': False, 'error': 'Unknown command'}


def serve(supervisor: Supervisor, path: str = CONTROL_SOCKET, stop: threading.Event | None = None) -> None:
  try:
    os.unlink(path)
  except FileNotFoundError:
    pass
  server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  server.bind(path)
  os.chmod(path, 0o600)
  server.listen(4)
  server.settimeout(0.5)
  while stop is None or not stop.is_set():
    try:
      connection, _ = server.accept()
    except TimeoutError:
      continue
    with connection:
      connection.settimeout(2.0)
      try:
        data = bytearray()
        while not data.endswith(b'\n') and len(data) < 8192:
          chunk = connection.recv(4096)
          if not chunk:
            break
          data.extend(chunk)
        request = json.loads(data)
        result = supervisor.handle(request) if isinstance(request, dict) else {'ok': False, 'error': 'Invalid request'}
      except (ValueError, OSError, RuntimeError) as error:
        result = {'ok': False, 'error': str(error) or 'Invalid request'}
      try:
        connection.sendall(json.dumps(result).encode() + b'\n')
      except OSError:
        pass


def main() -> None:
  os.nice(10)  # music yields to everything driving-related; children inherit this
  supervisor = Supervisor()
  reap_orphans(supervisor.layout)
  stop = threading.Event()

  def shutdown(*_):
    stop.set()
  signal.signal(signal.SIGTERM, shutdown)
  signal.signal(signal.SIGINT, shutdown)
  threading.Thread(target=serve, args=(supervisor, CONTROL_SOCKET, stop), name='spotify_control', daemon=True).start()
  try:
    while not stop.is_set():
      with supervisor.lock:
        supervisor.tick()
      supervisor.publish()
      stop.wait(1.0)
  finally:
    supervisor.stop_children()
    try:
      os.unlink(CONTROL_SOCKET)
    except FileNotFoundError:
      pass


if __name__ == '__main__':
  main()
