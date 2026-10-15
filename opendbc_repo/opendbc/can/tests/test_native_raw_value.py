import builtins
import importlib.util
import sys

import pytest

from opendbc.can import dbc
from opendbc.can.tests.test_signal_raw_value import make_signal, raw_reference


@pytest.fixture(params=['python', 'native'])
def decoder(request, monkeypatch):
  native = dbc._native_raw_value
  if request.param == 'native' and native is None:
    pytest.skip('optional raw CAN extension is not built')
  monkeypatch.setattr(dbc, '_native_raw_value', native if request.param == 'native' else None)
  return dbc.Signal


@pytest.fixture
def native():
  if dbc._native_raw_value is None:
    pytest.skip('optional raw CAN extension is not built')
  return dbc._native_raw_value


@pytest.mark.parametrize('little', [False, True])
@pytest.mark.parametrize('container', [bytes, bytearray])
def test_raw_widths_offsets_and_unsigned_high_bit(decoder, little, container):
  data = container(bytes(range(64)))
  for base in (0, 16, 55):
    for alignment in range(8):
      start = base * 8 + alignment
      available = 512 - start if little else alignment + 1 + 8 * (63 - base)
      for size in range(1, min(64, available) + 1):
        signal = make_signal(start, size, little)
        assert signal.get_raw_value(data) == raw_reference(data, start, size, little)
  signal = make_signal(7 if little else 0, 64, little)
  assert signal.get_raw_value(container(b'\xff' * 9)) == 2**64 - 1


@pytest.mark.parametrize('msb,lsb,size,little,payload,expected', [
  (23, 0, 24, True, b'\xab\xcd', 0),
  (7, 16, 24, False, b'\xab\xcd', 0xABCD00),
  (15, 0, 8, True, b'\xab\xcd', 0xCD),
  (7, 16, 16, False, b'\xab\xcd\xef', 0xABCD),
  (7, 0, 0, True, b'\xff', 0),
  (7, 0, -1, False, b'\xff', 0),
  (23, 24, 16, False, b'\xab\xcd', 0),
  (7, 0, 8, True, b'', 0),
])
def test_raw_partial_and_noncanonical_fallback(decoder, msb, lsb, size, little, payload, expected):
  signal = decoder('TEST', msb, msb, lsb, size, False, 1., 0., little)
  assert signal.get_raw_value(payload) == expected


def test_raw_full_width_python_fallback(decoder):
  for little in (False, True):
    signal = make_signal(0 if little else 7, 512, little)
    assert signal.get_raw_value(b'\xff' * 64) == 2**512 - 1


def test_raw_noncanonical_exception_order(decoder):
  for msb, lsb, size, little in ((7, 4, 2, True), (3, 0, 2, False)):
    signal = decoder('TEST', msb, msb, lsb, size, False, 1., 0., little)
    with pytest.raises(ValueError, match='negative shift count'):
      signal.get_raw_value(b'\xff')


def test_raw_geometry_updates_and_custom_values(decoder):
  class EqualInt(int):
    pass

  signal = make_signal(0, 16, True)
  assert signal.get_raw_value(b'\xab\xcd') == 0xCDAB
  signal.size = 8
  assert signal.get_raw_value(b'\xab\xcd') == 0xCD
  signal.__dict__.update(msb=7, lsb=0, size=8, is_little_endian=True)
  assert signal.get_raw_value(b'\xab\xcd') == 0xAB
  signal.__dict__['size'] = EqualInt(8)
  assert signal.get_raw_value(b'\xab\xcd') == 0xAB
  signal.__dict__['msb'] = 2**100
  assert signal.get_raw_value(b'\xab\xcd') == 0


@pytest.mark.parametrize('container', [memoryview, list])
def test_raw_custom_payload_falls_back(decoder, container):
  signal = make_signal(0, 16, True)
  assert signal.get_raw_value(container(b'\xab\xcd')) == 0xCDAB


def test_native_rejects_subclass_without_reading_fields(native):
  class CustomSignal(dbc.Signal):
    def __getattribute__(self, name):
      if name in ('msb', 'lsb', 'size', 'is_little_endian'):
        raise AssertionError('native must not read subclass fields')
      return super().__getattribute__(name)

  signal = CustomSignal('CUSTOM', 0, 7, 0, 8, False, 1., 0., True)
  assert native(signal, b'\xab', dbc.Signal) is NotImplemented


def test_native_keeps_mutable_payload_after_attribute_callbacks(native):
  class CallbackSignal:
    lsb, size, is_little_endian = 0, 8, True

    def __init__(self, payload, length):
      self.payload, self.length = payload, length

    @property
    def msb(self):
      self.payload[:] = b'\xcd' * self.length
      return 7

  for length in (0, 4096):
    payload = bytearray(b'\xab' * 64)
    result = native(CallbackSignal(payload, length), payload, CallbackSignal)
    assert result is NotImplemented if length == 0 else result == 0xCD


def test_native_unsupported_keeps_attribute_references(native):
  value = int('1000000000000000000000000000000000000000')
  signal = dbc.Signal('REFS', 0, value, 0, 8, False, 1., 0., True)
  before = sys.getrefcount(value)
  for _ in range(1000):
    assert native(signal, b'\xff', dbc.Signal) is NotImplemented
  assert sys.getrefcount(value) == before


def test_python_import_without_native_extension(monkeypatch):
  original_import = builtins.__import__

  def without_native(name, module_globals=None, module_locals=None, fromlist=(), level=0):
    if name == 'opendbc.can._raw_value':
      raise ImportError('optional extension unavailable')
    return original_import(name, module_globals, module_locals, fromlist, level)

  name = '_dbc_python_fallback_test'
  spec = importlib.util.spec_from_file_location(name, dbc.__file__)
  module = importlib.util.module_from_spec(spec)
  monkeypatch.setitem(sys.modules, name, module)
  monkeypatch.setattr(builtins, '__import__', without_native)
  spec.loader.exec_module(module)
  assert module._native_raw_value is None
  signal = module.Signal('FALLBACK', 0, 15, 0, 16, False, 1., 0., True)
  assert signal.get_raw_value(b'\xab\xcd') == 0xCDAB
