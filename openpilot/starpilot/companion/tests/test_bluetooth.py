import base64
import json
from pathlib import Path
import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from openpilot.starpilot.companion.bluetooth import UPSTREAM, pairing_payload, proxy_class, upstream_module


def test_snapshot_matches_pinned_commit_with_starpilot_branding():
  source = json.loads((UPSTREAM.parents[2] / 'SOURCE.json').read_text())
  overrides = source.get('branding_overrides', {})
  assert all('/Resources/Web/assets/images/' in name or name.endswith('/Resources/Web/galaxy-native-manifest.json') for name in overrides)
  for name, expected in source['files'].items():
    expected = overrides.get(name, expected)
    data = (UPSTREAM.parent.parent.parent / name).read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    assert actual == expected, name



def test_pairing_does_not_replace_existing_key(tmp_path):
  path = tmp_path / 'pairing.json'
  first = pairing_payload(path=path)
  assert pairing_payload(path=path) == first
  assert path.stat().st_mode & 0o077 == 0
  assert pairing_payload(True, path=path) != first


def test_adapter_preserves_session_and_supplies_origin():
  seen = []
  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
      pass

    def do_GET(self):
      if self.path == '/api/auth/session':
        self.send_response(200)
        self.send_header('Set-Cookie', 'galaxy_session=local-secret; HttpOnly; Path=/')
        self.end_headers()
        self.wfile.write(b'{"authenticated":true}')
      else:
        self.do_POST()

    def do_POST(self):
      self.rfile.read(int(self.headers.get('Content-Length', 0)))
      seen.append(dict(self.headers))
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
      self.wfile.write(b'{"ok":true}')

  server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  try:
    proxy = proxy_class()(server.server_port)
    for _ in range(2):
      result = proxy.handle({'id': 'one', 'session': 'session', 'method': 'POST', 'path': '/api/settings/preview',
                             'headers': {'Cookie': 'untrusted', 'Origin': 'https://evil.test', 'Content-Type': 'application/json'},
                             'body': base64.b64encode(b'{}').decode()})
      assert result['status'] == 200
      assert 'set-cookie' not in result['headers']
    assert len(proxy.clients) == 1
    assert all(headers['Cookie'] == 'galaxy_session=local-secret' for headers in seen)
    assert all(headers['Origin'] == f'http://127.0.0.1:{server.server_port}' for headers in seen)
    for path in ('/api/companion/bluetooth', '/api/companion/uplink', '/api/recordings/media/a', '/api/companion/app.apk'):
      assert proxy.handle({'id': 'one', 'path': path})['status'] == 501
    assert len(seen) == 2
  finally:
    server.shutdown()
    thread.join()
    server.server_close()


def test_android_wire_vectors():
  # These fixtures are also consumed by BleWireTest on the JVM.
  protocol = upstream_module('protocol')
  root = Path(__file__).parents[1] / 'android/app/src/test/resources/ble'
  key = bytes(range(32))
  for name in ('plain', 'compressed', 'compact'):
    frame = bytes.fromhex((root / f'{name}.hex').read_text())
    expected = json.loads((root / f'{name}.json').read_text())
    assert protocol.open_message(frame[4:], key, 'response') == expected
  frame = bytes.fromhex((root / 'request.hex').read_text())
  assert protocol.open_message(frame[4:], key, 'request') == {'method': 'GET', 'path': '/api/companion/status'}
  with pytest.raises(ValueError):
    protocol.open_message(frame[4:], key, 'response')
