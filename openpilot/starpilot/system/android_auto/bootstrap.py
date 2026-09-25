"""Phone-side Android Auto Wireless bootstrap over the head unit's RFCOMM service.

The head unit is the RFCOMM server; StarPilot connects as the phone and runs:

  HU -> WifiStartRequest(ip, port)          [some receivers first send WifiVersionRequest]
  ph -> WifiInfoRequest()
  HU -> WifiInfoResponse(ssid, key, bssid, security, ap_type)
  ph -> WifiStartResponse(status=0)
        ... phone joins the head unit's Wi-Fi ...
  ph -> WifiConnectStatus(status=0)
  ph -> TCP connect ip:port, where the ordinary Android Auto session starts

Frames are ``[payload length u16 BE][message id u16 BE][protobuf]``. Pings are
answered at every stage. Receivers disagree on a few details, so this module is
deliberately tolerant: the version exchange is optional, the endpoint may come
from WifiSetupInfo instead of WifiStartRequest, and the key/BSSID field order of
WifiInfoResponse is detected from content rather than assumed.

Wire facts: aa-proxy/aa-proxy-rs ``src/bluetooth.rs`` (MIT, pinned
d61ad375a669ede2f260ba65f0ccb48576e21885) and mrmees/open-android-auto
``docs/wireless-bluetooth-setup.md`` / ``oaa/wifi`` (reference only; not copied).
"""

from __future__ import annotations

import ipaddress
import re
import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field as dataclass_field

from openpilot.starpilot.system.android_auto.wire import field, one, parse_fields, signed, text

WIFI_START_REQUEST = 1
WIFI_INFO_REQUEST = 2
WIFI_INFO_RESPONSE = 3
WIFI_VERSION_REQUEST = 4
WIFI_VERSION_RESPONSE = 5
WIFI_CONNECT_STATUS = 6
WIFI_START_RESPONSE = 7
WIFI_PING_REQUEST = 8
WIFI_PING_RESPONSE = 9
WIFI_CONNECTION_REJECTION = 10
WIFI_SETUP_INFO = 11

NAMES = {1: "WifiStartRequest", 2: "WifiInfoRequest", 3: "WifiInfoResponse", 4: "WifiVersionRequest",
         5: "WifiVersionResponse", 6: "WifiConnectStatus", 7: "WifiStartResponse", 8: "WifiPingRequest",
         9: "WifiPingResponse", 10: "WifiConnectionRejection", 11: "WifiSetupInfo"}

STATUS_SUCCESS = 0
STATUS_NETWORK_UNAVAILABLE = -1

SECURITY_OPEN = 1
SECURITY_NAMES = {0: "unknown", 1: "open", 2: "wep64", 3: "wep128", 4: "wpa", 8: "wpa2", 12: "wpa/wpa2",
                  20: "wpa-enterprise", 24: "wpa2-enterprise", 28: "wpa/wpa2-enterprise", 32: "wpa3", 40: "wpa2/wpa3"}

MAX_FRAME = 4096
MAX_FRAMES = 64
MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


class BootstrapError(RuntimeError):
  def __init__(self, stage: str, message: str):
    super().__init__(f"{stage}: {message}")
    self.stage = stage


@dataclass(frozen=True)
class Endpoint:
  ip: str
  port: int


@dataclass(frozen=True)
class WifiCredentials:
  ssid: str
  key: str = dataclass_field(repr=False)
  bssid: str
  security: int
  ap_type: int

  @property
  def open(self) -> bool:
    return self.security == SECURITY_OPEN or not self.key

  def describe(self) -> dict:
    """Loggable summary; never includes the key."""
    return {"ssid": self.ssid, "bssid": self.bssid, "security": SECURITY_NAMES.get(self.security, str(self.security)),
            "ap_type": self.ap_type, "key_length": len(self.key)}


@dataclass
class BootstrapResult:
  endpoint: Endpoint
  credentials: WifiCredentials
  head_unit: dict = dataclass_field(default_factory=dict)
  version: tuple[int, int] | None = None


def encode_frame(message_id: int, payload: bytes = b"") -> bytes:
  if len(payload) > MAX_FRAME:
    raise ValueError("Bootstrap payload too large")
  return struct.pack(">HH", len(payload), message_id) + payload


def valid_endpoint(ip: str, port) -> Endpoint | None:
  try:
    address = ipaddress.IPv4Address(ip)
  except ValueError:
    return None
  if not isinstance(port, int) or not 0 < port < 65536 or address.is_unspecified or address.is_multicast:
    return None
  return Endpoint(str(address), port)


def parse_endpoint(payload: bytes) -> Endpoint | None:
  fields = parse_fields(payload)
  return valid_endpoint(text(fields, 1), one(fields, 2))


def parse_info_response(payload: bytes) -> WifiCredentials:
  """Decode WifiInfoResponse, detecting whether field 2 or 3 carries the BSSID.

  aa-proxy (which interoperates with real phones) uses ssid=1, key=2, bssid=3;
  open-android-auto's APK-derived schema lists bssid=2, passphrase=3.
  """
  fields = parse_fields(payload)
  ssid, second, third = text(fields, 1), text(fields, 2), text(fields, 3)
  if MAC_RE.match(second) and not MAC_RE.match(third):
    bssid, key = second, third
  else:
    key, bssid = second, third
  if not ssid:
    raise ValueError("WifiInfoResponse has no SSID")
  return WifiCredentials(ssid=ssid, key=key, bssid=bssid.upper().replace("-", ":") if MAC_RE.match(bssid) else "",
                         security=int(one(fields, 4, 0) or 0), ap_type=int(one(fields, 5, 0) or 0))


def parse_setup_info(payload: bytes) -> tuple[Endpoint | None, WifiCredentials | None]:
  fields = parse_fields(payload)
  endpoint = None
  if isinstance(one(fields, 4), bytes):
    endpoint = parse_endpoint(one(fields, 4))
  credentials = None
  network = one(fields, 5)
  if isinstance(network, bytes):
    net = parse_fields(network)
    ssid = text(net, 1)
    if ssid:
      bssid = text(net, 2)
      credentials = WifiCredentials(ssid=ssid, key=text(net, 3), bssid=bssid.upper() if MAC_RE.match(bssid) else "",
                                    security=int(one(net, 4, 0) or 0), ap_type=0)
  return endpoint, credentials


def parse_version_request(payload: bytes) -> tuple[int, int, Endpoint | None, dict]:
  """Major/minor, an optional projection endpoint, and head-unit identity strings."""
  fields = parse_fields(payload)
  major, minor = int(one(fields, 1, 1) or 1), int(one(fields, 2, 0) or 0)
  endpoint, head_unit = None, {}
  for number in (4, 5):
    for value in fields.get(number, []):
      if not isinstance(value, bytes):
        continue
      try:
        candidate = parse_endpoint(value)
        if candidate is not None:
          endpoint = candidate
          continue
        info = parse_fields(value)
      except ValueError:
        continue
      labels = {1: "car_make", 2: "car_model", 3: "car_year", 5: "head_unit_make", 6: "head_unit_model",
                7: "head_unit_software_build", 8: "head_unit_software_version"}
      head_unit.update({label: text(info, key) for key, label in labels.items() if text(info, key)})
  return major, minor, endpoint, head_unit


class FrameReader:
  """Incremental length-prefixed reader tolerant of fragmentation and coalescing."""

  def __init__(self):
    self.buffer = bytearray()

  def feed(self, data: bytes) -> list[tuple[int, bytes]]:
    self.buffer.extend(data)
    frames = []
    while len(self.buffer) >= 4:
      length, message_id = struct.unpack(">HH", self.buffer[:4])
      if length > MAX_FRAME:
        raise ValueError(f"Bootstrap frame of {length} bytes exceeds limit")
      if len(self.buffer) < 4 + length:
        break
      frames.append((message_id, bytes(self.buffer[4:4 + length])))
      del self.buffer[:4 + length]
    return frames


class WirelessBootstrap:
  """Runs the phone side of the handshake on a connected RFCOMM socket."""

  def __init__(self, sock, log: Callable[..., None], *, device_serial: str = "starpilot",
               version_status: int = STATUS_SUCCESS, stage_timeout: float = 20.0, start_request_delay: float = 5.0):
    self.sock = sock
    self.start_request_delay = start_request_delay
    self.log = log
    self.device_serial = device_serial
    self.version_status = version_status
    self.stage_timeout = stage_timeout
    self.reader = FrameReader()
    self.queue: list[tuple[int, bytes]] = []
    self.stage = "rfcomm"
    self.send_lock = threading.Lock()
    self.frames_seen = 0
    self.cancelled: Callable[[], bool] = lambda: False

  def send(self, message_id: int, payload: bytes = b"") -> None:
    with self.send_lock:
      self.sock.sendall(encode_frame(message_id, payload))
    if message_id not in (WIFI_PING_REQUEST, WIFI_PING_RESPONSE):
      self.log("bootstrap_tx", message=NAMES.get(message_id, message_id), bytes=len(payload))

  def next_frame(self, timeout: float) -> tuple[int, bytes]:
    deadline = time.monotonic() + timeout
    while not self.queue:
      remaining = deadline - time.monotonic()
      if remaining <= 0:
        raise BootstrapError(self.stage, "head unit did not answer in time")
      if self.cancelled():
        raise BootstrapError(self.stage, "cancelled")
      # Short slices keep Stop responsive even where closing a socket from
      # another thread does not wake a blocked recv.
      self.sock.settimeout(min(remaining, 0.5))
      try:
        data = self.sock.recv(1024)
      except TimeoutError:
        continue
      if not data:
        raise BootstrapError(self.stage, "head unit closed the RFCOMM connection")
      self.queue.extend(self.reader.feed(data))
    message_id, payload = self.queue.pop(0)
    if message_id not in (WIFI_PING_REQUEST, WIFI_PING_RESPONSE):
      # Pings are unbounded over a long Wi-Fi join; only real messages count toward the budget.
      self.frames_seen += 1
      if self.frames_seen > MAX_FRAMES:
        raise BootstrapError(self.stage, "too many bootstrap frames")
      self.log("bootstrap_rx", message=NAMES.get(message_id, message_id), bytes=len(payload))
    return message_id, payload

  def service(self, message_id: int, payload: bytes) -> bool:
    """Handle stage-independent frames; returns True when consumed."""
    if message_id == WIFI_PING_REQUEST:
      self.send(WIFI_PING_RESPONSE, payload)
      return True
    if message_id == WIFI_PING_RESPONSE:
      return True
    if message_id == WIFI_CONNECTION_REJECTION:
      reason = one(parse_fields(payload), 1, 0)
      raise BootstrapError(self.stage, f"head unit rejected the connection (reason {reason})")
    return False

  def run(self, join_wifi: Callable[[WifiCredentials], None], cancelled: Callable[[], bool] = lambda: False) -> BootstrapResult:
    self.cancelled = cancelled
    endpoint: Endpoint | None = None
    credentials: WifiCredentials | None = None
    head_unit: dict = {}
    version = None

    # Stage 1: wait for the endpoint (optionally after a version exchange).
    self.stage = "wifi_start"
    hinted: Endpoint | None = None  # endpoint carried by WifiVersionRequest, if any
    # Android Auto 17.6 asks the car to start projection 5 s after the version
    # exchange if the car has not started it; newer head units (2025 Honda) wait for it.
    start_request_at: float | None = None
    while endpoint is None:
      wait = 3.0 if hinted is not None else self.stage_timeout
      if start_request_at is not None:
        wait = min(wait, max(0.01, start_request_at - time.monotonic()))
      try:
        message_id, payload = self.next_frame(wait)
      except BootstrapError:
        if start_request_at is not None and time.monotonic() >= start_request_at:
          start_request_at = None
          self.send(WIFI_START_REQUEST)
          continue
        if hinted is None:
          raise
        endpoint = hinted  # the receiver sent its endpoint only with the version exchange
        break
      if cancelled():
        raise BootstrapError(self.stage, "cancelled")
      if self.service(message_id, payload):
        continue
      if message_id == WIFI_VERSION_REQUEST:
        major, minor, version_endpoint, info = parse_version_request(payload)
        version, head_unit = (major, minor), {**head_unit, **info}
        self.log("bootstrap_version", major=major, minor=minor, head_unit=info,
                 endpoint=version_endpoint.__dict__ if version_endpoint else None)
        self.send(WIFI_VERSION_RESPONSE, field(1, major) + field(2, minor) + field(3, self.device_serial) +
                  field(4, self.version_status))
        hinted = version_endpoint or hinted
        start_request_at = time.monotonic() + self.start_request_delay
      elif message_id == WIFI_START_REQUEST:
        parsed = parse_endpoint(payload)
        if parsed is None:
          raise BootstrapError(self.stage, "WifiStartRequest has no valid IPv4 endpoint")
        endpoint = parsed
      elif message_id == WIFI_SETUP_INFO:
        setup_endpoint, setup_credentials = parse_setup_info(payload)
        hinted = setup_endpoint or hinted
        credentials = setup_credentials or credentials
        self.log("bootstrap_setup_info", endpoint=setup_endpoint.__dict__ if setup_endpoint else None,
                 credentials=credentials.describe() if credentials else None)
      else:
        self.log("bootstrap_ignored", message=NAMES.get(message_id, message_id))
    assert endpoint is not None
    self.log("bootstrap_endpoint", ip=endpoint.ip, port=endpoint.port)

    # Stage 2: ask for the network, unless setup info already supplied it.
    if credentials is None:
      self.stage = "wifi_info"
      self.send(WIFI_INFO_REQUEST)
      while credentials is None:
        message_id, payload = self.next_frame(self.stage_timeout)
        if cancelled():
          raise BootstrapError(self.stage, "cancelled")
        if self.service(message_id, payload):
          continue
        if message_id == WIFI_INFO_RESPONSE:
          try:
            credentials = parse_info_response(payload)
          except ValueError as error:
            raise BootstrapError(self.stage, str(error)) from error
        else:
          self.log("bootstrap_ignored", message=NAMES.get(message_id, message_id))
    self.log("bootstrap_credentials", **credentials.describe())
    # Status is field 3 (fields 1/2 are ip/port); aa-proxy sends status alone to real head units.
    self.send(WIFI_START_RESPONSE, field(3, STATUS_SUCCESS))

    # Stage 3: join Wi-Fi while continuing to answer RFCOMM pings.
    self.stage = "joining_wifi"
    outcome: dict = {}

    def worker():
      try:
        join_wifi(credentials)
        outcome["ok"] = True
      except BaseException as error:  # reported to the bootstrap thread below
        outcome["error"] = error

    thread = threading.Thread(target=worker, name="aa_wifi_join", daemon=True)
    thread.start()
    while thread.is_alive():
      if cancelled():
        raise BootstrapError(self.stage, "cancelled")
      try:
        message_id, payload = self.next_frame(0.25)
      except BootstrapError as error:
        if "did not answer" in str(error):
          continue
        raise
      if not self.service(message_id, payload):
        self.log("bootstrap_ignored", message=NAMES.get(message_id, message_id))
    if "error" in outcome:
      try:
        self.send(WIFI_CONNECT_STATUS, field(1, STATUS_NETWORK_UNAVAILABLE))
      except OSError:
        pass
      error = outcome["error"]
      raise BootstrapError(self.stage, str(error)) from error
    self.send(WIFI_CONNECT_STATUS, field(1, STATUS_SUCCESS))
    self.stage = "connecting_tcp"
    return BootstrapResult(endpoint, credentials, head_unit, version)

  def keepalive(self, stop: threading.Event) -> None:
    """Keep the RFCOMM link serviced for the life of the projection session."""
    while not stop.is_set():
      try:
        message_id, payload = self.next_frame(0.5)
      except BootstrapError as error:
        if "did not answer" in str(error):
          continue
        self.log("bootstrap_link_closed", error=str(error))
        return
      except OSError as error:
        if not stop.is_set():
          self.log("bootstrap_link_closed", error=str(error))
        return
      self.frames_seen = 0  # the frame budget applies to the handshake, not the session
      try:
        if not self.service(message_id, payload):
          self.log("bootstrap_ignored", message=NAMES.get(message_id, message_id))
      except BootstrapError as error:
        self.log("bootstrap_link_closed", error=str(error))
        return
      except OSError:
        return


def describe_status(status: int | None) -> str:
  return "success" if signed(status) == 0 else f"status {signed(status)}"
