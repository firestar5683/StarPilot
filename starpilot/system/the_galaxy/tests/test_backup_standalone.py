import copy
import pytest
from openpilot.starpilot.system.the_galaxy import backup

class Params:
  def __init__(self, values=None): self.values = copy.deepcopy(values or {})
  def get(self, key): return self.values.get(key)
  def put(self, key, value): self.values[key] = value
  def remove(self, key): self.values.pop(key, None)

PARKED = {'IsOnroad': False, 'IsOffroad': True, 'SafeMode': False}

@pytest.mark.parametrize('change', [{'IsOnroad':True}, {'IsOffroad':False}, {'SafeMode':True}, {'SafeModeBackup':{}},
  {'IsOnroad':None}, {'IsOffroad':None}, {'SafeMode':None}, {'SafeMode':0}, {'SafeMode':'invalid'}])
def test_guard_fails_closed(change):
  with pytest.raises(ValueError,match='confirmed parked'):
    backup.require_parked(Params({**PARKED, **change}))

def test_guard_accepts_explicit_live_flags_without_readers():
  backup.require_parked(Params(PARKED))
  backup.require_parked(Params({'IsOnroad':b'0','IsOffroad':b'1','SafeMode':b'0'}))

def test_guard_rejects_read_failure():
  class Broken:
    def get(self,key): raise OSError('unavailable')
  with pytest.raises(ValueError,match='confirmed parked'): backup.require_parked(Broken())

def unavailable(): raise ValueError('Model statistics support is unavailable')

def test_optional_provider_has_explicit_export_and_import_behavior(tmp_path,monkeypatch):
  monkeypatch.setattr(backup,'_statistics_support',unavailable)
  assert backup.export_statistics(tmp_path/'missing.sqlite') is None
  assert backup.validate_statistics(None) is None
  (tmp_path/'existing.sqlite').touch()
  with pytest.raises(ValueError,match='unavailable'): backup.export_statistics(tmp_path/'existing.sqlite')
  with pytest.raises(ValueError,match='unavailable'):
    backup.validate_statistics({'schemaVersion':1,'drives':[],'metrics':[]})

def test_settings_history_roundtrip_repeated_import_without_recorder(tmp_path,monkeypatch):
  monkeypatch.setattr(backup,'_statistics_support',unavailable)
  params=Params({'setting':False,'GalaxyDashboardStats':{'version':1,'routes':{'retained':{'duration':4}}}})
  history={'GalaxyDashboardStats':{'version':1,'routes':{'imported':{'duration':2}}}}
  for n in range(2):
    result=backup.apply_restore(params,{'setting':True},history,None,tmp_path/'model.sqlite',tmp_path/f'r{n}',lambda:None)
    assert result=={'restoredCount':1,'addedDrives':0,'existingDrives':0}
    assert params.values['setting'] is True
    assert set(params.values['GalaxyDashboardStats']['routes'])=={'retained','imported'}
  assert not (tmp_path/'model.sqlite').exists()
  assert (tmp_path/'r0/settings-before.json').exists()

@pytest.mark.parametrize('stop_at',[1,2,3,4,5])
def test_road_state_changes_abort_and_restore_previous_values(tmp_path,stop_at):
  params=Params({'a':'before','b':12});calls=0
  def parked():
    nonlocal calls
    calls+=1
    if calls==stop_at: raise ValueError('moving')
  with pytest.raises(ValueError,match='moving'):
    backup.apply_restore(params,{'a':'after','b':99},{},None,tmp_path/'db',tmp_path/'recovery',parked)
  assert params.values=={'a':'before','b':12}

def test_silent_write_failure_rolls_back_all_settings(tmp_path):
  class Silent(Params):
    def put(self,key,value):
      if key!='b':super().put(key,value)
  params=Silent({'a':'before','b':12})
  with pytest.raises(backup.RestoreError,match='verified'):
    backup.apply_restore(params,{'a':'after','b':99},{},None,tmp_path/'db',tmp_path/'recovery',lambda:None)
  assert params.values=={'a':'before','b':12}

def test_statistics_import_without_provider_writes_nothing(tmp_path,monkeypatch):
  monkeypatch.setattr(backup,'_statistics_support',unavailable)
  params=Params({'a':'before'})
  with pytest.raises(ValueError,match='unavailable'):
    backup.apply_restore(params,{'a':'after'},{},{'schemaVersion':1,'drives':[],'metrics':[]},tmp_path/'db',tmp_path/'recovery',lambda:None)
  assert params.values=={'a':'before'}
  assert not list(tmp_path.iterdir())
