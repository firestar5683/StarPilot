from __future__ import annotations

import re
import socket
import threading


DEFAULT_CHANNEL = 1
OPEN_TIMEOUT = 10.0
DEFAULT_COMMAND_TIMEOUT = 10.0
DTC_COMMAND_TIMEOUT = 25.0
MAX_COMMAND_LENGTH = 256
MAX_RESPONSE_SIZE = 64 * 1024
RECV_SIZE = 4096


class DTCParseError(ValueError):
  def __init__(self, message: str, raw: str):
    super().__init__(message)
    self.raw = raw


def decode_dtc(first: int, second: int) -> str:
  prefixes = "PCBU"
  prefix = prefixes[(first >> 6) & 0x03]
  return f"{prefix}{(first >> 4) & 0x03:X}{first & 0x0F:X}{second >> 4:X}{second & 0x0F:X}"


_HEX_BYTE = re.compile(r"(?i)(?<![0-9a-f])([0-9a-f]{2})(?![0-9a-f])")


def parse_dtcs(raw: str) -> list[str]:
  codes = []
  seen = set()
  for line in raw.splitlines():
    values = [int(match, 16) for match in _HEX_BYTE.findall(line)]
    try:
      response_index = values.index(0x43)
    except ValueError:
      continue

    payload = values[response_index + 1:]
    if len(payload) % 2:
      count = payload[0]
      expected_length = count * 2
      if len(payload) - 1 < expected_length:
        raise DTCParseError(f"Mode 03 response claims {expected_length} DTC bytes, received {len(payload) - 1}", raw)
      payload = payload[1:1 + expected_length]

    for index in range(0, len(payload) - 1, 2):
      first, second = payload[index:index + 2]
      if first == 0 and second == 0:
        continue
      code = decode_dtc(first, second)
      if code not in seen:
        seen.add(code)
        codes.append(code)
  return codes


class ELM327Session:
  def __init__(self, address: str, channel: int = DEFAULT_CHANNEL):
    self.address = address
    self.channel = channel
    self.socket: socket.socket | None = None
    self.lock = threading.RLock()
    self.adapter_name = ""

  def _close_unlocked(self) -> None:
    client_socket = self.socket
    self.socket = None
    self.adapter_name = ""
    if client_socket is not None:
      try:
        client_socket.close()
      except Exception:
        pass

  def close(self) -> None:
    with self.lock:
      self._close_unlocked()

  def _receive_until_prompt_unlocked(self, timeout: float) -> bytes:
    if self.socket is None:
      raise RuntimeError("ELM327 session is not open")
    self.socket.settimeout(timeout)
    response = bytearray()
    while True:
      chunk = self.socket.recv(RECV_SIZE)
      if not chunk:
        raise RuntimeError("ELM327 connection closed")
      response.extend(chunk)
      if len(response) > MAX_RESPONSE_SIZE:
        raise RuntimeError("ELM327 response exceeded 64 KiB")
      if b">" in response:
        return bytes(response)

  @staticmethod
  def _clean_response(raw: bytes, command: str) -> str:
    response = raw.split(b">", 1)[0].decode("ascii", errors="replace")
    response = response.replace("\r\n", "\n").replace("\r", "\n")
    lines = response.split("\n")
    while lines and not lines[0].strip():
      lines.pop(0)
    if lines and lines[0].strip() == command:
      lines.pop(0)
    return "\n".join(lines).strip()

  def _exchange_unlocked(self, command: str, timeout: float) -> str:
    if self.socket is None:
      raise RuntimeError("ELM327 session is not open")
    try:
      self.socket.settimeout(timeout)
      self.socket.sendall(command.encode("ascii") + b"\r")
      return self._clean_response(self._receive_until_prompt_unlocked(timeout), command)
    except Exception as error:
      self._close_unlocked()
      raise RuntimeError(f"ELM327 transport failed: {error}") from error

  def open(self) -> str:
    with self.lock:
      if self.socket is not None:
        return self.adapter_name
      try:
        self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.socket.settimeout(OPEN_TIMEOUT)
        self.socket.connect((self.address, self.channel))
        adapter_name = self._exchange_unlocked("ATI", OPEN_TIMEOUT)
        if not adapter_name or adapter_name.strip().upper() in {"?", "ERROR", "COMMAND UNKNOWN", "UNKNOWN COMMAND", "NO DATA"}:
          raise RuntimeError("ELM327 adapter rejected ATI")
        self.adapter_name = adapter_name
        for setup_command in ("ATE0", "ATL0", "ATH0"):
          self._exchange_unlocked(setup_command, OPEN_TIMEOUT)
        return self.adapter_name
      except Exception as error:
        self._close_unlocked()
        if isinstance(error, RuntimeError) and str(error).startswith("ELM327 open failed:"):
          raise
        raise RuntimeError(f"ELM327 open failed: {error}") from error

  def command(self, command: str, timeout: float = DEFAULT_COMMAND_TIMEOUT) -> str:
    if not isinstance(command, str):
      raise ValueError("ELM327 command must be text")
    if "\r" in command or "\n" in command:
      raise ValueError("ELM327 command cannot contain carriage returns or newlines")
    command = command.strip()
    if not command:
      raise ValueError("ELM327 command cannot be empty")
    if len(command) > MAX_COMMAND_LENGTH:
      raise ValueError("ELM327 command is too long")
    try:
      command.encode("ascii")
    except UnicodeEncodeError as error:
      raise ValueError("ELM327 command must contain ASCII characters") from error
    if timeout <= 0:
      raise ValueError("ELM327 command timeout must be positive")

    with self.lock:
      return self._exchange_unlocked(command, timeout)

  def read_dtcs(self) -> dict[str, str | list[str]]:
    with self.lock:
      for setup_command in ("ATE0", "ATL0", "ATH0", "ATSP0"):
        self.command(setup_command)
      raw = self.command("03", timeout=DTC_COMMAND_TIMEOUT)
    return {"codes": parse_dtcs(raw), "raw": raw}
