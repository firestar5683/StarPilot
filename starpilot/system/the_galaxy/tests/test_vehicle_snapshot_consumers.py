import ast
from pathlib import Path
from types import SimpleNamespace
import pytest

def helpers(snapshot):
  source=Path('starpilot/system/the_galaxy/the_galaxy.py').read_text()
  tree=ast.parse(source)
  names={'_get_vehicle_parked','_build_vehicle_fault_status'}
  nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
  def forbidden(*args,**kwargs):
    raise AssertionError('Galaxy must not allocate vehicle-data readers')
  ns={'read_vehicle_snapshot':lambda:snapshot,'params':SimpleNamespace(get_bool=lambda k:True),
      'messaging':SimpleNamespace(SubMaster=forbidden),'car':SimpleNamespace(CarState=SimpleNamespace(GearShifter=SimpleNamespace(park='park')))}
  exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'production_helpers','exec'),ns)
  return ns

def car_state(**changes):
  return SimpleNamespace(gearShifter='park',accFaulted=False,steerFaultTemporary=False,
                         steerFaultPermanent=False,canValid=True,cruiseState=SimpleNamespace(available=True,enabled=False),**changes)

def test_repeated_settings_checks_use_snapshot_without_readers():
  h=helpers(car_state())
  for _ in range(100):assert h['_get_vehicle_parked']() is True

def test_diagnostics_preserve_fault_details_without_readers():
  state=car_state();state.accFaulted=True;state.steerFaultPermanent=True;state.canValid=False
  result=helpers(state)['_build_vehicle_fault_status']()
  assert result['available'] is True
  assert result['summarySeverity']=='fault'
  assert {x['label']:x['value'] for x in result['items']}=={'Cruise Fault':'Faulted','LKAS Fault':'Permanent','CAN Valid':'No','Cruise Available':'Yes','Cruise Engaged':'No'}

@pytest.mark.parametrize('snapshot',[None,SimpleNamespace(gearShifter='drive')])
def test_no_park_authorization_without_fresh_park(snapshot):
  assert helpers(snapshot)['_get_vehicle_parked']() is False

def test_missing_snapshot_keeps_diagnostics_unavailable():
  assert helpers(None)['_build_vehicle_fault_status']()['available'] is False
