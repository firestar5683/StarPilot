"""Private credentials, actual HTTP contracts, durable retries and RFC push crypto."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import struct
import threading
from types import SimpleNamespace
from urllib.parse import parse_qs

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import pytest

from openpilot.starpilot.sentry_mode.notifications import NotificationOwner, NotificationUnavailable, CHANNELS
from openpilot.starpilot.sentry_mode import web_push


def store(events=()):
  return SimpleNamespace(snapshot=lambda: {'events': list(events)})


def configure(owner, channel, url='https://example.test/private-secret', enabled=True):
  return owner.action({'action': 'configure', 'channel': channel, 'enabled': enabled, 'url': url, 'token': 'private-token'})


def test_private_configuration_redaction_validation_and_exclusive_owner(tmp_path):
  owner = NotificationOwner(tmp_path / 'notifications', store())
  try:
    snapshot = configure(owner, 'ntfy')
    assert snapshot['channels']['ntfy']['enabled'] and snapshot['channels']['ntfy']['configured']
    assert 'private-secret' not in json.dumps(snapshot) and 'private-token' not in json.dumps(snapshot)
    assert (tmp_path / 'notifications/state.json').stat().st_mode & 0o777 == 0o600
    duplicate = NotificationOwner(tmp_path / 'notifications', store())
    with pytest.raises(NotificationUnavailable):
      duplicate.snapshot()
    duplicate.close()
    for url in ('http://example.test/a', 'https://u:p@example.test', 'https://example.test/#x', 'https://example.test/\n'):
      with pytest.raises(ValueError):
        configure(owner, 'webhook', url)
    before = owner.snapshot()
    with pytest.raises(PermissionError):
      configure_kwargs = {'action': 'forget', 'channel': 'ntfy'}
      owner.action(configure_kwargs, permitted=lambda: False)
    assert owner.snapshot() == before
  finally:
    owner.close()


def test_event_scan_durable_dedupe_retry_and_disable(tmp_path):
  clock = [100.]
  calls = []
  outcomes = [503, 202]
  events = []
  def transport(*args):
    calls.append(args)
    return outcomes.pop(0)
  root = tmp_path / 'notifications'
  owner = NotificationOwner(root, store(events), clock=lambda: clock[0], transport=transport)
  configure(owner, 'webhook')
  events.append({'eventId': 'a'*32, 'kind': 'alarm', 'wallTimeNs': int(101e9)})
  clock[0] = 101.
  owner.tick()
  assert len(calls) == 1 and owner.snapshot()['channels']['webhook']['lastError'] == 'http'
  owner.close()
  owner = NotificationOwner(root, store(events), clock=lambda: clock[0], transport=transport)
  owner.tick()
  assert len(calls) == 1
  clock[0] = 132.
  owner.tick()
  assert len(calls) == 2 and calls[0][4] == calls[1][4]
  assert owner.snapshot()['channels']['webhook']['lastState'] == 'sent'
  owner.tick()
  assert len(calls) == 2
  configure(owner, 'webhook', enabled=False)
  events.append({'eventId': 'b'*32, 'kind': 'warning', 'wallTimeNs': int(133e9)})
  clock[0] = 133.
  owner.tick()
  assert len(calls) == 2
  owner.close()


def test_real_http_contracts_and_independent_channels(tmp_path):
  received = []
  class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
      received.append((self.path, self.headers, self.rfile.read(int(self.headers['Content-Length']))))
      self.send_response(200)
      self.send_header('Content-Length', '100000000')
      self.end_headers()
      self.wfile.write(b'x')  # Sender must read status only, not this unbounded/incomplete body.
    def log_message(self, *args):
      pass
  server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  owner = NotificationOwner(tmp_path / 'notifications', store(), allow_http=True)
  try:
    for name in ('discord', 'webhook', 'ntfy'):
      configure(owner, name, f'http://127.0.0.1:{server.server_port}/{name}')
      owner.action({'action': 'test', 'channel': name})
    owner.action({'action': 'pushKey'})
    receiver = ec.generate_private_key(ec.SECP256R1())
    owner.action({'action': 'subscribe', 'subscription': {'endpoint': f'http://127.0.0.1:{server.server_port}/push',
                  'keys': {'p256dh': web_push.b64(web_push.public(receiver)), 'auth': web_push.b64(b'0123456789abcdef')}}})
    owner.action({'action': 'configure', 'channel': 'webPush', 'enabled': True, 'url': '', 'token': ''})
    owner.action({'action': 'test', 'channel': 'webPush'})
    for _ in range(4):
      owner.tick()
    assert len(received) == 4
    paths = {path: (headers, body) for path, headers, body in received}
    assert json.loads(paths['/discord'][1])['content'].startswith('StarPilot Sentry Mode:')
    assert json.loads(parse_qs(paths['/webhook'][1].decode())['event'][0])['kind'] == 'test'
    assert paths['/ntfy'][0]['Priority'] == 'urgent'
    assert paths['/ntfy'][1].startswith(b'This is a test')
    for path, (headers, _) in paths.items():
      assert len(headers['Idempotency-Key']) == 64
      if path != '/push':
        assert headers['Authorization'] == 'Bearer private-token'
    assert paths['/push'][0]['Authorization'].startswith('vapid t=')
    assert paths['/push'][0]['Content-Encoding'] == 'aes128gcm'
    assert len(paths['/push'][1]) > 100 and b'This is a test' not in paths['/push'][1]
    assert all(owner.snapshot()['channels'][name]['lastState'] == 'sent' for name in CHANNELS)
  finally:
    owner.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_push_encrypts_decryptable_payload_and_valid_signed_vapid():
  receiver = ec.generate_private_key(ec.SECP256R1())
  auth = b'0123456789abcdef'
  subscription = {'endpoint': 'https://push.example.test/private', 'keys': {'p256dh': web_push.b64(web_push.public(receiver)), 'auth': web_push.b64(auth)}}
  pem = web_push.new_key()
  message = {'eventId': 'a'*32, 'body': 'Parked motion detected'}
  body, headers = web_push.request(subscription, message, pem, now=100)
  salt, rs, key_length = body[:16], struct.unpack('!I', body[16:20])[0], body[20]
  assert rs == 4096 and key_length == 65
  sender_public = body[21:86]
  shared = receiver.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), sender_public))
  ikm = HKDF(algorithm=hashes.SHA256(), length=32, salt=auth, info=b'WebPush: info\x00' + web_push.public(receiver) + sender_public).derive(shared)
  cek = HKDF(algorithm=hashes.SHA256(), length=16, salt=salt, info=b'Content-Encoding: aes128gcm\x00').derive(ikm)
  nonce = HKDF(algorithm=hashes.SHA256(), length=12, salt=salt, info=b'Content-Encoding: nonce\x00').derive(ikm)
  plaintext = AESGCM(cek).decrypt(nonce, body[86:], None)
  assert plaintext[-1] == 2 and json.loads(plaintext[:-1]) == message
  assert b'Parked motion' not in body
  token = headers['Authorization'].split('t=', 1)[1].split(',', 1)[0]
  head, claims, sig = token.split('.')
  claim_values = json.loads(web_push.unb64(claims))
  assert claim_values['aud'] == 'https://push.example.test' and claim_values['exp'] == 43300
  raw_signature = web_push.unb64(sig)
  der = utils.encode_dss_signature(int.from_bytes(raw_signature[:32], 'big'), int.from_bytes(raw_signature[32:], 'big'))
  web_push.load_key(pem).public_key().verify(der, (head + '.' + claims).encode(), ec.ECDSA(hashes.SHA256()))


def test_bounded_retry_and_expired_push_subscription(tmp_path):
  clock = [100.]
  calls = []
  owner = NotificationOwner(tmp_path / 'notifications', store(), clock=lambda: clock[0], transport=lambda *args: calls.append(args) or 503)
  try:
    configure(owner, 'ntfy')
    owner.action({'action': 'test', 'channel': 'ntfy'})
    for stamp in (100., 130., 250., 850., 2000.):
      clock[0] = stamp
      owner.tick()
    assert len(calls) == 4 and owner.snapshot()['channels']['ntfy']['lastState'] == 'failed'
    owner.action({'action': 'pushKey'})
    receiver = ec.generate_private_key(ec.SECP256R1())
    owner.action({'action': 'subscribe', 'subscription': {'endpoint': 'https://push.example.test/private',
                  'keys': {'p256dh': web_push.b64(web_push.public(receiver)), 'auth': web_push.b64(b'0123456789abcdef')}}})
    owner.action({'action': 'configure', 'channel': 'webPush', 'enabled': True, 'url': '', 'token': ''})
    owner.action({'action': 'test', 'channel': 'webPush'})
    owner.transport = lambda *args: 410
    owner.tick()
    assert owner.snapshot()['subscriptionCount'] == 0
    assert owner.snapshot()['channels']['webPush']['lastError'] == 'expired'
  finally:
    owner.close()


def test_published_rfc8291_section5_exact_ciphertext():
  # Independent published wire vector, https://www.rfc-editor.org/rfc/rfc8291#section-5
  subscription = {'endpoint': 'https://push.example.net/push/test', 'keys': {
    'auth': 'BTBZMqHH6r4Tts7J_aSIgg',
    'p256dh': 'BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4'}}
  sender = ec.derive_private_key(int.from_bytes(web_push.unb64('yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw'), 'big'), ec.SECP256R1())
  expected = web_push.unb64('DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27ml' +
                           'mlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPT' +
                           'pK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN')
  actual = web_push.encrypt(subscription, b'When I grow up, I want to be a watermelon', sender=sender, salt=expected[:16])
  assert actual == expected


@pytest.mark.parametrize('broken', [None, [], {}, 'bad', float('nan')])
def test_corrupt_saved_generation_and_timestamp_never_repaired_or_sent(tmp_path, broken):
  root = tmp_path / 'notifications'
  owner = NotificationOwner(root, store())
  configure(owner, 'webhook')
  owner.close()
  path = root / 'state.json'
  value = json.loads(path.read_text())
  value['channels']['webhook']['generation'] = broken
  original = json.dumps(value).encode()
  path.write_bytes(original)
  calls = []
  owner = NotificationOwner(root, store(), transport=lambda *args: calls.append(args) or 202)
  try:
    with pytest.raises(NotificationUnavailable):
      owner.snapshot()
    owner.tick()
    assert calls == [] and path.read_bytes() == original
  finally:
    owner.close()
