from pathlib import Path

import pytest

from openpilot.starpilot.soloist import backend, client, credentials, preferences, supervisor
from openpilot.starpilot.soloist.paths import Layout


@pytest.fixture
def layout(tmp_path):
  return Layout(tmp_path / 'soloist')


def test_credentials_are_private_and_never_echoed(layout):
  assert not credentials.present(layout)
  with pytest.raises(credentials.InvalidKey):
    credentials.store('short', layout)
  with pytest.raises(credentials.InvalidKey):
    credentials.store('abc def ghi jkl mno pqr', layout)
  credentials.store('  sk_live_0123456789abcdef  ', layout)
  assert credentials.load(layout) == 'sk_live_0123456789abcdef'
  assert layout.api_key.stat().st_mode & 0o777 == 0o600
  assert layout.api_key.parent.stat().st_mode & 0o777 == 0o700
  credentials.remove(layout)
  assert not credentials.present(layout)


def test_preferences_validate_and_round_trip(layout):
  assert preferences.load(layout) == preferences.Preferences()
  saved = preferences.save(preferences.Preferences(device_name=' Civic ', output_address='aa:bb:cc:dd:ee:ff', output_name='Car'), layout)
  assert saved.device_name == 'Civic' and saved.output_address == 'AA:BB:CC:DD:EE:FF'
  assert preferences.load(layout) == saved
  assert preferences.validated({**preferences.Preferences().__dict__, 'output': 'android_auto'}).output == 'android_auto'
  for bad in ({'device_name': ''}, {'cache_mb': 50}, {'initial_volume': 101}, {'output': 'speaker'}, {'output_address': 'nope'}):
    with pytest.raises(ValueError):
      preferences.validated({**preferences.Preferences().__dict__, **bad})
  layout.config.write_text('{"device_name": 7}')
  assert preferences.load(layout) == preferences.Preferences()


def test_enabled_flag(layout):
  from openpilot.starpilot.soloist.paths import enabled
  assert not enabled(layout)
  preferences.set_enabled(True, layout)
  assert enabled(layout)
  preferences.set_enabled(False, layout)
  assert not enabled(layout)


def test_alsa_config_is_process_local_bluealsa_pcm():
  text = backend.alsa_config('AA:BB:CC:DD:EE:FF', Path('/usr/share/alsa/alsa.conf'))
  assert text.startswith('</usr/share/alsa/alsa.conf>')
  assert 'type bluealsa' in text and 'device "AA:BB:CC:DD:EE:FF"' in text and 'profile "a2dp"' in text
  with pytest.raises(backend.BackendUnavailable):
    backend.alsa_config('AA:BB:CC:DD:EE:FF"\n}', Path('/usr/share/alsa/alsa.conf'))


def test_launch_commands_isolate_the_server_and_player(layout):
  prefs = preferences.Preferences(output_address='AA:BB:CC:DD:EE:FF')
  server = backend.server_launch(layout, prefs, alsa_base=Path('/usr/share/alsa/alsa.conf'))
  assert '-n' in server.argv and '--system=no' in server.argv
  assert any(arg.startswith('module-alsa-sink device=starpilot_spotify') for arg in server.argv)
  assert server.env['ALSA_CONFIG_PATH'].startswith(str(layout.runtime))
  assert (layout.runtime / 'alsa.conf').stat().st_mode & 0o777 == 0o600
  test = backend.server_launch(layout, preferences.Preferences(output='test'))
  assert any(arg.startswith('module-null-sink') for arg in test.argv) and 'ALSA_CONFIG_PATH' not in test.env
  player = backend.player_launch(layout, prefs, 'sk_live_0123456789abcdef')
  assert player.argv[player.argv.index('--ws') + 1] == '127.0.0.1:0'
  assert player.argv[player.argv.index('--cache-size') + 1] == '256'
  assert player.env['PULSE_SERVER'] == f'unix:{layout.runtime}/pulse/native'


def test_vendored_server_matches_its_checksums():
  import hashlib
  root = backend.SERVER_ROOT
  assert backend.bundle_ready()
  sums = [line.split() for line in (root / 'SHA256SUMS').read_text().splitlines() if line.strip()]
  assert {name for _, name in sums} >= {'bin/pulseaudio', 'lib/libpulsecore-16.1.so', 'modules/module-pipe-sink.so'}
  for digest, name in sums:
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
  for name in ('pulseaudio', 'libltdl7', 'liborc-0.4-0t64', 'libsoxr0', 'libspeexdsp1', 'libtdb1'):
    assert (root / 'licenses' / f'{name}.copyright').is_file()


def test_android_auto_output_is_a_real_time_pipe(layout):
  launch = backend.server_launch(layout, preferences.Preferences(output='android_auto'))
  sink = next(arg for arg in launch.argv if arg.startswith('module-pipe-sink'))
  assert f'file={backend.android_auto_pipe(layout)}' in sink
  assert 'rate=48000' in sink and 'channels=2' in sink and 'use_system_clock_for_timing=yes' in sink
  assert launch.env['LD_LIBRARY_PATH'] == str(backend.SERVER_ROOT / 'lib')


ENTITY = {'uri': 'spotify:track:1', 'entity_type': 'track', 'decorations': {
  'identity': {'name': 'My Song\x07'}, 'visual_identity': {'cover': [{'url': 'http://i.scdn.co/a', 'size': 'default'},
                                                                     {'url': 'https://i.scdn.co/image/x', 'size': 'large'},
                                                                     {'url': 'https://evil.example/x', 'size': 'default'}]},
  'parent': {'entity': {'decorations': {'identity': {'name': 'Album'}}}},
  'creators': [{'entity': {'decorations': {'identity': {'name': 'A'}}}}, {'entity': {'decorations': {'identity': {'name': 'B'}}}}],
  'playback': {'duration_ms': 210000}}}


def test_player_state_normalizes_untrusted_events():
  state = client.PlayerState()
  state.apply({'type': 'auth_state', 'logged_in': True, 'is_active': False, 'device_name': 'StarPilot'})
  state.apply({'type': 'playback_state', 'status': 'playing', 'item': ENTITY, 'volume': 65, 'is_active': True,
               'position': {'position_ms': 45000, 'timestamp_ms': 1747654321000, 'speed': 1.0},
               'options': {'shuffle': True, 'repeat': 'context'},
               'available_actions': {'pause': {}, 'skip_next': {}, 'seek_forward': {'step_ms': 15000}, 'bogus': {}}})
  value = state.value
  assert value['track'] == {'title': 'My Song', 'artists': 'A, B', 'album': 'Album', 'artwork': 'https://i.scdn.co/image/x',
                            'kind': 'track', 'durationMs': 210000}
  assert value['actions'] == ['pause', 'skip_next'] and value['shuffle'] and value['repeat'] == 'context'
  state.apply({'type': 'volume_changed', 'volume': 900})
  assert value['volume'] == 65
  state.apply({'type': 'playback_changed', 'status': 'paused'})
  assert value['status'] == 'paused'
  state.apply({'type': 'auth_state', 'logged_in': False})
  assert value['track'] is None and value['actions'] == []


def test_controls_map_to_documented_commands():
  assert client.commands('next', {}) == [{'type': 'command', 'command': 'skip_next'}]
  assert client.commands('volume', {'volume': 40}) == [{'type': 'command', 'command': 'set_volume', 'volume': 40}]
  assert [c['command'] for c in client.commands('repeat', {'mode': 'track'})] == ['set_repeat_context', 'set_repeat_track']
  assert [(c['command'], c['enabled']) for c in client.commands('repeat', {'mode': 'off'})] == \
         [('set_repeat_track', False), ('set_repeat_context', False)]
  for action, args in (('volume', {'volume': 101}), ('seek', {'positionMs': -1}), ('play', {'uri': 'x'}), ('shell', {}),
                       ('shuffle', {'enabled': 1})):
    with pytest.raises(ValueError):
      client.commands(action, args)


def test_endpoint_only_accepts_loopback(tmp_path):
  assert client.endpoint(tmp_path) is None
  (tmp_path / 'ws.addr').write_text('127.0.0.1\n')
  (tmp_path / 'ws.port').write_text('41103\n')
  assert client.endpoint(tmp_path) == 'ws://127.0.0.1:41103'
  (tmp_path / 'ws.addr').write_text('0.0.0.0')
  assert client.endpoint(tmp_path) is None


class FakeProcess:
  def __init__(self, argv, **kwargs):
    import io
    self.argv, self.kwargs = argv, kwargs
    self.pid = 99999999
    self.code = None
    self.stdout = io.BytesIO(b'I client expires in 42 days\nkey ' + b'sk_live_0123456789abcdef\n' if 'soloist' in argv[0] else b'')
  def poll(self): return self.code
  def wait(self, timeout=None): return self.code


class FakeClient:
  def __init__(self, _data):
    self.on_change = lambda: None
    self.started = self.stopped = False
    self.sent = []
  def start(self): self.started = True
  def stop(self): self.stopped = True
  def snapshot(self): return {'connected': True, 'loggedIn': False, 'status': 'idle', 'active': False}
  def send(self, action, args): self.sent.append((action, args))


def ready_layout(layout, monkeypatch, *, expired=False):
  monkeypatch.setattr(supervisor.package, 'release_status', lambda _l: {'installed': True, 'expired': expired})
  monkeypatch.setattr(supervisor.backend, 'bundle_ready', lambda: True)
  layout.root.mkdir(parents=True, exist_ok=True)
  credentials.store('sk_live_0123456789abcdef', layout)
  preferences.save(preferences.Preferences(output='test'), layout)


def make_supervisor(layout, spawned):
  def spawn(argv, **kwargs):
    process = FakeProcess(argv, **kwargs)
    spawned.append(process)
    if 'pulseaudio' in argv[0]:
      backend.runtime_paths(layout)['socket'].touch()
    return process
  now = [100.0]
  sup = supervisor.Supervisor(layout, spawn=spawn, clock=lambda: now[0], make_client=FakeClient)
  return sup, now


def test_supervisor_reports_missing_setup_steps(layout, monkeypatch):
  sup, _ = make_supervisor(layout, [])
  sup.tick()
  assert sup.status()['state'] == 'missing_package'
  monkeypatch.setattr(supervisor.package, 'release_status', lambda _l: {'installed': True})
  sup.tick()
  assert sup.status()['state'] == 'missing_key'
  credentials.store('sk_live_0123456789abcdef', layout)
  sup.tick()
  assert sup.status()['state'] == 'no_output'


def test_supervisor_starts_server_then_player_and_redacts_key(layout, monkeypatch):
  ready_layout(layout, monkeypatch)
  spawned = []
  sup, _ = make_supervisor(layout, spawned)
  sup.tick()
  assert [Path(p.argv[0]).name for p in spawned] == ['pulseaudio', 'soloist']
  assert all(p.kwargs['start_new_session'] for p in spawned)
  assert sup.status()['state'] == 'waiting'
  import time
  time.sleep(0.1)
  assert sup.days_left == 42
  assert all('sk_live' not in line for line in sup.log)
  assert sup.handle({'command': 'control', 'action': 'pause', 'args': {}}) == {'ok': True}
  assert sup.client.sent == [('pause', {})]


def test_supervisor_stops_retrying_an_expired_build(layout, monkeypatch):
  ready_layout(layout, monkeypatch)
  spawned = []
  sup, now = make_supervisor(layout, spawned)
  monkeypatch.setattr(supervisor, '_kill_group', lambda _p: None)
  sup.tick()
  sup.player.code = 10
  now[0] += 1
  sup.tick()
  assert sup.status()['state'] == 'expired'
  now[0] += 1000
  sup.tick()
  assert len(spawned) == 2


def test_supervisor_backs_off_and_rolls_back_a_failing_build(layout, monkeypatch):
  ready_layout(layout, monkeypatch)
  rolled = []
  monkeypatch.setattr(supervisor.package, 'rollback', lambda _l: rolled.append(True) or True)
  monkeypatch.setattr(supervisor, '_kill_group', lambda _p: None)
  spawned = []
  sup, now = make_supervisor(layout, spawned)
  for _ in range(supervisor.MAX_FAST_FAILURES):
    sup.tick()
    sup.player.code = 1
    now[0] += 1
    sup.tick()
    assert sup.status()['state'] == 'retrying'
    now[0] += 100
  assert rolled == [True]


def test_supervisor_waits_for_the_selected_bluetooth_output(layout, monkeypatch):
  ready_layout(layout, monkeypatch)
  preferences.save(preferences.Preferences(output_address='AA:BB:CC:DD:EE:FF', output_name='Car'), layout)
  class Output:
    connected = False
    def ready(self, address):
      return self.connected
  output = Output()
  spawned = []
  sup, now = make_supervisor(layout, spawned)
  sup.output = output
  sup.tick()
  assert sup.status()['state'] == 'waiting_output' and 'Car' in sup.status()['message'] and spawned == []
  output.connected = True
  now[0] += supervisor.OUTPUT_RETRY_SECONDS + 1
  sup.tick()
  assert len(spawned) == 2


def test_control_socket_round_trip(layout, tmp_path):
  import threading
  from openpilot.starpilot.galaxy.spotify_setup import SpotifyClient
  sup, _ = make_supervisor(layout, [])
  import tempfile
  path = tempfile.mktemp(prefix='sp-', suffix='.sock', dir='/tmp')  # AF_UNIX paths are short on macOS
  stop = threading.Event()
  thread = threading.Thread(target=supervisor.serve, args=(sup, path, stop), daemon=True)
  thread.start()
  for _ in range(50):
    if Path(path).exists():
      break
    import time
    time.sleep(0.02)
  result = SpotifyClient(path).call('status')
  assert result['status']['state'] == 'starting'
  with pytest.raises(RuntimeError):
    SpotifyClient(path).call('control', action='pause', args={})
  stop.set()
  thread.join(timeout=2)
  Path(path).unlink(missing_ok=True)


def test_reap_orphans_only_targets_feature_binaries(layout, tmp_path, monkeypatch):
  proc = tmp_path / 'proc'
  (proc / '100').mkdir(parents=True)
  (proc / '200').mkdir()
  binary = layout.root / 'releases' / 'x' / 'soloist'
  binary.parent.mkdir(parents=True)
  binary.write_text('')
  (proc / '100' / 'exe').symlink_to(binary)
  (proc / '200' / 'exe').symlink_to('/usr/bin/bluealsa')
  killed = []
  monkeypatch.setattr(supervisor.os, 'kill', lambda pid, sig: killed.append(pid))
  assert supervisor.reap_orphans(layout, proc) == 1 and killed == [100]


def test_status_publishes_the_spotify_track_for_the_car_screen(layout):
  sup, _ = make_supervisor(layout, [])
  sup.client = type('Client', (), {'snapshot': lambda self: {
    'connected': True, 'loggedIn': True, 'active': True, 'status': 'playing', 'position': None,
    'track': {'title': 'Song', 'artists': 'Band', 'album': '', 'durationMs': 1000}}})()
  assert sup.status()['nowPlaying']['title'] == 'Song'
  sup.client = None
  assert sup.status()['nowPlaying'] is None


def test_status_publishes_the_phone_track_only_while_phone_audio_runs(layout):
  sup, _ = make_supervisor(layout, [])
  sup.phone_prefs = object()
  sup.phone_track = {'Status': 'playing', 'Track': {'Title': 'Phone Song', 'Artist': 'Band'}}
  assert sup.status()['nowPlaying'] is None
  sup.player = object()
  found = sup.status()['nowPlaying']
  assert found['source'] == 'phone' and found['title'] == 'Phone Song'
