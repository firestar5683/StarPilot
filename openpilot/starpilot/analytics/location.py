"""Regional dashboard location, resolved without transmitting precise GPS."""
import json
import math


BASE_URL = 'https://nominatim.openstreetmap.org'
MINIMUM_POPULATION = 100_000
SEARCH_RADIUS_DEGREES = 1.45
UNKNOWN = {'city': 'N/A', 'state': 'N/A', 'country': 'N/A'}


def coarse_cell(gps):
  if not isinstance(gps, dict):
    return None
  lat, lon = gps.get('latitude'), gps.get('longitude')
  if (type(lat) not in (int, float) or type(lon) not in (int, float) or
      not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180):
    return None
  return float(round(lat)), float(round(lon))


def _population(candidate):
  try:
    return int(str((candidate.get('extratags') or {}).get('population', '0')).replace(',', '').split(';')[0])
  except (AttributeError, TypeError, ValueError):
    return 0


def _label(value):
  if not isinstance(value, str):
    return 'N/A'
  return ''.join(c for c in value if c.isprintable()).strip()[:96] or 'N/A'


def _point(candidate, state, country):
  address = candidate.get('address') or {}
  if not isinstance(address, dict):
    return None
  try:
    lat, lon = float(candidate['lat']), float(candidate['lon'])
  except (KeyError, TypeError, ValueError):
    return None
  if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
    return None
  return {'latitude': lat, 'longitude': lon,
          'city': _label(address.get('city') or address.get('town') or str(candidate.get('display_name', '')).split(',')[0]),
          'state': _label(state), 'country': _label(country)}


def resolve_region(gps, *, session=None, allowed=lambda: True):
  cell = coarse_cell(gps)
  if cell is None:
    return dict(UNKNOWN)
  latitude, longitude = cell
  fallback = dict(UNKNOWN, latitude=latitude, longitude=longitude)
  if not allowed():
    return fallback
  import requests
  owned = session is None
  session = session or requests.Session()
  session.headers.update({'Accept-Language': 'en', 'User-Agent': 'StarPilot-stats/1.0 (https://github.com/firestar5683/StarPilot)'})

  def get(path, **params):
    if not allowed():
      raise InterruptedError('Statistics are no longer available offroad')
    response = session.get(BASE_URL + path, params={'format': 'jsonv2', 'addressdetails': 1, **params},
                           timeout=(3, 5), stream=True, allow_redirects=False)
    try:
      if response.status_code != 200:
        raise ValueError('Regional lookup was not available')
      body = bytearray()
      for chunk in response.iter_content(chunk_size=4096):
        body.extend(chunk)
        if len(body) > 262144:
          raise ValueError('Regional lookup response exceeds its bound')
      return json.loads(body)
    finally:
      response.close()

  try:
    data = get('/reverse', lat=latitude, lon=longitude, zoom=8, namedetails=0, extratags=0)
    address = data.get('address') if isinstance(data, dict) else None
    if not isinstance(address, dict):
      return fallback
    state = address.get('province') or address.get('region') or address.get('state') or address.get('state_district')
    country = address.get('country')
    fallback.update(state=_label(state), country=_label(country))
    candidates = get('/search', q='city', bounded=1, extratags=1, limit=20,
                     viewbox=f'{longitude - SEARCH_RADIUS_DEGREES},{latitude + SEARCH_RADIUS_DEGREES},' +
                             f'{longitude + SEARCH_RADIUS_DEGREES},{latitude - SEARCH_RADIUS_DEGREES}')
    points = []
    for candidate in candidates[:20] if isinstance(candidates, list) else []:
      if isinstance(candidate, dict) and _population(candidate) >= MINIMUM_POPULATION:
        point = _point(candidate, state, country)
        if point is not None:
          points.append(point)
    if points:
      return min(points, key=lambda p: (p['latitude'] - latitude) ** 2 + (p['longitude'] - longitude) ** 2)
    return fallback
  except (requests.RequestException, OSError, TypeError, ValueError):
    return fallback
  finally:
    if owned:
      session.close()
