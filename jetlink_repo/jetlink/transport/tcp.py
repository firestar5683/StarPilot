"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

TCP transport, for a phone over the cable, and for testing and benchmarking.

Over the USB cable it rides the CDC-NCM interface of the comma's composite
gadget: the comma is 192.168.60.1 and a phone dials it. A Jetson or a Mac uses
the vendor interface instead. See docs/transport.md.

One sendmsg per message (header and body in one segment train, NODELAY set)
and reads straight into the reusable receive buffer, so the steady state does
not allocate on the wire. Over the cable, frames can go as UDP datagrams
instead (use_datagrams, protocol.DATAGRAM_MAGIC); everything else stays here.
"""
from __future__ import annotations

import logging
import socket
from collections.abc import Iterator

from jetlink import protocol as P
from jetlink.transport.base import LinkError, StreamTransport, advance, take, udc_speed, usb_link_info

log = logging.getLogger('jetlink.tcp')

DEFAULT_PORT = 5599
# The comma's end of the USB network link a phone dials (jetlink-root.sh gadget --ios).
# A connection whose local address is this one is a cable, not a LAN.
CABLE_ADDRESS = '192.168.60.1'


class TcpTransport(StreamTransport):
  def __init__(self, sock: socket.socket):
    super().__init__()
    self.sock = sock
    self._timeout: float | None = -1.0  # force the first settimeout
    _tune(sock)
    # (socket connected to the server's frame port, its token); see use_datagrams
    self._udp: tuple[socket.socket, int] | None = None
    self._drops_at = _softnet_dropped()

  def on_the_cable(self) -> bool:
    """Is either end the comma's cable address? Then this is a phone's USB
    cable: from the comma the local end, from a server the peer. Swift's
    LinkMedium(tcpPeer:) is the same rule."""
    try:
      return CABLE_ADDRESS in (self.sock.getsockname()[0], self.sock.getpeername()[0])
    except OSError:
      return False

  def link_info(self) -> dict:
    return usb_link_info('cable', udc_speed()) if self.on_the_cable() else {'kind': 'tcp'}

  def net_drops(self) -> int:
    """Every CPU's receive backlog drops since this link came up
    (/proc/net/softnet_stat): a receive core starved of time shows here
    before anywhere else. -1 where it cannot be read."""
    now = _softnet_dropped()
    return -1 if now < 0 or self._drops_at < 0 else now - self._drops_at

  # -- frames as datagrams ---------------------------------------------------

  def use_datagrams(self, port: int, token: int) -> bool:
    """Send frames the caller can do without (send_datagrams) to the peer's
    UDP `port` from now on, behind the server's `token`: what its HELLO_RESP
    offers over the cable. False, and nothing changes, anywhere else: off the
    cable a lost datagram has more than a USB link between it and the phone.
    Blocking: the 4 MB send buffer takes a frame whole."""
    self.stop_datagrams()
    if not self.on_the_cable():
      return False
    try:
      udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      udp.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 << 20)
      udp.connect((self.sock.getpeername()[0], port))
    except OSError as e:
      log.warning("jetlink: no frame datagrams to port %d (%s); frames stay on TCP", port, e)
      return False
    self._udp = (udp, token)
    return True

  def stop_datagrams(self) -> None:
    udp, self._udp = self._udp, None
    if udp is not None:
      udp[0].close()

  @property
  def datagrams(self) -> bool:
    return self._udp is not None

  def send_datagrams(self, msg_type: int, seq: int, parts=(), flags: int = 0) -> None:
    """The message as `datagrams`, one sendmsg each, once use_datagrams took
    an offer. A send the kernel refuses (the phone's server gone) fails the
    link, as a refused send on the stream does."""
    udp, token = self._udp
    try:
      for piece in datagrams(self._frame(msg_type, seq, parts, flags), token, seq):
        udp.sendmsg(piece)
    except OSError as e:
      raise LinkError(f"frame datagrams failed: {e}") from e

  @classmethod
  def connect(cls, host: str, port: int = DEFAULT_PORT, timeout: float = 5.0) -> TcpTransport:
    return cls(socket.create_connection((host, port), timeout=timeout))

  @classmethod
  def listen(cls, host: str = '0.0.0.0', port: int = DEFAULT_PORT, backlog: int = 1) -> socket.socket:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(backlog)
    return srv

  @classmethod
  def listen_once(cls, host: str = '0.0.0.0', port: int = DEFAULT_PORT,
                  timeout: float | None = None) -> tuple[TcpTransport, tuple]:
    """Take exactly one incoming connection and stop listening: a phone that
    dials us, for the benchmark and parity scripts run from a Mac."""
    srv = cls.listen(host, port)
    try:
      srv.settimeout(timeout)
      try:
        conn, addr = srv.accept()
      except TimeoutError as e:
        raise LinkError(f"nobody dialed {host}:{port} in {timeout:.0f}s") from e
      except OSError as e:
        raise LinkError(f"accept on {host}:{port} failed: {e}") from e
    finally:
      srv.close()
    return cls(conn), addr

  def _set_timeout(self, timeout: float | None) -> None:
    if timeout != self._timeout:
      self.sock.settimeout(timeout)
      self._timeout = timeout

  def _write(self, bufs: list[memoryview]) -> int:
    # sendmsg keeps the header and a 393 KB body in one syscall, so with NODELAY
    # they go out as one segment train.
    self._set_timeout(self._write_timeout())
    try:
      return self.sock.sendmsg(bufs)
    except OSError as e:
      raise LinkError(f"send failed: {e}") from e

  def _read_into(self, dest: memoryview, timeout: float | None) -> int:
    self._set_timeout(timeout)
    try:
      n = self.sock.recv_into(dest, dest.nbytes)
    except (TimeoutError, BlockingIOError):
      # nothing in time, or nothing at all on a read that may not wait (a
      # timeout of 0 makes the socket non-blocking); _fill owns the deadline
      return 0
    except OSError as e:
      raise LinkError(f"recv failed: {e}") from e
    if n == 0:
      raise LinkError("peer closed the connection")
    return n

  def close(self) -> None:
    self.stop_datagrams()
    # shut down first: a close alone keeps the connection up while another
    # process holds a copy of the socket (the comma's gadget owner holds the
    # phone's dial), and the peer hears nothing until that copy goes too
    for let_go in (lambda: self.sock.shutdown(socket.SHUT_RDWR), self.sock.close):
      try:
        let_go()
      except OSError:
        pass


def _softnet_dropped(path: str = '/proc/net/softnet_stat') -> int:
  """The kernel's receive backlog drops, all CPUs: the second column, in hex."""
  try:
    with open(path) as f:
      return sum(int(line.split()[1], 16) for line in f if line.strip())
  except (OSError, ValueError, IndexError):
    return -1


def datagrams(bufs: list[memoryview], token: int, seq: int) -> Iterator[list]:
  """A message's stream bytes `bufs` as protocol.datagram_pieces, each its
  header and views into `bufs`. The header's buffer is reused: send or copy
  each datagram before taking the next."""
  total = sum(b.nbytes for b in bufs)
  header = bytearray(P.DATAGRAM_HEADER_SIZE)
  for offset, size in P.datagram_pieces(total):
    P.pack_datagram_header_into(header, token, seq, offset, total)
    yield [header, *take(advance(bufs, offset), size)]


def _tune(sock: socket.socket) -> None:
  # NODELAY is the one that matters: without it the header and the body can be
  # split across an RTT. Guarded anyway; a transport must not die in setsockopt.
  for level, opt, value in ((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),
                            (socket.SOL_SOCKET, socket.SO_SNDBUF, 4 << 20),
                            (socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20),
                            (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)):
    try:
      sock.setsockopt(level, opt, value)
    except OSError:
      pass
