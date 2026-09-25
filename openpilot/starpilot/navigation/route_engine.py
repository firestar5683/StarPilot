from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import math

from openpilot.starpilot.navigation.owner import ValidationError, response_json

EARTH_RADIUS = 6371007.2
MAX_POINTS = 20000


def point(value) -> tuple[float, float]:
  if (not isinstance(value, (list, tuple)) or len(value) < 2 or
      any(type(v) not in (int, float) or not math.isfinite(v) for v in value[:2]) or
      not -180 <= value[0] <= 180 or not -90 <= value[1] <= 90):
    raise ValidationError('The route contains invalid coordinates')
  return float(value[0]), float(value[1])


def distance(a, b) -> float:
  lat1, lat2 = math.radians(a[1]), math.radians(b[1])
  h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(math.radians(b[0] - a[0]) / 2) ** 2
  return 2 * EARTH_RADIUS * math.asin(math.sqrt(min(1., max(0., h))))


def project(a, b, p) -> tuple[float, float]:
  latitude_scale = EARTH_RADIUS * math.pi / 180
  longitude_scale = latitude_scale * math.cos(math.radians((a[1] + b[1] + p[1]) / 3))
  x, y = (b[0] - a[0]) * longitude_scale, (b[1] - a[1]) * latitude_scale
  px, py = (p[0] - a[0]) * longitude_scale, (p[1] - a[1]) * latitude_scale
  fraction = min(1., max(0., (px * x + py * y) / (x * x + y * y))) if x * x + y * y > 1e-6 else 0.
  return fraction, math.hypot(px - fraction * x, py - fraction * y)


def number(value, maximum=1e8) -> float:
  if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
    raise ValidationError('The route contains invalid distances')
  return float(value)


def modifier(value) -> str:
  return str(value).replace('slight left', 'slightLeft').replace('slight right', 'slightRight').replace(
    'sharp left', 'sharpLeft').replace('sharp right', 'sharpRight')


@dataclass(frozen=True)
class Step:
  start: float
  end: float
  duration: float
  text: str
  maneuver_type: str
  modifier: str


@dataclass(frozen=True)
class Progress:
  instruction: dict
  next_maneuver: dict
  off_route: bool
  arrived: bool


class NavigationRoute:
  def __init__(self, data: dict):
    try:
      coordinates = data['geometry']['coordinates']
      if not 2 <= len(coordinates) <= MAX_POINTS:
        raise ValidationError('The route is too long')
      self.points = [point(row) for row in coordinates]
      self.cumulative = [0.]
      for a, b in zip(self.points, self.points[1:], strict=False):
        self.cumulative.append(self.cumulative[-1] + distance(a, b))
      steps = data['legs'][0]['steps']
      if not 1 <= len(steps) <= 2048:
        raise ValidationError('The route has too many instructions')
      self.steps = []
      offset = 0.
      for index, step in enumerate(steps):
        end = offset + number(step['distance'])
        maneuver = steps[min(index + 1, len(steps) - 1)]['maneuver']
        banners = step.get('bannerInstructions', [])
        primary = banners[0].get('primary', {}) if banners else {}
        text = str(primary.get('text') or maneuver.get('instruction', ''))[:256]
        self.steps.append(Step(offset, end, number(step['duration']), text,
                               str(primary.get('type') or maneuver['type'])[:40],
                               modifier(primary.get('modifier') or maneuver.get('modifier', 'none'))[:40]))
        offset = end
      self.total_distance = number(data['distance'])
      self.total_duration = number(data['duration'])
      if self.total_distance < 1 or offset < 1:
        raise ValidationError('The route is empty')
      self.starts = [step.start for step in self.steps]
    except (KeyError, TypeError, IndexError, AttributeError):
      raise ValidationError('The map service returned an incomplete route') from None

  def preview(self) -> list[dict]:
    stride = max(1, math.ceil((len(self.points) - 1) / 511))
    points = self.points[::stride]
    if points[-1] != self.points[-1]:
      points.append(self.points[-1])
    return [{'longitude': x, 'latitude': y} for x, y in points]

  def progress(self, position, speed: float, bearing: float | None = None) -> Progress:
    best = (float('inf'), 0., 0)
    for index, (a, b) in enumerate(zip(self.points, self.points[1:], strict=False)):
      fraction, separation = project(a, b, position)
      along = self.cumulative[index] + fraction * (self.cumulative[index + 1] - self.cumulative[index])
      if separation < best[0]:
        best = separation, along, index
    separation, along, segment = best
    # Directions step lengths and geometry lengths can differ slightly.
    along *= self.steps[-1].end / max(self.cumulative[-1], 1.)
    index = min(len(self.steps) - 1, max(0, bisect_right(self.starts, along + .001) - 1))
    step = self.steps[index]
    remaining = max(0., step.end - along)
    duration = step.duration * min(1., remaining / max(step.end - step.start, 1.))
    duration += sum(row.duration for row in self.steps[index + 1:])
    instruction = {'text': step.text, 'maneuverType': step.maneuver_type, 'maneuverModifier': step.modifier,
                       'distanceMeters': remaining, 'remainingDistanceMeters': max(0., self.steps[-1].end - along),
                       'remainingDurationSeconds': duration}
    upcoming = self.steps[min(index + 1, len(self.steps) - 1)]
    next_maneuver = {'maneuverType': upcoming.maneuver_type, 'maneuverModifier': upcoming.modifier,
                         'distanceMeters': max(0., upcoming.end - along)}
    speeds, distances = (0., 5., 10., 20., 40.), (40., 50., 60., 80., 100.)
    bucket = min(3, max(0, bisect_right(speeds, speed) - 1))
    fraction = min(1., max(0., (speed - speeds[bucket]) / (speeds[bucket + 1] - speeds[bucket])))
    threshold = distances[bucket] + fraction * (distances[bucket + 1] - distances[bucket])
    misaligned = False
    if bearing is not None and speed >= 2.5:
      a, b = self.points[segment], self.points[segment + 1]
      lat1, lat2, delta = math.radians(a[1]), math.radians(b[1]), math.radians(b[0] - a[0])
      direction = math.degrees(math.atan2(math.sin(delta) * math.cos(lat2),
                              math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta)))
      misaligned = abs((direction - bearing + 180) % 360 - 180) > 75
    arrived = speed < 2 and distance(position, self.points[-1]) < 40 and instruction['remainingDistanceMeters'] < 40
    return Progress(instruction, next_maneuver, separation > threshold or misaligned, arrived)


class MapboxRouteEngine:
  def __init__(self, session):
    self.session = session

  def fetch(self, token: str, position, destination: dict, bearing: float | None = None) -> NavigationRoute:
    url = ('https://api.mapbox.com/directions/v5/mapbox/driving-traffic/' +
           f'{position[0]},{position[1]};{destination["longitude"]},{destination["latitude"]}')
    params = {'access_token': token, 'geometries': 'geojson', 'steps': 'true', 'overview': 'full', 'banner_instructions': 'true', 'alternatives': 'true'}
    if bearing is not None:
      params['bearings'] = f'{int(bearing % 360)},90;'
    data = response_json(self.session, url, params)
    if data.get('code') != 'Ok' or not data.get('routes'):
      raise ValidationError('No driving route was found')
    routes = [NavigationRoute(row) for row in data['routes'][:3]]
    routes[0].alternatives = routes
    return routes[0]
