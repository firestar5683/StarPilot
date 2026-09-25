"""One-way control actions from the projected renderer to android_autod."""

from __future__ import annotations

import os
import socket


DEFAULT_CONTROL_SOCKET = "/tmp/starpilot-android-auto-control.sock"
NATIVE_FOCUS = "native_focus"
_ACTIONS = frozenset((NATIVE_FOCUS,))


class ProjectionControlSender:
  """Renderer side: best-effort requests to the projection session owner."""

  def __init__(self, path: str = DEFAULT_CONTROL_SOCKET):
    self.path = path
    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    self.sock.setblocking(False)

  def send(self, action: str) -> None:
    if action not in _ACTIONS:
      raise ValueError("Unknown projection control action")
    try:
      self.sock.sendto(action.encode(), self.path)
    except OSError:
      pass  # the session may already have left projection

  def close(self) -> None:
    self.sock.close()


class ProjectionControlReceiver:
  """android_autod side: receive bounded renderer actions without blocking video."""

  def __init__(self, path: str = DEFAULT_CONTROL_SOCKET):
    self.path = path
    try:
      os.unlink(path)
    except FileNotFoundError:
      pass
    self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
      self.sock.bind(path)
      os.chmod(path, 0o600)
      self.sock.setblocking(False)
    except BaseException:
      self.sock.close()
      raise

  def drain(self, limit: int = 8) -> list[str]:
    actions = []
    while len(actions) < limit:
      try:
        raw = self.sock.recv(64)
      except BlockingIOError:
        break
      try:
        action = raw.decode()
      except UnicodeDecodeError:
        continue
      if action in _ACTIONS:
        actions.append(action)
    return actions

  def close(self) -> None:
    self.sock.close()
    try:
      os.unlink(self.path)
    except FileNotFoundError:
      pass
