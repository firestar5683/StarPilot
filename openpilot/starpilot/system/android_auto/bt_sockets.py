"""Classic Bluetooth client sockets (L2CAP for SDP, RFCOMM for the wireless bootstrap).

Python exposes ``AF_BLUETOOTH`` only when it was built with BlueZ headers. Distro
builds are; some standalone builds are not. The fallback creates the same kernel
sockets through libc and wraps the descriptor, so the rest of the code sees an
ordinary ``socket.socket`` either way. Linux only.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import os
import re
import select
import socket
import struct
import time

AF_BLUETOOTH = 31
BTPROTO_L2CAP = 0
BTPROTO_RFCOMM = 3
ADDRESS_RE = re.compile(r"^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$")


def normalize_address(address: str) -> str:
  address = address.strip().upper()
  if not ADDRESS_RE.match(address):
    raise ValueError(f"Invalid Bluetooth address: {address!r}")
  return address


def _bdaddr(address: str) -> bytes:
  return bytes(reversed(bytes.fromhex(address.replace(":", ""))))


def _sockaddr(proto: int, address: str, port: int) -> bytes:
  if proto == BTPROTO_RFCOMM:
    # struct sockaddr_rc { sa_family_t; bdaddr_t; uint8_t channel; }
    return struct.pack("<H6sBx", AF_BLUETOOTH, _bdaddr(address), port)
  # struct sockaddr_l2 { sa_family_t; __le16 psm; bdaddr_t; __le16 cid; uint8_t bdaddr_type; }
  return struct.pack("<HH6sHBx", AF_BLUETOOTH, port, _bdaddr(address), 0, 0)


def _native(proto: int, kind: int, address: str, port: int, timeout: float) -> socket.socket:
  sock = socket.socket(socket.AF_BLUETOOTH, kind, proto)
  try:
    sock.settimeout(timeout)
    sock.connect((address, port))
    return sock
  except BaseException:
    sock.close()
    raise


def _libc_connect(proto: int, kind: int, address: str, port: int, timeout: float) -> socket.socket:
  libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
  fd = libc.socket(AF_BLUETOOTH, kind | getattr(socket, "SOCK_NONBLOCK", 0o4000) | getattr(socket, "SOCK_CLOEXEC", 0o2000000), proto)
  if fd < 0:
    err = ctypes.get_errno()
    raise OSError(err, f"Bluetooth socket unavailable: {os.strerror(err)}")
  try:
    raw = _sockaddr(proto, address, port)
    buffer = ctypes.create_string_buffer(raw, len(raw))
    if libc.connect(fd, buffer, len(raw)) != 0:
      err = ctypes.get_errno()
      if err not in (errno.EINPROGRESS, errno.EAGAIN):
        raise OSError(err, os.strerror(err))
      poller = select.poll()
      poller.register(fd, select.POLLOUT)
      if not poller.poll(max(1, int(timeout * 1000))):
        raise TimeoutError(f"Bluetooth connect to {address} timed out")
      result = ctypes.c_int(0)
      size = ctypes.c_uint(ctypes.sizeof(result))
      libc.getsockopt(fd, socket.SOL_SOCKET, socket.SO_ERROR, ctypes.byref(result), ctypes.byref(size))
      if result.value:
        raise OSError(result.value, os.strerror(result.value))
    sock = socket.socket(fileno=fd)
    fd = -1
    sock.settimeout(timeout)
    return sock
  finally:
    if fd >= 0:
      os.close(fd)


def _connect(proto: int, kind: int, address: str, port: int, timeout: float) -> socket.socket:
  address = normalize_address(address)
  if hasattr(socket, "AF_BLUETOOTH") and hasattr(socket, "BTPROTO_RFCOMM"):
    return _native(proto, kind, address, port, timeout)
  return _libc_connect(proto, kind, address, port, timeout)


def connect_l2cap(address: str, psm: int, timeout: float = 10.0) -> socket.socket:
  return _connect(BTPROTO_L2CAP, socket.SOCK_SEQPACKET, address, psm, timeout)


def connect_rfcomm(address: str, channel: int, timeout: float = 15.0) -> socket.socket:
  if not 1 <= channel <= 30:
    raise ValueError(f"Invalid RFCOMM channel {channel}")
  return _connect(BTPROTO_RFCOMM, socket.SOCK_STREAM, address, channel, timeout)


def settle(seconds: float) -> None:
  """Some kernels report L2CAP connected before writes are accepted (ENOTCONN)."""
  time.sleep(seconds)
