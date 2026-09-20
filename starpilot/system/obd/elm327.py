import socket
import threading
import time

from typing import Any


DEFAULT_COMMAND_TIMEOUT = 5.0
DEFAULT_CONNECT_TIMEOUT = 10.0
ELM_IDENTITY_MARKERS = ("ELM", "STN", "OBD")


class RFCOMMTransport:
  def __init__(self, connect_timeout: float = DEFAULT_CONNECT_TIMEOUT):
    self.connect_timeout = connect_timeout
    self.channel: int | None = None
    self._socket: socket.socket | None = None

  def connect(self, mac: str) -> None:
    self.close()
    address_family = getattr(socket, "AF_BLUETOOTH", None)
    protocol = getattr(socket, "BTPROTO_RFCOMM", None)
    if address_family is None or protocol is None:
      raise RuntimeError("Native Bluetooth RFCOMM sockets are unavailable")
    channels = tuple(dict.fromkeys((self.channel, 1, 2))) if self.channel is not None else (1, 2)
    last_error: OSError | None = None
    for channel in channels:
      sock = socket.socket(address_family, socket.SOCK_STREAM, protocol)
      try:
        sock.settimeout(self.connect_timeout)
        sock.connect((mac, channel))
      except OSError as error:
        last_error = error
        sock.close()
        continue
      self._socket = sock
      self.channel = channel
      return
    raise ConnectionError(f"Unable to connect to {mac} on RFCOMM channels 1 or 2") from last_error

  def close(self) -> None:
    sock = self._socket
    self._socket = None
    if sock is not None:
      sock.close()

  def read(self, size: int = 4096, timeout: float | None = None) -> bytes:
    if self._socket is None:
      raise ConnectionError("RFCOMM transport is not connected")
    self._socket.settimeout(timeout)
    data = self._socket.recv(size)
    if not data:
      self.close()
      raise ConnectionError("RFCOMM device disconnected")
    return data

  def write(self, data: bytes) -> None:
    if self._socket is None:
      raise ConnectionError("RFCOMM transport is not connected")
    try:
      self._socket.sendall(data)
    except OSError:
      self.close()
      raise


class ELM327:
  def __init__(self, mac: str, transport: RFCOMMTransport | None = None, command_timeout: float = DEFAULT_COMMAND_TIMEOUT,
               reconnect_attempts: int = 3, reconnect_backoff: float = 1.0, sleep=time.sleep):
    self.mac = mac
    self.command_timeout = command_timeout
    self.reconnect_attempts = reconnect_attempts
    self.reconnect_backoff = reconnect_backoff
    self._transport: Any = transport or RFCOMMTransport()
    self._lock = threading.RLock()
    self._connected = False
    self._initialized = False
    self._sleep = sleep

  def connect(self) -> str:
    with self._lock:
      self.close()
      try:
        return self._open_and_identify()
      except Exception:
        self.close()
        raise

  def close(self) -> None:
    with self._lock:
      self._transport.close()
      self._connected = False
      self._initialized = False

  def command(self, cmd: str, timeout: float | None = None) -> str:
    with self._lock:
      try:
        return self._command_once(cmd, self.command_timeout if timeout is None else timeout)
      except OSError:
        initialized = self._initialized
        self.close()
        self._reconnect(initialized)
        raise

  def initialize(self) -> None:
    with self._lock:
      try:
        self._initialize_once()
      except OSError:
        self.close()
        self._reconnect(initialize=True)
        raise

  def _open_and_identify(self) -> str:
    self._transport.connect(self.mac)
    self._connected = True
    identity = self._command_once("ATI", self.command_timeout)
    if not any(marker in identity.upper() for marker in ELM_IDENTITY_MARKERS):
      raise RuntimeError("RFCOMM device did not identify as an ELM-compatible adapter")
    return identity

  def _initialize_once(self) -> None:
    for command in ("ATZ", "ATE0", "ATL0", "ATI", "ATSP0"):
      self._command_once(command, self.command_timeout)
    self._initialized = True

  def _reconnect(self, initialize: bool) -> None:
    for attempt in range(self.reconnect_attempts):
      if attempt:
        self._sleep(self.reconnect_backoff * (2 ** (attempt - 1)))
      try:
        self._open_and_identify()
        if initialize:
          self._initialize_once()
        return
      except OSError:
        self.close()

  def _command_once(self, cmd: str, timeout: float) -> str:
    if not self._connected:
      raise ConnectionError("ELM327 is not connected")
    command = cmd.rstrip("\r\n")
    self._transport.write(command.encode("ascii") + b"\r")
    deadline = time.monotonic() + timeout
    response = bytearray()
    while b">" not in response:
      remaining = deadline - time.monotonic()
      if remaining <= 0:
        raise TimeoutError(f"Timed out waiting for ELM327 response to {command!r}")
      try:
        chunk = self._transport.read(4096, timeout=remaining)
      except TimeoutError as error:
        raise TimeoutError(f"Timed out waiting for ELM327 response to {command!r}") from error
      if not chunk:
        raise ConnectionError("ELM327 disconnected before sending a prompt")
      response.extend(chunk)
    raw = bytes(response).split(b">", 1)[0]
    return self._clean_response(raw, command)

  @staticmethod
  def _clean_response(raw: bytes, command: str) -> str:
    lines = raw.decode("ascii", errors="replace").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[0].strip():
      lines.pop(0)
    while lines and not lines[-1].strip():
      lines.pop()
    if lines and lines[0].strip().upper() == command.upper():
      lines.pop(0)
      while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)
