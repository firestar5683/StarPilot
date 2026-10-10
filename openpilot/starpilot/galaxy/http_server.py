"""Bounded Galaxy HTTP connections and shared-source shutdown."""

from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from functools import lru_cache
import gzip
from ipaddress import IPv4Address, ip_address, ip_network
import json
import mimetypes
from pathlib import Path
import threading
import time


class _LocalHTTPServer(ThreadingHTTPServer):
  """Bound idle browser connections without blocking other local requests."""

  MAX_CONNECTIONS = 8
  REQUEST_TIMEOUT = 4.0

  def __init__(self, *args, **kwargs):
    self._slots = threading.BoundedSemaphore(self.MAX_CONNECTIONS)
    super().__init__(*args, **kwargs)

  def get_request(self):
    request, address = super().get_request()
    request.settimeout(self.REQUEST_TIMEOUT)
    return request, address

  def process_request(self, request, client_address):
    if not self._slots.acquire(timeout=self.REQUEST_TIMEOUT):
      self.shutdown_request(request)
      return
    try:
      super().process_request(request, client_address)
    except Exception:
      self._slots.release()
      raise

  def process_request_thread(self, request, client_address):
    try:
      super().process_request_thread(request, client_address)
    finally:
      self._slots.release()

  def drain_requests(self, timeout: float) -> bool:
    """Wait for accepted requests before closing their shared data sources."""
    deadline = time.monotonic() + timeout
    acquired = 0
    try:
      for _ in range(self.MAX_CONNECTIONS):
        if not self._slots.acquire(timeout=max(0.0, deadline - time.monotonic())):
          return False
        acquired += 1
      return True
    finally:
      for _ in range(acquired):
        self._slots.release()

  def service_actions(self):
    super().service_actions()
    maintain = getattr(self, 'maintain_android_auto', None)
    if maintain is not None:
      try:
        maintain()
      except Exception:
        pass  # Optional housekeeping must never stop serve_forever.

  def server_close(self, *, close_sources: bool = True):
    if not close_sources:
      # Managed shutdown can abandon a stuck daemon request. Its readers must
      # remain alive until that process exits; only retire the listening socket.
      media = getattr(self, 'recording_media_source', None)
      if media is not None:
        media.stop_child()
      super().server_close()
      return
    # Always close every owned source, even if another cleanup raises. The
    # analysis child must stop before its parked-state reader is retired.
    with ExitStack() as cleanup:
      cleanup.callback(super().server_close)
      media = getattr(self, 'recording_media_source', None)
      if media is not None:
        cleanup.callback(media.close)
      for name in ('map_source', 'settings_source', 'vehicle_selection_source', 'model_source', 'plots_source',
                   'flm_source', 'bluetooth_authority', 'bluetooth_source', 'model_manager_source', 'model_authority', 'layout_authority', 'favorites_source',
                   'sound_authority', 'sound_source', 'software_operations_source', 'drive_stats_authority', 'drive_stats_source',
                   'pairing_authority', 'evidence_source', 'device_state_source', 'navigation_source', 'drive_physical_source', 'notification_source',
                   'android_auto_setup_source', 'play_install_source'):
        close = getattr(getattr(self, name, None), 'close', None)
        if callable(close):
          cleanup.callback(close)


LOCAL_NETWORKS = tuple(ip_network(network) for network in ('127.0.0.0/8', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '169.254.0.0/16'))


def direct_local_connection(peer: str, destination: str, headers) -> bool:
  """Passwordless access is limited to direct local sockets, never forwarded requests."""
  proxy_headers = {'forwarded', 'via', 'x-real-ip', 'x-client-ip', 'x-original-forwarded-for', 'cf-connecting-ip', 'true-client-ip'}
  if any(name.lower() in proxy_headers or name.lower().startswith('x-forwarded-') for name in headers):
    return False
  try:
    return all(isinstance(address, IPv4Address) and any(address in network for network in LOCAL_NETWORKS)
               for address in (ip_address(peer), ip_address(destination)))
  except ValueError:
    return False


def allowed_authority(host: str, local_address: str, port: int) -> bool:
  """Accept only the literal address reached by this socket, or loopback's name."""
  if host == f'localhost:{port}' and local_address == '127.0.0.1':
    return True
  if host != f'{local_address}:{port}':
    return False
  try:
    address = ip_address(local_address)
  except ValueError:
    return False
  return isinstance(address, IPv4Address) and not address.is_unspecified


@lru_cache(maxsize=128)
def static_asset(path: str, identity: tuple[int, int, int]):
  body = Path(path).read_bytes()
  content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
  compressible = content_type.startswith('text/') or content_type in ('application/javascript', 'application/json', 'image/svg+xml')
  packed = gzip.compress(body, compresslevel=5, mtime=0) if compressible and len(body) > 1024 else body
  if len(packed) >= len(body):
    packed = body
  return body, packed, content_type


class _LocalHTTPHandler(BaseHTTPRequestHandler):
  def log_message(self, format, *args):  # noqa: A002 - Match BaseHTTPRequestHandler's keyword signature.
    pass

  def handle(self):
    try:
      super().handle()
    except (BrokenPipeError, ConnectionResetError):
      # The browser can retire an in-flight fetch or speculative connection.
      self.close_connection = True

  def respond(self, status, body, content_type='application/json', cookie=None, *, asset_headers=None, cache_control=None):
    self.send_response(status)
    self.send_header('Content-Type', content_type)
    self.send_header('Content-Length', str(len(body)))
    self.send_header('Cache-Control', cache_control or ('private, max-age=0, must-revalidate' if asset_headers else 'no-store'))
    for key, value in (asset_headers or {}).items():
      self.send_header(key, value)
    self.send_header('X-Content-Type-Options', 'nosniff')
    self.send_header('Referrer-Policy', 'no-referrer')
    if cookie is not None:
      self.send_header('Set-Cookie', cookie)
    self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; " +
                     "img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
    self.end_headers()
    if self.command != 'HEAD':
      self.wfile.write(body)

  def json(self, status, value):
    self.respond(status, json.dumps(value, allow_nan=False).encode())

  def attachment(self, filename, body, content_type):
    """A download the browser saves as ``filename`` rather than displays."""
    self.send_response(200)
    self.send_header('Content-Type', content_type)
    self.send_header('Content-Length', str(len(body)))
    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
    self.send_header('Cache-Control', 'no-store')
    self.send_header('X-Content-Type-Options', 'nosniff')
    self.send_header('Referrer-Policy', 'no-referrer')
    self.end_headers()
    if self.command != 'HEAD':
      self.wfile.write(body)
