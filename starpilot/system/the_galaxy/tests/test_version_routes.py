"""Exercise the real route/worker bodies without loading vehicle daemons."""
import ast
from contextlib import nullcontext
import importlib.util
from pathlib import Path
import threading
from types import SimpleNamespace
import time
from unittest.mock import Mock

from flask import Flask, jsonify, request
import pytest

MODULE_DIR = Path(__file__).resolve().parents[1]

def load_module(name):
  spec = importlib.util.spec_from_file_location(name, MODULE_DIR / (name + '.py'))
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module

@pytest.fixture
def server():
  app = Flask(__name__)
  history, installer = load_module('version_history'), load_module('version_install')
  ns = dict(app=app, jsonify=jsonify, request=request, time=time, re=__import__('re'), Path=Path,
            version_history=history, version_install=installer, threading=SimpleNamespace(Thread=Mock()),
            _fast_update_lock=threading.Lock(), _fast_update_state={'running': False}, _FAST_UPDATE_TOTAL_STEPS=5,
            _get_openpilot_root=lambda: '/repo', _is_valid_git_branch_name=lambda repo, branch: branch in ('Dom','StarPilot','feature/test'),
            _get_fast_update_state=lambda: {}, _set_fast_update_state=Mock(), _set_fast_update_progress=Mock(),
            _set_fast_update_error_state=Mock(), _remote_git_check_allowed=lambda: True,
            _git_stdout=Mock(return_value='a'*40), _run_git_with_progress=Mock(return_value=(0,'')),
            _build_shallow_fetch_commit_args=lambda sha: ['fetch','--depth=1','origin',sha],
            _save_rollback_target=Mock(), update_starpilot_toggles=Mock(), HARDWARE=SimpleNamespace(reboot=Mock()),
            _FAST_UPDATE_REBOOT_NOTICE_SECONDS=0)
  history.resolve_version=Mock(return_value={'branch':'Dom','commit':'a'*40,'head':'b'*40,'pinned':True})
  history.list_versions=Mock(return_value={'branch':'Dom','head':'b'*40,'page':1,'hasMore':False,'commits':[]})
  installer.require_parked=Mock()
  installer.updater_control=SimpleNamespace(restart_after_install=Mock())
  installer.suspend_updater=lambda: nullcontext(installer.updater_control)
  installer.check_repository_idle=Mock()
  installer.install=Mock(return_value={'backup':'/data/test','commit':'a'*40,'branch':'Dom','pinned':True})
  tree=ast.parse((MODULE_DIR/'the_galaxy.py').read_text())
  names={'get_update_versions','run_version_install','_version_install_worker'}
  found=[node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name in names]
  assert len(found)==len(names),'Version routes and worker not implemented'
  for node in sorted(found,key=lambda n:n.name):
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(MODULE_DIR/'the_galaxy.py'),'exec'),ns)
  return app.test_client(),ns

def test_history_uses_branch_and_pinned_pagination(server):
  client,ns=server
  reply=client.get('/api/update/versions?branch=feature/test&page=2&head='+'b'*40)
  assert reply.status_code==200
  ns['version_history'].list_versions.assert_called_once_with('/repo','feature/test',page=2,head='b'*40)

@pytest.mark.parametrize('body',[{},[],{'branch':'Dom','commit':'a'*40}, {'branch':'Dom','commit':'HEAD','confirmed':True}, {'branch':'-evil','commit':'latest','confirmed':True}, {'branch':'Dom','commit':'latest','confirmed':'true'}])
def test_invalid_install_never_starts_worker(server,body):
  client,ns=server
  assert client.post('/api/update/version',json=body).status_code==400
  ns['threading'].Thread.assert_not_called()

def test_install_requires_known_parked_state(server):
  client,ns=server
  ns['version_install'].require_parked.side_effect=ns['version_install'].InstallError('Park first')
  assert client.post('/api/update/version',json={'branch':'Dom','commit':'latest','confirmed':True}).status_code==409
  ns['threading'].Thread.assert_not_called()

def test_concurrent_install_rejected(server):
  client,ns=server
  ns['_fast_update_state']['running']=True
  assert client.post('/api/update/version',json={'branch':'Dom','commit':'latest','confirmed':True}).status_code==409
  ns['threading'].Thread.assert_not_called()

def test_accepted_selection_keeps_exact_sha(server):
  client,ns=server
  assert client.post('/api/update/version',json={'branch':'Dom','commit':'c'*40,'confirmed':True}).status_code==202
  assert ns['_fast_update_state']['running'] is True
  assert ns['threading'].Thread.call_args.kwargs['args']==('Dom','c'*40)

def test_worker_refuses_fetch_mismatch_before_checkout_or_reboot(server):
  _,ns=server
  ns['_git_stdout'].return_value='d'*40
  ns['_version_install_worker']('Dom','a'*40)
  ns['version_install'].install.assert_not_called()
  ns['HARDWARE'].reboot.assert_not_called()
  ns['_set_fast_update_error_state'].assert_called_once()

def test_worker_preserves_selected_sha_and_rechecks_parked(server):
  _,ns=server
  ns['_version_install_worker']('Dom','a'*40)
  ns['version_history'].resolve_version.assert_called_once_with('/repo','Dom','a'*40)
  assert ns['_run_git_with_progress'].call_args.args[1][-1]=='a'*40
  assert ns['version_install'].install.call_args.args[1]['commit']=='a'*40
  assert ns['version_install'].require_parked.call_count>=3
  ns['HARDWARE'].reboot.assert_called_once()

def test_resolution_failure_does_not_fetch_or_change_source(server):
  _,ns=server
  ns['version_history'].resolve_version.side_effect=RuntimeError('Branch rewritten')
  ns['_version_install_worker']('Dom','a'*40)
  ns['_run_git_with_progress'].assert_not_called()
  ns['version_install'].install.assert_not_called()
  ns['HARDWARE'].reboot.assert_not_called()

def test_post_install_failure_reports_installed_revision_and_restarts_updater(server):
  _,ns=server
  ns['HARDWARE'].reboot.side_effect=RuntimeError('reboot denied')
  ns['_version_install_worker']('Dom','a'*40)
  ns['version_install'].updater_control.restart_after_install.assert_called_once()
  assert 'is installed' in ns['_set_fast_update_error_state'].call_args.args[0]
  ns['_set_fast_update_state'].assert_called_with(recoveryBackup='/data/test')

def test_install_failure_never_marks_success_or_reboots(server):
  _,ns=server
  ns['version_install'].install.side_effect=RuntimeError('disk full')
  ns['_version_install_worker']('Dom','a'*40)
  ns['version_install'].updater_control.restart_after_install.assert_not_called()
  ns['HARDWARE'].reboot.assert_not_called()

def test_history_has_no_artificial_page_depth_cutoff(server):
  client,ns=server
  reply=client.get('/api/update/versions?branch=Dom&page=1201&head='+'b'*40)
  assert reply.status_code==200
  ns['version_history'].list_versions.assert_called_once_with('/repo','Dom',page=1201,head='b'*40)

def test_historical_worker_records_pre_install_branch_and_commit_for_rollback(server):
  _, ns = server
  ns['_git_stdout'].side_effect=['a'*40, 'feature/test', 'b'*40]
  ns['_version_install_worker']('Dom','a'*40)
  ns['_save_rollback_target'].assert_called_once_with('/repo','feature/test','b'*40)
  ns['_set_fast_update_error_state'].assert_not_called()
