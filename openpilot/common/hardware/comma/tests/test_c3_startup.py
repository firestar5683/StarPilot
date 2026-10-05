import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "hardware.py"


@pytest.mark.parametrize("device,usb", [("tici", True), ("tizi", False), ("mici", False)])
def test_internal_panda_transport_irq_affinity(device, usb):
  tree = ast.parse(SOURCE.read_text())
  cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "HardwareComma")
  method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "initialize_hardware")
  start = next(i for i, node in enumerate(method.body) if isinstance(node, ast.Expr) and
               ast.unparse(node.value) == "affine_irq(3, 'spi_geni')")
  affinity = Mock()
  code = compile(ast.fix_missing_locations(ast.Module(body=method.body[start:start + 2], type_ignores=[])), str(SOURCE), "exec")
  exec(code, {"self": SimpleNamespace(get_device_type=lambda: device), "affine_irq": affinity})
  expected = [(3, "spi_geni")]
  if usb:
    expected += [(3, "xhci-hcd:usb3"), (3, "xhci-hcd:usb1")]
  assert [call.args for call in affinity.call_args_list] == expected


@pytest.mark.parametrize('model,right_volume,eq_enabled', [('tici', 0x1c, 1), ('tizi', 0x17, 0)])
def test_amplifier_profile_registers_and_shutdown_order(model, right_volume, eq_enabled):
  from collections import namedtuple

  path = SOURCE.with_name('amplifier.py')
  tree = ast.parse(path.read_text())
  selected: list[ast.stmt] = [node for node in tree.body if isinstance(node, (ast.Assign, ast.FunctionDef, ast.ClassDef))]
  namespace: dict = {'namedtuple': namedtuple}
  exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])), str(path), 'exec'), namespace)
  amp = namespace['Amplifier'].__new__(namespace['Amplifier'])
  amp.set_configs = Mock(return_value=True)
  assert amp.initialize_configuration(model)
  configs = amp.set_configs.call_args.args[0]
  assert configs[0].register == configs[-1].register == 0x51
  assert configs[0].value == 0 and configs[-1].value == 1
  assert next(config.value for config in configs if config.register == 0x3e) == right_volume
  eq = [config.value for config in configs if config.register == 0x49 and config.offset == 1]
  assert eq[-1] == eq_enabled
  assert sum(config.register >= 0x84 for config in configs) == (50 if model == 'tici' else 0)


def test_hardware_startup_and_wake_pass_actual_amplifier_model():
  tree = ast.parse(SOURCE.read_text())
  cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'HardwareComma')
  for name in ('initialize_hardware', 'set_power_save'):
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    calls = [node for node in ast.walk(method) if isinstance(node, ast.Call) and
             ast.unparse(node.func) == 'self.amplifier.initialize_configuration']
    assert len(calls) == 1
    assert ast.unparse(calls[0].args[0]) == 'self.get_device_type()'


@pytest.mark.parametrize('model', ['tici', 'tizi'])
@pytest.mark.parametrize('path_name', ['initialize_hardware', 'set_power_save'])
def test_startup_and_wake_write_model_registers(model, path_name):
  from collections import namedtuple

  registers = dict.fromkeys(range(256), 0xa5)
  writes = []

  class Bus:
    def __init__(self, bus):
      assert bus == 0

    def __enter__(self):
      return self

    def __exit__(self, *args):
      return False

    def read_byte_data(self, address, register, force):
      assert address == 0x10 and force
      return registers[register]

    def write_byte_data(self, address, register, value, force):
      assert address == 0x10 and force
      registers[register] = value
      writes.append((register, value))

  amp_path = SOURCE.with_name('amplifier.py')
  tree = ast.parse(amp_path.read_text())
  selected: list[ast.stmt] = [node for node in tree.body if isinstance(node, (ast.Assign, ast.FunctionDef, ast.ClassDef))]
  namespace: dict = {'namedtuple': namedtuple, 'SMBus': Bus}
  exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])), str(amp_path), 'exec'), namespace)
  amp = namespace['Amplifier']()
  tree = ast.parse(SOURCE.read_text())
  cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'HardwareComma')
  method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == path_name)
  code = compile(ast.fix_missing_locations(ast.Module(body=[method.body[0]], type_ignores=[])), str(SOURCE), 'exec')
  exec(code, {'self': SimpleNamespace(amplifier=amp, get_device_type=lambda: model), 'powersave_enabled': False})
  expected_registers = dict.fromkeys(range(256), 0xa5)
  configs = [amp._get_shutdown_config(True), *namespace['BASE_CONFIG'], *namespace['CONFIGS'][model], amp._get_shutdown_config(False)]
  if path_name == 'set_power_save':
    configs.insert(0, amp._get_shutdown_config(False))
  expected = []
  for config in configs:
    value = (expected_registers[config.register] & ~config.mask) | ((config.value << config.offset) & config.mask)
    expected_registers[config.register] = value
    expected.append((config.register, value))
  assert writes == expected
  assert registers == expected_registers
  assert registers[0x3e] & 0x1f == (0x1c if model == 'tici' else 0x17)
  assert registers[0x49] & 2 == (2 if model == 'tici' else 0)
  assert len([register for register, _ in writes if register >= 0x84]) == (50 if model == 'tici' else 0)


@pytest.mark.parametrize('device,reset_hold,recover_hold', [('tici', 1, 0.5), ('tizi', 0.01, 0.01), ('mici', 0.01, 0.01)])
def test_internal_panda_reset_and_recovery_timing(device, reset_hold, recover_hold):
  tree = ast.parse(SOURCE.read_text())
  cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'HardwareComma')
  methods: list[ast.stmt] = [node for node in cls.body if isinstance(node, ast.FunctionDef) and
             node.name in {'reset_internal_panda', 'recover_internal_panda'}]
  events = Mock()
  namespace: dict = {'gpio_init': Mock(), 'gpio_set': events.gpio, 'time': SimpleNamespace(sleep=events.sleep),
               'GPIO': SimpleNamespace(STM_RST_N='reset', STM_BOOT0='boot0')}
  exec(compile(ast.Module(body=methods, type_ignores=[]), str(SOURCE), 'exec'), namespace)
  hardware = SimpleNamespace(get_device_type=lambda: device)
  namespace['reset_internal_panda'](hardware)
  assert events.mock_calls == [call.gpio('reset', True), call.gpio('boot0', False), call.sleep(reset_hold), call.gpio('reset', False)]
  events.reset_mock()
  namespace['recover_internal_panda'](hardware)
  assert events.mock_calls == [call.gpio('reset', True), call.gpio('boot0', True), call.sleep(recover_hold),
                               call.gpio('reset', False), call.sleep(recover_hold), call.gpio('boot0', False)]


@pytest.mark.parametrize('device', ['tici', 'tizi', 'mici'])
@pytest.mark.parametrize('failure', [None, 'missing', 'usb', 'protocol', 'multiple'])
def test_pandad_enumeration_and_recovery(device, failure):
  pandad_path = SOURCE.parents[3] / 'selfdrive/pandad/pandad.py'
  tree = ast.parse(pandad_path.read_text())
  main_fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
  events = Mock()
  first_discovery = {'missing': [], 'usb': OSError(), 'multiple': ['one', 'two']}.get(failure, ['serial'])
  events.list.side_effect = [[], first_discovery, *([] if failure == 'multiple' else [['serial']]), KeyboardInterrupt()]
  events.dfu_list.return_value = []
  flash = Mock(side_effect=[RuntimeError(), None] if failure == 'protocol' else None)
  process = Mock()
  process.wait.side_effect = KeyboardInterrupt()
  launch = Mock(return_value=process)
  namespace: dict = {'Panda': SimpleNamespace(list=events.list), 'PandaDFU': SimpleNamespace(list=events.dfu_list),
               'HARDWARE': SimpleNamespace(get_device_type=lambda: device, reset_internal_panda=events.reset,
                                           recover_internal_panda=events.recover),
               'time': SimpleNamespace(sleep=events.sleep), 'cloudlog': Mock(), 'signal': Mock(),
               'usb1': SimpleNamespace(USBErrorNoDevice=OSError, USBErrorPipe=BrokenPipeError), 'PandaProtocolMismatch': RuntimeError,
               'flash_panda': flash, 'subprocess': SimpleNamespace(Popen=launch), 'BASEDIR': 'base',
               'os': SimpleNamespace(environ={}, path=SimpleNamespace(join=lambda *parts: '/'.join(parts)))}
  exec(compile(ast.Module(body=[main_fn], type_ignores=[]), str(pandad_path), 'exec'), namespace)
  with pytest.raises(KeyboardInterrupt):
    namespace['main']()

  expected = [call.list()]  # Initial health inspection.
  for reset in [call.reset()] if failure is None else [call.reset(), call.recover()]:
    expected += [reset, *([call.sleep(3)] if device == 'tici' else []), call.dfu_list(), call.list()]
  assert events.mock_calls == expected
  if failure == 'multiple':
    flash.assert_not_called()
    launch.assert_not_called()
  else:
    assert flash.call_args_list == [call('serial')] * (2 if failure == 'protocol' else 1)
    launch.assert_called_once_with(['./pandad', 'serial'], cwd='base/openpilot/selfdrive/pandad')
