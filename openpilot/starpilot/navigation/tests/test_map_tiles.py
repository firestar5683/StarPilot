from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from openpilot.starpilot.navigation.owner import NavigationOwner, ValidationError

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x0dIHDR' + b'\x00\x00\x02\x00' * 2 + b'fixture'


class Provider:
  def __init__(self, mutate=None, chunks=None):
    self.calls = []
    self.mutate = mutate
    self.chunks = chunks or [PNG]

  @contextmanager
  def get(self, url, **kwargs):
    self.calls.append((url, kwargs))
    if self.mutate:
      self.mutate()
    yield SimpleNamespace(status_code=200, headers={'Content-Type': 'image/png'}, iter_content=lambda size: iter(self.chunks))


def tile_owner(tmp_path, provider, token='pk.fixture'):
  class TileOwner(NavigationOwner):
    def read(self):
      return {'token': token}

  owner = TileOwner(tmp_path, runtime_source=lambda: None, session=provider)
  return owner


@pytest.mark.parametrize('coordinates', [(19, 0, 0), (-1, 0, 0), (1, 2, 0), (1, 0, -1), (True, 0, 0)])
def test_invalid_tiles_never_request_provider(tmp_path, coordinates):
  provider = Provider()
  with pytest.raises(ValidationError):
    tile_owner(tmp_path, provider).map_tile(*coordinates)
  assert not provider.calls


def test_missing_key_and_busy_fail_without_network(tmp_path):
  provider = Provider()
  owner = tile_owner(tmp_path, provider, '')
  with pytest.raises(ValidationError):
    owner.map_tile(0, 0, 0)
  owner = tile_owner(tmp_path, provider)
  for _ in range(4):
    assert owner._tile_slots.acquire(False)
  with pytest.raises(ValidationError):
    owner.map_tile(0, 0, 0)
  assert not provider.calls


def test_fixed_provider_and_server_only_key(tmp_path):
  provider = Provider()
  assert tile_owner(tmp_path, provider).map_tile(2, 3, 1) == PNG
  url, arguments = provider.calls[0]
  assert url == 'https://api.mapbox.com/styles/v1/frogsgomoo/cmcfv151j000o01rcdxebhl76/tiles/512/2/3/1.png'
  assert arguments['params'] == {'access_token': 'pk.fixture'}
  assert arguments['allow_redirects'] is False


def test_key_revoked_during_fetch_discards_bytes(tmp_path):
  provider = Provider()
  owner = tile_owner(tmp_path, provider)
  provider.mutate = lambda: setattr(owner, 'read', lambda: {'token': ''})
  with pytest.raises(ValidationError, match='key changed'):
    owner.map_tile(0, 0, 0)
  assert owner._tile_slots.acquire(False)


def test_oversize_response_releases_slot(tmp_path):
  owner = tile_owner(tmp_path, Provider(chunks=[b'x' * (2 * 1024 * 1024 + 1)]))
  with pytest.raises(ValidationError, match='request limit'):
    owner.map_tile(0, 0, 0)
  assert owner._tile_slots.acquire(False)


def test_cache_reuses_validated_tiles_and_expires(tmp_path, monkeypatch):
  now = [100.0]
  monkeypatch.setattr('openpilot.starpilot.navigation.owner.time.monotonic', lambda: now[0])
  provider = Provider()
  owner = tile_owner(tmp_path, provider)
  assert owner.map_tile(0, 0, 0) == PNG
  assert owner.map_tile(0, 0, 0) == PNG
  assert len(provider.calls) == 1
  now[0] += 61
  assert owner.map_tile(0, 0, 0) == PNG
  assert len(provider.calls) == 2


def test_cache_hit_rechecks_key_and_changed_key_invalidates(tmp_path):
  provider = Provider()
  owner = tile_owner(tmp_path, provider)
  owner.map_tile(0, 0, 0)
  reads = iter(['pk.fixture', ''])
  owner.read = lambda: {'token': next(reads)}
  with pytest.raises(ValidationError, match='key changed'):
    owner.map_tile(0, 0, 0)
  owner.read = lambda: {'token': 'pk.new'}
  owner.map_tile(0, 0, 0)
  assert len(provider.calls) == 2
  assert provider.calls[-1][1]['params']['access_token'] == 'pk.new'


def test_cache_bounds_and_failed_responses_are_not_cached(tmp_path, monkeypatch):
  monkeypatch.setattr('openpilot.starpilot.navigation.owner.TILE_CACHE_BYTES', len(PNG) * 2)
  provider = Provider()
  owner = tile_owner(tmp_path, provider)
  for x in range(3):
    owner.map_tile(2, x, 0)
  assert owner._tile_bytes == len(PNG) * 2
  owner.map_tile(2, 0, 0)
  assert len(provider.calls) == 4
  provider.chunks = [b'not png']
  for _ in range(2):
    with pytest.raises(ValidationError, match='Invalid map tile'):
      owner.map_tile(2, 3, 0)
  assert len(provider.calls) == 6
  monkeypatch.setattr('openpilot.starpilot.navigation.owner.TILE_CACHE_ENTRIES', 1)
  provider.chunks = [PNG]
  owner.map_tile(2, 3, 0)
  assert len(owner._tiles) == 1


def test_provider_runs_without_cache_metadata_lock(tmp_path):
  provider = Provider()
  owner = tile_owner(tmp_path, provider)
  def during_request():
    assert owner._tile_lock.acquire(False)
    owner._tile_lock.release()
  provider.mutate = during_request
  owner.map_tile(0, 0, 0)


def test_authorized_key_change_clears_cache_even_when_key_restored(tmp_path):
  provider = Provider()
  owner = NavigationOwner(tmp_path, runtime_source=lambda: None, session=provider)
  saved = owner.configure({'token': 'pk.first'}, '0', True)
  owner.map_tile(0, 0, 0)
  saved = owner.configure({'token': 'pk.second'}, saved['revision'], True)
  assert not owner._tiles
  owner.configure({'token': 'pk.first'}, saved['revision'], True)
  owner.map_tile(0, 0, 0)
  assert len(provider.calls) == 2
