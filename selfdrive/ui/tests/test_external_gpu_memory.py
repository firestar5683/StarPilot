"""VRAM accounting and additive telemetry regression tests, with no GPU access."""
import ast
import hashlib
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from cereal import log
from tinygrad.runtime.support.memory import TLSFAllocator
from starpilot.common.external_gpu_memory import allocated_vram, external_gpu_memory
from openpilot.selfdrive.ui.onroad.starpilot.developer_metrics import external_gpu_memory_metric
from openpilot.selfdrive.ui.tests.test_external_gpu_temperature import snapshot, NOW, publisher  # noqa: F401


def driver():
  mm = NS(boot_allocator=TLSFAllocator(16 << 20), ptable_allocator=TLSFAllocator(0), pa_allocator=TLSFAllocator(960 << 20))
  return NS(iface=NS(dev_impl=NS(vram_size=1024 << 20, mm=mm)))


def test_physical_allocator_alloc_free_and_reserved():
  d = driver()
  before = allocated_vram(d)
  assert before == (48 << 20, 1024 << 20)
  pool = d.iface.dev_impl.mm.pa_allocator
  a = pool.alloc(120 << 20)
  assert allocated_vram(d) == (168 << 20, 1024 << 20)
  pool.free(a)
  assert allocated_vram(d) == before
  boot = d.iface.dev_impl.mm.boot_allocator
  boot.alloc(4096)
  assert allocated_vram(d)[0] == before[0] + 4096


@pytest.mark.parametrize('failure', ['missing', 'negative', 'inconsistent', 'overfull', 'race'])
def test_bad_accounting_is_unavailable(failure):
  d = driver()
  if failure == 'missing':
    del d.iface.dev_impl.mm
  elif failure == 'negative':
    d.iface.dev_impl.vram_size = -1
  elif failure == 'inconsistent':
    d.iface.dev_impl.mm.pa_allocator.blocks.clear()
  elif failure == 'overfull':
    d.iface.dev_impl.vram_size = 4
  else:
    class Bad:
      def values(self): raise RuntimeError('concurrent modification')
    d.iface.dev_impl.mm.pa_allocator.blocks = Bad()
  assert allocated_vram(d) is None


def memory_snapshot():
  sm = snapshot()
  sm['chestnutState'].memoryUsedBytes = 1 << 30
  sm['chestnutState'].memoryTotalBytes = 4 << 30
  sm['chestnutState'].memorySampleMonoTime = NOW
  return sm


@pytest.mark.parametrize('used,total', [(0, 4 << 30), (1 << 30, 4 << 30), (4 << 30, 4 << 30)])
def test_memory_wire_and_format(used,total):
  sm = memory_snapshot()
  sm['chestnutState'].memoryUsedBytes = used
  sm['chestnutState'].memoryTotalBytes = total
  with log.ChestnutState.from_bytes(sm['chestnutState'].to_bytes()) as state:
    sm['chestnutState'] = state
    assert external_gpu_memory(sm, NOW) == ((used,total), 1000)
    assert external_gpu_memory_metric(sm,NOW) == f'eGPU RAM: {used/2**30:.1f}/4.0 GiB ({round(100*used/total)}%)'


@pytest.mark.parametrize('failure', ['old','future','zero_time','bad_total','over_total','disconnected','envelope','invalid','missing'])
def test_memory_stale_invalid_legacy(failure):
  sm = memory_snapshot()
  state = sm['chestnutState']
  if failure == 'old': state.memorySampleMonoTime = NOW - 15_000_000_001
  elif failure == 'future': state.memorySampleMonoTime = NOW + 1
  elif failure == 'zero_time': state.memorySampleMonoTime = 0
  elif failure == 'bad_total': state.memoryTotalBytes = 0
  elif failure == 'over_total': state.memoryUsedBytes = 8 << 30
  elif failure == 'disconnected': sm['deviceState'].chestnutPresent = False
  elif failure == 'envelope': sm.logMonoTime['chestnutState'] = NOW - 1_000_000_001
  elif failure == 'invalid': sm.valid['chestnutState'] = False
  else: del sm['chestnutState']
  assert external_gpu_memory_metric(sm,NOW) == 'eGPU RAM: --'


def test_memory_independent_of_temperature():
  sm = memory_snapshot()
  sm['chestnutState'].tempC = 0
  sm['chestnutState'].tempSampleMonoTime = 0
  assert external_gpu_memory(sm,NOW)[0] == (1 << 30,4 << 30)


def test_publisher_memory_failure_preserves_stock_diagnostics(publisher):
  p = publisher
  d = driver().iface.dev_impl
  p.devices['AMD'].iface.dev_impl.mm = d.mm
  p.devices['AMD'].iface.dev_impl.vram_size = d.vram_size
  p.obj.send()
  first = p.messages[-1]
  assert first['valid']
  assert first['chestnutState']['memoryUsedBytes'] == 48 << 20
  assert first['chestnutState']['memorySampleMonoTime'] == NOW
  del p.devices['AMD'].iface.dev_impl.mm
  p.obj.sends = 100
  p.obj.send()
  failed = p.messages[-1]
  assert failed['valid']
  assert failed['chestnutState']['tempC'] == 73
  assert failed['chestnutState']['memorySampleMonoTime'] == 0
  assert p.smu._send_msg.call_count == 2
  p.obj.big = False
  p.obj.send()
  assert p.messages[-1]['chestnutState']['memoryTotalBytes'] == 0


def test_all_stock_chestnut_fields_and_cadence_identical(publisher):
  p = publisher
  source = Path(os.environ['DOM_MODELD_SOURCE']).read_text() if os.environ.get('DOM_MODELD_SOURCE') else subprocess.check_output(['git','show','7f3bd6129:selfdrive/modeld/modeld.py'],text=True)
  assert hashlib.sha256(source.encode()).hexdigest() == '3fe2d92e43509473aeb93d4e38a3ea2164644f4285b60b2ab827611e230309bf'
  cls = next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name == 'ChestnutState')
  namespace = dict(p.namespace)
  exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])), '<stock Dom ChestnutState>', 'exec'), namespace)
  stock_messages = []
  stock = namespace['ChestnutState'](NS(send=lambda _,m:stock_messages.append(m.to_dict())),True)
  stock.power_limit = p.obj.power_limit
  stock._read_ina = p.obj._read_ina
  added = {'tempSampleMonoTime','memoryUsedBytes','memoryTotalBytes','memorySampleMonoTime'}
  for step in range(205):
    if step == 100: p.smu._send_msg.side_effect = RuntimeError('SMU failed')
    if step == 200: p.smu._send_msg.side_effect = None
    p.obj.send()
    stock.send()
    actual, baseline = p.messages[-1], stock_messages[-1]
    assert actual['valid'] == baseline['valid']
    assert {k:v for k,v in actual['chestnutState'].items() if k not in added} == {k:v for k,v in baseline['chestnutState'].items() if k not in added}
    p.clock.value += 100_000_000
  assert p.smu._send_msg.call_count == 6


def test_galaxy_transport_grace_does_not_extend_sample_lifetime():
  from openpilot.selfdrive.ui.tests.test_external_gpu_temperature import snapshot, NOW
  from openpilot.starpilot.common.external_gpu_temperature import external_gpu_temperature
  sm = snapshot(sample_time=NOW-10_000_000_000)
  sm.logMonoTime['deviceState'] = NOW-1_500_000_000
  assert external_gpu_temperature(sm, NOW) == (None, 0)
  value, ttl = external_gpu_temperature(sm, NOW, envelope_max_age_ns=3_000_000_000)
  assert value is not None and ttl == 1500
  assert external_gpu_temperature(sm, NOW+1_500_000_001, envelope_max_age_ns=3_000_000_000) == (None, 0)
  sm.logMonoTime['deviceState'] = NOW
  sm['chestnutState'].tempSampleMonoTime = NOW-15_000_000_001
  assert external_gpu_temperature(sm, NOW, envelope_max_age_ns=3_000_000_000) == (None, 0)
