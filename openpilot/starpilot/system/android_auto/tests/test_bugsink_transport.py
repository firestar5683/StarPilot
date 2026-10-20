import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from openpilot.starpilot.system.android_auto.bugsink_transport import Sender, configured_sender


@pytest.fixture
def endpoint():
  received = []
  status = [200]

  class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
      event = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
      received.append((self.path, dict(self.headers), event))
      self.send_response(status[0])
      self.end_headers()
      self.wfile.write(json.dumps({'id': event['event_id']}).encode())

    def log_message(self, format, *args):  # noqa: A002 - Match BaseHTTPRequestHandler.
      pass

  server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
  thread = threading.Thread(target=server.serve_forever)
  thread.start()
  try:
    yield f'http://testkey@127.0.0.1:{server.server_port}/1', received, status
  finally:
    server.shutdown()
    thread.join()
    server.server_close()


def test_server_acknowledgement_and_stable_retry_id(endpoint):
  dsn, received, status = endpoint
  send = Sender(dsn, metadata={'device_id': 'test-device', 'commit': 'test-commit'})
  event = {'message': 'Android Auto failed at joining_wifi', 'contexts': {'diagnosis': {'password': 'never-send'}}}
  status[0] = 503
  assert not send(**event)
  status[0] = 200
  assert send(**event)
  assert len(received) == 2
  assert received[0][2]['event_id'] == received[1][2]['event_id']
  assert received[1][0] == '/api/1/store/'
  assert received[1][2]['user']['id'] == 'test-device'
  assert 'never-send' not in json.dumps(received)


def test_default_project_unless_disabled_or_overridden(tmp_path):
  path = tmp_path / 'bugsink.json'
  sender = configured_sender(path)
  assert sender.endpoint == 'https://bugsink.firestar.link/api/3/store/'
  path.write_text(json.dumps({'dsn': 'https://key@example.com/7'}))
  assert configured_sender(path).endpoint == 'https://example.com/api/7/store/'
  path.write_text(json.dumps({'enabled': False}))
  assert configured_sender(path) is None


def test_reporting_stops_if_projection_starts(endpoint):
  dsn, received, _ = endpoint
  assert not Sender(dsn, active=lambda: False)(message='test')
  assert received == []


@pytest.mark.parametrize('dsn', ['ftp://key@example.com/1', 'https://example.com/1', 'http://key@example.com/1',
                                  'https://key@example.com/no-project', 'https://key@example.com/1?secret=true'])
def test_invalid_or_insecure_remote_destinations_are_rejected(dsn):
  with pytest.raises(ValueError):
    Sender(dsn)


def test_session_release_is_not_overwritten_by_uploading_build(endpoint):
  dsn, received, _ = endpoint
  sender = Sender(dsn, metadata={"device_id": "device", "commit": "uploader-build", "branch": "uploader-branch"})
  assert sender(message="Historical failure", tags={"commit": "session-build", "branch": "session-branch"})
  event = received[-1][2]
  assert event["release"] == event["tags"]["commit"] == "session-build"
  assert event["tags"]["reporter.commit"] == "uploader-build"
  assert event["tags"]["branch"] == "session-branch"
  assert sender(message="Legacy failure", tags={"commit": "unknown"})
  assert received[-1][2]["release"] == "unknown"
