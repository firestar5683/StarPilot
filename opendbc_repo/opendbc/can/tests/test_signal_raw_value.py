import pytest

from opendbc.can.dbc import Signal
from opendbc.can.parser import MessageState


def make_signal(start, size, little, signed=False):
  if little:
    msb, lsb = start + size - 1, start
  else:
    last = start
    for _ in range(size - 1):
      last = last - 1 if last % 8 else last + 15
    msb, lsb = start, last
  return Signal("TEST", start, msb, lsb, size, signed, 0.25, -1.0, little)


def raw_reference(dat, start, size, little):
  if little:
    return sum(((dat[(start + bit) // 8] >> ((start + bit) % 8)) & 1) << bit for bit in range(size))
  value, position = 0, start
  for _ in range(size):
    value = (value << 1) | ((dat[position // 8] >> (position % 8)) & 1)
    position = position - 1 if position % 8 else position + 15
  return value


@pytest.mark.parametrize("start,size,little", [
  (3, 13, True), (7, 64, True), (0, 512, True), (504, 8, True),
  (5, 13, False), (0, 64, False), (7, 512, False), (511, 1, False),
])
@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize("payload", [bytes(64), bytes([255]) * 64, bytes(range(64))])
@pytest.mark.parametrize("container", [bytes, bytearray])
def test_complete_signal_raw_bits(start, size, little, signed, payload, container):
  signal = make_signal(start, size, little, signed)
  dat = container(payload)
  original = dat[:]
  assert signal.get_raw_value(dat) == raw_reference(dat, start, size, little)
  assert dat == original


@pytest.mark.parametrize("msb,lsb,size,little,payload,expected", [
  (23, 0, 24, True, b"\xab\xcd", 0),
  (7, 16, 24, False, b"\xab\xcd", 0xABCD00),
  (15, 0, 8, True, b"\xab\xcd", 0xCD),
  (7, 16, 16, False, b"\xab\xcd\xef", 0xABCD),
  (7, 0, 0, True, b"\xff", 0),
  (7, 0, -1, False, b"\xff", 0),
  (23, 24, 16, False, b"\xab\xcd", 0),
  (7, 0, 8, True, b"", 0),
  (7, 0, 8, False, b"", 0),
])
@pytest.mark.parametrize("container", [bytes, bytearray])
def test_partial_and_noncanonical_signal_semantics(msb, lsb, size, little, payload, expected, container):
  signal = Signal("TEST", msb, msb, lsb, size, False, 1.0, 0.0, little)
  assert signal.get_raw_value(container(payload)) == expected


@pytest.mark.parametrize("msb,lsb,size,little", [(7, 4, 2, True), (3, 0, 2, False)])
def test_inconsistent_signal_retains_negative_shift_error(msb, lsb, size, little):
  signal = Signal("TEST", msb, msb, lsb, size, False, 1.0, 0.0, little)
  with pytest.raises(ValueError, match="negative shift count"):
    signal.get_raw_value(b"\xff")


def test_signal_geometry_is_rechecked_after_mutation():
  signal = make_signal(0, 16, True)
  assert signal.get_raw_value(b"\xab\xcd") == 0xCDAB
  signal.size = 8
  assert signal.get_raw_value(b"\xab\xcd") == 0xCD


@pytest.mark.parametrize("little", [False, True])
def test_parser_keeps_signed_conversion_and_scaling(little):
  signal = make_signal(3, 13, little, signed=True)
  dat = bytes([255]) * 8
  assert signal.get_raw_value(dat) == (1 << 13) - 1
  state = MessageState(address=0x123, name="TEST", size=8, signals=[signal])
  assert state.parse(1_000_000, dat)
  assert state.vals == [-1.25]
