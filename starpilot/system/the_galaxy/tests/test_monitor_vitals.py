import time
from types import SimpleNamespace
import pytest
from openpilot.starpilot.system.the_galaxy import external_gpu_vitals as backend

class Snapshot(dict):
  pass

def snapshot():
  now=time.monotonic_ns()
  sm=Snapshot(deviceState=SimpleNamespace(cpuTempC=[51.,57.],gpuTempC=[49.],chestnutPresent=True),
              chestnutState=SimpleNamespace(tempC=73.,tempSampleMonoTime=now,memoryUsedBytes=1073741824,memoryTotalBytes=4294967296,memorySampleMonoTime=now))
  sm.valid=dict.fromkeys(sm,True);sm.alive=dict.fromkeys(sm,True);sm.logMonoTime=dict.fromkeys(sm,now);sm.update=lambda timeout:None
  return sm

def test_monitor_exposes_onboard_maxima_and_real_hotspot(monkeypatch):
  sm=snapshot();monkeypatch.setattr(backend,'_sm',sm)
  result=backend.external_gpu_vitals(include_onboard=True)
  assert result['cpuTempC']==57 and result['gpuTempC']==49
  assert result['hotspotTempC']==73 and result['gpuEdgeTempC'] is None
  assert result['memoryUsedBytes']==1073741824 and result['memoryTotalBytes']==4294967296

@pytest.mark.parametrize('fault',['stale','invalid','missing','nan'])
def test_bad_onboard_readings_do_not_hide_valid_external_gpu(monkeypatch,fault):
  sm=snapshot();monkeypatch.setattr(backend,'_sm',sm)
  if fault=='stale':sm.logMonoTime['deviceState']=time.monotonic_ns()-4000000000
  elif fault=='invalid':sm.valid['deviceState']=False
  elif fault=='missing':sm['deviceState'].cpuTempC=[];sm['deviceState'].gpuTempC=[]
  else:sm['deviceState'].cpuTempC=[float('nan')];sm['deviceState'].gpuTempC=[float('inf')]
  result=backend.external_gpu_vitals(include_onboard=True)
  assert result['cpuTempC'] is None and result['gpuTempC'] is None
  if fault in ('missing','nan'):assert result['hotspotTempC']==73

def test_disconnected_external_gpu_keeps_onboard_temperatures(monkeypatch):
  sm=snapshot();sm['deviceState'].chestnutPresent=False;monkeypatch.setattr(backend,'_sm',sm)
  result=backend.external_gpu_vitals(include_onboard=True)
  assert result['cpuTempC']==57
  assert result['hotspotTempC'] is None and result['memoryUsedBytes'] is None

def test_legacy_home_response_stays_unchanged(monkeypatch):
  monkeypatch.setattr(backend,'_sm',snapshot())
  assert set(backend.external_gpu_vitals())=={'tempC','maxAgeMs','memoryUsedBytes','memoryTotalBytes','memoryMaxAgeMs'}
