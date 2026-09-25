"""Motion metadata requires a live local session before and after storage I/O."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.sentry_events import SentryEvents
from openpilot.starpilot.galaxy.server import make_server
from openpilot.starpilot.sentry_mode.storage import EventStore


class SentryEventsHTTPTest(unittest.TestCase):
  def test_auth_before_read_and_recheck_after_logout(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory).resolve()
      store = EventStore(root / "events")
      receipt = store.record("alarm", 123, permitted=lambda: True)
      access = GalaxyAccessOwner(root / "access")
      calls = []
      entered, release = threading.Event(), threading.Event()
      release.set()

      class PausedEvents:
        def snapshot(self):
          calls.append(True)
          result = SentryEvents(store).snapshot()
          entered.set()
          release.wait(2)
          return result

      server = make_server(port=0, owner=access, sentry_events=PausedEvents())
      worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
      worker.start()

      def request(path, *, cookie=None, payload=None):
        # Exercise the password-backed forwarded path.
        headers = {"Forwarded": "for=203.0.113.8", **({"Cookie": cookie} if cookie else {})}
        if payload is not None:
          headers.update({"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{server.server_port}"})
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        try:
          connection.request("GET" if payload is None else "POST", path,
                             None if payload is None else json.dumps(payload), headers)
          response = connection.getresponse()
          return response.status, response.read(), dict(response.getheaders())
        finally:
          connection.close()

      try:
        route = "/api/sentry/events"
        self.assertEqual(request(route)[0], 503)
        access.configure("password123", lambda: True)
        self.assertEqual(request(route)[0], 401)
        self.assertEqual(calls, [])
        status, _, headers = request("/api/auth/login", payload={"password": "password123"})
        self.assertEqual(status, 200)
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        status, body, headers = request(route, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        result = json.loads(body)
        self.assertEqual(result["events"][0]["eventId"], receipt.event_id)
        self.assertNotIn(b"sessionId", body)
        self.assertNotIn(b"monoTimeNs", body)
        self.assertNotIn(str(root).encode(), body)

        release.clear()
        entered.clear()
        responses = []
        pending = threading.Thread(target=lambda: responses.append(request(route, cookie=cookie)))
        pending.start()
        try:
          self.assertTrue(entered.wait(1))
          self.assertEqual(request("/api/auth/logout", cookie=cookie, payload={})[0], 200)
        finally:
          release.set()
          pending.join(2)
        self.assertEqual(responses[0][0], 401)
        self.assertNotIn(receipt.event_id.encode(), responses[0][1])
      finally:
        release.set()
        server.shutdown()
        worker.join(2)
        server.server_close()


if __name__ == "__main__":
  unittest.main()
