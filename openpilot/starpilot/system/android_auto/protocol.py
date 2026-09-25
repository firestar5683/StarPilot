"""Client for android_autod's local control socket (used by the settings UI)."""

from __future__ import annotations

import json
import os
import socket
from typing import Any

ANDROID_AUTO_SOCKET_PATH = "/tmp/starpilot-android-auto.sock"
COMMAND_TIMEOUTS = {"stop": 12.0, "prepare_pairing": 20.0, "devices": 10.0, "select_receiver": 10.0, "bluetooth_action": 25.0}


class AndroidAutoClient:
  def __init__(self, socket_path: str = ANDROID_AUTO_SOCKET_PATH, timeout: float = 5.0):
    self.socket_path = socket_path
    self.timeout = timeout

  @property
  def available(self) -> bool:
    return os.path.exists(self.socket_path)

  def call(self, command: str, **payload: Any) -> dict[str, Any]:
    if not self.available:
      raise RuntimeError("Android Auto service is not running (turn on Bluetooth)")
    request = json.dumps({"command": command, **payload}, separators=(",", ":")).encode() + b"\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
      sock.settimeout(COMMAND_TIMEOUTS.get(command, self.timeout))
      sock.connect(self.socket_path)
      sock.sendall(request)
      response = bytearray()
      while not response.endswith(b"\n"):
        chunk = sock.recv(65536)
        if not chunk:
          break
        response.extend(chunk)
    if not response:
      raise RuntimeError("Android Auto service returned no response")
    result = json.loads(response)
    if not result.get("ok", False):
      raise RuntimeError(str(result.get("error", "Android Auto operation failed")))
    return result

  def status(self) -> dict[str, Any]:
    return self.call("status").get("status", {})

  def start(self) -> None:
    self.call("start")

  def stop(self) -> None:
    self.call("stop")

  def select_receiver(self, address: str, name: str = "") -> None:
    self.call("select_receiver", address=address, name=name)

  def set_view(self, view: str) -> None:
    self.call("set_view", view=view)

  def set_connection(self, connection: str) -> None:
    self.call("set_connection", connection=connection)

  def prepare_pairing(self) -> None:
    self.call("prepare_pairing")

  def set_auto_connect(self, enabled: bool) -> None:
    self.call("set_auto_connect", enabled=enabled)

  def devices(self) -> list[dict[str, Any]]:
    return list(self.call("devices").get("devices", []))
