"""Persistent read connections must never reuse an unread body or partial response."""
from typing import Any

import http.client
from contextlib import closing
import os
import socket
import threading
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from openpilot.starpilot.galaxy.http_server import _LocalHTTPHandler, _LocalHTTPServer
from openpilot.starpilot.galaxy.replay_http import ReplayHTTP
from openpilot.starpilot.galaxy.recording_http import send_recording


@pytest.fixture
def server(tmp_path):
  session, client = '1' * 32, '2' * 32
  directory = tmp_path / 'sessions' / session / 'media' / '1'
  directory.mkdir(parents=True)
  media = directory / 'init.mp4'
  media.write_bytes(b'x' * (65536 + 5))
  state: dict[str, Any] = {'requests': [], 'chunks': 0, 'revoke_after': None, 'expire_session': False, 'expired': False,
           'recording_checks': 0, 'change_recording': False}

  def owner(payload):
    if payload['op'] == 'media':
      result = {'available': True, 'epoch': 1, 'sequence': 0, 'length': media.stat().st_size, 'mediaPath': str(media)}
    else:
      state['chunks'] += 1
      result = {'owned': state['revoke_after'] is None or state['chunks'] <= state['revoke_after'],
                'offroad': True, 'mediaReady': True, 'state': 'playing', 'sessionId': session, 'epoch': 1}
      state['expired'] = state['expire_session'] and not result['owned']
    return {'ok': True, 'result': result}

  api = ReplayHTTP(owner, tmp_path)

  class Handler(_LocalHTTPHandler):
    def settings_session(self):
      return None if state['expired'] else ('test', b'generation')

    def require_session(self):
      return True

    def authenticated(self):
      return True

    def do_GET(self):
      state['requests'].append(self.path)
      path = urlsplit(self.path).path
      if path == '/api/replay/media':
        api.get(self, path)
      elif path == '/recording':
        def current():
          state['recording_checks'] += 1
          return not state['change_recording'] or state['recording_checks'] <= 2
        fd = os.open(media, os.O_RDONLY)
        send_recording(self, SimpleNamespace(size=media.stat().st_size, video_fd=fd,
                                            source=SimpleNamespace(current=current), close=lambda: os.close(fd)))
      else:
        self.respond(304 if path == '/unchanged' else 200, b'' if path == '/unchanged' else b'ok')

    do_HEAD = do_GET

    def do_POST(self):
      state['requests'].append(self.path)
      self.json(413, {'error': 'Rejected before reading the body'})

  with _LocalHTTPServer(('127.0.0.1', 0), Handler) as http:
    thread = threading.Thread(target=http.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
      yield http, state, f'/api/replay/media?sessionId={session}&clientId={client}&epoch=1&sequence=0'
    finally:
      http.shutdown()
      thread.join(2)


def test_get_head_and_media_reuse_one_connection(server):
  running, _, media = server
  with closing(http.client.HTTPConnection('127.0.0.1', running.server_port, timeout=2)) as connection:
    connection.request('GET', media)
    response = connection.getresponse()
    assert response.version == 11 and response.read() == b'x' * (65536 + 5)
    opened = connection.sock
    assert opened is not None
    for method, path in [('HEAD', media), ('GET', '/recording'), ('GET', '/unchanged'), ('GET', '/next')]:
      connection.request(method, path)
      response = connection.getresponse()
      assert response.read() == (b'x' * (65536 + 5) if path == '/recording' else b'ok' if path == '/next' else b'')
      if path == '/unchanged':
        assert response.getheader('Content-Length') is None
      assert connection.sock is opened


@pytest.mark.parametrize('method,headers,body', [
  ('POST', 'Content-Length: 4', b'junk'),
  ('GET', 'Content-Length: 4', b'junk'),
  ('GET', 'Transfer-Encoding: chunked', b'0\r\n\r\n'),
])
def test_unread_request_body_closes_connection(server, method, headers, body):
  running, state, _ = server
  with socket.create_connection(('127.0.0.1', running.server_port), timeout=2) as connection:
    connection.sendall(f'{method} /first HTTP/1.1\r\nHost: localhost\r\n{headers}\r\n\r\n'.encode() + body +
                       b'GET /second HTTP/1.1\r\nHost: localhost\r\n\r\n')
    response = http.client.HTTPResponse(connection)
    response.begin()
    response.read()
    assert response.getheader('Connection') == 'close'
    assert state['requests'] == ['/first']


@pytest.mark.parametrize('allowed_chunks', [0, 1])
@pytest.mark.parametrize('expire_session', [False, True])
def test_revoked_media_closes_partial_response(server, allowed_chunks, expire_session):
  running, state, media = server
  state['revoke_after'] = allowed_chunks
  state['expire_session'] = expire_session
  with closing(http.client.HTTPConnection('127.0.0.1', running.server_port, timeout=2)) as connection:
    connection.request('GET', media)
    response = connection.getresponse()
    assert response.status == 200
    with pytest.raises(http.client.IncompleteRead) as receipt:
      response.read()
    assert receipt.value.partial == b'x' * (65536 * allowed_chunks)


def test_changed_recording_closes_partial_response(server):
  running, state, _ = server
  state['change_recording'] = True
  with closing(http.client.HTTPConnection('127.0.0.1', running.server_port, timeout=2)) as connection:
    connection.request('GET', '/recording')
    response = connection.getresponse()
    with pytest.raises(http.client.IncompleteRead) as receipt:
      response.read()
    assert receipt.value.partial == b'x' * 65536


def test_idle_persistent_connections_release_capacity(server):
  running, _, _ = server
  running.REQUEST_TIMEOUT = .15
  held = []
  try:
    for _ in range(running.MAX_CONNECTIONS):
      connection = http.client.HTTPConnection('127.0.0.1', running.server_port, timeout=2)
      held.append(connection)
      connection.request('GET', '/')
      assert connection.getresponse().read() == b'ok'
    with closing(http.client.HTTPConnection('127.0.0.1', running.server_port, timeout=2)) as waiting:
      waiting.request('GET', '/after-idle')
      assert waiting.getresponse().read() == b'ok'
  finally:
    for connection in held:
      connection.close()
