"""Published-message and production-method tests; no GPU/native UI access."""
import ast
import ctypes
import math
import time
from functools import cached_property
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from cereal import log
from starpilot.common.external_gpu_memory import allocated_vram

from openpilot.selfdrive.ui.onroad.starpilot.developer_metrics import (
  build_developer_metric_parts, external_gpu_temperature_metric, external_gpu_memory_metric,
)
from openpilot.selfdrive.ui.tests.test_developer_metrics import mici_metrics_view  # noqa: F401

NOW = 30_000_000_000


def snapshot(sample_time=NOW - 10_000_000_000, temperature=73.4):
  class SubMaster(dict):
    pass

  device = log.DeviceState.new_message(chestnutPresent=True, gpuTempC=[58.0])
  external = log.ChestnutState.new_message(tempC=temperature, tempSampleMonoTime=sample_time)
  sm = SubMaster(deviceState=device, chestnutState=external)
  sm.valid = dict.fromkeys(sm, True)
  sm.alive = dict.fromkeys(sm, True)
  sm.logMonoTime = dict.fromkeys(sm, NOW)
  return sm


def test_real_schema_roundtrip_and_distinct_sensor():
  sm = snapshot()
  with log.ChestnutState.from_bytes(sm['chestnutState'].to_bytes()) as state:
    sm['chestnutState'] = state
    assert external_gpu_temperature_metric(sm, NOW) == 'eGPU: 73°C'
    assert list(sm['deviceState'].gpuTempC) == [58.0]


@pytest.mark.parametrize('sample_age,available', [(0, True), (10_000_000_000, True), (15_000_000_000, True),
                                                (15_000_000_001, False), (-1, False), (NOW, False)])
def test_sample_freshness_not_cached_envelope(sample_age, available):
  sm = snapshot(NOW - sample_age)
  assert external_gpu_temperature_metric(sm, NOW) == ('eGPU: 73°C' if available else 'eGPU: --')


@pytest.mark.parametrize('service', ['deviceState', 'chestnutState'])
@pytest.mark.parametrize('mode', ['invalid', 'dead', 'old', 'future', 'missing'])
def test_missing_stale_or_invalid_messages(service, mode):
  sm = snapshot()
  if mode == 'invalid':
    sm.valid[service] = False
  elif mode == 'dead':
    sm.alive[service] = False
  elif mode == 'missing':
    del sm[service]
  else:
    sm.logMonoTime[service] = NOW - 1_000_000_001 if mode == 'old' else NOW + 1
  assert external_gpu_temperature_metric(sm, NOW) == 'eGPU: --'


@pytest.mark.parametrize('temperature', [0, -1, math.nan, math.inf, -math.inf])
def test_unusable_temperature_never_falls_back_to_onboard_or_zero(temperature):
  assert external_gpu_temperature_metric(snapshot(temperature=temperature), NOW) == 'eGPU: --'


def test_disconnection_and_legacy_publisher_are_unavailable():
  sm = snapshot()
  sm['deviceState'].chestnutPresent = False
  assert external_gpu_temperature_metric(sm, NOW) == 'eGPU: --'
  sm['deviceState'].chestnutPresent = True
  sm['chestnutState'] = SimpleNamespace(tempC=73.4)
  assert external_gpu_temperature_metric(sm, NOW) == 'eGPU: --'


@pytest.fixture
def publisher():
  """Compile the actual Chestnut publisher, mocking only hardware boundaries."""
  source = Path('selfdrive/modeld/modeld.py')
  tree = ast.parse(source.read_text())
  cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ChestnutState')
  clock = SimpleNamespace(value=NOW)
  messages = []

  def new_message(service):
    msg = log.Event.new_message(logMonoTime=clock.value)
    msg.init(service)
    return msg

  class Metrics(ctypes.Structure):
    _fields_ = [('AvgTemperature', ctypes.c_uint16 * 2), ('AverageSocketPower', ctypes.c_uint16),
               ('AverageGfxActivity', ctypes.c_uint16), ('AverageGfxclkFrequencyPostDs', ctypes.c_uint16),
               ('AvgFanRpm', ctypes.c_uint16)]

  class External(ctypes.Structure):
    _fields_ = [('SmuMetrics', Metrics)]

  raw = External(Metrics((73, 64), 30, 50, 1200, 2000))
  smu = SimpleNamespace(
    smu_mod=SimpleNamespace(SmuMetricsExternal_t=External, TEMP_HOTSPOT=0, TEMP_MEM=1,
                            PPSMC_MSG_TransferTableSmu2Dram=1, TABLE_SMU_METRICS=2),
    _send_msg=Mock(), adev=SimpleNamespace(vram=SimpleNamespace(view=lambda *_: bytes(raw))), driver_table_paddr=0,
  )
  gpu = SimpleNamespace(iface=SimpleNamespace(dev_impl=SimpleNamespace(smu=smu),
                        pci_dev=SimpleNamespace(usb=SimpleNamespace(read=Mock(return_value=b'\x10')))))

  class Devices(dict):
    _opened_devices = ['AMD']

  devices = Devices(AMD=gpu)
  namespace = dict(PubMaster=object, Device=devices, messaging=SimpleNamespace(new_message=new_message),
                   time=SimpleNamespace(monotonic_ns=lambda: clock.value), ctypes=ctypes,
                   cached_property=cached_property, cloudlog=Mock(), allocated_vram=allocated_vram)
  exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), str(source), 'exec'), namespace)
  obj = namespace['ChestnutState'](SimpleNamespace(send=lambda _, m: messages.append(m.to_dict())), True)
  obj.power_limit = 45
  obj._read_ina = Mock(return_value=(12000, 1000, False))
  return SimpleNamespace(obj=obj, messages=messages, clock=clock, smu=smu, devices=devices, namespace=namespace)


def test_publisher_stamps_only_successful_samples_not_cached_sends(publisher):
  p = publisher
  p.obj.send()
  assert p.messages[-1]['chestnutState']['tempSampleMonoTime'] == NOW
  assert p.messages[-1]['chestnutState']['tempC'] == 73
  for _ in range(99):
    p.clock.value += 100_000_000
    p.obj.send()
    assert p.messages[-1]['chestnutState']['tempSampleMonoTime'] == NOW
  assert p.smu._send_msg.call_count == 1
  p.clock.value += 100_000_000
  p.obj.send()
  assert p.messages[-1]['chestnutState']['tempSampleMonoTime'] == p.clock.value
  assert p.smu._send_msg.call_count == 2


def test_failed_smu_read_clears_timestamp_and_fallback_does_not_publish_cache(publisher):
  p = publisher
  p.obj.send()
  p.obj.sends = 100
  p.smu._send_msg.side_effect = RuntimeError('simulated read failure')
  p.obj.send()
  assert not p.messages[-1]['valid']
  assert p.messages[-1]['chestnutState']['tempSampleMonoTime'] == 0
  assert p.messages[-1]['chestnutState']['tempC'] == 0
  p.smu._send_msg.side_effect = None
  p.obj.sends = 200
  p.obj.send()
  p.obj.big = False
  p.obj.send()
  assert p.messages[-1]['chestnutState']['tempSampleMonoTime'] == 0
  assert p.messages[-1]['chestnutState']['tempC'] == 0


def test_no_opened_gpu_does_not_initialize_hardware(publisher):
  p = publisher
  p.devices._opened_devices = []
  p.obj.send()
  p.smu._send_msg.assert_not_called()
  assert p.messages[-1]['chestnutState']['tempSampleMonoTime'] == 0


@pytest.mark.parametrize('all_metrics', [False, True])
@pytest.mark.parametrize('temperature', [73.4, 125.0])
@pytest.mark.parametrize('border', [0, 24])
def test_actual_mici_renderer_draws_real_external_sample(mici_metrics_view, all_metrics, temperature, border):
  f = mici_metrics_view
  f.view._get_border_width = lambda: border
  now = time.monotonic_ns()
  sm = snapshot(now, temperature)
  sm.logMonoTime = dict.fromkeys(sm, now)
  sm['deviceState'] = f.state.sm['deviceState']
  sm['deviceState'].chestnutPresent = True
  sm['chestnutState'].memoryUsedBytes = 3 << 30
  sm['chestnutState'].memoryTotalBytes = 4 << 30
  sm['chestnutState'].memorySampleMonoTime = now
  f.state.sm = sm
  if all_metrics:
    f.state.starpilot_toggles.clear()
    f.params.update({'ShowCPU', 'NumericalTemp', 'ShowMemoryUsage', 'FPSCounter'})
  f.view._render(f.view.rect)
  text = ' | '.join(c.args[1] for c in f.raylib.draw_text_ex.call_args_list)
  assert 'GPU: 0% / 58°C' in text
  assert f'eGPU: {round(temperature)}°C' in text
  assert 'eGPU RAM: 3.0/4.0 GiB (75%)' in text
  panel = f.raylib.draw_rectangle_rec.call_args.args[0]
  for call in f.raylib.draw_text_ex.call_args_list:
    font, line, pos, size = call.args[:4]
    assert size >= 16
    assert panel.x <= pos.x < pos.x + f.measure_text(font, line, size).x <= panel.x + panel.width
    assert panel.y <= pos.y < pos.y + size * 1.16 <= panel.y + panel.height
  if all_metrics:
    for label in ['CPU:', 'TEMP:', 'RAM:', 'FPS:']:
      assert label in text


def test_actual_big_renderer_uses_external_telemetry(mici_metrics_view):
  f = mici_metrics_view
  sm = snapshot()
  sm['deviceState'] = f.state.sm['deviceState']
  sm['deviceState'].chestnutPresent = True
  f.state.sm = sm
  path = Path('selfdrive/ui/onroad/starpilot/starpilot_onroad_view.py')
  cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'StarPilotOnroadView')
  method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_render_developer_metrics')
  def measure_text(font, text, size):
    return SimpleNamespace(x=f.measure_text(font, text, size).x, y=size * 1.16)

  namespace = dict(ui_state=f.state, rl=f.raylib, math=math, measure_text_cached=measure_text,
                   build_developer_metric_parts=build_developer_metric_parts,
                   external_gpu_memory_metric=external_gpu_memory_metric, external_gpu_temperature_metric=lambda sm: external_gpu_temperature_metric(sm, NOW))
  exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), 'exec'), namespace)
  f.view._params = f.state.ui_params
  f.view._font_medium = f.view._metrics_font
  f.view._min_fps, f.view._max_fps, f.view._avg_fps = 20, 20, 20
  f.view._content_rect = f.view.rect
  namespace['_render_developer_metrics'](f.view)
  rendered = ' | '.join(c.args[1] for c in f.raylib.draw_text_ex.call_args_list)
  assert 'GPU: 0% / 58°C' in rendered and 'eGPU: 73°C' in rendered
  assert 'eGPU RAM: --' in rendered
  for c in f.raylib.draw_text_ex.call_args_list:
    _, text, pos, size = c.args[:4]
    assert f.view._content_rect.x <= pos.x
    assert pos.x + measure_text(None, text, size).x <= f.view._content_rect.x + f.view._content_rect.width


def test_subscription_is_read_only_and_existing_hardware_read_schedule_unchanged():
  assert '"chestnutState",' in Path('selfdrive/ui/ui_state.py').read_text()
  source = Path('selfdrive/modeld/modeld.py').read_text()
  assert 'self.sends % 100 == 1' in source
  formatter = Path('selfdrive/ui/onroad/starpilot/developer_metrics.py').read_text()
  assert 'tinygrad' not in formatter and 'Device[' not in formatter
