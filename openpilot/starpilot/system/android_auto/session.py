"""Phone-side Android Auto session over any socket-compatible byte transport.

StarPilot plays the *phone* role: the head unit sends the version request, then
acts as the TLS client while this side is the TLS server presenting the phone
identity. After authentication the session discovers services, opens only the
video channel (and, best effort, the input channel so touches are acknowledged
and discarded) and streams H.264 access units with bounded acknowledgement flow.

Adapted from yummydirtx/openpilot ``tools/android_auto/{session,video,live_session}.py``
(MIT), pinned at 672a16f6183567c0ada53654f8527d97e1a483fa, whose protocol facts
were cross-checked against AACS. Transport-neutral: the donor used USB and the
desktop head unit over TCP; here the transport is the head unit's Wi-Fi TCP port.
"""

from __future__ import annotations

import math
import re
import select
import ssl
import struct
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from openpilot.starpilot.system.android_auto.touch import InputConfig, TouchEvent, TouchMapper, parse_input_config
from openpilot.starpilot.system.android_auto.wire import field, json_fields, one, parse_fields, signed

MAX_MESSAGE = 2 * 1024 * 1024
PHONE_MAX_VERSION = (6, 1)  # protocol version Android Auto 17.6 reports to newer head units
MAX_FRAGMENT_BYTES = 2 * MAX_MESSAGE
FRAGMENT_SIZE = 16000

FLAG_FIRST = 1
FLAG_LAST = 2
FLAG_CONTROL = 4
FLAG_ENCRYPTED = 8

# Control channel (0) message ids.
MSG_VERSION_REQUEST = 0x01
MSG_VERSION_RESPONSE = 0x02
MSG_SSL_HANDSHAKE = 0x03
MSG_AUTH_COMPLETE = 0x04
MSG_SERVICE_DISCOVERY_REQUEST = 0x05
MSG_SERVICE_DISCOVERY_RESPONSE = 0x06
MSG_CHANNEL_OPEN_REQUEST = 0x07
MSG_CHANNEL_OPEN_RESPONSE = 0x08
MSG_PING_REQUEST = 0x0b
MSG_PING_RESPONSE = 0x0c
MSG_SHUTDOWN_REQUEST = 0x0f
MSG_SHUTDOWN_RESPONSE = 0x10

# Media channel message ids.
AV_MEDIA_WITH_TIMESTAMP = 0x0000
AV_MEDIA_CODEC_CONFIG = 0x0001  # SPS/PPS without a timestamp, sent before the first frame like a phone's MediaCodec
AV_SETUP_REQUEST = 0x8000
AV_START_INDICATION = 0x8001
AV_STOP_INDICATION = 0x8002
AV_SETUP_RESPONSE = 0x8003
AV_MEDIA_ACK = 0x8004
VIDEO_FOCUS_REQUEST = 0x8007
VIDEO_FOCUS_INDICATION = 0x8008

# Input channel message ids.
INPUT_EVENT = 0x8001
INPUT_BINDING_REQUEST = 0x8002
INPUT_BINDING_RESPONSE = 0x8003

CODEC_H264_BP = 3
SETUP_STATUS_READY = 2
FOCUS_PROJECTED = 1
FOCUS_NATIVE = 2
FOCUS_PROJECTED_NO_INPUT = 4
FOCUS_REASON_USER_SELECTION = 4
SHUTDOWN_REASON_USER_SELECTION = 1

RESOLUTIONS = {1: (800, 480), 2: (1280, 720), 3: (1920, 1080)}
FRAME_RATES = {1: 60, 2: 30}
# Software H.264 on the comma is the constraint: prefer 720p, then 480p. 1080p
# is accepted only when nothing smaller is offered.
RESOLUTION_PREFERENCE = (2, 1, 3)

# A real phone pings periodically; answering pings is mandatory, sending them
# is harmless and keeps impatient receivers from declaring the link idle.
PING_INTERVAL = 2.0


class AuthenticationRejected(ValueError):
  pass


class PeerRequestedStop(EOFError):
  pass


START_CODE = re.compile(b"\x00\x00(?:\x00)?\x01")


def codec_config(access_unit: bytes) -> bytes:
  """The SPS and PPS NAL units of a keyframe, as Android's codec-config buffer carries them."""
  starts = list(START_CODE.finditer(access_unit))
  units = []
  for index, match in enumerate(starts):
    end = starts[index + 1].start() if index + 1 < len(starts) else len(access_unit)
    if match.end() < end and access_unit[match.end()] & 31 in (7, 8):
      units.append(b"\x00\x00\x00\x01" + access_unit[match.end():end])
  return b"".join(units)


@dataclass(frozen=True)
class VideoMode:
  channel: int
  config_index: int
  width: int
  height: int
  fps: int
  margin_width: int
  margin_height: int

  @property
  def content_width(self) -> int:
    return self.width - self.margin_width

  @property
  def content_height(self) -> int:
    return self.height - self.margin_height

  def as_dict(self) -> dict:
    return {"channel": self.channel, "config_index": self.config_index, "width": self.width, "height": self.height,
            "fps": self.fps, "margin_width": self.margin_width, "margin_height": self.margin_height}


def choose_video_mode(channels: list[dict]) -> VideoMode:
  """Pick a negotiated H.264 mode the software encoder can sustain."""
  candidates = []
  for channel in channels:
    for index, config in enumerate(channel.get("video_configs", [])):
      resolution = one(config, 1)
      codec = one(config, 10, CODEC_H264_BP)
      if resolution not in RESOLUTIONS or codec != CODEC_H264_BP:
        continue
      width, height = RESOLUTIONS[resolution]
      margin_width, margin_height = int(one(config, 3, 0) or 0), int(one(config, 4, 0) or 0)
      if not (0 <= margin_width < width and 0 <= margin_height < height):
        continue
      fps = FRAME_RATES.get(one(config, 2, 2), 30)
      mode = VideoMode(int(channel["id"]), index, width, height, fps, margin_width, margin_height)
      candidates.append((RESOLUTION_PREFERENCE.index(resolution), fps != 30, index, mode))
  if not candidates:
    raise ValueError("Head unit did not advertise a supported H.264 video mode")
  return min(candidates, key=lambda item: item[:3])[3]


class Session:
  """TLS, framing and control-channel handshake; one instance per TCP connection."""

  def __init__(self, peer, cert: str, key: str, log: Callable[..., None] | None = None, ca: str | None = None, *,
               receive_timeout: float = 3.0, send_timeout: float = 3.0, handshake_timeout: float = 15.0):
    self.peer = peer
    self._log = log
    self.receive_timeout = self._timeout(receive_timeout)
    self.send_timeout = self._timeout(send_timeout)
    self.handshake_timeout = self._timeout(handshake_timeout)
    self.authenticated = False
    self.head_unit_subject: str = ""
    self.incoming = ssl.MemoryBIO()
    self.outgoing = ssl.MemoryBIO()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert, key)
    self.peer_verification_enabled = ca is not None
    if ca is not None:
      context.load_verify_locations(cafile=ca)
      context.verify_mode = ssl.CERT_REQUIRED
    self.tls = context.wrap_bio(self.incoming, self.outgoing, server_side=True)
    self.fragments: dict[int, tuple[int, int, bytearray]] = {}
    self.bytes_sent = 0
    self.bytes_received = 0

  @staticmethod
  def _timeout(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
      raise ValueError("Message timeout must be finite and positive")
    return value

  def event(self, name: str, **values) -> None:
    if self._log is not None:
      self._log(name, **values)

  # ----------------------------------------------------------------- framing

  def send(self, channel: int, kind: int, body: bytes = b"", encrypted: bool = True, control: bool = False, *,
           deadline: float | None = None) -> None:
    """Send one whole message within one deadline; the session is invalid on failure."""
    if self.authenticated and not encrypted:
      raise ValueError("Plaintext is forbidden after authentication")
    data = struct.pack(">H", kind) + body
    if len(data) > MAX_MESSAGE:
      raise ValueError("Message exceeds size limit")
    message_deadline = time.monotonic() + self.send_timeout
    deadline = message_deadline if deadline is None else min(deadline, message_deadline)
    timed_peer = hasattr(self.peer, "gettimeout") and hasattr(self.peer, "settimeout")
    previous_timeout = self.peer.gettimeout() if timed_peer else None
    try:
      for offset in range(0, len(data), FRAGMENT_SIZE):
        chunk = data[offset:offset + FRAGMENT_SIZE]
        flags = (FLAG_FIRST if offset == 0 else 0) | (FLAG_LAST if offset + len(chunk) == len(data) else 0)
        flags |= (FLAG_ENCRYPTED if encrypted else 0) | (FLAG_CONTROL if control else 0)
        if encrypted:
          written = self.tls.write(chunk)
          if written != len(chunk):
            raise ValueError("Incomplete TLS write")
          chunk = self.outgoing.read()
        header = struct.pack(">BBH", channel, flags, len(chunk))
        if flags & 3 == FLAG_FIRST:
          header += struct.pack(">I", len(data))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
          raise TimeoutError("Android Auto message send deadline exceeded")
        if timed_peer:
          self.peer.settimeout(remaining)
        self.peer.sendall(header + chunk)
        self.bytes_sent += len(header) + len(chunk)
        if time.monotonic() >= deadline:
          raise TimeoutError("Android Auto message send deadline exceeded")
    finally:
      if timed_peer:
        self.peer.settimeout(previous_timeout)

  def receive(self, *, deadline: float | None = None) -> tuple[int, int, bytes]:
    """Read one complete message within one deadline, tolerating partial reads."""
    message_deadline = time.monotonic() + (self.receive_timeout if self.authenticated else self.handshake_timeout)
    deadline = message_deadline if deadline is None else min(deadline, message_deadline)
    timed_peer = hasattr(self.peer, "gettimeout") and hasattr(self.peer, "settimeout")
    previous_timeout = self.peer.gettimeout() if timed_peer else None

    def read_exact(size: int) -> bytes:
      data = bytearray()
      while len(data) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
          raise TimeoutError("Android Auto message receive deadline exceeded")
        if timed_peer:
          self.peer.settimeout(remaining)
        chunk = self.peer.recv(size - len(data))
        if not chunk:
          raise EOFError(f"Head unit disconnected after {len(data)}/{size} bytes")
        data.extend(chunk)
      self.bytes_received += size
      return bytes(data)

    try:
      return self._receive_message(read_exact)
    finally:
      if timed_peer:
        self.peer.settimeout(previous_timeout)

  def _receive_message(self, read_exact) -> tuple[int, int, bytes]:
    while True:
      channel, flags, size = struct.unpack(">BBH", read_exact(4))
      if flags & ~15 or size == 0:
        raise ValueError("Invalid frame header")
      if self.authenticated and not flags & FLAG_ENCRYPTED:
        raise ValueError("Plaintext is forbidden after authentication")
      segment = flags & 3
      total = struct.unpack(">I", read_exact(4))[0] if segment == FLAG_FIRST else None
      if total is not None and not 2 <= total <= MAX_MESSAGE:
        raise ValueError("Invalid fragmented message size")
      if total is not None and total + sum(item[0] for item in self.fragments.values()) > MAX_FRAGMENT_BYTES:
        raise ValueError("Aggregate fragmented message limit exceeded")
      payload = read_exact(size)
      if flags & FLAG_ENCRYPTED:
        self.incoming.write(payload)
        plain = bytearray()
        while True:
          try:
            part = self.tls.read(65536)
            if not part:
              raise EOFError("TLS closed")
            plain.extend(part)
          except ssl.SSLWantReadError:
            break
        payload = bytes(plain)
      if segment == 3:
        if channel in self.fragments:
          raise ValueError("Full message interrupted fragment sequence")
      elif segment == FLAG_FIRST:
        if channel in self.fragments or total is None or len(payload) >= total:
          raise ValueError("Invalid first fragment")
        self.fragments[channel] = (total, flags & 12, bytearray(payload))
        continue
      else:
        if channel not in self.fragments:
          raise ValueError("Continuation without first fragment")
        expected, mode, assembled = self.fragments[channel]
        if mode != flags & 12 or len(assembled) + len(payload) > expected:
          raise ValueError("Inconsistent fragment sequence")
        assembled.extend(payload)
        if segment == 0:
          continue
        del self.fragments[channel]
        if len(assembled) != expected:
          raise ValueError("Incorrect assembled message size")
        payload = bytes(assembled)
      if len(payload) < 2:
        raise ValueError("Missing message type")
      kind = struct.unpack(">H", payload[:2])[0]
      return channel, kind, payload[2:]

  # --------------------------------------------------------------- handshake

  def authenticate(self) -> None:
    # Some wireless adapters send a control keepalive before their version request.
    # A pong keeps the transport alive; version, TLS and certificate checks remain mandatory.
    deadline = time.monotonic() + self.handshake_timeout
    pings = 0
    while True:
      channel, kind, data = self.receive(deadline=deadline)
      if channel != 0 or kind != MSG_PING_REQUEST:
        break
      pings += 1
      if pings > 8 or len(data) > 64:
        raise ValueError('Excessive pre-version Android Auto keepalive')
      fields = parse_fields(data)
      timestamps = fields.get(1, [])
      if len(timestamps) > 1 or timestamps and not isinstance(timestamps[0], int):
        raise ValueError('Invalid pre-version Android Auto ping timestamp')
      timestamp = timestamps[0] if timestamps else 0
      self.send(0, MSG_PING_RESPONSE, field(1, timestamp), encrypted=False, deadline=deadline)
      self.event('pre_version_ping', count=pings)
      if time.monotonic() >= deadline:
        raise TimeoutError('Android Auto version request deadline exceeded')
    if channel != 0 or kind != MSG_VERSION_REQUEST or len(data) != 4:
      raise ValueError(f"Expected version request; got {channel}/{kind:#x}")
    major, minor = struct.unpack(">HH", data)
    if major < 1:
      raise ValueError(f"Unsupported Android Auto protocol version {major}.{minor}")
    # Android Auto 17.6 answers any request above 1.7 with its own maximum and success;
    # newer head units (e.g. 2025 Honda, 4.1) hang up on anything else.
    reply = (1, min(minor, 5)) if (major, minor) <= (1, 7) else PHONE_MAX_VERSION
    self.event("version", major=major, minor=minor, reply=f"{reply[0]}.{reply[1]}")
    self.send(0, MSG_VERSION_RESPONSE, struct.pack(">HHH", *reply, 0), encrypted=False)
    while True:
      channel, kind, data = self.receive()
      if channel != 0 or kind != MSG_SSL_HANDSHAKE:
        raise ValueError(f"Expected TLS handshake; got {channel}/{kind:#x}")
      self.incoming.write(data)
      done = False
      try:
        self.tls.do_handshake()
        done = True
      except ssl.SSLWantReadError:
        pass
      response = self.outgoing.read()
      if response:
        self.send(0, MSG_SSL_HANDSHAKE, response, encrypted=False)
      if done:
        break
    self.event("tls_established", version=self.tls.version(), cipher=self.tls.cipher()[0])
    if self.peer_verification_enabled:
      peer_cert = self.tls.getpeercert() or {}
      organizations = [value for rdn in peer_cert.get("subject", ()) for name, value in rdn if name == "organizationName"]
      if any(name in ("CarService", "Google Automotive Link") for name in organizations):
        raise ValueError("Head unit presented a phone or CA identity")
      self.head_unit_subject = ", ".join(f"{name}={value}" for rdn in peer_cert.get("subject", ()) for name, value in rdn)
      self.event("head_unit_verified", subject=self.head_unit_subject, expires=peer_cert.get("notAfter", ""))
    channel, kind, data = self.receive()
    if channel != 0 or kind != MSG_AUTH_COMPLETE:
      raise ValueError(f"Expected authentication status; got {channel}/{kind:#x}")
    status = signed(one(parse_fields(data), 1))
    if status is None or not isinstance(status, int):
      raise ValueError("Missing or invalid authentication status")
    if status != 0:
      self.event("authentication_rejected", status=status)
      raise AuthenticationRejected(f"Head unit rejected the phone certificate (status {status})")
    self.authenticated = True
    self.event("authenticated", version=self.tls.version(), cipher=self.tls.cipher()[0])

  def discover(self, device_name: str, device_brand: str) -> list[dict]:
    self.send(0, MSG_SERVICE_DISCOVERY_REQUEST, field(4, device_name) + field(5, device_brand))
    raw = self.wait_for(0, MSG_SERVICE_DISCOVERY_RESPONSE)
    response = parse_fields(raw)
    channels = []
    for descriptor in response.get(1, []):
      if not isinstance(descriptor, bytes):
        continue
      fields = parse_fields(descriptor)
      item: dict = {"id": one(fields, 1), "services": sorted(number for number in fields if number != 1)}
      av = one(fields, 3)
      if isinstance(av, bytes):
        media = parse_fields(av)
        item["media_type"] = one(media, 1)
        item["video_configs"] = [parse_fields(c) for c in media.get(4, []) if isinstance(c, bytes)]
      if isinstance(one(fields, 4), bytes):
        item["input"] = True
        try:
          item["input_config"] = parse_input_config(one(fields, 4))
        except ValueError:
          item["input_config"] = InputConfig()
      channels.append(item)
    head_unit = {number: [value.decode("utf-8", "replace") for value in values if isinstance(value, bytes)]
                 for number, values in response.items() if number in (2, 3, 4, 5, 6, 7, 8, 9)}
    self.event("discovered", channels=[{k: (json_fields_list(v) if k == "video_configs" else str(v) if k == "input_config" else v)
                                        for k, v in ch.items()} for ch in channels],
               head_unit={k: v for k, v in head_unit.items() if v})
    return channels

  def wait_for(self, channel: int, kind: int, timeout: float = 10.0) -> bytes:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
      ch, message, data = self.receive()
      if ch == channel and message == kind:
        return data
      self.dispatch(ch, message, data, expected=f"{channel}/{kind:#x}")
    raise TimeoutError(f"Head unit did not send {channel}/{kind:#x}")

  def dispatch(self, channel: int, kind: int, data: bytes, expected: str) -> None:
    """Handle a message that arrived while waiting for another one."""
    if channel == 0 and kind == MSG_PING_REQUEST:
      self.send(0, MSG_PING_RESPONSE, field(1, one(parse_fields(data), 1, 0)))
    elif not (channel == 0 and kind == MSG_PING_RESPONSE):
      self.event("unexpected_while_waiting", channel=channel, kind=kind, expected=expected, bytes=len(data))


def json_fields_list(configs: list[dict]) -> list[dict]:
  return [json_fields(config) for config in configs]


class ProjectionSession(Session):
  """Video projection with focus epochs, bounded ACK window and mandatory resume keyframes."""

  ACK_TIMEOUT = 1.5  # Wi-Fi adds jitter compared to the donor's USB 500 ms budget.
  MAX_WINDOW = 2

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.channels: list[dict] = []
    self.mode: VideoMode | None = None
    self.window = 1
    self.focused = False
    self.allow_projection = True
    self.media_started = False
    self.needs_keyframe = True
    self.session_id = 1
    self.retired_sessions: deque[int] = deque(maxlen=8)
    self.pending: deque[float] = deque()
    self.unacked = 0
    self.acked = 0
    self.frames_sent = 0
    self.focus_epoch = 0
    self.max_ack_seconds = 0.0
    self.config_ack_slack = 0  # codec-config messages a head unit may acknowledge like frames
    self.input_channel: int | None = None
    self.input_events = 0
    self.touch: TouchMapper | None = None
    self.touch_events: deque[TouchEvent] = deque(maxlen=128)
    self.last_ping_sent = 0.0
    self.last_rx = time.monotonic()
    self.ping_responses = 0

  # ------------------------------------------------------------------- setup

  def start(self, device_name: str, device_brand: str) -> VideoMode:
    self.channels = self.discover(device_name, device_brand)
    self.mode = choose_video_mode(self.channels)
    self.open_video()
    self.open_input()
    self.request_projection()
    return self.mode

  def open_video(self) -> None:
    mode = self.mode
    assert mode is not None
    self.send(mode.channel, MSG_CHANNEL_OPEN_REQUEST, field(1, 0) + field(2, mode.channel), control=True)
    opened = parse_fields(self.wait_for(mode.channel, MSG_CHANNEL_OPEN_RESPONSE))
    if signed(one(opened, 1)) != 0:
      raise ValueError(f"Head unit rejected opening the video channel: {json_fields(opened)}")
    self.send(mode.channel, AV_SETUP_REQUEST, field(1, CODEC_H264_BP))
    setup = parse_fields(self.wait_for(mode.channel, AV_SETUP_RESPONSE))
    window = int(one(setup, 2, 0) or 0)
    if one(setup, 1) != SETUP_STATUS_READY or not 1 <= window <= 32:
      raise ValueError(f"Unsupported video setup response: {json_fields(setup)}")
    configs = setup.get(3, [])
    if configs and mode.config_index not in configs:
      raise ValueError(f"Head unit did not accept video configuration {mode.config_index}: {json_fields(setup)}")
    self.window = min(window, self.MAX_WINDOW)
    self.event("video_setup", mode=mode.as_dict(), window=window, used_window=self.window)

  def open_input(self) -> None:
    """Open the touch/key channel so input is acknowledged; failures are not fatal."""
    channel = next((ch for ch in self.channels if ch.get("input")), None)
    if channel is None:
      return
    try:
      self.send(channel["id"], MSG_CHANNEL_OPEN_REQUEST, field(1, 0) + field(2, channel["id"]), control=True)
      opened = parse_fields(self.wait_for(channel["id"], MSG_CHANNEL_OPEN_RESPONSE, timeout=3.0))
      if signed(one(opened, 1)) != 0:
        raise ValueError("channel open rejected")
      self.input_channel = channel["id"]
      config = channel.get("input_config") or InputConfig()
      # Echo the advertised keycodes, as a phone does; touch needs no binding.
      self.send(channel["id"], INPUT_BINDING_REQUEST, b"".join(field(1, code) for code in config.keycodes))
      if self.mode is not None:
        self.touch = TouchMapper(config, self.mode.width, self.mode.height, self.mode.margin_width, self.mode.margin_height)
      self.event("input_opened", channel=channel["id"], keycodes=len(config.keycodes),
                 touch=f"{config.touch_width}x{config.touch_height}")
    except (TimeoutError, ValueError) as error:
      self.event("input_unavailable", error=str(error))

  def request_projection(self) -> None:
    """Ask for display focus; the Mazda donor needed this, DHU grants it unsolicited."""
    assert self.mode is not None
    self.allow_projection = True
    self.send(self.mode.channel, VIDEO_FOCUS_REQUEST, field(2, FOCUS_PROJECTED) + field(3, FOCUS_REASON_USER_SELECTION))

  def dispatch(self, channel: int, kind: int, data: bytes, expected: str) -> None:
    # Once video is set up, an early focus grant or ping must not be lost while
    # waiting for the input channel.
    if self.mode is not None and not (channel == 0 and kind in (MSG_VERSION_REQUEST, MSG_SSL_HANDSHAKE)):
      self.handle(channel, kind, data)
    else:
      super().dispatch(channel, kind, data, expected)

  # --------------------------------------------------------------- streaming

  def pump(self, timeout: float) -> bool:
    """Handle at most one incoming message; returns True when one was handled."""
    now = time.monotonic()
    if self.authenticated and now - self.last_ping_sent >= PING_INTERVAL:
      self.last_ping_sent = now
      self.send(0, MSG_PING_REQUEST, field(1, time.monotonic_ns() // 1000))
    if not select.select([self.peer], [], [], max(0.0, timeout))[0]:
      return False
    self.handle(*self.receive())
    self.last_rx = time.monotonic()
    return True

  def handle(self, channel: int, kind: int, data: bytes) -> None:
    try:
      fields = parse_fields(data) if kind not in (AV_MEDIA_WITH_TIMESTAMP, 1) else {}
    except ValueError:
      fields = {}  # non-protobuf payload on a channel this sender never opened
    mode = self.mode
    if channel == 0:
      if kind == MSG_PING_REQUEST:
        self.send(0, MSG_PING_RESPONSE, field(1, one(fields, 1, 0)))
      elif kind == MSG_PING_RESPONSE:
        self.ping_responses += 1
      elif kind == MSG_SHUTDOWN_REQUEST:
        self.send(0, MSG_SHUTDOWN_RESPONSE)
        self.event("peer_requested_shutdown", reason=one(fields, 1))
        raise PeerRequestedStop(f"Head unit ended projection (reason {one(fields, 1)})")
      else:
        self.event("control_ignored", kind=kind, fields=json_fields(fields))
    elif mode is not None and channel == mode.channel:
      if kind == VIDEO_FOCUS_INDICATION:
        self._handle_focus(one(fields, 1), one(fields, 2, 0))
      elif kind == AV_MEDIA_ACK:
        self._handle_ack(one(fields, 1), int(one(fields, 2, 0) or 0))
      else:
        self.event("video_ignored", kind=kind, fields=json_fields(fields))
    elif channel == self.input_channel:
      if kind == INPUT_EVENT:
        self.input_events += 1
        if self.touch is not None and self.focused:
          try:
            self.touch_events.extend(self.touch.decode(data))
          except ValueError as error:
            self.event("input_invalid", error=str(error))
      elif kind == INPUT_BINDING_RESPONSE:
        self.event("input_bound", status=signed(one(fields, 1, 0)))
      else:
        self.event("input_ignored", kind=kind)
    else:
      self.event("channel_ignored", channel=channel, kind=kind, bytes=len(data))

  def _handle_focus(self, focus, unsolicited) -> None:
    was_focused = self.focused
    granted = focus in (FOCUS_PROJECTED, FOCUS_PROJECTED_NO_INPUT)
    self.focused = granted and self.allow_projection
    self.event("video_focus", focus=focus, unsolicited=unsolicited, focused=self.focused)
    if was_focused and not self.focused and self.touch is not None:
      self.touch_events.extend(self.touch.reset())
    if self.focused and not was_focused:
      assert self.mode is not None
      if self.media_started:
        # A new media epoch: retire in-flight frames from the previous one so
        # late ACKs are harmless, and never continue an old inter-frame chain.
        self.retired_sessions.append(self.session_id)
        self.session_id += 1
        self.unacked = 0
        self.pending.clear()
        self.config_ack_slack = 0
      self.media_started = True
      self.needs_keyframe = True
      self.focus_epoch += 1
      self.send(self.mode.channel, AV_START_INDICATION, field(1, self.session_id) + field(2, self.mode.config_index))

  def _handle_ack(self, sid, count: int) -> None:
    if sid in self.retired_sessions:
      return
    # Head units may acknowledge codec config like a frame: under the current
    # session (as an extra count) or, like the DHU, under session 0.
    if sid != self.session_id and 0 < count <= self.config_ack_slack:
      self.config_ack_slack -= count
      return
    excess = count - self.unacked
    if sid == self.session_id and 0 < excess <= self.config_ack_slack:
      self.config_ack_slack -= excess
      count -= excess
      if count == 0:
        return
    if sid != self.session_id or not 0 < count <= self.unacked or count > len(self.pending):
      raise ValueError(f"Invalid video acknowledgement session={sid} count={count} pending={self.unacked}")
    now = time.monotonic()
    for _ in range(count):
      self.max_ack_seconds = max(self.max_ack_seconds, now - self.pending.popleft())
    self.unacked -= count
    self.acked += count

  def can_send(self) -> bool:
    return self.focused and self.unacked < self.window

  def check_progress(self, now: float | None = None) -> None:
    now = time.monotonic() if now is None else now
    if self.focused and self.pending and now - self.pending[0] > self.ACK_TIMEOUT:
      raise TimeoutError(f"Video acknowledgement older than {self.ACK_TIMEOUT:.1f} s")
    # Only a receiver known to answer pings can be declared dead by silence; for
    # others a lost link surfaces as a socket error or a dropped Wi-Fi lease.
    if self.ping_responses and now - self.last_rx > 15.0:
      raise TimeoutError("Head unit stopped answering for 15 s")

  def send_frame(self, data: bytes, timestamp_us: int, *, keyframe: bool) -> None:
    if not self.can_send():
      raise RuntimeError("Cannot send without video focus and window credit")
    if self.needs_keyframe and not keyframe:
      raise ValueError("A fresh media epoch must start with SPS/PPS and an IDR frame")
    assert self.mode is not None
    if self.needs_keyframe:
      config = codec_config(data)
      if config:
        self.send(self.mode.channel, AV_MEDIA_CODEC_CONFIG, config)
        self.config_ack_slack += 1
    self.send(self.mode.channel, AV_MEDIA_WITH_TIMESTAMP, struct.pack(">Q", timestamp_us) + data)
    self.needs_keyframe = False
    self.pending.append(time.monotonic())
    self.unacked += 1
    self.frames_sent += 1

  def shutdown(self, timeout: float = 2.0) -> None:
    self.send(0, MSG_SHUTDOWN_REQUEST, field(1, SHUTDOWN_REASON_USER_SELECTION))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
      if not select.select([self.peer], [], [], 0.05)[0]:
        continue
      channel, kind, data = self.receive()
      if channel == 0 and kind == MSG_SHUTDOWN_RESPONSE:
        self.event("shutdown_acknowledged")
        return
      if channel == 0 and kind == MSG_SHUTDOWN_REQUEST:
        self.send(0, MSG_SHUTDOWN_RESPONSE)
        return
      if self.mode is not None and channel == self.mode.channel and kind in (VIDEO_FOCUS_INDICATION, AV_MEDIA_ACK):
        continue
      if channel == 0 and kind == MSG_PING_REQUEST:
        self.send(0, MSG_PING_RESPONSE, field(1, one(parse_fields(data), 1, 0)))
    raise TimeoutError("Head unit did not acknowledge shutdown")

  def stats(self) -> dict:
    return {"frames_sent": self.frames_sent, "frames_acked": self.acked, "pending": self.unacked,
            "focus_epoch": self.focus_epoch, "focused": self.focused, "max_ack_ms": round(self.max_ack_seconds * 1000),
            "input_events": self.input_events, "touch": self.touch is not None}
