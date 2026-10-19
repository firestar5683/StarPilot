"""One-shot phone claim: a phone gets its own key while comma's pairing window is open.

The window is a small private file written by comma when someone presses Pair phone.
The phone sends an unsealed request with a P-256 public key; comma answers with a new
per-phone key sealed under an ECDH-derived key. Nothing else is accepted without a key.
"""
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import time

CLAIM_PATH = Path("/dev/shm/starpilot-phone-claim.json")
REQUEST_MAGIC = b"GCL1"
REPLY_MAGIC = b"GCR1"
INFO = b"galaxy-claim-v1"
AAD = b"galaxy-claim-v1/reply"
WINDOW_SECONDS = 120
POINT_SIZE = 65
MAX_NAME = 40
GRACE_SECONDS = 60


def _read(path):
  fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
  with os.fdopen(fd) as stream:
    return json.loads(stream.read(4096))


def arm(adapter_address, adapter_name, path=None, seconds=WINDOW_SECONDS, now=None):
  """Open the window. Replaces any earlier one."""
  path = Path(CLAIM_PATH if path is None else path)
  value = {"deadline": (time.monotonic() if now is None else now) + seconds, "adapterAddress": str(adapter_address)[:17],
           "adapterName": str(adapter_name)[:80], "used": False, "claimed": ""}
  fd, tmp = tempfile.mkstemp(prefix=".claim-", dir=path.parent)
  try:
    with os.fdopen(fd, "w") as stream:
      os.fchmod(stream.fileno(), 0o600)
      json.dump(value, stream)
    os.replace(tmp, path)
  finally:
    if os.path.exists(tmp):
      os.unlink(tmp)


def clear(path=None):
  path = CLAIM_PATH if path is None else path
  try:
    os.unlink(path)
  except FileNotFoundError:
    pass


def window(path=CLAIM_PATH, now=None):
  """The open window, or None when there is none, it ran out, or a phone already claimed it."""
  if path is None:
    return None
  try:
    value = _read(path)
  except (OSError, ValueError):
    return None
  if not isinstance(value, dict) or value.get("used") is not False:
    return None
  deadline = value.get("deadline")
  if type(deadline) not in (int, float) or (time.monotonic() if now is None else now) >= deadline:
    return None
  return value


def view(path=CLAIM_PATH, now=None):
  """What Galaxy shows: seconds left in the window, the phone that claimed the app key, and whether music paired."""
  now = time.monotonic() if now is None else now
  try:
    value = _read(path)
  except (OSError, ValueError):
    return {"open": False, "left": 0, "claimed": "", "paired": False}
  deadline = value.get("deadline") if isinstance(value, dict) else None
  if type(deadline) not in (int, float) or now >= deadline + GRACE_SECONDS:
    return {"open": False, "left": 0, "claimed": "", "paired": False}
  return {"open": now < deadline, "left": max(0, int(deadline - now + 0.999)),
          "claimed": str(value.get("claimed", ""))[:MAX_NAME] if value.get("used") is True else "",
          "paired": bool(value.get("pairedAddress"))}


def status(path=CLAIM_PATH, now=None):
  """What comma shows: open, the name of the phone that claimed, or nothing."""
  if path is None:
    return {}
  try:
    value = _read(path)
  except (OSError, ValueError):
    return {}
  if not isinstance(value, dict):
    return {}
  if value.get("used") is True:
    return {"claimed": str(value.get("claimed", ""))[:MAX_NAME], "paired": bool(value.get("pairedAddress"))}
  return {"open": window(path, now) is not None, "paired": bool(value.get("pairedAddress"))}


def _update(path, change):
  """Change the claim file under a lock; returns change's result, or None when there is no file."""
  path = Path(path)
  try:
    lock = os.open(path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
  except OSError:
    return None
  with os.fdopen(lock, "w") as stream:
    fcntl.flock(stream, fcntl.LOCK_EX)
    try:
      value = _read(path)
    except (OSError, ValueError):
      return None
    if not isinstance(value, dict):
      return None
    result = change(value)
    if result is not None:
      fd, tmp = tempfile.mkstemp(prefix=".claim-", dir=path.parent)
      try:
        with os.fdopen(fd, "w") as out:
          os.fchmod(out.fileno(), 0o600)
          json.dump(value, out)
        os.replace(tmp, path)
      finally:
        if os.path.exists(tmp):
          os.unlink(tmp)
    return result


def finish(name, phone_id, path=None):
  """Mark the window used so a second phone cannot claim it."""
  path = CLAIM_PATH if path is None else path

  def change(value):
    if window(path) is None:
      return None
    value.update(used=True, claimed=str(name)[:MAX_NAME], claimedId=str(phone_id))
    return True
  return bool(_update(path, change))


def note_paired(address, path=None, now=None):
  """The phone also finished the music pairing in this window (a little late is fine)."""
  path = CLAIM_PATH if path is None else path

  def change(value):
    deadline = value.get("deadline")
    if type(deadline) not in (int, float) or (time.monotonic() if now is None else now) >= deadline + GRACE_SECONDS:
      return None
    value["pairedAddress"] = str(address)[:17].upper()
    return True
  return bool(_update(path, change))


def take_link(path=None):
  """(phone id, bluetooth address) once the same window did both the app claim and the music pairing; once only."""
  path = CLAIM_PATH if path is None else path

  def change(value):
    if value.get("linked") or not value.get("claimedId") or not value.get("pairedAddress"):
      return None
    value["linked"] = True
    return (value["claimedId"], value["pairedAddress"])
  return _update(path, change)


def parse_request(data):
  """-> (phone public key bytes, phone name). Raises ValueError for anything else."""
  if len(data) < 4 + POINT_SIZE or data[:4] != REQUEST_MAGIC or data[4] != 4:
    raise ValueError("Not a claim request")
  public = bytes(data[4:4 + POINT_SIZE])
  name = bytes(data[4 + POINT_SIZE:])
  if len(name) > 4 * MAX_NAME:
    raise ValueError("Name too long")
  return public, name.decode("utf-8", "replace")


P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b


def validate(public):
  """Raises ValueError unless public is an uncompressed point that lies on P-256 (not infinity)."""
  if len(public) != POINT_SIZE or public[0] != 4:
    raise ValueError("Invalid public key")
  x, y = int.from_bytes(public[1:33], "big"), int.from_bytes(public[33:], "big")
  if x >= P or y >= P or (y * y - (x * x * x - 3 * x + B)) % P:
    raise ValueError("Invalid public key")
  return _point(public)


def _point(public):
  from Crypto.PublicKey import ECC
  return ECC.EccPoint(int.from_bytes(public[1:33], "big"), int.from_bytes(public[33:], "big"), curve="P-256")


def derive(private_scalar, peer_public, salt):
  """ECDH on P-256, then HKDF-SHA256 (RFC 5869) with the session challenge as salt -> 32-byte key."""
  shared = (_point(peer_public) * private_scalar).x
  secret = int(shared).to_bytes(32, "big")
  prk = hmac.new(salt, secret, hashlib.sha256).digest()
  return hmac.new(prk, INFO + b"\x01", hashlib.sha256).digest()


def reply(public, challenge, payload):
  """Build the reply frame body for a valid request: our public key and the sealed payload."""
  from Crypto.Cipher import AES
  from Crypto.PublicKey import ECC
  validate(public)
  ours = ECC.generate(curve="P-256")
  mine = b"\x04" + int(ours.pointQ.x).to_bytes(32, "big") + int(ours.pointQ.y).to_bytes(32, "big")
  key = derive(int(ours.d), public, challenge)
  cipher = AES.new(key, AES.MODE_GCM, nonce=secrets.token_bytes(12))
  cipher.update(AAD)
  ciphertext, tag = cipher.encrypt_and_digest(json.dumps(payload, separators=(",", ":")).encode())
  return REPLY_MAGIC + mine + bytes(cipher.nonce) + ciphertext + tag
