"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from jetlink import protocol as P

# Stops a corrupt length field making RxBuffer allocate gigabytes. A big
# model's request is 393 KB.
MAX_MESSAGE = 16 << 20
_PAD = bytes(P.GADGET_TX_ALIGN)


# The USB generation of each speed Linux names, as the server's link event
# shows it. The comma's hello carries the speed (Transport.link_info), because
# only its end always knows: a phone's cable is TCP over USB, and a host may
# not see the bus speed. The server maps it with this (Pinned.usbSpeedMedia).
USB_MEDIA = {'super-speed-plus': 'usb3', 'super-speed': 'usb3', 'high-speed': 'usb2',
             'full-speed': 'usb1', 'low-speed': 'usb1'}
UDC_SYSFS = '/sys/class/udc'


def udc_speed(udc: str | None = None, root: str | None = None) -> str | None:
  """The speed a device controller negotiated with its host, as Linux names it
  (super-speed, high-speed, ...), from `udc` or the first controller; None
  without one, or before a host has configured it."""
  import os
  root = root or UDC_SYSFS
  try:
    name = udc or sorted(os.listdir(root))[0]
    with open(os.path.join(root, name, 'current_speed')) as f:
      speed = f.read().strip()
  except (OSError, IndexError):
    return None
  return speed if speed in USB_MEDIA else None


def usb_link_info(kind: str, speed: str | None) -> dict:
  return {'kind': kind, **({'usb_speed': speed} if speed else {})}


class LinkError(IOError):
  """The link is unusable. Callers treat this as 'fall back to the small model'."""


class LinkTimeout(LinkError):
  """No complete message arrived in time. The stream is still in sync."""


@dataclass
class Message:
  msg_type: int
  seq: int
  flags: int
  payload: memoryview  # valid only until the next recv() on this transport


class Transport(ABC):
  """One framed, ordered, reliable message channel.

  Implementations must preserve message boundaries and ordering. recv() hands
  back a view into a reusable buffer: copy anything you need to keep.
  """

  def link_info(self) -> dict:
    """What the comma's hello says about this link: its kind (usb, cable or
    tcp) and, over USB, the speed the controller negotiated. Empty when there
    is nothing to say."""
    return {}

  @abstractmethod
  def send(self, msg_type: int, seq: int, parts=(), flags: int = 0, timeout: float | None = None) -> None:
    """Send one message. `parts` is an iterable of buffers, sent as one message."""

  def try_send(self, msg_type: int, seq: int, parts=(), timeout: float | None = None) -> bool:
    """send(), unless the link would first make the caller wait for the peer
    to take earlier messages: then False, and nothing was sent. Only a
    transport that queues its writes can tell (FfsTransport); the rest send,
    within `timeout` as send() does, and say True."""
    self.send(msg_type, seq, parts, timeout=timeout)
    return True

  @property
  def datagrams(self) -> bool:
    """Do frames the caller can do without go as datagrams? Only a phone's
    cable, once its server offered them (TcpTransport.use_datagrams)."""
    return False

  def use_datagrams(self, port: int, token: int) -> bool:
    """Send those frames to the server's UDP `port` behind its `token`, where
    the link can (TcpTransport); False and nothing changes elsewhere."""
    return False

  def stop_datagrams(self) -> None:
    """Frames on the link itself again."""

  def net_drops(self) -> int | None:
    """Packets the kernel dropped on their way in since the link came up, on a
    link that goes through the network stack (TcpTransport); None elsewhere."""
    return None

  @abstractmethod
  def recv(self, timeout: float | None = None) -> Message:
    """Block for one message. Raises LinkTimeout if `timeout` elapses."""

  @abstractmethod
  def close(self) -> None:
    ...

  def send_json(self, msg_type: int, seq: int, obj, flags: int = 0, timeout: float | None = None) -> None:
    import json
    self.send(msg_type, seq, (json.dumps(obj).encode(),), flags, timeout)

  @property
  def lendable(self) -> bool:
    """Could another process take over the IO on this link right now? Only a
    gadget can be handed over; see FfsTransport.lendable."""
    return False

  def rebind(self) -> bool:
    """Bounce the link so the peer sees it arrive again, if that means
    anything here. Only the gadget transport can; see FfsTransport.rebind."""
    return False

  def release_endpoints(self) -> bool:
    """Give up the IO without giving up the link, where the two are separable.
    Only the gadget transport can; see FfsTransport.release_endpoints."""
    return False


class RxBuffer:
  """Receive buffer for a byte stream carrying framed messages.

  Reads land in here and messages are handed out as views, so the steady state
  neither allocates nor copies. Resumable: a read that times out mid-message
  leaves the bytes in place, so a missed deadline costs a frame, not the stream.
  """

  def __init__(self, size: int = 1 << 20):
    self.buf = bytearray(size)
    self.view = memoryview(self.buf)
    self.start = 0  # first byte not yet consumed
    self.end = 0    # one past the last byte read

  @property
  def available(self) -> int:
    return self.end - self.start

  def reserve(self, need: int) -> None:
    """Guarantee room for `need` unconsumed bytes, compacting or growing."""
    if self.start and self.start + need > len(self.buf):
      # Through the bytearray, not the view: the ranges overlap and a
      # memoryview slice assignment is a memcpy. Compaction is rare.
      self.buf[:self.available] = self.buf[self.start:self.end]
      self.end -= self.start
      self.start = 0
    if need > len(self.buf):
      grown = bytearray(max(need, len(self.buf) * 2))
      grown[:self.available] = self.view[self.start:self.end]
      self.buf, self.view = grown, memoryview(grown)
      self.end -= self.start
      self.start = 0

  def writable(self) -> memoryview:
    return self.view[self.end:]

  def committed(self, n: int) -> None:
    self.end += n

  def take(self, n: int) -> memoryview:
    out = self.view[self.start:self.start + n]
    self.start += n
    return out

  def consumed(self) -> None:
    """Call once a message has been fully handed out."""
    if self.start == self.end:
      self.start = self.end = 0


class StreamTransport(Transport):
  """Framing over any ordered byte stream.

  TCP and FunctionFS are both streams, so they both need exactly this.
  Subclasses supply only the two primitives that differ.
  """

  # Pad sent messages to a multiple of this; 0 uses the one-byte PADDED rule.
  # The peer's messages always use the PADDED rule: only the gadget pads to a
  # burst, and only a USB host (the Swift server) reads what it sends. See
  # protocol.GADGET_TX_ALIGN.
  tx_align = 0
  def __init__(self, rx_size: int = 1 << 20):
    self.rx = RxBuffer(rx_size)
    self._desynced = False
    self._send_deadline: float | None = None

  def _write_timeout(self) -> float | None:
    if self._send_deadline is None:
      return None
    remaining = self._send_deadline - time.monotonic()
    if remaining <= 0:
      raise LinkError('send timed out; link abandoned')
    return remaining

  # -- primitives a subclass must provide ----------------------------------

  def _write(self, bufs: list[memoryview]) -> int:
    """Write from one or more buffers. Returns bytes written (may be partial).
    A transport that overrides send (FfsTransport) need not provide it."""
    raise NotImplementedError

  @abstractmethod
  def _read_into(self, dest: memoryview, timeout: float | None) -> int:
    """Read up to len(dest) bytes, returning how many arrived.

    May return short, including 0. Must not raise on a timeout, and must not
    drop what did arrive: that is how a stream silently desyncs.
    """

  # -- framing -------------------------------------------------------------

  def send(self, msg_type: int, seq: int, parts=(), flags: int = 0, timeout: float | None = None) -> None:
    bufs = self._frame(msg_type, seq, parts, flags)
    self._send_deadline = None if timeout is None else time.monotonic() + timeout
    try:
      while bufs:
        self._write_timeout()
        n = self._write(bufs)
        if n <= 0:
          raise LinkError("peer went away during send")
        bufs = advance(bufs, n)
    finally:
      self._send_deadline = None

  def _frame(self, msg_type: int, seq: int, parts, flags: int) -> list[memoryview]:
    """One message as the buffers that go on the wire, in order: the header,
    `parts`, then the padding. Nothing is copied."""
    # cast('B'): slicing a float32 view in advance() would step by elements
    bufs = [memoryview(p).cast('B') for p in parts]
    length = sum(b.nbytes for b in bufs)
    if self.tx_align:
      # Never a short packet in this direction; see protocol.GADGET_TX_ALIGN.
      pad = -(P.HEADER_SIZE + length) % self.tx_align
      if pad:
        bufs.append(memoryview(_PAD)[:pad])
    elif (P.HEADER_SIZE + length) % P.PACKET_MULTIPLE == 0:
      # A bulk transfer only ends on a short packet; see protocol.PACKET_MULTIPLE.
      flags |= P.Flag.PADDED
      bufs.append(memoryview(_PAD)[:1])
    bufs.insert(0, memoryview(P.pack_header(msg_type, seq, length, flags)))
    return bufs

  def _fill(self, need: int, timeout: float | None) -> None:
    """Read until `need` bytes are buffered, or the deadline passes.

    The deadline is per message, not per read, or one response could take
    several times the caller's budget. Partial reads are kept, so a missed
    deadline costs a frame and leaves the stream in sync. A deadline that has
    passed still gets one read that does not wait, so a timeout of 0 takes
    whatever has already arrived and nothing else: that is how a caller
    polls for a reply without blocking (JetlinkClient.drain).
    """
    self.rx.reserve(need)
    end = None if timeout is None else time.monotonic() + timeout
    while self.rx.available < need:
      dest = self.rx.writable()[:need - self.rx.available]
      remaining = None if end is None else max(0.0, end - time.monotonic())
      n = self._read_into(dest, remaining)
      if n:
        self.rx.committed(n)
      elif remaining == 0.0:
        raise LinkTimeout(f"only {self.rx.available} of {need} bytes arrived in time")

  def recv(self, timeout: float | None = None) -> Message:
    if self._desynced:
      raise LinkError("stream desynced; the link must be reopened")
    end = None if timeout is None else time.monotonic() + timeout
    self._fill(P.HEADER_SIZE, timeout)
    try:
      _, _, msg_type, seq, flags, length, _reserved = P.unpack_header(
        self.rx.view[self.rx.start:self.rx.start + P.HEADER_SIZE])
      if length > MAX_MESSAGE:
        raise P.ProtocolError(f"message claims {length} bytes, over the {MAX_MESSAGE} cap")
    except P.ProtocolError as e:
      # Nothing resynchronises a byte stream mid-message. Latch it and report a
      # LinkError, which callers reconnect on and modeld answers with the
      # small model; a ProtocolError is something no caller catches.
      self._desynced = True
      raise LinkError(f"protocol error, link unusable: {e}") from e
    # the remainder of the budget, so one recv cannot block for twice what it
    # was given
    pad = 1 if flags & P.Flag.PADDED else 0
    self._fill(P.HEADER_SIZE + length + pad,
               None if end is None else max(0.0, end - time.monotonic()))
    self.rx.take(P.HEADER_SIZE)
    payload = self.rx.take(length)
    self.rx.take(pad)
    self.rx.consumed()
    return Message(msg_type, seq, flags, payload)


def take(bufs: list[memoryview], n: int) -> list[memoryview]:
  """The first `n` bytes across a list of buffers, without copying."""
  out: list[memoryview] = []
  for mv in bufs:
    if n <= 0:
      break
    out.append(mv if mv.nbytes <= n else mv[:n])
    n -= out[-1].nbytes
  return out


def advance(bufs: list[memoryview], n: int) -> list[memoryview]:
  """Drop the first `n` bytes across a list of buffers, returning what is left."""
  out: list[memoryview] = []
  for mv in bufs:
    if n:
      if n >= mv.nbytes:
        n -= mv.nbytes
        continue
      mv = mv[n:]
      n = 0
    out.append(mv)
  return out
