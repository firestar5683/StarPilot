import json
from types import SimpleNamespace
import pytest
from starpilot.common.vehicle_snapshot import write_vehicle_snapshot, read_vehicle_snapshot, MAX_AGE_NS

class Snapshot(dict):pass

def snapshot():
  sm=Snapshot(carState=SimpleNamespace(gearShifter='park',accFaulted=False,steerFaultTemporary=False,steerFaultPermanent=False,canValid=True,cruiseState=SimpleNamespace(available=True,enabled=False)))
  sm.seen={'carState':True};sm.alive={'carState':True};sm.valid={'carState':True};sm.logMonoTime={'carState':1_000_000_000}
  return sm

def test_atomic_roundtrip_and_source_expiry(tmp_path):
  path=tmp_path/'vehicle';sm=snapshot()
  assert write_vehicle_snapshot(sm,path)
  assert read_vehicle_snapshot(path,now_ns=1_050_000_000).gearShifter=='park'
  # Rewriting a cached message must not give it a fresh timestamp.
  assert write_vehicle_snapshot(sm,path)
  assert read_vehicle_snapshot(path,now_ns=1_000_000_000+MAX_AGE_NS) is None
  assert read_vehicle_snapshot(path,now_ns=999_999_999) is None
  sm['carState'].gearShifter='drive';sm.logMonoTime['carState']+=MAX_AGE_NS
  assert write_vehicle_snapshot(sm,path)
  assert read_vehicle_snapshot(path,now_ns=1_100_000_001).gearShifter=='drive'

@pytest.mark.parametrize('field',['valid','alive','seen'])
def test_invalid_producer_overwrites_previous_park(tmp_path,field):
  path=tmp_path/'vehicle';sm=snapshot();write_vehicle_snapshot(sm,path)
  getattr(sm,field)['carState']=False
  assert write_vehicle_snapshot(sm,path)
  assert read_vehicle_snapshot(path,now_ns=1_000_000_001) is None

@pytest.mark.parametrize('content',['{}','[]','null','{','{"sourceMonoTime":true}', 'x'*5000])
def test_corrupt_or_partial_payload_fails_closed(tmp_path,content):
  path=tmp_path/'vehicle';path.write_text(content)
  assert read_vehicle_snapshot(path,now_ns=1_000_000_001) is None

def test_missing_path_and_write_failure_are_nonfatal(tmp_path):
  path=tmp_path/'absent'/'vehicle'
  assert read_vehicle_snapshot(path) is None
  assert write_vehicle_snapshot(snapshot(),path) is False
