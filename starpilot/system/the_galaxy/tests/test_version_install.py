import importlib.util
import subprocess
import json
import os
import sqlite3
import stat
from pathlib import Path
import pytest

SPEC=importlib.util.spec_from_file_location('version_install',Path(__file__).resolve().parents[1]/'version_install.py')
if SPEC.origin and Path(SPEC.origin).exists():
 module=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(module)
else: module=None

def git(repo,*args):
 return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.STDOUT).decode().strip()

@pytest.fixture
def fixture(tmp_path):
 repo=tmp_path/'repo';repo.mkdir();git(repo,'init','-b','Dom');git(repo,'config','user.email','test@example.invalid');git(repo,'config','user.name','Test')
 files={'launch_env.sh':'export AGNOS_VERSION="19.6.20"\n','launch_chffrplus.sh':'#!/bin/sh\n','starpilot/common/starpilot_variables.py':'automatic_updates = AutomaticUpdates\n','system/updated/updated.py':'automatic_updates_enabled\n','common/params_keys.h':'AutomaticUpdates\n','system/hardware/tici/agnos.json':'[]\n','feature.txt':'old\n'}
 for name,value in files.items():
  p=repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
 git(repo,'add','.');git(repo,'commit','-m','first');old=git(repo,'rev-parse','HEAD')
 (repo/'feature.txt').write_text('new\n');git(repo,'commit','-am','second');new=git(repo,'rev-parse','HEAD')
 (repo/'feature.txt').write_text('local changes\n');(repo/'local.txt').write_text('untracked settings tool\n')
 data=tmp_path/'data';params=data/'params/d';params.mkdir(parents=True)
 (params/'IsOnroad').write_text('0');(params/'IsOffroad').write_text('1');(params/'AutomaticUpdates').write_text('1');(params/'ExampleSetting').write_text('preserve')
 staging=data/'safe_staging/finalized';staging.mkdir(parents=True);(staging/'.overlay_consistent').write_text('')
 return repo,data,old,new

def run(f,check=lambda:None):
 assert module is not None,'Exact-revision installer is not implemented'
 repo,data,old,new=f
 return module.install(repo,{'branch':'Dom','commit':old,'head':new,'pinned':True},data_root=data,check_parked=check,progress=lambda *a:None,require_device_binaries=False)

def test_installs_exact_revision_and_preserves_local_recovery(fixture):
 result=run(fixture);repo,data,old,new=fixture
 assert git(repo,'rev-parse','HEAD')==old
 assert (repo/'feature.txt').read_text()=='old\n'
 assert (data/'params/d/ExampleSetting').read_text()=='preserve'
 assert (data/'params/d/AutomaticUpdates').read_text()=='0'
 assert not (data/'safe_staging/finalized/.overlay_consistent').exists()
 backup=Path(result['backup'])
 assert (backup/'working.patch').stat().st_size>0
 assert (backup/'recover.py').is_file()
 assert (backup/'params/ExampleSetting').read_text()=='preserve'
 assert module.read_pin(repo,data)['commit']==old
 module.restore(backup,check_parked=lambda:None,restore_data=False)
 assert git(repo,'rev-parse','HEAD')==new
 assert (repo/'feature.txt').read_text()=='local changes\n'
 assert (repo/'local.txt').read_text()=='untracked settings tool\n'

def test_rejects_target_with_incompatible_agnos_before_checkout(fixture):
 repo,data,old,new=fixture
 (repo/'launch_env.sh').write_text('export AGNOS_VERSION="20.0"\n');git(repo,'add','launch_env.sh');git(repo,'commit','-m','new OS')
 current=git(repo,'rev-parse','HEAD')
 assert module is not None,'Exact-revision installer is not implemented'
 with pytest.raises(module.InstallError,match='AGNOS'):
  run((repo,data,old,current))
 assert git(repo,'rev-parse','HEAD')==current
 assert (data/'params/d/AutomaticUpdates').read_text()=='1'

def test_onroad_guard_prevents_changes(fixture):
 repo,data,old,new=fixture
 def reject():raise RuntimeError('park first')
 with pytest.raises(RuntimeError,match='park first'):run(fixture,check=reject)
 assert git(repo,'rev-parse','HEAD')==new
 assert (data/'params/d/AutomaticUpdates').read_text()=='1'

def test_fetch_sha_mismatch_cannot_install_a_different_commit(fixture):
 assert module is not None,'Exact-revision installer is not implemented'
 with pytest.raises(module.InstallError):module.validate_target({'branch':'Dom','commit':'HEAD','pinned':True})

def test_failed_checkout_keeps_recovery_and_restores_previous_source(fixture,monkeypatch):
 assert module is not None,'Exact-revision installer is not implemented'
 repo,data,old,new=fixture
 original=module.git
 def fail(repo,*args,**kwargs):
  if args and args[0]=='checkout' and args[-1]==old:raise module.InstallError('injected checkout failure')
  return original(repo,*args,**kwargs)
 monkeypatch.setattr(module,'git',fail)
 with pytest.raises(module.InstallError,match='injected'):run(fixture)
 assert git(repo,'rev-parse','HEAD')==new
 assert (repo/'feature.txt').read_text()=='local changes\n'
 assert (data/'params/d/ExampleSetting').read_text()=='preserve'


def test_atomic_write_preserves_mode_and_does_not_touch_another_temporary_file(tmp_path):
 path=tmp_path/'setting';path.write_bytes(b'old');path.chmod(0o640)
 stale=tmp_path/'setting.version-tmp';stale.write_bytes(b'other writer')
 module.atomic_write(path,b'new')
 assert path.read_bytes()==b'new' and stat.S_IMODE(path.stat().st_mode)==0o640
 assert stale.read_bytes()==b'other writer'


@pytest.mark.parametrize('content',['[]','null','1','"text"','{broken'])
def test_malformed_pin_is_ignored(fixture,content):
 repo,data,*_=fixture
 path=data/'starpilot/version_selection.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
 assert module.read_pin(repo,data) is None


def test_untracked_symlink_rejected_before_source_or_settings_changes(fixture):
 repo,data,old,new=fixture
 (repo/'unsupported-link').symlink_to('feature.txt')
 with pytest.raises(module.InstallError,match='symlink|regular file'):run(fixture)
 assert git(repo,'rev-parse','HEAD')==new and (repo/'feature.txt').read_text()=='local changes\n'
 assert (data/'params/d/AutomaticUpdates').read_text()=='1'
 assert (data/'safe_staging/finalized/.overlay_consistent').exists()


def test_new_branch_has_explicit_origin_upstream(fixture):
 repo,data,old,new=fixture
 git(repo,'remote','add','origin','https://github.com/example/project.git')
 module.install(repo,{'branch':'feature/old','commit':old,'head':new,'pinned':True},data_root=data,check_parked=lambda:None,progress=lambda *a:None,require_device_binaries=False)
 assert git(repo,'config','branch.feature/old.remote')=='origin'
 assert git(repo,'config','branch.feature/old.merge')=='refs/heads/feature/old'


def test_database_backup_contains_wal_and_recovery_keeps_newer_settings_and_stats(fixture):
 repo,data,old,new=fixture
 db=data/'starpilot/model_stats.sqlite';db.parent.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(db) as connection:
  connection.execute('pragma journal_mode=WAL');connection.execute('create table events (id integer, note text)')
  connection.execute('insert into events values (1, ?)',('before',));connection.commit()
  result=run(fixture)
  backup=Path(result['backup'])
  with sqlite3.connect(backup/'model_stats.sqlite') as saved:
   assert saved.execute('select * from events').fetchall()==[(1,'before')]
   assert saved.execute('pragma integrity_check').fetchone()==('ok',)
  connection.execute('insert into events values (2, ?)',('after',));connection.commit()
  (data/'params/d/ExampleSetting').write_text('newer setting')
  module.restore(backup,check_parked=lambda:None)
  assert connection.execute('select * from events').fetchall()==[(1,'before'),(2,'after')]
 assert (data/'params/d/ExampleSetting').read_text()=='newer setting'
 assert (backup/'params/ExampleSetting').read_text()=='preserve'


def test_device_preflight_checks_actual_installed_os_before_mutation(fixture,tmp_path,monkeypatch):
 repo,data,old,new=fixture
 version=tmp_path/'VERSION';version.write_text('18.0\n')
 monkeypatch.setattr(module,'OS_VERSION_FILE',version)
 with pytest.raises(module.InstallError,match='running|installed'):
  module.install(repo,{'branch':'Dom','commit':old,'head':new,'pinned':True},data_root=data,check_parked=lambda:None,progress=lambda *a:None,require_device_binaries=True)
 assert git(repo,'rev-parse','HEAD')==new and (data/'params/d/AutomaticUpdates').read_text()=='1'


def test_active_tesla_setting_rejects_target_without_wake_support(fixture):
 repo,data,old,new=fixture
 (data/'params/d/TeslaWakeOnCAN').write_text('1')
 with pytest.raises(module.InstallError,match='TeslaWakeOnCAN'):run(fixture)
 assert git(repo,'rev-parse','HEAD')==new and (data/'params/d/TeslaWakeOnCAN').read_text()=='1'
 assert (data/'params/d/AutomaticUpdates').read_text()=='1'


@pytest.mark.parametrize('setting',['RemoteStartBootsComma','HKGRemoteStartBootsComma','IgnoreIgnitionLine'])
def test_active_panda_variant_cannot_be_silently_ignored(fixture,setting):
 repo,data,old,new=fixture
 (data/'params/d'/setting).write_text('1')
 with pytest.raises(module.InstallError,match=setting):run(fixture)
 assert git(repo,'rev-parse','HEAD')==new and (data/'params/d'/setting).read_text()=='1'


def test_dirty_submodule_is_rejected_without_losing_edits(fixture,tmp_path):
 repo,data,old,new=fixture
 child=tmp_path/'child';child.mkdir();git(child,'init','-b','main');git(child,'config','user.name','Test');git(child,'config','user.email','test@example.invalid')
 (child/'nested.txt').write_text('original');git(child,'add','.');git(child,'commit','-m','child')
 git(repo,'-c','protocol.file.allow=always','submodule','add',str(child),'vendor/child')
 git(repo,'commit','-m','submodule')
 current=git(repo,'rev-parse','HEAD');(repo/'vendor/child/nested.txt').write_text('valuable local edit')
 with pytest.raises(module.InstallError,match='submodule'):run((repo,data,old,current))
 assert git(repo,'rev-parse','HEAD')==current
 assert (repo/'vendor/child/nested.txt').read_text()=='valuable local edit'
 assert (data/'params/d/AutomaticUpdates').read_text()=='1'


def test_backup_failure_does_not_disable_updates_or_change_source(fixture,monkeypatch):
 repo,data,old,new=fixture
 def fail(*a,**kw):raise OSError('backup full')
 monkeypatch.setattr(module.shutil,'copytree',fail)
 with pytest.raises(OSError,match='backup full'):run(fixture)
 assert git(repo,'rev-parse','HEAD')==new and (repo/'feature.txt').read_text()=='local changes\n'
 assert (data/'params/d/AutomaticUpdates').read_text()=='1'


@pytest.mark.parametrize('lock',['index.lock','shallow.lock'])
def test_repository_idle_check_rejects_locks_without_deleting_them(fixture,lock):
 repo,data,*_=fixture
 path=repo/'.git'/lock;path.write_text('busy')
 with pytest.raises(module.InstallError,match='lock|busy'):module.check_repository_idle(repo)
 assert path.read_text()=='busy'


@pytest.mark.parametrize('argv',[[b'python3',b'-m',b'openpilot.system.updated.updated'],[b'system.updated.updated'],[b'python3',b'/data/openpilot/system/updated/updated.py']])
def test_updater_recognizes_prefixed_process_titles(argv):
 assert module._is_updater(argv) is True


def test_updater_does_not_match_unrelated_process():
 assert module._is_updater([b'python3',b'/tmp/not-updated.py']) is False


def firmware_target(fixture, *, missing=False):
 repo,data,old,new=fixture
 selector=(Path(__file__).resolve().parents[4]/'selfdrive/pandad/panda_firmware.py').read_text()
 path=repo/'selfdrive/pandad/panda_firmware.py';path.parent.mkdir(parents=True);path.write_text(selector)
 (repo/'common/params_keys.h').write_text('AutomaticUpdates TeslaWakeOnCAN RemoteStartBootsComma HKGRemoteStartBootsComma IgnoreIgnitionLine')
 for name in ('panda_tesla_wake.bin.signed','panda_h7_tesla_wake.bin.signed'):
  path=repo/'panda/board/obj'/name;path.parent.mkdir(parents=True,exist_ok=True)
  if not missing or 'h7' not in name:path.write_bytes(b'firmware-test-content')
 git(repo,'add','selfdrive','panda','common/params_keys.h');git(repo,'commit','-m','firmware')
 target=git(repo,'rev-parse','HEAD')
 (data/'params/d/TeslaWakeOnCAN').write_text('1')
 return target


def test_active_firmware_variant_validates_target_images(fixture):
 repo,data,*_=fixture
 target=firmware_target(fixture)
 assert module.preflight(repo,target,False,data)['agnos']=='19.6.20'


def test_missing_selected_h7_image_blocks_even_when_other_image_exists(fixture):
 repo,data,*_=fixture
 target=firmware_target(fixture,missing=True)
 with pytest.raises(module.InstallError,match='panda_h7_tesla_wake'):
  module.preflight(repo,target,False,data)
 assert (data/'params/d/TeslaWakeOnCAN').read_bytes()==b'1'


def test_modified_recovery_archive_is_rejected_before_checkout(fixture):
 import io
 import tarfile
 repo,data,*_=fixture
 result=run(fixture)
 backup=Path(result['backup'])
 with tarfile.open(backup/'untracked.tar','w') as archive:
  member=tarfile.TarInfo('../escaped');member.size=4;archive.addfile(member,io.BytesIO(b'evil'))
 before=git(repo,'rev-parse','HEAD')
 with pytest.raises(module.InstallError,match='Unsafe recovery'):
  module.restore(backup,check_parked=lambda:None)
 assert git(repo,'rev-parse','HEAD')==before
 assert not (repo.parent/'escaped').exists()


@pytest.mark.parametrize('restart',[False,True])
def test_updater_only_signals_owned_processes_and_restarts_after_install(monkeypatch,restart):
 records={100:(1,'1000','S',[b'openpilot.system.updated.updated']),
          101:(100,'1001','S',[b'git',b'fetch']),
          102:(1,'1002','T',[b'system.updated.updated']),
          103:(1,'1003','S',[b'other'])}
 calls=[]
 monkeypatch.setattr(module,'_processes',lambda:dict(records))
 def kill(pid,sig):
  calls.append((pid,sig))
  parent,start,state,argv=records[pid]
  records[pid]=(parent,start,'T' if sig==module.signal.SIGSTOP else 'S',argv)
 monkeypatch.setattr(module.os,'kill',kill)
 with module.suspend_updater() as control:
  assert records[100][2]==records[101][2]=='T'
  if restart:control.restart_after_install()
 end=module.signal.SIGKILL if restart else module.signal.SIGCONT
 assert calls==[(100,module.signal.SIGSTOP),(101,module.signal.SIGSTOP),(101,end),(100,end)]
 assert not any(pid in (102,103) for pid,_ in calls)
 assert module._ACTIVE_UPDATER.get() is None


def test_updater_does_not_signal_reused_pid(monkeypatch):
 records={100:(1,'original','S',[b'system.updated.updated'])}
 calls=[]
 monkeypatch.setattr(module,'_processes',lambda:dict(records))
 def kill(pid,sig):
  calls.append((pid,sig));records[pid]=(1,'original','T',[b'system.updated.updated'])
 monkeypatch.setattr(module.os,'kill',kill)
 with module.suspend_updater() as control:
  control.restart_after_install()
  records[100]=(1,'replacement','S',[b'other'])
 assert calls==[(100,module.signal.SIGSTOP)]


def test_failed_install_recovery_marks_updater_for_restart(fixture,monkeypatch):
 repo,data,old,new=fixture
 original=module.git
 def fail(repo,*args,**kwargs):
  if args and args[0]=='checkout' and args[-1]==old:raise module.InstallError('checkout failure')
  return original(repo,*args,**kwargs)
 monkeypatch.setattr(module,'git',fail)
 monkeypatch.setattr(module,'_processes',lambda:{})
 with module.suspend_updater() as control:
  with pytest.raises(module.InstallError,match='previous source restored'):run(fixture)
  assert control.restart
 assert (data/'params/d/AutomaticUpdates').read_bytes()==b'0'


def test_failure_after_update_pause_still_restarts_updater(fixture,monkeypatch):
 repo,data,*_=fixture
 monkeypatch.setattr(module,'_processes',lambda:{})
 def fail(*args):raise OSError('staging failure')
 monkeypatch.setattr(module,'_clear_staging',fail)
 with module.suspend_updater() as control:
  with pytest.raises(OSError,match='staging failure'):run(fixture)
  assert control.restart
 assert (data/'params/d/AutomaticUpdates').read_bytes()==b'0'


def test_failed_manual_restore_after_pause_still_restarts_updater(fixture,monkeypatch):
 repo,data,*_=fixture
 backup=Path(run(fixture)['backup'])
 (data/'params/d/AutomaticUpdates').write_bytes(b'1')
 monkeypatch.setattr(module,'_processes',lambda:{})
 original=module.git
 def fail(repo,*args,**kwargs):
  if args and args[0]=='checkout':raise module.InstallError('restore checkout failure')
  return original(repo,*args,**kwargs)
 monkeypatch.setattr(module,'git',fail)
 with module.suspend_updater() as control:
  with pytest.raises(module.InstallError,match='restore checkout failure'):
   module.restore(backup,check_parked=lambda:None)
  assert control.restart
 assert (data/'params/d/AutomaticUpdates').read_bytes()==b'0'


def test_preflight_failure_does_not_restart_updater(fixture,monkeypatch):
 repo,data,*_=fixture
 (repo/'.git/index.lock').write_bytes(b'busy')
 monkeypatch.setattr(module,'_processes',lambda:{})
 with module.suspend_updater() as control:
  with pytest.raises(module.InstallError,match='busy'):run(fixture)
  assert not control.restart
 assert (data/'params/d/AutomaticUpdates').read_bytes()==b'1'


def test_reviewed_legacy_firmware_selector_remains_compatible(fixture):
 repo,data,*_=fixture
 firmware_target(fixture)
 path=repo/'selfdrive/pandad/panda_firmware.py'
 source=path.read_text()
 guard='  if tesla_wake and (remote_start or hkg_remote_start):\n    raise ValueError("Tesla wake firmware cannot be combined with remote-start firmware")\n'
 path.write_text(source.replace(guard,''))
 git(repo,'add',str(path));git(repo,'commit','--allow-empty','-m','legacy firmware selector')
 assert module.preflight(repo,git(repo,'rev-parse','HEAD'),False,data)['agnos']=='19.6.20'


@pytest.mark.parametrize('key', ['RemoteStartBootsComma', 'HKGRemoteStartBootsComma', 'RemoteStart', 'HkgRemoteStart'])
def test_conflicting_enabled_firmware_flags_are_refused(fixture,key):
 repo,data,*_=fixture
 target=firmware_target(fixture)
 (data/'params/d'/key).write_text('1')
 with pytest.raises(module.InstallError,match='cannot be combined'):
  module.preflight(repo,target,False,data)
 assert (data/'params/d/TeslaWakeOnCAN').read_bytes()==b'1'
 assert (data/'params/d'/key).read_bytes()==b'1'


def test_unrecognized_firmware_selector_is_refused(fixture):
 repo,data,*_=fixture
 firmware_target(fixture)
 path=repo/'selfdrive/pandad/panda_firmware.py'
 path.write_text(path.read_text().replace('name_parts.extend(["tesla", "wake"])','name_parts.extend(["unexpected", "wake"])'))
 git(repo,'add',str(path));git(repo,'commit','-m','unrecognized firmware selector')
 with pytest.raises(module.InstallError,match='unrecognized firmware selection logic'):
  module.preflight(repo,git(repo,'rev-parse','HEAD'),False,data)
