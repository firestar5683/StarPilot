"""Notification credentials and sending require a current authenticated session."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.server import make_remote_server, make_server
from openpilot.starpilot.sentry_mode.notifications import NotificationOwner


class NotificationHTTPTests(unittest.TestCase):
  def test_auth_origin_secret_redaction_and_session_change(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory).resolve()
      access = GalaxyAccessOwner(root / 'access')
      access.configure('password123', lambda: True)
      entered, release = threading.Event(), threading.Event()
      release.set()

      class PausedOwner(NotificationOwner):
        def action(self, payload, *, permitted):
          entered.set()
          release.wait(2)
          return super().action(payload, permitted=permitted)

      owner = PausedOwner(root / 'notifications')
      server = make_server(port=0, owner=access, notifications=owner, parked=lambda: True)
      worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
      worker.start()
      def request(path, *, cookie=None, payload=None, origin=None):
        headers = {'Forwarded': 'for=203.0.113.8'}
        if cookie:
          headers['Cookie'] = cookie
        if payload is not None:
          headers.update({'Content-Type': 'application/json', 'Origin': origin or f'http://127.0.0.1:{server.server_port}'})
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
          connection.request('GET' if payload is None else 'POST', path,
                             None if payload is None else json.dumps(payload), headers)
          response = connection.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          connection.close()
      try:
        route = '/api/sentry/notifications'
        self.assertEqual(request(route)[0], 401)
        self.assertEqual(request(route, payload={'action': 'pushKey'})[0], 401)
        status, _, headers = request('/api/auth/login', payload={'password': 'password123'})
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        payload = {'action': 'configure', 'channel': 'ntfy', 'enabled': False,
                   'url': 'https://notify.example/secret-topic', 'token': 'private-token'}
        self.assertEqual(request(route, cookie=cookie, payload=payload, origin='https://elsewhere.invalid')[0], 403)
        self.assertFalse(owner.state['channels']['ntfy']['url'])
        status, body, headers = request(route, cookie=cookie, payload=payload)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn(b'secret-topic', body)
        self.assertNotIn(b'private-token', body)
        self.assertEqual(owner.state['channels']['ntfy']['token'], 'private-token')
        self.assertEqual(request(route, cookie=cookie)[0], 200)

        release.clear()
        entered.clear()
        responses = []
        pending = threading.Thread(target=lambda: responses.append(request(route, cookie=cookie,
                                                                           payload={'action': 'forget', 'channel': 'ntfy'})))
        pending.start()
        try:
          self.assertTrue(entered.wait(1))
          self.assertEqual(request('/api/auth/logout', cookie=cookie, payload={})[0], 200)
        finally:
          release.set()
          pending.join(2)
        self.assertEqual(responses[0][0], 401)
        self.assertEqual(owner.state['channels']['ntfy']['token'], 'private-token')
      finally:
        release.set()
        server.shutdown()
        worker.join(2)
        server.server_close()
      self.assertIsNone(owner.lock_fd)
      self.assertFalse(owner.thread.is_alive())

  def test_remote_listener_shares_sender_and_bind_failure_closes_owner(self):
    class Owner:
      def __init__(self):
        self.starts = 0
        self.closes = 0
      def start(self):
        self.starts += 1
      def close(self):
        self.closes += 1
    owner = Owner()
    server = make_server(port=0, notifications=owner, parked=lambda: True)
    try:
      remote = make_remote_server(server, port=0)
      remote.server_close()
      self.assertEqual((owner.starts, owner.closes), (1, 0))
      blocked = Owner()
      with self.assertRaises(OSError):
        make_server(port=server.server_port, notifications=blocked, parked=lambda: True)
      self.assertEqual((blocked.starts, blocked.closes), (0, 1))
    finally:
      server.server_close()
    self.assertEqual((owner.starts, owner.closes), (1, 1))


if __name__ == '__main__':
  unittest.main()
