"""Local read-only API/schema regressions using real Cap'n Proto messages."""
import ast
import time
from pathlib import Path

import capnp
import pytest
from flask import Flask, jsonify
from cereal import log

from openpilot.selfdrive.ui.tests.test_external_gpu_temperature import snapshot
from starpilot.system.the_galaxy import external_gpu_vitals as backend


@pytest.fixture
def client(monkeypatch):
  sm = snapshot(time.monotonic_ns())
  sm.logMonoTime = dict.fromkeys(sm, time.monotonic_ns())
  sm.update = lambda timeout: None
  monkeypatch.setattr(backend, '_sm', sm)
  tree = ast.parse(Path('starpilot/system/the_galaxy/the_galaxy.py').read_text())
  handler = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'get_external_gpu_vitals')
  app = Flask(__name__)
  exec(compile(ast.fix_missing_locations(ast.Module(body=[handler], type_ignores=[])), 'production_endpoint', 'exec'),
       {'app': app, 'jsonify': jsonify})
  client = app.test_client()
  # Fixture construction may exceed the real 1s envelope budget on ARM.
  # Stamp the synthetic message only after Flask/AST setup, as a new sample.
  sm.logMonoTime = dict.fromkeys(sm, time.monotonic_ns())
  sm["chestnutState"].tempSampleMonoTime = time.monotonic_ns()
  return client, sm


def test_api_real_schema_temperature_and_cache_control(client):
  c, sm = client
  response = c.get('/api/vitals/external-gpu')
  assert response.status_code == 200
  assert response.headers['Cache-Control'] == 'no-store'
  assert response.json['tempC'] == pytest.approx(73.4)
  assert 0 < response.json['maxAgeMs'] <= 3000
  assert list(sm['deviceState'].gpuTempC) == [58.0]
  assert c.post('/api/vitals/external-gpu').status_code == 405
  sm['chestnutState'].memoryUsedBytes = 1 << 30
  sm['chestnutState'].memoryTotalBytes = 4 << 30
  sm['chestnutState'].memorySampleMonoTime = time.monotonic_ns()
  value = c.get('/api/vitals/external-gpu').json
  assert value['memoryUsedBytes'] == 1 << 30 and value['memoryTotalBytes'] == 4 << 30
  assert 0 < value['memoryMaxAgeMs'] <= 3000
  assert value['tempC'] == pytest.approx(73.4)


@pytest.mark.parametrize('failure', ['offroad', 'sample_stale', 'envelope_stale', 'invalid', 'legacy', 'exception'])
def test_api_unavailable_not_zero_or_onboard(client, failure):
  c, sm = client
  if failure == 'offroad':
    sm.alive['chestnutState'] = False
  elif failure == 'sample_stale':
    sm['chestnutState'].tempSampleMonoTime = time.monotonic_ns() - 15_000_000_001
  elif failure == 'envelope_stale':
    sm.logMonoTime['chestnutState'] = time.monotonic_ns() - 3_000_000_001
  elif failure == 'invalid':
    sm.valid['chestnutState'] = False
  elif failure == 'legacy':
    sm['chestnutState'].tempSampleMonoTime = 0
  else:
    def fail(_):
      raise RuntimeError('simulated subscriber failure')
    sm.update = fail
  assert c.get('/api/vitals/external-gpu').json == {'tempC': None, 'maxAgeMs': 0, 'memoryUsedBytes': None, 'memoryTotalBytes': None, 'memoryMaxAgeMs': 0}


def test_old_new_native_capnp_wire_compatibility(tmp_path):
  # Independent native schema parser: exact original struct layout, without
  # the additive field. Verify both directions, not merely Python attributes.
  source = Path('cereal/log.capnp').read_text()
  struct = source.split('struct ChestnutState {', 1)[1].split('\n}', 1)[0]
  struct = '\n'.join(line for line in struct.splitlines() if not any(field in line for field in ('tempSampleMonoTime @11', 'memoryUsedBytes @12', 'memoryTotalBytes @13', 'memorySampleMonoTime @14')))
  schema = tmp_path / 'legacy.capnp'
  schema.write_text('@0xdedfbee5cafea123;\nstruct ChestnutState {' + struct + '\n}\n')
  old = capnp.SchemaParser().load(str(schema))
  legacy = old.ChestnutState.new_message(tempC=73.0, supplyVoltage=12000)
  with log.ChestnutState.from_bytes(legacy.to_bytes()) as new:
    assert new.tempC == 73.0 and new.supplyVoltage == 12000
    assert new.tempSampleMonoTime == 0
  current = log.ChestnutState.new_message(tempC=74.0, supplyVoltage=12500, tempSampleMonoTime=30_000_000_000)
  with old.ChestnutState.from_bytes(current.to_bytes()) as previous:
    assert previous.tempC == 74.0 and previous.supplyVoltage == 12500
