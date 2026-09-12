import json
import pytest
from test_navigation_params import _params_client, the_galaxy as server

def setup(monkeypatch, state=None):
  client,params=_params_client(monkeypatch,{'IsOnroad':False,'IsOffroad':True,'SafeMode':False,'ForceOffroad':False,**(state or {})},'tici')
  monkeypatch.setattr(server,'_params_raw',params)
  monkeypatch.setattr(server,'_params_live_raw',params)
  monkeypatch.setattr(server,'_get_toggle_backup_keys',lambda:{'ForceOffroad','CustomPersonalities',server.PERSONALITY_PROFILES_PARAM})
  monkeypatch.setattr(server,'_coerce_toggle_restore_value',lambda key,value:value)
  monkeypatch.setattr(server.galaxy_backup,'export_statistics',lambda path:None)
  monkeypatch.setattr(server.utilities,'stop_dashboard_background_analysis',lambda:None)
  monkeypatch.setattr(server.utilities,'_invalidate_dashboard_cache',lambda:None)
  monkeypatch.setattr(server,'update_starpilot_toggles',lambda:None)
  calls=[]
  monkeypatch.setattr(server.galaxy_backup,'apply_restore',lambda *args:calls.append(args) or {'restoredCount':len(args[1]),'addedDrives':0,'existingDrives':0})
  return client,params,calls

def test_standalone_export_restore_excludes_profile_documents(monkeypatch):
  client,params,calls=setup(monkeypatch)
  params.values[server.PERSONALITY_PROFILES_PARAM]={'unsupported':'profile document'}
  response=client.post('/api/backup');assert response.status_code==200,response.data
  data=json.loads(response.data)
  assert data['format']=='starpilot-backup'
  assert data['modelStatistics'] is None
  assert 'personalityProfiles' not in data
  assert data['omittedSettings']==[server.PERSONALITY_PROFILES_PARAM,'CustomPersonalities']
  assert server.PERSONALITY_PROFILES_PARAM not in data['settings']
  assert 'CustomPersonalities' not in data['settings']
  assert client.post('/api/restore',json=data).status_code==200
  assert calls[0][1]=={'ForceOffroad':False}

@pytest.mark.parametrize('damage',['profile','version','missing_statistics','statistics','secret_history','negative_distance'])
def test_invalid_backup_fails_before_apply(monkeypatch,damage):
  client,params,calls=setup(monkeypatch)
  data=json.loads(client.post('/api/backup').data)
  if damage=='profile':data['personalityProfiles']={'profiles':{}}
  elif damage=='version':data['version']=99
  elif damage=='missing_statistics':del data['modelStatistics']
  elif damage=='statistics':
    data['modelStatistics']={'schemaVersion':1,'drives':[],'metrics':[]}
    def unavailable():raise ValueError('Model statistics support is unavailable')
    monkeypatch.setattr(server.galaxy_backup,'_statistics_support',unavailable)
  elif damage=='secret_history':data['history']['GithubSshKeys']='secret'
  else:data['history']['GalaxyDashboardStats']={'version':1,'routes':{'x':{'distanceMeters':-1}}}
  response=client.post('/api/restore',json=data)
  assert response.status_code==400,response.data
  assert not calls

@pytest.mark.parametrize('state',[{'IsOnroad':True},{'SafeMode':True},{'SafeModeBackup':{}},{'IsOffroad':None}])
def test_restore_refuses_unconfirmed_parked_state(monkeypatch,state):
  client,params,calls=setup(monkeypatch,state)
  data=json.loads(client.post('/api/backup').data)
  assert client.post('/api/restore',json=data).status_code==400
  assert not calls

def test_statistics_export_failure_is_explicit(monkeypatch):
  client,params,calls=setup(monkeypatch)
  def unavailable(path):raise ValueError('Model statistics support is unavailable')
  monkeypatch.setattr(server.galaxy_backup,'export_statistics',unavailable)
  response=client.post('/api/backup')
  assert response.status_code==409
  assert 'unavailable' in response.json['message']

@pytest.mark.parametrize('onroad',[False,True])
def test_legacy_file_on_new_route_uses_guarded_restore(monkeypatch,onroad):
  client,params,calls=setup(monkeypatch,{'IsOnroad':onroad,'IsOffroad':not onroad})
  monkeypatch.setattr(server.utilities,'decode_parameters',lambda _: {'ForceOffroad':False,'CustomPersonalities':True})
  response=client.post('/api/restore',json={'format':server.TOGGLE_BACKUP_FORMAT,'version':1,'data':'encoded'})
  assert response.status_code==(400 if onroad else 200),response.data
  if onroad:assert not calls
  else:assert calls[0][1]=={'ForceOffroad':False}


def test_restore_rechecks_live_safe_mode_during_apply(monkeypatch):
  client,params,calls=setup(monkeypatch)
  data=json.loads(client.post('/api/backup').data)
  def apply(*args):
    params.values['SafeMode']=True
    args[-1]()
    raise AssertionError('Restore guard must reject new Safe Mode')
  monkeypatch.setattr(server.galaxy_backup,'apply_restore',apply)
  assert client.post('/api/restore',json=data).status_code==400
