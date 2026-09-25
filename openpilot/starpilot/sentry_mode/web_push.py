"""RFC8291 aes128gcm and RFC8292 VAPID using the existing JWT crypto dependency."""
import base64
import json
import os
import struct
import time
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def b64(raw: bytes) -> str:
  return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def unb64(value: str) -> bytes:
  return base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)


def public(key) -> bytes:
  return key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def new_key() -> str:
  key = ec.generate_private_key(ec.SECP256R1())
  return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption()).decode()


def load_key(pem: str):
  key = serialization.load_pem_private_key(pem.encode(), password=None)
  if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
    raise ValueError('Invalid push key')
  return key


def validate_subscription(subscription: dict) -> None:
  if type(subscription) is not dict or set(subscription) != {'endpoint', 'keys'}:
    raise ValueError('Invalid push subscription')
  keys = subscription['keys']
  if type(keys) is not dict or set(keys) != {'p256dh', 'auth'}:
    raise ValueError('Invalid push keys')
  if any(type(value) is not str or len(value) > 256 for value in keys.values()):
    raise ValueError('Invalid push keys')
  receiver = unb64(keys['p256dh'])
  if len(receiver) != 65 or len(unb64(keys['auth'])) != 16:
    raise ValueError('Invalid push keys')
  ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), receiver)


def encrypt(subscription: dict, payload: bytes, *, sender=None, salt: bytes | None = None) -> bytes:
  validate_subscription(subscription)
  receiver = unb64(subscription['keys']['p256dh'])
  auth = unb64(subscription['keys']['auth'])
  sender = sender if sender is not None else ec.generate_private_key(ec.SECP256R1())
  sender_public = public(sender)
  shared = sender.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), receiver))
  ikm = HKDF(algorithm=hashes.SHA256(), length=32, salt=auth,
             info=b'WebPush: info\x00' + receiver + sender_public).derive(shared)
  salt = salt if salt is not None else os.urandom(16)
  cek = HKDF(algorithm=hashes.SHA256(), length=16, salt=salt, info=b'Content-Encoding: aes128gcm\x00').derive(ikm)
  nonce = HKDF(algorithm=hashes.SHA256(), length=12, salt=salt, info=b'Content-Encoding: nonce\x00').derive(ikm)
  plaintext = payload + b'\x02'
  if len(plaintext) > 3000:
    raise ValueError('Push payload exceeds limit')
  return salt + struct.pack('!I', 4096) + bytes([65]) + sender_public + AESGCM(cek).encrypt(nonce, plaintext, None)


def request(subscription: dict, message: dict, pem: str, *, now: int | None = None) -> tuple[bytes, dict]:
  body = encrypt(subscription, json.dumps(message, separators=(',', ':')).encode())
  parsed = urlsplit(subscription['endpoint'])
  origin = f'{parsed.scheme}://{parsed.netloc}'
  header = b64(b'{"typ":"JWT","alg":"ES256"}')
  # RFC8292 expiration is a Unix epoch, independent of process monotonic time.
  claims = b64(json.dumps({'aud': origin, 'exp': (time.time_ns() // 1_000_000_000 if now is None else now) + 43200,
                          'sub': os.getenv('STARPILOT_VAPID_SUBJECT', 'mailto:galaxy@firestar.link')}, separators=(',', ':')).encode())
  signing = f'{header}.{claims}'.encode()
  vapid = load_key(pem)
  r, s = utils.decode_dss_signature(vapid.sign(signing, ec.ECDSA(hashes.SHA256())))
  token = signing.decode() + '.' + b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))
  return body, {'Authorization': f'vapid t={token}, k={b64(public(vapid))}', 'Content-Encoding': 'aes128gcm',
                'Content-Type': 'application/octet-stream', 'TTL': '300', 'Topic': message['eventId'][:32]}
