from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import math
import time
import uuid

from openpilot.starpilot.navigation.owner import NavigationOwner, ValidationError
from openpilot.starpilot.navigation.route_engine import MapboxRouteEngine

GPS_MAX_AGE_NS = 2_500_000_000


def location(sm, now_ns: int):
  candidates = []
  for service in ('gpsLocationExternal', 'gpsLocation'):
    stamp, gps = sm.logMonoTime[service], sm[service]
    if (sm.valid[service] and 0 < stamp <= now_ns <= stamp + GPS_MAX_AGE_NS and gps.hasFix and
        all(math.isfinite(v) for v in (gps.latitude, gps.longitude, gps.speed, gps.horizontalAccuracy)) and
        -90 <= gps.latitude <= 90 and -180 <= gps.longitude <= 180 and 0 < gps.horizontalAccuracy <= 25):
      candidates.append((stamp, (gps.longitude, gps.latitude), max(0., gps.speed), gps.bearingDeg if math.isfinite(gps.bearingDeg) else None))
  return max(candidates, default=None, key=lambda row: row[0])


class RouteRuntime:
  def __init__(self, owner: NavigationOwner, engine=None, executor=None):
    self.owner = owner
    self.engine = engine or MapboxRouteEngine(owner.session)
    self.executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix='route')
    self.key = None
    self.route = None
    self.routes = []
    self.future = None
    self.fetch_key = None
    self.retry_after = 0
    self.off_route_since = 0
    self.arrived_since = 0
    self.session = uuid.uuid4().hex

  def update(self, now_ns: int, position, drive_id: int) -> dict:
    if position is not None:
      stamp, coordinates, _, bearing = position
      if 0 < stamp <= now_ns <= stamp + GPS_MAX_AGE_NS:
        self.owner.position_store.record({'longitude': coordinates[0], 'latitude': coordinates[1], 'bearing': bearing})
    if position is None:
      self.owner.position_store.flush()
    settings = self.owner.read_routing()
    selected = settings['destination']
    destination_key = None if selected is None else (selected['id'], selected['longitude'], selected['latitude'])
    key = settings['enabled'], hashlib.sha256(settings['token'].encode()).digest(), destination_key, drive_id
    if key != self.key:
      self.key, self.route = key, None
      self.routes = []
      self.retry_after = self.off_route_since = self.arrived_since = 0
    base_status = ('disabled' if not settings['enabled'] else 'needsKey' if not settings['token'] else
                   'noDestination' if settings['destination'] is None else 'waitingForLocation')
    result = {'sessionId': self.session, 'frameMonoTime': now_ns, 'startedMonoTime': drive_id,
                  'revision': settings['revision'], 'enabled': settings['enabled'], 'status': base_status,
                  'destinationName': (settings['destination'] or {}).get('name', ''), 'instruction': {}, 'nextManeuver': {},
                  'route': [], 'locationMonoTime': 0, 'controlValid': False}
    if self.future is not None and self.future.done():
      try:
        route = self.future.result()
      except (ValidationError, OSError, ValueError):
        route = None
      if self.fetch_key == self.key:
        self.routes = getattr(route, 'alternatives', [route]) if route is not None else []
        self.route = route
        if self.routes:
          self.owner.record_routes(settings['revision'], self.routes)
        self.retry_after = now_ns + 30_000_000_000 if route is None else 0
      self.future = None
    if self.routes:
      if getattr(self, 'routes_revision', None) != settings['revision']:
        self.owner.record_routes(settings['revision'], self.routes)
        self.routes_revision = settings['revision']
      index = settings.get('routeChoice', 0)
      selected_route = self.routes[index] if type(index) is int and 0 <= index < len(self.routes) else self.routes[0]
      if selected_route is not self.route:
        self.off_route_since = self.arrived_since = 0
      self.route = selected_route
    if base_status != 'waitingForLocation' or position is None:
      if self.route is not None and base_status == 'waitingForLocation':
        result['route'] = self.route.preview()
      return result
    stamp, coordinates, speed, bearing = position
    result['locationMonoTime'] = stamp
    if self.route is None:
      result['status'] = 'routeUnavailable' if self.retry_after > now_ns else 'routing'
      if self.future is None and now_ns >= self.retry_after:
        self.fetch_key = self.key
        self.future = self.executor.submit(self.engine.fetch, settings['token'], coordinates, settings['destination'], bearing)
      return result
    progress = self.route.progress(coordinates, speed, bearing)
    self.off_route_since = (self.off_route_since or now_ns) if progress.off_route else 0
    self.arrived_since = (self.arrived_since or now_ns) if progress.arrived else 0
    if self.off_route_since and now_ns - self.off_route_since >= 2_000_000_000:
      self.route = None
      self.routes = []
      result['status'] = 'routing'
      return result
    arrived = self.arrived_since and now_ns - self.arrived_since >= 5_000_000_000
    result.update(status='arrived' if arrived else 'guiding', instruction=progress.instruction,
                  nextManeuver=progress.next_maneuver, route=self.route.preview(),
                  controlValid=bool(drive_id > 0 and not progress.off_route and not progress.arrived and stamp >= drive_id))
    return result


def publish_status(pm, value: dict) -> None:
  from openpilot.cereal import messaging
  message = messaging.new_message('starpilotNavigation', valid=True)
  message.starpilotNavigation = value
  pm.send('starpilotNavigation', message)


def main():
  from openpilot.cereal import messaging
  from openpilot.common.realtime import Ratekeeper
  from openpilot.common.swaglog import cloudlog
  owner = NavigationOwner()
  runtime = RouteRuntime(owner)
  sm = messaging.SubMaster(['deviceState', 'gpsLocationExternal', 'gpsLocation'])
  pm = messaging.PubMaster(['starpilotNavigation'])
  rate = Ratekeeper(1.)
  try:
    while True:
      sm.update(0)
      now = time.monotonic_ns()
      device = sm['deviceState']
      device_stamp = sm.logMonoTime['deviceState']
      drive_id = (device.startedMonoTime if sm.valid['deviceState'] and device.started and
                  0 < device.startedMonoTime <= device_stamp <= now <= device_stamp + 2_000_000_000 else 0)
      try:
        value = runtime.update(now, location(sm, now), drive_id)
        publish_status(pm, value)
      except (ValidationError, OSError, ValueError):
        cloudlog.warning('navigation settings or route unavailable')
      rate.keep_time()
  finally:
    owner.position_store.flush(force=True)


if __name__ == '__main__':
  main()
