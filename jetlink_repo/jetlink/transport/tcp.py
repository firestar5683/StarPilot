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
not allocate on the wire.
"""
from __future__ import annotations

import socket

from jetlink.transport.base import LinkError, StreamTransport, udc_speed, usb_link_info

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
  def accept(cls, srv: socket.socket) -> tuple[TcpTransport, tuple]:
    conn, addr = srv.accept()
    return cls(conn), addr

  @classmethod
  def listen_once(cls, host: str = '0.0.0.0', port: int = DEFAULT_PORT,
                  timeout: float | None = None) -> tuple[TcpTransport, tuple]:
    """Take exactly one incoming connection and stop listening: a phone that
    dials us, for the bench and parity scripts run from a Mac."""
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
    # shut down first: a close alone keeps the connection up while another
    # process holds a copy of the socket (the comma's gadget owner holds the
    # phone's dial), and the peer hears nothing until that copy goes too
    for let_go in (lambda: self.sock.shutdown(socket.SHUT_RDWR), self.sock.close):
      try:
        let_go()
      except OSError:
        pass


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
