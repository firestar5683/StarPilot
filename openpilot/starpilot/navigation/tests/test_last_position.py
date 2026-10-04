import json
import math
from types import SimpleNamespace

from openpilot.starpilot.navigation.owner import NavigationOwner
from openpilot.starpilot.navigation.position import LastPositionStore
from openpilot.starpilot.navigation.runtime import RouteRuntime


def test_durable_context_survives_owner_restart_loss_toggle_and_boot(tmp_path):
  source = SimpleNamespace(map_position=lambda: {'longitude': -88., 'latitude': 42., 'bearing': 170., 'validForMs': 2000})
  owner = NavigationOwner(tmp_path, runtime_source=source, transient_root=tmp_path / 'boot-one')
  RouteRuntime(owner).update(1_000_000_000, (999_000_000, (-88., 42.), 3., 170.), 0)
  state = owner.configure({'enabled': True, 'token': 'pk.test'}, '0', True)
  assert state['location']['bearing'] == 170
  initial = owner.position_store.path.read_bytes()
  source.map_position = lambda: None
  lost = owner.snapshot()['location']
  assert lost['lastKnown'] and lost['validForMs'] == 0 and lost['latitude'] == 42
  assert owner.position_store.path.read_bytes() == initial
  disabled = owner.configure({'enabled': False}, state['revision'], True)
  enabled = owner.configure({'enabled': True}, disabled['revision'], True)
  assert enabled['location'] == lost
  # Independent owner and new boot-temporary directory model Galaxy restart and reboot.
  restarted = NavigationOwner(tmp_path, runtime_source=source, transient_root=tmp_path / 'boot-two')
  assert restarted.snapshot()['location'] == lost
  source.map_position = lambda: {'longitude': -87., 'latitude': 43., 'validForMs': 1800}
  fresh = restarted.snapshot()['location']
  assert fresh['latitude'] == 43 and fresh['validForMs'] == 1800 and fresh['bearing'] == 170
  source.map_position = lambda: None
  # The always-running daemon records the new fix even while no Galaxy page is open.
  writer = LastPositionStore(tmp_path)
  writer.record({'longitude': -87., 'latitude': 43., 'bearing': None})
  updated = restarted.snapshot()['location']
  assert updated['latitude'] == 43 and updated['bearing'] == 170
  assert not updated.get('controlValid', False)


def test_runtime_records_while_page_closed_without_using_cache_for_control(tmp_path):
  owner = NavigationOwner(tmp_path, runtime_source=lambda: None, transient_root=tmp_path / 'boot')
  runtime = RouteRuntime(owner, engine=SimpleNamespace(), executor=SimpleNamespace())
  # Navigation itself is off: fresh GPS still becomes durable map context.
  value = runtime.update(1_000_000_000, (999_000_000, (-88., 42.), 3., 90.), 0)
  assert not value['controlValid'] and owner.position_store.read()['bearing'] == 90
  initial = owner.position_store.path.read_bytes()
  runtime.update(2_000_000_000, None, 1)
  runtime.update(4_000_000_000, (1, (-86., 44.), 3., 40.), 1)
  assert owner.position_store.path.read_bytes() == initial
  # A new valid fix replaces coordinates, missing bearing retains the last valid bearing.
  runtime.update(4_000_000_000, (3_999_000_000, (-87., 43.), 3., None), 1)
  assert owner.position_store.read()['latitude'] == 43
  assert owner.position_store.read()['bearing'] == 90


def test_invalid_state_and_partial_files_do_not_replace_valid_context(tmp_path):
  store = LastPositionStore(tmp_path)
  store.record({'longitude': -88., 'latitude': 42., 'bearing': 370.})
  initial = store.path.read_bytes()
  assert store.read()['bearing'] == 10
  for point in (None, {}, {'longitude': 181, 'latitude': 42}, {'longitude': math.nan, 'latitude': 42},
                {'longitude': -88, 'latitude': True}):
    store.record(point)
    assert store.path.read_bytes() == initial
  assert store.path.stat().st_mode & 0o777 == 0o600
  store.path.write_text('{"latitude":')
  store = LastPositionStore(tmp_path)
  assert store.read() is None
  store.record({'longitude': -87., 'latitude': 43., 'bearing': math.nan})
  assert store.read()['latitude'] == 43 and 'bearing' not in store.read()
  assert all(p.name == '.position-lock' for p in tmp_path.glob('.position-*'))
  store.path.write_text(json.dumps({'version': 1, 'latitude': 43, 'longitude': -87, 'recordedAt': math.inf}))
  assert LastPositionStore(tmp_path).read() is None

def test_indoor_search_uses_durable_context_without_live_guidance(tmp_path):
  source = SimpleNamespace(map_position=lambda: None, search_position=lambda: None)
  owner = NavigationOwner(tmp_path, runtime_source=source, transient_root=tmp_path / 'boot')
  owner.position_store.record({'longitude': -88., 'latitude': 42., 'bearing': 180.})
  assert owner._search_context() == {'proximity': '-88.000000,42.000000'}
  source.search_position = lambda: (-87., 43.)
  assert owner._search_context() == {'proximity': '-87.000000,43.000000'}

def test_changed_fix_writes_are_bounded_and_shutdown_checkpoints_latest(tmp_path, monkeypatch):
  clock = [0.]
  store = LastPositionStore(tmp_path, clock=lambda: clock[0])
  replaces = []
  import os
  actual_replace = os.replace
  def replace(*args):
    replaces.append(clock[0])
    actual_replace(*args)
  monkeypatch.setattr(os, 'replace', replace)
  for tick in range(201):
    clock[0] = tick / 20
    store.record({'longitude': -88 + tick / 10000, 'latitude': 42., 'bearing': 90.})
  assert replaces == [0., 5., 10.]
  clock[0] = 10.05
  store.record({'longitude': -87., 'latitude': 43., 'bearing': 100.})
  assert store.read()['latitude'] == 43
  store.flush(force=True)
  assert replaces == [0., 5., 10., 10.05]
  assert LastPositionStore(tmp_path).read()['latitude'] == 43


def test_failed_write_preserves_live_status_cache_and_previous_durable_fix(tmp_path, monkeypatch):
  owner = NavigationOwner(tmp_path, runtime_source=SimpleNamespace(
    map_position=lambda: {'longitude': -88., 'latitude': 42., 'bearing': 90., 'validForMs': 2000}),
    transient_root=tmp_path / 'boot')
  RouteRuntime(owner).update(1_000_000_000, (999_000_000, (-88., 42.), 3., 90.), 0)
  owner.configure({'enabled': True, 'token': 'pk.test'}, '0', True)
  previous = owner.position_store.path.read_bytes()
  import os
  monkeypatch.setattr(os, 'replace', lambda *args: (_ for _ in ()).throw(OSError('disk full')))
  owner.position_store.last_attempt = None
  monkeypatch.setattr(owner.runtime_source, 'map_position', lambda: {'longitude': -87., 'latitude': 43., 'validForMs': 1800})
  snapshot = owner.snapshot()
  assert snapshot['location']['latitude'] == 43 and snapshot['location']['validForMs'] == 1800
  assert snapshot['location']['bearing'] == 90
  assert owner.position_store.path.read_bytes() == previous
  runtime = RouteRuntime(owner, engine=SimpleNamespace(), executor=SimpleNamespace())
  assert runtime.update(1_000_000_000, (999_000_000, (-86., 44.), 3., None), 0)['status'] == 'noDestination'
  assert owner.position_store.read()['latitude'] == 44
  assert owner.position_store.path.read_bytes() == previous


def test_daemon_is_sole_writer_and_galaxy_reads_latest_checkpoint_after_clock_correction(tmp_path, monkeypatch):
  import time
  wall = [1000.]
  monkeypatch.setattr(time, 'time', lambda: wall[0])
  daemon = NavigationOwner(tmp_path, runtime_source=lambda: None, transient_root=tmp_path / 'boot')
  runtime = RouteRuntime(daemon)
  # Fresh fixes persist even when navigation is disabled and no Galaxy page is open.
  runtime.update(1_000_000_000, (999_000_000, (-88., 42.), 3., 90.), 0)
  source = SimpleNamespace(map_position=lambda: {'longitude': -87., 'latitude': 43., 'bearing': None, 'validForMs': 1800})
  galaxy = NavigationOwner(tmp_path, runtime_source=source, transient_root=tmp_path / 'boot')
  galaxy.configure({'enabled': True, 'token': 'pk.test'}, '0', True)
  saved = daemon.position_store.path.read_bytes()
  def no_checkpoint(*args, **kwargs):
    raise AssertionError('Galaxy must not write GPS checkpoints')
  monkeypatch.setattr(galaxy.position_store, 'record', no_checkpoint)
  monkeypatch.setattr(galaxy.position_store, 'flush', no_checkpoint)
  assert galaxy.snapshot()['location']['latitude'] == 43
  assert galaxy.snapshot()['location']['bearing'] == 90
  assert daemon.position_store.path.read_bytes() == saved
  source.map_position = lambda: None
  assert galaxy.snapshot()['location']['latitude'] == 42
  # A corrected wall clock must not prevent either checkpointing or reading a fresh fix.
  wall[0] = 900.
  runtime.update(2_000_000_000, (1_999_000_000, (-86., 44.), 3., None), 0)
  daemon.position_store.flush(force=True)
  assert galaxy.snapshot()['location']['latitude'] == 44
  reloaded = NavigationOwner(tmp_path, runtime_source=source, transient_root=tmp_path / 'another-boot')
  assert reloaded.snapshot()['location']['latitude'] == 44
  assert reloaded.snapshot()['location']['bearing'] == 90


def test_explicit_missing_bearing_retains_saved_bearing_in_live_response(tmp_path):
  source = SimpleNamespace(map_position=lambda: {'longitude': -88., 'latitude': 42., 'bearing': 90., 'validForMs': 2000})
  owner = NavigationOwner(tmp_path, runtime_source=source, transient_root=tmp_path / 'boot')
  RouteRuntime(owner).update(1_000_000_000, (999_000_000, (-88., 42.), 3., 90.), 0)
  owner.configure({'enabled': True, 'token': 'pk.test'}, '0', True)
  source.map_position = lambda: {'longitude': -87., 'latitude': 43., 'bearing': None, 'validForMs': 1800}
  value = owner.snapshot()['location']
  assert value['latitude'] == 43 and value['validForMs'] == 1800 and value['bearing'] == 90
