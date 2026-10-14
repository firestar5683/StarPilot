import hashlib
import json
import os
from pathlib import Path
from unittest import mock

import pytest

from openpilot.starpilot.maps import operation_owner as ops
from openpilot.starpilot.maps import shadow_lifecycle as shadow
from openpilot.starpilot.navigation.navtilesd import Environment, TileDaemon
from openpilot.starpilot.navigation.offline_roads import OfflineState, TileStore
from openpilot.starpilot.navigation.road_tiles import TileKey, decode_road_tile
from openpilot.starpilot.navigation.tests.test_navtilesd import Clock, Session, daemon


def snapshot(root, payload=b'filesystem inventory fixture', *, path='35/-98/35.000000_-98.000000_35.250000_-97.750000'):
  root.mkdir(parents=True, exist_ok=True)
  receipt = {'version': 1, 'tileSchema': 'offline.capnp:0xda3a0d9284ca402f',
             'attribution': '© OpenStreetMap contributors; https://www.openstreetmap.org/copyright (ODbL)',
             'sourceVerified': False, 'sourceKind': 'local-pbf', 'inputs': [{'name': 'fixture', 'size': 1, 'sha256': 'a' * 64}],
             'bounds': [35, -98, 35.25, -97.75],
             'tiles': [{'path': path, 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'empty': False}]}
  raw = json.dumps(receipt, separators=(',', ':')).encode()
  generation = hashlib.sha256(raw).hexdigest()
  selected = root / 'generations' / generation
  selected.mkdir(parents=True)
  (selected / 'receipt.json').write_bytes(raw)
  tile = selected / path
  if '..' not in Path(path).parts:
    tile.parent.mkdir(parents=True, exist_ok=True)
    tile.write_bytes(payload)
  (root / 'current.json').write_text(json.dumps({'version': 1, 'generation': generation}))
  return generation, tile, len(raw) + len(payload)


def test_inventory_reports_actual_nonempty_package_and_survives_owner_reload(tmp_path):
  generation, _, size = snapshot(tmp_path / 'offline')
  owner = ops.MapSnapshotOperationOwner(root=tmp_path / 'offline', parked=lambda: True, package_ready=lambda: True)
  try:
    status = owner.snapshot()
    assert status['state'] == 'idle'
    assert status['selectedGeneration'] == generation
    assert status['selectedSnapshot'] == {'generation': generation, 'storedBytes': size, 'tileCount': 1,
                                          'bounds': [35, -98, 35.25, -97.75]}
    assert owner.setup()['snapshotReady']
    assert not status['selectedForNextShadowStart']
  finally:
    owner.close()
  second = ops.MapSnapshotOperationOwner(root=tmp_path / 'offline', parked=lambda: True, package_ready=lambda: True)
  try:
    assert second.snapshot()['selectedSnapshot']['storedBytes'] == size
  finally:
    second.close()


@pytest.mark.parametrize('damage', ['missing', 'zero', 'truncated', 'symlink', 'folder_symlink'])
def test_missing_or_unsafe_tile_cannot_be_presented_as_download_complete(tmp_path, damage):
  generation, tile, _ = snapshot(tmp_path / 'offline')
  if damage == 'folder_symlink':
    real = tile.parent
    moved = real.with_name('moved')
    real.rename(moved)
    real.symlink_to(moved, target_is_directory=True)
  else:
    tile.unlink()
    if damage == 'zero':
      tile.write_bytes(b'')
    elif damage == 'truncated':
      tile.write_bytes(b'x')
    elif damage == 'symlink':
      other = tmp_path / 'outside'
      other.write_bytes(b'filesystem inventory fixture')
      tile.symlink_to(other)
  assert shadow.selected_snapshot_info(tmp_path / 'offline') is None
  owner = ops.MapSnapshotOperationOwner(root=tmp_path / 'offline', parked=lambda: True)
  try:
    owner._status.update(state='completed', preparedGeneration=generation)
    status = owner.snapshot()
    assert status['state'] == 'unavailable'
    assert status['selectedSnapshot'] is None
    assert not status['selectedForNextShadowStart']
    assert not owner.setup()['snapshotReady']
    assert (tmp_path / 'offline/current.json').is_file()
  finally:
    owner.close()


def test_selector_receipt_without_data_cannot_complete_operation(tmp_path):
  root = tmp_path / 'offline'
  generation, tile, _ = snapshot(root)
  tile.unlink()
  owner = ops.MapSnapshotOperationOwner(root=root, parked=lambda: True, execute=lambda *_: generation)
  try:
    owner._status.update(state='transferring', totalGroups=1)
    owner._work('us_state.Oklahoma', 1024, 2048, generation)
    assert owner._status['state'] != 'completed'
    assert not owner.snapshot()['selectedForNextShadowStart']
  finally:
    owner.close()


def test_road_download_bytes_are_current_before_next_five_minute_trim(tmp_path):
  clock = Clock()
  d = daemon(tmp_path, Session(), clock)
  env = Environment(token='pk.test', network='cellular', onroad=True, map_enabled=True,
                    position=(36.1147, -115.1728), bearing=0.0)
  d.plan(env)
  d.maintain()
  assert d.sizes['driven'] == 0
  assert d.step(env) == 0
  d.status(env, force=True)
  saved_status = OfflineState(tmp_path).status()
  assert saved_status is not None
  stored = saved_status['bytes']['driven']
  assert stored == d.store.size('driven') and stored > 0
  reloaded = TileDaemon(store=TileStore(tmp_path, min_free_bytes=0), clock=clock)
  reloaded.maintain()
  assert reloaded.sizes['driven'] == stored
  env.network, env.token = 'offline', ''
  reloaded.plan(env)
  assert reloaded.step(env) is None
  key_path = next((tmp_path / 'driven').rglob('*.rt'))
  z, x = (int(value) for value in key_path.parts[-3:-1])
  key = TileKey(z, x, int(key_path.stem))
  saved_tile = reloaded.store.read(key)
  assert saved_tile is not None
  assert not decode_road_tile(key, saved_tile).empty


def test_promotion_keeps_storage_totals_exact_and_uses_saved_tile_first(tmp_path):
  d = daemon(tmp_path)
  key = TileKey(14, 2, 3)
  data = d.fetcher.fetch(key, 'pk.test')
  assert data is not None
  assert d._store('cache', key, data)
  assert d.sizes['cache'] == len(data)
  assert d._promote('driven', key)
  assert d.sizes == {'saved': 0, 'driven': len(data), 'cache': 0}
  assert d._promote('saved', key)
  assert d.sizes == {'saved': len(data), 'driven': 0, 'cache': 0}
  assert d.store.find(key) == d.store.path('saved', key)
  assert d.store.read(key) == data


def test_zero_tile_is_repaired_and_failed_sync_is_not_complete(tmp_path):
  store = TileStore(tmp_path, min_free_bytes=0)
  key = TileKey(14, 2, 3)
  path = store.path('saved', key)
  path.parent.mkdir(parents=True)
  path.write_bytes(b'')
  assert store.find(key) is None and not store.has('saved', key) and store.age('saved', key) is None
  assert not store.write('saved', key, b'')
  with mock.patch('openpilot.starpilot.navigation.offline_roads.os.fsync', side_effect=OSError('sync failed')):
    assert not store.write('saved', key, b'nonempty')
  assert not list(path.parent.glob('.tile-*'))
  assert path.read_bytes() == b''



def test_status_reuses_verified_index_and_invalidates_changed_directory(tmp_path):
  generation, tile, _ = snapshot(tmp_path / 'offline')
  owner = ops.MapSnapshotOperationOwner(root=tmp_path / 'offline', parked=lambda: True)
  try:
    original = shadow.selected_snapshot_info
    with mock.patch.object(shadow, 'selected_snapshot_info', wraps=original) as inspect:
      for _ in range(6):
        assert owner.snapshot()['selectedSnapshot']['generation'] == generation
      assert inspect.call_count == 1
      prior = tile.parent.stat()
      tile.unlink()
      os.utime(tile.parent, ns=(prior.st_atime_ns, prior.st_mtime_ns + 1_000_000_000))
      assert tile.parent.stat().st_mtime_ns != prior.st_mtime_ns
      status = owner.snapshot()
      assert inspect.call_count == 2
      assert status['state'] == 'unavailable' and status['selectedSnapshot'] is None
  finally:
    owner.close()



def test_new_parent_directories_are_synced_before_success(tmp_path):
  from openpilot.starpilot.navigation import offline_roads
  sync = offline_roads._sync_directory
  with mock.patch.object(offline_roads, '_sync_directory', wraps=sync) as captured:
    state = OfflineState(tmp_path / 'new/maps/roads')
    assert state.set_settings({'saveDriven': False}) == {'saveDriven': False}
  paths = [call.args[0] for call in captured.call_args_list]
  assert tmp_path in paths and tmp_path / 'new' in paths and tmp_path / 'new/maps' in paths
  assert paths[-1] == state.root



@pytest.mark.parametrize('operation', ['write', 'promote'])
def test_post_replace_sync_failure_cannot_be_credited_until_successful_retry(tmp_path, operation):
  from openpilot.starpilot.navigation import offline_roads
  from openpilot.starpilot.navigation.navtilesd import AreaProgress
  store = TileStore(tmp_path, min_free_bytes=0)
  area = {'latitude': 35.0, 'longitude': -98.0, 'radiusKm': 2.0, 'name': 'Fixture'}
  progress = AreaProgress(area, store, refresh=False)
  key = progress.tiles[0]
  data = daemon(tmp_path).fetcher.fetch(key, 'pk.test')
  assert data is not None
  if operation == 'promote':
    assert store.write('cache', key, data)
  target = store.path('saved', key)
  actual_sync = offline_roads._sync_directory
  fail = [True]
  def sync(directory):
    if fail[0] and directory == target.parent and target.is_file():
      raise OSError('target-directory sync failed after replacement')
    return actual_sync(directory)
  with mock.patch.object(offline_roads, '_sync_directory', side_effect=sync):
    result = store.write('saved', key, data) if operation == 'write' else store.promote('saved', key)
    assert not result and target.is_file() and target.read_bytes() == data
    assert store.find(key) is None and not store.has('saved', key) and store.age('saved', key) is None
    assert not store.promote('saved', key)
    assert list(progress.pending()) == [key] and progress.done == 0
    fail[0] = False
    assert store.has('saved', key)
    assert store.find(key) == target and store.read(key) == data
    assert store.age('saved', key) is not None
    next(progress.pending(), None)
    assert progress.done == 1
  with mock.patch.object(offline_roads, '_sync_directory', side_effect=AssertionError('healthy read must not sync')):
    assert store.has('saved', key) and store.find(key) == target
    assert store.read(key) == data and store.age('saved', key) is not None
