import ast
import binascii
import importlib.util
from itertools import accumulate
import os
from pathlib import Path
import struct
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[2]


def constants():
  spec = importlib.util.spec_from_file_location('tested_panda_constants', ROOT / 'panda/python/constants.py')
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def production_panda(tmp_path):
  tree = ast.parse((ROOT / 'panda/python/__init__.py').read_text())
  original = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Panda')
  selected = {'get_mcu_type', 'is_internal', 'get_dfu_serial', 'up_to_date', 'flash', 'flash_static'}
  body = [node for node in original.body if isinstance(node, ast.Assign) or isinstance(node, ast.FunctionDef) and node.name in selected]
  cls = ast.ClassDef(name='Panda', bases=[], keywords=[], body=body, decorator_list=[])
  mcu = constants().McuType
  env = {'accumulate': accumulate, 'McuType': mcu, 'compute_version_hash': lambda _: 1, 'opendbc': SimpleNamespace(INCLUDE_PATH=''),
         'os': os, 'BASEDIR': str(tmp_path), '_parse_c_struct': lambda *args: None, 'struct': struct,
         'FW_PATH': str(tmp_path), 'logger': Mock(), 'PandaDFU': Mock(),
         'usb1': SimpleNamespace(ENDPOINT_IN=1, TYPE_VENDOR=2, RECIPIENT_DEVICE=3, ENDPOINT_OUT=4)}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), '<current-panda>', 'exec'), env)
  return env['Panda'], env, mcu


@pytest.mark.parametrize('hardware,expected', [(b'\x06', 'F4'), (b'\x07', 'H7'), (b'\x09', 'H7'), (b'\x0a', 'H7')])
def test_detected_hardware_selects_exact_firmware_and_dfu_config(tmp_path, hardware, expected):
  cls, env, mcu = production_panda(tmp_path)
  panda = cls()
  panda.get_type = lambda: hardware
  panda._serial = '010002000300040005000600'
  assert panda.get_mcu_type() == getattr(mcu, expected)
  panda.get_dfu_serial()
  env['PandaDFU'].st_serial_to_dfu_serial.assert_called_once_with(panda._serial, getattr(mcu, expected))
  assert panda.is_internal() == (hardware != b'\x07')


@pytest.mark.parametrize('hardware', [b'\x00', b'\x03', b'\xff'])
def test_unknown_hardware_never_defaults_to_h7(tmp_path, hardware):
  cls, _, _ = production_panda(tmp_path)
  panda = cls()
  panda.get_type = lambda: hardware
  with pytest.raises(ValueError, match='Unknown HW'):
    panda.get_mcu_type()


@pytest.mark.parametrize('hardware', [b'\x06', b'\x09'])
def test_default_flash_uses_detected_mcu_image_and_static_flash_target(tmp_path, hardware):
  cls, env, _ = production_panda(tmp_path)
  panda = cls()
  panda.get_type = lambda: hardware
  target = panda.get_mcu_type()
  image = tmp_path / target.config.app_fn
  image.write_bytes(b'exact configured image')
  panda.up_to_date = lambda **kwargs: False
  panda.bootstub = True
  panda.get_version = lambda: 'bootstub'
  panda._handle = object()
  panda.reconnect = Mock()
  cls.flash_static = Mock()
  panda.flash()
  cls.flash_static.assert_called_once_with(panda._handle, image.read_bytes(), mcu_type=target)
  panda.reconnect.assert_called_once()
  captured = []
  cls.get_signature_from_firmware = lambda path: captured.append(path) or b'correct'
  panda.get_signature = lambda: b'correct'
  assert cls.up_to_date(panda)
  assert captured == [str(image)]


def test_pandad_signature_binds_detected_mcu_and_rejects_wrong_packet_hashes(tmp_path):
  tree = ast.parse((ROOT / 'openpilot/selfdrive/pandad/pandad.py').read_text())
  functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {'get_expected_signature', 'flash_panda'}]
  mcu = constants().McuType
  for target in (mcu.F4, mcu.H7):
    for versions in ((11, 22), (0, 0), (11, 23)):
      device = SimpleNamespace(get_mcu_type=lambda: target, is_internal=lambda: True, bootstub=False,
                               get_version=lambda: 'current', get_signature=lambda: b'correct',
                               get_packets_versions=lambda: versions, close=Mock(), flash=Mock())
      factory = Mock(return_value=device)
      factory.HEALTH_PACKET_VERSION, factory.CAN_PACKET_VERSION = 11, 22
      factory.get_signature_from_firmware = Mock(return_value=b'correct')
      class Mismatch(Exception):
        pass
      env = {'os': os, 'FW_PATH': str(tmp_path), 'McuType': mcu, 'Panda': factory,
             'PandaProtocolMismatch': Mismatch, 'cloudlog': Mock(), 'HARDWARE': Mock()}
      exec(compile(ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[])), '<current-wrapper>', 'exec'), env)
      if versions == (11, 22):
        env['flash_panda']('serial')
      else:
        with pytest.raises(Mismatch, match='protocol hash mismatch'):
          env['flash_panda']('serial')
      factory.get_signature_from_firmware.assert_called_once_with(str(tmp_path / target.config.app_fn))
      device.flash.assert_not_called()
      device.close.assert_called_once()


def test_dfu_serial_uses_f4_rom_offset_and_h7_unchanged():
  tree = ast.parse((ROOT / 'panda/python/dfu.py').read_text())
  original = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'PandaDFU')
  method = next(node for node in original.body if isinstance(node, ast.FunctionDef) and node.name == 'st_serial_to_dfu_serial')
  cls = ast.ClassDef(name='PandaDFU', bases=[], keywords=[], body=[method], decorator_list=[])
  mcu = constants().McuType
  env = {'McuType': mcu, 'binascii': binascii, 'struct': struct}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), '<current-dfu>', 'exec'), env)
  convert = env['PandaDFU'].st_serial_to_dfu_serial
  assert convert('010002000300040005000600', mcu.F4) == '000800100004'
  assert convert('010002000300040005000600', mcu.H7) == '000800060004'
  assert convert(None, mcu.F4) is None


def test_f4_sector12_is_rejected_before_any_erase_or_write(tmp_path):
  cls, _, mcu = production_panda(tmp_path)
  cls.flasher_present = lambda handle: True
  handle = SimpleNamespace(controlWrite=Mock(), bulkWrite=Mock())
  code = bytes(sum(mcu.F4.config.sector_sizes[1:12]))
  with pytest.raises(AssertionError, match='DOS bootstubs support sectors 1..11'):
    cls.flash_static(handle, code, mcu.F4)
  handle.controlWrite.assert_not_called()
  handle.bulkWrite.assert_not_called()
