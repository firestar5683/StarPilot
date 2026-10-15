"""Browser sessions cannot borrow replay authority or arbitrary media paths."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_server


SESSION = '1' * 32
CLIENT = '2' * 32
OWNER = '3' * 32


class ReplayHTTPTest(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.root = Path(self.temp.name)
    self.media = self.root / 'sessions' / SESSION / 'media' / '1'
    self.media.mkdir(parents=True)
    (self.media / 'init.mp4').write_bytes(b'initialization')
    for sequence in range(1, 10):
      (self.media / f'{sequence}.m4s').write_bytes(f'fragment-{sequence}'.encode())
    self.access = GalaxyAccessOwner(self.root / 'access')
    self.access.configure('password123', lambda: True)
    self.calls = []
    self.entered, self.release = threading.Event(), threading.Event()
    self.release.set()
    self.path_override = None
    self.evicted = False
    self.media_ready = True
    self.replay_state = 'playing'

    def replay(payload):
      self.calls.append(payload)
      if payload['op'] == 'media':
        if self.evicted:
          return {'ok': True, 'result': {'available': False, 'code': 'media_evicted'}}
        self.entered.set()
        self.release.wait(2)
        sequence = payload['sequence']
        if sequence > 9:
          return {'ok': True, 'result': {'available': False}}
        rows = []
        for selected in range(sequence, min(10, sequence + (1 if sequence == 0 else payload.get('count', 1)))):
          path = self.media / ('init.mp4' if selected == 0 else f'{selected}.m4s')
          rows.append({'mediaPath': str(self.path_override or path), 'length': path.stat().st_size,
                       'epoch': payload['epoch'], 'sequence': selected})
        result = rows[0] if sequence == 0 or payload.get('count', 1) == 1 else {'fragments': rows}
        return {'ok': True, 'result': result}
      return {'ok': True, 'result': {'schemaVersion': 1, 'ownerId': OWNER, 'sessionId': SESSION,
                                    'state': self.replay_state if self.media_ready else 'seeking', 'mediaReady': self.media_ready,
                                    'epoch': 1, 'offroad': True, 'owned': True, 'framePath': '/private/frame'}}

    self.server = make_server(port=0, owner=self.access, parked=lambda: True, replay_client=replay, replay_root=self.root)
    self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    self.thread.start()

  def tearDown(self):
    self.release.set()
    self.server.shutdown()
    self.thread.join(2)
    self.server.server_close()
    self.temp.cleanup()

  def request(self, path, payload=None, cookie=None, origin=True):
    headers = {'Forwarded': 'for=203.0.113.8'}
    if cookie:
      headers['Cookie'] = cookie
    if payload is not None:
      headers['Content-Type'] = 'application/json'
      if origin:
        headers['Origin'] = f'http://127.0.0.1:{self.server.server_port}'
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
    try:
      connection.request('GET' if payload is None else 'POST', path, None if payload is None else json.dumps(payload), headers)
      response = connection.getresponse()
      return response.status, response.read(), dict(response.getheaders())
    finally:
      connection.close()

  def login(self):
    return self.request('/api/auth/login', {'password': 'password123'})[2]['Set-Cookie'].split(';', 1)[0]

  def test_auth_origin_and_actor_binding(self):
    self.assertEqual(self.request('/api/replay/catalog')[0], 401)
    self.assertEqual(self.calls, [])
    first, second = self.login(), self.login()
    self.assertEqual(self.request('/api/replay/start', {'clientId': CLIENT}, first, origin=False)[0], 403)
    payload = {'clientId': CLIENT, 'routeId': '00000042--abcdef1234', 'target': 'web', 'requestId': '4' * 32,
               'expectedOwnerId': OWNER}
    status, body, _ = self.request('/api/replay/start', payload, first)
    self.assertEqual(status, 200)
    self.assertNotIn(b'/private/frame', body)
    first_actor = self.calls[-1]['clientId']
    self.assertNotEqual(first_actor, CLIENT)
    self.assertEqual(self.request('/api/replay/status?clientId=' + CLIENT, cookie=first)[0], 200)
    self.assertEqual(self.calls[-1]['clientId'], first_actor)
    self.request('/api/replay/start', payload, second)
    self.assertNotEqual(self.calls[-1]['clientId'], first_actor)
    count = len(self.calls)
    self.assertEqual(self.request('/api/replay/start', {**payload, 'target': 'native'}, first)[0], 400)
    self.assertEqual(self.request('/api/replay/start', {key: value for key, value in payload.items() if key != 'target'}, first)[0], 400)
    self.assertEqual(len(self.calls), count, 'Galaxy cannot ask the owner for a native viewer')
    self.assertEqual(self.request('/api/replay/start', {**payload, 'op': 'shell'}, first)[0], 400)
    self.assertEqual(self.request('/api/replay/media?sessionId=../x&clientId=' + CLIENT + '&epoch=1&sequence=0', cookie=first)[0], 400)

  def test_selected_segment_reaches_shared_owner(self):
    cookie = self.login()
    for segment in (0, 2):
      payload = {'clientId': CLIENT, 'routeId': '00000042--abcdef1234', 'target': 'web',
                 'requestId': '4' * 32, 'expectedOwnerId': OWNER, 'segment': segment}
      self.assertEqual(self.request('/api/replay/start', payload, cookie)[0], 200)
      self.assertEqual(self.calls[-1]['segment'], segment)
      self.assertEqual(self.calls[-1]['target'], 'web')

  def test_media_batch_budget_and_no_path_disclosure(self):
    cookie = self.login()
    path = f'/api/replay/media?sessionId={SESSION}&clientId={CLIENT}&epoch=1&sequence='
    status, body, headers = self.request(path + '0', cookie=cookie)
    self.assertEqual((status, body), (200, b'initialization'))
    self.assertEqual(headers['Content-Type'], 'video/mp4')
    self.assertEqual(headers['X-Replay-Epoch'], '1')
    self.assertEqual(headers['Cache-Control'], 'no-store')
    self.calls.clear()
    status, body, headers = self.request(path + '1', cookie=cookie)
    self.assertEqual([call.get('count', 1) for call in self.calls if call['op'] == 'media'], [8, 1])
    self.assertEqual(status, 200)
    self.assertEqual(body, b''.join(f'fragment-{number}'.encode() for number in range(1, 9)))
    self.assertEqual(headers['X-Replay-Next-Sequence'], '9')
    self.assertEqual(self.request(path + '10', cookie=cookie)[0], 202)
    self.path_override = self.root / 'access' / 'secret'
    status, body, _ = self.request(path + '0', cookie=cookie)
    self.assertEqual(status, 503)
    self.assertNotIn(str(self.path_override).encode(), body)

  def test_buffering_keeps_published_media_and_waits_for_missing_fragment(self):
    self.replay_state = 'buffering'
    cookie = self.login()
    path = f'/api/replay/media?sessionId={SESSION}&clientId={CLIENT}&epoch=1&sequence='
    status, body, _ = self.request(path + '1', cookie=cookie)
    self.assertEqual(status, 200)
    self.assertEqual(body, b''.join(f'fragment-{number}'.encode() for number in range(1, 9)))
    self.assertEqual(self.request(path + '10', cookie=cookie)[0], 202)

  def test_logout_during_slow_media_withholds_bytes(self):
    cookie = self.login()
    self.release.clear()
    responses = []
    path = f'/api/replay/media?sessionId={SESSION}&clientId={CLIENT}&epoch=1&sequence=0'
    pending = threading.Thread(target=lambda: responses.append(self.request(path, cookie=cookie)))
    pending.start()
    self.assertTrue(self.entered.wait(1))
    self.assertEqual(self.request('/api/auth/logout', {}, cookie)[0], 200)
    self.release.set()
    pending.join(2)
    self.assertEqual(responses[0][0], 401)
    self.assertNotIn(b'initialization', responses[0][1])

  def test_eviction_is_a_conflict_not_endless_pending(self):
    self.evicted = True
    status, body, _ = self.request(f'/api/replay/media?sessionId={SESSION}&clientId={CLIENT}&epoch=1&sequence=1', cookie=self.login())
    self.assertEqual(status, 409)
    self.assertEqual(json.loads(body)['code'], 'media_evicted')

  def test_symlink_media_is_rejected(self):
    path = self.media / 'init.mp4'
    path.unlink()
    outside = self.root / 'outside'
    outside.write_bytes(b'initialization')
    path.symlink_to(outside)
    status, body, _ = self.request(f'/api/replay/media?sessionId={SESSION}&clientId={CLIENT}&epoch=1&sequence=0', cookie=self.login())
    self.assertEqual(status, 409)
    self.assertNotIn(b'initialization', body)

  def test_accepted_seek_with_same_epoch_withholds_media(self):
    cookie = self.login()
    self.media_ready = False
    path = f'/api/replay/media?sessionId={SESSION}&clientId={CLIENT}&epoch=1&sequence=0'
    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
    try:
      connection.request('GET', path, headers={'Cookie': cookie})
      response = connection.getresponse()
      self.assertEqual(response.status, 200)
      with self.assertRaises(http.client.IncompleteRead) as receipt:
        response.read()
      self.assertEqual(receipt.exception.partial, b'')
    finally:
      connection.close()
