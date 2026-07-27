"""Small dependency-free HTTP API for standalone telemetry modes."""

from __future__ import annotations

import json
import re
import socket
import threading
import time

from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from openpilot.system.vehicle_telemetry.core import (
  VehicleTelemetryCache,
  is_fetch_authorized,
  load_vehicle_telemetry_config,
  load_vehicle_telemetry_status,
  public_vehicle_telemetry_config,
  telemetry_response,
)


TELEMETRY_HTTP_MAX_CONCURRENT_REQUESTS = 4
TELEMETRY_HTTP_REQUEST_TIMEOUT_SECONDS = 3.0
TELEMETRY_HTTP_MAX_REQUEST_LINE_BYTES = 2048
TELEMETRY_HTTP_MAX_HEADER_BYTES = 8192
TELEMETRY_HTTP_MAX_HEADER_COUNT = 32
TELEMETRY_HTTP_REQUESTS_PER_SECOND = 2.0
TELEMETRY_HTTP_REQUEST_BURST = 8
TELEMETRY_HTTP_FAILED_AUTHS_PER_SECOND = 0.2
TELEMETRY_HTTP_FAILED_AUTH_BURST = 5
TELEMETRY_HTTP_READ_CACHE_SECONDS = 1.0


class TokenBucket:
  """Small thread-safe limiter with fixed memory use."""

  def __init__(self, rate_per_second, capacity, *, monotonic=None):
    self.rate_per_second = max(0.0, float(rate_per_second))
    self.capacity = max(1.0, float(capacity))
    self.monotonic = monotonic or time.monotonic
    self.tokens = self.capacity
    self.updated_at = self.monotonic()
    self._lock = threading.Lock()

  def consume(self, amount=1.0):
    requested = max(0.0, float(amount))
    with self._lock:
      now = self.monotonic()
      elapsed = max(0.0, now - self.updated_at)
      self.updated_at = now
      self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_second)
      if self.tokens < requested:
        return False
      self.tokens -= requested
      return True


class TimedLoader:
  """Bound filesystem reads during abusive request bursts."""

  def __init__(self, loader, cache_seconds=TELEMETRY_HTTP_READ_CACHE_SECONDS, *, monotonic=None):
    self.loader = loader
    self.cache_seconds = max(0.0, float(cache_seconds))
    self.monotonic = monotonic or time.monotonic
    self._lock = threading.Lock()
    self._loaded_at = float("-inf")
    self._value = None

  def get(self):
    now = self.monotonic()
    with self._lock:
      if now - self._loaded_at >= self.cache_seconds:
        self._value = self.loader()
        self._loaded_at = now
      return self._value


class _TelemetryHTTPServer(ThreadingHTTPServer):
  daemon_threads = True
  block_on_close = True
  allow_reuse_address = True
  request_queue_size = TELEMETRY_HTTP_MAX_CONCURRENT_REQUESTS

  def __init__(
    self,
    server_address,
    handler_class,
    *,
    config_path=None,
    tunnel_status_path=None,
    max_concurrent_requests=TELEMETRY_HTTP_MAX_CONCURRENT_REQUESTS,
    request_timeout_seconds=TELEMETRY_HTTP_REQUEST_TIMEOUT_SECONDS,
    requests_per_second=TELEMETRY_HTTP_REQUESTS_PER_SECOND,
    request_burst=TELEMETRY_HTTP_REQUEST_BURST,
    failed_auths_per_second=TELEMETRY_HTTP_FAILED_AUTHS_PER_SECOND,
    failed_auth_burst=TELEMETRY_HTTP_FAILED_AUTH_BURST,
  ):
    super().__init__(server_address, handler_class)
    self.config_path = config_path
    self.tunnel_status_path = tunnel_status_path
    self.request_timeout_seconds = max(0.25, float(request_timeout_seconds))
    self.request_slots = threading.BoundedSemaphore(max(1, int(max_concurrent_requests)))
    self.request_limiter = TokenBucket(requests_per_second, request_burst)
    self.failed_auth_limiter = TokenBucket(failed_auths_per_second, failed_auth_burst)
    self.config_loader = TimedLoader(lambda: load_vehicle_telemetry_config(self.config_path))
    self.snapshot_loader = TimedLoader(lambda: VehicleTelemetryCache().load())

  def process_request(self, request, client_address):
    if not self.request_slots.acquire(blocking=False):
      self._reject_busy(request)
      return
    try:
      super().process_request(request, client_address)
    except Exception:
      self.request_slots.release()
      raise

  def process_request_thread(self, request, client_address):
    try:
      super().process_request_thread(request, client_address)
    finally:
      self.request_slots.release()

  @staticmethod
  def _reject_busy(request):
    response = b"\r\n".join((
      b"HTTP/1.0 503 Service Unavailable",
      b"Content-Type: application/json",
      b"Content-Length: 32",
      b"Cache-Control: no-store",
      b"Connection: close",
      b"",
      b'{"error":"Service unavailable."}',
    ))
    try:
      request.settimeout(0.1)
      request.sendall(response)
    except OSError:
      pass
    finally:
      try:
        request.shutdown(socket.SHUT_RDWR)
      except OSError:
        pass
      request.close()


class VehicleTelemetryRequestHandler(BaseHTTPRequestHandler):
  server_version = "openpilot-vehicle-telemetry/1"
  protocol_version = "HTTP/1.0"

  def setup(self):
    super().setup()
    self.connection.settimeout(self.server.request_timeout_seconds)

  def handle_one_request(self):
    """Read one bounded request and always close the connection afterward."""
    try:
      self.raw_requestline = self.rfile.readline(TELEMETRY_HTTP_MAX_REQUEST_LINE_BYTES + 1)
      if len(self.raw_requestline) > TELEMETRY_HTTP_MAX_REQUEST_LINE_BYTES:
        self.requestline = ""
        self.request_version = "HTTP/1.0"
        self.command = ""
        self.send_error(414, "Request-URI Too Long")
        return
      if not self.raw_requestline:
        self.close_connection = True
        return
      if not self.parse_request():
        return
      method = getattr(self, f"do_{self.command}", None)
      if method is None:
        self.send_error(501, f"Unsupported method ({self.command!r})")
        return
      method()
      self.wfile.flush()
    except TimeoutError:
      self.close_connection = True

  def parse_request(self):
    """Parse only the small HTTP subset needed by this read-only JSON API."""
    self.command = None
    self.request_version = "HTTP/1.0"
    self.close_connection = True
    try:
      self.requestline = self.raw_requestline.decode("iso-8859-1").rstrip("\r\n")
    except UnicodeDecodeError:
      self.send_error(400, "Bad request syntax")
      return False
    words = self.requestline.split()
    if len(words) != 3:
      self.send_error(400, "Bad request syntax")
      return False
    command, path, version = words
    if not re.fullmatch(r"[A-Z]{1,16}", command) or not path.startswith("/") or any(ord(char) < 0x20 for char in path):
      self.send_error(400, "Bad request syntax")
      return False
    if version not in ("HTTP/1.0", "HTTP/1.1"):
      self.send_error(505, "Invalid HTTP version")
      return False
    self.command = command
    self.path = path
    self.request_version = version

    headers = Message()
    total = 0
    count = 0
    authorization_seen = False
    while True:
      remaining = TELEMETRY_HTTP_MAX_HEADER_BYTES - total
      line = self.rfile.readline(remaining + 1)
      total += len(line)
      if total > TELEMETRY_HTTP_MAX_HEADER_BYTES:
        self.send_error(431, "Request Header Fields Too Large")
        return False
      if not line:
        self.send_error(400, "Unexpected end of headers")
        return False
      if line in (b"\r\n", b"\n"):
        break
      count += 1
      if count > TELEMETRY_HTTP_MAX_HEADER_COUNT or line[:1] in (b" ", b"\t"):
        self.send_error(431, "Request Header Fields Too Large")
        return False
      try:
        decoded = line.decode("iso-8859-1").rstrip("\r\n")
      except UnicodeDecodeError:
        self.send_error(400, "Invalid request header")
        return False
      name, separator, value = decoded.partition(":")
      if not separator or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,64}", name):
        self.send_error(400, "Invalid request header")
        return False
      value = value.strip(" \t")
      if any(ord(char) < 0x20 and char != "\t" for char in value):
        self.send_error(400, "Invalid request header")
        return False
      if name.lower() == "authorization":
        if authorization_seen:
          self.send_error(400, "Duplicate authorization header")
          return False
        authorization_seen = True
      headers.add_header(name, value)
    self.headers = headers
    return True

  def log_message(self, format, *args):  # noqa: A002
    # Do not put request metadata next to authentication failures in logs. The
    # daemon's status documents provide the useful operational diagnostics.
    return

  def _write_json(self, status, payload, *, authenticate=False, retry_after=None):
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(encoded)))
    self.send_header("Cache-Control", "no-store")
    self.send_header("Connection", "close")
    self.send_header("X-Content-Type-Options", "nosniff")
    if authenticate:
      self.send_header("WWW-Authenticate", 'Bearer realm="vehicle-telemetry"')
    if retry_after is not None:
      self.send_header("Retry-After", str(max(1, int(retry_after))))
    self.end_headers()
    try:
      self.wfile.write(encoded)
    except (BrokenPipeError, ConnectionResetError, TimeoutError):
      pass
    self.close_connection = True

  def _config(self):
    return self.server.config_loader.get()

  def _authorized_config(self):
    config = self._config()
    if not config["fetch"]["enabled"]:
      self._write_json(404, {"error": "EV Vehicle Telemetry fetch is disabled."})
      return None
    if not is_fetch_authorized(config, self.headers.get("Authorization")):
      if not self.server.failed_auth_limiter.consume():
        self._write_json(429, {"error": "Too many requests."}, retry_after=5)
        return None
      self._write_json(401, {"error": "EV Vehicle Telemetry authorization failed."}, authenticate=True)
      return None
    return config

  def do_GET(self):
    if not self.server.request_limiter.consume():
      self._write_json(429, {"error": "Too many requests."}, retry_after=1)
      return
    path = self.path.split("?", 1)[0]
    if path == "/health":
      self._write_json(200, {"status": "ok"})
      return
    if path not in ("/api/vehicle/telemetry", "/api/vehicle/telemetry/status"):
      self._write_json(404, {"error": "Not found."})
      return

    config = self._authorized_config()
    if config is None:
      return
    cache = telemetry_response(self.server.snapshot_loader.get(), vehicle_id=config["push"]["vehicleId"])
    if path == "/api/vehicle/telemetry":
      if cache is None:
        self._write_json(503, {"error": "No validated EV Vehicle Telemetry has been cached yet."})
      else:
        self._write_json(200, cache)
      return

    tunnel_status = {}
    if self.server.tunnel_status_path is not None:
      tunnel_status = load_vehicle_telemetry_status(self.server.tunnel_status_path)
      tunnel_status.pop("ownerURL", None)
    self._write_json(
      200,
      {
        "config": public_vehicle_telemetry_config(config),
        "cache": cache,
        "exporter": load_vehicle_telemetry_status(),
        "tunnel": tunnel_status,
      },
    )


class VehicleTelemetryHTTPService:
  def __init__(self, *, config_path=None, tunnel_status_path=None, server_options=None):
    self.config_path = config_path
    self.tunnel_status_path = tunnel_status_path
    self.server_options = dict(server_options or {})
    self._server = None
    self._thread = None
    self.address = None

  def set_tunnel_status_path(self, path):
    self.tunnel_status_path = path
    if self._server is not None:
      self._server.tunnel_status_path = path

  def start(self, bind_address, port):
    requested = (str(bind_address), int(port))
    if self._server is not None and self.address == requested:
      return
    self.stop()
    self._server = _TelemetryHTTPServer(
      requested,
      VehicleTelemetryRequestHandler,
      config_path=self.config_path,
      tunnel_status_path=self.tunnel_status_path,
      **self.server_options,
    )
    self.address = requested
    self._thread = threading.Thread(target=self._server.serve_forever, name="vehicle-telemetry-http", daemon=True)
    self._thread.start()

  def stop(self):
    server, thread = self._server, self._thread
    self._server = None
    self._thread = None
    self.address = None
    if server is not None:
      server.shutdown()
      server.server_close()
    if thread is not None:
      thread.join(timeout=2.0)
