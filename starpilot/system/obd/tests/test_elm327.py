from collections import deque

import pytest

import openpilot.starpilot.system.obd.elm327 as elm327_module
from openpilot.starpilot.system.obd.elm327 import ELM327, RFCOMMTransport


class ScriptedTransport:
  def __init__(self, responses):
    self.responses = deque(responses)
    self.current = deque()
    self.connects = []
    self.writes = []
    self.connected = False

  def connect(self, mac):
    self.connects.append(mac)
    self.connected = True

  def close(self):
    self.connected = False

  def write(self, data):
    if not self.connected:
      raise ConnectionError("transport is closed")
    self.writes.append(data)
    self.current = deque(self.responses.popleft())

  def read(self, _size=4096, timeout=None):
    item = self.current.popleft()
    if isinstance(item, BaseException):
      raise item
    return item


class FakeRFCOMMSocket:
  def __init__(self, attempts, failing_channels):
    self.attempts = attempts
    self.failing_channels = failing_channels
    self.closed = False
    self.timeout = None

  def settimeout(self, timeout):
    self.timeout = timeout

  def connect(self, address):
    self.attempts.append(address)
    if address[1] in self.failing_channels:
      raise OSError("channel unavailable")

  def close(self):
    self.closed = True


def test_command_returns_clean_normal_response():
  transport = ScriptedTransport([
    [b"ATI\rELM327 v1.5\r>"],
    [b"41 00 BE 3E B8 13\r>"],
  ])
  elm = ELM327("00:11:22:33:44:55", transport=transport)

  assert elm.connect() == "ELM327 v1.5"
  assert elm.command("0100") == "41 00 BE 3E B8 13"
  assert transport.writes == [b"ATI\r", b"0100\r"]


def test_command_handles_echo_crlf_chunks_and_multiline_response():
  transport = ScriptedTransport([
    [b"ATI\r\rELM327 v1.5\r\r>"],
    [b"010C\r\rSEARCHING...\r\n", b"41 0C 1A F8\r\n>"],
  ])
  elm = ELM327("00:11:22:33:44:55", transport=transport)

  elm.connect()

  assert elm.command("010C") == "SEARCHING...\n41 0C 1A F8"


def test_command_preserves_substantive_spacing_and_blank_lines():
  transport = ScriptedTransport([
    [b"ELM327 v1.5\r>"],
    [b"0100\r\r  VALUE  \r\rSECOND\r>"],
  ])
  elm = ELM327("00:11:22:33:44:55", transport=transport)

  elm.connect()

  assert elm.command("0100") == "  VALUE  \n\nSECOND"


@pytest.mark.parametrize(("raw", "expected"), [
  (b"NO DATA\r>", "NO DATA"),
  (b"?\r>", "?"),
])
def test_command_returns_valid_adapter_states(raw, expected):
  transport = ScriptedTransport([
    [b"ELM327 v1.5\r>"],
    [raw],
  ])
  elm = ELM327("00:11:22:33:44:55", transport=transport)

  elm.connect()

  assert elm.command("0100") == expected


def test_initialize_uses_the_minimal_obd_command_sequence():
  transport = ScriptedTransport([
    [b"ELM327 v1.5\r>"],
    [b"ATZ\rELM327 v1.5\r>"],
    [b"ATE0\rOK\r>"],
    [b"OK\r>"],
    [b"ELM327 v1.5\r>"],
    [b"OK\r>"],
  ])
  elm = ELM327("00:11:22:33:44:55", transport=transport)

  elm.connect()
  elm.initialize()

  assert transport.writes == [b"ATI\r", b"ATZ\r", b"ATE0\r", b"ATL0\r", b"ATI\r", b"ATSP0\r"]


@pytest.mark.parametrize("identity", [b"OK\r>", b"NO DATA\r>", b"CAN ERROR\r>", b"garbage\r>"])
def test_connect_requires_a_sensible_elm_identity(identity):
  transport = ScriptedTransport([[identity]])
  elm = ELM327("00:11:22:33:44:55", transport=transport)

  with pytest.raises(RuntimeError, match="identify"):
    elm.connect()

  assert not transport.connected


def test_timeout_is_an_exception_and_reconnects_the_session():
  transport = ScriptedTransport([
    [b"ELM327 v1.5\r>"],
    [TimeoutError("read timed out")],
    [b"ELM327 v1.5\r>"],
    [b"NO DATA\r>"],
  ])
  elm = ELM327("00:11:22:33:44:55", transport=transport)

  elm.connect()
  with pytest.raises(TimeoutError, match="0100"):
    elm.command("0100", timeout=0.01)

  assert transport.connects == ["00:11:22:33:44:55", "00:11:22:33:44:55"]
  assert elm.command("0100") == "NO DATA"


def test_disconnect_before_prompt_reconnects_and_reinitializes():
  initialization = [
    [b"ELM327 v1.5\r>"],
    [b"OK\r>"],
    [b"OK\r>"],
    [b"ELM327 v1.5\r>"],
    [b"OK\r>"],
  ]
  transport = ScriptedTransport([
    [b"ELM327 v1.5\r>"],
    *initialization,
    [b"41 00 BE", b""],
    [b"ELM327 v1.5\r>"],
    *initialization,
    [b"41 00 BE 3E B8 13\r>"],
  ])
  elm = ELM327("00:11:22:33:44:55", transport=transport)

  elm.connect()
  elm.initialize()
  with pytest.raises(ConnectionError, match="prompt"):
    elm.command("0100")

  assert transport.connects == ["00:11:22:33:44:55", "00:11:22:33:44:55"]
  assert transport.writes[-6:] == [b"ATI\r", b"ATZ\r", b"ATE0\r", b"ATL0\r", b"ATI\r", b"ATSP0\r"]
  assert elm.command("0100") == "41 00 BE 3E B8 13"


def test_initialize_failure_reconnects_and_restarts_initialization():
  transport = ScriptedTransport([
    [b"ELM327 v1.5\r>"],
    [b"ELM327 v1.5\r>"],
    [b""],
    [b"ELM327 v1.5\r>"],
    [b"ELM327 v1.5\r>"],
    [b"OK\r>"],
    [b"OK\r>"],
    [b"ELM327 v1.5\r>"],
    [b"OK\r>"],
    [b"NO DATA\r>"],
  ])
  elm = ELM327("00:11:22:33:44:55", transport=transport)

  elm.connect()
  with pytest.raises(ConnectionError, match="prompt"):
    elm.initialize()

  assert transport.writes[-6:] == [b"ATI\r", b"ATZ\r", b"ATE0\r", b"ATL0\r", b"ATI\r", b"ATSP0\r"]
  assert elm.command("0100") == "NO DATA"


def test_rfcomm_transport_falls_back_then_reuses_the_working_channel(monkeypatch):
  attempts = []
  failing_channels = {1}

  def socket_factory(*_args):
    return FakeRFCOMMSocket(attempts, failing_channels)

  monkeypatch.setattr(elm327_module.socket, "AF_BLUETOOTH", 31, raising=False)
  monkeypatch.setattr(elm327_module.socket, "BTPROTO_RFCOMM", 3, raising=False)
  monkeypatch.setattr(elm327_module.socket, "socket", socket_factory)
  transport = RFCOMMTransport()

  transport.connect("00:11:22:33:44:55")
  assert transport.channel == 2
  transport.close()
  failing_channels.clear()
  transport.connect("00:11:22:33:44:55")

  assert attempts == [
    ("00:11:22:33:44:55", 1),
    ("00:11:22:33:44:55", 2),
    ("00:11:22:33:44:55", 2),
  ]
