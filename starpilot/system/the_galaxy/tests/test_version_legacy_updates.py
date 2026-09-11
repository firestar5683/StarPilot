"""Real local Git update/rollback regressions. No device, OS flashing or reboot."""
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask, jsonify, request
import pytest
from test_version_routes import server
from test_version_install_rehearsal import rehearsal, git, load_module, write

MODULE_DIR = Path(__file__).resolve().parents[1]

def unpack(state):
  return (getattr(state, name) for name in ('root','repo','origin','old','latest','data','installer','history'))

def test_latest_uses_existing_branch_worker_without_historical_restrictions(server):
  _, ns = server
  ns['_branch_switch_worker'] = Mock()
  ns['version_history'].resolve_version.side_effect = AssertionError('Latest must not require history API')
  ns['_version_install_worker']('StarPilot', 'latest')
  ns['_branch_switch_worker'].assert_called_once_with('StarPilot')
  ns['version_install'].install.assert_not_called()
  ns['_set_fast_update_error_state'].assert_not_called()

def legacy_namespace(repo, data, installer):
  def run(repo, args, **_):
    return subprocess.run(['git','-C',str(repo),*args], capture_output=True, text=True)
  def stdout(repo, args, **_):
    return git(repo, *args)
  def config(repo, key):
    return run(repo, ['config','--get',key]).stdout.strip()
  def fetch(repo, args, **_):
    result=run(repo,args)
    return result.returncode, result.stderr
  params=SimpleNamespace(get_bool=lambda key:(data/'params/d'/key).read_bytes()==b'1',
                         put_bool=lambda key,value:write(data,'params/d/'+key,'1' if value else '0'))
  app=Flask(__name__)
  ns=dict(app=app,request=request,jsonify=jsonify,params=params,time=time,datetime=datetime,timezone=timezone,
          threading=SimpleNamespace(Thread=Mock()), _fast_update_lock=threading.Lock(), _fast_update_state={'running':False},
          _FAST_UPDATE_TOTAL_STEPS=5, _FAST_BRANCH_SWITCH_FETCH_TIMEOUT_S=20, _FAST_ROLLBACK_FETCH_TIMEOUT_S=20,
          _ROLLBACK_REF='refs/starpilot/rollback', _ROLLBACK_BRANCH_CONFIG_KEY='starpilot.rollbackbranch',
          _ROLLBACK_RECORDED_AT_CONFIG_KEY='starpilot.rollbackrecordedat',
          _get_openpilot_root=lambda:repo, _run_git=run, _git_stdout=stdout,
          _git_config_get=config, _git_config_set=lambda repo,key,value:git(repo,'config',key,value),
          _git_config_unset=lambda repo,key:run(repo,['config','--unset',key]),
          _git_update_ref=lambda repo,ref,sha:git(repo,'update-ref',ref,sha),
          _git_delete_ref=lambda repo,ref:git(repo,'update-ref','-d',ref),
          _git_has_commit=lambda repo,sha:run(repo,['cat-file','-e',sha+'^{commit}']).returncode==0,
          _build_shallow_fetch_args=lambda branch:['fetch','--depth=1','origin',branch],
          _build_shallow_fetch_commit_args=lambda sha:['fetch','--depth=1','origin',sha],
          _run_git_with_progress=fetch, _clear_generated_build_state=Mock(), _run_submodule_update_if_needed=Mock(),
          _set_fast_update_state=Mock(), _set_fast_update_progress=Mock(), _set_fast_update_error_state=Mock(),
          _finish_update_and_reboot=Mock(), version_install=SimpleNamespace(clear_pin=lambda:installer.clear_pin(data)))
  names={'_is_valid_git_branch_name','_save_rollback_target','_load_rollback_target','_clear_rollback_target',
         '_branch_switch_worker','_rollback_worker','run_update_rollback'}
  for node in ast.walk(ast.parse((MODULE_DIR/'the_galaxy.py').read_text())):
    if isinstance(node,ast.FunctionDef) and node.name in names:
      exec(compile(ast.Module(body=[node],type_ignores=[]),'the_galaxy.py','exec'),ns)
  return ns, app.test_client()

def test_latest_changed_os_still_uses_standard_update_and_rolls_back(rehearsal):
  root, repo, origin, old, latest, data, installer, history = unpack(rehearsal)
  seed=root/'seed'
  git(seed,'checkout','-b','StarPilot')
  write(seed,'launch_env.sh','export AGNOS_VERSION="99.0"\n')
  write(seed,'system/hardware/tici/agnos.json','[{"name":"system","hash":"new-os"}]\n')
  git(seed,'add','.');git(seed,'commit','-m','Different OS requirement')
  target=git(seed,'rev-parse','HEAD')
  git(seed,'push',str(origin),'StarPilot')
  write(data,'starpilot/version_selection.json',json.dumps({'branch':'Dom','commit':latest}))
  ns, client=legacy_namespace(repo,data,installer)
  ns['_branch_switch_worker']('StarPilot')
  ns['_set_fast_update_error_state'].assert_not_called()
  assert git(repo,'rev-parse','HEAD')==target
  assert '99.0' in (repo/'launch_env.sh').read_text()
  assert not (data/'starpilot/version_selection.json').exists()
  assert (data/'params/d/AutomaticUpdates').read_bytes()==b'1'
  assert ns['_load_rollback_target'](repo)['rollbackCommit']==latest
  ns['_finish_update_and_reboot'].assert_called_once()
  assert client.post('/api/update/rollback').status_code==202
  assert (data/'params/d/AutomaticUpdates').read_bytes()==b'0'
  ns['_rollback_worker']()
  ns['_set_fast_update_error_state'].assert_not_called()
  assert git(repo,'rev-parse','HEAD')==latest
  assert git(repo,'branch','--show-current')=='Dom'
  assert ns['_load_rollback_target'](repo)['rollbackAvailable'] is False
  assert (data/'params/d/ExampleSetting').read_text()=='preserve me'

def test_historical_install_records_previous_commit_for_existing_rollback(rehearsal):
  root, repo, origin, old, latest, data, installer, history = unpack(rehearsal)
  ns, client=legacy_namespace(repo,data,installer)
  git(repo,'fetch','--depth=1','origin',old)
  installer.install(repo,{'branch':'Dom','commit':old,'pinned':True},data_root=data,
                    check_parked=lambda:installer.require_parked(data),progress=lambda *args:None)
  ns['_save_rollback_target'](repo,'Dom',latest)
  assert ns['_load_rollback_target'](repo)['rollbackAvailable'] is True
  assert client.post('/api/update/rollback').status_code==202
  ns['_rollback_worker']()
  ns['_set_fast_update_error_state'].assert_not_called()
  assert git(repo,'rev-parse','HEAD')==latest
  assert not (data/'starpilot/version_selection.json').exists()
  assert (data/'params/d/AutomaticUpdates').read_bytes()==b'0'

def test_rollback_remains_blocked_while_driving_or_updating(rehearsal):
  root, repo, origin, old, latest, data, installer, history = unpack(rehearsal)
  git(repo,'fetch','--depth=1','origin',old)
  ns,client=legacy_namespace(repo,data,installer)
  ns['_save_rollback_target'](repo,'Dom',old)
  write(data,'params/d/IsOnroad','1')
  assert client.post('/api/update/rollback').status_code==409
  write(data,'params/d/IsOnroad','0')
  ns['_fast_update_state']['running']=True
  assert client.post('/api/update/rollback').status_code==409
  ns['threading'].Thread.assert_not_called()
  assert git(repo,'rev-parse','HEAD')==latest
