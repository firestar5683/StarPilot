from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
import stat
import sys
import subprocess
from urllib.parse import quote
from pathlib import Path
import tempfile
import threading
import time
import uuid
from itertools import islice

import requests

from openpilot.starpilot.storage import starpilot_storage_root
from openpilot.starpilot.navigation.position import LastPositionStore

MAX_DOCUMENT = 256 * 1024
MAX_RESPONSE = 8 * 1024 * 1024
SEARCH_TTL = 180
ACTIVE_TTL = 12 * 60 * 60
MAX_SEARCHES = 32


class ValidationError(ValueError):
  pass


class ConflictError(ValueError):
  pass


def destination(value: dict) -> dict:
  if not isinstance(value, dict):
    raise ValidationError('Choose a destination')
  name = value.get('name', '')
  latitude, longitude = value.get('latitude'), value.get('longitude')
  if (not isinstance(name, str) or not 1 <= len(name.strip()) <= 256 or
      (not isinstance(latitude, (int, float)) or isinstance(latitude, bool) or not math.isfinite(latitude) or
       not isinstance(longitude, (int, float)) or isinstance(longitude, bool) or not math.isfinite(longitude)) or
      not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
    raise ValidationError('Destination name and coordinates are invalid')
  identity = hashlib.sha256(f'{latitude:.6f},{longitude:.6f}'.encode()).hexdigest()[:20]
  return {'id': identity, 'name': name.strip(), 'latitude': float(latitude), 'longitude': float(longitude)}


def response_json(session, url: str, params: dict) -> dict:
  started = time.monotonic()
  try:
    with session.get(url, params=params, timeout=(3, 2), stream=True) as response:
      if response.status_code != 200:
        raise ValidationError('The map service could not complete this request')
      raw = bytearray()
      for chunk in response.iter_content(64 * 1024):
        raw.extend(chunk)
        if time.monotonic() - started > 10:
          raise ValidationError('The map service took too long to respond')
        if len(raw) > MAX_RESPONSE:
          raise ValidationError('The map service response is too large')
      result = json.loads(raw)
      if not isinstance(result, dict):
        raise ValueError
      return result
  except (requests.RequestException, ValueError) as exc:
    if isinstance(exc, ValidationError):
      raise
    raise ValidationError('The map service could not complete this request') from None


class NavigationOwner:
  def __init__(self, root: Path | None = None, runtime_source=None, session=requests, transient_root: Path | None = None):
    self.root = Path(root) if root is not None else starpilot_storage_root() / 'navigation'
    self.path = self.root / 'settings.json'
    self.position_store = LastPositionStore(self.root)
    self.runtime_source, self.session = runtime_source, session
    self._tile_slots = threading.BoundedSemaphore(4)
    self._lock = threading.RLock()
    self._searches = {}
    identity = hashlib.sha256(str(self.root.resolve()).encode()).hexdigest()[:24]
    if transient_root is not None:
      self.transient_root = Path(transient_root)
    elif sys.platform == "linux":
      self.transient_root = Path("/dev/shm") / ("starpilot-navigation-" + identity)
    else:
      boot = subprocess.check_output(["/usr/sbin/sysctl", "-n", "kern.boottime"]).strip()
      boot_id = hashlib.sha256(boot).hexdigest()[:16]
      self.transient_root = Path("/tmp") / ("starpilot-navigation-" + boot_id + "-" + identity)

  def read(self) -> dict:
    try:
      with self.path.open('rb') as source:
        raw = source.read(MAX_DOCUMENT + 1)
    except FileNotFoundError:
      return {'version': 1, 'revision': '0', 'enabled': False, 'token': '', 'destination': None, 'favorites': []}
    try:
      value = json.loads(raw)
      if (len(raw) > MAX_DOCUMENT or not isinstance(value, dict) or value.get('version') != 1 or
          type(value.get('enabled')) is not bool or not isinstance(value.get('token'), str) or
          not isinstance(value.get('revision'), str) or not 1 <= len(value['revision']) <= 64 or
          any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for ch in value['revision']) or
          len(value['token']) > 2048 or 'destination' not in value or
          type(value.get('routeChoice', 0)) is not int or not 0 <= value.get('routeChoice', 0) <= 2 or
          not isinstance(value.get('favorites'), list) or len(value['favorites']) > 100):
        raise ValueError
      if value.get('destination') is not None:
        value['destination'] = destination(value['destination'])
      value['favorites'] = [destination(item) for item in value['favorites']]
      return value
    except (ValueError, TypeError, KeyError):
      raise ValidationError('Saved navigation settings could not be read') from None

  def _temporary_directory(self):
    self.transient_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(self.transient_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    info = os.fstat(fd)
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
      os.close(fd)
      raise ValidationError('Navigation temporary storage is unavailable')
    return fd

  def _sweep_active(self, current):
    directory = self._temporary_directory()
    try:
      with os.scandir(directory) as entries:
        for entry in islice(entries, MAX_SEARCHES + 1):
          if ((entry.name.endswith('.json') and entry.name != current['revision'] + '.json') or
              entry.name.startswith('.active-')):
            os.unlink(entry.name, dir_fd=directory)
    finally:
      os.close(directory)

  def _read_active(self, current):
    directory = self._temporary_directory()
    try:
      try:
        fd = os.open(current['revision'] + '.json', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
      except FileNotFoundError:
        return None
      with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
          raise ValidationError('Navigation temporary storage is unavailable')
        raw = source.read(4097)
      value = json.loads(raw)
      if (len(raw) > 4096 or set(value) != {'version', 'revision', 'expires', 'destination'} or type(value['version']) is not int or value['version'] != 1 or
          not isinstance(value['revision'], str) or type(value['expires']) not in (float, int) or
          not math.isfinite(value['expires'])):
        raise ValueError
      selected = destination(value['destination'])
      if value['revision'] != current['revision'] or not time.monotonic() < value['expires'] <= time.monotonic() + ACTIVE_TTL:
        os.unlink(current['revision'] + '.json', dir_fd=directory)
        return None
      return dict(value, destination=selected)
    except (ValueError, TypeError, KeyError):
      raise ValidationError('Navigation temporary destination could not be read') from None
    finally:
      os.close(directory)

  def _write_active(self, value):
    directory = self._temporary_directory()
    name = '.active-' + uuid.uuid4().hex
    try:
      fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
      with os.fdopen(fd, 'w') as out:
        json.dump(value, out, allow_nan=False, separators=(',', ':'))
        out.flush()
        os.fsync(out.fileno())
      os.replace(name, value['revision'] + '.json', src_dir_fd=directory, dst_dir_fd=directory)
      os.fsync(directory)
    finally:
      try:
        os.unlink(name, dir_fd=directory)
      except FileNotFoundError:
        pass
      os.close(directory)

  def read_routing(self):
    with self._exclusive():
      current = self.read()
      self._sweep_active(current)
      active = self._read_active(current)
      if active is not None:
        current['destination'] = dict(active['destination'], temporary=True)
      return current

  @contextmanager
  def _exclusive(self):
    with self._lock:
      self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
      with (self.root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield

  def _change(self, transform, expected_revision: str, authorized, *, active_destination=None, preserve_active=False) -> dict:
    with self._exclusive():
      current = self.read()
      if not isinstance(expected_revision, str) or current['revision'] != expected_revision:
        raise ConflictError('Navigation changed; refresh and try again')
      self._sweep_active(current)
      active = self._read_active(current) if preserve_active else None
      transform(current)
      if not (authorized() if callable(authorized) else authorized is True):
        raise PermissionError('Navigation changes are not available right now')
      current['revision'] = uuid.uuid4().hex
      if active_destination is not None:
        active = {'version':1, 'destination':active_destination, 'expires':time.monotonic() + ACTIVE_TTL}
      if active is not None:
        self._write_active(dict(active, revision=current['revision']))
      committed = False
      fd, temporary = tempfile.mkstemp(dir=self.root, prefix='.settings-')
      try:
        with os.fdopen(fd, 'w') as out:
          json.dump(current, out, allow_nan=False, separators=(',', ':'))
          out.flush()
          os.fsync(out.fileno())
        if not (authorized() if callable(authorized) else authorized is True):
          raise PermissionError('Navigation changes are not available right now')
        os.replace(temporary, self.path)
        committed = True
        temporary_directory = self._temporary_directory()
        try:
          with os.scandir(temporary_directory) as entries:
            for stale in islice(entries, MAX_SEARCHES + 1):
              if stale.name.endswith('.json') and stale.name != current['revision'] + '.json':
                os.unlink(stale.name, dir_fd=temporary_directory)
        finally:
          os.close(temporary_directory)
        directory = os.open(self.root, os.O_RDONLY)
        try:
          os.fsync(directory)
        finally:
          os.close(directory)
      finally:
        Path(temporary).unlink(missing_ok=True)
        if not committed and active is not None:
          directory = self._temporary_directory()
          try:
            os.unlink(current['revision'] + '.json', dir_fd=directory)
          except FileNotFoundError:
            pass
          finally:
            os.close(directory)
    return self.snapshot()

  def snapshot(self) -> dict:
    with self._lock:
      return self._snapshot()

  def _snapshot(self) -> dict:
    document = self.read_routing()
    from openpilot.common.params import Params
    is_metric = Params().get_bool('IsMetric')
    status = ('disabled' if not document['enabled'] else 'needsKey' if not document['token'] else
              'noDestination' if document['destination'] is None else 'waitingForLocation')
    result = {key: document[key] for key in ('enabled', 'destination', 'favorites', 'revision')}
    result['alternatives'] = self.route_options(document['revision'])
    result['selectedRoute'] = document.get('routeChoice', 0)
    result.update(hasKey=bool(document['token']), status=status, instruction=None, route=[], isMetric=is_metric, location=None)
    if document['enabled'] and document['token']:
      if self.runtime_source is None:
        from openpilot.starpilot.navigation.status import NavigationStatusSource
        self.runtime_source = NavigationStatusSource()
      if hasattr(self.runtime_source, 'map_position'):
        try:
          result['location'] = self.runtime_source.map_position()
        except (OSError, ValueError, RuntimeError):
          result['location'] = None
      if result['location'] is not None and result['location'].get('validForMs', 0) > 0:
        # navigationd is the sole durable writer; HTTP reads must not checkpoint older samples.
        saved = self.position_store.read()
        bearing = result['location'].get('bearing')
        if saved and 'bearing' in saved and (not isinstance(bearing, (int, float)) or isinstance(bearing, bool) or not math.isfinite(bearing)):
          result['location'] = dict(result['location'], bearing=saved['bearing'])
      if result['location'] is None:
        result['location'] = self.position_store.read()
      state = (self.runtime_source() if callable(self.runtime_source) else self.runtime_source.snapshot()) if document['destination'] else None
      if document['destination'] and isinstance(state, dict) and state.get('revision') == document['revision']:
        for key in ('status', 'instruction', 'route'):
          result[key] = state[key]
    return result

  def route_options(self, revision):
    try:
      value = json.loads((self.transient_root / 'routes.cache').read_text())
      return value['routes'] if value['revision'] == revision and time.monotonic() < value['expires'] else []
    except (OSError, ValueError, KeyError):
      return []

  def record_routes(self, revision, routes):
    rows = [{'index': index, 'durationSeconds': route.total_duration, 'distanceMeters': route.total_distance,
             'geometry': route.preview()} for index, route in enumerate(routes)]
    with self._exclusive():
      if self.read()['revision'] != revision:
        return
      directory = self._temporary_directory()
      os.close(directory)
      fd, name = tempfile.mkstemp(dir=self.transient_root, prefix='.routes-')
      try:
        with os.fdopen(fd, 'w') as out:
          json.dump({'revision': revision, 'expires': time.monotonic() + ACTIVE_TTL, 'routes': rows}, out, allow_nan=False)
        os.replace(name, self.transient_root / 'routes.cache')
      finally:
        Path(name).unlink(missing_ok=True)

  def select_route(self, index, expected_revision, authorized):
    if self.read()['revision'] != expected_revision:
      raise ConflictError('Navigation changed; refresh and try again')
    rows = self.route_options(expected_revision)
    if type(index) is not int or not 0 <= index < len(rows):
      raise ValidationError('This route is no longer available; refresh and try again')
    result = self._change(lambda doc: doc.update(routeChoice=index), expected_revision, authorized, preserve_active=True)
    # Retain choices across the preference revision without requesting another route.
    with self._exclusive():
      value = {'revision': result['revision'], 'expires': time.monotonic() + ACTIVE_TTL, 'routes': rows}
      (self.transient_root / 'routes.cache').write_text(json.dumps(value, allow_nan=False))
    return self.snapshot()

  def map_tile(self, z: int, x: int, y: int) -> bytes:
    if any(type(v) is not int for v in (z, x, y)) or not 0 <= z <= 18 or not 0 <= x < 2 ** z or not 0 <= y < 2 ** z:
      raise ValidationError('Invalid map tile')
    token = self.read()['token']
    if not token:
      raise ValidationError('Save a Mapbox key to view the map')
    if not self._tile_slots.acquire(blocking=False):
      raise ValidationError('Map is busy; try again')
    try:
      started = time.monotonic()
      with self.session.get(f'https://api.mapbox.com/styles/v1/frogsgomoo/cmcfv151j000o01rcdxebhl76/tiles/512/{z}/{x}/{y}.png',
                            params={'access_token': token}, timeout=(2, 2), stream=True, allow_redirects=False) as response:
        if response.status_code != 200 or response.headers.get('Content-Type', '').split(';')[0] != 'image/png':
          raise ValidationError('Map tiles are unavailable')
        raw = bytearray()
        for chunk in response.iter_content(64 * 1024):
          raw.extend(chunk)
          if len(raw) > 2 * 1024 * 1024 or time.monotonic() - started > 5:
            raise ValidationError('Map tile exceeded the request limit')
        if bytes(raw[:8]) != b'\x89PNG\r\n\x1a\n' or bytes(raw[12:16]) != b'IHDR' or bytes(raw[16:24]) != b'\x00\x00\x02\x00' * 2:
          raise ValidationError('Invalid map tile response')
      if self.read()['token'] != token:
        raise ValidationError('Map key changed; try again')
      return bytes(raw)
    except requests.RequestException:
      raise ValidationError('Map tiles are unavailable') from None
    finally:
      self._tile_slots.release()

  def configure(self, patch: dict, expected_revision: str, authorized) -> dict:
    if not isinstance(patch, dict) or not patch or set(patch) - {'enabled', 'token'}:
      raise ValidationError('Unknown navigation setting')
    if 'enabled' in patch and type(patch['enabled']) is not bool:
      raise ValidationError('Navigation enabled must be on or off')
    if 'token' in patch and (not isinstance(patch['token'], str) or len(patch['token']) > 2048 or
                             any(ch.isspace() for ch in patch['token'])):
      raise ValidationError('Enter a valid Mapbox access token')
    with self._lock:
      self._searches.clear()
    return self._change(lambda value: value.update(patch), expected_revision, authorized)

  def search(self, query: str) -> list[dict]:
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 256:
      raise ValidationError('Enter at least two characters to search')
    token = self.read()['token']
    if not token:
      raise ValidationError('Add your Mapbox access token first')
    data = response_json(self.session, 'https://api.mapbox.com/search/geocode/v6/forward',
                         {'q': query.strip(), 'access_token': token, 'limit': 8, 'autocomplete': 'false', 'permanent': 'true'})
    results = []
    features = data.get('features')
    if not isinstance(features, list):
      raise ValidationError('The map service returned invalid search results')
    for feature in features[:8]:
      try:
        properties = feature['properties']
        coordinates = feature['geometry']['coordinates']
        name = properties.get('full_address') or properties.get('name') or properties.get('name_preferred')
        results.append(destination({'name': name, 'longitude': coordinates[0], 'latitude': coordinates[1]}))
      except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        continue
    return results

  def cancel_search(self, caller, search_id):
    if not isinstance(search_id, str):
      raise ValidationError('Start a new destination search')
    with self._lock:
      self._searches.pop((caller, search_id), None)

  def _search_context(self) -> dict:
    with self._lock:
      try:
        if self.runtime_source is None:
          from openpilot.starpilot.navigation.status import NavigationStatusSource
          self.runtime_source = NavigationStatusSource()
        position = getattr(self.runtime_source, 'search_position', None)
        if position is None:
          return {}
        coordinates = position()
        if coordinates is None:
          saved = self.position_store.read()
          if saved is not None:
            coordinates = (saved['longitude'], saved['latitude'])
        if (type(coordinates) is not tuple or len(coordinates) != 2 or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in coordinates) or
            not -180 <= coordinates[0] <= 180 or not -90 <= coordinates[1] <= 90):
          return {}
        return {'proximity': f'{coordinates[0]:.6f},{coordinates[1]:.6f}'}
      except (AttributeError, ImportError, OSError, ValueError, TypeError, OverflowError, RuntimeError):
        return {}

  def search_places(self, query, caller, search_id, client_id):
    if not isinstance(client_id, str) or len(client_id) != 36:
      raise ValidationError('Start a new destination search')
    if not isinstance(search_id, str) or len(search_id) != 36:
      raise ValidationError('Start a new destination search')
    try:
      if str(uuid.UUID(search_id, version=4)) != search_id or str(uuid.UUID(client_id, version=4)) != client_id:
        raise ValueError
    except ValueError:
      raise ValidationError('Start a new destination search') from None
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 256:
      raise ValidationError('Enter at least two characters to search')
    current = self.read()
    if not current['token']:
      raise ValidationError('Add your Mapbox access token first')
    key = (caller, search_id)
    with self._lock:
      now = time.monotonic()
      self._searches = {key:value for key,value in self._searches.items()
                        if value['expires'] > now and not (key[0] == caller and value['client_id'] == client_id)}
      if key in self._searches:
        raise ValidationError('Start a new destination search')
      if len(self._searches) >= MAX_SEARCHES or sum(key[0] == caller for key in self._searches) >= 8:
        raise ValidationError('Too many destination searches; try again shortly')
      entry = {'client_id':client_id, 'session':str(uuid.uuid4()), 'expires':now + SEARCH_TTL, 'revision':current['revision'],
               'token_digest':hashlib.sha256(current['token'].encode()).digest(), 'ids':set()}
      self._searches[key] = entry
    try:
      context = self._search_context()
      with self._lock:
        if (self._searches.get(key) is not entry or entry['expires'] <= time.monotonic() or
            self.read()['token'] != current['token']):
          raise ValidationError('Start a new destination search')
      data = response_json(self.session, 'https://api.mapbox.com/search/searchbox/v1/suggest',
                           {'q':query.strip(), 'access_token':current['token'], 'session_token':entry['session'], 'types':'poi', 'limit':8,
                            **context})
      suggestions = data.get('suggestions')
      if not isinstance(suggestions, list):
        raise ValidationError('The map service returned invalid search results')
      results = []
      for item in suggestions[:8]:
        if not isinstance(item, dict):
          continue
        identity, name = item.get('mapbox_id'), item.get('name')
        if (item.get('feature_type') == 'poi' and isinstance(identity, str) and 1 <= len(identity) <= 256 and
            isinstance(name, str) and 1 <= len(name.strip()) <= 256):
          description = item.get('full_address') or item.get('place_formatted') or ''
          description = description.strip()[:512] if isinstance(description, str) else ''
          results.append({'id':identity, 'name':name.strip(), 'description':description, 'searchId':search_id, 'temporary':True})
      with self._lock:
        if (self._searches.get(key) is not entry or entry['expires'] <= time.monotonic() or
            self.read()['token'] != current['token']):
          raise ValidationError('Start a new destination search')
        entry['ids'] = {item['id'] for item in results}
      if results:
        return results
    except ValidationError:
      with self._lock:
        if (self._searches.get(key) is not entry or entry['expires'] <= time.monotonic() or
            self.read()['token'] != current['token']):
          raise ValidationError('Start a new destination search') from None
      self.cancel_search(caller, search_id)
      # Existing permanently storable address search remains available if POI search is unavailable.
      return self.search(query)
    self.cancel_search(caller, search_id)
    return self.search(query)

  def select_place(self, identity, search_id, caller, expected_revision, authorized):
    if not isinstance(identity, str) or not isinstance(search_id, str):
      raise ValidationError('Choose a place from search results')
    with self._lock:
      entry = self._searches.pop((caller, search_id), None)
    current = self.read()
    if (entry is None or entry['expires'] <= time.monotonic() or identity not in entry['ids'] or
        current['revision'] != expected_revision or entry['revision'] != expected_revision or
        entry['token_digest'] != hashlib.sha256(current['token'].encode()).digest()):
      raise ValidationError('Search again before choosing this place')
    if not (authorized() if callable(authorized) else authorized is True):
      raise PermissionError('Navigation changes are not available right now')
    data = response_json(self.session, 'https://api.mapbox.com/search/searchbox/v1/retrieve/' + quote(identity, safe=''),
                         {'access_token':current['token'], 'session_token':entry['session']})
    try:
      feature = data['features'][0]
      properties = feature['properties']
      if properties.get('mapbox_id') != identity:
        raise ValueError
      coordinates = feature['geometry']['coordinates']
      selected = destination({'name':properties.get('name'), 'longitude':coordinates[0], 'latitude':coordinates[1]})
    except (ValueError, TypeError, KeyError, IndexError):
      raise ValidationError('The map service returned an invalid place') from None
    return self._change(lambda doc:doc.update(destination=None, routeChoice=0), expected_revision, authorized, active_destination=selected)

  def _reject_temporary_promotion(self, doc, selected):
    active = self._read_active(doc)
    if active is not None and active['destination']['id'] == selected['id']:
      raise ValidationError('This place can be used for a route but cannot be saved')

  def select(self, value: dict, expected_revision: str, authorized) -> dict:
    if isinstance(value, dict) and value.get('temporary'):
      raise ValidationError('This place can be used for a route but cannot be saved')
    selected = destination(value)
    def update(doc):
      self._reject_temporary_promotion(doc, selected)
      doc.update(destination=selected, routeChoice=0)
    return self._change(update, expected_revision, authorized)

  def clear(self, expected_revision: str, authorized) -> dict:
    with self._lock:
      self._searches.clear()
    return self._change(lambda doc: doc.update(destination=None, routeChoice=0), expected_revision, authorized)

  def favorite(self, value: dict, expected_revision: str, authorized) -> dict:
    if isinstance(value, dict) and value.get('temporary'):
      raise ValidationError('This place can be used for a route but cannot be saved')
    selected = destination(value)
    def update(doc):
      self._reject_temporary_promotion(doc, selected)
      favorites = [row for row in doc['favorites'] if row['id'] != selected['id']]
      if len(favorites) >= 100:
        raise ValidationError('Remove a saved place before adding another')
      doc['favorites'] = favorites + [selected]
    return self._change(update, expected_revision, authorized, preserve_active=True)

  def remove_favorite(self, identity: str, expected_revision: str, authorized) -> dict:
    return self._change(lambda doc: doc.update(favorites=[row for row in doc['favorites'] if row['id'] != identity]),
                        expected_revision, authorized, preserve_active=True)

  def close(self):
    with self._lock:
      if self.runtime_source is not None and hasattr(self.runtime_source, 'close'):
        self.runtime_source.close()
      self.runtime_source = None
