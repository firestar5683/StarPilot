"""Map shadow status through the real tracker and authenticated loopback HTTP."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from unittest import mock

from openpilot.cereal import log
from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.map_status import MapStatus, MapUnavailable
from openpilot.starpilot.speed_limits.map_source import decode_event
from openpilot.starpilot.galaxy.server import make_server


def wire(now: int, *, status='matchedLimit', speed=13.0, valid=True, version=2):
  event = log.Event.new_message()
  event.valid = valid
  event.logMonoTime = now
  road = event.init('mapdOut')
  road.sampleVersion = version
  road.roadStatus = status
  road.gpsSource = 'external'
  road.gpsMonoTime = now - 10_000_000
  road.computedMonoTime = now
  road.sourceGeneration = 1
  road.producerSession = 123
  road.speedLimit = speed
  road.tileLoaded = status.startswith('matched')
  road.wayId = 42 if status.startswith('matched') else 0
  road.waySelectionType = 'current' if status.startswith('matched') else 'fail'
  road.wayName = 'Private Road Name'
  return event.to_bytes()


class Queue:
  def __init__(self):
    self.items = []
    self.closed = False

  def receive(self, *, non_blocking):
    assert non_blocking
    return self.items.pop(0) if self.items else None

  def close(self):
    self.closed = True


class MapStatusTest(unittest.TestCase):
  def test_v1_gps_clock_evidence_is_rejected_without_poisoning_v2(self):
    queue = Queue()
    now = 10_100_000_000
    source = MapStatus(queue, clock=lambda: now)
    queue.items.append(wire(now, version=1))
    self.assertEqual(source.snapshot()['state'], 'unknown')
    self.assertIsNone(source.snapshot()['candidateSpeedMps'])
    queue.items.append(wire(now, version=2))
    current = source.snapshot()
    self.assertEqual(current['state'], 'matched_limit_unqualified')
    self.assertEqual(current['candidateSpeedMps'], 13.0)

  def test_slow_decode_expires_before_projection(self):
    queue = Queue()
    now = 10_100_000_000
    source = MapStatus(queue, clock=lambda: now)
    queue.items.append(wire(now))
    def slow_decode(raw):
      nonlocal now
      decoded = decode_event(raw)
      now += 300_000_000
      return decoded
    with mock.patch('openpilot.starpilot.galaxy.map_status.decode_event', side_effect=slow_decode):
      result = source.snapshot()
    self.assertEqual(result['state'], 'stale')
    self.assertIsNone(result['candidateSpeedMps'])
    self.assertIsNone(result['roadStatus'])

  def test_isolated_real_mapdout_ipc(self):
    from openpilot.cereal import messaging
    messaging.set_fake_prefix('galaxy_map_' + uuid.uuid4().hex)
    source = MapStatus(clock=lambda: 10_100_000_000)
    publisher = None
    try:
      publisher = messaging.pub_sock('mapdOut')
      self.assertEqual(source.snapshot()['state'], 'unknown')  # opens the actual subscriber
      publisher.send(wire(10_100_000_000))
      self.assertEqual(source.snapshot()['state'], 'matched_limit_unqualified')
    finally:
      source.close()
      del publisher
      messaging.delete_fake_prefix()

  def test_bounded_real_wire_tracker_and_expiry(self):
    queue = Queue()
    now = 10_100_000_000
    source = MapStatus(queue, clock=lambda: now)
    self.assertEqual(source.snapshot()['state'], 'unknown')
    queue.items.append(wire(10_100_000_000))
    result = source.snapshot()
    self.assertEqual(result['state'], 'matched_limit_unqualified')
    self.assertEqual(result['candidateSpeedMps'], 13.0)
    self.assertEqual(result['roadStatus'], 'matchedLimit')
    self.assertEqual(result['gpsSource'], 'external')
    self.assertEqual(result['gpsAgeMs'], 10)
    self.assertEqual(result['computedAgeMs'], 0)
    self.assertTrue(result['tileLoaded'])
    self.assertNotIn('Private Road Name', json.dumps(result))
    for status in ('noCoverage', 'noMatch'):
      now += 1_000_000
      queue.items.append(wire(now, status=status, speed=0, valid=False))
      loss = source.snapshot()
      self.assertEqual((loss['state'], loss['roadStatus'], loss['gpsSource'], loss['tileLoaded']),
                       ('loss', status, 'external', False))
    now += 300_000_000
    self.assertEqual(source.snapshot()['state'], 'stale')
    queue.items.append(wire(now, status='noGps', speed=0, valid=False))
    self.assertEqual(source.snapshot()['state'], 'loss')  # noGps may retain the last source timestamp
    queue.items.extend([b'bad'] * source.MAX_DRAIN)
    with self.assertRaises(MapUnavailable):
      source.snapshot()
    source.close()
    self.assertTrue(queue.closed)

  def test_auth_before_sampling_and_recheck_after_revoke(self):
    with tempfile.TemporaryDirectory() as temporary:
      owner = GalaxyAccessOwner(Path(temporary) / 'access')
      class Paused:
        def __init__(self):
          self.calls = 0
          self.entered = threading.Event()
          self.release = threading.Event()
        def snapshot(self):
          self.calls += 1
          self.entered.set()
          self.release.wait(2)
          return {'schemaVersion': 1, 'qualification': 'unqualified', 'state': 'unknown', 'candidateSpeedMps': None,
                  'roadStatus': None, 'gpsSource': None, 'gpsAgeMs': None, 'eventAgeMs': None,
                  'computedAgeMs': None,
                  'tileLoaded': None, 'producerRestarts': 0, 'sourceSwitches': 0}
        def close(self):
          pass
      source = Paused()
      server = make_server(port=0, owner=owner, maps=source)
      thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
      thread.start()
      def request(path, method='GET', body=None, headers=None):
        # Exercise the password-backed forwarded path.
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=2)
        try:
          connection.request(method, path, body=body, headers={'Forwarded': 'for=203.0.113.8', **(headers or {})})
          response = connection.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          connection.close()
      try:
        self.assertEqual(request('/api/maps/status')[0], 503)
        owner.configure('password123', lambda: True)
        self.assertEqual(request('/api/maps/status')[0], 401)
        self.assertEqual(source.calls, 0)
        origin = f'http://127.0.0.1:{server.server_port}'
        status, _, headers = request('/api/auth/login', 'POST', json.dumps({'password': 'password123'}),
                                     {'Content-Type': 'application/json', 'Origin': origin})
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        source.release.set()
        status, body, headers = request('/api/maps/status', headers={'Cookie': cookie})
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(json.loads(body)['qualification'], 'unqualified')
        self.assertNotIn(b'Private Road Name', body)
        self.assertEqual(request('/api/maps/status', headers={'Cookie': cookie, 'Host': 'other.example'})[0], 403)
        source.release.clear()
        source.entered.clear()
        result = []
        worker = threading.Thread(target=lambda: result.append(request('/api/maps/status', headers={'Cookie': cookie})))
        worker.start()
        self.assertTrue(source.entered.wait(1))
        self.assertEqual(request('/api/auth/logout', 'POST', '{}', {'Content-Type': 'application/json',
                                                                  'Origin': origin, 'Cookie': cookie})[0], 200)
        source.release.set()
        worker.join(2)
        self.assertEqual(result[0][0], 401)
        self.assertNotIn(b'candidateSpeedMps', result[0][1])
      finally:
        source.release.set()
        server.shutdown()
        thread.join(2)
        server.server_close()
