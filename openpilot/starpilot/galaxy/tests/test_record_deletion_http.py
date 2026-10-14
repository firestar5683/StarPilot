"""Authenticated real HTTP cleanup and destructive confirmation."""
import http.client
import json
import threading

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.crash_reports import CrashReports
from openpilot.starpilot.galaxy.sentry_events import SentryEvents
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.sentry_mode.storage import EventStore


def test_record_deletion_auth_confirmation_refresh_and_idempotence(tmp_path):
  store = EventStore(tmp_path / 'events')
  receipt = store.record('warning', 1, permitted=lambda: True, images={'wide': b'\xff\xd8abc\xff\xd9'})
  crash = tmp_path / 'crash'
  crash.mkdir()
  (crash / 'native-crash').write_bytes(b'broken\xffreport')
  reports = CrashReports(crash)
  token = reports.list()['reports'][0]['id']
  access = GalaxyAccessOwner(tmp_path / 'access')
  access.configure('password123', lambda: True)
  server = make_server(port=0, owner=access, sentry_events=SentryEvents(store), crashes=reports, parked=lambda: True)
  worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
  worker.start()

  def request(path, payload, cookie=None, origin=None):
    headers = {'Forwarded': 'for=203.0.113.8', 'Content-Type': 'application/json',
               'Origin': origin or f'http://127.0.0.1:{server.server_port}'}
    if cookie:
      headers['Cookie'] = cookie
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
    try:
      connection.request('POST', path, json.dumps(payload), headers)
      response = connection.getresponse()
      return response.status, json.loads(response.read()), dict(response.getheaders())
    finally:
      connection.close()

  try:
    for route in ('/api/sentry/events/delete', '/api/crash-reports/delete'):
      assert request(route, {'all': True, 'confirmed': True})[0] == 401
    assert (store.root / (receipt.event_id + '.json')).exists() and (crash / 'native-crash').exists()
    status, _, headers = request('/api/auth/login', {'password': 'password123'})
    assert status == 200
    cookie = headers['Set-Cookie'].split(';', 1)[0]
    for route in ('/api/sentry/events/delete', '/api/crash-reports/delete'):
      assert request(route, {'all': True}, cookie)[0] == 400
      assert request(route, {'all': True, 'confirmed': False}, cookie)[0] == 400
      assert request(route, {'all': True, 'confirmed': True}, cookie, 'https://outside.invalid')[0] == 403
    assert request('/api/sentry/events/delete', {'eventId': '../crash'}, cookie)[0] == 400
    status, data, _ = request('/api/sentry/events/delete', {'eventId': receipt.event_id}, cookie)
    assert status == 200 and data['events'] == [] and data['storageBytes'] == 0 and data['more'] is False
    assert request('/api/sentry/events/delete', {'eventId': receipt.event_id}, cookie)[0] == 200
    status, data, _ = request('/api/crash-reports/delete', {'id': token}, cookie)
    assert status == 200 and data['reports'] == [] and data['reportCount'] == 0 and data['storageBytes'] == 0
    assert request('/api/crash-reports/delete', {'id': token}, cookie)[0] == 200
    fresh = store.record('alarm', 2, permitted=lambda: True)
    (crash / 'new-crash').write_text('new collection')
    for route in ('/api/sentry/events/delete', '/api/crash-reports/delete'):
      status, data, _ = request(route, {'all': True, 'confirmed': True}, cookie)
      assert status == 200 and data['storageBytes'] == 0 and data['more'] is False
    assert not (store.root / (fresh.event_id + '.json')).exists() and list(crash.iterdir()) == [crash / '.lock']
    assert request('/api/auth/logout', {}, cookie)[0] == 200
    assert request('/api/crash-reports/delete', {'all': True, 'confirmed': True}, cookie)[0] == 401
  finally:
    server.shutdown()
    server.server_close()
    worker.join(2)
