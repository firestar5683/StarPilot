import base64
import hashlib
import http.client
import json
import threading

from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
from openpilot.starpilot.galaxy.android_auto_setup import AndroidAutoSetup
from openpilot.starpilot.galaxy.remote import RemotePairing
from openpilot.starpilot.galaxy.server import make_remote_server, make_server
from openpilot.starpilot.galaxy.test_android_auto_http import FakeImport
from openpilot.starpilot.system.android_auto.source_verifier import GalaxySourceVerifier


def test_remote_binary_upload_and_pairing_use_existing_gateway_session(tmp_path):
  access = GalaxyAccessOwner(tmp_path / 'access')
  pairing = RemotePairing(tmp_path / 'pairing')
  assert access.configure('password123', lambda: True)
  slug = pairing.pair(hashlib.sha256(b'password123').hexdigest())
  cookie = 'galaxy_session=' + base64.urlsafe_b64encode(json.dumps({slug: pairing.read()['session']}).encode()).decode().rstrip('=')
  state = {'parked': True}
  job = FakeImport(tmp_path / 'imports')
  setup = AndroidAutoSetup(parked=lambda: state['parked'], enabled=lambda: True,
    session_valid=lambda _identity: True, import_job=job, identity_status=lambda: {'installed': True},
    bluetooth_enabled=lambda: True, install_ready=lambda: True, service_ready=lambda: True)
  class Client:
    source = None
    def call(self, command, **kwargs):
      if command != 'status':
        self.source = kwargs['source']
        assert verifier.valid(self.source)
      return {'status': {'receiver_address': '', 'running': False}} if command == 'status' else {}
  client = Client()
  local = make_server(port=0, owner=access, remote_pairing=pairing, parked=lambda: state['parked'],
                      android_auto_setup=setup, android_auto_client=client)
  remote = make_remote_server(local, port=0)
  verifier = GalaxySourceVerifier(port=local.server_port)
  threads = []
  for server in (local, remote):
    worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    worker.start()
    threads.append(worker)
  def request(path, body=None, *, auth=cookie, origin='https://galaxy.firestar.link', content_type='application/octet-stream'):
    conn = http.client.HTTPConnection('127.0.0.1', remote.server_port, timeout=10)
    headers = {'Host': f'{slug}.devices.local', 'Cookie': auth, 'Origin': origin, 'Content-Type': content_type}
    try:
      conn.request('POST' if body is not None else 'GET', '/' + slug + path, body, headers)
      response = conn.getresponse()
      return response.status, json.loads(response.read())
    finally:
      conn.close()
  try:
    assert request('/api/android-auto/setup', auth='')[0] == 401
    assert request('/api/android-auto/setup')[0] == 200
    assert request('/api/android-auto/upload', b'abc', origin='https://example.com')[0] == 403
    assert request('/api/android-auto/upload', b'abc', content_type='application/json')[0] == 415
    body = b'APK\x00\xff' * (20 * 1024 * 1024 // 5)
    assert request('/api/android-auto/upload', body)[0] == 202
    assert len(job.calls) == 1 and job.calls[0][0] == body
    job.running = False
    assert request('/api/android-auto/pairing', b'{}', content_type='application/json')[0] == 200
    assert client.source and verifier.valid(client.source)
    # Pairing material is daemon-only even through the authenticated remote listener.
    assert request('/api/android-auto/source/' + client.source)[0] == 403
    state['parked'] = False
    assert request('/api/android-auto/upload', b'retry')[0] == 409
    assert job.calls[0][1]() is False
    state['parked'] = True
    pairing.unpair()
    assert not verifier.valid(client.source)
    assert request('/api/android-auto/upload', b'retry')[0] in (401, 403)
    assert len(job.calls) == 1
  finally:
    for server, worker in zip((remote, local), reversed(threads), strict=True):
      server.shutdown()
      worker.join(timeout=2)
      server.server_close()
