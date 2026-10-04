"""Private pairing identity and FRPC configuration for Galaxy remote access."""

from __future__ import annotations

import base64
import binascii
from contextlib import contextmanager
import fcntl
import json
import hmac
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections.abc import Callable
import threading

SLUG = re.compile(r"[A-Za-z0-9]{16}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


def gateway_cookie_valid(cookie: str | None, record: dict[str, str]) -> bool:
  """Validate this comma's token in either generation of the gateway cookie."""
  if cookie is None or not 1 <= len(cookie) <= 4096:
    return False
  try:
    decoded = unquote(cookie, errors="strict")
    if not decoded.isascii():
      return False
    if decoded.startswith(record["slug"] + ":"):
      token = decoded[len(record["slug"]) + 1:]
    else:
      if re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", decoded) is None:
        return False
      sessions = json.loads(base64.b64decode(decoded + "=" * (-len(decoded) % 4), altchars=b"-_", validate=True))
      if type(sessions) is not dict or len(sessions) > 40:
        return False
      token = sessions.get(record["slug"])
    return type(token) is str and HASH.fullmatch(token) is not None and hmac.compare_digest(token, record["session"])
  except (ValueError, UnicodeError, binascii.Error):
    return False


class RemotePairing:
  FILE = "remote-v1.json"
  UNPAIRED = "remote-unpaired-v1"

  def __init__(self, root: Path):
    self.root = root

  @contextmanager
  def _locked(self):
    self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = self.root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
      raise ValueError("Pairing directory is unsafe")
    fd = os.open(self.root / '.remote.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
      info = os.fstat(fd)
      if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError("Pairing lock is unsafe")
      fcntl.flock(fd, fcntl.LOCK_EX)
      yield
    finally:
      os.close(fd)

  def _sync_directory(self):
    fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
      os.fsync(fd)
    finally:
      os.close(fd)

  def read(self) -> dict[str, str] | None:
    try:
      directory = self.root.lstat()
      if not stat.S_ISDIR(directory.st_mode) or directory.st_mode & 0o077:
        return None
      path = self.root / self.FILE
      info = path.lstat()
      if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > 512:
        return None
      fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
      with os.fdopen(fd, encoding="utf-8") as stream:
        record = json.load(stream)
      if type(record) is not dict or set(record) != {"version", "slug", "authHash", "session"} or record["version"] != 1:
        return None
      if not (type(record["slug"]) is str and SLUG.fullmatch(record["slug"]) and
              type(record["authHash"]) is str and HASH.fullmatch(record["authHash"]) and
              type(record["session"]) is str and HASH.fullmatch(record["session"])):
        return None
      return record
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
      return None

  @staticmethod
  def _legacy_record(root: Path, auth_hash: str | None = None) -> dict[str, str] | None:
    values = {}
    try:
      directory = root.lstat()
      if not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.geteuid() or directory.st_mode & 0o022:
        return None
      for name in ('glxyauth', 'glxysession', 'glxyslug'):
        fd = os.open(root / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'r', encoding='ascii') as stream:
          info = os.fstat(stream.fileno())
          if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022 or info.st_size > 128:
            return None
          values[name] = stream.read(129).strip()
      if not HASH.fullmatch(values['glxyauth']) or (auth_hash is not None and not hmac.compare_digest(values['glxyauth'], auth_hash)) or \
         not SLUG.fullmatch(values['glxyslug']) or not HASH.fullmatch(values['glxysession']):
        return None
      return {'version': 1, 'slug': values['glxyslug'], 'authHash': values['glxyauth'], 'session': values['glxysession']}
    except (OSError, UnicodeError):
      return None

  def pair(self, auth_hash: str, *, legacy_root: Path | None = None) -> str | None:
    if not HASH.fullmatch(auth_hash):
      return None
    try:
      with self._locked():
        if os.path.lexists(self.root / self.FILE):
          return None
        record = None
        if legacy_root is not None and not os.path.lexists(self.root / self.UNPAIRED):
          record = self._legacy_record(legacy_root, auth_hash)
        if record is None:
          record = {"version": 1, "slug": ''.join(secrets.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(16)),
                    "authHash": auth_hash, "session": secrets.token_hex(32)}
        return self._store(record)
    except (OSError, ValueError):
      return None

  def migrate_legacy(self, legacy_root: Path | None) -> bool:
    from openpilot.starpilot.galaxy.access import GalaxyAccessOwner
    if legacy_root is None:
      return False
    try:
      with self._locked():
        if any(os.path.lexists(self.root / name) for name in (self.FILE, self.UNPAIRED, GalaxyAccessOwner.FILE)):
          return False
        record = self._legacy_record(legacy_root)
        if record is None or record != self._legacy_record(legacy_root):
          return False
        return self._store(record) is not None
    except (OSError, ValueError):
      return False

  def _store(self, record: dict[str, str]) -> str | None:
    fd, temporary = tempfile.mkstemp(prefix=".remote-", dir=self.root)
    try:
      os.fchmod(fd, 0o600)
      with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(record, stream, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
      os.link(temporary, self.root / self.FILE)
      self._sync_directory()
      return record["slug"]
    except (OSError, ValueError):
      return None
    finally:
      if os.path.exists(temporary):
        os.unlink(temporary)

  def unpair(self) -> bool:
    try:
      with self._locked():
        if not os.path.lexists(self.root / self.FILE):
          return False
        fd = os.open(self.root / self.UNPAIRED, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
          info = os.fstat(fd)
          if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            return False
          os.fsync(fd)
        finally:
          os.close(fd)
        self._sync_directory()
        (self.root / self.FILE).unlink()
        self._sync_directory()
        return True
    except (OSError, ValueError):
      return False

  @staticmethod
  def url(slug: str) -> str:
    return f"https://galaxy.firestar.link/{slug}"

  @staticmethod
  def frpc_config(slug: str, remote_port: int, auth_port: int) -> str:
    if not SLUG.fullmatch(slug):
      raise ValueError("Invalid Galaxy slug")
    return f'''serverAddr = "galaxy.firestar.link"
serverPort = 7000

[transport]
tls.enable = true
poolCount = 2

[[proxies]]
name = "{slug}_galaxy"
type = "http"
localIP = "127.0.0.1"
localPort = {remote_port}
customDomains = ["{slug}.devices.local"]
transport.useCompression = true

[[proxies]]
name = "{slug}_auth"
type = "http"
localIP = "127.0.0.1"
localPort = {auth_port}
customDomains = ["auth-{slug}.devices.local"]
'''


def default_remote_pairing() -> RemotePairing:
  from openpilot.starpilot.galaxy.access import legacy_galaxy_root
  from openpilot.starpilot.storage import galaxy_storage_root
  pairing = RemotePairing(galaxy_storage_root())
  pairing.migrate_legacy(legacy_galaxy_root())
  return pairing


class _GatewayAuthServer(ThreadingHTTPServer):
  daemon_threads = True
  block_on_close = False

  def __init__(self, *args, **kwargs):
    self.slots = threading.BoundedSemaphore(8)
    super().__init__(*args, **kwargs)

  def get_request(self):
    request, address = super().get_request()
    request.settimeout(4)
    return request, address

  def process_request(self, request, client_address):
    if not self.slots.acquire(blocking=False):
      self.shutdown_request(request)
      return
    try:
      super().process_request(request, client_address)
    except BaseException:
      self.slots.release()
      raise

  def process_request_thread(self, request, client_address):
    try:
      super().process_request_thread(request, client_address)
    finally:
      self.slots.release()


def make_gateway_auth_server(pairing: RemotePairing, dongle_id: str | Callable[[], str], *, port: int = 8083):
  """Original Galaxy gateway's two loopback auth endpoints, without local web authority."""
  class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - Match BaseHTTPRequestHandler.
      pass

    def do_POST(self):
      if self.path not in ('/glxylogin', '/glxyverify'):
        self.send_error(404)
        return
      record = pairing.read()
      try:
        length = int(self.headers.get('Content-Length', ''))
      except ValueError:
        length = -1
      if record is None or not 1 <= length <= 128 or self.headers.get('Transfer-Encoding') is not None:
        self.send_error(403)
        return
      try:
        body = self.rfile.read(length).decode('ascii').strip()
      except (OSError, UnicodeError):
        self.send_error(403)
        return
      expected = record['authHash'] if self.path == '/glxylogin' else record['session']
      if not hmac.compare_digest(body, expected):
        self.send_error(403)
        return
      device_id = dongle_id() if callable(dongle_id) else dongle_id
      if self.path == '/glxylogin' and not device_id:
        self.send_error(503)
        return
      data = json.dumps({'dongle_id': device_id, 'token': record['session']}).encode() if self.path == '/glxylogin' else b''
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.send_header('Content-Length', str(len(data)))
      self.send_header('Cache-Control', 'no-store')
      self.end_headers()
      self.wfile.write(data)

  return _GatewayAuthServer(('127.0.0.1', port), Handler)
