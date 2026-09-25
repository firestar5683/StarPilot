"""Bounded local replay operations shared by native UI and Galaxy."""

from __future__ import annotations

import json
from pathlib import Path
import socket
import struct
import time

from openpilot.starpilot.storage import starpilot_storage_root


MAX_REQUEST = 4096
MAX_RESPONSE = 262144


def replay_root() -> Path:
  return starpilot_storage_root() / 'replay'


def socket_path() -> Path:
  return replay_root() / 'owner.sock'


class ReplayUnavailable(RuntimeError):
  pass


def _unique(pairs):
  value = {}
  for key, item in pairs:
    if key in value:
      raise ValueError('duplicate field')
    value[key] = item
  return value


def parse(raw: bytes, limit: int) -> dict:
  if len(raw) > limit:
    raise ValueError('message exceeds limit')
  value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite value')))
  if type(value) is not dict:
    raise ValueError('message must be an object')
  return value


def encode(value: dict, limit: int) -> bytes:
  raw = json.dumps(value, separators=(',', ':'), allow_nan=False).encode('utf-8')
  if not raw or len(raw) > limit:
    raise ValueError('message exceeds limit')
  return struct.pack('!I', len(raw)) + raw


def receive(sock: socket.socket, limit: int, timeout: float) -> dict:
  deadline = time.monotonic() + timeout

  def exact(size):
    output = bytearray()
    while len(output) < size:
      remaining = deadline - time.monotonic()
      if remaining <= 0:
        raise ReplayUnavailable('Replay response timed out')
      sock.settimeout(remaining)
      chunk = sock.recv(size - len(output))
      if not chunk:
        raise ReplayUnavailable('Replay connection closed')
      output.extend(chunk)
    return bytes(output)

  length = struct.unpack('!I', exact(4))[0]
  if not 0 < length <= limit:
    raise ValueError('message size invalid')
  return parse(exact(length), limit)


def request_operation(request: dict, *, socket_path: Path | None = None, timeout: float = 2.0) -> dict:
  if type(request) is not dict or type(timeout) not in (int, float) or not 0 < timeout <= 4:
    raise ReplayUnavailable('Invalid replay operation')
  path = replay_root() / 'owner.sock' if socket_path is None else Path(socket_path)
  try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
      peer.settimeout(timeout)
      peer.connect(str(path))
      peer.sendall(encode(request, MAX_REQUEST))
      response = receive(peer, MAX_RESPONSE, timeout)
  except (OSError, ValueError, TypeError, UnicodeError, RecursionError) as error:
    raise ReplayUnavailable('Replay owner is unavailable') from error
  if (type(response.get('ok')) is not bool or
      set(response) != ({'ok', 'result'} if response['ok'] else {'ok', 'error'}) or
      type(response.get('result' if response['ok'] else 'error')) is not dict):
    raise ReplayUnavailable('Replay response is invalid')
  return response
