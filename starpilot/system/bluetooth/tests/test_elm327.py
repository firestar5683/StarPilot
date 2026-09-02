from collections import deque
import threading

import pytest

from openpilot.starpilot.system.bluetooth import elm327


ADDRESS = "00:11:22:33:44:55"


class FakeSocket:
  def __init__(self, responses):
    self.responses = deque(deque(response) for response in responses)
    self.pending = deque()
    self.sent = []
    self.connected_to = None
    self.timeouts = []
    self.closed = False
    self.close_calls = 0
    self.recv_error = None
    self.send_error = None

  def settimeout(self, timeout):
    self.timeouts.append(timeout)

  def connect(self, address):
    self.connected_to = address

  def sendall(self, value):
    if self.send_error is not None:
      raise self.send_error
    self.sent.append(value)
    self.pending.extend(self.responses.popleft() if self.responses else deque())

  def recv(self, _size):
    if self.recv_error is not None:
      raise self.recv_error
    return self.pending.popleft() if self.pending else b""

  def close(self):
    self.close_calls += 1
    self.closed = True


def startup_responses(identity=b"ELM327 v1.5"):
  return [
    [b"ATI\r\n", identity + b"\r\n>"],
    [b"ATE0\r\nOK\r\n>"],
    [b"ATL0\r\nOK\r\n>"],
    [b"ATH0\r\nOK\r\n>"],
  ]


def make_session(monkeypatch, responses):
  fake = FakeSocket(responses)
  monkeypatch.setattr(elm327.socket, "AF_BLUETOOTH", 31, raising=False)
  monkeypatch.setattr(elm327.socket, "BTPROTO_RFCOMM", 3, raising=False)
  monkeypatch.setattr(elm327.socket, "socket", lambda *args: fake)
  return elm327.ELM327Session(ADDRESS), fake


def test_open_uses_rfccomm_channel_one_and_validates_ati(monkeypatch):
  session, fake = make_session(monkeypatch, startup_responses())

  assert session.open() == "ELM327 v1.5"
  assert fake.connected_to == (ADDRESS, 1)
  assert fake.sent == [b"ATI\r", b"ATE0\r", b"ATL0\r", b"ATH0\r"]
  assert session.adapter_name == "ELM327 v1.5"


def test_open_drains_stale_boot_prompt_and_late_packets(monkeypatch):
  session, fake = make_session(monkeypatch, startup_responses() + [[b"ATRV\r\n12.5V\r\n>"]])
  fake.pending = deque([b"\r\nELM327 v1.5\r\n>"])
  assert session.open() == "ELM327 v1.5"
  assert fake.sent[:4] == [b"ATI\r", b"ATE0\r", b"ATL0\r", b"ATH0\r"]
  fake.pending = deque([b"UNSOLICITED NOISE\r\n"])
  assert session.command("ATRV") == "12.5V"


def test_open_rejects_empty_or_obviously_rejected_ati(monkeypatch):
  for identity in (b"", b"?", b"ERROR"):
    session, fake = make_session(monkeypatch, startup_responses(identity))
    with pytest.raises(RuntimeError, match="ATI"):
      session.open()
    assert session.socket is None and fake.closed


def test_command_removes_exact_echo_and_reads_split_prompt_response(monkeypatch):
  responses = startup_responses() + [[b"ATR", b"V\r\n12.4V\r", b"\n>"]]
  session, fake = make_session(monkeypatch, responses)
  session.open()

  assert session.command(" ATRV ") == "12.4V"
  assert fake.sent[-1] == b"ATRV\r"


def test_malformed_response_bytes_decode_with_replacement(monkeypatch):
  responses = startup_responses() + [[b"ATI\r\n\xffOK\r\n>"]]
  session, _ = make_session(monkeypatch, responses)
  session.open()

  assert session.command("ATI") == "�OK"


@pytest.mark.parametrize("command", ["", "   ", "ATI\r", "ATI\n", "AT\r\nI", "A" * (elm327.MAX_COMMAND_LENGTH + 1)])
def test_command_rejects_invalid_input(monkeypatch, command):
  session, _ = make_session(monkeypatch, [])
  with pytest.raises(ValueError):
    session.command(command)


def test_command_rejects_non_ascii_input(monkeypatch):
  session, _ = make_session(monkeypatch, [])
  with pytest.raises(ValueError, match="ASCII"):
    session.command("ATé")


def test_response_size_limit_closes_session(monkeypatch):
  responses = startup_responses() + [[b"x" * (elm327.MAX_RESPONSE_SIZE + 1)]]
  session, fake = make_session(monkeypatch, responses)
  session.open()

  with pytest.raises(RuntimeError, match="64 KiB"):
    session.command("ATI")
  assert session.socket is None and fake.closed


@pytest.mark.parametrize("error", [TimeoutError("timed out"), OSError("disconnected")])
def test_timeout_or_eof_closes_session(monkeypatch, error):
  responses = startup_responses() + [[]]
  session, fake = make_session(monkeypatch, responses)
  session.open()
  fake.recv_error = error if isinstance(error, TimeoutError) else None

  if isinstance(error, TimeoutError):
    with pytest.raises(RuntimeError, match="transport"):
      session.command("ATI")
  else:
    with pytest.raises(RuntimeError, match="connection closed"):
      session.command("ATI")
  assert session.socket is None and fake.closed


def test_send_failure_closes_session(monkeypatch):
  responses = startup_responses() + [[b"OK>"]]
  session, fake = make_session(monkeypatch, responses)
  session.open()
  fake.send_error = OSError("send failed")

  with pytest.raises(RuntimeError, match="transport"):
    session.command("ATI")
  assert session.socket is None and fake.closed


def test_close_is_idempotent(monkeypatch):
  session, fake = make_session(monkeypatch, startup_responses())
  session.open()
  session.close()
  session.close()

  assert fake.close_calls == 1
  assert session.socket is None


def test_simultaneous_commands_are_serialized(monkeypatch):
  class SerializedSocket(FakeSocket):
    def __init__(self, responses):
      super().__init__(responses)
      self.command_started = threading.Event()
      self.release_command = threading.Event()
      self._command_sends = 0

    def sendall(self, value):
      super().sendall(value)
      self._command_sends += 1
      if self._command_sends == 5:
        self.command_started.set()
        assert self.release_command.wait(timeout=1.0)

  fake = SerializedSocket(startup_responses() + [[b"VALUE1>"], [b"VALUE2>"]])
  monkeypatch.setattr(elm327.socket, "AF_BLUETOOTH", 31, raising=False)
  monkeypatch.setattr(elm327.socket, "BTPROTO_RFCOMM", 3, raising=False)
  monkeypatch.setattr(elm327.socket, "socket", lambda *args: fake)
  session = elm327.ELM327Session(ADDRESS)
  session.open()

  results = []
  first = threading.Thread(target=lambda: results.append(session.command("ONE")))
  second = threading.Thread(target=lambda: results.append(session.command("TWO")))
  first.start()
  assert fake.command_started.wait(timeout=1.0)
  second.start()
  assert len(fake.sent) == 5
  fake.release_command.set()
  first.join(timeout=1.0)
  second.join(timeout=1.0)

  assert sorted(results) == ["VALUE1", "VALUE2"]
  assert len(fake.sent) == 6


def test_read_dtcs_runs_known_setup_and_returns_mode_three_result(monkeypatch):
  responses = startup_responses() + [[b"OK>"] for _ in range(5)] + [[b"43 01 33 04 20 00 00>"]]
  session, fake = make_session(monkeypatch, responses)
  session.open()

  assert session.read_dtcs() == {"codes": ["P0133", "P0420"], "raw": "43 01 33 04 20 00 00"}
  assert fake.sent[-6:] == [b"ATE0\r", b"ATL0\r", b"ATS1\r", b"ATH0\r", b"ATCAF1\r", b"03\r"]


@pytest.mark.parametrize("raw_command", ["ATS0", "ATCAF0"])
def test_read_dtcs_restores_parser_state_after_raw_command(monkeypatch, raw_command):
  responses = startup_responses() + [[b"OK>"]] + [[b"OK>"] for _ in range(5)] + [[b"43 01 33 00 00 00 00>"]]
  session, fake = make_session(monkeypatch, responses)
  session.open()
  session.command(raw_command)

  assert session.read_dtcs() == {"codes": ["P0133"], "raw": "43 01 33 00 00 00 00"}
  assert fake.sent[-6:] == [b"ATE0\r", b"ATL0\r", b"ATS1\r", b"ATH0\r", b"ATCAF1\r", b"03\r"]


def test_non_can_dtc_is_decoded_and_padding_ignored():
  assert elm327.parse_dtcs("43 01 33 00 00 00 00") == ["P0133"]


def test_can_dtc_count_byte_is_skipped():
  assert elm327.parse_dtcs("43 02 01 33 04 20") == ["P0133", "P0420"]


def test_no_data_returns_no_codes():
  assert elm327.parse_dtcs("NO DATA") == []
  assert elm327.parse_dtcs("SEARCHING...\nNO DATA") == []
  assert elm327.parse_dtcs("SEARCHING...\r\nNO DATA") == []
  assert elm327.parse_dtcs("SEARCHING...\n43 01 33 00 00") == ["P0133"]


def test_can_dtc_multiframe_response_is_reassembled():
  raw = "008\n0: 43 03 00 59 01 54\n1: 01 55"
  assert elm327.parse_dtcs(raw) == ["P0059", "P0154", "P0155"]


def test_larger_numbered_multiframe_response_is_reassembled():
  raw = "00E\n0: 43 06 01 33 04 20\n1: 00 59 01 54\n2: 01 55 01 56"
  assert elm327.parse_dtcs(raw) == ["P0133", "P0420", "P0059", "P0154", "P0155", "P0156"]


@pytest.mark.parametrize("raw", [
  "008\n0: 43 03 00 59 01 54",
  "008\n1: 43 03 00 59 01 54\n1: 01 55",
  "008\n0: 43 03 00 59 GG 54\n1: 01 55",
  "008\n0: 43 03 00 59 01 54\n00E",
])
def test_invalid_numbered_multiframe_response_raises(raw):
  with pytest.raises(elm327.DTCParseError):
    elm327.parse_dtcs(raw)


@pytest.mark.parametrize("raw", ["UNABLE TO CONNECT", "STOPPED", "?", "BUS ERROR", "7F 03 11", "43"])
def test_non_mode_three_response_raises(raw):
  with pytest.raises(elm327.DTCParseError):
    elm327.parse_dtcs(raw)


def test_multiple_ecu_lines_are_ordered_and_deduplicated():
  raw = "43 01 33 00 00\n43 04 20 00 00\n43 01 33 00 00"
  assert elm327.parse_dtcs(raw) == ["P0133", "P0420"]


def test_malformed_can_count_raises_with_raw_response():
  raw = "43 02 01 33"
  with pytest.raises(elm327.DTCParseError) as error:
    elm327.parse_dtcs(raw)
  assert error.value.raw == raw
